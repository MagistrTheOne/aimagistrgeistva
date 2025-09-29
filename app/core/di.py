"""Dependency Injection container."""

from typing import Any, Protocol

from app.core.config import settings


class LoggerProtocol(Protocol):
    """Logger protocol."""

    def info(self, message: str, **kwargs) -> None: ...
    def error(self, message: str, **kwargs) -> None: ...
    def warning(self, message: str, **kwargs) -> None: ...
    def debug(self, message: str, **kwargs) -> None: ...


class MetricsProtocol(Protocol):
    """Metrics protocol."""

    def increment(self, name: str, value: int = 1, **labels) -> None: ...
    def gauge(self, name: str, value: float, **labels) -> None: ...
    def histogram(self, name: str, value: float, **labels) -> None: ...


class DatabaseProtocol(Protocol):
    """Database protocol."""

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...


class RedisProtocol(Protocol):
    """Redis protocol."""

    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> int: ...
    async def exists(self, key: str) -> bool: ...
    async def expire(self, key: str, ttl: int) -> bool: ...
    async def incr(self, key: str) -> int: ...
    async def publish(self, channel: str, message: str) -> int: ...
    async def set_json(self, key: str, data: Any, ttl: int | None = None) -> None: ...
    async def get_json(self, key: str) -> Any: ...

    # Task Management
    async def add_task(self, task_id: str, task_data: dict) -> None: ...
    async def get_task(self, task_id: str) -> dict | None: ...
    async def get_user_tasks(self, user_id: str) -> list: ...
    async def update_task_status(self, task_id: str, status: str) -> None: ...

    # Document Management
    async def store_document(self, doc_id: str, doc_data: dict) -> None: ...
    async def get_document(self, doc_id: str) -> dict | None: ...

    # Financial Records
    async def add_expense(self, user_id: str, expense_data: dict) -> None: ...
    async def get_user_expenses(self, user_id: str, limit: int = 50) -> list: ...

    # RSS Feed Cache
    async def cache_feed_item(self, feed_url: str, item_data: dict, ttl: int = 3600) -> None: ...
    async def get_cached_feed_items(self, feed_url: str) -> list: ...

    # User Preferences
    async def set_user_preference(self, user_id: str, key: str, value: Any) -> None: ...
    async def get_user_preference(self, user_id: str, key: str) -> Any: ...

    # Background Jobs Queue
    async def enqueue_job(self, job_type: str, job_data: dict) -> None: ...
    async def dequeue_job(self, job_type: str) -> dict | None: ...

    # Notification Queue
    async def schedule_notification(self, user_id: str, notification: dict, delay_seconds: int = 0) -> None: ...
    async def get_pending_notifications(self, user_id: str) -> list: ...
    async def get_due_notifications(self, user_id: str) -> list: ...


class HTTPClientProtocol(Protocol):
    """HTTP client protocol."""

    async def get(self, url: str, **kwargs) -> dict: ...
    async def post(self, url: str, **kwargs) -> dict: ...


class Container:
    """Dependency injection container."""

    def __init__(self):
        self._services = {}
        self._singletons = {}

    def register(self, interface: type, implementation: type, singleton: bool = False):
        """Register a service implementation."""
        self._services[interface] = (implementation, singleton)

    def register_instance(self, interface: type, instance):
        """Register a service instance."""
        self._singletons[interface] = instance

    def resolve(self, interface: type):
        """Resolve a service instance."""
        if interface in self._singletons:
            return self._singletons[interface]

        if interface not in self._services:
            raise ValueError(f"Service {interface} not registered")

        implementation, singleton = self._services[interface]

        if singleton:
            instance = implementation()
            self._singletons[interface] = instance
            return instance

        return implementation()


# Global container instance
container = Container()


def get_logger() -> LoggerProtocol:
    """Get logger instance."""
    return container.resolve(LoggerProtocol)


def get_metrics() -> MetricsProtocol:
    """Get metrics instance."""
    return container.resolve(MetricsProtocol)


def get_database() -> DatabaseProtocol:
    """Get database instance."""
    return container.resolve(DatabaseProtocol)


def get_redis() -> RedisProtocol:
    """Get Redis instance."""
    return container.resolve(RedisProtocol)


def get_http_client() -> HTTPClientProtocol:
    """Get HTTP client instance."""
    return container.resolve(HTTPClientProtocol)


def init_container():
    """Initialize the DI container with default implementations."""
    from app.adapters.db import DatabaseAdapter
    from app.adapters.http_client import HTTPClient
    from app.adapters.redis_client import RedisAdapter
    from app.core.logging import get_structlog_logger
    from app.core.metrics import MetricsCollector

    # Register services
    container.register(LoggerProtocol, lambda: get_structlog_logger(), singleton=True)
    container.register(MetricsProtocol, MetricsCollector, singleton=True)
    container.register(DatabaseProtocol, DatabaseAdapter, singleton=True)
    container.register(RedisProtocol, RedisAdapter, singleton=True)
    container.register(HTTPClientProtocol, HTTPClient, singleton=True)


def get_settings():
    """Get application settings."""
    return settings
