"""SEED-GEOM-V1 readout: audit echoes + the both-legs test per (theta, arm).

Pools the synced campaign cells (``aws s3 sync .../cells/ <dir>``) for
``covid_seed_geom_v1`` and reports, per (theta, arm) row:

* the index-geometry audit (payload echo vs the arm's declared patch —
  seed_spec, seeded_count, seeded_hosts role, index_onset_day,
  index_shedding_at_day0, exposure_cap_include_fixed_rings),
* takeoff-seed medians and q05-q95 of recorded_onsets, infections_total
  and before_share (the two anchors: 197 / 0.173 vs the H5 band
  [712, 960]),
* the report-immediately triggers: any row whose takeoff-seed
  infections_total median lands inside [712, 960] or whose before_share
  median lands inside 0.173 +/- 0.10.

CLI paths are confined under the repository root (sync cells to
``campaign_results/<design>/cells/``); an audit failure is reported per
cell.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    KEY_INDEX_ONSET_DAY,
    KEY_INDEX_SHEDDING_AT_DAY0,
    enumerate_cells,
    load_design,
)
from simulation_utils.paths import (  # noqa: E402
    repo_root,
    resolve_child_path,
    resolve_repo_path,
    validated_open,
)

REPO_ROOT = repo_root()

TAKEOFF_MIN_ONSETS = 10
T1_RECORDED = 197.0
T1_BEFORE_SHARE = 0.173
BEFORE_SHARE_TOL = 0.10
H5_BAND = (712.0, 960.0)
MIN_TAKEOFF_SEEDS = 5


def _q(values: list[float], p: float) -> float | None:
    if not values:
        return None
    srt = sorted(values)
    i = min(len(srt) - 1, max(0, int(round(p * (len(srt) - 1)))))
    return float(srt[i])


def _declared(arm: dict) -> dict:
    """The arm's declared seed geometry + channel expectations."""
    patch = (arm.get("overrides") or {}).get("seed_patch") or {}
    tx = (arm.get("overrides") or {}).get("transmission_overrides") or {}
    om = (
        (arm.get("overrides") or {})
        .get("pathogen_overrides", {})
        .get("sars_cov2_resp", {})
        .get("observation_model", {})
    )
    return {
        "onset_day": patch.get("onset_day", -1.0),
        "count": patch.get("count", 1),
        "role": patch.get("role", "passenger"),
        "role_removed": "role" in patch and patch["role"] is None,
        "include_fixed_rings": (
            (tx.get("exposure_cap") or {}).get("include_fixed_rings")
        ),
        "onset_recording": om.get("onset_recording"),
        "eligibility": om.get("syndrome_case_eligibility_by_severity"),
    }


def _audit_seed_echoes(ring: dict, declared: dict) -> list[str]:
    """seed_spec / seeded_count / seeded_hosts vs the declared patch."""
    failures: list[str] = []
    spec = ring.get("seed_spec") or {}
    for key in ("onset_day", "count"):
        if spec.get(key) != declared[key]:
            failures.append(
                f"seed_spec.{key} {spec.get(key)} "
                f"!= declared {declared[key]}",
            )
    if declared["role_removed"]:
        if "role" in spec:
            failures.append("seed_spec.role present on a role-removed arm")
    elif spec.get("role") != declared["role"]:
        failures.append(
            f"seed_spec.role {spec.get('role')} "
            f"!= declared {declared['role']}",
        )
    if ring.get("seeded_count") != declared["count"]:
        failures.append(
            f"seeded_count {ring.get('seeded_count')} "
            f"!= declared {declared['count']}",
        )
    if not declared["role_removed"]:
        bad = [
            h for h in ring.get("seeded_hosts") or []
            if h.get("role") != declared["role"]
        ]
        if bad:
            failures.append(
                f"{len(bad)} seeded host(s) with role outside "
                f"{declared['role']!r}",
            )
    return failures


def _audit_index_echo(payload: dict, declared: dict) -> list[str]:
    """index_onset_day echo check (stamps whenever the index presents,
    including post-departure illness on the silent-aboard arms).
    index_shedding_at_day0 is a derived readback — report-only."""
    onset = payload.get(KEY_INDEX_ONSET_DAY)
    declared_onset = float(declared["onset_day"])
    if onset is None:
        return ["index_onset_day null on a presenting index"]
    if abs(float(onset) - declared_onset) > 0.05:
        return [
            f"index_onset_day {onset} != declared {declared_onset}",
        ]
    return []


def _audit_channel_echoes(payload: dict, declared: dict) -> list[str]:
    """exposure-cap flag and the REF arm's channel echoes."""
    failures: list[str] = []
    if payload.get("exposure_cap_include_fixed_rings") != (
        declared["include_fixed_rings"]
    ):
        failures.append(
            "exposure_cap_include_fixed_rings "
            f"{payload.get('exposure_cap_include_fixed_rings')} "
            f"!= declared {declared['include_fixed_rings']}",
        )
    if declared["onset_recording"] is not None and (
        payload.get("onset_recording") != declared["onset_recording"]
    ):
        failures.append("onset_recording echo != declared block")
    if declared["eligibility"] is not None and (
        payload.get("onset_eligibility_by_severity")
        != declared["eligibility"]
    ):
        failures.append(
            "onset_eligibility_by_severity echo != declared ladder",
        )
    return failures


def audit_cell(payload: dict, declared: dict) -> list[str]:
    """Return the list of audit violations for one cell payload."""
    ring = payload.get("seed_ring")
    if not isinstance(ring, dict):
        return ["missing seed_ring block"]
    return (
        _audit_seed_echoes(ring, declared)
        + _audit_index_echo(payload, declared)
        + _audit_channel_echoes(payload, declared)
    )


def _row_stats(payloads: list[dict]) -> dict:
    """Takeoff-conditional medians/quantiles for one (theta, arm) row."""
    obs = [p["observables"] for p in payloads]
    takeoff = [
        p for p, o in zip(payloads, obs)
        if int(o["recorded_onsets"]) >= TAKEOFF_MIN_ONSETS
    ]
    rec = [float(o["recorded_onsets"]) for o in obs]
    shares = [
        float(o["onsets_before_split_day"]) / float(o["recorded_onsets"])
        for o in obs
        if int(o["recorded_onsets"]) > 0
    ]
    t_rec = [float(p["observables"]["recorded_onsets"]) for p in takeoff]
    t_inf = [
        float(p["infections_total"]) for p in takeoff
        if p.get("infections_total") is not None
    ]
    t_share = [
        float(p["observables"]["onsets_before_split_day"])
        / float(p["observables"]["recorded_onsets"])
        for p in takeoff
    ]
    shed_flags = [
        p.get(KEY_INDEX_SHEDDING_AT_DAY0) for p in payloads
        if p.get(KEY_INDEX_SHEDDING_AT_DAY0) is not None
    ]
    med_inf = _q(t_inf, 0.5)
    med_share = _q(t_share, 0.5)
    enough = len(takeoff) >= MIN_TAKEOFF_SEEDS
    in_band = (
        med_inf is not None and H5_BAND[0] <= med_inf <= H5_BAND[1]
    )
    timing_hit = (
        med_share is not None
        and abs(med_share - T1_BEFORE_SHARE) <= BEFORE_SHARE_TOL
    )
    return {
        "n": len(payloads),
        "takeoff_n": len(takeoff),
        "recorded_onsets": {
            "median": _q(rec, 0.5), "q05": _q(rec, 0.05),
            "q95": _q(rec, 0.95),
        },
        "before_share": {"median": _q(shares, 0.5)},
        "index_shedding_day0_fraction": (
            sum(bool(f) for f in shed_flags) / len(shed_flags)
            if shed_flags else None
        ),
        "takeoff_recorded_onsets": {
            "median": _q(t_rec, 0.5), "q05": _q(t_rec, 0.05),
            "q95": _q(t_rec, 0.95),
        },
        "takeoff_infections_total": {
            "median": med_inf, "q05": _q(t_inf, 0.05),
            "q95": _q(t_inf, 0.95),
        },
        "takeoff_before_share": {
            "median": med_share, "q05": _q(t_share, 0.05),
            "q95": _q(t_share, 0.95),
        },
        "truth_leg_in_band": bool(in_band and enough),
        "timing_leg_in_band": bool(timing_hit and enough),
        "both_legs": bool(in_band and timing_hit and enough),
    }


def _load_payloads(cells_dir: str) -> dict[str, dict]:
    """Read every cell JSON under *cells_dir* (contained to the dir)."""
    payloads: dict[str, dict] = {}
    for name in sorted(os.listdir(cells_dir)):
        if not name.endswith(".json"):
            continue
        path = resolve_child_path(cells_dir, name)
        with validated_open(
            path, allowed_roots=(cells_dir,), encoding="utf-8",
        ) as fh:
            payloads[name] = json.load(fh)
    return payloads


def _audit_all(
    payloads: dict[str, dict],
    cells: list,
    declared_by_arm: dict[str, dict],
) -> tuple[dict[str, list[str]], dict[tuple, list[dict]]]:
    """Audit each payload and bucket by (theta, arm)."""
    by_key = {(c.theta, c.arm_id, c.seed): c for c in cells}
    audit_failures: dict[str, list[str]] = {}
    rows: dict[tuple, list[dict]] = {}
    for name, payload in payloads.items():
        cell = payload.get("cell") or {}
        key = (
            float(cell.get("theta")), cell.get("arm_id"),
            int(cell.get("seed")),
        )
        if key not in by_key:
            audit_failures[name] = ["cell key not in the declared lattice"]
            continue
        declared = declared_by_arm.get(cell.get("arm_id"))
        failures = audit_cell(payload, declared) if declared else [
            f"unknown arm {cell.get('arm_id')}",
        ]
        if failures:
            audit_failures[name] = failures
        rows.setdefault((key[0], key[1]), []).append(payload)
    return audit_failures, rows


def _print_rows(report: dict) -> None:
    for label, stats in report["rows"].items():
        ti = stats["takeoff_infections_total"]
        ts = stats["takeoff_before_share"]
        tr = stats["takeoff_recorded_onsets"]
        flags = []
        if stats["truth_leg_in_band"]:
            flags.append("TRUTH-IN-BAND")
        if stats["timing_leg_in_band"]:
            flags.append("TIMING-IN-BAND")

        def med(v: float | None) -> str:
            return "n/a" if v is None else f"{v:.3g}"

        print(
            f"  {label}: takeoff {stats['takeoff_n']}/{stats['n']} "
            f"rec med {med(tr['median'])} "
            f"[{med(tr['q05'])},{med(tr['q95'])}] "
            f"inf med {med(ti['median'])} "
            f"[{med(ti['q05'])},{med(ti['q95'])}] "
            f"bshr med {med(ts['median'])} {' '.join(flags)}",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument(
        "--allow-partial", action="store_true",
        help="read whatever cells exist (canary/incomplete arrays)",
    )
    args = parser.parse_args(argv)

    cells_dir = resolve_repo_path(REPO_ROOT, args.cells)
    design_path = resolve_repo_path(REPO_ROOT, args.design)
    design = load_design(design_path, repo_root=REPO_ROOT)
    cells = enumerate_cells(design)
    declared_by_arm = {
        arm["arm_id"]: _declared(arm) for arm in (design.arms or ())
    }

    payloads = _load_payloads(cells_dir)
    if not args.allow_partial and len(payloads) < len(cells):
        print(
            f"{len(payloads)} of {len(cells)} cells present; "
            "pass --allow-partial for a partial read",
            file=sys.stderr,
        )
        return 2

    audit_failures, rows = _audit_all(payloads, cells, declared_by_arm)

    report = {
        "cells_found": len(payloads),
        "cells_expected": len(cells),
        "audit_failures": audit_failures,
        "rows": {},
        "in_band_landings": [],
    }
    for (theta, arm_id), row in sorted(rows.items()):
        stats = _row_stats(row)
        report["rows"][f"theta={theta:.4g}|arm={arm_id}"] = stats
        if stats["truth_leg_in_band"] or stats["timing_leg_in_band"]:
            report["in_band_landings"].append(
                {
                    "theta": theta, "arm_id": arm_id,
                    "truth_leg_in_band": stats["truth_leg_in_band"],
                    "timing_leg_in_band": stats["timing_leg_in_band"],
                    "takeoff_infections_total": (
                        stats["takeoff_infections_total"]
                    ),
                    "takeoff_before_share": stats["takeoff_before_share"],
                },
            )

    if args.out:
        out_path = resolve_repo_path(REPO_ROOT, args.out)
        with validated_open(
            out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as fh:
            json.dump(report, fh, indent=2, sort_keys=True)

    print(
        f"{report['cells_found']}/{report['cells_expected']} cells; "
        f"{len(audit_failures)} audit failures",
    )
    _print_rows(report)
    if report["in_band_landings"]:
        print("IN-BAND LANDINGS:", json.dumps(
            report["in_band_landings"], indent=1,
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
