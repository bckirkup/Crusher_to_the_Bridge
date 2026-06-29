"""Ship-local deck geometry and contamination metrics (meters, not lat/lon)."""
from __future__ import annotations

import os
import sys
from typing import Any, Iterator

from dashboard.loaders import PlatformBundle
from telemetry_buffer.agent_axes import agent_has_symptomatic_presentation

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
from blueprint_shapes import blueprint_compartment  # noqa: E402


def zone_metric(record: dict[str, Any], zone_id: str, color_mode: str) -> float:
    spaces = record.get("spaces", {})
    obs = record.get("observation_engine", {})
    if color_mode == "Airborne Aerosol Mass":
        return float(spaces.get(zone_id, {}).get("pathogen_mass", 0.0))
    if color_mode == "Surface Fomite Contamination":
        return float(obs.get("surface_swab", {}).get(zone_id, {}).get("surface_mass", 0.0))
    count = 0
    for agent in record.get("agents", []):
        if agent.get("location") == zone_id and agent_has_symptomatic_presentation(agent):
            count += 1
    return float(count)


def collect_zone_metrics(
    record: dict[str, Any],
    bundle: PlatformBundle,
    color_mode: str,
    deck_filter: str | None,
) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for zid, zinfo in bundle.zone_coords.items():
        if deck_filter and deck_filter != "All Decks":
            if zinfo.get("deck") != deck_filter:
                continue
        metrics[zid] = zone_metric(record, zid, color_mode)
    return metrics


def color_scale_max(metrics: dict[str, float]) -> float:
    """Avoid one hot zone washing out the entire hull."""
    if not metrics:
        return 1.0
    vals = sorted(metrics.values())
    if not vals or max(vals) <= 0:
        return 1.0
    if len(vals) < 4:
        return max(max(vals), 1e-6)
    idx = min(len(vals) - 1, int(len(vals) * 0.9))
    p90 = vals[idx]
    return max(p90, max(vals) * 0.35, 1e-6)


def metric_fraction(value: float, scale_max: float) -> float:
    if scale_max <= 0:
        return 0.0
    return min(1.0, max(0.0, value / scale_max))


def _zone_ring(zinfo: dict[str, Any]) -> list[list[float]]:
    return blueprint_compartment(
        float(zinfo["x"]),
        float(zinfo["y"]),
        float(zinfo.get("volume_m3", 100)),
        zinfo.get("type", "Free"),
    )


def iter_hull_rings(bundle: PlatformBundle) -> Iterator[tuple[str, list[list[float]]]]:
    for feat in bundle.deck_graphics.get("features", []):
        kind = feat.get("properties", {}).get("kind", "")
        if kind not in ("hull_outline", "hull_waterline"):
            continue
        geom = feat.get("geometry", {})
        if geom.get("type") == "Polygon" and geom.get("coordinates"):
            yield kind, geom["coordinates"][0]


def iter_compartment_rings(
    bundle: PlatformBundle,
    deck_filter: str | None,
) -> Iterator[tuple[str, list[list[float]], str]]:
    """Yield (zone_id, ring, deck) for every zone in layout — GeoJSON or synthetic."""
    geo_by_zone: dict[str, list[list[float]]] = {}
    deck_by_zone: dict[str, str] = {}
    for feat in bundle.deck_graphics.get("features", []):
        props = feat.get("properties", {})
        if props.get("kind") != "compartment":
            continue
        zid = props.get("zone_id", "")
        geom = feat.get("geometry", {})
        if geom.get("type") == "Polygon" and geom.get("coordinates"):
            geo_by_zone[zid] = geom["coordinates"][0]
            deck_by_zone[zid] = str(props.get("deck", ""))

    for zid, zinfo in bundle.zone_coords.items():
        deck = zinfo.get("deck", "main")
        if deck_filter and deck_filter != "All Decks" and deck != deck_filter:
            continue
        ring = geo_by_zone.get(zid) or _zone_ring(zinfo)
        yield zid, ring, deck


def iter_hvac_paths(
    bundle: PlatformBundle,
    deck_filter: str | None,
) -> Iterator[list[list[float]]]:
    for feat in bundle.deck_graphics.get("features", []):
        props = feat.get("properties", {})
        if props.get("kind") != "hvac_path":
            continue
        geom = feat.get("geometry", {})
        if geom.get("type") == "LineString":
            yield geom["coordinates"]
    if deck_filter and deck_filter != "All Decks":
        return
    for link in bundle.airflow.get("adjacency", []):
        fz, tz = link.get("from", ""), link.get("to", "")
        if fz in bundle.zone_coords and tz in bundle.zone_coords:
            a, b = bundle.zone_coords[fz], bundle.zone_coords[tz]
            yield [
                [float(a["x"]), float(a["y"])],
                [float(b["x"]), float(b["y"])],
            ]
