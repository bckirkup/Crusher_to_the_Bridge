#!/usr/bin/env python3
"""Download class reference photos and composite LCARS deck plates."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from deck_footprint_builder import compute_view_bounds

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(REPO, "data", "platforms", "class_photo_catalog.json")
USER_AGENT = "Crusher-to-the-Bridge/1.0 (deck plate precompute; +https://github.com/bckirkup/Crusher_to_the_Bridge)"


def load_catalog() -> dict[str, Any]:
    with open(CATALOG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def catalog_entry(platform_id: str) -> dict[str, Any] | None:
    cat = load_catalog()
    return (cat.get("platforms") or {}).get(platform_id)


def _trim_dark_border(img: Any, *, threshold: int = 32) -> Any:
    """Crop letterbox/black padding around orthographic schematics."""
    gray = img.convert("L")
    mask = gray.point(lambda p: 255 if p > threshold else 0)
    bbox = mask.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def _apply_relative_crop(img: Any, crop: list[float]) -> Any:
    """Crop by fractions [left, top, right, bottom] in 0..1."""
    if len(crop) != 4:
        return img
    w, h = img.size
    left = int(w * crop[0])
    top = int(h * crop[1])
    right = int(w * crop[2])
    bottom = int(h * crop[3])
    if right > left and bottom > top:
        return img.crop((left, top, right, bottom))
    return img


def fetch_reference_photo(platform_id: str, pdir: str, *, force: bool = False) -> str | None:
    """Download reference_photo.jpg if catalog entry exists. Returns path or None."""
    entry = catalog_entry(platform_id)
    if not entry:
        return None
    out_path = os.path.join(pdir, entry.get("local_file", "reference_photo.jpg"))
    if os.path.isfile(out_path) and not force:
        return out_path
    url = entry.get("download_url")
    if not url:
        return None
    os.makedirs(pdir, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"  WARN {platform_id}: could not download reference photo: {exc}")
        return None
    with open(out_path, "wb") as fh:
        fh.write(data)
    print(f"  fetched {platform_id} reference -> {out_path}")
    return out_path


def render_photo_plate(
    geojson: dict[str, Any],
    photo_path: str,
    out_path: str,
    *,
    title: str,
    subtitle: str,
    credit: str,
    license_label: str,
    fiction: bool,
    photo_style: str = "profile",
    auto_trim: bool = False,
    crop_fraction: list[float] | None = None,
) -> bool:
    """Composite reference photo under vector hull / compartment overlay."""
    from PIL import Image, ImageDraw, ImageEnhance, ImageOps

    if not os.path.isfile(photo_path):
        return False

    bounds = compute_view_bounds(geojson, padding=2.0)
    xmin, xmax = bounds["xmin"], bounds["xmax"]
    ymin, ymax = bounds["ymin"], bounds["ymax"]
    w_m = max(xmax - xmin, 1.0)
    h_m = max(ymax - ymin, 1.0)
    img_w = 1000
    img_h = max(320, int(1000 * h_m / w_m))
    header, footer = 52, 36

    def to_px(x: float, y: float) -> tuple[int, int]:
        px = int((x - xmin) / w_m * (img_w - 80) + 40)
        py = int((ymax - y) / h_m * (img_h - header - footer) + header)
        return px, py

    canvas = Image.new("RGB", (img_w, img_h), "#061018")
    try:
        photo = Image.open(photo_path).convert("RGB")
    except OSError:
        return False

    if photo_style == "ortho" or auto_trim:
        photo = _trim_dark_border(photo)
    if crop_fraction:
        photo = _apply_relative_crop(photo, crop_fraction)

    # Fit photo to plot area (cover crop).
    plot_h = img_h - header - footer
    plot_w = img_w
    photo = ImageOps.fit(photo, (plot_w, plot_h), method=Image.Resampling.LANCZOS)
    if photo_style == "plan":
        photo = ImageEnhance.Contrast(photo).enhance(1.15)
    elif photo_style == "ortho":
        photo = ImageEnhance.Brightness(photo).enhance(0.62)
        photo = ImageEnhance.Contrast(photo).enhance(1.2)
    else:
        photo = ImageEnhance.Brightness(photo).enhance(0.55)
        photo = ImageEnhance.Contrast(photo).enhance(1.05)
    canvas.paste(photo, (0, header))

    # LCARS tint over photo
    tint = Image.new("RGBA", (plot_w, plot_h), (10, 20, 36, 140))
    canvas.paste(tint.convert("RGB"), (0, header), tint.split()[3])

    draw = ImageDraw.Draw(canvas)
    gold = "#e8b060"
    hull_edge = "#c9e4ff"
    bay_edge = "#6eb5e8"

    # Faint grid for deck-plan readability
    for i in range(0, img_w, 50):
        draw.line([(i, header), (i, img_h - footer)], fill="#1a3358", width=1)
    for j in range(header, img_h - footer, 50):
        draw.line([(0, j), (img_w, j)], fill="#1a3358", width=1)

    for feat in geojson.get("features", []):
        if feat.get("properties", {}).get("kind") == "hull_outline":
            geom = feat.get("geometry", {})
            if geom.get("type") == "Polygon" and geom.get("coordinates"):
                pts = [to_px(p[0], p[1]) for p in geom["coordinates"][0]]
                draw.polygon(pts, fill="#1a4a7a", outline=hull_edge, width=2)

    for feat in geojson.get("features", []):
        kind = feat.get("properties", {}).get("kind", "")
        geom = feat.get("geometry", {})
        if geom.get("type") != "Polygon" or not geom.get("coordinates"):
            continue
        pts = [to_px(p[0], p[1]) for p in geom["coordinates"][0]]
        if kind == "hull_waterline":
            draw.polygon(pts, outline="#88b8e8", width=1)
        elif kind == "compartment":
            draw.polygon(pts, fill="#0d2848", outline=bay_edge, width=1)

    for feat in geojson.get("features", []):
        if feat.get("properties", {}).get("kind") != "hvac_path":
            continue
        geom = feat.get("geometry", {})
        if geom.get("type") == "LineString":
            pts = [to_px(p[0], p[1]) for p in geom["coordinates"]]
            if len(pts) >= 2:
                draw.line(pts, fill="#3d7ab8", width=1)

    # Gold hull outline on top
    for feat in geojson.get("features", []):
        if feat.get("properties", {}).get("kind") != "hull_outline":
            continue
        geom = feat.get("geometry", {})
        if geom.get("type") == "Polygon" and geom.get("coordinates"):
            pts = [to_px(p[0], p[1]) for p in geom["coordinates"][0]]
            draw.polygon(pts, fill=None, outline=gold, width=4)

    if fiction and photo_style == "ortho":
        banner = "FICTION-ADAPTED — GALAXY-CLASS ORTHO (NON-CANON FAN REFERENCE)"
    elif fiction:
        banner = "FICTION-ADAPTED — IMAGINARY CLASS (photo stand-in)"
    else:
        banner = "CLASS REPRESENTATIVE — REFERENCE PHOTO UNDERLAY"
    draw.rectangle([(0, 0), (img_w, header)], fill="#061018")
    draw.text((24, 10), title[:70], fill=gold)
    draw.text((24, 30), subtitle[:90], fill=hull_edge)
    draw.text((24, img_h - footer + 6), banner, fill="#88aacc")
    draw.text((24, img_h - 18), f"{credit[:95]}  [{license_label}]", fill="#6688aa")

    canvas.save(out_path, format="PNG")
    return True
