"""Unit tests for NLU (Natural Language Understanding) system."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.nlp_nlu import (
    IntentResult,
    IntentType,
    NLUProcessor,
    SlotType,
    Utterance,
    nlu_processor,
)


class TestNLUProcessor:
    """Test NLU processor functionality."""

    @pytest.fixture
    def processor(self):
        """Create NLU processor instance."""
        return NLUProcessor()

    def test_intent_patterns_initialization(self, processor):
        """Test that intent patterns are properly initialized."""
        assert len(processor.intent_patterns) > 0

        # Check that all patterns have required fields
        for pattern in processor.intent_patterns:
            assert pattern.intent is not None
            assert len(pattern.patterns) > 0
            assert isinstance(pattern.optional_slots, list)
            assert isinstance(pattern.required_slots, list)

    def test_rule_based_confidence_calculation(self, processor):
        """Test rule-based confidence calculation."""
        # Test exact match
        text = "Мага, найди вакансии Python в Москве"
        confidence, slots = processor._calculate_rule_based_confidence(text, processor.intent_patterns[0])

        assert confidence >= 0.0
        assert isinstance(slots, dict)

    @pytest.mark.parametrize("text,intent_type", [
        ("Мага, слушай", IntentType.WAKE),
        ("привет", IntentType.CHAT_ANSWER),
        ("найди работу", IntentType.HH_SEARCH),
        ("переведи текст", IntentType.OCR_TRANSLATE),
        ("напомни мне", IntentType.REMIND),
        ("сделай скриншот", IntentType.TAKE_SCREENSHOT),
    ])
    @pytest.mark.asyncio
    async def test_intent_detection_basic(self, processor, text, intent_type):
        """Test basic intent detection with various inputs."""
        utterance = Utterance(
            text=text,
            source="voice",
            language="ru",
            timestamp=1234567890.0,
            user_id="test_user",
        )

        # Mock LLM to avoid external calls
        with patch.object(processor, '_calculate_llm_confidence', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = None  # Force rule-based only

            result = await processor.detect_intent(utterance)

            assert isinstance(result, IntentResult)
            assert result.raw_text == text
            assert result.confidence >= 0.0

    def test_slot_extraction(self, processor):
        """Test slot extraction from text."""
        text = "найди вакансии Python в Москве от 100000 рублей"
        slots = processor._extract_slots(text, IntentType.HH_SEARCH)

        assert SlotType.QUERY in slots
        assert SlotType.LOCATION in slots
        assert SlotType.SALARY_MIN in slots

    @pytest.mark.asyncio
    async def test_fallback_to_chat_answer(self, processor):
        """Test fallback to chat_answer for unknown intents."""
        utterance = Utterance(
            text="какая погода сегодня",
            source="voice",
            language="ru",
            timestamp=1234567890.0,
            user_id="test_user",
        )

        # Mock LLM to return None (no good matches)
        with patch.object(processor, '_calculate_llm_confidence', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = None

            result = await processor.detect_intent(utterance)

            assert result.intent == IntentType.CHAT_ANSWER
            assert result.confidence == 0.5

    @pytest.mark.asyncio
    async def test_llm_confidence_calculation(self, processor):
        """Test LLM-based confidence calculation."""
        text = "помоги мне найти работу"

        # Mock GPT response
        mock_response = {
            "intent": "hh_search",
            "confidence": 0.85,
            "explanation": "User is asking for job search help"
        }

        with patch('app.services.nlp_nlu.yandex_gpt') as mock_gpt:
            mock_gpt.generate = AsyncMock(return_value={"text": '{"intent": "hh_search", "confidence": 0.85, "explanation": "User is asking for job search help"}'})

            rule_results = [(IntentType.HH_SEARCH, 0.6, {}), (IntentType.CHAT_ANSWER, 0.3, {})]
            result = await processor._calculate_llm_confidence(text, rule_results)

            assert result is not None
            assert result.intent == IntentType.HH_SEARCH
            assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_confidence_threshold(self, processor):
        """Test confidence threshold filtering."""
        from app.core.config import settings

        # Temporarily set low threshold
        original_threshold = settings.nlp_confidence_threshold
        settings.nlp_confidence_threshold = 0.8

        try:
            utterance = Utterance(
                text="привет",
                source="voice",
                language="ru",
                timestamp=1234567890.0,
                user_id="test_user",
            )

            with patch.object(processor, '_calculate_llm_confidence', new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = None

                result = await processor.detect_intent(utterance)

                # Should fallback to chat_answer due to low confidence
                assert result.intent == IntentType.CHAT_ANSWER
                assert result.confidence == 0.5

        finally:
            settings.nlp_confidence_threshold = original_threshold

    def test_utterance_creation(self):
        """Test Utterance model creation."""
        utterance = Utterance(
            text="тестовый текст",
            source="telegram",
            language="ru",
            timestamp=1234567890.0,
            user_id="user123",
        )

        assert utterance.text == "тестовый текст"
        assert utterance.source == "telegram"
        assert utterance.language == "ru"
        assert utterance.user_id == "user123"

    def test_intent_result_creation(self):
        """Test IntentResult model creation."""
        result = IntentResult(
            intent=IntentType.CHAT_ANSWER,
            confidence=0.9,
            slots={SlotType.QUERY: "test query"},
            raw_text="тестовый текст",
            explanation="rule-based match",
        )

        assert result.intent == IntentType.CHAT_ANSWER
        assert result.confidence == 0.9
        assert result.slots[SlotType.QUERY] == "test query"
        assert result.raw_text == "тестовый текст"
        assert result.explanation == "rule-based match"


class TestIntentTypes:
    """Test intent type definitions."""

    def test_intent_type_values(self):
        """Test that all intent types have string values."""
        for intent_type in IntentType:
            assert isinstance(intent_type.value, str)
            assert len(intent_type.value) > 0

    def test_all_intents_covered(self):
        """Test that all expected intents are defined."""
        expected_intents = {
            "wake", "sleep", "pause", "resume", "set_lang", "set_volume",
            "chat_answer", "summarize", "read_aloud",
            "hh_search", "jobs_digest", "compose_reply",
            "ocr_translate", "describe_screen",
            "remind", "schedule_task", "daily_digest",
            "open_app", "take_screenshot", "clipboard_read"
        }

        actual_intents = {intent.value for intent in IntentType}

        assert expected_intents.issubset(actual_intents)


class TestSlotTypes:
    """Test slot type definitions."""

    def test_slot_type_values(self):
        """Test that all slot types have string values."""
        for slot_type in SlotType:
            assert isinstance(slot_type.value, str)
            assert len(slot_type.value) > 0

    def test_slot_extraction_patterns(self):
        """Test slot extraction patterns work."""
        processor = NLUProcessor()

        # Test language extraction
        slots = processor._extract_slots("переведи на английский", IntentType.OCR_TRANSLATE)
        assert SlotType.LANG in slots
        assert slots[SlotType.LANG] == "en"

        # Test location extraction
        slots = processor._extract_slots("вакансии в Санкт-Петербурге", IntentType.HH_SEARCH)
        assert SlotType.LOCATION in slots

        # Test salary extraction
        slots = processor._extract_slots("зарплата от 150000 рублей", IntentType.HH_SEARCH)
        assert SlotType.SALARY_MIN in slots
        assert slots[SlotType.SALARY_MIN] == 150000
