"""Anthropic Claude vision digest provider (REST, soft dependency)."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Any

from tools.ship_blueprint_import.models import ShipDigest
from tools.ship_blueprint_import.providers import (
    DigestProvider,
    build_user_prompt,
    extract_json_object,
)

DEFAULT_MODEL = "claude-sonnet-4-5"


class AnthropicDigestProvider(DigestProvider):
    name = "anthropic"

    def digest(
        self,
        *,
        page_images: list[dict[str, Any]],
        hint: str = "",
        model: str | None = None,
    ) -> ShipDigest:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Anthropic provider requires ANTHROPIC_API_KEY")
        model_name = model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL

        content: list[dict[str, Any]] = []
        for page in page_images:
            with open(page["path"], "rb") as fh:  # NOSONAR — operator workdir image
                raw = fh.read()
            b64 = base64.b64encode(raw).decode("ascii")
            media = "image/png"
            if str(page["path"]).lower().endswith((".jpg", ".jpeg")):
                media = "image/jpeg"
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media,
                        "data": b64,
                    },
                }
            )
        content.append(
            {
                "type": "text",
                "text": build_user_prompt(page_count=len(page_images), hint=hint),
            }
        )

        body = {
            "model": model_name,
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": content}],
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:  # noqa: S310
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic HTTP {exc.code}: {detail}") from exc

        blocks = payload.get("content") or []
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        return ShipDigest.model_validate(extract_json_object(text))
