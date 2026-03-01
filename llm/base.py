from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """Abstract interface that every LLM backend must implement.

    Concrete subclasses wrap vendor-specific SDKs (Anthropic, OpenAI, etc.)
    while exposing a uniform API to the rest of the application.
    """

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_message: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        """Send a prompt to the LLM and return the raw text response.

        Args:
            system_prompt: The system-level instruction.
            user_message:  The user-level message / query.
            model:         Override the default model for this call.
            temperature:   Sampling temperature.
            max_tokens:    Maximum tokens in the response.

        Returns:
            The model's text response.
        """
        ...

    @abstractmethod
    def generate_json(
        self,
        system_prompt: str,
        user_message: str,
        **kwargs,
    ) -> dict:
        """Same as ``generate`` but parse the response as JSON.

        Implementations should handle common quirks such as markdown code
        fences wrapping the JSON payload.

        Args:
            system_prompt: The system-level instruction.
            user_message:  The user-level message / query.
            **kwargs:      Forwarded to ``generate`` (model, temperature, etc.).

        Returns:
            A Python dictionary parsed from the model's JSON response.

        Raises:
            ValueError: If the response cannot be parsed as valid JSON.
        """
        ...

    @abstractmethod
    def generate_multimodal(
        self,
        system_prompt: str,
        content_blocks: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        """Send a multimodal prompt (text + images) to the LLM.

        Args:
            system_prompt:  The system-level instruction.
            content_blocks: List of content dicts, each either:
                - ``{"type": "text", "text": "..."}`` for text
                - ``{"type": "image", "data": base64_str, "media_type": str}``
                  for images
            model:          Override the default model for this call.
            temperature:    Sampling temperature.
            max_tokens:     Maximum tokens in the response.

        Returns:
            The model's text response.
        """
        ...
