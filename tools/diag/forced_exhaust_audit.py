#!/usr/bin/env python3
"""Fleet-wide audit of ``cross_zone_links`` direction, mechanism and filtration.

Read-only companion to ``docs/proposals/forced_exhaust_audit_and_fix_plan.md``.
It changes no engine, schema or hull data.

``audit`` classifies every ``cross_zone_links`` entry of every
``data/platforms/*/air_flow_paths.json`` exactly once and writes

* ``forced_exhaust_audit_links.csv``   - one row per link, and
* ``forced_exhaust_audit_summary.json`` - per-platform and fleet totals with
  a reconciliation block (platform and link counts against a direct recount).

For each link it records what the hull data declares, what the description
*states* (a keyword reading of ``path`` + ``description`` - an authoring
intent, never a physical measurement), what the native lane does
(``engines.py_contam_bridge.cross_zone_link_bidirectional``) and what the
ContamX exporter emits (``tools.contamw34_prj._add_cross_zone_paths``:
``fan_cvf`` when ``is_hvac_ducted`` else a ``plr_orfc`` sized at 1 Pa; the
exporter never reads ``direction``).

``exact-check`` reads no campaign output. It rebuilds the linear transport
operator for the named hulls under the frozen Phase 1 tracer conditions and
reports, per source zone, the exact whole-hull material-time integral next to
the hourly endpoint sum the campaign cells record, with and without
``direction="oneway"`` applied in memory to ``Sanitary_Makeup`` links. With a
ContamX binary available it adds the commissioned export (E) lane.
``--filter-efficiency`` / ``--decay-per-hour`` evaluate other declared
conditions and write to a ``--label``-suffixed file, leaving the frozen-
condition artifact untouched.
"""

from __future__ import annotations

import argparse
import copy
import csv
import glob
import json
import os
import re
import statistics
import sys
import tempfile
from typing import Any

REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engines.py_contam_bridge import (  # noqa: E402
    DEFAULT_PASSIVE_LINK_MODE,
    ContamTransportEngine,
    cross_zone_link_bidirectional,
)
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)

PLATFORM_GLOB = os.path.join("data", "platforms", "*", "air_flow_paths.json")
DESIGN_REL = os.path.join(
    "campaigns", "contam", "phase1_hvac_tracer_01", "design",
    "phase1_hvac_tracer_design.json",
)
DEFAULT_OUT = os.path.join("docs", "proposals")
LINKS_CSV = "forced_exhaust_audit_links.csv"
SUMMARY_JSON = "forced_exhaust_audit_summary.json"
EXACT_JSON = "forced_exhaust_exact_integral_check.json"
SANITARY_PATH = "Sanitary_Makeup"

# Hulls of the frozen CONTAM study plus the hull fixed by #1171.
STUDY_HULLS = (
    "destroyer_baseline", "fletcher_class_destroyer", "lexington_cv2",
    "saratoga_cv3", "missouri_bb63", "expedition_cruise_450",
    "classic_cruise_1900", "spirit_cruise_3000", "mega_cruise_5000",
    "greg_mortimer",
)

# Ordered keyword reading of ``path`` + ``description``. First match wins.
# (intent class, stated direction, stated mechanism, pattern)
INTENT_RULES: tuple[tuple[str, str, str, str], ...] = (
    ("forced_exhaust", "oneway", "prescribed_flow",
     r"exhaust|extract|hood|relief"),
    ("forced_supply", "oneway", "prescribed_flow",
     r"supply|make-?up"),
    ("pressure_directed", "oneway", "pressure_opening",
     r"negative|positive pressure|draws|drawn|net in"),
)
# Applied only to links not declared ``is_hvac_ducted`` (a ducted link with no
# stated exhaust/supply/pressure role is a ``ducted_transfer`` fan leg).
PASSIVE_PATTERN = (
    r"ladder|stair|hatch|door|passage|corridor|shaft|trunk|well|elevator"
    r"|lift|ramp|access|deck|passive|leak|transfer|curtain|lobby"
)
GALLEY_PATTERN = r"galley|scullery|pantry|kitchen|mess"

CSV_FIELDS = (
    "platform", "link_index", "path", "from", "to", "flow_rate_m3h",
    "is_hvac_ducted", "is_hvac_ducted_declared", "direction_declared",
    "direction_present", "from_kind", "to_kind", "room_pairs",
    "to_exhaust_only_terminal", "galley_related", "intent_class",
    "intent_rule", "stated_direction", "stated_mechanism",
    "native_bidirectional", "native_reverse_paths", "native_filtered",
    "exporter_element", "exporter_reads_direction", "flags", "description",
)

FLAG_REVERSE = "native_reverse_on_stated_oneway"
FLAG_ORIFICE = "exporter_orifice_on_stated_prescribed_flow"
FLAG_FILTER = "filtration_coupled_to_ducted_flag"
FLAG_ZERO = "zero_flow_dropped_by_exporter"
FLAG_ENDPOINT = "endpoint_unresolved"
FLAG_UNSTATED = "intent_unstated"
ALL_FLAGS = (
    FLAG_REVERSE, FLAG_ORIFICE, FLAG_FILTER, FLAG_ZERO, FLAG_ENDPOINT,
    FLAG_UNSTATED,
)


def _load_json(rel_path: str) -> dict[str, Any]:
    path = resolve_repo_path(REPO_ROOT, rel_path)
    with validated_open(path, "r", allowed_roots=(REPO_ROOT,),
                        encoding="utf-8") as fh:
        return json.load(fh)


def _platform_files() -> list[str]:
    return sorted(glob.glob(os.path.join(REPO_ROOT, PLATFORM_GLOB)))


def _platform_id(path: str) -> str:
    return os.path.basename(os.path.dirname(path))


def _room_ids(spatial: dict[str, Any]) -> set[str]:
    return {str(zone["id"]) for zone in spatial.get("zones", [])}


def _exhaust_only_groups(airflow: dict[str, Any]) -> set[str]:
    """Groups the native lane treats as duty-0, oa-1 exhaust terminals."""
    default_oa = float(airflow.get("oa_fraction", 0.2))
    default_duty = float(airflow.get("hvac_duty", 1.0))
    found = set()
    for group in airflow.get("hvac_zones", []):
        duty = float(group.get("hvac_duty", default_duty))
        oa = float(group.get("oa_fraction", default_oa))
        if duty <= 0.0 and oa >= 1.0:
            found.add(str(group["id"]))
    return found


def _endpoint(
    token: str, groups: dict[str, list[str]], rooms: set[str],
) -> tuple[str, int]:
    """Endpoint kind and room count, in the order both lanes resolve it."""
    if token in groups:
        return "hvac_group", len([r for r in groups[token] if r in rooms])
    if token in rooms:
        return "room", 1
    return "unresolved", 0


def classify_intent(
    link: dict[str, Any], to_exhaust_terminal: bool,
) -> tuple[str, str, str, str]:
    """(intent class, matched rule, stated direction, stated mechanism)."""
    path = str(link.get("path", ""))
    if path == SANITARY_PATH or to_exhaust_terminal:
        rule = "path" if path == SANITARY_PATH else "to_exhaust_only_terminal"
        return "sanitary_makeup", rule, "oneway", "prescribed_flow"
    text = f"{path} {link.get('description', '')}".lower().replace("_", " ")
    for intent, direction, mechanism, pattern in INTENT_RULES:
        match = re.search(pattern, text)
        if match:
            return intent, match.group(0), direction, mechanism
    if bool(link.get("is_hvac_ducted", False)):
        return "ducted_transfer", "is_hvac_ducted", "oneway", "prescribed_flow"
    match = re.search(PASSIVE_PATTERN, text)
    if match:
        return (
            "passive_opening", match.group(0), "bidirectional",
            "pressure_opening",
        )
    return "unstated", "", "unstated", "unstated"


def _flags(row: dict[str, Any]) -> list[str]:
    checks = (
        (FLAG_REVERSE,
         row["stated_direction"] == "oneway" and row["native_bidirectional"]),
        (FLAG_ORIFICE,
         row["stated_mechanism"] == "prescribed_flow"
         and row["exporter_element"] == "plr_orfc"),
        (FLAG_FILTER, row["is_hvac_ducted"]),
        (FLAG_ZERO, row["exporter_element"] == "dropped_zero_flow"),
        (FLAG_ENDPOINT, row["room_pairs"] == 0),
        (FLAG_UNSTATED, row["intent_class"] == "unstated"),
    )
    return [name for name, hit in checks if hit]


def _exporter_element(ducted: bool, flow: float, pairs: int) -> str:
    if pairs == 0:
        return "dropped_unresolved"
    if flow <= 0.0:
        return "dropped_zero_flow"
    return "fan_cvf" if ducted else "plr_orfc"


def classify_link(
    platform: str, index: int, link: dict[str, Any],
    airflow: dict[str, Any], rooms: set[str],
) -> dict[str, Any]:
    groups = {
        str(g["id"]): list(g.get("rooms", []))
        for g in airflow.get("hvac_zones", [])
    }
    from_kind, n_from = _endpoint(str(link["from"]), groups, rooms)
    to_kind, n_to = _endpoint(str(link["to"]), groups, rooms)
    pairs = n_from * n_to
    ducted = bool(link.get("is_hvac_ducted", False))
    flow = float(link.get("flow_rate_m3h", 0.0))
    to_terminal = str(link["to"]) in _exhaust_only_groups(airflow)
    intent, rule, direction, mechanism = classify_intent(link, to_terminal)
    bidirectional = cross_zone_link_bidirectional(
        link, DEFAULT_PASSIVE_LINK_MODE,
    )
    text = f"{link.get('path', '')} {link.get('description', '')}".lower()
    row: dict[str, Any] = {
        "platform": platform,
        "link_index": index,
        "path": str(link.get("path", "")),
        "from": str(link["from"]),
        "to": str(link["to"]),
        "flow_rate_m3h": flow,
        "is_hvac_ducted": ducted,
        "is_hvac_ducted_declared": "is_hvac_ducted" in link,
        "direction_declared": str(link.get("direction", "")),
        "direction_present": "direction" in link,
        "from_kind": from_kind,
        "to_kind": to_kind,
        "room_pairs": pairs,
        "to_exhaust_only_terminal": to_terminal,
        "galley_related": bool(re.search(GALLEY_PATTERN, text)),
        "intent_class": intent,
        "intent_rule": rule,
        "stated_direction": direction,
        "stated_mechanism": mechanism,
        "native_bidirectional": bidirectional,
        "native_reverse_paths": pairs if bidirectional else 0,
        "native_filtered": ducted,
        "exporter_element": _exporter_element(ducted, flow, pairs),
        "exporter_reads_direction": False,
        "description": str(link.get("description", "")),
    }
    row["flags"] = ";".join(_flags(row))
    return row


def audit_platform(path: str) -> list[dict[str, Any]]:
    platform = _platform_id(path)
    airflow = _load_json(path)
    spatial = _load_json(
        os.path.join(os.path.dirname(path), "spatial_layout.json"),
    )
    rooms = _room_ids(spatial)
    return [
        classify_link(platform, index, link, airflow, rooms)
        for index, link in enumerate(airflow.get("cross_zone_links", []))
    ]


def _count(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row[key])
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _flag_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        flag: sum(1 for row in rows if flag in row["flags"].split(";"))
        for flag in ALL_FLAGS
    }


def _summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    reverse = [
        r for r in rows if FLAG_REVERSE in r["flags"].split(";")
    ]
    return {
        "links": len(rows),
        "direction_present": sum(1 for r in rows if r["direction_present"]),
        "is_hvac_ducted_true": sum(1 for r in rows if r["is_hvac_ducted"]),
        "sanitary_makeup_links": sum(
            1 for r in rows if r["path"] == SANITARY_PATH
        ),
        "galley_related_links": sum(1 for r in rows if r["galley_related"]),
        "by_intent_class": _count(rows, "intent_class"),
        "by_exporter_element": _count(rows, "exporter_element"),
        "flags": _flag_counts(rows),
        "native_reverse_paths_on_stated_oneway": sum(
            int(r["native_reverse_paths"]) for r in reverse
        ),
    }


def _direct_recount() -> dict[str, int]:
    """Independent recount with no classification code on the path."""
    platforms = 0
    links = 0
    for path in _platform_files():
        with validated_open(path, "r", allowed_roots=(REPO_ROOT,),
                            encoding="utf-8") as fh:
            raw = json.load(fh)
        platforms += 1
        links += len(raw.get("cross_zone_links", []))
    return {"platforms": platforms, "links": links}


def build_audit() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    files = _platform_files()
    rows: list[dict[str, Any]] = []
    per_platform: dict[str, Any] = {}
    for path in files:
        platform_rows = audit_platform(path)
        rows.extend(platform_rows)
        entry = _summarise(platform_rows)
        entry["study_hull"] = _platform_id(path) in STUDY_HULLS
        entry["has_contam_bundle"] = os.path.isdir(
            os.path.join(os.path.dirname(path), "contam"),
        )
        per_platform[_platform_id(path)] = entry
    recount = _direct_recount()
    keys = {(r["platform"], r["link_index"]) for r in rows}
    reconciliation = {
        "platforms_audited": len(per_platform),
        "platforms_direct_recount": recount["platforms"],
        "links_audited": len(rows),
        "links_direct_recount": recount["links"],
        "links_sum_of_platforms": sum(
            p["links"] for p in per_platform.values()
        ),
        "unique_link_keys": len(keys),
        "sum_by_intent_class": sum(_summarise(rows)["by_intent_class"].values()),
    }
    reconciliation["reconciled"] = (
        reconciliation["platforms_audited"]
        == reconciliation["platforms_direct_recount"]
        and len({
            reconciliation["links_audited"],
            reconciliation["links_direct_recount"],
            reconciliation["links_sum_of_platforms"],
            reconciliation["unique_link_keys"],
            reconciliation["sum_by_intent_class"],
        }) == 1
    )
    summary = {
        "schema": "forced_exhaust_audit_summary_v1",
        "native_passive_link_mode": DEFAULT_PASSIVE_LINK_MODE,
        "intent_rules": [list(rule) for rule in INTENT_RULES],
        "passive_pattern": PASSIVE_PATTERN,
        "reconciliation": reconciliation,
        "fleet": _summarise(rows),
        "platforms": per_platform,
    }
    return rows, summary


def _open_out(out_dir: str, name: str) -> Any:
    return validated_open(
        os.path.join(out_dir, name), "w",
        allowed_roots=(REPO_ROOT, out_dir), encoding="utf-8", newline="",
    )


def _out_dir(raw: str) -> str:
    return prepare_output_directory(
        resolve_repo_path(REPO_ROOT, raw), allowed_roots=(REPO_ROOT,),
    )


def run_audit(out: str) -> int:
    rows, summary = build_audit()
    out_dir = _out_dir(out)
    with _open_out(out_dir, LINKS_CSV) as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with _open_out(out_dir, SUMMARY_JSON) as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)
        fh.write("\n")
    rec = summary["reconciliation"]
    print(
        f"platforms={rec['platforms_audited']} links={rec['links_audited']} "
        f"recount={rec['platforms_direct_recount']}/"
        f"{rec['links_direct_recount']} reconciled={rec['reconciled']}",
    )
    return 0 if rec["reconciled"] else 1


# ── exact-integral check ────────────────────────────────────────────────


def _material_time(
    operator: Any, index: int, horizon_h: float, step_h: float,
) -> tuple[float, float]:
    """(exact integral, endpoint sum) of retained mass fraction, hours."""
    import numpy as np
    from scipy.linalg import expm

    n = operator.shape[0]
    start = np.zeros(n)
    start[index] = 1.0
    block = np.zeros((2 * n, 2 * n))
    block[:n, :n] = operator
    block[:n, n:] = np.eye(n)
    exact = float((expm(block * horizon_h)[:n, n:] @ start).sum())
    propagator = expm(operator * step_h)
    mass = start
    sampled = 0.0
    for _ in range(int(round(horizon_h / step_h))):
        mass = propagator @ mass
        sampled += float(mass.sum()) * step_h
    return exact, sampled


def _spread(values: list[float]) -> dict[str, float]:
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def _lane_report(
    engine: Any, sanitary: list[str], named: list[str],
    horizon_h: float, step_h: float, decay_per_h: float,
) -> dict[str, Any]:
    import numpy as np

    ids = list(engine._real_zone_ids)
    operator = engine._build_decay_free_operator() - decay_per_h * np.eye(
        len(ids),
    )
    report: dict[str, Any] = {"zones": len(ids), "sources": {}}
    pairs = [
        _material_time(operator, ids.index(zone), horizon_h, step_h)
        for zone in sanitary if zone in ids
    ]
    if pairs:
        report["sanitary_exact_h"] = _spread([p[0] for p in pairs])
        report["sanitary_endpoint_sum_h"] = _spread([p[1] for p in pairs])
    for zone in named:
        if zone in ids:
            exact, sampled = _material_time(
                operator, ids.index(zone), horizon_h, step_h,
            )
            report["sources"][zone] = {
                "exact_h": exact, "endpoint_sum_h": sampled,
            }
    return report


def _native(
    spatial: dict[str, Any], airflow: dict[str, Any], tracer: dict[str, Any],
    step_h: float,
) -> ContamTransportEngine:
    from engines.sim_clock import SimClock

    return ContamTransportEngine(
        spatial, airflow,
        filter_efficiency=float(tracer["filter_efficiency"]),
        natural_decay_rate=float(tracer["natural_decay_rate"]),
        clock=SimClock(epoch_duration_hours=step_h, mode="hours"),
    )


def _contamx(
    spatial: dict[str, Any], airflow: dict[str, Any], tracer: dict[str, Any],
    step_h: float, binary: str, tmp_root: str,
) -> tuple[Any, dict[str, dict[str, float]]]:
    """Commissioned-export (E) lane engine and its galley-related flows.

    Solved flows are signed in the declared from->to sense: a negative
    value is air moving against the link's declared direction.
    """
    from engines.contamx_transport import ContamXTransportEngine
    from engines.sim_clock import SimClock
    from tools.contam_fleet_compare import _contamx_field

    eta = float(tracer["filter_efficiency"])
    field = _contamx_field(
        spatial, airflow, tmp_dir=tempfile.mkdtemp(dir=tmp_root),
        binary=binary, prj_rel=None, filter_efficiency=eta,
    )
    entries = field["entries"]
    flows = {int(k): float(v) for k, v in field["flows"].items()}
    engine = ContamXTransportEngine(
        spatial, entries, flows, filter_efficiency=eta,
        natural_decay_rate=float(tracer["natural_decay_rate"]),
        path_map_entries=entries,
        oa_fraction=float(airflow.get("oa_fraction", 0.2)),
        clock=SimClock(epoch_duration_hours=step_h, mode="hours"),
    )
    galley: dict[str, dict[str, float]] = {}
    for entry in entries:
        kind = str(entry.get("kind", ""))
        if not entry.get("crusher_transfer"):
            continue
        if not re.search(GALLEY_PATTERN, kind.lower()):
            continue
        flow = float(flows.get(int(entry["path_nr"]), 0.0))
        row = galley.setdefault(
            kind, {"paths": 0, "total_m3h": 0.0, "min_m3h": flow,
                   "max_m3h": flow},
        )
        row["paths"] += 1
        row["total_m3h"] += flow
        row["min_m3h"] = min(row["min_m3h"], flow)
        row["max_m3h"] = max(row["max_m3h"], flow)
    return engine, galley


def _oneway_sanitary(airflow: dict[str, Any]) -> dict[str, Any]:
    pinned = copy.deepcopy(airflow)
    for link in pinned.get("cross_zone_links", []):
        if link.get("path") == SANITARY_PATH:
            link["direction"] = "oneway"
    return pinned


def _hull_check(
    hull: str, named: list[str], tracer: dict[str, Any],
    horizon_h: float, step_h: float, binary: str | None, tmp_root: str,
) -> dict[str, Any]:
    base = os.path.join("data", "platforms", hull)
    spatial = _load_json(os.path.join(base, "spatial_layout.json"))
    airflow = _load_json(os.path.join(base, "air_flow_paths.json"))
    sanitary = sorted(
        str(group["rooms"][0])
        for group in airflow.get("hvac_zones", [])
        if str(group["id"]) in _exhaust_only_groups(airflow)
        and len(group.get("rooms", [])) == 1
    )
    variants = {
        "as_authored": airflow,
        "sanitary_makeup_oneway": _oneway_sanitary(airflow),
    }
    result: dict[str, Any] = {"sanitary_source_zones": len(sanitary)}
    decay = float(tracer["natural_decay_rate"])
    for label, variant in variants.items():
        lanes: dict[str, Any] = {
            "native": _lane_report(
                _native(spatial, variant, tracer, step_h),
                sanitary, named, horizon_h, step_h, decay,
            ),
        }
        if binary:
            engine, galley = _contamx(
                spatial, variant, tracer, step_h, binary, tmp_root,
            )
            lanes["contamx_commissioned_export"] = _lane_report(
                engine, sanitary, named, horizon_h, step_h, decay,
            )
            lanes["contamx_commissioned_export"][
                "galley_related_solved_flows"
            ] = galley
        result[label] = lanes
    return result


def _tracer_conditions(
    design: dict[str, Any], filter_efficiency: float | None,
    decay_per_h: float | None,
) -> dict[str, float]:
    """Frozen Phase 1 tracer conditions unless a value is overridden."""
    frozen = design["tracer"]
    return {
        "filter_efficiency": float(
            frozen["filter_efficiency"]
            if filter_efficiency is None else filter_efficiency,
        ),
        "natural_decay_rate": float(
            frozen["natural_decay_rate"]
            if decay_per_h is None else decay_per_h,
        ),
    }


def run_exact_check(
    hulls: list[str], named: list[str], out: str, use_contamx: bool,
    filter_efficiency: float | None = None,
    decay_per_h: float | None = None, label: str = "",
) -> int:
    from engines.contamx_runner import find_contamx

    design = _load_json(DESIGN_REL)
    tracer = _tracer_conditions(design, filter_efficiency, decay_per_h)
    step_h = float(design["matrix"]["epoch_hours"])
    horizon_h = step_h * int(design["matrix"]["epochs"])
    binary = find_contamx() if use_contamx else None
    out_dir = _out_dir(out)
    scratch = _out_dir(os.path.join("telemetry_buffer", "forced_exhaust_audit"))
    report: dict[str, Any] = {
        "schema": "forced_exhaust_exact_integral_check_v1",
        "design": DESIGN_REL,
        "filter_efficiency": tracer["filter_efficiency"],
        "natural_decay_rate": tracer["natural_decay_rate"],
        "conditions": (
            "frozen Phase 1 tracer"
            if filter_efficiency is None and decay_per_h is None
            else "overridden on the command line"
        ),
        "horizon_hours": horizon_h,
        "sampling_step_hours": step_h,
        "contamx_lane": bool(binary),
        "definition": (
            "unit t0 pulse in one source zone; exact_h is the integral of "
            "total retained mass fraction over the horizon; endpoint_sum_h "
            "is the sum of end-of-step retained fractions times the step"
        ),
        "hulls": {},
    }
    with tempfile.TemporaryDirectory(dir=scratch) as tmp_root:
        for hull in hulls:
            report["hulls"][hull] = _hull_check(
                hull, named, tracer, horizon_h, step_h, binary, tmp_root,
            )
            print(f"checked {hull}")
    name = EXACT_JSON
    if label:
        if not re.fullmatch(r"[a-z0-9_]+", label):
            raise SystemExit("--label must match [a-z0-9_]+")
        name = EXACT_JSON.replace(".json", f"_{label}.json")
    with _open_out(out_dir, name) as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="classify every cross_zone_link")
    audit.add_argument("--out", default=DEFAULT_OUT)
    exact = sub.add_parser(
        "exact-check", help="exact vs hourly-endpoint material-time",
    )
    exact.add_argument("--hull", action="append", required=True)
    exact.add_argument("--source", action="append", default=[])
    exact.add_argument("--out", default=DEFAULT_OUT)
    exact.add_argument("--no-contamx", action="store_true")
    exact.add_argument(
        "--filter-efficiency", type=float, default=None,
        help="override the frozen Phase 1 filter efficiency",
    )
    exact.add_argument(
        "--decay-per-hour", type=float, default=None,
        help="override the frozen Phase 1 natural decay rate",
    )
    exact.add_argument(
        "--label", default="",
        help="suffix for the output file name (required with overrides)",
    )
    args = parser.parse_args(argv)
    if args.command == "audit":
        return run_audit(args.out)
    overridden = (
        args.filter_efficiency is not None or args.decay_per_hour is not None
    )
    if overridden and not args.label:
        parser.error("--label is required when conditions are overridden")
    return run_exact_check(
        args.hull, args.source, args.out, not args.no_contamx,
        args.filter_efficiency, args.decay_per_hour, args.label,
    )


if __name__ == "__main__":
    raise SystemExit(main())
