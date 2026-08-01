"""Smoke tests for the epoch timing harness helpers (no long sims)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "_epoch_timing"))

from time_epochs import (  # noqa: E402
    CRUISE_COMPARE_DEFAULTS,
    _build_platform_spec,
)


def test_build_platform_spec_wires_agents_and_compact() -> None:
    spec = _build_platform_spec("expedition_cruise_450", epochs=12, num_agents=450)
    assert spec["catalog"]["platform_id"] == "expedition_cruise_450"
    assert spec["run"]["history_retention"] == "compact"
    assert spec["config_overrides"]["ship_graph"]["num_agents"] == 450
    # Round-trip JSON-serializable
    json.dumps(spec)


def test_compare_defaults_cover_cabin_corridor_fleet() -> None:
    platforms = {e["platform"] for e in CRUISE_COMPARE_DEFAULTS}
    assert platforms == {
        "expedition_cruise_450",
        "classic_cruise_1900",
        "spirit_cruise_3000",
        "mega_cruise_5000",
    }
