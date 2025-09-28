"""Yandex GPT integration."""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.adapters.http_client import http_client
from app.core.config import settings
from app.core.errors import LLMError
from app.core.metrics import metrics


class YandexGPT:
    """Yandex GPT integration."""

    def __init__(self):
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        self.iam_token = None
        self.token_expires = 0

    async def _get_iam_token(self) -> str:
        """Get IAM token for Yandex Cloud authentication."""
        current_time = asyncio.get_event_loop().time()

        # Check if token is still valid (with 5 minute buffer)
        if self.iam_token and current_time < self.token_expires - 300:
            return self.iam_token

        try:
            # Use OAuth token directly
            self.iam_token = settings.yc_oauth_token.get_secret_value()
            self.token_expires = current_time + 3600  # Assume 1 hour validity
            return self.iam_token

        except Exception as e:
            raise LLMError(f"Failed to get IAM token: {e}")

    async def _load_system_prompt(self) -> str:
        """Load system prompt from file."""
        prompt_path = Path(__file__).parent / "prompts" / "system_ai_maga.md"
        try:
            return prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            # Fallback system prompt
            return "You are AI Мага, a helpful assistant. Be concise and practical."

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate text using Yandex GPT.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            system_prompt: Custom system prompt

        Returns:
            Dict with generated text and metadata
        """
        metrics.histogram("llm_request_duration", 0, stage="start")

        try:
            token = await self._get_iam_token()

            # Load system prompt if not provided
            if not system_prompt:
                system_prompt = await self._load_system_prompt()

            # Prepare messages with system prompt
            full_messages = [{"role": "system", "content": system_prompt}]
            full_messages.extend(messages)

            # Prepare request data for Yandex GPT
            # Convert messages to prompt format
            prompt_parts = []
            for msg in full_messages:
                if msg["role"] == "system":
                    prompt_parts.append(f"System: {msg['content']}")
                elif msg["role"] == "user":
                    prompt_parts.append(f"User: {msg['content']}")
                elif msg["role"] == "assistant":
                    prompt_parts.append(f"Assistant: {msg['content']}")

            prompt = "\n\n".join(prompt_parts)

            data = {
                "modelUri": f"gpt://{settings.yc_folder_id}/{model or settings.yandex_gpt_model}",
                "completionOptions": {
                    "stream": False,
                    "temperature": temperature or settings.llm_temperature,
                    "maxTokens": max_tokens or settings.llm_max_tokens,
                },
                "messages": [
                    {
                        "role": "user",
                        "text": prompt
                    }
                ]
            }


            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            # Make request
            response_data = await http_client.post(
                self.base_url,
                json=data,
                headers=headers,
                timeout=settings.llm_timeout,
            )


            # Parse response
            result = self._parse_response(response_data)

            metrics.increment("llm_requests_total", model=model or "yandex-gpt", status="success")
            metrics.histogram("llm_request_duration", 1, stage="complete")

            return result

        except Exception as e:
            metrics.increment("llm_requests_total", model=model or "yandex-gpt", status="error")
            metrics.histogram("llm_request_duration", 1, stage="error")
            raise LLMError(f"GPT generation failed: {e}")

    def _parse_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Yandex GPT API response."""
        try:
            result = response_data.get("result", {})

            if "alternatives" not in result or not result["alternatives"]:
                raise LLMError("No alternatives in GPT response")

            # Get first alternative
            alternative = result["alternatives"][0]
            text = alternative.get("message", {}).get("text", "")

            # Extract usage info if available
            usage = result.get("usage", {})

            return {
                "text": text,
                "usage": {
                    "input_tokens": usage.get("inputTextTokens", 0),
                    "output_tokens": usage.get("completionTokens", 0),
                    "total_tokens": usage.get("totalTokens", 0),
                },
                "model": result.get("model", ""),
                "finished": True,
            }

        except (KeyError, TypeError) as e:
            raise LLMError(f"Invalid GPT response format: {e}")

    async def chat(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """
        Simple chat interface.

        Args:
            user_message: User's message
            conversation_history: Previous messages
            **kwargs: Additional parameters for generate()

        Returns:
            AI response text
        """
        messages = conversation_history or []
        messages.append({"role": "user", "content": user_message})

        result = await self.generate(messages, **kwargs)
        return result["text"]

    async def classify_intent(
        self,
        text: str,
        intents: List[str],
    ) -> Dict[str, Any]:
        """
        Classify user intent from text.

        Args:
            text: Input text
            intents: List of possible intents

        Returns:
            Dict with detected intent and confidence
        """
        intents_str = ", ".join(intents)

        prompt = f"""
        Определи намерение пользователя из текста. Возможные намерения: {intents_str}

        Текст: {text}

        Верни JSON с полями:
        - intent: выбранное намерение
        - confidence: уверенность от 0 до 1
        - explanation: краткое объяснение
        """

        messages = [{"role": "user", "content": prompt}]

        result = await self.generate(
            messages,
            temperature=0.1,  # Low temperature for classification
            max_tokens=200,
        )

        try:
            # Try to parse JSON from response
            response_text = result["text"].strip()
            # Find JSON in response (might have extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                parsed = json.loads(json_str)
                return parsed
            else:
                # Fallback if no JSON found
                return {
                    "intent": "unknown",
                    "confidence": 0.0,
                    "explanation": "Could not parse response"
                }
        except (json.JSONDecodeError, KeyError):
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "explanation": "Invalid response format"
            }


class MockGPT:
    """Mock GPT for testing and development."""

    async def generate(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Mock text generation."""
        await asyncio.sleep(0.1)  # Simulate API delay

        # Simple mock responses based on input
        last_message = messages[-1]["content"] if messages else ""

        if "привет" in last_message.lower() or "hello" in last_message.lower():
            response = "Привет! Я AI Мага. Чем могу помочь?"
        elif "погода" in last_message.lower():
            response = "Извини, я не умею проверять погоду. Попробуй спросить о чем-то другом."
        elif "ваканси" in last_message.lower():
            response = "Я могу помочь найти вакансии на HH.ru. Какую должность ищешь?"
        else:
            response = "Понял. Это интересный вопрос. Дай мне подумать..."

        return {
            "text": response,
            "usage": {
                "input_tokens": len(last_message.split()),
                "output_tokens": len(response.split()),
                "total_tokens": len(last_message.split()) + len(response.split()),
            },
            "model": "mock-gpt",
            "finished": True,
        }

    async def chat(self, user_message: str, **kwargs) -> str:
        """Mock chat."""
        result = await self.generate([{"role": "user", "content": user_message}])
        return result["text"]

    async def classify_intent(self, text: str, intents: List[str]) -> Dict[str, Any]:
        """Mock intent classification."""
        # Simple keyword matching
        text_lower = text.lower()

        if any(word in text_lower for word in ["найди", "поиск", "ваканси"]):
            intent = "search_jobs"
        elif any(word in text_lower for word in ["напомни", "напоминание"]):
            intent = "create_reminder"
        elif any(word in text_lower for word in ["переведи", "translate"]):
            intent = "translate"
        elif any(word in text_lower for word in ["прочитай", "read"]):
            intent = "read_text"
        else:
            intent = intents[0] if intents else "unknown"

        return {
            "intent": intent,
            "confidence": 0.8,
            "explanation": "Keyword matching"
        }


# Choose GPT implementation
if settings.is_prod or settings.yc_oauth_token:
    yandex_gpt = YandexGPT()
else:
    print("Using mock GPT (no Yandex credentials)")
    yandex_gpt = MockGPT()
