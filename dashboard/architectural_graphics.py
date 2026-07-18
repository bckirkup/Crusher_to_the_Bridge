"""Resolve user-supplied architectural ship graphics (elevation + deck plans)."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ArchitecturalGraphics:
    """Paths and credits for plan/elevation underlays."""

    graphics_dir: str | None = None
    elevation_path: str | None = None
    plan_overview_path: str | None = None
    deck_plan_paths: dict[str, str] = field(default_factory=dict)
    elevation_credit: str = ""
    plan_credit: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def has_elevation(self) -> bool:
        return bool(self.elevation_path and os.path.isfile(self.elevation_path))

    @property
    def has_plan(self) -> bool:
        return bool(self.plan_overview_path and os.path.isfile(self.plan_overview_path))

    def plan_for_deck(self, deck: str | None) -> str | None:
        if deck and deck in self.deck_plan_paths:
            path = self.deck_plan_paths[deck]
            if path and os.path.isfile(path):
                return path
        if self.has_plan:
            return self.plan_overview_path
        return None


def _abs_under(graphics_dir: str, rel: str | None) -> str | None:
    if not rel:
        return None
    path = rel if os.path.isabs(rel) else os.path.join(graphics_dir, rel)
    return path if os.path.isfile(path) else None


def load_architectural_graphics(platform_dir: str) -> ArchitecturalGraphics:
    """Load ``graphics/graphics.json`` when present under a platform directory."""
    gdir = os.path.join(platform_dir, "graphics")
    manifest_path = os.path.join(gdir, "graphics.json")
    if not os.path.isfile(manifest_path):
        # Fallback: discover elevation.jpg / plan_overview.jpg without manifest.
        elev = os.path.join(gdir, "elevation.jpg")
        plan = os.path.join(gdir, "plan_overview.jpg")
        if os.path.isfile(elev) or os.path.isfile(plan):
            return ArchitecturalGraphics(
                graphics_dir=gdir if os.path.isdir(gdir) else None,
                elevation_path=elev if os.path.isfile(elev) else None,
                plan_overview_path=plan if os.path.isfile(plan) else None,
            )
        return ArchitecturalGraphics()

    with open(manifest_path, encoding="utf-8") as fh:
        data = json.load(fh)

    elev_meta = data.get("elevation") or {}
    plan_meta = data.get("plan") or {}
    deck_plans: dict[str, str] = {}
    for deck_id, rel in (data.get("deck_plans") or {}).items():
        path = _abs_under(gdir, rel)
        if path:
            deck_plans[str(deck_id)] = path

    return ArchitecturalGraphics(
        graphics_dir=gdir,
        elevation_path=_abs_under(gdir, elev_meta.get("file", "elevation.jpg")),
        plan_overview_path=_abs_under(gdir, plan_meta.get("file", "plan_overview.jpg")),
        deck_plan_paths=deck_plans,
        elevation_credit=str(elev_meta.get("credit", "")),
        plan_credit=str(plan_meta.get("credit", "")),
        raw=data,
    )


_DECK_NUM = re.compile(r"^(\d+)")


def deck_sort_key(deck: str) -> tuple[int, str]:
    """Sort decks low-to-high by leading numeric prefix when present."""
    m = _DECK_NUM.match(deck or "")
    if m:
        return (int(m.group(1)), deck)
    # Fiction decks without leading numbers: keep alphabetical after numeric decks.
    return (10_000, deck)


def ordered_decks(layout: dict[str, Any]) -> list[str]:
    decks = sorted(
        {str(z.get("deck", "main")) for z in layout.get("zones", [])},
        key=deck_sort_key,
    )
    return decks
