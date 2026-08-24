"""Vision LLM provider interface for ShipDigest extraction."""

from __future__ import annotations

import abc
import json
from typing import Any

from tools.ship_blueprint_import.models import ShipDigest
from tools.ship_blueprint_import.ontology import DIGEST_SYSTEM_PROMPT, ontology_prompt_block


class DigestProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def digest(
        self,
        *,
        page_images: list[dict[str, Any]],
        hint: str = "",
        model: str | None = None,
    ) -> ShipDigest:
        """Return a ShipDigest from page image records.

        Each ``page_images`` item: ``{page, path, width, height}``.
        """


def _strip_markdown_fence(text: str) -> str:
    """Remove a leading/trailing ``` or ```json fence without regex backtracking."""
    if not text.startswith("```"):
        return text
    body = text[3:]
    if body.lower().startswith("json"):
        body = body[4:]
    body = body.lstrip("\r\n")
    if body.rstrip().endswith("```"):
        body = body.rstrip()
        body = body[: -3].rstrip()
    return body


def _consume_string_char(ch: str, escape: bool) -> tuple[bool, bool]:
    """Advance string-scan state. Returns (still_in_string, next_escape)."""
    if escape:
        return True, False
    if ch == "\\":
        return True, True
    if ch == '"':
        return False, False
    return True, False


def _first_json_object_span(text: str) -> str | None:
    """Return the first top-level ``{...}`` slice via brace counting (no ReDoS)."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            in_string, escape = _consume_string_char(ch, escape)
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return None


def extract_json_object(text: str) -> dict[str, Any]:
    """Pull the first JSON object from a model response."""
    text = _strip_markdown_fence(text.strip())
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        # Continue to the broader object-span parser for fenced responses.
        pass
    payload = _first_json_object_span(text)
    if payload is None:
        raise ValueError("model response did not contain a JSON object")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("JSON payload is not an object")
    return data


def build_user_prompt(*, page_count: int, hint: str = "") -> str:
    parts = [
        DIGEST_SYSTEM_PROMPT,
        ontology_prompt_block(),
        f"\nThere are {page_count} page image(s) attached in order (page 1..N).",
        "Emit a single ShipDigest JSON object. Required keys: platform_id, "
        "length_m, beam_m, crew_estimate, decks, zones. Each zone needs id, "
        "type, deck, page, polygon_norm (3+ vertices), and preferably "
        "volume_m3_est / max_occupancy / traffic.",
        "Also include hvac_hints, adjacency_hints, graywater_zones when possible.",
    ]
    if hint.strip():
        parts.append(f"Operator hint: {hint.strip()}")
    return "\n\n".join(parts)


def get_provider(name: str) -> DigestProvider:
    key = name.strip().lower()
    if key in ("mock", "fixture"):
        from tools.ship_blueprint_import.providers.mock import MockDigestProvider

        return MockDigestProvider()
    if key in ("gemini", "google"):
        from tools.ship_blueprint_import.providers.gemini import GeminiDigestProvider

        return GeminiDigestProvider()
    if key in ("openai", "openai_compat", "openai-compatible"):
        from tools.ship_blueprint_import.providers.openai_compat import (
            OpenAICompatDigestProvider,
        )

        return OpenAICompatDigestProvider()
    if key in ("anthropic", "claude"):
        from tools.ship_blueprint_import.providers.anthropic import (
            AnthropicDigestProvider,
        )

        return AnthropicDigestProvider()
    raise ValueError(
        f"unknown digest provider {name!r}; "
        "choose mock|gemini|openai_compat|anthropic"
    )
