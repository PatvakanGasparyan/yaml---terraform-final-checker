"""
OpenAI-compatible async client with retries, timeouts, and streaming.

Centralizes all LLM HTTP calls; API keys load from settings / .env only.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class OpenAIClientError(Exception):
    """Raised when the AI provider returns an unrecoverable error."""


class OpenAIClient:
    """
    Production-grade wrapper around the OpenAI Python SDK.

    Features: configurable model/temperature/max_tokens, retries, timeout, streaming.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.provider = self.settings.AI_PROVIDER
        self.model = self._resolve_model()
        self.client = self._build_client()
        self.max_retries = self.settings.AI_MAX_RETRIES
        self.timeout = self.settings.AI_TIMEOUT_SECONDS

    def _resolve_model(self) -> str:
        if self.provider == "azure":
            return self.settings.AZURE_OPENAI_DEPLOYMENT
        if self.provider in ("ollama", "local"):
            return self.settings.OLLAMA_MODEL
        return self.settings.OPENAI_MODEL

    def _build_client(self) -> AsyncOpenAI | None:
        if self.provider == "openai" and self.settings.OPENAI_API_KEY:
            return AsyncOpenAI(
                api_key=self.settings.OPENAI_API_KEY,
                base_url=self.settings.OPENAI_BASE_URL,
                timeout=self.settings.AI_TIMEOUT_SECONDS,
                max_retries=0,
            )
        if self.provider == "azure" and self.settings.AZURE_OPENAI_API_KEY:
            endpoint = self.settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
            deployment = self.settings.AZURE_OPENAI_DEPLOYMENT
            return AsyncOpenAI(
                api_key=self.settings.AZURE_OPENAI_API_KEY,
                base_url=f"{endpoint}/openai/deployments/{deployment}",
                default_headers={"api-key": self.settings.AZURE_OPENAI_API_KEY},
                timeout=self.settings.AI_TIMEOUT_SECONDS,
                max_retries=0,
            )
        if self.provider in ("ollama", "local"):
            return AsyncOpenAI(
                api_key="ollama",
                base_url=f"{self.settings.OLLAMA_BASE_URL.rstrip('/')}/v1",
                timeout=self.settings.AI_TIMEOUT_SECONDS,
                max_retries=0,
            )
        return None

    @property
    def is_available(self) -> bool:
        return self.client is not None

    @retry(
        retry=retry_if_exception_type((TimeoutError, asyncio.TimeoutError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> dict[str, Any]:
        """
        Execute a chat completion with retries and structured error handling.

        Returns dict with keys: content, model, tokens_used.
        """
        if not self.client:
            raise OpenAIClientError("AI provider not configured (missing API key)")

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.settings.AI_TEMPERATURE,
            "max_tokens": max_tokens if max_tokens is not None else self.settings.AI_MAX_TOKENS,
            "top_p": self.settings.AI_TOP_P,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        logger.info(
            "AI request provider=%s model=%s messages=%d",
            self.provider,
            self.model,
            len(messages),
        )

        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(**kwargs),
                timeout=self.timeout,
            )
        except Exception as exc:
            logger.error("AI request failed: %s", exc)
            raise OpenAIClientError(str(exc)) from exc

        content = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0
        logger.info("AI response tokens=%d model=%s", tokens, self.model)

        return {
            "content": content,
            "model": self.model,
            "tokens_used": tokens,
        }

    async def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens (SSE-style chunks as plain text)."""
        if not self.client:
            raise OpenAIClientError("AI provider not configured")

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.settings.AI_TEMPERATURE,
            max_tokens=self.settings.AI_MAX_TOKENS,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def analyze_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Chat completion expecting JSON object response."""
        result = await self.chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            json_mode=True,
        )
        try:
            return json.loads(result["content"] or "{}")
        except json.JSONDecodeError:
            logger.warning("AI returned non-JSON; wrapping raw content")
            return {"raw_content": result["content"], "parse_error": True}
