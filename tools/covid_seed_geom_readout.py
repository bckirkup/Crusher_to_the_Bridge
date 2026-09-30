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

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    KEY_INDEX_ONSET_DAY,
    KEY_INDEX_SHEDDING_AT_DAY0,
    enumerate_cells,
    load_design,
)
from simulation_utils.paths import repo_root  # noqa: E402
from tools.covid_screen_readout_common import (  # noqa: E402
    anchor_legs,
    band_stats,
    quantile,
    resolve_design_arg,
    run_readout,
    takeoff_split,
)

REPO_ROOT = repo_root()


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


def audit_cell(
    payload: dict, declared: dict, theta: float | None = None,
) -> list[str]:
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
    takeoff, vectors = takeoff_split(payloads)
    shed_flags = [
        p.get(KEY_INDEX_SHEDDING_AT_DAY0) for p in payloads
        if p.get(KEY_INDEX_SHEDDING_AT_DAY0) is not None
    ]
    return {
        "n": len(payloads),
        "takeoff_n": len(takeoff),
        "recorded_onsets": band_stats(vectors["rec"]),
        "before_share": {"median": quantile(vectors["shares"], 0.5)},
        "index_shedding_day0_fraction": (
            sum(bool(f) for f in shed_flags) / len(shed_flags)
            if shed_flags else None
        ),
        "takeoff_recorded_onsets": band_stats(vectors["t_rec"]),
        "takeoff_infections_total": band_stats(vectors["t_inf"]),
        "takeoff_before_share": band_stats(vectors["t_share"]),
        **{
            k: v for k, v in anchor_legs(
                len(takeoff), vectors["t_inf"], vectors["t_share"],
            ).items()
            if k != "enough_takeoff"
        },
    }


def _in_band_trigger(
    theta: float, arm_id: str, stats: dict,
) -> dict | None:
    if not (stats["truth_leg_in_band"] or stats["timing_leg_in_band"]):
        return None
    return {
        "theta": theta, "arm_id": arm_id,
        "truth_leg_in_band": stats["truth_leg_in_band"],
        "timing_leg_in_band": stats["timing_leg_in_band"],
        "takeoff_infections_total": stats["takeoff_infections_total"],
        "takeoff_before_share": stats["takeoff_before_share"],
    }


def main(argv: list[str] | None = None) -> int:
    design = load_design(
        resolve_design_arg(argv, REPO_ROOT), repo_root=REPO_ROOT,
    )
    return run_readout(
        argv,
        repo_root=REPO_ROOT,
        cells=enumerate_cells(design),
        declared_by_arm={
            arm["arm_id"]: _declared(arm) for arm in (design.arms or ())
        },
        audit_cell=audit_cell,
        row_stats=_row_stats,
        report_key="in_band_landings",
        row_triggers=_in_band_trigger,
    )


if __name__ == "__main__":
    raise SystemExit(main())
