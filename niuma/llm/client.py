"""LLM client for Niuma supporting multiple providers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator

import httpx
from openai import AsyncOpenAI

from niuma.config import get_settings


class MessageRole(Enum):
    """Message roles for chat completions."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A message in the conversation."""

    role: MessageRole
    content: str
    name: str | None = None
    tool_calls: list[dict] | None = None


@dataclass
class LLMResponse:
    """Response from LLM."""

    content: str
    usage: dict[str, int] | None = None
    model: str | None = None
    finish_reason: str | None = None


class LLMClient:
    """Unified LLM client supporting OpenAI and Anthropic."""

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
        retry_count: int | None = None,
    ) -> None:
        """Initialize LLM client with settings."""
        settings = get_settings()
        llm_settings = settings.llm

        self.provider = (provider or llm_settings.provider).lower()
        self.temperature = temperature if temperature is not None else llm_settings.temperature
        self.max_tokens = max_tokens or llm_settings.max_tokens
        self.timeout = timeout or llm_settings.timeout
        self.retry_count = retry_count if retry_count is not None else llm_settings.retry_count

        # Provider-specific setup
        if self.provider == "openai":
            self.api_key = api_key or llm_settings.openai_api_key
            base = base_url or llm_settings.openai_base_url
            self.model = model or llm_settings.openai_model
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=base,
                timeout=httpx.Timeout(self.timeout),
            )

        elif self.provider == "anthropic":
            self.api_key = api_key or llm_settings.anthropic_api_key
            self.base_url = base_url or llm_settings.anthropic_base_url
            self.model = model or llm_settings.anthropic_model
            self._client = None  # Will use httpx directly for Anthropic

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        if not self.api_key:
            raise ValueError(f"API key required for {self.provider}")

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Complete a single prompt."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self.chat(messages, **kwargs)
        return response.content

    async def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send chat messages and get response."""
        for attempt in range(self.retry_count + 1):
            try:
                if self.provider == "openai":
                    return await self._chat_openai(messages, tools, **kwargs)
                elif self.provider == "anthropic":
                    return await self._chat_anthropic(messages, tools, **kwargs)
            except Exception as e:
                if attempt == self.retry_count:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        raise RuntimeError("Unexpected exit from retry loop")

    async def _chat_openai(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send chat request to OpenAI."""
        params: dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
        }

        if self.max_tokens:
            params["max_tokens"] = self.max_tokens

        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        response = await self._client.chat.completions.create(**params)

        return LLMResponse(
            content=response.choices[0].message.content or "",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            } if response.usage else None,
            model=response.model,
            finish_reason=response.choices[0].finish_reason,
        )

    async def _chat_anthropic(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send chat request to Anthropic."""
        # Convert OpenAI format to Anthropic format
        system_message = None
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        # Anthropic uses "assistant" instead of "model" in messages
        for msg in anthropic_messages:
            if msg["role"] == "model":
                msg["role"] = "assistant"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        params: dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": anthropic_messages,
            "max_tokens": self.max_tokens or 4096,
            "temperature": kwargs.get("temperature", self.temperature),
        }

        if system_message:
            params["system"] = system_message

        if tools:
            params["tools"] = tools

        base_url = self.base_url or "https://api.anthropic.com"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{base_url}/v1/messages",
                headers=headers,
                json=params,
            )
            response.raise_for_status()
            data = response.json()

        return LLMResponse(
            content=data["content"][0]["text"] if data["content"] else "",
            usage={
                "prompt_tokens": data["usage"]["input_tokens"],
                "completion_tokens": data["usage"]["output_tokens"],
            },
            model=data["model"],
            finish_reason=data.get("stop_reason"),
        )

    async def stream(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream response tokens."""
        if self.provider != "openai":
            # Fallback for other providers
            response = await self.chat(messages, **kwargs)
            yield response.content
            return

        params: dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "stream": True,
        }

        if self.max_tokens:
            params["max_tokens"] = self.max_tokens

        stream = await self._client.chat.completions.create(**params)
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        """Get embeddings for texts (OpenAI only)."""
        if self.provider != "openai":
            raise NotImplementedError("Embeddings only supported for OpenAI")

        response = await self._client.embeddings.create(
            model=model or "text-embedding-3-small",
            input=texts,
        )

        return [item.embedding for item in response.data]

    async def close(self) -> None:
        """Close client connections."""
        if self._client and hasattr(self._client, "close"):
            await self._client.close()

    @staticmethod
    def create_messages(
        system: str | None = None,
        user: str | None = None,
        history: list[tuple[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        """Helper to create message list."""
        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        if history:
            for user_msg, assistant_msg in history:
                messages.append({"role": "user", "content": user_msg})
                messages.append({"role": "assistant", "content": assistant_msg})

        if user:
            messages.append({"role": "user", "content": user})

        return messages
