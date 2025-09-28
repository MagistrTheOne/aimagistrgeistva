"""Unit tests for domain models."""

import pytest
from uuid import uuid4

from app.domain.models import (
    Command,
    CommandStatus,
    CommandType,
    ConversationContext,
    UserProfile,
)


def test_user_profile_creation():
    """Test UserProfile creation."""
    profile = UserProfile(
        telegram_id=12345,
        name="Test User",
        language="ru",
    )

    assert profile.telegram_id == 12345
    assert profile.name == "Test User"
    assert profile.language == "ru"
    assert profile.preferences == {}
    assert profile.id is not None


def test_command_creation():
    """Test Command creation."""
    user_id = uuid4()
    session_id = uuid4()

    command = Command(
        type=CommandType.CHAT_MESSAGE,
        user_id=user_id,
        session_id=session_id,
        payload={"text": "Hello"},
    )

    assert command.type == CommandType.CHAT_MESSAGE
    assert command.user_id == user_id
    assert command.session_id == session_id
    assert command.payload["text"] == "Hello"
    assert command.status == CommandStatus.PENDING


def test_conversation_context():
    """Test ConversationContext creation."""
    user_id = uuid4()

    context = ConversationContext(
        user_id=user_id,
        context_data={"topic": "work"},
    )

    assert context.user_id == user_id
    assert context.context_data["topic"] == "work"
    assert context.messages == []


def test_command_status_transitions():
    """Test command status transitions."""
    command = Command(type=CommandType.CHAT_MESSAGE, user_id=uuid4())

    assert command.status == CommandStatus.PENDING

    command.status = CommandStatus.PROCESSING
    assert command.status == CommandStatus.PROCESSING

    command.status = CommandStatus.COMPLETED
    assert command.status == CommandStatus.COMPLETED
    assert command.completed_at is not None


def test_domain_events():
    """Test domain events creation."""
    from app.domain.models import VoiceHotwordDetected

    session_id = uuid4()

    event = VoiceHotwordDetected(
        aggregate_id=session_id,
        device_id="mic1",
        confidence=0.95,
    )

    assert event.event_type == "voice.hotword.detected"
    assert event.aggregate_id == session_id
    assert event.device_id == "mic1"
    assert event.confidence == 0.95
    assert event.event_id is not None
    assert event.timestamp is not None
