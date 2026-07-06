"""Abstract base class for session memory."""

from abc import ABC, abstractmethod


class BaseSessionMemory(ABC):
    """Abstract base class defining the interface for agent session memory."""

    @abstractmethod
    def to_yaml(self) -> str:
        """Serializes memory state to structured YAML string for LLM injection."""
        pass

    @abstractmethod
    def to_json(self) -> str:
        """Serializes memory state to JSON string representation."""
        pass
