#!/usr/bin/env python3
"""
museum_hull_audit.py – museum/GA hull divergence audit (CONTAM-MUSEUM-01)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mechanically classifies each platform's committed ``spatial_layout.json`` +
``air_flow_paths.json`` (and ``contam/platform.prj`` where present) against
the three questions the museum-hull divergence audit poses:

- **Q1 missing-geometry mistakes**: hvac/adjacency/cross-zone references to
  zone ids that do not exist; zones with volume but zero declared airflow
  incidence (unreachable compartments); hvac groups whose rooms are all
  missing; systems-notes zones absent from the layout (and vice versa);
  committed-prj zone/volume drift vs the JSON.
- **Q2 dead-end topology**: per-engine directed zone graphs. *Native* uses
  the edges ``ContamTransportEngine`` actually builds (star topology with
  ``hvac_duty`` gating — duty-0 groups emit no legs, so rooms fed only by
  transfer links become sinks). *ContamX (export)* uses the commissioned
  ``path_map`` the fleet sweep solved (duty-0 groups emit return legs that
  drain via the exhaust AHS). *ContamX (committed)* parses the authentic
  prj topology. Per real zone: ``sink`` (inflow, no outflow), ``orphan``
  (no edges), ``unreachable`` (not reachable from the sweep injection
  zone), ``dead`` = union. Dead-zone fractions are correlated against the
  committed fleet-compare ``mean_l1`` column (Spearman).
- **Q3 HVAC declaration coverage**: top-level ``hvac_duty`` /
  ``oa_fraction``, per-group duty/ACH distributions, per-group
  ``oa_fraction`` / ``filter_efficiency`` / ``nbc_filter_*`` coverage, and
  committed-prj ``ach=`` annotations vs the JSON-declared ACH.

ContamX orifice paths are treated as bidirectional (a pressure-driven
orifice flows either way); fan/AHS legs and ambient links are directed.

Usage::

    python3 tools/museum_hull_audit.py                    # every platform
    python3 tools/museum_hull_audit.py --platforms gordon_gunter_r338
    python3 tools/museum_hull_audit.py \
        --out telemetry_buffer/museum_hull_audit \
        --md-out docs/museum_hull_audit_table.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engines.py_contam_bridge import (  # noqa: E402
    ContamTransportEngine,
)
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)
from tools.contam_hobbyist import load_hobbyist_overrides  # noqa: E402
from tools.contam_prj_bridge import export_prj_with_path_map  # noqa: E402
from tools.contamw34_prj import (  # noqa: E402
    _is_phantom_zone,
    _section_blocks,
    path_map_from_prj,
    prj_zone_aliases,
)

PLATFORMS_DIR = "data/platforms"
PRJ_REL_PATH = os.path.join("contam", "platform.prj")
_DEFAULT_TABLE = "docs/contam_fleet_compare_table.md"

# Hulls named in the audit brief: the union of both divergence tails, the
# no-committed-prj hulls, the sane counterexamples, and degenerate olympia.
AUDIT_SET = [
    "gordon_gunter_r338", "enterprise_galaxy_tng", "castle_class_corvette",
    "fletcher_class_destroyer", "pt_564", "cannon_de701", "lexington_cv2",
    "saratoga_cv3", "legend_class_nsc", "spirit_cruise_3000", "apl_24",
    "winnipeg_j337", "esteem_mso438", "river_class_frigate",
    "expedition_cruise_300", "messy_cruise_500",
    "san_antonio_class_lpd", "erie_pg50", "olympia_c6",
]

# Hand-authored cruise hulls — the "tuned" convention museum hulls are
# compared against for Q3.
CRUISE_REFERENCE = [
    "classic_cruise_1900", "expedition_cruise_300", "expedition_cruise_450",
    "messy_cruise_500", "mega_cruise_5000", "spirit_cruise_3000",
]


# ── loading ─────────────────────────────────────────────────────────────


def _load_json(path: str) -> dict[str, Any]:
    with validated_open(path, "r", allowed_roots=(REPO_ROOT,),
                        encoding="utf-8") as fh:
        return json.load(fh)


def _platform_dirs(root: str) -> list[str]:
    base = os.path.join(REPO_ROOT, root)
    return sorted(
        d for d in os.listdir(base)
        if os.path.isdir(os.path.join(base, d))
        and os.path.exists(os.path.join(base, d, "air_flow_paths.json"))
    )


def _zone_map(spatial: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {z["id"]: z for z in spatial.get("zones", [])}


def _hvac_room_refs(airflow: dict[str, Any]) -> dict[str, list[str]]:
    return {
        g["id"]: list(g.get("rooms", []))
        for g in airflow.get("hvac_zones", [])
    }


# ── Q1: missing-geometry mistakes ───────────────────────────────────────


def _referenced_zone_ids(airflow: dict[str, Any]) -> set[str]:
    """Zone ids the airflow JSON references that must exist in layout."""
    refs: set[str] = set()
    for g in airflow.get("hvac_zones", []):
        refs.update(g.get("rooms", []))
    for adj in airflow.get("adjacency", []):
        refs.add(adj["from"])
        refs.add(adj["to"])
    return refs


def _resolve_link_rooms(token: str, airflow: dict[str, Any],
                        zone_ids: set[str]) -> list[str]:
    """Mirror ContamTransportEngine._get_zone_rooms + export _endpoint_rooms."""
    for g in airflow.get("hvac_zones", []):
        if g["id"] == token:
            return [r for r in g.get("rooms", []) if r in zone_ids]
    return [token] if token in zone_ids else []


def _orphan_zones(spatial: dict[str, Any],
                  airflow: dict[str, Any]) -> list[str]:
    """Volume-bearing zones with zero declared airflow incidence."""
    zones = _zone_map(spatial)
    touched: set[str] = set()
    for g in airflow.get("hvac_zones", []):
        touched.update(r for r in g.get("rooms", []) if r in zones)
    for adj in airflow.get("adjacency", []):
        touched.update({adj["from"], adj["to"]} & set(zones))
    zone_ids = set(zones)
    for link in airflow.get("cross_zone_links", []):
        touched.update(_resolve_link_rooms(link["from"], airflow, zone_ids))
        touched.update(_resolve_link_rooms(link["to"], airflow, zone_ids))
    return sorted(
        zid for zid, z in zones.items()
        if zid not in touched and float(z.get("volume_m3", 0.0)) > 0.0
    )


def audit_q1(platform_dir: str, spatial: dict[str, Any],
             airflow: dict[str, Any]) -> dict[str, Any]:
    """Missing-geometry flags for one platform."""
    zones = _zone_map(spatial)
    refs = _referenced_zone_ids(airflow)
    hvac_refs = _hvac_room_refs(airflow)
    out: dict[str, Any] = {
        "missing_zone_refs": sorted(refs - set(zones)),
        "hvac_groups_all_rooms_missing": sorted(
            gid for gid, rooms in hvac_refs.items()
            if rooms and not [r for r in rooms if r in zones]
        ),
        "orphan_zones": _orphan_zones(spatial, airflow),
        "dangling_xzone_endpoints": sorted(
            f"{link['from']}->{link['to']}"
            for link in airflow.get("cross_zone_links", [])
            if not _resolve_link_rooms(link["from"], airflow, set(zones))
            or not _resolve_link_rooms(link["to"], airflow, set(zones))
        ),
        # Links whose endpoints are bare room ids (not HVAC group ids).
        # Pre-CONTAM-XZONE-01 the native engine silently dropped these
        # (~45 links on 10 hulls); it now resolves them like the export
        # lane and raises on endpoints that are neither group nor room.
        "room_id_xzone_endpoints": sorted(
            f"{link['from']}->{link['to']}"
            for link in airflow.get("cross_zone_links", [])
            if any(
                ep in zones
                and ep not in {g["id"] for g in airflow.get("hvac_zones", [])}
                for ep in (link["from"], link["to"])
            )
        ),
    }
    out.update(_provenance_q1(platform_dir, zones))
    out.update(_prj_zone_diff(platform_dir, zones))
    return out


def _provenance_q1(platform_dir: str,
                   zones: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """GA-source-record checks: systems_notes coverage + digest zone count."""
    result: dict[str, Any] = {"provenance_absent": True}
    notes_path = os.path.join(platform_dir, "systems_notes.json")
    if os.path.exists(notes_path):
        result["provenance_absent"] = False
        noted = set((_load_json(notes_path).get("zone_modes") or {}))
        result["notes_only_zones"] = sorted(noted - set(zones))
        result["unnoted_zones"] = sorted(set(zones) - noted)
    prov_path = os.path.join(platform_dir, "import_provenance.json")
    if os.path.exists(prov_path):
        result["provenance_absent"] = False
        digest_n = _load_json(prov_path).get("zone_count")
        result["digest_zone_count"] = digest_n
        result["zone_count_drift"] = (
            digest_n - len(zones) if isinstance(digest_n, int) else None
        )
    return result


def _prj_zone_records(text: str) -> dict[str, float]:
    """Committed prj ``zones`` section → {name: volume} for real zones."""
    sections = dict(_section_blocks(text))
    records: dict[str, float] = {}
    for ln in sections.get("zones", []):
        if ln.strip().startswith("!"):
            continue
        toks = ln.split()
        if len(toks) < 11 or not toks[0].isdigit():
            continue
        name = toks[10]
        if _is_phantom_zone(int(toks[1]), name):
            continue
        try:
            records[name] = float(toks[7])
        except ValueError:
            records[name] = 0.0
    return records


def _prj_zone_diff(platform_dir: str,
                   zones: dict[str, dict[str, Any]]) -> dict[str, Any]:
    prj_path = os.path.join(platform_dir, PRJ_REL_PATH)
    if not os.path.exists(prj_path):
        return {"prj": None}
    prj_zones = _prj_zone_records(
        _read_text(prj_path))
    # Resolve ContamW-mangled prj names to JSON ids (strip/truncate, ContamW
    # ``_N`` dedup, declared post-prj renames); whatever still does not
    # resolve is a genuine prj-only zone.
    overrides = load_hobbyist_overrides(platform_dir)
    aliases = prj_zone_aliases(
        list(prj_zones), list(zones),
        declared_aliases=overrides.get("zone_aliases"),
    )
    resolved = {
        aliases[name]: vol
        for name, vol in prj_zones.items()
    }
    renamed = sorted(
        (aliases[name], name)
        for name in prj_zones
        if aliases[name] != name
    )
    drift = {
        zid: {"json": float(zones[zid].get("volume_m3", 0.0)),
              "prj": vol}
        for zid, vol in resolved.items()
        if zid in zones
        and float(zones[zid].get("volume_m3", 0.0)) > 0
        and abs(vol - float(zones[zid].get("volume_m3", 0.0)))
        / float(zones[zid].get("volume_m3", 0.0)) > 0.10
    }
    return {"prj": {
        "prj_only_zones": sorted(set(resolved) - set(zones)),
        "json_only_zones": sorted(set(zones) - set(resolved)),
        "renamed_zones": renamed,
        "volume_drift_zones": drift,
        "n_prj_zones": len(prj_zones),
    }}


def _read_text(path: str) -> str:
    with validated_open(path, "r", allowed_roots=(REPO_ROOT,),
                        encoding="utf-8") as fh:
        return fh.read()


# ── zone-graph classes (Q2) ─────────────────────────────────────────────


def _contamx_edges(entries: list[dict[str, Any]],
                   zone_ids: set[str]) -> list[tuple[str, str]]:
    """Directed zone graph from a path_map (export or committed prj).

    Non-ducted links between two real zones are passive orifices — treated
    bidirectional. Fan/AHS legs and ambient links stay directed. Zero-flow
    declared terminals (commissioned supply 0 on duty-0 groups) drop out.
    """
    edges: list[tuple[str, str]] = []
    for e in entries:
        flow = e.get("declared_flow_m3h")
        if isinstance(flow, int | float) and flow <= 0.0:
            continue
        frm, to = e["from_zone"], e["to_zone"]
        edges.append((frm, to))
        if (
            not e.get("is_hvac_ducted")
            and e.get("crusher_transfer")
            and frm in zone_ids and to in zone_ids
        ):
            edges.append((to, frm))
    return edges


def _native_edges(engine: ContamTransportEngine) -> list[tuple[str, str]]:
    return [(p.from_zone, p.to_zone) for p in engine.airflow_paths]


def _reachable(edges: list[tuple[str, str]], source: str) -> set[str]:
    out: dict[str, list[str]] = {}
    for frm, to in edges:
        out.setdefault(frm, []).append(to)
    seen = {source}
    queue = [source]
    while queue:
        nxt = []
        for node in queue:
            for dst in out.get(node, []):
                if dst not in seen:
                    seen.add(dst)
                    nxt.append(dst)
        queue = nxt
    return seen


def _zone_classes(zone_ids: set[str], edges: list[tuple[str, str]],
                  injection: str | None) -> dict[str, Any]:
    """sink / orphan / unreachable / dead classification per real zone."""
    in_deg: dict[str, int] = dict.fromkeys(zone_ids, 0)
    out_deg: dict[str, int] = dict.fromkeys(zone_ids, 0)
    for frm, to in edges:
        if to in in_deg:
            in_deg[to] += 1
        if frm in out_deg:
            out_deg[frm] += 1
    sinks = {z for z in zone_ids if in_deg[z] > 0 and out_deg[z] == 0}
    orphans = {z for z in zone_ids if in_deg[z] == 0 and out_deg[z] == 0}
    if injection is None:
        unreachable: set[str] = set()
    else:
        unreachable = set(zone_ids) - _reachable(edges, injection)
    dead = sinks | orphans | unreachable
    return {
        "sinks": sorted(sinks),
        "orphans": sorted(orphans),
        "unreachable": sorted(unreachable),
        "dead": sorted(dead),
        "dead_frac": len(dead) / len(zone_ids) if zone_ids else 0.0,
    }


def _injection_zone(spatial: dict[str, Any],
                    airflow: dict[str, Any]) -> str | None:
    """Same selector as tools/contam_fleet_compare.py._injection_zone."""
    zones = _zone_map(spatial)
    volume = {zid: float(z.get("volume_m3", 0.0)) for zid, z in zones.items()}
    served = {
        r for g in airflow.get("hvac_zones", [])
        for r in g.get("rooms", []) if r in zones
    }
    pool = served or set(zones)
    if not pool:
        return None
    return max(pool, key=lambda zid: volume.get(zid, 0.0))


def audit_q2(platform_dir: str, spatial: dict[str, Any],
             airflow: dict[str, Any]) -> dict[str, Any]:
    """Per-engine dead-zone classes for one platform."""
    zones = _zone_map(spatial)
    zone_ids = set(zones)
    injection = _injection_zone(spatial, airflow)
    out: dict[str, Any] = {"injection_zone": injection, "n_zones": len(zone_ids)}

    # An unresolvable cross-zone endpoint raises in the engine — the
    # audit reports it instead of crashing the fleet run.
    try:
        engine = ContamTransportEngine(
            spatial_layout=dict(spatial), air_flow_paths=dict(airflow),
            filter_efficiency=0.5, natural_decay_rate=0.0,
        )
        out["native"] = _zone_classes(
            zone_ids, _native_edges(engine), injection)
    except ValueError as exc:
        out["native"] = None
        out["native_error"] = str(exc)

    _, entries = export_prj_with_path_map(
        spatial, airflow, ahs_terminal_mode="commissioned")
    out["contamx_export"] = _zone_classes(
        zone_ids, _contamx_edges(entries, zone_ids), injection)

    prj_path = os.path.join(platform_dir, PRJ_REL_PATH)
    if os.path.exists(prj_path):
        # Committed GA prjs mangle zone names to the CONTAMW 15-char field —
        # endpoints are normalized to JSON ids inside the parser.
        overrides = load_hobbyist_overrides(platform_dir)
        prj_entries = path_map_from_prj(
            _read_text(prj_path),
            list(zones),
            declared_aliases=overrides.get("zone_aliases"),
        )
        out["contamx_committed"] = _zone_classes(
            zone_ids, _contamx_edges(prj_entries, zone_ids), injection)
    else:
        out["contamx_committed"] = None

    native_dead = set(out["native"]["dead"]) if out["native"] else set()
    cx_dead = set(out["contamx_export"]["dead"])
    out["native_only_dead"] = (
        sorted(native_dead - cx_dead) if out["native"] else None
    )
    out["contamx_only_dead"] = sorted(cx_dead - native_dead)
    out["native_only_dead_frac"] = (
        len(native_dead - cx_dead) / len(zone_ids)
        if out["native"] and zone_ids else None
    )
    duty0 = {
        r for g in airflow.get("hvac_zones", [])
        if float(g.get("hvac_duty", airflow.get("hvac_duty", 1.0)) or 0.0) <= 0
        for r in g.get("rooms", []) if r in zones
    }
    out["duty0_rooms"] = sorted(duty0)
    dead_vol = sum(
        float(zones[z].get("volume_m3", 0.0)) for z in native_dead
    )
    total_vol = sum(float(z.get("volume_m3", 0.0)) for z in zones.values())
    out["native_dead_volume_share"] = (
        dead_vol / total_vol if out["native"] and total_vol else None
    )
    return out


# ── Q3: HVAC declaration coverage ───────────────────────────────────────


def _prj_ahs_ach(text: str) -> dict[str, float]:
    """``simple AHS`` desc lines ``Crusher HVAC <id> ach=<f>`` → {id: ach}."""
    sections = dict(_section_blocks(text))
    declared: dict[str, float] = {}
    for ln in sections.get("simple AHS", []):
        if "ach=" not in ln:
            continue
        toks = ln.split()
        if "HVAC" in toks:
            idx = toks.index("HVAC")
            hvac_id = toks[idx + 1] if idx + 1 < len(toks) else ""
        else:
            hvac_id = ""
        try:
            ach = float(toks[-1].split("ach=")[-1])
        except ValueError:
            continue
        if hvac_id:
            declared[hvac_id] = ach
    return declared


def audit_q3(platform_dir: str, airflow: dict[str, Any]) -> dict[str, Any]:
    """HVAC declaration coverage vs tuned cruise-hull conventions."""
    groups = airflow.get("hvac_zones", [])
    top_duty = airflow.get("hvac_duty")
    default_duty = float(top_duty) if top_duty is not None else 1.0
    duties = [float(g.get("hvac_duty", default_duty)) for g in groups]
    achs = [float(g.get("ach", 0.0)) for g in groups]
    out: dict[str, Any] = {
        "top_hvac_duty": top_duty,
        "top_oa_fraction": airflow.get("oa_fraction"),
        "n_groups": len(groups),
        "duty_values": sorted(set(duties)),
        "n_duty0_groups": sum(1 for d in duties if d <= 0.0),
        "n_duty_nondefault": sum(1 for d in duties if d != default_duty and d > 0),
        "ach_values": sorted(set(achs)),
        "ach_min": min(achs) if achs else None,
        "ach_max": max(achs) if achs else None,
        "oa_group_coverage": (
            sum(1 for g in groups if "oa_fraction" in g) / len(groups)
            if groups else 0.0
        ),
        "filter_declared_groups": sum(
            1 for g in groups if "filter_efficiency" in g),
        "nbc_groups": sum(
            1 for g in groups if any(k.startswith("nbc_filter") for k in g)),
    }
    prj_path = os.path.join(platform_dir, PRJ_REL_PATH)
    if os.path.exists(prj_path):
        prj_ach = _prj_ahs_ach(_read_text(prj_path))
        json_ach = {g["id"]: float(g.get("ach", 0.0)) for g in groups}
        out["prj_ach_annotations"] = prj_ach
        out["prj_ach_mismatch"] = sorted(
            {"group": gid, "json_ach": json_ach[gid], "prj_ach": prj_ach[gid]}
            for gid in set(prj_ach) & set(json_ach)
            if abs(prj_ach[gid] - json_ach[gid]) > 0.05
        )
        out["prj_ahs_unknown_groups"] = sorted(set(prj_ach) - set(json_ach))
        out["prj_ahs_missing_groups"] = sorted(set(json_ach) - set(prj_ach))
    else:
        out["prj_ach_annotations"] = None
    return out


# ── per-platform audit ──────────────────────────────────────────────────


def audit_platform(platform_id: str,
                   root: str = PLATFORMS_DIR) -> dict[str, Any]:
    """Run Q1/Q2/Q3 metrics for one platform directory."""
    pdir = os.path.join(REPO_ROOT, root, platform_id)
    spatial = _load_json(os.path.join(pdir, "spatial_layout.json"))
    airflow = _load_json(os.path.join(pdir, "air_flow_paths.json"))
    zones = _zone_map(spatial)
    result: dict[str, Any] = {
        "platform": platform_id,
        "ga_imported": os.path.exists(
            os.path.join(pdir, "import_provenance.json")),
        "has_prj": os.path.exists(os.path.join(pdir, PRJ_REL_PATH)),
        "n_zones": len(zones),
        "total_volume_m3": round(sum(
            float(z.get("volume_m3", 0.0)) for z in zones.values()), 2),
    }
    result["q1"] = audit_q1(pdir, spatial, airflow)
    result["q3"] = audit_q3(pdir, airflow)
    if zones:
        result["q2"] = audit_q2(pdir, spatial, airflow)
    else:
        result["q2"] = None
    return result


# ── divergence table + correlation ──────────────────────────────────────


def load_mean_l1(table_path: str) -> dict[str, float]:
    """Parse the committed fleet-compare markdown table → {platform: L1}."""
    out: dict[str, float] = {}
    for ln in _read_text(table_path).splitlines():
        toks = [t.strip() for t in ln.strip().strip("|").split("|")]
        if len(toks) < 10 or not toks or toks[0] in ("platform", "---"):
            continue
        try:
            out[toks[0]] = float(toks[8])
        except (ValueError, IndexError):
            continue
    return out


def _ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return 0.0
    return cov / (vx * vy) ** 0.5


def spearman(xs: list[float], ys: list[float]) -> float:
    """Spearman rank correlation with average ranks on ties."""
    if len(xs) < 3 or len(xs) != len(ys):
        return 0.0
    return _pearson(_ranks(xs), _ranks(ys))


def fleet_correlations(results: dict[str, dict[str, Any]],
                       mean_l1: dict[str, float]) -> dict[str, Any]:
    """Spearman of dead-zone metrics vs measured export-twin mean_l1."""
    rows = [
        (pid, r["q2"], mean_l1[pid])
        for pid, r in results.items()
        if pid in mean_l1 and r.get("q2")
    ]
    metrics = {
        "native_dead_frac": lambda q: q["native"]["dead_frac"],
        "native_sink_count": lambda q: len(q["native"]["sinks"]),
        "native_unreachable_count": lambda q: len(q["native"]["unreachable"]),
        "native_dead_volume_share": lambda q: q["native_dead_volume_share"],
        "native_only_dead_frac": lambda q: q["native_only_dead_frac"],
        "duty0_rooms_frac": lambda q: len(q["duty0_rooms"]) / q["n_zones"],
        "contamx_dead_frac": lambda q: q["contamx_export"]["dead_frac"],
    }
    corr: dict[str, Any] = {"n_hulls": len(rows), "vs_mean_l1": {}}
    for name, fn in metrics.items():
        # Metrics needing the native graph skip hulls whose engine failed
        # to build (dangling link endpoint — the CONTAM-XZONE-01 raise).
        pairs = [
            (float(fn(q)), float(l)) for _p, q, l in rows
            if q.get("native") is not None or "native" not in name
        ]
        corr["vs_mean_l1"][name] = (
            round(spearman([x for x, _ in pairs], [y for _, y in pairs]), 3)
            if len(pairs) >= 2 else None
        )
    return corr


# ── output ──────────────────────────────────────────────────────────────


def _fmt_dead(q2: dict[str, Any] | None) -> str:
    if not q2:
        return "-"
    n, c = q2["native"], q2["contamx_export"]
    if n is None:
        return f"ERR/{c['dead_frac']:.2f}"
    return (f"{n['dead_frac']:.2f}/{c['dead_frac']:.2f}"
            f" ({len(q2['native_only_dead'])} native-only)")


def write_table(results: dict[str, dict[str, Any]],
                mean_l1: dict[str, float], out_path: str) -> None:
    """Per-hull audit markdown table (audit-set order, then the rest)."""
    ordered = [p for p in AUDIT_SET if p in results]
    ordered += sorted(p for p in results if p not in set(ordered))
    lines = [
        "| platform | zones | L1 | Q1 missing/orphan | Q2 dead n/cx | "
        "Q3 duty | Q3 oa-cov | Q3 flags |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for pid in ordered:
        r = results[pid]
        q1, q2, q3 = r["q1"], r["q2"], r["q3"]
        flags = []
        if q3["nbc_groups"]:
            flags.append(f"nbc×{q3['nbc_groups']}")
        if q3["filter_declared_groups"]:
            flags.append(f"filt×{q3['filter_declared_groups']}")
        if q3.get("prj_ach_mismatch"):
            flags.append(f"ach-drift×{len(q3['prj_ach_mismatch'])}")
        lines.append(
            f"| {pid} | {r['n_zones']} | "
            f"{mean_l1.get(pid, float('nan')):.1f} | "
            f"{len(q1['missing_zone_refs'])}/{len(q1['orphan_zones'])} | "
            f"{_fmt_dead(q2)} | "
            f"{q3['duty_values']} | {q3['oa_group_coverage']:.2f} | "
            f"{','.join(flags) or '-'} |"
        )
    with validated_open(out_path, "w", allowed_roots=(REPO_ROOT,),
                        encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--platforms", nargs="+", default=["all"])
    ap.add_argument("--platforms-root", default=PLATFORMS_DIR,
                    help="Repo-relative platforms directory")
    ap.add_argument("--out", default=None,
                    help="Directory for the JSON report "
                         "(telemetry_buffer/museum_hull_audit)")
    ap.add_argument("--md-out", default=None,
                    help="Markdown table output path")
    ap.add_argument("--divergence-table", default=_DEFAULT_TABLE)
    ap.add_argument("--committed-dose", default=None,
                    help="Optional JSON {platform: committed-lane dose_l1}")
    args = ap.parse_args(argv)

    platforms = (
        _platform_dirs(args.platforms_root)
        if args.platforms == ["all"] else args.platforms
    )
    results: dict[str, dict[str, Any]] = {}
    for pid in platforms:
        try:
            results[pid] = audit_platform(pid, root=args.platforms_root)
        except (OSError, ValueError, KeyError) as exc:
            results[pid] = {"platform": pid, "error": f"{type(exc).__name__}: {exc}"}

    table_path = os.path.join(REPO_ROOT, args.divergence_table)
    mean_l1 = load_mean_l1(table_path) if os.path.exists(table_path) else {}
    corr = fleet_correlations(
        {p: r for p, r in results.items() if "q2" in r}, mean_l1)

    committed: dict[str, float] = {}
    if args.committed_dose:
        committed = json.loads(_read_text(
            os.path.join(REPO_ROOT, args.committed_dose)))
        cx_rows = [
            (pid, r["q2"], committed[pid])
            for pid, r in results.items()
            if pid in committed and r.get("q2")
            and r["q2"].get("native") and r["q2"]["contamx_committed"]
        ]
        corr["vs_committed_dose_l1"] = {
            "n_hulls": len(cx_rows),
            "native_dead_frac": round(spearman(
                [q["native"]["dead_frac"] for _p, q, _d in cx_rows],
                [d for _p, _q, d in cx_rows]), 3),
            "committed_cx_dead_frac": round(spearman(
                [q["contamx_committed"]["dead_frac"] for _p, q, _d in cx_rows],
                [d for _p, _q, d in cx_rows]), 3),
        }

    report = {
        "generated_by": "tools/museum_hull_audit.py",
        "audit_set": AUDIT_SET,
        "cruise_reference": CRUISE_REFERENCE,
        "correlations": corr,
        "hulls": results,
    }
    if args.out:
        out_dir = prepare_output_directory(
            resolve_repo_path(REPO_ROOT, args.out), allowed_roots=(REPO_ROOT,))
        path = os.path.join(out_dir, "museum_hull_audit_latest.json")
        with validated_open(path, "w", allowed_roots=(REPO_ROOT, out_dir),
                            encoding="utf-8") as fh:
            json.dump(report, fh, indent=1, sort_keys=True)
        print(f"wrote {path}")
    if args.md_out:
        write_table(results, mean_l1,
                    resolve_repo_path(REPO_ROOT, args.md_out))
        print(f"wrote {args.md_out}")
    print(json.dumps(corr, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
