"""Build pydeck Deck in ship-local Cartesian coordinates (not a world map)."""
from __future__ import annotations

from typing import Any

from dashboard.deck_geometry import (
    collect_zone_metrics,
    color_scale_max,
    iter_compartment_rings,
    iter_hull_rings,
    iter_hvac_paths,
    metric_fraction,
)

try:
    import pydeck as pdk
except ImportError:
    pdk = None  # type: ignore[assignment]

# deck.gl COORDINATE_SYSTEM.CARTESIAN — local meters, no globe
_CARTESIAN = 1


def _lcars_rgba(fraction: float, alpha: int = 200) -> list[int]:
    if fraction <= 0.01:
        return [26, 26, 46, 140]
    if fraction < 0.33:
        return [153, 204, 153, alpha]
    if fraction < 0.66:
        return [255, 153, 0, alpha]
    return [204, 102, 102, min(255, alpha + 40)]


def build_pydeck_deck(
    bundle: Any,
    record: dict[str, Any],
    manifest: dict[str, Any],
    color_mode: str,
    deck_filter: str | None = None,
) -> Any | None:
    if pdk is None:
        return None

    metrics = collect_zone_metrics(record, bundle, color_mode, deck_filter)
    scale_max = color_scale_max(metrics)

    compartments: list[dict[str, Any]] = []
    for zid, ring, _deck in iter_compartment_rings(bundle, deck_filter):
        frac = metric_fraction(metrics.get(zid, 0.0), scale_max)
        compartments.append({
            "zone_id": zid,
            "polygon": ring,
            "fill_color": _lcars_rgba(frac),
            "line_color": [255, 204, 153, 255],
        })

    if not compartments:
        return None

    hull_paths: list[dict[str, Any]] = []
    for kind, ring in iter_hull_rings(bundle):
        closed = ring + [ring[0]] if ring and ring[0] != ring[-1] else ring
        if kind == "hull_waterline":
            hull_paths.append({
                "path": closed,
                "color": [153, 153, 255, 120],
                "width": 2,
            })
        else:
            hull_paths.append({
                "path": closed,
                "color": [255, 153, 0, 255],
                "width": 6,
            })

    hvac_paths: list[dict[str, Any]] = []
    for path in iter_hvac_paths(bundle, deck_filter):
        hvac_paths.append({
            "path": path,
            "color": [255, 153, 0, 90],
            "width": 2,
        })

    bounds = manifest.get("view_bounds", {})
    xmin = float(bounds.get("xmin", 0))
    xmax = float(bounds.get("xmax", 120))
    ymin = float(bounds.get("ymin", 0))
    ymax = float(bounds.get("ymax", 15))
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    span = max(xmax - xmin, ymax - ymin, 1.0)
    zoom = max(0.5, min(8.0, 14.0 / span))

    layers: list[Any] = []

    if hull_paths:
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=hull_paths,
                get_path="path",
                get_color="color",
                get_width="width",
                width_min_pixels=4,
                coordinate_system=_CARTESIAN,
            )
        )

    if hvac_paths:
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=hvac_paths,
                get_path="path",
                get_color="color",
                get_width="width",
                width_min_pixels=1,
                coordinate_system=_CARTESIAN,
            )
        )

    layers.append(
        pdk.Layer(
            "PolygonLayer",
            data=compartments,
            get_polygon="polygon",
            get_fill_color="fill_color",
            get_line_color="line_color",
            get_line_width=2,
            line_width_min_pixels=1,
            stroked=True,
            filled=True,
            pickable=True,
            auto_highlight=True,
            coordinate_system=_CARTESIAN,
        )
    )

    view_state = pdk.ViewState(
        target=[cx, cy, 0],
        zoom=zoom,
        rotation_x=0,
        rotation_orbit=0,
    )

    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        views=[pdk.View(type="OrthographicView", controller=True)],
        map_provider=None,
        map_style=None,
        tooltip={"text": "{zone_id}"},
    )
