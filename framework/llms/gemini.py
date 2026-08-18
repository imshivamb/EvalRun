"""Google Gemini client wrapper implementation."""

from typing import List, Optional
from framework.llms.base import BaseLLM, LLMResponse, Message


class GeminiLLM(BaseLLM):
    """Google Gemini API client wrapper."""

    def __init__(
        self, model_name: str = "gemini-1.5-pro", api_key: Optional[str] = None
    ):
        """Initializes the GeminiLLM.

        Validates that the 'google-generativeai' library is installed immediately.

        Args:
            model_name: The target model name.
            api_key: The Gemini API key. If not provided, configuration is skipped.

        Raises:
            ImportError: If the 'google-generativeai' library is not installed.
        """
        try:
            # pyrefly: ignore [missing-import]
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "The 'google-generativeai' library is required to use GeminiLLM. "
                "Please install it using 'pip install google-generativeai'."
            )

        if api_key:
            genai.configure(api_key=api_key)

        self._genai = genai
        # Ensure name is prefixed correctly (e.g. models/gemini-1.5-pro)
        if model_name and not model_name.startswith("models/"):
            self.model_name = f"models/{model_name}"
        else:
            self.model_name = model_name

    def generate(self, messages: List[Message]) -> LLMResponse:
        system_instruction = None
        gemini_contents = []

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            else:
                # Map standard roles: user -> user, assistant/model -> model
                role = "user" if msg.role == "user" else "model"
                gemini_contents.append(
                    {"role": role, "parts": [{"text": msg.content}]}
                )

        config = {}
        if system_instruction:
            config["system_instruction"] = system_instruction

        import time

        model = self._genai.GenerativeModel(self.model_name, **config)
        
        max_retries = 4
        for attempt in range(max_retries):
            try:
                response = model.generate_content(
                    gemini_contents,
                    request_options={"timeout": 300.0},
                )
                response_text = response.text or ""
                return LLMResponse(text=response_text)
            except Exception as e:
                err_str = str(e).lower()
                is_transient = any(
                    err in err_str
                    for err in ["504", "deadline", "timeout", "resourceexhausted", "429", "503", "unavailable"]
                )
                if is_transient and attempt < max_retries - 1:
                    sleep_seconds = 5 * (attempt + 1)
                    print(f"[GeminiLLM] Transient error ({e}). Retrying in {sleep_seconds}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(sleep_seconds)
                else:
                    raise e
