"""Helper utilities."""

import asyncio
import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

import pytz


def now_utc() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def parse_datetime(date_str: str) -> datetime:
    """Parse ISO datetime string."""
    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))


def format_datetime(dt: datetime) -> str:
    """Format datetime to ISO string."""
    return dt.isoformat()


def generate_id() -> str:
    """Generate a unique ID."""
    return str(UUID())


def hash_string(text: str) -> str:
    """Generate SHA256 hash of a string."""
    return hashlib.sha256(text.encode()).hexdigest()


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    return text


def truncate_text(text: str, max_length: int = 1000) -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    return url_pattern.findall(text)


def is_valid_email(email: str) -> bool:
    """Validate email address."""
    pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return bool(pattern.match(email))


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate simple text similarity (Jaccard similarity)."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    if not union:
        return 0.0

    return len(intersection) / len(union)


async def timeout_after(seconds: float):
    """Create a timeout context manager."""
    async def timeout():
        await asyncio.sleep(seconds)
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    return asyncio.create_task(timeout())


def get_timezone(tz_name: str = "Europe/Moscow") -> pytz.timezone:
    """Get timezone object."""
    return pytz.timezone(tz_name)


def convert_to_timezone(dt: datetime, tz_name: str) -> datetime:
    """Convert datetime to specific timezone."""
    tz = get_timezone(tz_name)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)


def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get value from dictionary."""
    try:
        return data[key]
    except (KeyError, TypeError):
        return default


def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result
