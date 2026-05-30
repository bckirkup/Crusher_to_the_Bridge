"""Static global health briefings keyed by epoch."""

from __future__ import annotations

import json
import os
from typing import Any


def load_global_health_timeline(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def briefing_for_epoch(timeline: dict[str, Any], epoch: int) -> dict[str, Any]:
    briefings = timeline.get("briefings", [])
    result: dict[str, Any] = {
        "alerts": [],
        "pandemic_declarations": [],
        "travel_advisories": [],
    }
    for b in briefings:
        if int(b.get("epoch", -1)) <= epoch:
            result["alerts"] = list(b.get("alerts", []))
            result["pandemic_declarations"] = list(b.get("pandemic_declarations", []))
            result["travel_advisories"] = list(b.get("travel_advisories", []))
    return result


def default_timeline_path(repo_root: str) -> str:
    return os.path.join(
        repo_root,
        "presidio",
        "data",
        "intelligence",
        "global_health_timeline.json",
    )
