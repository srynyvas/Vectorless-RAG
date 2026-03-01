"""Factory for constructing the configured LLM provider."""

from __future__ import annotations

from typing import Optional

from config.settings import settings
from llm.base import LLMProvider


def get_llm_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """Return an LLM provider instance based on the given name or settings.

    Args:
        provider_name: ``"anthropic"`` or ``"openai"``.  When *None*, the
                       value of ``settings.LLM_PROVIDER`` is used.

    Returns:
        A ready-to-use :class:`LLMProvider` instance.

    Raises:
        ValueError: If the provider name is not recognized.
    """
    name = (provider_name or settings.LLM_PROVIDER).strip().lower()

    if name == "anthropic":
        from llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider()

    if name == "openai":
        from llm.openai_provider import OpenAIProvider
        return OpenAIProvider()

    raise ValueError(
        f"Unknown LLM provider: {name!r}. "
        f"Supported providers are 'anthropic' and 'openai'."
    )
