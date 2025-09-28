"""Domain events handling."""

from typing import Any, Awaitable, Callable, Dict, List
from uuid import UUID

from app.domain.models import DomainEvent


class EventBus:
    """Simple in-memory event bus."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable[[DomainEvent], Awaitable[None]]]] = {}

    def subscribe(self, event_type: str, handler: Callable[[DomainEvent], Awaitable[None]]):
        """Subscribe to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent):
        """Publish an event to all subscribers."""
        event_type = event.event_type
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    # Log error but don't stop other handlers
                    print(f"Error in event handler for {event_type}: {e}")

    async def publish_batch(self, events: List[DomainEvent]):
        """Publish multiple events."""
        for event in events:
            await self.publish(event)


# Additional event types for Iteration 2
class ActionStarted(DomainEvent):
    """Event when action execution starts."""

    event_type: str = "action.started"
    action_id: str
    plan_id: str
    action_type: str
    started_at: float


class ActionFailed(DomainEvent):
    """Event when action execution fails."""

    event_type: str = "action.failed"
    action_id: str
    plan_id: str
    action_type: str
    error: str
    failed_at: float


class PlanCreated(DomainEvent):
    """Event when orchestration plan is created."""

    event_type: str = "plan.created"
    plan_id: str
    intent: str
    user_id: str
    step_count: int


class PlanCompleted(DomainEvent):
    """Event when orchestration plan is completed."""

    event_type: str = "plan.completed"
    plan_id: str
    status: str
    execution_time_ms: float
    step_results: Dict[str, Any]


class RateLimitExceeded(DomainEvent):
    """Event when rate limit is exceeded."""

    event_type: str = "rate_limit.exceeded"
    user_id: str
    action: str
    limit: int
    window_seconds: int


class UserMessageReceived(DomainEvent):
    """Event when user message is received."""

    event_type: str = "user.message.received"
    user_id: str
    message_id: str
    source: str
    content_type: str
    content_length: int


class TelegramCommandReceived(DomainEvent):
    """Event when Telegram command is received."""

    event_type: str = "telegram.command.received"
    user_id: str
    command: str
    args: List[str]
    message_id: str


# Global event bus instance
event_bus = EventBus()


async def publish_event(event: DomainEvent):
    """Convenience function to publish an event."""
    await event_bus.publish(event)


def subscribe_to_event(event_type: str):
    """Decorator to subscribe to an event type."""
    def decorator(handler: Callable[[DomainEvent], Awaitable[None]]):
        event_bus.subscribe(event_type, handler)
        return handler
    return decorator
