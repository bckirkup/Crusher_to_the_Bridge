#!/usr/bin/env python3
"""Score a transport-engine re-lane of a settled QUAR-ATTR-V2 cell.

Reads the per-seed payloads written by
``tools/covid_attribution_arm_smoke.py --transport-engine <lane>`` for one
settled (theta, arm) cell, joins them against the committed QUAR-ATTR-V2
surface row for the same seeds, and answers the only question the probe
exists for: does the settled verdict move when the transport operator is
ContamX instead of native?

The movement yardstick is the design's own frozen attribution criterion
(``covid_quarantine_attribution_v1_design.json``): a shift is
**load-bearing** at >= 50%, **non-load-bearing** below 20%, indeterminate
between — measured on the conditional median over seeds that took off in
BOTH lanes, exactly as ``tools/covid_attribution_readout.py`` scores an
arm against A0. Per-seed deltas are never quoted: an engine swap reorders
RNG draws, so only distributional statistics over the 20 seeds compare.

Usage:
    python3 tools/covid_quar_attr_contamx_compare.py \
        --probe-dir results/covid_quar_attr_contamx_probe/contamx \
        --theta 1e9 --arm A0_declared \
        [--native-dir results/covid_quar_attr_contamx_probe/native] \
        [--out-csv docs/covid/covid_quar_attr_contamx_probe_surface.csv] \
        [--out-json results/covid_quar_attr_contamx_probe/summary.json]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
)
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)

ATTRIBUTION_DESIGN_REL = os.path.join(
    "picard_framework", "runs", "covid_quarantine_attribution_v1_design.json",
)
SETTLED_SURFACE_REL = os.path.join(
    "docs", "covid", "covid_quarantine_attribution_v2_surface.csv",
)

ROUTES = ("direct_contact", "droplet", "hvac_airborne", "fomite")
ZONES = ("cabin", "crew_mess", "galley", "corridor", "other")
ROLES = ("passenger", "crew")

SURFACE_COLUMNS = [
    "theta", "arm_id", "seed", "infections_total", "attack_rate",
    "recorded_onsets", "onsets_before_split_day",
    "infections_before_quarantine", "infections_during_quarantine",
    "infections_after_quarantine",
    "confined_passenger_infections_during_quarantine",
    "confined_at_activation", "ledger_events_during",
    "during_role_passenger", "during_role_crew",
    "during_zone_cabin", "during_zone_crew_mess", "during_zone_galley",
    "during_zone_corridor", "during_zone_other",
    "during_route_direct_contact", "during_route_droplet",
    "during_route_hvac_airborne", "during_route_fomite",
]
PROBE_EXTRA_COLUMNS = [
    "engine_class", "n_airflow_paths", "total_flow_m3h",
    "transport_engine_requested",
]
TAKEOFF_ONSETS = 10  # design.takeoff_recorded_onsets


def _resolve_cli_path(path: str) -> str:
    """Resolve a CLI path argument (S8707): absolute as-is, relative under the repo."""
    if os.path.isabs(path):
        return os.path.realpath(path)
    return resolve_repo_path(REPO_ROOT, path)


def _load_settled_rows(csv_path: str, theta: float, arm_id: str) -> dict[int, dict]:
    rows: dict[int, dict] = {}
    with validated_open(
        csv_path, "r", allowed_roots=(REPO_ROOT,), newline="", encoding="utf-8",
    ) as fh:
        for row in csv.DictReader(fh):
            if float(row["theta"]) == theta and row["arm_id"] == arm_id:
                rows[int(row["seed"])] = row
    return rows


def _payload_row(payload: dict, cell) -> dict:
    """One surface-CSV row read off a smoke-tool payload.

    Mirrors tools/covid_attribution_readout.py::_rows exactly so the probe
    surface and the settled surface carry the same fields on the same
    definitions.
    """
    obs = payload.get("observables") or {}
    by_role = payload.get("during_quarantine_by_role") or {}
    by_zone = payload.get("during_quarantine_by_zone_class") or {}
    by_route = payload.get("during_quarantine_by_route") or {}
    engine = payload.get("transport_engine") or {}
    row = {
        "theta": cell.theta,
        "arm_id": cell.arm_id,
        "seed": cell.seed,
        "infections_total": payload.get("infections_total"),
        "attack_rate": payload.get("attack_rate"),
        "recorded_onsets": obs.get("recorded_onsets"),
        "onsets_before_split_day": obs.get("onsets_before_split_day"),
        "infections_before_quarantine": payload.get(
            "infections_before_quarantine",
        ),
        "infections_during_quarantine": payload.get(
            "infections_during_quarantine",
        ),
        "infections_after_quarantine": payload.get(
            "infections_after_quarantine",
        ),
        "confined_passenger_infections_during_quarantine": payload.get(
            "confined_passenger_infections_during_quarantine",
        ),
        "confined_at_activation": (payload.get("quarantine_witness") or {}).get(
            "confined_at_activation",
        ),
        "ledger_events_during": sum(by_role.values()) if by_role else 0,
        "invalid_reason": (payload.get("quarantine_witness") or {}).get(
            "invalid_reason",
        ),
        "engine_class": engine.get("engine_class"),
        "n_airflow_paths": engine.get("n_airflow_paths"),
        "total_flow_m3h": engine.get("total_flow_m3h"),
        "transport_engine_requested": engine.get("requested"),
    }
    for k in ROLES:
        row[f"during_role_{k}"] = by_role.get(k, 0)
    for k in ZONES:
        row[f"during_zone_{k}"] = by_zone.get(k, 0)
    for k in ROUTES:
        row[f"during_route_{k}"] = by_route.get(k, 0)
    return row


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _lane_rows(directory: str, cells) -> dict[int, dict]:
    rows: dict[int, dict] = {}
    for cell in cells:
        path = os.path.join(directory, cell.key)
        if not os.path.isfile(path):
            continue
        with validated_open(
            path, "r", allowed_roots=(directory,), encoding="utf-8",
        ) as fh:
            payload = json.load(fh)
        rows[cell.seed] = _payload_row(payload, cell)
    return rows


def _lane_stats(by_seed: dict[int, dict]) -> dict:
    key = "infections_during_quarantine"
    during = [
        float(r[key]) for r in by_seed.values()
        if r.get(key) is not None
    ]
    takeoff = {
        s for s, r in by_seed.items()
        if r.get("recorded_onsets") is not None
        and float(r["recorded_onsets"]) >= TAKEOFF_ONSETS
    }
    return {
        "n": len(by_seed),
        "takeoff_n": len(takeoff),
        "takeoff_seeds": sorted(takeoff),
        "takeoff_probability": (
            len(takeoff) / len(by_seed) if by_seed else None
        ),
        "all_seed_median": _median(during),
    }


def _verdict_shift(
    settled: dict[int, dict], probe: dict[int, dict],
) -> dict:
    """Conditional-median shift on the shared takeoff set, 20/50 bands.

    Same scoring tools/covid_attribution_readout.py applies to an arm vs
    A0, run here between the settled lane and the probe lane of the same
    cell.
    """
    key = "infections_during_quarantine"
    to0 = {
        s for s, r in settled.items()
        if r.get("recorded_onsets") is not None
        and float(r["recorded_onsets"]) >= TAKEOFF_ONSETS
    }
    to1 = {
        s for s, r in probe.items()
        if r.get("recorded_onsets") is not None
        and float(r["recorded_onsets"]) >= TAKEOFF_ONSETS
    }
    both = sorted(to0 & to1)
    cond_settled = _median(
        [float(settled[s][key]) for s in both],
    ) if both else None
    cond_probe = _median(
        [float(probe[s][key]) for s in both],
    ) if both else None
    all_settled = _median(
        [float(r[key]) for r in settled.values() if r.get(key) is not None],
    )
    all_probe = _median(
        [float(r[key]) for r in probe.values() if r.get(key) is not None],
    )
    if cond_settled is None or cond_probe is None or cond_settled == 0:
        return {
            "n_both": len(both),
            "both_takeoff_seeds": both,
            "band": "not eligible (no takeoff overlap)",
        }
    change = (cond_probe - cond_settled) / cond_settled
    if change <= -0.5 and (all_probe or 0) < (all_settled or 0):
        band = "load_bearing_decrease"
    elif abs(change) < 0.2:
        band = "non_load_bearing_shift"
    else:
        band = "indeterminate"
    return {
        "n_both": len(both),
        "both_takeoff_seeds": both,
        "settled_conditional_median": cond_settled,
        "probe_conditional_median": cond_probe,
        "shift": change,
        "all_seed_median": {"settled": all_settled, "probe": all_probe},
        "takeoff": {
            "settled": f"{len(to0)}/{len(settled)}",
            "probe": f"{len(to1)}/{len(probe)}",
            "probe_only": sorted(to1 - to0),
            "settled_only": sorted(to0 - to1),
        },
        "band": band,
    }


def _paired_deltas(probe: dict[int, dict], head: dict[int, dict]) -> dict:
    """Seed-paired probe-vs-HEAD-native deltas.

    This is the attribution layer: the probe-vs-settled verdict is
    confounded by any model drift between the settled commit and HEAD, so
    the engine question is answered on seeds present in BOTH local lanes.
    """
    shared = sorted(set(probe) & set(head))
    keys = ("infections_total", "infections_during_quarantine",
            "recorded_onsets")
    per_seed = {}
    for s in shared:
        diffs = {}
        for k in keys:
            a, b = probe[s].get(k), head[s].get(k)
            if a is None or b is None:
                continue
            diffs[k] = {"head_native": b, "probe": a,
                        "delta": float(a) - float(b)}
        per_seed[str(s)] = diffs
    to_probe = {
        s for s in shared
        if (probe[s].get("recorded_onsets") or 0) >= TAKEOFF_ONSETS
    }
    to_head = {
        s for s in shared
        if (head[s].get("recorded_onsets") or 0) >= TAKEOFF_ONSETS
    }
    med_delta_during = _median([
        float(probe[s]["infections_during_quarantine"])
        - float(head[s]["infections_during_quarantine"])
        for s in shared
        if probe[s].get("infections_during_quarantine") is not None
        and head[s].get("infections_during_quarantine") is not None
    ])
    med_delta_total = _median([
        float(probe[s]["infections_total"])
        - float(head[s]["infections_total"])
        for s in shared
        if probe[s].get("infections_total") is not None
        and head[s].get("infections_total") is not None
    ])
    return {
        "shared_seeds": shared,
        "n_shared": len(shared),
        "per_seed": per_seed,
        "median_delta": {
            "infections_during_quarantine": med_delta_during,
            "infections_total": med_delta_total,
        },
        "takeoff": {
            "head_native": sorted(to_head),
            "probe": sorted(to_probe),
            "probe_only": sorted(to_probe - to_head),
            "head_only": sorted(to_head - to_probe),
        },
        "verdict_shift_vs_head": _verdict_shift(head, probe),
    }


def _native_parity(native_dir: str, cells, settled_rows: dict[int, dict]) -> dict:
    """HEAD native lane vs the settled CSV row, column for column."""
    checked = []
    mismatches = []
    for cell in cells:
        path = os.path.join(native_dir, cell.key)
        if not os.path.isfile(path):
            continue
        with validated_open(
            path, "r", allowed_roots=(native_dir,), encoding="utf-8",
        ) as fh:
            payload = json.load(fh)
        row = _payload_row(payload, cell)
        checked.append(cell.seed)
        settled = settled_rows.get(cell.seed)
        if settled is None:
            continue
        diffs = {
            col: {"settled": settled.get(col), "head": row.get(col)}
            for col in SURFACE_COLUMNS
            if col not in ("theta", "arm_id", "seed")
            and str(settled.get(col)) != str(row.get(col))
        }
        if diffs:
            mismatches.append({"seed": cell.seed, "diffs": diffs})
    return {
        "seeds_checked": checked,
        "byte_identical_to_settled": not mismatches,
        "mismatches": mismatches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-dir", required=True)
    parser.add_argument("--native-dir", default="")
    parser.add_argument("--theta", type=float, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--settled-csv", default=SETTLED_SURFACE_REL)
    parser.add_argument("--out-csv", default="")
    parser.add_argument("--out-json", default="")
    parser.add_argument("--repo-root", default=os.getcwd())
    args = parser.parse_args()

    repo_root = _resolve_cli_path(args.repo_root)
    probe_dir = _resolve_cli_path(args.probe_dir)
    native_dir = _resolve_cli_path(args.native_dir) if args.native_dir else ""
    settled_csv = _resolve_cli_path(args.settled_csv)

    design = load_design(ATTRIBUTION_DESIGN_REL, repo_root=repo_root)
    cells = [
        c for c in enumerate_cells(design)
        if c.theta == args.theta and c.arm_id == args.arm
    ]
    if not cells:
        parser.error(
            f"no design cells for arm {args.arm} @ theta {args.theta}",
        )

    settled_rows = _load_settled_rows(
        settled_csv, args.theta, args.arm,
    )
    missing_settled = [c.seed for c in cells if c.seed not in settled_rows]
    if missing_settled:
        parser.error(
            f"settled surface lacks seeds {missing_settled} for "
            f"{args.arm} @ theta {args.theta}",
        )

    probe_rows = _lane_rows(probe_dir, cells)
    missing_probe = [c.seed for c in cells if c.seed not in probe_rows]
    if missing_probe:
        print(f"WARNING: missing probe payloads for seeds {missing_probe}",
              file=sys.stderr)

    settled_stats = _lane_stats(settled_rows)
    probe_stats = _lane_stats(probe_rows)
    verdict = _verdict_shift(settled_rows, probe_rows)
    parity = None
    paired = None
    if native_dir:
        parity = _native_parity(native_dir, cells, settled_rows)
        head_rows = _lane_rows(native_dir, cells)
        if head_rows:
            paired = _paired_deltas(probe_rows, head_rows)

    engine_classes = sorted({
        str(r.get("engine_class")) for r in probe_rows.values()
    })
    invalid = {
        s: r.get("invalid_reason") for s, r in probe_rows.items()
        if r.get("invalid_reason")
    }
    summary = {
        "cell": {
            "theta": args.theta, "arm_id": args.arm,
            "seeds": [c.seed for c in cells],
        },
        "settled_source": settled_csv,
        "probe_dir": probe_dir,
        "probe_engine_classes": engine_classes,
        "probe_all_contamx": engine_classes == ["ContamXTransportEngine"],
        "invalid_reasons": invalid,
        "settled_stats": settled_stats,
        "probe_stats": probe_stats,
        "verdict_shift": verdict,
        "native_head_parity": parity,
        "probe_vs_head": paired,
    }
    print(json.dumps(summary, indent=2, default=str))

    if args.out_csv:
        # Sonar pythonsecurity:S8707 — output paths stay under the repo.
        out_csv = resolve_repo_path(REPO_ROOT, args.out_csv)
        prepare_output_directory(
            os.path.dirname(out_csv), allowed_roots=(REPO_ROOT,),
        )
        fieldnames = SURFACE_COLUMNS + PROBE_EXTRA_COLUMNS
        with validated_open(
            out_csv, "w", allowed_roots=(REPO_ROOT,), newline="",
            encoding="utf-8",
        ) as fh:
            writer = csv.DictWriter(
                fh, fieldnames=fieldnames, extrasaction="ignore",
            )
            writer.writeheader()
            for cell in cells:
                if cell.seed in probe_rows:
                    writer.writerow(probe_rows[cell.seed])
    if args.out_json:
        out_json = resolve_repo_path(REPO_ROOT, args.out_json)
        prepare_output_directory(
            os.path.dirname(out_json), allowed_roots=(REPO_ROOT,),
        )
        with validated_open(
            out_json, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as fh:
            json.dump(summary, fh, indent=2, default=str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
