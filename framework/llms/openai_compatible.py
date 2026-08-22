"""Provider-agnostic OpenAI-compatible LLM client adapter for hosted and local models."""

import os
from typing import Any, Dict, List, Optional
from openai import OpenAI

from framework.llms.base import BaseLLM, LLMResponse, Message


class OpenAICompatibleLLM(BaseLLM):
    """Universal OpenAI-compatible completion client adapter.

    Supports cloud hosted APIs (OpenAI, NVIDIA NIM, Gemini OpenAI-compat) and
    local user-hosted servers (vLLM, LM Studio, Ollama) via a single base_url.
    """

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 180.0,
        extra_headers: Optional[Dict[str, str]] = None,
        provider: str = "openai_compatible",
    ):
        """Initializes the OpenAICompatibleLLM client.

        Args:
            model_name: Model identifier (e.g. 'gpt-4o', 'qwen2.5-72b-instruct', 'llama-3.3-70b').
            api_key: API key. Defaults to OPENAI_API_KEY environment variable or 'EMPTY' for local endpoints.
            base_url: Base endpoint URL (e.g. 'http://localhost:8000/v1', 'https://integrate.api.nvidia.com/v1').
            timeout: Request timeout in seconds.
            extra_headers: Optional custom HTTP headers.
            provider: Human-readable provider label.
        """
        self.model_name = model_name
        self.provider = provider
        self.base_url = base_url or "https://api.openai.com/v1"
        self.timeout = timeout
        self.extra_headers = extra_headers

        resolved_api_key = api_key or os.environ.get("OPENAI_API_KEY") or "EMPTY"
        self.client = OpenAI(
            api_key=resolved_api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            default_headers=self.extra_headers,
        )

        self.request_count: int = 0
        self.retries_attempted: int = 0
        self.last_error: Optional[str] = None
        self.last_token_usage: Optional[Dict[str, int]] = None

    def generate(self, messages: List[Message]) -> LLMResponse:
        """Generates a text response from chat messages.

        Args:
            messages: List of Message instances.

        Returns:
            An LLMResponse containing the text output and execution metadata.
        """
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=formatted_messages,
            )
        except Exception as e:
            self.last_error = str(e)
            raise

        self.request_count += 1
        self.last_error = None

        if hasattr(response, "usage") and response.usage:
            self.last_token_usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }
        else:
            self.last_token_usage = None

        if not getattr(response, "choices", None):
            return LLMResponse(
                text="",
                metadata={
                    "error": "Empty choices array in model response",
                    "provider": self.provider,
                    "model_name": self.model_name,
                },
            )

        content = response.choices[0].message.content or ""
        return LLMResponse(
            text=content,
            metadata={
                "provider": self.provider,
                "model_name": self.model_name,
                "token_usage": self.last_token_usage,
            },
        )
