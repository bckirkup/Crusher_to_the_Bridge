#!/usr/bin/env python3
"""Pack compartment footprints per deck so plan polygons do not overlap."""
from __future__ import annotations

import math
import re
from typing import Any

from blueprint_shapes import blueprint_compartment, zone_size

_LATERAL_HINTS = (
    (re.compile(r"_Port(?:_|$)", re.I), 0.22),
    (re.compile(r"_Stbd(?:_|$)|_Starboard", re.I), 0.78),
    (re.compile(r"_Central(?:_|$)|_Center(?:_|$)", re.I), 0.50),
)

_LONGITUDINAL_HINTS = (
    (re.compile(r"_Fwd(?:_|$)|_Forward", re.I), 0.28),
    (re.compile(r"_Mid(?:_|$)|_Middle", re.I), 0.55),
    (re.compile(r"_Aft(?:_|$)", re.I), 0.82),
)


def infer_beam_fraction(zone_id: str) -> float | None:
    for pattern, frac in _LATERAL_HINTS:
        if pattern.search(zone_id):
            return frac
    return None


def infer_length_fraction(zone_id: str) -> float | None:
    for pattern, frac in _LONGITUDINAL_HINTS:
        if pattern.search(zone_id):
            return frac
    return None


def _aabb(ring: list[list[float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in ring[:-1] or ring]
    ys = [p[1] for p in ring[:-1] or ring]
    return min(xs), max(xs), min(ys), max(ys)


def _overlap_area(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax0, ax1, ay0, ay1 = a
    bx0, bx1, by0, by1 = b
    ix = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    iy = max(0.0, min(ay1, by1) - max(ay0, by0))
    return ix * iy


def _ring_at(cx: float, cy: float, w: float, h: float, zone_type: str) -> list[list[float]]:
    """Build chamfered footprint with explicit width/height (meters)."""
    vol_proxy = max(16.0, (w / 1.05) * (h / 0.82) if zone_type == "Free" else w * h)
    # Prefer blueprint_compartment sizing via aspect, then scale to target w/h.
    ring = blueprint_compartment(cx, cy, vol_proxy, zone_type)
    xmin, xmax, ymin, ymax = _aabb(ring)
    cur_w = max(xmax - xmin, 1e-6)
    cur_h = max(ymax - ymin, 1e-6)
    sx = w / cur_w
    sy = h / cur_h
    return [
        [cx + (p[0] - cx) * sx, cy + (p[1] - cy) * sy]
        for p in ring
    ]


def _preferred_centers(
    zones: list[dict[str, Any]],
    length_m: float,
    beam_m: float,
) -> list[tuple[str, float, float, float, str]]:
    """Return (zone_id, cx, cy, volume, type) remapped into hull plan meters."""
    margin_x = max(4.0, length_m * 0.03)
    margin_y = max(2.0, beam_m * 0.06)
    usable_x0, usable_x1 = margin_x, max(margin_x + 1.0, length_m - margin_x)
    usable_y0, usable_y1 = margin_y, max(margin_y + 1.0, beam_m - margin_y)

    raw: list[tuple[str, float, float, float, str]] = []
    for zone in zones:
        zid = zone["id"]
        display = zone.get("display", {})
        dx = float(display.get("x", length_m * 0.5))
        dy = float(display.get("y", beam_m * 0.5))
        vol = float(zone.get("volume_m3", 100))
        ztype = zone.get("type", "Free")
        raw.append((zid, dx, dy, vol, ztype))

    xs = sorted({r[1] for r in raw})
    ys = sorted({r[2] for r in raw})

    def map_axis(values: list[float], v: float, lo: float, hi: float) -> float:
        if len(values) == 1:
            return (lo + hi) * 0.5
        vmin, vmax = values[0], values[-1]
        if abs(vmax - vmin) < 1e-9:
            return (lo + hi) * 0.5
        t = (v - vmin) / (vmax - vmin)
        return lo + t * (hi - lo)

    placed: list[tuple[str, float, float, float, str]] = []
    for zid, dx, dy, vol, ztype in raw:
        lx = infer_length_fraction(zid)
        ly = infer_beam_fraction(zid)
        if lx is not None:
            cx = length_m * lx
            cx = min(max(cx, usable_x0), usable_x1)
        else:
            cx = map_axis(xs, dx, usable_x0, usable_x1)
        if ly is not None:
            cy = beam_m * ly
            cy = min(max(cy, usable_y0), usable_y1)
        else:
            cy = map_axis(ys, dy, usable_y0, usable_y1)
        placed.append((zid, cx, cy, vol, ztype))
    return placed


def pack_deck_compartments(
    zones: list[dict[str, Any]],
    length_m: float,
    beam_m: float,
    *,
    max_iters: int = 80,
) -> dict[str, list[list[float]]]:
    """
    Pack non-overlapping blueprint footprints for zones on one deck.

    Display coordinates are treated as ordering hints and remapped into the
    hull plan (length × beam). Name cues (Port/Stbd/Fwd/Mid/Aft) win when present.
    """
    if not zones:
        return {}

    n = len(zones)
    # Cap footprint so a crowded deck still fits.
    area_budget = (length_m * beam_m) * 0.55 / max(n, 1)
    items: list[dict[str, Any]] = []
    for zid, cx, cy, vol, ztype in _preferred_centers(zones, length_m, beam_m):
        w0, h0 = zone_size(vol, ztype)
        # Cabin corridors become slender along-ship strips.
        if "Corridor" in zid or ztype == "Cabin_Corridor":
            w0 = max(w0 * 1.35, length_m * 0.08)
            h0 = min(h0 * 0.55, beam_m * 0.12)
        scale = min(1.0, math.sqrt(area_budget / max(w0 * h0, 1.0)))
        w = max(3.0, w0 * scale)
        h = max(2.5, h0 * scale)
        # Keep inside hull margins.
        cx = min(max(cx, w / 2 + 1.0), length_m - w / 2 - 1.0)
        cy = min(max(cy, h / 2 + 1.0), beam_m - h / 2 - 1.0)
        items.append({
            "id": zid,
            "cx": cx,
            "cy": cy,
            "w": w,
            "h": h,
            "type": ztype,
        })

    for _ in range(max_iters):
        moved = False
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                ax0, ax1 = a["cx"] - a["w"] / 2, a["cx"] + a["w"] / 2
                ay0, ay1 = a["cy"] - a["h"] / 2, a["cy"] + a["h"] / 2
                bx0, bx1 = b["cx"] - b["w"] / 2, b["cx"] + b["w"] / 2
                by0, by1 = b["cy"] - b["h"] / 2, b["cy"] + b["h"] / 2
                ov = _overlap_area((ax0, ax1, ay0, ay1), (bx0, bx1, by0, by1))
                if ov <= 1e-3:
                    continue
                # Shrink slightly, then push apart along the stronger separation axis.
                shrink = 0.96
                a["w"] = max(3.0, a["w"] * shrink)
                a["h"] = max(2.5, a["h"] * shrink)
                b["w"] = max(3.0, b["w"] * shrink)
                b["h"] = max(2.5, b["h"] * shrink)
                dx = b["cx"] - a["cx"]
                dy = b["cy"] - a["cy"]
                if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                    dx = 0.5
                if abs(dx) * a["h"] >= abs(dy) * a["w"]:
                    push = (a["w"] + b["w"]) * 0.5 - abs(dx) + 0.4
                    if push > 0:
                        sign = 1.0 if dx >= 0 else -1.0
                        a["cx"] -= sign * push * 0.5
                        b["cx"] += sign * push * 0.5
                        moved = True
                else:
                    push = (a["h"] + b["h"]) * 0.5 - abs(dy) + 0.4
                    if push > 0:
                        sign = 1.0 if dy >= 0 else -1.0
                        a["cy"] -= sign * push * 0.5
                        b["cy"] += sign * push * 0.5
                        moved = True
                for it in (a, b):
                    it["cx"] = min(max(it["cx"], it["w"] / 2 + 1.0), length_m - it["w"] / 2 - 1.0)
                    it["cy"] = min(max(it["cy"], it["h"] / 2 + 1.0), beam_m - it["h"] / 2 - 1.0)
        if not moved:
            break

    return {
        it["id"]: _ring_at(it["cx"], it["cy"], it["w"], it["h"], it["type"])
        for it in items
    }


def count_aabb_overlaps(rings: dict[str, list[list[float]]]) -> int:
    ids = list(rings)
    overlaps = 0
    for i in range(len(ids)):
        ai = _aabb(rings[ids[i]])
        for j in range(i + 1, len(ids)):
            if _overlap_area(ai, _aabb(rings[ids[j]])) > 1e-3:
                overlaps += 1
    return overlaps
