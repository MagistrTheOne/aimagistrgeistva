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
