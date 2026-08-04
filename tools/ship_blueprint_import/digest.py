"""Stage 2: vision LLM digest → ShipDigest JSON + draft SVG overlays."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from simulation_utils.paths import (
    prepare_output_directory,
    resolve_child_path,
    validated_open,
)
from tools.ship_blueprint_import.models import ShipDigest
from tools.ship_blueprint_import.providers import get_provider
from tools.ship_blueprint_import.svg_io import OverlayPolygon, norm_to_pixel, write_overlay_svg


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_manifest(workdir: str, *, allowed_roots: tuple[str, ...]) -> dict[str, Any]:
    path = resolve_child_path(workdir, "pages_manifest.json")
    with validated_open(path, "r", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        return json.load(fh)


def _write_text(path: str, text: str, *, allowed_roots: tuple[str, ...]) -> None:
    prepare_output_directory(os.path.dirname(path), allowed_roots=allowed_roots)
    with validated_open(path, "w", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        fh.write(text)
        if not text.endswith("\n"):
            fh.write("\n")


def _write_json(path: str, payload: dict[str, Any], *, allowed_roots: tuple[str, ...]) -> None:
    prepare_output_directory(os.path.dirname(path), allowed_roots=allowed_roots)
    with validated_open(path, "w", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def draft_svgs_from_digest(
    digest: ShipDigest,
    manifest: dict[str, Any],
    overlays_dir: str,
    *,
    allowed_roots: tuple[str, ...],
    suffix: str = "draft",
) -> list[str]:
    """Write per-page SVG overlays from digest polygon_norm geometry."""
    prepare_output_directory(overlays_dir, allowed_roots=allowed_roots)
    pages = {int(p["page"]): p for p in manifest.get("pages", [])}
    written: list[str] = []
    by_page: dict[int, list[OverlayPolygon]] = {}
    for zone in digest.zones:
        page_meta = pages.get(int(zone.page))
        if not page_meta:
            continue
        w, h = int(page_meta["width"]), int(page_meta["height"])
        if not zone.polygon_norm:
            # Placeholder rectangle so editors still see a named path
            pad = 0.05
            zone.polygon_norm = [
                [pad, pad],
                [1.0 - pad, pad],
                [1.0 - pad, 1.0 - pad],
                [pad, 1.0 - pad],
            ]
        pts = norm_to_pixel(zone.polygon_norm, w, h)
        by_page.setdefault(int(zone.page), []).append(
            OverlayPolygon(zone_id=zone.id, points=pts, page=int(zone.page))
        )

    for page_num, polys in sorted(by_page.items()):
        page_meta = pages[page_num]
        svg = write_overlay_svg(
            polys,
            width=int(page_meta["width"]),
            height=int(page_meta["height"]),
            title=f"{digest.platform_id} page {page_num} {suffix}",
        )
        name = f"page_{page_num:02d}_{suffix}.svg"
        path = resolve_child_path(overlays_dir, name)
        _write_text(path, svg, allowed_roots=allowed_roots)
        written.append(name)
    return written


def digest_workdir(
    *,
    workdir: str,
    provider_name: str = "mock",
    model: str | None = None,
    hint: str = "",
    fixture_path: str | None = None,
    allowed_roots: tuple[str, ...],
) -> ShipDigest:
    """Run vision digest against workdir pages; write digest + draft SVGs."""
    manifest = _load_manifest(workdir, allowed_roots=allowed_roots)
    page_images: list[dict[str, Any]] = []
    for page in manifest.get("pages", []):
        rel = page["file"]
        abs_path = os.path.realpath(os.path.join(workdir, rel))
        page_images.append(
            {
                "page": int(page["page"]),
                "path": abs_path,
                "width": int(page["width"]),
                "height": int(page["height"]),
            }
        )
    if not page_images:
        raise RuntimeError("pages_manifest.json has no pages; run ingest first")

    provider = get_provider(provider_name)
    if provider_name in ("mock", "fixture") and fixture_path:
        from tools.ship_blueprint_import.providers.mock import MockDigestProvider

        provider = MockDigestProvider(fixture_path=fixture_path)

    digest = provider.digest(page_images=page_images, hint=hint, model=model)

    digest_path = resolve_child_path(workdir, "ship_digest.json")
    payload = digest.to_json_dict()
    _write_json(digest_path, payload, allowed_roots=allowed_roots)

    overlays_dir = os.path.join(workdir, "overlays")
    written = draft_svgs_from_digest(
        digest, manifest, overlays_dir, allowed_roots=allowed_roots, suffix="draft"
    )

    meta = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "provider": provider.name,
        "model": model,
        "hint": hint,
        "digest_sha256": _sha256_bytes(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ),
        "draft_overlays": written,
    }
    _write_json(
        resolve_child_path(workdir, "digest_meta.json"),
        meta,
        allowed_roots=allowed_roots,
    )
    return digest
