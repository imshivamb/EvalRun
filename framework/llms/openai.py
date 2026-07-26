"""OpenAI client wrapper implementation."""

from typing import List, Optional
from framework.llms.base import BaseLLM, LLMResponse, Message


class OpenAILLM(BaseLLM):
    """OpenAI API client wrapper."""

    def __init__(
        self,
        model_name: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 60.0,
        max_retries: int = 2,
    ):
        """Initializes the OpenAILLM.

        Validates that the 'openai' library is installed immediately.

        Args:
            model_name: The target model ID.
            api_key: The OpenAI API key. Reads from environment if None.
            base_url: The API base URL to connect to. Defaults to OpenAI API.
            timeout: The request timeout in seconds. Defaults to 60.0.
            max_retries: The maximum number of retries for request failures. Defaults to 2.

        Raises:
            ImportError: If the 'openai' library is not installed.
        """
        try:
            # pyrefly: ignore [missing-import]
            import openai
        except ImportError:
            raise ImportError(
                "The 'openai' library is required to use OpenAILLM. "
                "Please install it using 'pip install openai'."
            )

        self._client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.model_name = model_name
        # GPT-5 family Chat Completions models use the newer
        # `max_completion_tokens` parameter. NVIDIA's OpenAI-compatible NIM
        # endpoint continues to expect `max_tokens`.
        self._token_parameter = (
            "max_completion_tokens"
            if base_url.rstrip("/") == "https://api.openai.com/v1" and model_name.startswith("gpt-5")
            else "max_tokens"
        )

    def generate(self, messages: List[Message]) -> LLMResponse:
        # Compatibility layer: prepend system content to user content
        # since some NIM endpoints (e.g. MiniMax) do not support the system role.
        formatted_messages = []
        system_content = ""
        for msg in messages:
            if msg.role == "system":
                system_content += msg.content + "\n"
            else:
                role = msg.role
                content = msg.content
                if system_content:
                    content = system_content + "\n" + content
                    system_content = ""
                formatted_messages.append({"role": role, "content": content})
        
        if system_content and not formatted_messages:
            formatted_messages.append({"role": "user", "content": system_content})

        request_kwargs = {
            "model": self.model_name,
            "messages": formatted_messages,
            self._token_parameter: 4096,
        }
        response = self._client.chat.completions.create(
            **request_kwargs,
        )

        if not response.choices:
            raise ValueError(f"API returned empty choices. Full response: {response}")

        response_text = response.choices[0].message.content or ""
        return LLMResponse(text=response_text)
