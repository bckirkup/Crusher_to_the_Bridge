#!/usr/bin/env python3
"""H5-RESCORE-01: the truth-side scored surface on the committed refit grid.

ONSET-FUNNEL-01 measured the fitted theta landing magnitude by saturating
true incidence the observation layer cannot see: the scored contract
(covid.T1 recorded onsets + covid.T3 campaign positives, log-residual,
equal weights) has no attack-size term, while covid.H5 - the
serology-informed true-infection band [712, 960] on ``infections_total``
- exists as a held-out anchor and enters no scored term.

Every THETA-REFIT-01 cell payload already carries ``infections_total``,
so the surface that contract revision would see is a pure readout of the
committed cells: no re-run, same realizations. For each theta on the DP
fit grid this reports the verbatim contract loss, the takeoff fraction
(the scorer's ``recorded_onsets >= 10`` gate), and the H5 diagnostics the
anchor itself declares: band membership scored only on takeoff seeds (the
anchor is a burn-seed draw, not the set of all voyages) with the >=5
takeoff-seed reporting floor the screens used. The candidate H5 term is a
log-space band residual on ``infections_total`` - zero inside the band,
log distance to the nearest edge outside it - and the augmented candidate
contract (verbatim loss + H5 term, equal weight, declared not tuned) is
scored with the same paired-bootstrap selection frequency as the shipped
merge. Both selections are reported; neither is adopted - this is a
measurement of what a serology-aware contract would select, not a refit.

GM is held out and carries no serology band: its per-theta block reports
positives, shares and ``infections_total`` for context only.

Usage:
    python3 tools/covid_h5_rescore.py \
        --cells <dir> [--cells <dir>] --out <json>

``--cells`` and ``--out`` resolve against the repository root regardless
of the caller's working directory, so sync payloads into the checkout.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from simulation_utils.paths import resolve_repo_path, validated_open  # noqa: E402

H5_BAND = (712.0, 960.0)
TAKEOFF_SEED_FLOOR = 5
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20200205


def _h5_band_residual(infections_total: float) -> float:
    """Log-space distance of ``infections_total`` from the H5 band."""
    lo, hi = H5_BAND
    inf = max(float(infections_total), 1.0)
    if inf < lo:
        return float(np.log(lo / inf))
    if inf > hi:
        return float(np.log(inf / hi))
    return 0.0


def _objective() -> Any:
    """The verbatim scored contract (covid.T1 + covid.T3, equal weights)."""
    from picard_framework.covid_theta_fit import (
        ThetaObjective,
        load_fit_targets,
    )

    return ThetaObjective(
        targets=load_fit_targets(),
        runner=lambda scenario_id, theta, seed: None,
        scenario_id="diamond_princess_2020",
    )


def _decompose_cell(payload: dict[str, Any], objective: Any) -> dict[str, Any]:
    """Project one cell payload to the surface row the rescore needs."""
    from picard_framework.covid_first_look import observables_from_payload

    obs = observables_from_payload(payload)
    cell = payload.get("cell") or {}
    verbatim_loss = sum(
        term.residual for term in objective.terms(obs)
    )
    recorded = int(obs.recorded_onsets)
    infections = payload.get("infections_total")
    return {
        "scenario_id": obs.scenario_id,
        "theta": float(obs.theta),
        "seed": int(obs.seed),
        "arm_id": payload.get("arm_id") or cell.get("arm_id"),
        "design_id": payload.get("design_id"),
        "recorded_onsets": recorded,
        "campaign_positives": int(obs.campaign_positives),
        "campaign_specimens": int(obs.campaign_specimens),
        "asymptomatic_share": obs.asymptomatic_share,
        "infections_total": (
            int(infections) if infections is not None else None
        ),
        "lab_confirmed_total": payload.get("lab_confirmed_total"),
        "verbatim_loss": float(verbatim_loss),
        "h5_band_residual": _h5_band_residual(infections or 0),
    }


def _quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"n": 0, "q05": None, "median": None, "q95": None}
    arr = np.asarray(values, dtype=float)
    return {
        "n": len(values),
        "q05": float(np.quantile(arr, 0.05)),
        "median": float(np.quantile(arr, 0.5)),
        "q95": float(np.quantile(arr, 0.95)),
    }


def _selection_frequencies(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, float], dict[str, float]]:
    """Paired-seed bootstrap over theta rows sharing a seed set.

    Each row is ``{"theta", "seeded": {seed: (verbatim, takeoff, h5)}}``;
    a resample draws seed indices with replacement and the winner is the
    smallest mean loss, ties toward the smaller theta - the merge's own
    selection rule. The verbatim column scores T1+T3 only; the augmented
    column adds the H5 band residual as a third equally-weighted term,
    averaged over the drawn takeoff seeds (the anchor is takeoff-
    conditional); a resample drawing no takeoff seed plugs the row's own
    takeoff-set mean. Rows under the takeoff-seed floor sit out the
    augmented comparison entirely.
    """
    common = sorted(
        set.intersection(*(set(r["seeded"]) for r in rows)),
    )
    if not rows or not common:
        return {}, {}
    scored = [r for r in rows if r["h5_scored"]]
    thetas = np.asarray([r["theta"] for r in rows])
    scored_thetas = np.asarray([r["theta"] for r in scored])
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    wins = np.zeros(len(rows), dtype=int)
    scored_wins = np.zeros(len(scored), dtype=int)
    n_seeds = len(common)
    verbatim = np.asarray(
        [[r["seeded"][s][0] for s in common] for r in rows], dtype=float,
    )
    takeoff = np.asarray(
        [[r["seeded"][s][1] for s in common] for r in scored], dtype=bool,
    )
    h5 = np.asarray(
        [[r["seeded"][s][2] for s in common] for r in scored], dtype=float,
    )
    h5_plug = np.asarray(
        [r["h5_takeoff_mean"] for r in scored], dtype=float,
    )
    scored_verbatim = np.asarray(
        [[r["seeded"][s][0] for s in common] for r in scored], dtype=float,
    )
    for _ in range(BOOTSTRAP_RESAMPLES):
        draw = rng.integers(0, n_seeds, size=n_seeds)
        order = np.lexsort((thetas, verbatim[:, draw].mean(axis=1)))
        wins[order[0]] += 1
        drawn_takeoff = takeoff[:, draw]
        counts = drawn_takeoff.sum(axis=1)
        drawn_h5 = np.where(
            counts > 0,
            (h5[:, draw] * drawn_takeoff).sum(axis=1)
            / np.maximum(counts, 1),
            h5_plug,
        )
        aug = scored_verbatim[:, draw].mean(axis=1) + drawn_h5
        order = np.lexsort((scored_thetas, aug))
        scored_wins[order[0]] += 1
    verbatim_freq = {
        f"{r['theta']:.6g}": float(w / BOOTSTRAP_RESAMPLES)
        for r, w in zip(rows, wins)
    }
    augmented_freq = {
        f"{r['theta']:.6g}": float(w / BOOTSTRAP_RESAMPLES)
        for r, w in zip(scored, scored_wins)
    }
    return verbatim_freq, augmented_freq


def _dp_theta_block(
    theta: float,
    cells: list[dict[str, Any]],
    takeoff_onsets: int,
) -> dict[str, Any]:
    takeoff = [c for c in cells if c["recorded_onsets"] >= takeoff_onsets]
    infections = [
        c["infections_total"] for c in takeoff
        if c["infections_total"] is not None
    ]
    in_band = sum(
        1 for inf in infections if H5_BAND[0] <= inf <= H5_BAND[1]
    )
    h5_scored = len(takeoff) >= TAKEOFF_SEED_FLOOR
    block = {
        "theta": theta,
        "seeds": len(cells),
        "takeoff_seeds": len(takeoff),
        "takeoff_fraction": len(takeoff) / len(cells),
        "verbatim_loss_mean": float(
            np.mean([c["verbatim_loss"] for c in cells])
        ),
        "infections_total_takeoff": _quantiles(infections),
        "h5_in_band_fraction": (
            in_band / len(infections) if infections else None
        ),
        "h5_median_in_band": bool(
            infections and H5_BAND[0] <= median(infections) <= H5_BAND[1],
        ),
        "h5_band_residual_mean": (
            float(np.mean([c["h5_band_residual"] for c in takeoff]))
            if h5_scored else None
        ),
        "h5_scored": h5_scored,
        "recorded_onsets": _quantiles(
            [c["recorded_onsets"] for c in cells],
        ),
        "campaign_positives": _quantiles(
            [c["campaign_positives"] for c in cells],
        ),
        "lab_confirmed_total": _quantiles(
            [c["lab_confirmed_total"] for c in cells
             if c["lab_confirmed_total"] is not None],
        ),
    }
    return block


def _gm_theta_block(
    theta: float,
    cells: list[dict[str, Any]],
    takeoff_onsets: int,
) -> dict[str, Any]:
    takeoff = [c for c in cells if c["recorded_onsets"] >= takeoff_onsets]
    infections = [
        c["infections_total"] for c in takeoff
        if c["infections_total"] is not None
    ]
    asym = [
        c["asymptomatic_share"] for c in cells
        if c["asymptomatic_share"] is not None
    ]
    return {
        "theta": theta,
        "seeds": len(cells),
        "takeoff_seeds": len(takeoff),
        "takeoff_fraction": len(takeoff) / len(cells),
        "infections_total_takeoff": _quantiles(infections),
        "campaign_positives": _quantiles(
            [c["campaign_positives"] for c in cells],
        ),
        "asymptomatic_share": _quantiles(asym),
        "recorded_onsets": _quantiles(
            [c["recorded_onsets"] for c in cells],
        ),
    }


def _surface(
    cells: list[dict[str, Any]],
    takeoff_onsets: int,
) -> dict[str, Any]:
    by_scenario: dict[str, dict[float, list[dict[str, Any]]]] = {}
    for c in cells:
        by_scenario.setdefault(c["scenario_id"], {}).setdefault(
            c["theta"], [],
        ).append(c)
    dp = {
        theta: _dp_theta_block(theta, block, takeoff_onsets)
        for theta, block in sorted(
            by_scenario.get("diamond_princess_2020", {}).items(),
        )
    }
    gm = {
        theta: _gm_theta_block(theta, block, takeoff_onsets)
        for theta, block in sorted(
            by_scenario.get("greg_mortimer_2020", {}).items(),
        )
    }

    verbatim_freq, augmented_freq = _selection_frequencies(
        [
            {
                "theta": b["theta"],
                "h5_scored": b["h5_scored"],
                "h5_takeoff_mean": b["h5_band_residual_mean"] or 0.0,
                "seeded": {
                    c["seed"]: (
                        c["verbatim_loss"],
                        c["recorded_onsets"] >= takeoff_onsets,
                        c["h5_band_residual"],
                    )
                    for c in by_scenario["diamond_princess_2020"][b["theta"]]
                },
            }
            for b in dp.values()
        ],
    )
    return {
        "h5_band": list(H5_BAND),
        "takeoff_onsets": takeoff_onsets,
        "takeoff_seed_floor": TAKEOFF_SEED_FLOOR,
        "dp": list(dp.values()),
        "gm": list(gm.values()),
        "verbatim_selection_frequency": verbatim_freq,
        "augmented_selection_frequency": augmented_freq,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", action="append", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--takeoff-onsets", type=int, default=10)
    args = parser.parse_args(argv)

    objective = _objective()
    cells: list[dict[str, Any]] = []
    for cells_arg in args.cells:
        cells_dir = resolve_repo_path(str(_REPO_ROOT), cells_arg)
        for path in sorted(glob.glob(str(Path(cells_dir) / "cell_*.json"))):
            payload = json.loads(Path(path).read_text())
            cells.append(_decompose_cell(payload, objective))
    if not cells:
        raise ValueError(
            f"no cell_*.json found under {args.cells!r} "
            "(paths resolve against the repository root)"
        )
    surface = _surface(cells, args.takeoff_onsets)
    out = {"cells": cells, "surface": surface}
    out_path = Path(resolve_repo_path(str(_REPO_ROOT), args.out))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with validated_open(
        str(out_path), "w", allowed_roots=(str(_REPO_ROOT),)
    ) as fh:
        fh.write(json.dumps(out, indent=1) + "\n")
    print(json.dumps({
        "cells": len(cells),
        "dp_thetas": len(surface["dp"]),
        "gm_thetas": len(surface["gm"]),
        "verbatim_selection_frequency":
            surface["verbatim_selection_frequency"],
        "augmented_selection_frequency":
            surface["augmented_selection_frequency"],
        "h5_median_in_band_thetas": [
            b["theta"] for b in surface["dp"] if b["h5_median_in_band"]
        ],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
