"""Unit tests for command orchestrator."""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.services.nlp_nlu import IntentResult, IntentType, SlotType
from app.services.orchestrator import (
    ActionPlan,
    ActionStep,
    CommandOrchestrator,
    orchestrator,
)


class TestActionStep:
    """Test ActionStep functionality."""

    def test_action_step_creation(self):
        """Test ActionStep creation."""
        step = ActionStep(
            step_id="test_1",
            action="test_action",
            service="test_service",
            params={"key": "value"},
            timeout_ms=5000,
            required=True,
        )

        assert step.step_id == "test_1"
        assert step.action == "test_action"
        assert step.service == "test_service"
        assert step.params == {"key": "value"}
        assert step.timeout_ms == 5000
        assert step.required is True
        assert step.status == "pending"

    def test_step_status_transitions(self):
        """Test step status transitions."""
        step = ActionStep("test_1", "action", "service", {})

        assert step.status == "pending"

        step.status = "running"
        assert step.status == "running"

        step.status = "completed"
        assert step.status == "completed"


class TestActionPlan:
    """Test ActionPlan functionality."""

    def test_action_plan_creation(self):
        """Test ActionPlan creation."""
        plan = ActionPlan(
            plan_id="test_plan",
            intent="chat_answer",
            user_id="user123",
            time_budget_ms=1000,
        )

        assert plan.plan_id == "test_plan"
        assert plan.intent == "chat_answer"
        assert plan.user_id == "user123"
        assert plan.time_budget_ms == 1000
        assert plan.status == "planning"
        assert len(plan.steps) == 0

    def test_plan_step_management(self):
        """Test adding and managing steps in plan."""
        plan = ActionPlan("test_plan", "test_intent", "user123", 1000)

        step1 = ActionStep("step1", "action1", "service1", {})
        step2 = ActionStep("step2", "action2", "service2", {})

        plan.add_step(step1)
        plan.add_step(step2)

        assert len(plan.steps) == 2
        assert plan.steps[0].step_id == "step1"
        assert plan.steps[1].step_id == "step2"

    def test_plan_completion(self):
        """Test plan completion logic."""
        plan = ActionPlan("test_plan", "test_intent", "user123", 1000)

        # Add and complete steps
        step1 = ActionStep("step1", "action1", "service1", {})
        step2 = ActionStep("step2", "action2", "service2", {})
        plan.add_step(step1)
        plan.add_step(step2)

        plan.mark_step_completed("step1", "result1")
        plan.mark_step_completed("step2", "result2")

        assert plan.is_completed()
        assert not plan.has_failed_required_step()

    def test_plan_with_failed_step(self):
        """Test plan with failed required step."""
        plan = ActionPlan("test_plan", "test_intent", "user123", 1000)

        step1 = ActionStep("step1", "action1", "service1", {}, required=True)
        step2 = ActionStep("step2", "action2", "service2", {}, required=False)
        plan.add_step(step1)
        plan.add_step(step2)

        plan.mark_step_failed("step1", "error")
        plan.mark_step_completed("step2", "result")

        assert plan.is_completed()
        assert plan.has_failed_required_step()

    def test_plan_timeout(self):
        """Test plan timeout logic."""
        import time
        plan = ActionPlan("test_plan", "test_intent", "user123", 100)  # Very short budget

        # Simulate time passing
        plan.created_at = time.time() - 1  # 1 second ago

        assert plan.get_execution_time_ms() > 100  # Should be timed out


class TestCommandOrchestrator:
    """Test CommandOrchestrator functionality."""

    @pytest.fixture
    def orchestrator_instance(self):
        """Create orchestrator instance."""
        return CommandOrchestrator()

    def test_orchestrator_creation(self, orchestrator_instance):
        """Test orchestrator creation."""
        assert orchestrator_instance.active_commands == {}
        assert orchestrator_instance.active_plans == {}

    def test_create_action_plan_chat_answer(self, orchestrator_instance):
        """Test creating action plan for chat answer."""
        intent_result = IntentResult(
            intent=IntentType.CHAT_ANSWER,
            confidence=0.9,
            slots={SlotType.QUERY: "test query"},
            raw_text="test text",
        )

        plan = orchestrator_instance._create_action_plan(intent_result, "user123")

        assert plan.intent == "chat_answer"
        assert plan.user_id == "user123"
        assert len(plan.steps) == 1
        assert plan.steps[0].action == "generate_response"
        assert plan.steps[0].service == "llm"

    def test_create_action_plan_hh_search(self, orchestrator_instance):
        """Test creating action plan for HH search."""
        intent_result = IntentResult(
            intent=IntentType.HH_SEARCH,
            confidence=0.9,
            slots={
                SlotType.QUERY: "python developer",
                SlotType.LOCATION: "Москва",
                SlotType.SALARY_MIN: 100000,
            },
            raw_text="test text",
        )

        plan = orchestrator_instance._create_action_plan(intent_result, "user123")

        assert len(plan.steps) == 1
        assert plan.steps[0].action == "search_jobs"
        assert plan.steps[0].service == "hh_api"
        assert plan.steps[0].params["query"] == "python developer"
        assert plan.steps[0].params["location"] == "Москва"
        assert plan.steps[0].params["salary_min"] == 100000

    def test_create_action_plan_ocr_translate(self, orchestrator_instance):
        """Test creating action plan for OCR + translate."""
        intent_result = IntentResult(
            intent=IntentType.OCR_TRANSLATE,
            confidence=0.9,
            slots={SlotType.LANG: "en"},
            raw_text="test text",
        )

        plan = orchestrator_instance._create_action_plan(intent_result, "user123")

        assert len(plan.steps) == 3
        assert plan.steps[0].action == "take_screenshot"
        assert plan.steps[1].action == "ocr_text"
        assert plan.steps[2].action == "translate_text"

    def test_create_action_plan_remind(self, orchestrator_instance):
        """Test creating action plan for reminder."""
        intent_result = IntentResult(
            intent=IntentType.REMIND,
            confidence=0.9,
            slots={
                SlotType.QUERY: "buy milk",
                SlotType.WHEN: "tomorrow",
            },
            raw_text="test text",
        )

        plan = orchestrator_instance._create_action_plan(intent_result, "user123")

        assert len(plan.steps) == 1
        assert plan.steps[0].action == "create_reminder"
        assert plan.steps[0].service == "scheduler"

    def test_create_action_plan_screenshot(self, orchestrator_instance):
        """Test creating action plan for screenshot."""
        intent_result = IntentResult(
            intent=IntentType.TAKE_SCREENSHOT,
            confidence=0.9,
            slots={},
            raw_text="test text",
        )

        plan = orchestrator_instance._create_action_plan(intent_result, "user123")

        assert len(plan.steps) == 1
        assert plan.steps[0].action == "take_screenshot"
        assert plan.steps[0].service == "vision"

    def test_create_action_plan_read_aloud(self, orchestrator_instance):
        """Test creating action plan for text-to-speech."""
        intent_result = IntentResult(
            intent=IntentType.READ_ALOUD,
            confidence=0.9,
            slots={SlotType.QUERY: "hello world"},
            raw_text="test text",
        )

        plan = orchestrator_instance._create_action_plan(intent_result, "user123")

        assert len(plan.steps) == 1
        assert plan.steps[0].action == "synthesize_speech"
        assert plan.steps[0].service == "tts"

    @pytest.mark.asyncio
    async def test_execute_step_llm(self, orchestrator_instance):
        """Test executing LLM step."""
        step = ActionStep(
            "test_step",
            "generate_response",
            "llm",
            {"text": "test message"},
        )

        with patch('app.services.orchestrator.yandex_gpt') as mock_gpt:
            mock_gpt.chat = AsyncMock(return_value="test response")

            result = await orchestrator_instance._execute_step(step)

            assert result == "test response"
            mock_gpt.chat.assert_called_once_with("test message")

    @pytest.mark.asyncio
    async def test_execute_step_tts(self, orchestrator_instance):
        """Test executing TTS step."""
        step = ActionStep(
            "test_step",
            "synthesize_speech",
            "tts",
            {"text": "test text", "lang": "ru"},
        )

        with patch('app.services.orchestrator.tts') as mock_tts:
            mock_tts.synthesize = AsyncMock(return_value=b"audio_data")

            result = await orchestrator_instance._execute_step(step)

            assert result == b"audio_data"
            mock_tts.synthesize.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_step_unknown(self, orchestrator_instance):
        """Test executing unknown step."""
        step = ActionStep(
            "test_step",
            "unknown_action",
            "unknown_service",
            {},
        )

        with pytest.raises(ValueError, match="Unknown service/action"):
            await orchestrator_instance._execute_step(step)

    @pytest.mark.asyncio
    async def test_orchestrate_intent_success(self, orchestrator_instance):
        """Test successful intent orchestration."""
        intent_result = IntentResult(
            intent=IntentType.CHAT_ANSWER,
            confidence=0.9,
            slots={SlotType.QUERY: "test"},
            raw_text="test",
        )

        with patch.object(orchestrator_instance, '_execute_action_plan') as mock_execute:
            mock_execute.return_value = {
                "plan_id": "test_plan",
                "status": "completed",
                "execution_time_ms": 100.0,
                "steps_completed": 1,
                "steps_failed": 0,
                "results": {"step1": "response"},
            }

            result = await orchestrator_instance.orchestrate_intent(intent_result, "user123")

            assert result["status"] == "completed"
            assert result["plan_id"] == "test_plan"

    @pytest.mark.asyncio
    async def test_orchestrate_intent_unauthorized(self, orchestrator_instance):
        """Test orchestration with unauthorized user."""
        intent_result = IntentResult(
            intent=IntentType.CHAT_ANSWER,
            confidence=0.9,
            slots={},
            raw_text="test",
        )

        with patch('app.services.orchestrator.AuthorizationPolicy.can_execute_command', return_value=False):
            with pytest.raises(Exception):  # Should raise AIError
                await orchestrator_instance.orchestrate_intent(intent_result, "user123")

    def test_max_steps_limit(self, orchestrator_instance):
        """Test that plan respects max steps limit."""
        from app.core.config import settings

        # Create intent that would generate many steps
        intent_result = IntentResult(
            intent=IntentType.OCR_TRANSLATE,
            confidence=0.9,
            slots={},
            raw_text="test",
        )

        # Temporarily set low max steps
        original_max = settings.orch_max_steps
        settings.orch_max_steps = 1

        try:
            plan = orchestrator_instance._create_action_plan(intent_result, "user123")
            assert len(plan.steps) == 1  # Should be limited
        finally:
            settings.orch_max_steps = original_max
