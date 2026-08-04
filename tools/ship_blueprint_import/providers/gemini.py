"""Google Gemini vision digest provider (REST, soft dependency)."""

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

DEFAULT_MODEL = "gemini-2.0-flash"


class GeminiDigestProvider(DigestProvider):
    name = "gemini"

    def digest(
        self,
        *,
        page_images: list[dict[str, Any]],
        hint: str = "",
        model: str | None = None,
    ) -> ShipDigest:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Gemini provider requires GEMINI_API_KEY (or GOOGLE_API_KEY)"
            )
        model_name = model or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
        parts: list[dict[str, Any]] = [
            {"text": build_user_prompt(page_count=len(page_images), hint=hint)}
        ]
        for page in page_images:
            with open(page["path"], "rb") as fh:  # NOSONAR — operator workdir image
                raw = fh.read()
            b64 = base64.b64encode(raw).decode("ascii")
            mime = "image/png"
            if str(page["path"]).lower().endswith((".jpg", ".jpeg")):
                mime = "image/jpeg"
            parts.append({"inline_data": {"mime_type": mime, "data": b64}})

        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={api_key}"
        )
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:  # noqa: S310
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc

        candidates = payload.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {payload!r}")
        parts_out = candidates[0].get("content", {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts_out)
        return ShipDigest.model_validate(extract_json_object(text))
