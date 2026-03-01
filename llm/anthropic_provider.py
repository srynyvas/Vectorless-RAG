"""Anthropic (Claude) LLM provider implementation."""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

import anthropic

from config.settings import settings
from llm.base import LLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """LLM provider backed by the Anthropic Messages API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or settings.ANTHROPIC_API_KEY
        if not self._api_key:
            raise ValueError(
                "Anthropic API key is not set. "
                "Provide it via the ANTHROPIC_API_KEY environment variable or .env file."
            )
        self._default_model = model or settings.ANTHROPIC_MODEL
        self._client = anthropic.Anthropic(api_key=self._api_key)

    # ── Core generation ──────────────────────────────────────────────

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        model = model or self._default_model
        logger.debug(
            "Anthropic request  model=%s  temperature=%s  max_tokens=%s",
            model,
            temperature,
            max_tokens,
        )

        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        text = response.content[0].text
        logger.debug(
            "Anthropic response  input_tokens=%s  output_tokens=%s",
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return text

    # ── Multimodal generation ─────────────────────────────────────────

    def generate_multimodal(
        self,
        system_prompt: str,
        content_blocks: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        """Send a multimodal prompt (text + images) via the Anthropic API.

        Converts the unified ``content_blocks`` format into the Anthropic
        Messages API image/text structure and returns the model's text
        response.

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
        model = model or self._default_model
        logger.debug(
            "Anthropic multimodal request  model=%s  temperature=%s  max_tokens=%s  blocks=%d",
            model,
            temperature,
            max_tokens,
            len(content_blocks),
        )

        # Convert content_blocks to Anthropic format
        anthropic_content = []
        for block in content_blocks:
            if block["type"] == "text":
                anthropic_content.append({"type": "text", "text": block["text"]})
            elif block["type"] == "image":
                anthropic_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": block["media_type"],
                        "data": block["data"],
                    },
                })

        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": anthropic_content}],
        )

        text = response.content[0].text
        logger.debug(
            "Anthropic multimodal response  input_tokens=%s  output_tokens=%s",
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return text

    # ── JSON generation ──────────────────────────────────────────────

    def generate_json(
        self,
        system_prompt: str,
        user_message: str,
        **kwargs,
    ) -> dict:
        """Generate a response and parse it as JSON.

        The system prompt is augmented with an instruction to respond with
        valid JSON only.  Markdown code fences (```json ... ```) are stripped
        before parsing.
        """
        json_system_prompt = (
            f"{system_prompt}\n\n"
            "IMPORTANT: Respond with valid JSON only. "
            "Do not include any text outside the JSON object."
        )

        raw = self.generate(json_system_prompt, user_message, **kwargs)
        return self._parse_json(raw)

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Parse JSON from a model response, stripping code fences if present."""
        cleaned = text.strip()

        # Strip markdown code fences: ```json ... ``` or ``` ... ```
        fence_pattern = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", re.DOTALL)
        match = fence_pattern.match(cleaned)
        if match:
            cleaned = match.group(1).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse JSON from Anthropic response:\n%s", cleaned)
            raise ValueError(
                f"Anthropic response is not valid JSON: {exc}"
            ) from exc
