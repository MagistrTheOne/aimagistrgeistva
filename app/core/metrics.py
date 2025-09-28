"""Metrics collection using Prometheus."""

import asyncio
from typing import Any, Dict

from prometheus_client import Counter, Gauge, Histogram, start_http_server
from prometheus_client.core import CollectorRegistry

from app.core.config import settings


class MetricsCollector:
    """Prometheus metrics collector."""

    def __init__(self):
        self.registry = CollectorRegistry()

        # Request metrics
        self.request_total = Counter(
            "ai_maga_requests_total",
            "Total number of requests",
            ["method", "endpoint", "status"],
            registry=self.registry,
        )

        self.request_duration = Histogram(
            "ai_maga_request_duration_seconds",
            "Request duration in seconds",
            ["method", "endpoint"],
            registry=self.registry,
        )

        # Voice pipeline metrics
        self.voice_commands_total = Counter(
            "ai_maga_voice_commands_total",
            "Total number of voice commands processed",
            ["status"],
            registry=self.registry,
        )

        self.voice_processing_duration = Histogram(
            "ai_maga_voice_processing_duration_seconds",
            "Voice processing duration in seconds",
            ["stage"],
            registry=self.registry,
        )

        # LLM metrics
        self.llm_requests_total = Counter(
            "ai_maga_llm_requests_total",
            "Total number of LLM requests",
            ["model", "status"],
            registry=self.registry,
        )

        self.llm_tokens_used = Counter(
            "ai_maga_llm_tokens_total",
            "Total number of tokens used",
            ["model", "direction"],
            registry=self.registry,
        )

        # Integration metrics
        self.integration_requests_total = Counter(
            "ai_maga_integration_requests_total",
            "Total number of integration requests",
            ["service", "status"],
            registry=self.registry,
        )

        # Error metrics
        self.errors_total = Counter(
            "ai_maga_errors_total",
            "Total number of errors",
            ["type", "component"],
            registry=self.registry,
        )

        # System metrics
        self.active_connections = Gauge(
            "ai_maga_active_connections",
            "Number of active connections",
            registry=self.registry,
        )

        self.memory_usage = Gauge(
            "ai_maga_memory_usage_bytes",
            "Memory usage in bytes",
            registry=self.registry,
        )

    def increment(self, name: str, value: int = 1, **labels: Any) -> None:
        """Increment a counter metric."""
        metric = getattr(self, name, None)
        if metric and isinstance(metric, Counter):
            metric.labels(**labels).inc(value)

    def gauge(self, name: str, value: float, **labels: Any) -> None:
        """Set a gauge metric."""
        metric = getattr(self, name, None)
        if metric and isinstance(metric, Gauge):
            metric.labels(**labels).set(value)

    def histogram(self, name: str, value: float, **labels: Any) -> None:
        """Observe a histogram metric."""
        metric = getattr(self, name, None)
        if metric and isinstance(metric, Histogram):
            metric.labels(**labels).observe(value)

    async def start_server(self):
        """Start Prometheus metrics server."""
        try:
            start_http_server(
                port=settings.metrics_port,
                addr="0.0.0.0",
                registry=self.registry,
            )
            print(f"Metrics server started on port {settings.metrics_port}")
        except Exception as e:
            print(f"Failed to start metrics server: {e}")


# Global metrics instance
metrics = MetricsCollector()


async def get_health_status() -> Dict[str, Any]:
    """Get health status information."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.app_env,
        "database_connected": True,  # TODO: implement actual check
        "redis_connected": True,     # TODO: implement actual check
    }
