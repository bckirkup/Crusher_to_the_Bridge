"""Stage 4: approved SVG + ShipDigest → Crusher platform JSON (deterministic)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from typing import Any

from simulation_utils.paths import (
    prepare_output_directory,
    resolve_child_path,
    validated_open,
)
from tools.ship_blueprint_import.models import ShipDigest, ZoneDigest
from tools.ship_blueprint_import.ontology import ach_for_zone_type
from tools.ship_blueprint_import.svg_io import (
    OverlayPolygon,
    polygons_touch,
    read_overlay_svg,
)

DEFAULT_CROSS_FLOW = 50.0


def _sha256_file(path: str, *, allowed_roots: tuple[str, ...]) -> str:
    h = hashlib.sha256()
    with validated_open(path, "rb", allowed_roots=allowed_roots) as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: str, payload: dict[str, Any], *, allowed_roots: tuple[str, ...]) -> None:
    prepare_output_directory(os.path.dirname(path) or ".", allowed_roots=allowed_roots)
    with validated_open(path, "w", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def load_digest(workdir: str, *, allowed_roots: tuple[str, ...]) -> ShipDigest:
    path = resolve_child_path(workdir, "ship_digest.json")
    with validated_open(path, "r", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        return ShipDigest.model_validate(json.load(fh))


def load_manifest(workdir: str, *, allowed_roots: tuple[str, ...]) -> dict[str, Any]:
    path = resolve_child_path(workdir, "pages_manifest.json")
    with validated_open(path, "r", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        return json.load(fh)


def discover_approved_overlays(overlays_dir: str) -> list[tuple[int, str]]:
    """Return (page_number, absolute_path) for approved SVGs, else draft."""
    if not os.path.isdir(overlays_dir):
        return []
    approved: list[tuple[int, str]] = []
    drafts: list[tuple[int, str]] = []
    for name in sorted(os.listdir(overlays_dir)):
        if not name.endswith(".svg"):
            continue
        # page_01_approved.svg / page_01_draft.svg
        parts = name.replace(".svg", "").split("_")
        if len(parts) < 3 or parts[0] != "page":
            continue
        try:
            page_num = int(parts[1])
        except ValueError:
            continue
        path = os.path.join(overlays_dir, name)
        if name.endswith("_approved.svg"):
            approved.append((page_num, path))
        elif name.endswith("_draft.svg"):
            drafts.append((page_num, path))
    return approved if approved else drafts


def _meters_per_pixel(
    digest: ShipDigest,
    page_meta: dict[str, Any],
) -> tuple[float, float]:
    """Map image width→length_m, height→beam_m (plan-view assumption)."""
    w = max(int(page_meta["width"]), 1)
    h = max(int(page_meta["height"]), 1)
    return digest.length_m / w, digest.beam_m / h


def _zone_geometry(
    poly: OverlayPolygon,
    zone_meta: ZoneDigest | None,
    digest: ShipDigest,
    page_meta: dict[str, Any],
) -> dict[str, Any]:
    mx, my = _meters_per_pixel(digest, page_meta)
    area_m2 = abs(poly.area_px()) * mx * my
    ceiling = digest.ceiling_height_m
    if zone_meta and zone_meta.volume_m3_est and zone_meta.volume_m3_est > 0:
        # Prefer operator/LLM volume estimate; still record geometry-derived area
        volume = float(zone_meta.volume_m3_est)
        if area_m2 < 1.0:
            area_m2 = volume / ceiling
    else:
        volume = area_m2 * ceiling
    volume = max(volume, 1.0)
    area_m2 = max(area_m2, volume / max(ceiling, 1e-6))
    cx, cy = poly.centroid()
    display_x = (cx / max(int(page_meta["width"]), 1)) * digest.length_m
    display_y = (cy / max(int(page_meta["height"]), 1)) * digest.beam_m
    return {
        "floor_area_m2": round(area_m2, 2),
        "ceiling_height_m": ceiling,
        "volume_m3": round(volume, 2),
        "display": {"x": round(display_x, 2), "y": round(display_y, 2)},
    }


def _adjacency_from_polygons(
    polys: list[OverlayPolygon],
    digest: ShipDigest,
) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def _add(a: str, b: str, typ: str) -> None:
        key = tuple(sorted((a, b)))
        if key in seen or a == b:
            return
        seen.add(key)
        edges.append({"from": a, "to": b, "type": typ})

    for hint in digest.adjacency_hints:
        _add(hint.from_, hint.to, hint.type or "passageway")

    # Same-page proximity
    by_page: dict[int | None, list[OverlayPolygon]] = {}
    for p in polys:
        by_page.setdefault(p.page, []).append(p)
    for group in by_page.values():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                if polygons_touch(a.points, b.points):
                    _add(a.zone_id, b.zone_id, "passageway")

    return edges


def _auto_hvac(
    digest: ShipDigest,
    zone_ids: list[str],
    zone_meta: dict[str, ZoneDigest],
) -> list[dict[str, Any]]:
    if digest.hvac_hints:
        out = []
        for hint in digest.hvac_hints:
            rooms = [r for r in hint.rooms if r in zone_ids]
            if not rooms:
                continue
            out.append(
                {
                    "id": hint.id,
                    "rooms": rooms,
                    "ach": float(hint.ach),
                    "description": hint.description or f"AHU branch {hint.id}",
                }
            )
        if out:
            return out

    # Group by deck
    by_deck: dict[str, list[str]] = {}
    for zid in zone_ids:
        deck = zone_meta[zid].deck if zid in zone_meta else "main"
        by_deck.setdefault(deck, []).append(zid)

    hvac: list[dict[str, Any]] = []
    for deck, rooms in by_deck.items():
        achs = [
            ach_for_zone_type(zone_meta[r].type) if r in zone_meta else 6.0
            for r in rooms
        ]
        ach = sum(achs) / max(len(achs), 1)
        safe = deck.replace(" ", "_")[:20]
        hvac.append(
            {
                "id": f"zone_{safe}",
                "rooms": rooms,
                "ach": round(ach, 1),
                "description": f"Auto AHU for deck {deck}",
            }
        )
    return hvac


def _cross_zone_links(
    digest: ShipDigest,
    hvac_zones: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if digest.cross_zone_hints:
        return [
            {
                "from": h.from_,
                "to": h.to,
                "flow_rate_m3h": float(h.flow_rate_m3h),
                "path": h.path,
                "is_hvac_ducted": bool(h.is_hvac_ducted),
                "description": h.description
                or f"Cross-link {h.from_} → {h.to}",
            }
            for h in digest.cross_zone_hints
        ]

    links: list[dict[str, Any]] = []
    ids = [z["id"] for z in hvac_zones]
    for i in range(len(ids) - 1):
        links.append(
            {
                "from": ids[i],
                "to": ids[i + 1],
                "flow_rate_m3h": DEFAULT_CROSS_FLOW,
                "path": f"ladder_well_{i + 1}",
                "is_hvac_ducted": False,
                "description": "Auto ladder-well coupling between adjacent AHU branches",
            }
        )
    return links


def synthesize(
    *,
    workdir: str,
    output_dir: str,
    platform_id: str | None = None,
    allowed_roots: tuple[str, ...],
    copy_graphics: bool = True,
    require_approved: bool = False,
) -> dict[str, Any]:
    """Build spatial_layout.json + air_flow_paths.json from approved overlays."""
    digest = load_digest(workdir, allowed_roots=allowed_roots)
    manifest = load_manifest(workdir, allowed_roots=allowed_roots)
    pid = (platform_id or digest.platform_id).strip().lower().replace("-", "_")
    digest.platform_id = pid

    overlays_dir = os.path.join(workdir, "overlays")
    overlay_files = discover_approved_overlays(overlays_dir)
    if require_approved:
        approved_only = [
            (p, path) for p, path in overlay_files if path.endswith("_approved.svg")
        ]
        if not approved_only:
            raise RuntimeError(
                "require_approved set but no page_*_approved.svg overlays found"
            )
        overlay_files = approved_only
    if not overlay_files:
        raise RuntimeError(
            "no overlay SVGs found; run digest (draft) or export approved SVGs"
        )

    pages = {int(p["page"]): p for p in manifest.get("pages", [])}
    zone_meta = digest.zone_by_id()
    polys: list[OverlayPolygon] = []
    svg_hashes: dict[str, str] = {}

    for page_num, svg_path in overlay_files:
        with validated_open(
            svg_path, "r", allowed_roots=allowed_roots, encoding="utf-8"
        ) as fh:
            text = fh.read()
        svg_hashes[os.path.basename(svg_path)] = hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()
        for poly in read_overlay_svg(text, page=page_num):
            polys.append(poly)

    if not polys:
        raise RuntimeError("approved/draft SVGs contained no named zone polygons")

    # Deduplicate zone ids (last wins) while preserving order
    ordered: list[OverlayPolygon] = []
    seen_ids: set[str] = set()
    for poly in reversed(polys):
        if poly.zone_id in seen_ids:
            continue
        seen_ids.add(poly.zone_id)
        ordered.append(poly)
    ordered.reverse()

    berthing = [
        p.zone_id
        for p in ordered
        if (zone_meta.get(p.zone_id) and zone_meta[p.zone_id].type == "Room")
        or "berth" in p.zone_id.lower()
        or "quarter" in p.zone_id.lower()
    ]
    if not berthing:
        raise RuntimeError(
            "synthesis requires at least one Room/berthing zone "
            "(type Room or id containing Berth/Quarter)"
        )

    # Contam level elevations: digest decks or stable stack by first-seen deck
    deck_elev: dict[str, float] = {}
    for i, deck_info in enumerate(digest.decks):
        if deck_info.elevation_m is not None:
            deck_elev[deck_info.id] = float(deck_info.elevation_m)
        else:
            deck_elev[deck_info.id] = float(i) * float(digest.ceiling_height_m)
    deck_order: list[str] = []

    zones_out: list[dict[str, Any]] = []
    for poly in ordered:
        meta = zone_meta.get(poly.zone_id)
        page_meta = pages.get(poly.page or 1) or next(iter(pages.values()))
        geom = _zone_geometry(poly, meta, digest, page_meta)
        if geom["volume_m3"] <= 0:
            raise RuntimeError(f"zone {poly.zone_id} has non-positive volume")
        ztype = meta.type if meta else "Free"
        traffic = meta.traffic if meta else "medium"
        deck = meta.deck if meta else f"page_{poly.page or 1}"
        if deck not in deck_order:
            deck_order.append(deck)
            deck_elev.setdefault(
                deck, float(len(deck_order) - 1) * float(digest.ceiling_height_m)
            )
        elev = float(deck_elev.get(deck, 0.0))
        if meta and meta.elevation_m is not None:
            elev = float(meta.elevation_m)
        entry: dict[str, Any] = {
            "id": poly.zone_id,
            "type": ztype,
            "traffic": traffic,
            "volume_m3": geom["volume_m3"],
            "floor_area_m2": geom["floor_area_m2"],
            "ceiling_height_m": geom["ceiling_height_m"],
            "elevation_m": elev,
            "deck": deck,
            "display": geom["display"],
        }
        if meta and meta.max_occupancy:
            entry["max_occupancy"] = int(meta.max_occupancy)
        if meta and meta.notes:
            entry["description"] = meta.notes
        zones_out.append(entry)

    graywater = list(digest.graywater_zones)
    zone_ids = [z["id"] for z in zones_out]
    graywater = [g for g in graywater if g in zone_ids]
    if not graywater:
        for cand in ("Engine_Room", "Machinery_Space"):
            if cand in zone_ids:
                graywater = [cand]
                break
        if not graywater and zone_ids:
            # Prefer engineering type
            for z in zones_out:
                if z["type"] == "Engineering":
                    graywater = [z["id"]]
                    break
            if not graywater:
                graywater = [zone_ids[-1]]

    spatial: dict[str, Any] = {
        "platform": pid,
        "description": digest.description
        or digest.class_name
        or f"Naval platform imported from general arrangements ({pid})",
        "isolation_unit_capacity": int(digest.isolation_unit_capacity),
        "deck_dimensions": {
            "length_m": float(digest.length_m),
            "beam_m": float(digest.beam_m),
        },
        "graywater_zones": graywater,
        "zones": zones_out,
    }

    hvac_zones = _auto_hvac(digest, zone_ids, zone_meta)
    airflow: dict[str, Any] = {
        "platform": pid,
        "description": f"HVAC network synthesized for {pid}",
        "oa_fraction": 0.2,
        "hvac_duty": 0.5,
        "hvac_zones": hvac_zones,
        "cross_zone_links": _cross_zone_links(digest, hvac_zones),
        "adjacency": _adjacency_from_polygons(ordered, digest),
    }

    prepare_output_directory(output_dir, allowed_roots=allowed_roots)
    spatial_path = resolve_child_path(output_dir, "spatial_layout.json")
    airflow_path = resolve_child_path(output_dir, "air_flow_paths.json")
    _write_json(spatial_path, spatial, allowed_roots=allowed_roots)
    _write_json(airflow_path, airflow, allowed_roots=allowed_roots)

    digest_path = resolve_child_path(workdir, "ship_digest.json")
    provenance = {
        "schema_version": "1.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "platform_id": pid,
        "workdir": workdir,
        "digest_sha256": _sha256_file(digest_path, allowed_roots=allowed_roots),
        "svg_sha256": svg_hashes,
        "overlay_mode": (
            "approved"
            if any(p.endswith("_approved.svg") for _, p in overlay_files)
            else "draft"
        ),
        "zone_count": len(zones_out),
        "berthing_zones": berthing,
    }
    meta_file = os.path.join(workdir, "digest_meta.json")
    if os.path.isfile(meta_file):
        with validated_open(
            meta_file, "r", allowed_roots=allowed_roots, encoding="utf-8"
        ) as fh:
            provenance["digest_meta"] = json.load(fh)
    _write_json(
        resolve_child_path(output_dir, "import_provenance.json"),
        provenance,
        allowed_roots=allowed_roots,
    )

    if copy_graphics and pages:
        graphics_dir = os.path.join(output_dir, "graphics")
        prepare_output_directory(graphics_dir, allowed_roots=allowed_roots)
        # Prefer first page as plan overview
        first = pages[min(pages)]
        src = os.path.join(workdir, first["file"])
        dest_name = "plan_overview.png"
        dest = resolve_child_path(graphics_dir, dest_name)
        shutil.copy2(src, dest)
        graphics_json = {
            "schema_version": "1.0",
            "description": "Blueprint plates copied from naval GA import workdir",
            "plan": {
                "file": dest_name,
                "style": "general_arrangement_scan",
                "credit": "Imported via tools.ship_blueprint_import",
                "license": "Source drawing rights remain with original owner",
            },
            "deck_plans": {},
        }
        _write_json(
            resolve_child_path(graphics_dir, "graphics.json"),
            graphics_json,
            allowed_roots=allowed_roots,
        )

    return {
        "platform_id": pid,
        "output_dir": output_dir,
        "spatial_layout": spatial_path,
        "air_flow_paths": airflow_path,
        "zone_count": len(zones_out),
        "provenance": provenance,
    }
