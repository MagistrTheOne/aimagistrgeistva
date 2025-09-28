"""Command orchestrator for AI Мага."""

import asyncio
from typing import Any, Dict, Optional
from uuid import UUID

from app.core.di import get_logger, get_metrics
from app.core.errors import AIError
from app.domain.commands import CommandType, create_command
from app.domain.events import publish_event
from app.domain.models import (
    ActionCompleted,
    Command,
    IntentDetected,
    TranscriptionReady,
    VoiceHotwordDetected,
)
from app.services.llm.yandex_gpt import yandex_gpt
from app.services.voice.stt import stt
from app.services.voice.tts import tts


class CommandOrchestrator:
    """Orchestrates command execution across services."""

    def __init__(self):
        self.logger = get_logger()
        self.metrics = get_metrics()
        self.active_commands: Dict[UUID, asyncio.Task] = {}

    async def handle_voice_input(
        self,
        audio_data: bytes,
        session_id: UUID,
        user_id: UUID,
    ) -> Optional[str]:
        """
        Handle voice input: STT -> Intent Detection -> Command Execution.

        Args:
            audio_data: Raw audio data
            session_id: Voice session ID
            user_id: User ID

        Returns:
            Response text to speak back
        """
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

            # Step 2: Intent Detection
            intents = [
                "chat_message",
                "search_jobs",
                "create_reminder",
                "translate_text",
                "read_text",
                "generate_response",
            ]

            intent_result = await yandex_gpt.classify_intent(transcription, intents)

            intent = intent_result["intent"]
            intent_confidence = intent_result["confidence"]

            self.logger.info(
                "Intent detected",
                session_id=str(session_id),
                intent=intent,
                confidence=intent_confidence,
            )

            # Publish intent event
            await publish_event(IntentDetected(
                aggregate_id=session_id,
                intent=intent,
                slots={},  # TODO: extract slots
                confidence=intent_confidence,
            ))

            if intent_confidence < 0.3:
                return "Не понял намерение. Уточни, пожалуйста."

            # Step 3: Execute Command
            command_type = CommandType(intent)
            command = create_command(command_type, user_id=user_id, session_id=session_id)

            # Add command-specific parameters
            if command_type == CommandType.CHAT_MESSAGE:
                command.payload["text"] = transcription
            elif command_type == CommandType.SEARCH_JOBS:
                command.payload["query"] = transcription
            # TODO: Add more command parameter extraction

            response = await self.execute_command(command)

            # Publish completion event
            await publish_event(ActionCompleted(
                aggregate_id=command.id,
                action_id=command.id,
                status="completed",
                result={"response": response},
            ))

            return response

        except Exception as e:
            self.logger.error(
                "Voice processing failed",
                session_id=str(session_id),
                error=str(e),
            )
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
