"""Build pydeck Deck for tactical compartment contamination overlay."""
from __future__ import annotations

from typing import Any

from dashboard.theme import LCARS_AMBER, LCARS_GOLD, LCARS_GREEN, LCARS_RED

try:
    import pydeck as pdk
except ImportError:
    pdk = None  # type: ignore[assignment]


def _hex_to_rgb(hex_color: str) -> list[int]:
    h = hex_color.lstrip("#")
    return [int(h[i : i + 2], 16) for i in (0, 2, 4)]


def metric_to_rgba(value: float, max_val: float) -> list[int]:
    if max_val <= 0:
        return _hex_to_rgb(LCARS_GREEN) + [180]
    t = min(1.0, max(0.0, value / max_val))
    if t < 0.33:
        base = _hex_to_rgb(LCARS_GREEN)
    elif t < 0.66:
        base = _hex_to_rgb(LCARS_GOLD)
    else:
        base = _hex_to_rgb(LCARS_RED)
    alpha = int(120 + 100 * t)
    return base + [alpha]


def _zone_metric(record: dict[str, Any], zone_id: str, color_mode: str) -> float:
    spaces = record.get("spaces", {})
    obs = record.get("observation_engine", {})
    if color_mode == "Airborne Aerosol Mass":
        return float(spaces.get(zone_id, {}).get("pathogen_mass", 0.0))
    if color_mode == "Surface Fomite Contamination":
        return float(obs.get("surface_swab", {}).get(zone_id, {}).get("surface_mass", 0.0))
    count = 0
    for agent in record.get("agents", []):
        if agent.get("location") == zone_id and agent.get("status") in (
            "symptomatic", "infected",
        ):
            count += 1
    return float(count)


def _features_to_rows(
    geojson: dict[str, Any],
    record: dict[str, Any],
    color_mode: str,
    deck_filter: str | None,
) -> tuple[list[dict[str, Any]], float]:
    rows: list[dict[str, Any]] = []
    max_val = 0.0
    for feat in geojson.get("features", []):
        props = feat.get("properties", {})
        kind = props.get("kind", "")
        geom = feat.get("geometry", {})
        if kind == "compartment":
            zid = props.get("zone_id", "")
            if deck_filter and deck_filter != "All Decks":
                if str(props.get("deck", "")) != deck_filter:
                    continue
            val = _zone_metric(record, zid, color_mode)
            max_val = max(max_val, val)
            if geom.get("type") != "Polygon":
                continue
            ring = geom["coordinates"][0]
            rows.append({
                "zone_id": zid,
                "kind": kind,
                "polygon": ring,
                "metric": val,
            })
        elif kind in ("hull_outline", "hvac_path"):
            if kind == "hull_outline" or (
                deck_filter is None or deck_filter == "All Decks"
            ):
                if geom.get("type") == "Polygon":
                    path = geom["coordinates"][0]
                elif geom.get("type") == "LineString":
                    path = geom["coordinates"]
                else:
                    continue
                rows.append({
                    "zone_id": props.get("zone_id", kind),
                    "kind": kind,
                    "path": path,
                    "metric": 0.0,
                })
    return rows, max_val


def build_pydeck_deck(
    geojson: dict[str, Any],
    record: dict[str, Any],
    manifest: dict[str, Any],
    color_mode: str,
    deck_filter: str | None = None,
) -> Any | None:
    if pdk is None or not geojson.get("features"):
        return None

    rows, max_val = _features_to_rows(geojson, record, color_mode, deck_filter)
    for row in rows:
        if row["kind"] == "compartment":
            row["fill_color"] = metric_to_rgba(row["metric"], max(max_val, 0.01))

    bounds = manifest.get("view_bounds", {})
    xmin = float(bounds.get("xmin", 0))
    xmax = float(bounds.get("xmax", 120))
    ymin = float(bounds.get("ymin", 0))
    ymax = float(bounds.get("ymax", 15))
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2

    compartment_layer = pdk.Layer(
        "PolygonLayer",
        data=[r for r in rows if r["kind"] == "compartment"],
        get_polygon="polygon",
        get_fill_color="fill_color",
        get_line_color=[255, 204, 153],
        get_line_width=2,
        pickable=True,
        auto_highlight=True,
    )

    path_data = []
    for r in rows:
        if r["kind"] == "hull_outline":
            path_data.append({"path": r["path"], "color": [255, 153, 0, 200]})
        elif r["kind"] == "hvac_path":
            path_data.append({"path": r["path"], "color": [255, 153, 0, 80]})

    layers = []
    if path_data:
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=path_data,
                get_path="path",
                get_color="color",
                get_width=3,
                width_min_pixels=1,
            )
        )
    layers.append(compartment_layer)

    view = pdk.ViewState(
        latitude=cy,
        longitude=cx,
        zoom=0.8,
        pitch=25,
        min_zoom=0.2,
        max_zoom=5,
    )

    return pdk.Deck(
        layers=layers,
        initial_view_state=view,
        map_style=None,
        tooltip={"text": "{zone_id}"},
    )
