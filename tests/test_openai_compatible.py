"""Unit tests for OpenAICompatibleLLM adapter supporting hosted and local endpoints."""

import unittest
from unittest.mock import MagicMock, patch

from framework.llms.openai_compatible import OpenAICompatibleLLM
from framework.llms.base import Message, LLMResponse


class TestOpenAICompatibleLLM(unittest.TestCase):

    @patch("framework.llms.openai_compatible.OpenAI")
    def test_local_endpoint_initialization_and_generation(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = "Response from local Qwen model."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 45
        mock_response.usage.completion_tokens = 110
        mock_response.usage.total_tokens = 155
        mock_client.chat.completions.create.return_value = mock_response

        # Test local vLLM / LM Studio / Ollama endpoint initialization
        llm = OpenAICompatibleLLM(
            model_name="qwen2.5-72b-instruct",
            base_url="http://localhost:8000/v1",
            api_key="EMPTY",
            provider="vllm",
        )

        self.assertEqual(llm.model_name, "qwen2.5-72b-instruct")
        self.assertEqual(llm.base_url, "http://localhost:8000/v1")
        self.assertEqual(llm.provider, "vllm")

        messages = [Message(role="user", content="Test prompt")]
        resp = llm.generate(messages)

        self.assertIsInstance(resp, LLMResponse)
        self.assertEqual(resp.text, "Response from local Qwen model.")
        self.assertEqual(llm.request_count, 1)
        self.assertEqual(llm.last_token_usage["total_tokens"], 155)

        mock_client.chat.completions.create.assert_called_once_with(
            model="qwen2.5-72b-instruct",
            messages=[{"role": "user", "content": "Test prompt"}],
        )

    @patch("framework.llms.openai_compatible.OpenAI")
    def test_hosted_endpoint_generation(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = "Response from hosted NVIDIA NIM."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = None  # Local or non-standard provider with no usage object
        mock_client.chat.completions.create.return_value = mock_response

        llm = OpenAICompatibleLLM(
            model_name="meta/llama-3.3-70b-instruct",
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="nvapi-test-key",
            provider="nvidia_nim",
        )

        resp = llm.generate([Message(role="user", content="Hello")])
        self.assertEqual(resp.text, "Response from hosted NVIDIA NIM.")
        self.assertIsNone(llm.last_token_usage)

    @patch("framework.llms.openai_compatible.OpenAI")
    def test_empty_choices_response_handling(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = []  # Empty choices list
        mock_client.chat.completions.create.return_value = mock_response

        llm = OpenAICompatibleLLM(model_name="test-model")
        resp = llm.generate([Message(role="user", content="Hello")])

        self.assertEqual(resp.text, "")
        self.assertIn("Empty choices array", resp.metadata.get("error", ""))

    @patch("framework.llms.openai_compatible.OpenAI")
    def test_last_error_captured_on_exception(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = RuntimeError("API connection failure")

        llm = OpenAICompatibleLLM(model_name="test-model")
        with self.assertRaises(RuntimeError):
            llm.generate([Message(role="user", content="Hello")])

        self.assertEqual(llm.last_error, "API connection failure")


if __name__ == "__main__":
    unittest.main()
