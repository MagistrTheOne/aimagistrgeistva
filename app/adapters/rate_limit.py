"""Rate limiting adapter."""

import asyncio
import time
from typing import Dict, Optional, Tuple

from app.adapters.redis_client import redis_adapter
from app.core.errors import RateLimitError
from app.domain.models import CommandType
from app.domain.policies import RateLimitPolicy


class RateLimiter:
    """Rate limiter using Redis."""

    def __init__(self):
        self._local_cache: Dict[str, Tuple[int, float]] = {}
        self._cache_ttl = 60  # seconds

    def _get_key(self, user_id: str, action: str) -> str:
        """Generate Redis key for rate limiting."""
        return f"ratelimit:{user_id}:{action}"

    async def _get_current_count(self, key: str, window_seconds: int) -> Tuple[int, float]:
        """Get current count and reset time from Redis."""
        current_time = time.time()
        window_start = current_time - window_seconds

        # Use Redis sorted set to track requests
        # Remove old entries
        await redis_adapter._client.zremrangebyscore(key, 0, window_start)

        # Count current requests in window
        count = await redis_adapter._client.zcount(key, window_start, current_time)

        # Get reset time (next window)
        reset_time = current_time + window_seconds

        return count, reset_time

    async def check_rate_limit(
        self,
        user_id: str,
        action: str,
        max_requests: int,
        window_seconds: int,
    ) -> Tuple[bool, float]:
        """
        Check if request is within rate limit.

        Returns:
            Tuple of (allowed: bool, reset_time: float)
        """
        key = self._get_key(user_id, action)

        try:
            count, reset_time = await self._get_current_count(key, window_seconds)

            if count >= max_requests:
                return False, reset_time

            # Add current request
            current_time = time.time()
            await redis_adapter._client.zadd(key, {str(current_time): current_time})

            # Set expiration on the key
            await redis_adapter._client.expire(key, window_seconds * 2)

            return True, reset_time

        except Exception:
            # If Redis is down, allow request but log error
            # In production, you might want stricter behavior
            return True, time.time() + window_seconds

    async def check_command_rate_limit(
        self,
        user_id: str,
        command_type: CommandType,
    ) -> Tuple[bool, float]:
        """Check rate limit for command type."""
        action = f"command:{command_type.value}"
        limits = RateLimitPolicy.get_limit_for_command(command_type)

        return await self.check_rate_limit(
            user_id=str(user_id),
            action=action,
            max_requests=limits["requests"],
            window_seconds=limits["window_seconds"],
        )

    async def get_remaining_requests(
        self,
        user_id: str,
        action: str,
        max_requests: int,
        window_seconds: int,
    ) -> int:
        """Get remaining requests for user action."""
        key = self._get_key(user_id, action)

        try:
            count, _ = await self._get_current_count(key, window_seconds)
            return max(0, max_requests - count)
        except Exception:
            return max_requests


class InMemoryRateLimiter:
    """In-memory rate limiter for fallback when Redis is unavailable."""

    def __init__(self):
        self._requests: Dict[str, list] = {}
        self._lock = asyncio.Lock()

    def _cleanup_old_requests(self, key: str, window_seconds: int):
        """Clean up old requests."""
        if key in self._requests:
            current_time = time.time()
            window_start = current_time - window_seconds
            self._requests[key] = [
                req_time for req_time in self._requests[key]
                if req_time > window_start
            ]

    async def check_rate_limit(
        self,
        user_id: str,
        action: str,
        max_requests: int,
        window_seconds: int,
    ) -> Tuple[bool, float]:
        """Check rate limit in memory."""
        async with self._lock:
            key = f"{user_id}:{action}"
            self._cleanup_old_requests(key, window_seconds)

            current_time = time.time()
            request_times = self._requests.get(key, [])

            if len(request_times) >= max_requests:
                # Calculate reset time
                oldest_request = min(request_times)
                reset_time = oldest_request + window_seconds
                return False, reset_time

            # Add current request
            request_times.append(current_time)
            self._requests[key] = request_times

            reset_time = current_time + window_seconds
            return True, reset_time


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(user_id: str, command_type: CommandType) -> None:
    """Check rate limit and raise error if exceeded."""
    allowed, reset_time = await rate_limiter.check_command_rate_limit(user_id, command_type)

    if not allowed:
        raise RateLimitError(
            f"Rate limit exceeded for {command_type.value}. Try again after {reset_time - time.time():.0f} seconds."
        )
