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
from deck_photo_plate import (  # noqa: E402
    catalog_entry,
    fetch_reference_photo,
    render_fiction_schematic,
    render_photo_plate,
)
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
    resolve_repo_path,
    validate_path_component,
    validated_open,
)

PLATFORMS = [
    "destroyer_baseline",
    "fletcher_class_destroyer",
    "legend_class_nsc",
    "san_antonio_class_lpd",
    "expedition_cruise_300",
    "expedition_cruise_450",
    "classic_cruise_1900",
    "spirit_cruise_3000",
    "mega_cruise_5000",
    "messy_cruise_500",
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
    with validated_open(path, allowed_roots=(REPO,), encoding="utf-8") as fh:
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
            elif kind == "hull_waterline":
                draw.polygon(pts, outline="#9999FF", width=1)
            elif kind == "compartment":
                draw.polygon(pts, fill=panel, outline=peach, width=1)
        elif geom.get("type") == "LineString" and kind == "hvac_path":
            pts = [to_px(p[0], p[1]) for p in geom["coordinates"]]
            if len(pts) >= 2:
                draw.line(pts, fill=gold, width=1)

    img.save(out_path, format="PNG")


def _render_blueprint_background(
    geojson: dict[str, Any],
    out_path: str,
    *,
    title: str,
    subtitle: str,
    fiction: bool,
) -> None:
    """Blueprint-style class plate for Plotly underlay (historic / fiction-adapted)."""
    from PIL import Image, ImageDraw, ImageFont

    bounds = compute_view_bounds(geojson, padding=2.0)
    xmin, xmax = bounds["xmin"], bounds["xmax"]
    ymin, ymax = bounds["ymin"], bounds["ymax"]
    w_m = max(xmax - xmin, 1.0)
    h_m = max(ymax - ymin, 1.0)
    img_w = 1000
    img_h = max(320, int(1000 * h_m / w_m))

    def to_px(x: float, y: float) -> tuple[int, int]:
        px = int((x - xmin) / w_m * (img_w - 80) + 40)
        py = int((ymax - y) / h_m * (img_h - 100) + 70)
        return px, py

    paper = "#0a1424"
    grid_major = "#1a3358"
    grid_minor = "#122a48"
    hull_fill = "#1a4a7a"
    hull_edge = "#c9e4ff"
    bay_edge = "#6eb5e8"
    gold = "#e8b060"

    img = Image.new("RGB", (img_w, img_h), paper)
    draw = ImageDraw.Draw(img)

    for i in range(0, img_w, 25):
        draw.line([(i, 0), (i, img_h)], fill=grid_minor, width=1)
    for j in range(0, img_h, 25):
        draw.line([(0, j), (img_w, j)], fill=grid_minor, width=1)
    for i in range(0, img_w, 50):
        draw.line([(i, 0), (i, img_h)], fill=grid_major, width=1)
    for j in range(0, img_h, 50):
        draw.line([(0, j), (img_w, j)], fill=grid_major, width=1)

    for feat in geojson.get("features", []):
        kind = feat.get("properties", {}).get("kind", "")
        geom = feat.get("geometry", {})
        if geom.get("type") != "Polygon" or not geom.get("coordinates"):
            continue
        pts = [to_px(p[0], p[1]) for p in geom["coordinates"][0]]
        if kind == "hull_outline":
            draw.polygon(pts, fill=hull_fill, outline=hull_edge, width=3)
        elif kind == "hull_waterline":
            draw.polygon(pts, outline="#88b8e8", width=1)
        elif kind == "compartment":
            draw.polygon(pts, fill="#143050", outline=bay_edge, width=1)

    for feat in geojson.get("features", []):
        if feat.get("properties", {}).get("kind") != "hvac_path":
            continue
        geom = feat.get("geometry", {})
        if geom.get("type") == "LineString":
            pts = [to_px(p[0], p[1]) for p in geom["coordinates"]]
            if len(pts) >= 2:
                draw.line(pts, fill="#3d7ab8", width=1)

    banner = "FICTION-ADAPTED VESSEL — IMAGINARY LAYOUT" if fiction else "CLASS REPRESENTATIVE — DECK PLAN"
    draw.rectangle([(0, 0), (img_w, 52)], fill="#061018")
    draw.text((24, 10), title[:70], fill=gold)
    draw.text((24, 30), subtitle[:90], fill=hull_edge)
    draw.text((24, img_h - 28), banner, fill="#88aacc")

    img.save(out_path, format="PNG")


def _tier_for(platform_id: str) -> str:
    if platform_id in ENTERPRISE_IDS:
        return "fiction_adapted"
    if platform_id in GIS_SOURCES and os.path.isfile(GIS_SOURCES[platform_id]):
        return "gis_traced"
    return "representative"


def _render_background_plate(
    platform_id: str,
    tier: str,
    geojson: dict[str, Any],
    bg_path: str,
    manifest: dict[str, Any],
    photo_entry: dict[str, Any] | None,
    pdir: str,
) -> tuple[bool, dict[str, Any]]:
    labels = manifest.get("ship_class_label", platform_id)
    plate_ok = False

    if photo_entry and photo_entry.get("generated"):
        plate_ok = render_fiction_schematic(
            platform_id,
            geojson,
            bg_path,
            title=labels,
            subtitle=manifest.get("representative_of", "")[:90],
            credit=photo_entry.get("credit", ""),
            license_label=photo_entry.get("license", ""),
        )
        if plate_ok:
            manifest["background_plate"] = "fiction_schematic"
            manifest["reference_photo"] = {
                "license": photo_entry.get("license"),
                "credit": photo_entry.get("credit"),
                "local_file": photo_entry.get("local_file", "reference_photo.jpg"),
            }
        return plate_ok, manifest

    ref_path = fetch_reference_photo(platform_id, pdir)
    if ref_path and photo_entry:
        plate_ok = render_photo_plate(
            geojson,
            ref_path,
            bg_path,
            title=labels,
            subtitle=manifest.get("representative_of", "")[:90],
            credit=photo_entry.get("credit", ""),
            license_label=photo_entry.get("license", ""),
            fiction=tier == "fiction_adapted" or bool(photo_entry.get("fiction_adapted")),
            photo_style=photo_entry.get("photo_style", "profile"),
            auto_trim=bool(photo_entry.get("auto_trim")),
            crop_fraction=photo_entry.get("crop_fraction"),
        )
        if plate_ok:
            manifest["background_plate"] = "reference_photo_composite"
            manifest["reference_photo"] = {
                "wikimedia_title": photo_entry.get("wikimedia_title"),
                "source_page": photo_entry.get("source_page"),
                "license": photo_entry.get("license"),
                "credit": photo_entry.get("credit"),
                "local_file": photo_entry.get("local_file", "reference_photo.jpg"),
            }
    return plate_ok, manifest


def precompute_platform(platform_id: str) -> None:
    safe_id = validate_path_component(platform_id, label="platform_id")
    pdir = resolve_child_path(os.path.join(REPO, "data", "platforms"), safe_id)
    layout_path = resolve_child_path(pdir, "spatial_layout.json")
    airflow_path = resolve_child_path(pdir, "air_flow_paths.json")
    if not os.path.isfile(layout_path):
        print(f"  SKIP {platform_id}: no spatial_layout.json")
        return

    layout = _load_json(layout_path)
    airflow = _load_json(airflow_path) if os.path.isfile(airflow_path) else {}
    tier = _tier_for(platform_id)

    if platform_id in ENTERPRISE_IDS:
        geojson = build_representative_geojson(platform_id, layout, airflow)
    elif tier == "gis_traced":
        from geojson_deck_emit import emit_from_geojson_file

        geojson = emit_from_geojson_file(
            GIS_SOURCES[platform_id], platform_id, layout,
        )
    else:
        geojson = build_representative_geojson(platform_id, layout, airflow)

    gfx_path = resolve_child_path(pdir, "deck_graphics.geojson")
    prepare_output_directory(pdir, allowed_roots=(REPO,))
    with validated_open(gfx_path, "w", allowed_roots=(REPO,), encoding="utf-8") as fh:
        json.dump(geojson, fh, indent=2, ensure_ascii=False)

    png_path = resolve_child_path(pdir, "deck_hull.png")
    _render_hull_png(geojson, png_path)

    bounds = compute_view_bounds(geojson)
    manifest = build_manifest(platform_id, layout, tier, bounds)
    bg_path = resolve_child_path(pdir, "deck_blueprint_bg.png")
    photo_entry = catalog_entry(platform_id)
    plate_ok, manifest = _render_background_plate(
        platform_id, tier, geojson, bg_path, manifest, photo_entry, pdir,
    )
    if not plate_ok:
        _render_blueprint_background(
            geojson,
            bg_path,
            title=manifest.get("ship_class_label", platform_id),
            subtitle=manifest.get("representative_of", "")[:90],
            fiction=tier == "fiction_adapted",
        )
        manifest["background_plate"] = "synthetic_blueprint"

    # User-supplied architectural plates (elevation + plan) live under graphics/.
    graphics_manifest = os.path.join(pdir, "graphics", "graphics.json")
    if os.path.isfile(graphics_manifest):
        with validated_open(
            graphics_manifest, allowed_roots=(REPO,), encoding="utf-8",
        ) as fh:
            arch = json.load(fh)
        manifest["architectural_graphics"] = arch
        plan_rel = (arch.get("plan") or {}).get("file")
        if plan_rel:
            plan_abs = os.path.join(pdir, "graphics", plan_rel)
            if os.path.isfile(plan_abs):
                # Prefer plan plate as the Plotly/legacy underlay source of truth.
                from shutil import copyfile

                copyfile(plan_abs, bg_path)
                manifest["background_plate"] = "architectural_plan"
                manifest.setdefault("assets", {})["plan_overview"] = f"graphics/{plan_rel}"
        elev_rel = (arch.get("elevation") or {}).get("file")
        if elev_rel and os.path.isfile(os.path.join(pdir, "graphics", elev_rel)):
            manifest.setdefault("assets", {})["elevation"] = f"graphics/{elev_rel}"

    # Hull-native view bounds when packing into deck_dimensions (not GIS-traced).
    if tier != "gis_traced" or os.path.isfile(graphics_manifest):
        dims = layout.get("deck_dimensions", {}) or {}
        length_m = float(dims.get("length_m", 120))
        beam_m = float(dims.get("beam_m", 15))
        manifest["view_bounds"] = {
            "xmin": -2.0,
            "xmax": length_m + 2.0,
            "ymin": -2.0,
            "ymax": beam_m + 2.0,
        }

    manifest_path = resolve_child_path(pdir, "deck_manifest.json")
    with validated_open(manifest_path, "w", allowed_roots=(REPO,), encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(
        f"  OK {platform_id} ({tier}) -> deck_graphics.geojson, "
        f"deck_hull.png, deck_blueprint_bg.png, deck_manifest.json",
    )


def write_deck_provenance_catalog() -> None:
    catalog: dict[str, Any] = {"schema_version": "1.0", "platforms": {}}
    for pid in PLATFORMS:
        mpath = os.path.join(REPO, "data", "platforms", pid, "deck_manifest.json")
        if os.path.isfile(mpath):
            catalog["platforms"][pid] = _load_json(mpath)
    out = resolve_child_path(os.path.join(REPO, "data", "platforms"), "deck_provenance.json")
    prepare_output_directory(os.path.dirname(out), allowed_roots=(REPO,))
    with validated_open(out, "w", allowed_roots=(REPO,), encoding="utf-8") as fh:
        json.dump(catalog, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"  Wrote {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Precompute dashboard deck assets")
    parser.add_argument("--platform", help="Single platform_id")
    args = parser.parse_args()

    targets = [validate_path_component(args.platform, label="platform_id")] if args.platform else PLATFORMS
    print("Precomputing deck assets...")
    for pid in targets:
        precompute_platform(pid)
    write_deck_provenance_catalog()
    print("Done.")


if __name__ == "__main__":
    main()
