"""Command orchestrator for AI Мага."""

import asyncio
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.adapters.rate_limit import check_rate_limit
from app.core.config import settings
from app.core.di import get_logger, get_metrics
from app.core.errors import AIError, RateLimitError
from app.domain.commands import CommandType, create_command
from app.domain.events import publish_event
from app.domain.models import (
    ActionCompleted,
    Command,
    IntentDetected,
    TranscriptionReady,
    VoiceHotwordDetected,
)
from app.domain.policies import AuthorizationPolicy
from app.services.llm.yandex_gpt import yandex_gpt
from app.services.voice.stt import stt
from app.services.voice.tts import tts


class ActionStep:
    """Шаг в плане действий."""

    def __init__(
        self,
        step_id: str,
        action: str,
        service: str,
        params: Dict[str, Any],
        timeout_ms: int = 5000,
        required: bool = True,
    ):
        self.step_id = step_id
        self.action = action
        self.service = service
        self.params = params
        self.timeout_ms = timeout_ms
        self.required = required
        self.status = "pending"  # pending, running, completed, failed
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None


class ActionPlan:
    """План выполнения действий."""

    def __init__(self, plan_id: str, intent: str, user_id: str, time_budget_ms: int):
        self.plan_id = plan_id
        self.intent = intent
        self.user_id = user_id
        self.time_budget_ms = time_budget_ms
        self.steps: List[ActionStep] = []
        self.status = "planning"  # planning, executing, completed, failed, timeout
        self.created_at = time.time()
        self.completed_at: Optional[float] = None
        self.total_time_ms: float = 0.0
        self.results: Dict[str, Any] = {}

    def add_step(self, step: ActionStep):
        """Добавить шаг в план."""
        self.steps.append(step)

    def get_next_step(self) -> Optional[ActionStep]:
        """Получить следующий шаг для выполнения."""
        for step in self.steps:
            if step.status == "pending":
                return step
        return None

    def mark_step_completed(self, step_id: str, result: Any = None):
        """Отметить шаг как выполненный."""
        for step in self.steps:
            if step.step_id == step_id:
                step.status = "completed"
                step.result = result
                step.end_time = time.time()
                if step.start_time:
                    step_duration = (step.end_time - step.start_time) * 1000
                    self.total_time_ms += step_duration
                break

    def mark_step_failed(self, step_id: str, error: str):
        """Отметить шаг как проваленный."""
        for step in self.steps:
            if step.step_id == step_id:
                step.status = "failed"
                step.error = error
                step.end_time = time.time()
                if step.start_time:
                    step_duration = (step.end_time - step.start_time) * 1000
                    self.total_time_ms += step_duration
                break

    def is_completed(self) -> bool:
        """Проверить, завершен ли план."""
        return all(step.status in ["completed", "failed"] for step in self.steps)

    def has_failed_required_step(self) -> bool:
        """Проверить, есть ли проваленные обязательные шаги."""
        return any(
            step.status == "failed" and step.required
            for step in self.steps
        )

    def get_execution_time_ms(self) -> float:
        """Получить время выполнения плана."""
        if self.completed_at:
            return (self.completed_at - self.created_at) * 1000
        return (time.time() - self.created_at) * 1000


class CommandOrchestrator:
    """Orchestrates command execution across services."""

    def __init__(self):
        self.logger = get_logger()
        self.metrics = get_metrics()
        self.active_commands: Dict[UUID, asyncio.Task] = {}
        self.active_plans: Dict[str, ActionPlan] = {}

    def _create_action_plan(self, intent_result, user_id: str) -> ActionPlan:
        """Создать план действий на основе распознанного интента."""
        from app.services.nlp_nlu import IntentType

        plan_id = f"plan_{int(time.time())}_{user_id}"
        plan = ActionPlan(
            plan_id=plan_id,
            intent=intent_result.intent.value,
            user_id=user_id,
            time_budget_ms=settings.orch_time_budget_ms,
        )

        # Создаем шаги на основе интента
        if intent_result.intent == IntentType.CHAT_ANSWER:
            plan.add_step(ActionStep(
                step_id="chat_1",
                action="generate_response",
                service="llm",
                params={"text": intent_result.slots.get("query", intent_result.raw_text)},
                timeout_ms=10000,
            ))

        elif intent_result.intent == IntentType.HH_SEARCH:
            plan.add_step(ActionStep(
                step_id="hh_search_1",
                action="search_jobs",
                service="hh_api",
                params={
                    "query": intent_result.slots.get("query", ""),
                    "location": intent_result.slots.get("location"),
                    "seniority": intent_result.slots.get("seniority"),
                    "salary_min": intent_result.slots.get("salary_min"),
                    "salary_max": intent_result.slots.get("salary_max"),
                },
                timeout_ms=8000,
            ))

        elif intent_result.intent == IntentType.OCR_TRANSLATE:
            plan.add_step(ActionStep(
                step_id="ocr_1",
                action="take_screenshot",
                service="vision",
                params={},
                timeout_ms=3000,
            ))
            plan.add_step(ActionStep(
                step_id="ocr_2",
                action="ocr_text",
                service="vision",
                params={"image_source": "screenshot"},
                timeout_ms=5000,
            ))
            plan.add_step(ActionStep(
                step_id="translate_1",
                action="translate_text",
                service="translation",
                params={
                    "target_lang": intent_result.slots.get("lang", settings.translate_default_lang)
                },
                timeout_ms=3000,
            ))

        elif intent_result.intent == IntentType.REMIND:
            plan.add_step(ActionStep(
                step_id="remind_1",
                action="create_reminder",
                service="scheduler",
                params={
                    "title": intent_result.slots.get("query", "Напоминание"),
                    "when": intent_result.slots.get("when"),
                    "duration": intent_result.slots.get("duration"),
                },
                timeout_ms=2000,
            ))

        elif intent_result.intent == IntentType.TAKE_SCREENSHOT:
            plan.add_step(ActionStep(
                step_id="screenshot_1",
                action="take_screenshot",
                service="vision",
                params={},
                timeout_ms=3000,
            ))

        elif intent_result.intent == IntentType.READ_ALOUD:
            plan.add_step(ActionStep(
                step_id="tts_1",
                action="synthesize_speech",
                service="tts",
                params={
                    "text": intent_result.slots.get("query", intent_result.raw_text),
                    "lang": intent_result.slots.get("lang", "ru"),
                },
                timeout_ms=5000,
            ))

        # Ограничение количества шагов
        if len(plan.steps) > settings.orch_max_steps:
            plan.steps = plan.steps[:settings.orch_max_steps]

        return plan

    async def _execute_action_plan(self, plan: ActionPlan) -> Dict[str, Any]:
        """Выполнить план действий."""
        plan.status = "executing"
        start_time = time.time()

        try:
            while not plan.is_completed():
                # Проверка таймаута
                if plan.get_execution_time_ms() > plan.time_budget_ms:
                    plan.status = "timeout"
                    break

                step = plan.get_next_step()
                if not step:
                    break

                # Выполнение шага
                step.start_time = time.time()
                step.status = "running"

                try:
                    result = await self._execute_step(step)
                    plan.mark_step_completed(step.step_id, result)
                    plan.results[step.step_id] = result

                except Exception as e:
                    error_msg = f"Step {step.step_id} failed: {str(e)}"
                    self.logger.error(error_msg)
                    plan.mark_step_failed(step.step_id, error_msg)

                    # Если обязательный шаг провалился, останавливаем план
                    if step.required:
                        plan.status = "failed"
                        break

            # Финализация плана
            plan.completed_at = time.time()
            plan.status = "completed" if not plan.has_failed_required_step() else "failed"

            return {
                "plan_id": plan.plan_id,
                "status": plan.status,
                "execution_time_ms": plan.get_execution_time_ms(),
                "steps_completed": len([s for s in plan.steps if s.status == "completed"]),
                "steps_failed": len([s for s in plan.steps if s.status == "failed"]),
                "results": plan.results,
            }

        except Exception as e:
            plan.status = "failed"
            plan.completed_at = time.time()
            raise e

    async def _execute_step(self, step: ActionStep) -> Any:
        """Выполнить отдельный шаг плана."""
        self.logger.info(f"Executing step {step.step_id}: {step.action}")

        if step.service == "llm":
            if step.action == "generate_response":
                return await yandex_gpt.chat(step.params["text"])

        elif step.service == "vision":
            if step.action == "take_screenshot":
                # TODO: Implement screenshot functionality
                return {"screenshot_id": "mock_screenshot"}
            elif step.action == "ocr_text":
                # TODO: Implement OCR functionality
                return {"text": "Mock OCR text"}

        elif step.service == "translation":
            if step.action == "translate_text":
                # TODO: Implement translation
                return {
                    "original_text": step.params.get("text", ""),
                    "translated_text": f"Translated: {step.params.get('text', '')}",
                    "target_lang": step.params.get("target_lang", "en")
                }

        elif step.service == "tts":
            if step.action == "synthesize_speech":
                return await tts.synthesize(
                    text=step.params["text"],
                    language=step.params.get("lang", "ru")
                )

        elif step.service == "scheduler":
            if step.action == "create_reminder":
                # TODO: Implement reminder creation
                return {"reminder_id": "mock_reminder"}

        elif step.service == "hh_api":
            if step.action == "search_jobs":
                # TODO: Implement HH.ru search
                return {"jobs": [], "total": 0}

        # Unknown service/action
        raise ValueError(f"Unknown service/action: {step.service}/{step.action}")

    async def orchestrate_intent(self, intent_result, user_id: str) -> Dict[str, Any]:
        """Оркестрировать выполнение интента через Action Plan."""
        try:
            # Проверка авторизации
            if not AuthorizationPolicy.can_execute_command(UUID(user_id), None):
                raise AIError("Unauthorized access", "AUTHZ_ERROR", 403)

            # Проверка rate limit
            await check_rate_limit(user_id, None)  # TODO: Add intent-based rate limiting

            # Создание плана
            plan = self._create_action_plan(intent_result, user_id)
            self.active_plans[plan.plan_id] = plan

            # Выполнение плана
            result = await self._execute_action_plan(plan)

            # Метрики
            self.metrics.increment("orchestrator_plans_total", status=result["status"])
            self.metrics.histogram("orchestrator_plan_duration", result["execution_time_ms"])

            return result

        except RateLimitError:
            self.metrics.increment("orchestrator_rate_limited_total")
            raise
        except Exception as e:
            self.logger.error(f"Orchestration failed: {e}")
            self.metrics.increment("orchestrator_errors_total")
            raise

    async def handle_voice_input(
        self,
        audio_data: bytes,
        session_id: UUID,
        user_id: UUID,
    ) -> Optional[str]:
        """
        Handle voice input: STT -> Intent Detection -> Orchestration.

        Args:
            audio_data: Raw audio data
            session_id: Voice session ID
            user_id: User ID

        Returns:
            Response text to speak back
        """
        from app.services.nlp_nlu import Utterance, nlu_processor

        try:
            # Step 1: Speech-to-Text
            self.logger.info("Starting STT processing", session_id=str(session_id))
            stt_result = await stt.transcribe(audio_data)

            transcription = stt_result["text"]
            confidence = stt_result["confidence"]

            self.logger.info(
                "STT completed",
                session_id=str(session_id),
                transcription=transcription,
                confidence=confidence,
            )

            # Publish transcription event
            await publish_event(TranscriptionReady(
                aggregate_id=session_id,
                text=transcription,
                language="ru-RU",  # TODO: detect language
                confidence=confidence,
            ))

            if not transcription or confidence < 0.5:
                return "Не расслышал. Повтори, пожалуйста."

            # Step 2: Intent Detection using NLU processor
            utterance = Utterance(
                text=transcription,
                source="voice",
                language="ru",
                timestamp=time.time(),
                user_id=str(user_id),
            )

            intent_result = await nlu_processor.detect_intent(utterance)

            self.logger.info(
                "Intent detected",
                session_id=str(session_id),
                intent=intent_result.intent.value,
                confidence=intent_result.confidence,
                slots=intent_result.slots,
            )

            # Publish intent event
            await publish_event(IntentDetected(
                aggregate_id=session_id,
                intent=intent_result.intent.value,
                slots=intent_result.slots,
                confidence=intent_result.confidence,
            ))

            if intent_result.confidence < settings.nlp_confidence_threshold:
                return "Не понял намерение. Уточни, пожалуйста."

            # Step 3: Orchestrate through Action Plan
            plan_result = await self.orchestrate_intent(intent_result, str(user_id))

            # Extract final response
            if plan_result["status"] == "completed":
                # Get the final result from the last step
                results = plan_result["results"]
                if results:
                    last_step_result = list(results.values())[-1]
                    if isinstance(last_step_result, str):
                        return last_step_result
                    elif isinstance(last_step_result, dict) and "translated_text" in last_step_result:
                        return last_step_result["translated_text"]
                    elif isinstance(last_step_result, dict) and "text" in last_step_result:
                        return last_step_result["text"]

                return "Задача выполнена успешно."
            else:
                return f"Не удалось выполнить задачу. Статус: {plan_result['status']}"

        except Exception as e:
            self.logger.error(
                "Voice processing failed",
                session_id=str(session_id),
                error=str(e),
            )
            self.metrics.increment("voice_processing_errors_total")
            return "Произошла ошибка при обработке голоса."

    async def execute_command(self, command: Command) -> str:
        """
        Execute a command and return response.

        Args:
            command: Command to execute

        Returns:
            Response text
        """
        try:
            self.logger.info(
                "Executing command",
                command_id=str(command.id),
                command_type=command.type.value,
            )

            # Update command status
            command.status = "processing"
            # TODO: Save to database

            response = ""

            # Route to appropriate handler
            if command.type == CommandType.CHAT_MESSAGE:
                response = await self._handle_chat_message(command)
            elif command.type == CommandType.SEARCH_JOBS:
                response = await self._handle_search_jobs(command)
            elif command.type == CommandType.CREATE_REMINDER:
                response = await self._handle_create_reminder(command)
            elif command.type == CommandType.TRANSLATE_TEXT:
                response = await self._handle_translate_text(command)
            elif command.type == CommandType.READ_TEXT:
                response = await self._handle_read_text(command)
            elif command.type == CommandType.GENERATE_RESPONSE:
                response = await self._handle_generate_response(command)
            else:
                response = "Неизвестная команда."

            # Update command status
            command.status = "completed"
            command.result = {"response": response}
            # TODO: Save to database

            self.metrics.increment("commands_completed_total", command_type=command.type.value)

            return response

        except Exception as e:
            self.logger.error(
                "Command execution failed",
                command_id=str(command.id),
                error=str(e),
            )

            command.status = "failed"
            command.error_message = str(e)
            # TODO: Save to database

            self.metrics.increment("commands_failed_total", command_type=command.type.value)

            return "Ошибка выполнения команды."

    async def _handle_chat_message(self, command: Command) -> str:
        """Handle chat message command."""
        text = command.payload.get("text", "")

        # Use GPT for general chat
        response = await yandex_gpt.chat(text)

        return response

    async def _handle_search_jobs(self, command: Command) -> str:
        """Handle job search command."""
        query = command.payload.get("query", "")

        # TODO: Integrate with HH.ru API
        # For now, return mock response
        return f"Ищу вакансии по запросу: {query}. Результаты будут доступны скоро."

    async def _handle_create_reminder(self, command: Command) -> str:
        """Handle create reminder command."""
        # TODO: Implement reminder creation
        return "Напоминание создано."

    async def _handle_translate_text(self, command: Command) -> str:
        """Handle text translation command."""
        # TODO: Integrate with Yandex Translate
        text = command.payload.get("text", "")
        return f"Перевод текста: {text}"

    async def _handle_read_text(self, command: Command) -> str:
        """Handle read text command."""
        text = command.payload.get("text", "")

        # TODO: Generate audio and play it
        return f"Читаю текст: {text}"

    async def _handle_generate_response(self, command: Command) -> str:
        """Handle generate response command."""
        prompt = command.payload.get("prompt", "")

        response = await yandex_gpt.chat(prompt)
        return response

    async def handle_hotword_detected(
        self,
        device_id: str,
        session_id: UUID,
        user_id: UUID,
    ):
        """Handle hotword detection."""
        self.logger.info(
            "Hotword detected",
            device_id=device_id,
            session_id=str(session_id),
        )

        # Publish hotword event
        await publish_event(VoiceHotwordDetected(
            aggregate_id=session_id,
            device_id=device_id,
            confidence=1.0,  # Hotword detection confidence
        ))

        # TODO: Start voice recording session
        # TODO: Return audio focus to AI Мага

    async def cancel_command(self, command_id: UUID):
        """Cancel a running command."""
        if command_id in self.active_commands:
            task = self.active_commands[command_id]
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            del self.active_commands[command_id]

    async def get_command_status(self, command_id: UUID) -> Optional[Dict[str, Any]]:
        """Get command execution status."""
        # TODO: Load from database
        return None


# Global orchestrator instance
orchestrator = CommandOrchestrator()
