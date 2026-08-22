"""Base interfaces and data classes for LLM clients."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Message:
    """Represents a chat message sent to/from an LLM."""

    role: str
    content: str


@dataclass
class LLMResponse:
    """Represents a structured response from an LLM."""

    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseLLM(ABC):
    """Abstract base class representing an LLM client wrapper."""

    @abstractmethod
    def generate(self, messages: List[Message]) -> LLMResponse:
        """Generates a structured completion for the given list of chat messages.

        Args:
            messages: A list of Message dataclasses.

        Returns:
            An LLMResponse containing the text outcome.
        """
        pass
