#!/usr/bin/env python3
"""COVID-THETA-V14 stage-1 readout — stream-reads the S3 cell objects.

The submitted scope is the single-arm 1,800-cell stage-1 lattice: the
committed two-arm design's ``hygiene_cycle`` blocks only (cell indices
``r*400 .. r*400+199`` per lattice row). Every cell JSON under the
campaign prefix is streamed straight off S3 — each object is fetched,
parsed, and only the parsed payload retained in memory; no cells/
directory is ever materialised on disk.

Reads:

- ``merge_screen`` (the framework's pooling) over the streamed payloads —
  ``fleet_shape_ok`` is the frozen v11 selector verbatim (median recorded
  attack in [0.0005, 0.008], IQR overlapping [0.0003, 0.015], mean <= 0.06).
- The v13 parent surface's own cells, streamed the same way, for the
  declared ``paired_vs_v13`` drift diagnostic (per-seed recorded-onsets
  deltas and takeoff-class flips at the same Theta + seed).

Scored here, frozen in the design file:

- admissible set = interior lattice Thetas (endpoints are boundary
  verification, never candidates) whose hygiene_cycle row's
  ``fleet_shape_ok`` is true;
- ``report_immediately_if`` — window illusory (every interior row fails on
  the same side, or overshoot at both ends), admissible only at a
  boundary, takeoff transition outside the bracket (no takeoff at the top
  row or saturation at the bottom), a generic-voyage audit failure
  (``delivery.hand_reservoir_mode`` not the declared arm), or the user's
  session trigger (a suppression-shaped seed-paired move vs v13 outside
  the stream-reorder band, or the admissible set moving off
  {1.78e11..5.62e11}).

Usage:

    python3 tools/covid_theta_v14_readout.py \
        --design picard_framework/runs/covid_theta_screen_v14_design.json \
        --s3-prefix s3://<bucket>/campaign/covid_theta_screen_v14/<sha>/ \
        --parent-design picard_framework/runs/covid_theta_screen_v13_design.json \
        --parent-s3-prefix s3://<bucket>/campaign/covid_theta_screen_v13/edb7fc41/ \
        --out telemetry_buffer/covid_theta_v14_readout.json \
        --surface-out docs/covid/covid_theta_screen_v14_surface.csv \
        --pairs-out docs/covid/covid_theta_screen_v14_pairs.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Iterable

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
    merge_screen,
)
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)
from tools.covid_screen_readout_common import quantile  # noqa: E402
from tools.covid_theta_screen_csv import write_surface_csv  # noqa: E402

TAKEOFF_MIN_ONSETS = 10

# The stream-reorder band for the user's session trigger: the hygiene_cycle
# arm draws routine-wash randoms the spike_decay-era cells never drew, so
# every v14 cell re-rolls against its v13 pair. A row is only a suppression
# candidate when the move is systematic, not a reshuffle: paired median
# recorded_onsets falling by more than half AND the takeoff-seed count
# dropping past the design's declared 20/200 drift band.
SUPPRESSION_RATIO = 0.5
TAKEOFF_COUNT_DRIFT_BAND = 20

PAIR_COLUMNS = (
    "theta",
    "seed",
    "infections_total",
    "attack_rate",
    "recorded_onsets",
    "index_onset_day",
    "index_shedding_at_day0",
    "parent_infections_total",
    "parent_attack_rate",
    "parent_recorded_onsets",
)


def _s3_client() -> Any:
    import boto3  # noqa: PLC0415 - imported lazily: only the CLI needs it

    return boto3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION"))


def _s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise SystemExit(f"--s3-prefix must be an s3:// URI, got {uri!r}")
    rest = uri[5:]
    bucket, _, prefix = rest.partition("/")
    return bucket, prefix.rstrip("/") + "/"


def _fetch_cell(client: Any, bucket: str, key: str) -> dict:
    body = client.get_object(Bucket=bucket, Key=key)["Body"]
    with body:
        return json.load(body)


def stream_cells(
    client: Any, bucket: str, prefix: str, *, workers: int = 32,
) -> dict[str, dict]:
    """Fetch every cell object under ``prefix`` cells/, parsed in memory.

    The entrypoint writes ``<prefix>cells/<cell.key>``; the v13 prefix has a
    doubled ``cells/cells/`` segment, so the listing takes every ``.json``
    object under the prefix whatever its depth. Fetches fan out across a
    small thread pool — sequential get_object on an 1,800-key row stalls
    the readout for tens of minutes.
    """
    keys: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        keys.extend(
            obj["Key"] for obj in page.get("Contents", [])
            if obj["Key"].endswith(".json")
        )
    payloads: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_fetch_cell, client, bucket, key): key
            for key in keys
        }
        for future in as_completed(futures):
            key = futures[future]
            payloads[key.rsplit("/", 1)[-1]] = future.result()
    return payloads


def _row_side(entry: dict[str, Any]) -> str | None:
    """Which side of the frozen selector a failing row sits on."""
    attack = entry.get("recorded_attack_rate") or {}
    median = attack.get("median")
    mean = attack.get("mean")
    if median is None or mean is None:
        return "no_cells"
    if entry.get("fleet_shape_ok"):
        return None
    if median < 0.0005:
        return "floor"
    if median > 0.008 or mean > 0.06:
        return "ceiling"
    return "iqr"


def _audit_cell(
    payload: dict[str, Any],
    expected_arm: str,
    expected_thetas: set[float],
    expected_design: str,
) -> list[str]:
    """Per-cell audit of the stage-1 generic-voyage contract.

    Lattice cells carry no declared replay geometry — index_onset_day /
    index_shedding_at_day0 are stage-2 fields. What a stage-1 cell must
    echo instead: the resolved hand mode and arm, the lattice theta, a
    drawn infection age, and a scoreable recorded_onsets channel.
    """
    failures: list[str] = []
    delivery = payload.get("delivery") or {}
    mode = delivery.get("hand_reservoir_mode")
    if mode != expected_arm:
        failures.append(
            f"delivery.hand_reservoir_mode {mode!r} != {expected_arm!r}",
        )
    cell = payload.get("cell") or {}
    if cell.get("arm_id") != expected_arm:
        failures.append(
            f"cell.arm_id {cell.get('arm_id')!r} != {expected_arm!r}",
        )
    if cell.get("theta") not in expected_thetas:
        failures.append(f"cell.theta {cell.get('theta')!r} not in the lattice")
    if cell.get("infection_age_days") is None:
        failures.append("cell.infection_age_days missing")
    if payload.get("design_id") != expected_design:
        failures.append(
            f"design_id {payload.get('design_id')!r} != {expected_design!r}",
        )
    if (payload.get("observables") or {}).get("recorded_onsets") is None:
        failures.append("observables.recorded_onsets missing")
    return failures


def _pairs(
    cells: dict[str, dict],
    parent_cells: dict[str, dict],
) -> dict[tuple[float, int], dict[str, Any]]:
    """Seed-paired deltas vs the parent surface at the same (theta, seed)."""
    parent_by_ts: dict[tuple[float, int], dict] = {}
    for payload in parent_cells.values():
        cell = payload.get("cell") or {}
        theta, seed = cell.get("theta"), cell.get("seed")
        if theta is None or seed is None:
            continue
        parent_by_ts[(float(theta), int(seed))] = payload
    paired: dict[tuple[float, int], dict[str, Any]] = {}
    for payload in cells.values():
        cell = payload.get("cell") or {}
        theta, seed = cell.get("theta"), cell.get("seed")
        if theta is None or seed is None:
            continue
        paired[(float(theta), int(seed))] = {
            "payload": payload,
            "parent": parent_by_ts.get((float(theta), int(seed))),
        }
    return paired


def _pair_row_stats(
    paired: dict[tuple[float, int], dict[str, Any]],
) -> dict[float, dict[str, Any]]:
    """Per-theta paired-delta summary against the parent cells."""
    by_theta: dict[float, dict[str, list]] = {}
    for (theta, _seed), rec in paired.items():
        parent = rec["parent"]
        if parent is None:
            continue
        obs = rec["payload"].get("observables") or {}
        p_obs = parent.get("observables") or {}
        cur = obs.get("recorded_onsets")
        par = p_obs.get("recorded_onsets")
        if cur is None or par is None:
            continue
        slot = by_theta.setdefault(theta, {"delta": [], "flips": 0.0, "n_par_takeoff": 0.0})
        slot["delta"].append(float(cur) - float(par))
        slot["flips"] += float(
            (cur >= TAKEOFF_MIN_ONSETS) != (par >= TAKEOFF_MIN_ONSETS)
        )
        slot["n_par_takeoff"] += float(par >= TAKEOFF_MIN_ONSETS)
    out: dict[float, dict[str, Any]] = {}
    for theta, slot in by_theta.items():
        deltas = slot["delta"]
        out[theta] = {
            "n_paired": len(deltas),
            "delta_recorded_onsets_median": quantile(deltas, 0.5),
            "delta_recorded_onsets_q05": quantile(deltas, 0.05),
            "delta_recorded_onsets_q95": quantile(deltas, 0.95),
            "takeoff_class_flips": int(slot["flips"]),
            "parent_takeoff_seeds": int(slot["n_par_takeoff"]),
        }
    return out


def _write_pairs_csv(paired: dict[tuple[float, int], dict[str, Any]], out: str) -> int:
    rows = []
    for (theta, seed), rec in sorted(paired.items()):
        payload, parent = rec["payload"], rec["parent"]
        obs = payload.get("observables") or {}
        p_obs = (parent or {}).get("observables") or {}
        rows.append({
            "theta": theta,
            "seed": seed,
            "infections_total": payload.get("infections_total"),
            "attack_rate": payload.get("attack_rate"),
            "recorded_onsets": obs.get("recorded_onsets"),
            "index_onset_day": payload.get("index_onset_day"),
            "index_shedding_at_day0": payload.get("index_shedding_at_day0"),
            "parent_infections_total": (parent or {}).get("infections_total"),
            "parent_attack_rate": (parent or {}).get("attack_rate"),
            "parent_recorded_onsets": p_obs.get("recorded_onsets"),
        })
    with validated_open(out, "w", allowed_roots=(REPO_ROOT,), newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=PAIR_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _fail_sides(surface: Iterable[dict[str, Any]], interior: set[float]) -> list[str]:
    return [
        side
        for side in (
            _row_side(e)
            for e in surface
            if e.get("theta") in interior and e.get("arm_id") != "spike_decay"
        )
        if side is not None
    ]


def _evaluate(surface: list[dict[str, Any]], interior: set[float], boundary: set[float]) -> dict[str, Any]:
    """Apply the frozen selector and the report-immediately triggers."""
    rows = [e for e in surface if e.get("arm_id") != "spike_decay"]
    admissible = sorted(
        e["theta"] for e in rows
        if e.get("theta") in interior and e.get("fleet_shape_ok")
    )
    boundary_pass = sorted(
        e["theta"] for e in rows
        if e.get("theta") in boundary and e.get("fleet_shape_ok")
    )
    sides = _fail_sides(surface, interior)
    takeoff = {
        e["theta"]: e.get("takeoff_probability") for e in rows
    }
    triggers: list[dict[str, Any]] = []
    if not admissible and sides and len(set(sides)) == 1:
        triggers.append({
            "trigger": "window_illusory",
            "detail": f"every interior row fails on the {sides[0]} side",
        })
    if not admissible and len(interior) >= 2:
        ordered = sorted(interior)
        first = next((e for e in rows if e.get("theta") == ordered[0]), None)
        last = next((e for e in rows if e.get("theta") == ordered[-1]), None)
        if (
            first is not None and last is not None
            and _row_side(first) == "ceiling" and _row_side(last) == "ceiling"
        ):
            triggers.append({
                "trigger": "window_illusory",
                "detail": "monotone overshoot at both interior ends",
            })
    if not admissible and boundary_pass:
        triggers.append({
            "trigger": "boundary_only_admissible",
            "detail": f"selector passes only at boundary {boundary_pass}",
        })
    low, high = min(boundary), max(boundary)
    if (takeoff.get(high) or 0.0) <= 0.0:
        triggers.append({
            "trigger": "takeoff_transition_outside_bracket",
            "detail": f"zero takeoff at boundary {high:g}",
        })
    if (takeoff.get(low) or 0.0) >= 1.0:
        triggers.append({
            "trigger": "takeoff_transition_outside_bracket",
            "detail": f"saturation (P(takeoff)>=1.0) at boundary {low:g}",
        })
    return {
        "admissible_thetas": admissible,
        "boundary_passing": boundary_pass,
        "interior_fail_sides": sides,
        "report_immediately": triggers,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", required=True)
    parser.add_argument("--s3-prefix", required=True)
    parser.add_argument("--parent-design", default=None)
    parser.add_argument("--parent-s3-prefix", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--surface-out", default=None)
    parser.add_argument("--pairs-out", default=None)
    parser.add_argument("--expected-cells", type=int, default=1800)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args(argv)

    design_path = resolve_repo_path(REPO_ROOT, args.design)
    design = load_design(design_path, repo_root=REPO_ROOT)
    expected_cells = {
        c.key for c in enumerate_cells(design) if c.arm_id == "hygiene_cycle"
    }

    client = _s3_client()
    bucket, prefix = _s3_uri(args.s3_prefix)
    payloads = {
        k: v for k, v in stream_cells(client, bucket, prefix).items()
        if k in expected_cells
    }
    if len(payloads) < args.expected_cells and not args.allow_partial:
        print(
            f"{len(payloads)} of {args.expected_cells} cells present; "
            "pass --allow-partial for a partial read",
            file=sys.stderr,
        )
        return 2

    audit_failures: dict[str, list[str]] = {}
    expected_thetas = set(design.thetas)
    for key, payload in payloads.items():
        failures = _audit_cell(
            payload, "hygiene_cycle", expected_thetas, design.design_id,
        )
        if failures:
            audit_failures[key] = failures

    parent_cells: dict[str, dict] = {}
    parent_surface: dict[str, Any] = {}
    if args.parent_s3_prefix and args.parent_design:
        p_bucket, p_prefix = _s3_uri(args.parent_s3_prefix)
        parent_cells = stream_cells(client, p_bucket, p_prefix)
        parent_design = load_design(
            resolve_repo_path(REPO_ROOT, args.parent_design), repo_root=REPO_ROOT,
        )
        parent_surface = merge_screen(parent_design, parent_cells, allow_partial=True)

    surface = merge_screen(design, payloads, allow_partial=True)
    thetas = sorted(design.thetas)
    interior = set(thetas[1:-1])
    boundary = {thetas[0], thetas[-1]}
    verdict = _evaluate(surface["surface"], interior, boundary)

    paired = _pairs(payloads, parent_cells) if parent_cells else {}
    pair_stats = _pair_row_stats(paired) if paired else {}
    for theta, stats in pair_stats.items():
        med = stats["delta_recorded_onsets_median"]
        flips = stats["takeoff_class_flips"]
        n = stats["n_paired"] or 1
        if med is not None:
            entry = next(
                (e for e in surface["surface"] if e.get("theta") == theta
                 and e.get("arm_id") == "hygiene_cycle"),
                None,
            )
            p_med = None
            for p_entry in (parent_surface.get("surface") or []):
                if p_entry.get("theta") == theta:
                    p_med = ((p_entry.get("recorded_onsets") or {}).get("median"))
            suppression = (
                p_med is not None and p_med > 0
                and med / p_med <= -SUPPRESSION_RATIO
            )
            stats["suppression_candidate"] = bool(
                suppression and flips > TAKEOFF_COUNT_DRIFT_BAND * n / 200.0,
            )
            if stats["suppression_candidate"]:
                verdict["report_immediately"].append({
                    "trigger": "suppression_shaped_delta",
                    "theta": theta,
                    "detail": (
                        f"paired median recorded_onsets {med:g} vs parent "
                        f"median {p_med:g}; takeoff flips {flips}"
                    ),
                })

    report = {
        "cells_found": len(payloads),
        "cells_expected": args.expected_cells,
        "audit_failures": audit_failures,
        "surface": surface["surface"],
        "admissible_thetas": verdict["admissible_thetas"],
        "boundary_passing": verdict["boundary_passing"],
        "interior_fail_sides": verdict["interior_fail_sides"],
        "paired_vs_v13": pair_stats,
        "report_immediately": verdict["report_immediately"],
        "coverage": surface["coverage"],
        "sanitary_witness": surface["sanitary_witness"],
    }

    if args.out:
        out_path = resolve_repo_path(REPO_ROOT, args.out)
        prepare_output_directory(
            os.path.dirname(out_path) or REPO_ROOT,
            allowed_roots=(REPO_ROOT,),
        )
        with validated_open(out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
    if args.surface_out:
        write_surface_csv(surface, resolve_repo_path(REPO_ROOT, args.surface_out))
    if args.pairs_out:
        _write_pairs_csv(paired, resolve_repo_path(REPO_ROOT, args.pairs_out))

    print(
        f"{report['cells_found']}/{args.expected_cells} cells; "
        f"{len(audit_failures)} audit failures",
    )
    for entry in surface["surface"]:
        attack = entry.get("recorded_attack_rate") or {}
        print(
            f"theta={entry.get('theta'):.4g} arm={entry.get('arm_id')} "
            f"median={attack.get('median')} mean={attack.get('mean')} "
            f"fleet_shape_ok={entry.get('fleet_shape_ok')}",
        )
    print("admissible:", verdict["admissible_thetas"])
    if verdict["report_immediately"]:
        print("REPORT_IMMEDIATELY:", json.dumps(verdict["report_immediately"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
