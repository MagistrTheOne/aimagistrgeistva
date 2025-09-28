"""HTTP client adapter with retry, backoff and circuit breaker."""

import asyncio
from typing import Any, Dict, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.core.config import settings
from app.core.di import HTTPClientProtocol
from app.core.errors import ExternalServiceError


class CircuitBreakerOpenError(Exception):
    """Circuit breaker is open."""
    pass


class SimpleCircuitBreaker:
    """Simple circuit breaker implementation."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit."""
        if self.state != "open":
            return True

        current_time = asyncio.get_event_loop().time()
        if current_time - self.last_failure_time >= self.recovery_timeout:
            self.state = "half-open"
            return True

        return False

    def record_success(self):
        """Record a successful call."""
        if self.state == "half-open":
            self.state = "closed"
        self.failures = 0

    def record_failure(self):
        """Record a failed call."""
        self.failures += 1
        self.last_failure_time = asyncio.get_event_loop().time()

        if self.failures >= self.failure_threshold:
            self.state = "open"

    def call_allowed(self) -> bool:
        """Check if call is allowed."""
        if self.state == "closed":
            return True
        elif self.state == "open":
            return self._should_attempt_reset()
        else:  # half-open
            return True


class HTTPClient(HTTPClientProtocol):
    """HTTP client with retry, backoff and circuit breaker."""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._circuit_breaker = SimpleCircuitBreaker()

    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.http_timeout),
                follow_redirects=True,
            )

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _should_retry(self, exception: Exception) -> bool:
        """Determine if request should be retried."""
        return isinstance(exception, (
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.ConnectError,
            httpx.RemoteProtocolError,
        ))

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, CircuitBreakerOpenError)),
        stop=stop_after_attempt(settings.http_max_retries),
        wait=wait_exponential_jitter(
            initial=settings.http_backoff_factor,
            max=60,
            jitter=0.1,
        ),
        reraise=True,
    )
    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with circuit breaker."""
        if not self._circuit_breaker.call_allowed():
            raise CircuitBreakerOpenError("Circuit breaker is open")

        await self._ensure_client()

        try:
            response = await self._client.request(method, url, **kwargs)
            self._circuit_breaker.record_success()
            return response
        except Exception as e:
            self._circuit_breaker.record_failure()
            if self._should_retry(e):
                raise  # Let tenacity handle retry
            raise ExternalServiceError(
                f"HTTP request failed: {e}",
                service=url.split("/")[2] if "/" in url else "unknown",
            )

    async def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make GET request."""
        response = await self._make_request("GET", url, **kwargs)
        return self._handle_response(response)

    async def post(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make POST request."""
        response = await self._make_request("POST", url, **kwargs)
        return self._handle_response(response)

    async def put(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make PUT request."""
        response = await self._make_request("PUT", url, **kwargs)
        return self._handle_response(response)

    async def delete(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make DELETE request."""
        response = await self._make_request("DELETE", url, **kwargs)
        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle HTTP response."""
        try:
            response.raise_for_status()

            # Try to parse JSON
            if response.headers.get("content-type", "").startswith("application/json"):
                return response.json()
            else:
                return {"text": response.text}

        except httpx.HTTPStatusError as e:
            raise ExternalServiceError(
                f"HTTP {e.response.status_code}: {e.response.text}",
                service=response.url.host or "unknown",
                status_code=e.response.status_code,
            )
        except Exception as e:
            raise ExternalServiceError(f"Response parsing failed: {e}")


# Global HTTP client instance
http_client = HTTPClient()
