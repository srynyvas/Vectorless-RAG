"""OpenAI (GPT) LLM provider implementation."""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

import openai

from config.settings import settings
from llm.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """LLM provider backed by the OpenAI Chat Completions API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or settings.OPENAI_API_KEY
        if not self._api_key:
            raise ValueError(
                "OpenAI API key is not set. "
                "Provide it via the OPENAI_API_KEY environment variable or .env file."
            )
        self._default_model = model or settings.OPENAI_MODEL
        self._client = openai.OpenAI(api_key=self._api_key)

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
            "OpenAI request  model=%s  temperature=%s  max_tokens=%s",
            model,
            temperature,
            max_tokens,
        )

        response = self._client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        text = response.choices[0].message.content
        logger.debug(
            "OpenAI response  prompt_tokens=%s  completion_tokens=%s",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
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
        """Send a multimodal prompt (text + images) via the OpenAI API.

        Converts the unified ``content_blocks`` format into OpenAI's
        ``image_url`` / ``text`` content-part structure.  If the chosen model
        does not support vision, the method falls back to a text-only request
        using only the text blocks.

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
            "OpenAI multimodal request  model=%s  temperature=%s  max_tokens=%s  blocks=%d",
            model,
            temperature,
            max_tokens,
            len(content_blocks),
        )

        # Convert content_blocks to OpenAI format
        openai_content = []
        for block in content_blocks:
            if block["type"] == "text":
                openai_content.append({"type": "text", "text": block["text"]})
            elif block["type"] == "image":
                data_url = f"data:{block['media_type']};base64,{block['data']}"
                openai_content.append({
                    "type": "image_url",
                    "image_url": {"url": data_url, "detail": "high"},
                })

        try:
            response = self._client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": openai_content},
                ],
            )
            text = response.choices[0].message.content
            logger.debug(
                "OpenAI multimodal response  prompt_tokens=%s  completion_tokens=%s",
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
            )
            return text
        except openai.BadRequestError:
            # Model may not support vision; fall back to text-only content.
            logger.warning(
                "Model %s does not support vision; "
                "falling back to text-only multimodal request.",
                model,
            )
            text_only = " ".join(
                block["text"] for block in content_blocks if block["type"] == "text"
            )
            return self.generate(
                system_prompt,
                text_only,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

    # ── JSON generation ──────────────────────────────────────────────

    def generate_json(
        self,
        system_prompt: str,
        user_message: str,
        **kwargs,
    ) -> dict:
        """Generate a response constrained to JSON output.

        Uses the OpenAI ``response_format`` parameter to guarantee valid JSON.
        Falls back to manual parsing if ``response_format`` is not supported
        by the model.
        """
        model = kwargs.pop("model", None) or self._default_model
        temperature = kwargs.pop("temperature", 0.1)
        max_tokens = kwargs.pop("max_tokens", 4096)

        json_system_prompt = (
            f"{system_prompt}\n\n"
            "IMPORTANT: Respond with valid JSON only. "
            "Do not include any text outside the JSON object."
        )

        logger.debug(
            "OpenAI JSON request  model=%s  temperature=%s  max_tokens=%s",
            model,
            temperature,
            max_tokens,
        )

        try:
            response = self._client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": json_system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            raw = response.choices[0].message.content
            logger.debug(
                "OpenAI JSON response  prompt_tokens=%s  completion_tokens=%s",
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
            )
        except openai.BadRequestError:
            # Model may not support response_format; fall back to plain generation.
            logger.warning(
                "Model %s does not support response_format; "
                "falling back to plain text generation.",
                model,
            )
            raw = self.generate(
                json_system_prompt,
                user_message,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

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
            logger.error("Failed to parse JSON from OpenAI response:\n%s", cleaned)
            raise ValueError(
                f"OpenAI response is not valid JSON: {exc}"
            ) from exc
