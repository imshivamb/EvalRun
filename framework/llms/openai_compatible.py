import os
import time
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
        max_retries: int = 3,
        retry_delay: float = 1.0,
        extra_headers: Optional[Dict[str, str]] = None,
        provider: str = "openai_compatible",
        temperature: Optional[float] = 0.0,
        seed: Optional[int] = None,
    ):
        """Initializes the OpenAICompatibleLLM client.

        Args:
            model_name: Model identifier (e.g. 'gpt-5.6-terra', 'qwen2.5-72b-instruct', 'llama-3.3-70b').
            api_key: API key. Defaults to OPENAI_API_KEY environment variable or 'EMPTY' for local endpoints.
            base_url: Base endpoint URL (e.g. 'http://localhost:8000/v1', 'https://integrate.api.nvidia.com/v1').
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts on transient errors.
            retry_delay: Base delay between retries in seconds.
            extra_headers: Optional custom HTTP headers.
            provider: Human-readable provider label.
        """
        self.model_name = model_name
        self.provider = provider
        self.base_url = base_url or "https://api.openai.com/v1"
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.extra_headers = extra_headers
        self.temperature = temperature
        self.seed = seed

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

    def _is_transient_error(self, e: Exception) -> bool:
        """Determines whether an exception is a transient network/server error suitable for retries."""
        if isinstance(e, (TimeoutError, ConnectionError)):
            return True
        status_code = getattr(e, "status_code", None)
        if status_code is not None:
            if status_code in (429, 500, 502, 503, 504):
                return True
            if 400 <= status_code < 500 and status_code != 429:
                return False
        err_str = str(e).lower()
        if any(k in err_str for k in ("timeout", "connection", "rate limit", "500", "502", "503", "504", "deadline exceeded")):
            return True
        return False

    def generate(self, messages: List[Message]) -> LLMResponse:
        """Generates a text response from chat messages with retry logic.

        Args:
            messages: List of Message instances.

        Returns:
            An LLMResponse containing the text output and execution metadata.
        """
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        response = None
        last_exception = None
        retries_this_call = 0

        for attempt in range(1 + self.max_retries):
            try:
                request_kwargs = {
                    "model": self.model_name,
                    "messages": formatted_messages,
                }
                if self.temperature is not None:
                    request_kwargs["temperature"] = self.temperature
                if self.seed is not None:
                    request_kwargs["seed"] = self.seed
                response = self.client.chat.completions.create(
                    **request_kwargs,
                )
                break
            except Exception as e:
                last_exception = e
                self.last_error = str(e)
                if attempt < self.max_retries and self._is_transient_error(e):
                    retries_this_call += 1
                    self.retries_attempted += 1
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise last_exception

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
                    "retries_attempted": retries_this_call,
                },
            )

        content = response.choices[0].message.content or ""
        return LLMResponse(
            text=content,
            metadata={
                "provider": self.provider,
                "model_name": self.model_name,
                "token_usage": self.last_token_usage,
                "retries_attempted": retries_this_call,
            },
        )
