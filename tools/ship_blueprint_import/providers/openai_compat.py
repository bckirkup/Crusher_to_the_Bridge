"""OpenAI-compatible vision digest provider (REST, soft dependency)."""

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

DEFAULT_MODEL = "gpt-4o"


class OpenAICompatDigestProvider(DigestProvider):
    name = "openai_compat"

    def digest(
        self,
        *,
        page_images: list[dict[str, Any]],
        hint: str = "",
        model: str | None = None,
    ) -> ShipDigest:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OpenAI-compatible provider requires OPENAI_API_KEY")
        base = (
            os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        model_name = model or os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL

        content: list[dict[str, Any]] = [
            {"type": "text", "text": build_user_prompt(page_count=len(page_images), hint=hint)}
        ]
        for page in page_images:
            with open(page["path"], "rb") as fh:  # NOSONAR — operator workdir image
                raw = fh.read()
            b64 = base64.b64encode(raw).decode("ascii")
            mime = "image/png"
            if str(page["path"]).lower().endswith((".jpg", ".jpeg")):
                mime = "image/jpeg"
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                }
            )

        body = {
            "model": model_name,
            "messages": [{"role": "user", "content": content}],
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            f"{base}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:  # noqa: S310
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI HTTP {exc.code}: {detail}") from exc

        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError(f"OpenAI returned no choices: {payload!r}")
        text = choices[0]["message"]["content"]
        return ShipDigest.model_validate(extract_json_object(text))
