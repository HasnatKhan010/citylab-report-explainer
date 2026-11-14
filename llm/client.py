"""Provider fallback client with timeouts, retries, retry-after, cache, and breakers."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Provider:
    name: str
    key: str
    model: str
    endpoint: str


class CircuitBreaker:
    def __init__(self, threshold: int = 2, cooldown_seconds: float = 60.0):
        self.threshold = threshold
        self.cooldown_seconds = cooldown_seconds
        self.failures = 0
        self.opened_at: float | None = None

    def available(self) -> bool:
        if self.opened_at is None:
            return True
        if time.monotonic() - self.opened_at >= self.cooldown_seconds:
            self.opened_at = None
            self.failures = 0
            return True
        return False

    def success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = time.monotonic()


class LLMClient:
    def __init__(self, timeout_seconds: float = 12.0, attempts: int = 2):
        self.timeout_seconds = timeout_seconds
        self.attempts = attempts
        self.cache: dict[str, str] = {}
        self.breakers: dict[str, CircuitBreaker] = {}

    @staticmethod
    def _providers() -> list[Provider]:
        providers = [
            Provider("gemini", os.getenv("GEMINI_API_KEY", "").strip(), os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(), ""),
            Provider("groq", os.getenv("GROQ_API_KEY", "").strip(), os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip(), "https://api.groq.com/openai/v1/chat/completions"),
            Provider("openrouter", os.getenv("OPENROUTER_API_KEY", "").strip(), os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free").strip(), "https://openrouter.ai/api/v1/chat/completions"),
        ]
        return [provider for provider in providers if provider.key and provider.model]

    async def complete(self, system_prompt: str, user_prompt: str, use_cache: bool = True) -> tuple[str, str] | None:
        key = hashlib.sha256((system_prompt + "\0" + user_prompt).encode("utf-8")).hexdigest()
        if use_cache and key in self.cache:
            return self.cache[key], "cache"
        for provider in self._providers():
            breaker = self.breakers.setdefault(provider.name, CircuitBreaker())
            if not breaker.available():
                continue
            for attempt in range(self.attempts):
                try:
                    response = await self._request(provider, system_prompt, user_prompt)
                    breaker.success()
                    if use_cache:
                        self.cache[key] = response
                    return response, provider.name
                except Exception as exc:
                    breaker.failure()
                    retry_after = self._retry_after(exc)
                    logger.warning("LLM provider %s failed (attempt %d): %s", provider.name, attempt + 1, type(exc).__name__)
                    if attempt + 1 < self.attempts:
                        delay = retry_after if retry_after is not None else min(8.0, 0.25 * (2 ** attempt) + random.random() * 0.2)
                        await asyncio.sleep(delay)
                        continue
                    break
        return None

    def _retry_after(self, exc: Exception) -> float | None:
        if not isinstance(exc, httpx.HTTPStatusError) or exc.response.status_code != 429:
            return None
        raw = exc.response.headers.get("Retry-After")
        if not raw:
            return None
        try:
            return min(15.0, max(0.0, float(raw)))
        except ValueError:
            try:
                when = parsedate_to_datetime(raw)
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
                return min(15.0, max(0.0, (when - datetime.now(timezone.utc)).total_seconds()))
            except (TypeError, ValueError):
                return None

    async def _request(self, provider: Provider, system_prompt: str, user_prompt: str) -> str:
        headers = {"Content-Type": "application/json"}
        if provider.name == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{provider.model}:generateContent"
            headers["x-goog-api-key"] = provider.key
            payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
            }
        else:
            url = provider.endpoint
            headers["Authorization"] = f"Bearer {provider.key}"
            payload = {
                "model": provider.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        if provider.name == "gemini":
            return data["candidates"][0]["content"]["parts"][0]["text"]
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            return "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return str(content)

