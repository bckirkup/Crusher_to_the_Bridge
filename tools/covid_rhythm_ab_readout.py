"""COVID-RHYTHM-01 readout: pool the paired rhythm A/B cells.

Reads the per-seed cell JSONs the Batch array wrote
(``tools/covid_rhythm_ab.run_cell`` payloads — fetched from S3 or a local
directory) and pools them by (class_id, arm) into the six numbers the
ledger reports:

1. exposure-set metrics (dosed-set size, challenged share, route split);
2. takeoff burn (recorded-onset distribution, clause ratio vs ~197,
   before_share);
3. clock correlation (transit occupancy vs synchronized-end mask);
4. anchor readout (takeoff gate, H1/H2 on the expedition leg, H3
   fleet-shape placement per class);
5. class scoping (passenger occupants and challenges inside crew-only
   zones);
6. the paired A/B deltas against the paired-seed spread.

Usage:
    python3 tools/covid_rhythm_ab_readout.py \
        --cells-dir /path/to/cells --out readout.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    FLEET_IQR_WINDOW,
    FLEET_MEAN_MAX,
    FLEET_MEDIAN_WINDOW,
)
from picard_framework.covid_fit_targets import load_fit_targets  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    resolve_repo_path,
    safe_listdir,
    validated_open,
)
from tools.covid_route_attribution import _quantiles  # noqa: E402

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))

CHANNELS = (
    "cabin_mate_ring",
    "dining_ring",
    "near_field_plume",
    "zone_pool",
    "hvac_airborne",
    "contact",
    "other",
)

T1_RECORDED_ONSETS = 197.0
T1_BEFORE_SHARE = 34.0 / 197.0
HELD_OUT_TOLERANCE = 0.1


def _cell_summaries(cells_dir: str) -> list[dict[str, Any]]:
    safe_dir = resolve_repo_path(REPO_ROOT, cells_dir)
    rows = []
    for name in sorted(safe_listdir(safe_dir, allowed_roots=(REPO_ROOT,))):
        if not name.endswith(".json"):
            continue
        with validated_open(
            os.path.join(safe_dir, name), "r",
            allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as handle:
            payload = json.load(handle)
        if "summary" not in payload or "cell" not in payload:
            continue
        payload["_file"] = name
        rows.append(payload)
    return rows


def _recorded(c: dict[str, Any]) -> float:
    obs = c.get("payload_observables") or {}
    return float(obs.get("recorded_onsets") or c["summary"]["recorded_onsets"])


def _before_share(c: dict[str, Any]) -> float | None:
    obs = c.get("payload_observables") or {}
    recorded = _recorded(c)
    if recorded <= 0:
        return None
    return float(obs.get("onsets_before_split_day") or 0) / recorded


def _attack_rate(c: dict[str, Any]) -> float | None:
    """Recorded attack rate — the H3 channel, not the truth channel."""
    aboard = c.get("aboard_total")
    if not aboard:
        return None
    return _recorded(c) / float(aboard)


def _p_infection_mean(c: dict[str, Any]) -> float | None:
    """Mean counterfactual P(infection) over challenged-uninfected hosts."""
    acc = (
        c["summary"].get("mechanism", {}).get("susceptibility", {})
        .get("accrued_hazard", {})
    )
    value = acc.get("challenged_uninfected_p_infection_mean")
    return float(value) if value is not None else None


def _t1_clause(cells: list[dict[str, Any]], takeoff_min: int) -> dict[str, Any]:
    """The conditional_trajectory_clause, verbatim from v12 stage 2.

    Scored among takeoff seeds only: q05-q95 of recorded_onsets contains
    197 AND median before_share within 0.10 of 0.173; scored only when
    >= 5 takeoff seeds, else 'insufficient takeoff mass'.
    """
    taken = [c for c in cells if _recorded(c) >= takeoff_min]
    if len(taken) < 5:
        return {
            "takeoff_seeds": len(taken),
            "verdict": "insufficient takeoff mass",
        }
    onsets = _quantiles([_recorded(c) for c in taken])
    before = [s for s in (_before_share(c) for c in taken) if s is not None]
    before_median = _quantiles(before)["median"]
    contains = (
        onsets["q05"] is not None
        and onsets["q05"] <= T1_RECORDED_ONSETS <= onsets["q95"]
    )
    before_ok = (
        before_median is not None
        and abs(before_median - T1_BEFORE_SHARE) <= 0.10
    )
    near_target = [
        0.5 * T1_RECORDED_ONSETS <= _recorded(c) <= 2.0 * T1_RECORDED_ONSETS
        for c in taken
    ]
    return {
        "takeoff_seeds": len(taken),
        "recorded_onsets": onsets,
        "clause_ratio": (
            onsets["median"] / T1_RECORDED_ONSETS
            if onsets["median"] is not None else None
        ),
        "before_share_median": before_median,
        "before_share_quantiles": _quantiles(before),
        "onset_mass_near_197": (
            sum(near_target) / len(near_target) if near_target else None
        ),
        "verdict": "pass" if (contains and before_ok) else "fail",
    }


def _exposure_pool(cells: list[dict[str, Any]]) -> dict[str, Any]:
    mechanisms = [c["summary"].get("mechanism", {}) for c in cells]
    dosed = [
        m.get("dosed_targets_by_epoch") for m in mechanisms
        if m.get("dosed_targets_by_epoch", {}).get("median") is not None
    ]
    challenged = [
        float(m["susceptibility"]["challenged_share_of_aboard"])
        for m in mechanisms
        if m.get("susceptibility", {}).get("challenged_share_of_aboard")
        is not None
    ]
    shares = {
        chan: _quantiles([
            float(c["summary"]["route_split"]["by_onset_share"].get(chan))
            for c in cells
            if c["summary"]["route_split"]["by_onset_share"].get(chan)
            is not None
        ])
        for chan in CHANNELS
    }
    haz = [
        m["susceptibility"]["accrued_hazard"] for m in mechanisms
        if m.get("susceptibility", {}).get("accrued_hazard")
    ]

    def _haz(key: str) -> list[float]:
        return [
            float(h[key]) for h in haz if h.get(key) is not None
        ]

    return {
        "dosed_targets_by_epoch_median": _quantiles([
            float(d["median"]) for d in dosed
        ]),
        "dosed_targets_by_epoch_q95_max": (
            max(float(d["q95"]) for d in dosed) if dosed else None
        ),
        "challenged_share_of_aboard": _quantiles(challenged),
        "accrued_hazard": {
            "challenged_uninfected_median": _quantiles([
                float(h["challenged_uninfected"]["median"]) for h in haz
                if h.get("challenged_uninfected", {}).get("median")
                is not None
            ]),
            "challenged_uninfected_p_infection_mean": _quantiles(
                _haz("challenged_uninfected_p_infection_mean")
            ),
            "share_p_ge_0p5": _quantiles(
                _haz("challenged_uninfected_share_p_ge_0p5")
            ),
            "share_p_ge_0p1": _quantiles(
                _haz("challenged_uninfected_share_p_ge_0p1")
            ),
            "never_challenged_hosts": _quantiles(
                _haz("never_challenged_hosts")
            ),
        },
        "route_split_onset_share_quantiles": shares,
    }


def _clock_pool(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Corridor occupancy vs the catalog synchronized-end mask."""
    blocks = [c["summary"].get("rhythm_ab") or {} for c in cells]
    return {
        "sync_end_epochs": _quantiles([
            float(b["sync_end_epochs"]) for b in blocks
            if b.get("sync_end_epochs") is not None
        ]),
        "occupancy_mean_at_sync_end": _quantiles([
            float(b["occupancy_mean_at_sync_end"]) for b in blocks
            if b.get("occupancy_mean_at_sync_end") is not None
        ]),
        "occupancy_mean_other": _quantiles([
            float(b["occupancy_mean_other"]) for b in blocks
            if b.get("occupancy_mean_other") is not None
        ]),
        "occupancy_lift_at_sync_end": _quantiles([
            float(b["occupancy_lift_at_sync_end"]) for b in blocks
            if b.get("occupancy_lift_at_sync_end") is not None
        ]),
        "occupancy_sync_corr": _quantiles([
            float(b["occupancy_sync_corr"]) for b in blocks
            if b.get("occupancy_sync_corr") is not None
        ]),
    }


def _scoping_pool(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """The emptiness measurement inside crew-only zones."""
    blocks = [c["summary"].get("rhythm_ab") or {} for c in cells]
    challenge_epochs = [
        int(b.get("crew_zone_passenger_challenge_epochs") or 0)
        for b in blocks
    ]
    return {
        "crew_zones_n": blocks[0].get("crew_zones"),
        "passenger_epochs_in_crew_zones": {
            "seeds_with_any": sum(
                1 for b in blocks
                if (b.get("crew_zone_passenger_epochs") or 0) > 0
            ),
            "max_concurrent_passengers": max(
                (int(b.get("crew_zone_passenger_max") or 0) for b in blocks),
                default=None,
            ),
        },
        "passenger_challenge_epochs_in_crew_zones": {
            "seeds_with_any": sum(1 for v in challenge_epochs if v > 0),
            "total_epochs": sum(challenge_epochs),
        },
    }


def _fleet_shape(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """covid.H3 placement per class: the recorded attack-rate shape."""
    rates = [r for r in (_attack_rate(c) for c in cells) if r is not None]
    if not rates:
        return {"n": 0, "h3_placement": "no recorded aboard totals"}
    q = _quantiles(rates)
    iqr_overlaps = not (
        q["q75"] < FLEET_IQR_WINDOW[0] or q["q25"] > FLEET_IQR_WINDOW[1]
    )
    return {
        "n": len(rates),
        "recorded_attack_rate": {
            "median": q["median"], "mean": q["mean"],
            "q25": q["q25"], "q75": q["q75"],
        },
        "h3_placement": bool(
            FLEET_MEDIAN_WINDOW[0] <= q["median"] <= FLEET_MEDIAN_WINDOW[1]
            and iqr_overlaps
            and q["mean"] <= FLEET_MEAN_MAX
        ),
    }


def _held_out_scores(
    cells: list[dict[str, Any]],
    targets: Any,
) -> list[dict[str, Any]]:
    """covid.H1/H2 scored verbatim where the leg is greg_mortimer_2020."""
    if not any(
        c["cell"].get("scenario_id") == "greg_mortimer_2020" for c in cells
    ):
        return []
    h1 = targets.by_id("covid.H1")
    h2 = targets.by_id("covid.H2")
    positives = [
        c["payload_observables"]["positive_share"]
        for c in cells if c["cell"].get("scenario_id") == "greg_mortimer_2020"
        and c.get("payload_observables", {}).get("positive_share") is not None
    ]
    asym = [
        c["payload_observables"]["asymptomatic_share"]
        for c in cells if c["cell"].get("scenario_id") == "greg_mortimer_2020"
        and c.get("payload_observables", {}).get("asymptomatic_share")
        is not None
    ]

    def verdict(obs: float | None, target: float) -> str:
        if obs is None:
            return "undefined"
        return "hit" if abs(obs - target) <= HELD_OUT_TOLERANCE else "miss"

    h1_med = _quantiles(positives)["median"]
    h2_med = _quantiles(asym)["median"]
    return [
        {
            "anchor_id": "covid.H1",
            "observed_median": h1_med,
            "target": float(h1.values["share"]),
            "verdict": verdict(h1_med, float(h1.values["share"])),
        },
        {
            "anchor_id": "covid.H2",
            "observed_median": h2_med,
            "target": float(h2.values["share"]),
            "verdict": verdict(h2_med, float(h2.values["share"])),
        },
    ]


def _arm_pool(
    cells: list[dict[str, Any]],
    takeoff_min: int,
    targets: Any,
) -> dict[str, Any]:
    takeoff = _t1_clause(cells, takeoff_min)
    return {
        "n_cells": len(cells),
        "recorded_onsets": _quantiles([_recorded(c) for c in cells]),
        "takeoff_probability": (
            sum(1 for c in cells if _recorded(c) >= takeoff_min)
            / len(cells)
        ),
        "takeoff": takeoff,
        "exposure_set": _exposure_pool(cells),
        "clock_correlation": _clock_pool(cells),
        "class_scoping": _scoping_pool(cells),
        "h3_fleet_shape": _fleet_shape(cells),
        "held_out": _held_out_scores(cells, targets),
    }


def _paired_spread(
    off: list[dict[str, Any]],
    on: list[dict[str, Any]],
) -> dict[str, Any]:
    """Per-seed A/B deltas against the declared paired-seed spread.

    The effect is real only where the |off-on| median exceeds the
    paired-seed spread within the off arm itself (neighbouring-seed
    absolute differences, the TAKEOFF-ATTR-01 null).
    """
    by_seed_off = {c["cell"]["seed"]: c for c in off}
    by_seed_on = {c["cell"]["seed"]: c for c in on}
    paired = sorted(set(by_seed_off) & set(by_seed_on))
    deltas = [
        _recorded(by_seed_on[s]) - _recorded(by_seed_off[s])
        for s in paired
    ]
    off_sorted = sorted(_recorded(by_seed_off[s]) for s in paired)
    spread = [
        abs(b - a) for a, b in zip(off_sorted, off_sorted[1:])
    ]
    challenged_off = [
        float(c["summary"]["mechanism"]["susceptibility"]
              ["challenged_share_of_aboard"])
        for c in off
        if c["summary"].get("mechanism", {}).get("susceptibility")
    ]
    challenged_on = [
        float(c["summary"]["mechanism"]["susceptibility"]
              ["challenged_share_of_aboard"])
        for c in on
        if c["summary"].get("mechanism", {}).get("susceptibility")
    ]
    return {
        "n_paired_seeds": len(paired),
        "recorded_onsets_delta": _quantiles([abs(d) for d in deltas]),
        "recorded_onsets_off_seed_spread": _quantiles(spread),
        "effect_exceeds_spread": bool(
            deltas
            and _quantiles([abs(d) for d in deltas])["median"]
            > (_quantiles(spread)["median"] or 0.0)
        ),
        "challenged_share_off_median": (
            _quantiles(challenged_off)["median"]
        ),
        "challenged_share_on_median": (
            _quantiles(challenged_on)["median"]
        ),
        "challenged_share_dropped": bool(
            challenged_on and _quantiles(challenged_on)["q95"] < 1.0
        ),
        "p_infection_mean_off_median": _quantiles([
            _p_infection_mean(c) for c in off
            if _p_infection_mean(c) is not None
        ])["median"],
        "p_infection_mean_on_median": _quantiles([
            _p_infection_mean(c) for c in on
            if _p_infection_mean(c) is not None
        ])["median"],
    }


def _group_cells(
    cells: list[dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Cell payloads keyed by (class_id, arm_id)."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for c in cells:
        groups.setdefault(
            (str(c["cell"]["class_id"]), str(c["cell"]["arm_id"])),
            [],
        ).append(c)
    return groups


def _emit_text(text: str, out: str | None) -> None:
    """Write the readout to --out under the repo root, else stdout."""
    if out:
        out_path = resolve_repo_path(REPO_ROOT, out)
        with validated_open(
            out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as handle:
            handle.write(text)
        print(f"wrote {out_path}")
    else:
        print(text)


def pool(
    cells: list[dict[str, Any]],
    *,
    takeoff_min: int = 10,
) -> dict[str, Any]:
    groups = _group_cells(cells)
    targets = load_fit_targets()
    classes: dict[str, Any] = {}
    for class_id in sorted({k[0] for k in groups}):
        arms = {
            arm: _arm_pool(pool, takeoff_min, targets)
            for (cid, arm), pool in sorted(groups.items())
            if cid == class_id
        }
        entry: dict[str, Any] = {"arms": arms}
        if "off" in arms and "on" in arms:
            entry["paired_ab"] = _paired_spread(
                groups[(class_id, "off")], groups[(class_id, "on")],
            )
        classes[class_id] = entry
    return {
        "design": "covid_rhythm_ab_v1",
        "takeoff_recorded_onsets": takeoff_min,
        "n_cells": len(cells),
        "classes": classes,
    }


def main() -> None:  # pragma: no cover - CLI driver
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cells-dir", required=True)
    parser.add_argument("--takeoff-min", type=int, default=10)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    cells = _cell_summaries(args.cells_dir)
    if not cells:
        raise SystemExit(f"no cell payloads under {args.cells_dir}")
    text = json.dumps(pool(cells, takeoff_min=args.takeoff_min),
                      indent=1, default=str)
    _emit_text(text, args.out)


if __name__ == "__main__":
    main()
