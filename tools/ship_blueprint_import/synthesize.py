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
from tools.ship_blueprint_import.models import (
    HvacHint,
    ShipDigest,
    ZoneDigest,
)
from tools.ship_blueprint_import.ontology import ach_for_zone_type
from tools.ship_blueprint_import.svg_io import (
    OverlayPolygon,
    polygons_touch,
    read_overlay_svg,
)
from tools.ship_blueprint_import.systems import infer_systems, write_systems_notes

DEFAULT_CROSS_FLOW = 50.0
APPROVED_OVERLAY_SUFFIX = "_approved.svg"

# Sanitary hardware constants mirror engines/transmission_core.py (and
# scripts/derive_sanitary_provisioning.py): test_shared_sanitary_zones pins
# these values against the engine's derived ratio on every platform.
SANITARY_AREA_M2_PER_WC = 2.7
SANITARY_CEILING_M = 2.3
SANITARY_EXHAUST_M3H_PER_WC = 118.9
SANITARY_ACH = SANITARY_EXHAUST_M3H_PER_WC / (
    SANITARY_AREA_M2_PER_WC * SANITARY_CEILING_M
)


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
        if name.endswith(APPROVED_OVERLAY_SUFFIX):
            approved.append((page_num, path))
        elif name.endswith("_draft.svg"):
            drafts.append((page_num, path))
    return approved if approved else drafts


def _plan_maps(
    digest: ShipDigest,
) -> dict[str, tuple[int, list[float], list[float], list[float]]]:
    """deck id → (page, plan_bbox_norm, hull_x_span_m, hull_y_span_m).

    DeckInfo.plan_bbox_norm marks the drawn deck-plan region inside a sheet
    (pages carry title blocks/margins and can stack several deck views);
    hull spans say which metres of hull that region covers. Absent fields
    mean "the whole page is the whole hull" — the legacy mapping.
    """
    out: dict[str, tuple[int, list[float], list[float], list[float]]] = {}
    for deck in digest.decks:
        bbox = deck.plan_bbox_norm or [0.0, 0.0, 1.0, 1.0]
        x_span = deck.hull_x_span_m or [0.0, digest.length_m]
        y_span = deck.hull_y_span_m or [0.0, digest.beam_m]
        out[deck.id] = (int(deck.page), bbox, x_span, y_span)
    return out


def _zone_geometry(
    poly: OverlayPolygon,
    zone_meta: ZoneDigest | None,
    digest: ShipDigest,
    page_meta: dict[str, Any],
    plan_map: tuple[list[float], list[float], list[float]] | None,
) -> dict[str, Any]:
    w = max(int(page_meta["width"]), 1)
    h = max(int(page_meta["height"]), 1)
    if plan_map is None:
        # Fall back to the map of the first deck drawn on this page, else the
        # full page (legacy behaviour).
        bbox, x_span, y_span = (
            [0.0, 0.0, 1.0, 1.0],
            [0.0, digest.length_m],
            [0.0, digest.beam_m],
        )
        for deck in digest.decks:
            if int(deck.page) == poly.page:
                bbox = deck.plan_bbox_norm or bbox
                x_span = deck.hull_x_span_m or x_span
                y_span = deck.hull_y_span_m or y_span
                break
    else:
        _page, bbox, x_span, y_span = plan_map
    bw = max((bbox[2] - bbox[0]) * w, 1e-6)
    bh = max((bbox[3] - bbox[1]) * h, 1e-6)
    mx = max(x_span[1] - x_span[0], 1e-6) / bw
    my = max(y_span[1] - y_span[0], 1e-6) / bh
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
    rel_x = (cx - bbox[0] * w) / bw
    rel_y = (cy - bbox[1] * h) / bh
    display_x = x_span[0] + rel_x * (x_span[1] - x_span[0])
    display_y = y_span[0] + rel_y * (y_span[1] - y_span[0])
    return {
        "floor_area_m2": round(area_m2, 2),
        "ceiling_height_m": ceiling,
        "volume_m3": round(volume, 2),
        "display": {"x": round(display_x, 2), "y": round(display_y, 2)},
    }


def _add_edge(
    edges: list[dict[str, str]],
    seen: set[tuple[str, str]],
    a: str,
    b: str,
    typ: str,
) -> None:
    key = tuple(sorted((a, b)))
    if key in seen or a == b:
        return
    seen.add(key)
    edges.append({"from": a, "to": b, "type": typ})


def _add_touching_pairs(
    edges: list[dict[str, str]],
    seen: set[tuple[str, str]],
    group: list[OverlayPolygon],
) -> None:
    for i, a in enumerate(group):
        for b in group[i + 1 :]:
            if polygons_touch(a.points, b.points):
                _add_edge(edges, seen, a.zone_id, b.zone_id, "passageway")


def _adjacency_from_polygons(
    polys: list[OverlayPolygon],
    digest: ShipDigest,
) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for hint in digest.adjacency_hints:
        _add_edge(edges, seen, hint.from_, hint.to, hint.type or "passageway")

    # Same-page proximity
    by_page: dict[int | None, list[OverlayPolygon]] = {}
    for p in polys:
        by_page.setdefault(p.page, []).append(p)
    for group in by_page.values():
        _add_touching_pairs(edges, seen, group)

    return edges


def _hint_group(hint: HvacHint, rooms: list[str]) -> dict[str, Any]:
    group: dict[str, Any] = {
        "id": hint.id,
        "rooms": rooms,
        "ach": float(hint.ach),
        "description": hint.description or f"AHU branch {hint.id}",
    }
    if hint.oa_fraction is not None:
        group["oa_fraction"] = float(hint.oa_fraction)
    if hint.filter_preset is not None:
        group["filter_preset"] = hint.filter_preset
    return group


def _hvac_from_hints(
    digest: ShipDigest, ducted: list[str]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for hint in digest.hvac_hints:
        rooms = [r for r in hint.rooms if r in ducted]
        if rooms:
            out.append(_hint_group(hint, rooms))
    return out


def _auto_hvac(
    digest: ShipDigest,
    zone_ids: list[str],
    zone_meta: dict[str, ZoneDigest],
    head_ids: set[str],
) -> list[dict[str, Any]]:
    ducted = [z for z in zone_ids if z not in head_ids]
    if digest.hvac_hints:
        hinted = _hvac_from_hints(digest, ducted)
        if hinted:
            return hinted

    # Group by deck
    by_deck: dict[str, list[str]] = {}
    for zid in ducted:
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


def _head_branch_groups(
    head_ids: list[str],
    zones_out: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """One exhaust-only AHU per head; makeup air comes from the served branch."""
    by_id = {z["id"]: z for z in zones_out}
    groups: list[dict[str, Any]] = []
    for zid in head_ids:
        wc = max(
            1,
            round(by_id[zid]["floor_area_m2"] / SANITARY_AREA_M2_PER_WC),
        )
        groups.append(
            {
                "id": f"AHU_HD_{zid}",
                "rooms": [zid],
                "ach": round(SANITARY_ACH, 1),
                "oa_fraction": 1.0,
                "hvac_duty": 0.0,
                "description": (
                    f"Exhaust-only sanitary branch ({zid}, {wc} WC); makeup "
                    "air enters from the served space's branch and leaves "
                    "overboard."
                ),
            }
        )
    return groups


def _head_makeup_links(
    head_ids: list[str],
    zones_out: list[dict[str, Any]],
    hvac_zones: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """One directional Sanitary_Makeup link into each head's branch.

    The source is the non-head group covering the most of the head's served
    zones, else the group covering most same-deck rooms, else the first
    sorted branch — heads never source air themselves.
    """
    zones_by_id = {z["id"]: z for z in zones_out}
    branches = [
        g for g in hvac_zones if not str(g["id"]).startswith("AHU_HD_")
    ]
    links: list[dict[str, Any]] = []
    if not branches:
        return links
    for zid in head_ids:
        head = zones_by_id[zid]
        serves = set(head.get("serves", []))
        scored = sorted(
            branches,
            key=lambda g, serves=serves: (
                -len(serves & set(g.get("rooms", []))), str(g["id"]),
            ),
        )
        if serves & set(scored[0].get("rooms", [])):
            source = str(scored[0]["id"])
        else:
            deck_no = str(head.get("deck", "")).split("_")[0]
            same_deck = {
                z["id"]
                for z in zones_out
                if str(z.get("deck", "")).split("_")[0] == deck_no
            }
            scored = sorted(
                branches,
                key=lambda g, same_deck=same_deck: (
                    -len(same_deck & set(g.get("rooms", []))),
                    str(g["id"]),
                ),
            )
            source = str(scored[0]["id"])
        wc = max(
            1,
            round(head["floor_area_m2"] / SANITARY_AREA_M2_PER_WC),
        )
        links.append(
            {
                "from": source,
                "to": f"AHU_HD_{zid}",
                "flow_rate_m3h": round(wc * SANITARY_EXHAUST_M3H_PER_WC, 1),
                "is_hvac_ducted": False,
                "path": "Sanitary_Makeup",
                "description": (
                    f"Transfer air into {zid}; the head exhausts overboard, "
                    "never back to the served space."
                ),
            }
        )
    return links


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
    # Exhaust-only head branches carry no ladder-well chain: a head never
    # sources air and its only inbound edge is a Sanitary_Makeup link.
    ids = [
        z["id"] for z in hvac_zones if not str(z["id"]).startswith("AHU_HD_")
    ]
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


def _select_overlay_files(
    workdir: str,
    require_approved: bool,
) -> list[tuple[int, str]]:
    overlays_dir = os.path.join(workdir, "overlays")
    overlay_files = discover_approved_overlays(overlays_dir)
    if require_approved:
        approved_only = [
            (p, path)
            for p, path in overlay_files
            if path.endswith(APPROVED_OVERLAY_SUFFIX)
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
    return overlay_files


def _load_overlay_polys(
    overlay_files: list[tuple[int, str]],
    allowed_roots: tuple[str, ...],
) -> tuple[list[OverlayPolygon], dict[str, str]]:
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
        polys.extend(read_overlay_svg(text, page=page_num))
    return polys, svg_hashes


def _dedupe_polys(polys: list[OverlayPolygon]) -> list[OverlayPolygon]:
    """Deduplicate zone ids (last wins) while preserving order."""
    ordered: list[OverlayPolygon] = []
    seen_ids: set[str] = set()
    for poly in reversed(polys):
        if poly.zone_id in seen_ids:
            continue
        seen_ids.add(poly.zone_id)
        ordered.append(poly)
    ordered.reverse()
    return ordered


def _berthing_zones(
    ordered: list[OverlayPolygon],
    zone_meta: dict[str, ZoneDigest],
) -> list[str]:
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
    return berthing


def _zone_entry(
    poly: OverlayPolygon,
    zone_meta: dict[str, ZoneDigest],
    digest: ShipDigest,
    pages: dict[int, dict[str, Any]],
    deck_elev: dict[str, float],
    deck_order: list[str],
    plan_maps: dict[str, tuple[int, list[float], list[float], list[float]]],
) -> dict[str, Any]:
    meta = zone_meta.get(poly.zone_id)
    page_num = poly.page or 1
    page_meta = pages.get(page_num) or next(iter(pages.values()))
    plan_map = plan_maps.get(meta.deck) if meta else None
    geom = _zone_geometry(poly, meta, digest, page_meta, plan_map)
    if geom["volume_m3"] <= 0:
        raise RuntimeError(f"zone {poly.zone_id} has non-positive volume")
    ztype = meta.type if meta else "Free"
    traffic = meta.traffic if meta else "medium"
    deck = meta.deck if meta else f"page_{page_num}"
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
    if meta and meta.serves:
        entry["serves"] = list(meta.serves)
    if meta and meta.notes:
        entry["description"] = meta.notes
    if ztype == "Sanitary":
        # Heads carry fixture-geometry: the ceiling is the MLC headroom
        # figure, volume follows floor area, and the exhaust ACH is the
        # hardware-derived constant — test_shared_sanitary_zones enforces
        # the wiring on every platform.
        wc = max(1, round(entry["floor_area_m2"] / SANITARY_AREA_M2_PER_WC))
        entry["ceiling_height_m"] = SANITARY_CEILING_M
        entry["volume_m3"] = round(
            entry["floor_area_m2"] * SANITARY_CEILING_M, 2
        )
        entry["base_ach"] = round(SANITARY_ACH, 1)
        entry["max_occupancy"] = wc
    return entry


def _zones_from_polys(
    ordered: list[OverlayPolygon],
    zone_meta: dict[str, ZoneDigest],
    digest: ShipDigest,
    pages: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    # Contam level elevations: digest decks or stable stack by first-seen deck
    deck_elev: dict[str, float] = {}
    for i, deck_info in enumerate(digest.decks):
        if deck_info.elevation_m is not None:
            deck_elev[deck_info.id] = float(deck_info.elevation_m)
        else:
            deck_elev[deck_info.id] = float(i) * float(digest.ceiling_height_m)
    deck_order: list[str] = []

    plan_maps = _plan_maps(digest)
    return [
        _zone_entry(
            poly, zone_meta, digest, pages, deck_elev, deck_order, plan_maps
        )
        for poly in ordered
    ]


def _graywater_zones(
    digest: ShipDigest,
    zones_out: list[dict[str, Any]],
    zone_ids: list[str],
) -> list[str]:
    graywater = [g for g in digest.graywater_zones if g in zone_ids]
    if graywater:
        return graywater
    for cand in ("Engine_Room", "Machinery_Space"):
        if cand in zone_ids:
            return [cand]
    if zone_ids:
        # Prefer engineering type
        for z in zones_out:
            if z["type"] == "Engineering":
                return [z["id"]]
        return [zone_ids[-1]]
    return []


def _copy_plan_graphics(
    workdir: str,
    output_dir: str,
    pages: dict[int, dict[str, Any]],
    allowed_roots: tuple[str, ...],
) -> None:
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


def _zone_geometry_bundle(
    digest: ShipDigest,
    polys: list,
    zone_meta: dict,
    pages: dict,
) -> tuple[list, list[str], list[dict], list[str], list[str], set[str], list[str]]:
    ordered = _dedupe_polys(polys)
    berthing = _berthing_zones(ordered, zone_meta)
    zones_out = _zones_from_polys(ordered, zone_meta, digest, pages)
    zone_ids = [z["id"] for z in zones_out]
    head_ids = [z["id"] for z in zones_out if z["type"] == "Sanitary"]
    head_set = set(head_ids)
    graywater = [
        g for g in _graywater_zones(digest, zones_out, zone_ids)
        if g not in head_set
    ]
    return ordered, berthing, zones_out, zone_ids, head_ids, head_set, graywater


def _spatial_layout_doc(
    pid: str, digest: ShipDigest, zones_out: list[dict], graywater: list[str],
) -> dict[str, Any]:
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
    if (
        digest.complement
        and digest.complement.passengers > 0
        and digest.complement.crew > 0
    ):
        spatial["nominal_complement"] = {
            "passengers": int(digest.complement.passengers),
            "crew": int(digest.complement.crew),
        }
    return spatial


def _airflow_layout_doc(
    pid: str,
    digest: ShipDigest,
    ordered: list,
    zones_out: list[dict],
    zone_ids: list[str],
    head_ids: list[str],
    head_set: set[str],
    zone_meta: dict,
) -> dict[str, Any]:
    hvac_zones = _auto_hvac(digest, zone_ids, zone_meta, head_set)
    hvac_zones += _head_branch_groups(head_ids, zones_out)
    return {
        "platform": pid,
        "description": f"HVAC network synthesized for {pid}",
        "oa_fraction": 0.2,
        "hvac_duty": 0.5,
        "hvac_zones": hvac_zones,
        "cross_zone_links": _cross_zone_links(digest, hvac_zones)
        + _head_makeup_links(head_ids, zones_out, hvac_zones),
        "adjacency": [
            e
            for e in _adjacency_from_polygons(ordered, digest)
            if e["from"] not in head_set and e["to"] not in head_set
        ],
    }


def synthesize(
    *,
    workdir: str,
    output_dir: str,
    platform_id: str | None = None,
    allowed_roots: tuple[str, ...],
    copy_graphics: bool = True,
    require_approved: bool = False,
    source_credit: str | None = None,
) -> dict[str, Any]:
    """Build spatial_layout.json + air_flow_paths.json from approved overlays."""
    digest = load_digest(workdir, allowed_roots=allowed_roots)
    manifest = load_manifest(workdir, allowed_roots=allowed_roots)
    pid = (platform_id or digest.platform_id).strip().lower().replace("-", "_")
    digest.platform_id = pid

    overlay_files = _select_overlay_files(workdir, require_approved)

    pages = {int(p["page"]): p for p in manifest.get("pages", [])}
    zone_meta = digest.zone_by_id()
    polys, svg_hashes = _load_overlay_polys(overlay_files, allowed_roots)

    if not polys:
        raise RuntimeError("approved/draft SVGs contained no named zone polygons")

    ordered, berthing, zones_out, zone_ids, head_ids, head_set, graywater = (
        _zone_geometry_bundle(digest, polys, zone_meta, pages)
    )
    spatial = _spatial_layout_doc(pid, digest, zones_out, graywater)
    airflow = _airflow_layout_doc(
        pid, digest, ordered, zones_out, zone_ids, head_ids, head_set, zone_meta,
    )

    systems_notes_path: str | None = None
    if digest.systems is not None:
        # Era-typed systems inference: sheet-read vent markers and tank labels
        # enrich the airflow groups (vent_mode/evidence/oa_fraction) and record
        # every step in systems_notes.{json,md} with its evidence grade.
        declared_oa = {
            h.id for h in digest.hvac_hints if h.oa_fraction is not None
        }
        airflow, systems_notes, sewage_ids = infer_systems(
            digest, zones_out, airflow, declared_oa
        )
        sewage_ids = [s for s in sewage_ids if s not in head_set]
        if sewage_ids:
            graywater += [s for s in sewage_ids if s not in graywater]
            spatial["graywater_zones"] = graywater
        write_systems_notes(
            output_dir,
            systems_notes,
            allowed_roots=allowed_roots,
            source_credit=source_credit,
        )
        systems_notes_path = resolve_child_path(output_dir, "systems_notes.json")

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
        **({"source_credit": source_credit} if source_credit else {}),
        "workdir": workdir,
        "digest_sha256": _sha256_file(digest_path, allowed_roots=allowed_roots),
        "svg_sha256": svg_hashes,
        "overlay_mode": (
            "approved"
            if any(p.endswith(APPROVED_OVERLAY_SUFFIX) for _, p in overlay_files)
            else "draft"
        ),
        "zone_count": len(zones_out),
        "berthing_zones": berthing,
    }
    if digest.systems is not None:
        provenance["systems_era"] = digest.systems.era
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
        _copy_plan_graphics(workdir, output_dir, pages, allowed_roots)

    crew_manifest_path: str | None = None
    if digest.complement:
        crew_manifest_path = _write_crew_manifest(
            digest, output_dir, allowed_roots
        )

    return {
        "platform_id": pid,
        "output_dir": output_dir,
        "spatial_layout": spatial_path,
        "air_flow_paths": airflow_path,
        "crew_manifest": crew_manifest_path,
        "systems_notes": systems_notes_path,
        "zone_count": len(zones_out),
        "provenance": provenance,
    }


def _write_crew_manifest(
    digest: ShipDigest,
    output_dir: str,
    allowed_roots: tuple[str, ...],
) -> str:
    """Emit crew_manifest.json — the proposed class-level complement."""
    assert digest.complement is not None  # guarded by caller
    comp = digest.complement
    zone_ids = {z.id for z in digest.zones}
    manifest_rows = []
    for row in comp.manifest:
        notes = list(filter(None, [row.notes]))
        if row.berth_zone and row.berth_zone not in zone_ids:
            notes.append(f"berth_zone '{row.berth_zone}' not a digest zone")
        if row.duty_zone and row.duty_zone not in zone_ids:
            notes.append(f"duty_zone '{row.duty_zone}' not a digest zone")
        manifest_rows.append(
            {
                "class_id": row.class_id,
                "role_group": row.role_group,
                "count": int(row.count),
                "berth_zone": row.berth_zone,
                "duty_zone": row.duty_zone,
                "notes": "; ".join(notes),
            }
        )
    declared = comp.passengers + comp.crew
    listed = sum(int(r.count) for r in comp.manifest)
    payload = {
        "schema_version": "1.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "platform": digest.platform_id,
        "description": (
            "Proposed crew manifest from GA import — class-level complement "
            "split with berth/duty zones. Engineers adjust before run configs "
            "consume it; nominal_complement in spatial_layout.json is the "
            "machine-read summary."
        ),
        "nominal_complement": {
            "passengers": int(comp.passengers),
            "crew": int(comp.crew),
        },
        "manifest": manifest_rows,
        "source": comp.source,
        "consistency": {
            "declared_total": declared,
            "manifest_total": listed,
            "matches": declared == listed,
        },
        "generated_by": "tools.ship_blueprint_import.synthesize",
    }
    path = resolve_child_path(output_dir, "crew_manifest.json")
    _write_json(path, payload, allowed_roots=allowed_roots)
    return path
