#!/usr/bin/env python3
"""
Precompute deck_graphics.geojson, deck_hull.png, and deck_manifest.json per platform.

Regenerate when spatial_layout.json zones change::

    python3 scripts/precompute_deck_assets.py
    python3 scripts/precompute_deck_assets.py --platform enterprise_galaxy_tng
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

from deck_footprint_builder import (  # noqa: E402
    build_manifest,
    build_representative_geojson,
    compute_view_bounds,
)
from enterprise_deck_graphics import (  # noqa: E402
    constitution_tos_geojson,
    galaxy_tng_geojson,
)

PLATFORMS = [
    "destroyer_baseline",
    "fletcher_class_destroyer",
    "legend_class_nsc",
    "san_antonio_class_lpd",
    "expedition_cruise_300",
    "mega_cruise_5000",
    "enterprise_constitution_tos",
    "enterprise_galaxy_tng",
]

ENTERPRISE_IDS = frozenset({
    "enterprise_constitution_tos",
    "enterprise_galaxy_tng",
})

GIS_SOURCES = {
    "destroyer_baseline": os.path.join(REPO, "data", "shp", "test_destroyer_deck.geojson"),
}


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _render_hull_png(geojson: dict[str, Any], out_path: str) -> None:
    """Render LCARS hull PNG using Pillow (no matplotlib required)."""
    from PIL import Image, ImageDraw

    bounds = compute_view_bounds(geojson, padding=2.0)
    xmin, xmax = bounds["xmin"], bounds["xmax"]
    ymin, ymax = bounds["ymin"], bounds["ymax"]
    w_m = max(xmax - xmin, 1.0)
    h_m = max(ymax - ymin, 1.0)
    img_w, img_h = 800, int(800 * h_m / w_m)
    img_h = max(img_h, 200)

    def to_px(x: float, y: float) -> tuple[int, int]:
        px = int((x - xmin) / w_m * (img_w - 40) + 20)
        py = int((ymax - y) / h_m * (img_h - 40) + 20)
        return px, py

    img = Image.new("RGB", (img_w, img_h), "#000000")
    draw = ImageDraw.Draw(img)
    gold = "#FF9900"
    panel = "#1A1A2E"
    peach = "#FFCC99"

    for feat in geojson.get("features", []):
        kind = feat.get("properties", {}).get("kind", "")
        geom = feat.get("geometry", {})
        if geom.get("type") == "Polygon" and geom.get("coordinates"):
            pts = [to_px(p[0], p[1]) for p in geom["coordinates"][0]]
            if kind == "hull_outline":
                draw.polygon(pts, outline=gold, width=3)
            elif kind == "compartment":
                draw.polygon(pts, fill=panel, outline=peach, width=1)
        elif geom.get("type") == "LineString" and kind == "hvac_path":
            pts = [to_px(p[0], p[1]) for p in geom["coordinates"]]
            if len(pts) >= 2:
                draw.line(pts, fill=gold, width=1)

    img.save(out_path, format="PNG")


def _tier_for(platform_id: str) -> str:
    if platform_id in ENTERPRISE_IDS:
        return "fiction_adapted"
    if platform_id in GIS_SOURCES and os.path.isfile(GIS_SOURCES[platform_id]):
        return "gis_traced"
    return "representative"


def precompute_platform(platform_id: str) -> None:
    pdir = os.path.join(REPO, "data", "platforms", platform_id)
    layout_path = os.path.join(pdir, "spatial_layout.json")
    airflow_path = os.path.join(pdir, "air_flow_paths.json")
    if not os.path.isfile(layout_path):
        print(f"  SKIP {platform_id}: no spatial_layout.json")
        return

    layout = _load_json(layout_path)
    airflow = _load_json(airflow_path) if os.path.isfile(airflow_path) else {}
    tier = _tier_for(platform_id)

    if platform_id == "enterprise_galaxy_tng":
        geojson = galaxy_tng_geojson()
    elif platform_id == "enterprise_constitution_tos":
        geojson = constitution_tos_geojson()
    elif tier == "gis_traced":
        from geojson_deck_emit import emit_from_geojson_file

        geojson = emit_from_geojson_file(GIS_SOURCES[platform_id], platform_id)
    else:
        geojson = build_representative_geojson(platform_id, layout, airflow)

    gfx_path = os.path.join(pdir, "deck_graphics.geojson")
    with open(gfx_path, "w", encoding="utf-8") as fh:
        json.dump(geojson, fh, indent=2, ensure_ascii=False)

    png_path = os.path.join(pdir, "deck_hull.png")
    _render_hull_png(geojson, png_path)

    bounds = compute_view_bounds(geojson)
    manifest = build_manifest(platform_id, layout, tier, bounds)
    manifest_path = os.path.join(pdir, "deck_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"  OK {platform_id} ({tier}) -> deck_graphics.geojson, deck_hull.png, deck_manifest.json")


def write_deck_provenance_catalog() -> None:
    catalog: dict[str, Any] = {"schema_version": "1.0", "platforms": {}}
    for pid in PLATFORMS:
        mpath = os.path.join(REPO, "data", "platforms", pid, "deck_manifest.json")
        if os.path.isfile(mpath):
            catalog["platforms"][pid] = _load_json(mpath)
    out = os.path.join(REPO, "data", "platforms", "deck_provenance.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"  Wrote {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Precompute dashboard deck assets")
    parser.add_argument("--platform", help="Single platform_id")
    args = parser.parse_args()

    targets = [args.platform] if args.platform else PLATFORMS
    print("Precomputing deck assets...")
    for pid in targets:
        precompute_platform(pid)
    write_deck_provenance_catalog()
    print("Done.")


if __name__ == "__main__":
    main()
