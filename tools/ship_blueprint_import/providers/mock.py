"""Mock / fixture digest provider for offline CI."""

from __future__ import annotations

import json
import os
from typing import Any

from tools.ship_blueprint_import.models import ShipDigest
from tools.ship_blueprint_import.providers import DigestProvider


class MockDigestProvider(DigestProvider):
    name = "mock"

    def __init__(self, fixture_path: str | None = None) -> None:
        self.fixture_path = fixture_path

    def digest(
        self,
        *,
        page_images: list[dict[str, Any]],
        hint: str = "",
        model: str | None = None,
    ) -> ShipDigest:
        path = self.fixture_path
        if not path:
            # Default fixture beside the package templates
            here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(here, "templates", "toy_destroyer_digest.json")
        with open(path, encoding="utf-8") as fh:  # NOSONAR — package-local fixture
            data = json.load(fh)
        # Align page count if caller provided pages
        if page_images:
            for zone in data.get("zones", []):
                zone["page"] = min(int(zone.get("page", 1)), len(page_images))
        return ShipDigest.model_validate(data)
