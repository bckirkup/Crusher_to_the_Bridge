#!/usr/bin/env python3
"""Score the FLU-CONTAMX-01 paired lanes of the settled flu confined cell.

Joins the per-seed payloads written by
``tools/flu_confined_contamx_probe.py --transport-engine <lane>`` for the
settled conditioned ``influenza_a`` confined cell and answers the probe's
question: does the settled confined-SAR verdict move when the transport
operator is ContamX instead of native — and does the cell route through
the transported (environmental) pool at all?

The verdict language is the anchor's own: the confined-SAR band from
``docs/confined_attack_floor_spec.md`` (CABIN-FLOOR-03) with the spec's
Wilson-overlap comparison rule, and per-channel confined-slot dose shares
for the environmental-load check. Per-seed rows carry the engine-identity
fields because a contamx request falls back to native silently.

Usage:
    python3 tools/flu_confined_contamx_compare.py \
        --native-dir results/flu_confined_contamx_probe/native \
        --probe-dir results/flu_confined_contamx_probe/contamx \
        [--out-csv docs/flu/flu_confined_contamx_probe_surface.csv] \
        [--out-json results/flu_confined_contamx_probe/summary.json]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)

CHANNELS = ("pool", "plume", "contact", "hvac", "emesis", "flush", "fomite")

SURFACE_COLUMNS = [
    "seed", "lane", "infections_total", "infections_imported",
    "infections_acquired", "pairs_observed", "confined_index_pairs",
    "confined_slots", "confined_secondaries",
    "observed_mate_case_attack_confined", "implied_sar_confined_median",
    "channel_pool", "channel_plume", "channel_contact", "channel_hvac",
    "channel_emesis", "channel_flush", "channel_fomite",
    "acquired_droplet", "acquired_hvac_airborne", "acquired_caregiver",
    "acquired_direct_contact", "acquired_fomite",
    "dominant_droplet", "dominant_hvac_airborne", "dominant_caregiver",
    "dominant_direct_contact",
    "engine_class", "n_airflow_paths", "total_flow_m3h",
    "transport_engine_requested",
]


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    if n <= 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


def _load_lane(lane_dir: str, lane_name: str) -> list[dict]:
    rows = []
    for name in sorted(os.listdir(lane_dir)):
        if not name.endswith(".json"):
            continue
        with validated_open(
            os.path.join(lane_dir, name), "r",
            allowed_roots=(os.path.realpath(lane_dir),),
            encoding="utf-8",
        ) as fh:
            payload = json.load(fh)
        rows.append((lane_name, payload))
    return rows


def _surface_row(lane: str, p: dict) -> dict:
    ch = p.get("confined_channel_dose_totals", {})
    acq = p.get("acquired_particles_sums", {})
    dom = p.get("infections_by_dominant_route", {})
    eng = p.get("transport_engine", {})
    return {
        "seed": p["seed"], "lane": lane,
        "infections_total": p["infections_total"],
        "infections_imported": p["infections_imported"],
        "infections_acquired": p["infections_acquired"],
        "pairs_observed": p["pairs_observed"],
        "confined_index_pairs": p["confined_index_pairs"],
        "confined_slots": p["confined_slots"],
        "confined_secondaries": p["confined_secondaries"],
        "observed_mate_case_attack_confined": (
            p["observed_mate_case_attack_confined"]
        ),
        "implied_sar_confined_median": p["implied_sar_confined_median"],
        **{f"channel_{c}": round(ch.get(c, 0.0), 4) for c in CHANNELS},
        "acquired_droplet": round(acq.get("droplet", 0.0), 4),
        "acquired_hvac_airborne": round(acq.get("hvac_airborne", 0.0), 4),
        "acquired_caregiver": round(acq.get("caregiver", 0.0), 4),
        "acquired_direct_contact": round(acq.get("direct_contact", 0.0), 4),
        "acquired_fomite": round(acq.get("fomite", 0.0), 4),
        "dominant_droplet": dom.get("droplet", 0),
        "dominant_hvac_airborne": dom.get("hvac_airborne", 0),
        "dominant_caregiver": dom.get("caregiver", 0),
        "dominant_direct_contact": dom.get("direct_contact", 0),
        "engine_class": eng.get("engine_class"),
        "n_airflow_paths": eng.get("n_airflow_paths"),
        "total_flow_m3h": eng.get("total_flow_m3h"),
        "transport_engine_requested": eng.get("requested"),
    }


def _pooled_attack(rows: list[dict]) -> dict:
    slots = sum(r["confined_slots"] for r in rows)
    sec = sum(r["confined_secondaries"] for r in rows)
    wilson = _wilson(sec, slots) if slots else None
    return {
        "confined_slots": slots,
        "confined_secondaries": sec,
        "observed_attack": sec / slots if slots else None,
        "wilson95": wilson,
        "channel_totals": {
            c: sum(r[f"channel_{c}"] for r in rows) for c in CHANNELS
        },
        "acquired_sums": {
            route: sum(r[f"acquired_{route}"] for r in rows)
            for route in (
                "droplet", "hvac_airborne", "caregiver",
                "direct_contact", "fomite",
            )
        },
        "dominant_sums": {
            route: sum(r[f"dominant_{route}"] for r in rows)
            for route in (
                "droplet", "hvac_airborne", "caregiver", "direct_contact",
            )
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-dir", required=True)
    parser.add_argument("--probe-dir", required=True)
    parser.add_argument(
        "--probe-lane", default="contamx",
        help="label for the probe lane's engine",
    )
    parser.add_argument("--out-csv", default=None)
    parser.add_argument("--out-json", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = [
        _surface_row(lane, payload)
        for lane, payload in (
            _load_lane(os.path.realpath(args.native_dir), "native")
            + _load_lane(os.path.realpath(args.probe_dir), args.probe_lane)
        )
    ]
    rows.sort(key=lambda r: (r["seed"], r["lane"]))
    by_lane: dict[str, list[dict]] = {}
    for row in rows:
        by_lane.setdefault(row["lane"], []).append(row)
    paired = sorted(
        set(by_lane.get("native", []) and {r["seed"] for r in by_lane["native"]})
        & {r["seed"] for r in by_lane.get(args.probe_lane, [])}
    )
    summary = {
        "paired_seeds": paired,
        "pooled_by_lane": {
            lane: _pooled_attack(lane_rows)
            for lane, lane_rows in by_lane.items()
        },
        "seed_rows": rows,
    }
    if args.out_csv:
        csv_path = resolve_repo_path(REPO_ROOT, args.out_csv)
        prepare_output_directory(
            os.path.dirname(csv_path), allowed_roots=(REPO_ROOT,),
        )
        with validated_open(
            csv_path, "w", allowed_roots=(REPO_ROOT,), newline="",
            encoding="utf-8",
        ) as fh:
            writer = csv.DictWriter(fh, fieldnames=SURFACE_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
    if args.out_json:
        json_path = resolve_repo_path(REPO_ROOT, args.out_json)
        prepare_output_directory(
            os.path.dirname(json_path), allowed_roots=(REPO_ROOT,),
        )
        with validated_open(
            json_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as fh:
            json.dump(summary, fh, indent=2, sort_keys=True)
    print(json.dumps(
        {lane: {
            "slots": pooled["confined_slots"],
            "secondaries": pooled["confined_secondaries"],
            "attack": pooled["observed_attack"],
            "wilson95": pooled["wilson95"],
            "channel_totals": pooled["channel_totals"],
        } for lane, pooled in summary["pooled_by_lane"].items()},
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
