#!/usr/bin/env python3
"""PLATFORM-FIDELITY-02 paired-seed power calculation (analysis only).

Reads the 20 PLATFORM-FIDELITY-01 proxy cells and the 20 PLATFORM-FIDELITY-01b
dedicated cells, estimates the paired-seed power of the two pre-declared
primary endpoints, and fixes the PF-02 seed count before any PF-02 cell runs:

- P(takeoff): exact two-sided McNemar on the discordant pairs, with the
  discordant rate and proxy-only split plugged in from the 20 paired seeds;
- outbreak size when takeoff occurs: one-sample t on the both-takeoff paired
  ``dedicated - proxy`` ``recorded_onsets`` deltas, with the both-takeoff
  rate plugged in from the same 20 seeds.

The selection rule is frozen in ``docs/covid/covid_platform_fidelity_02_prereg.md``:
smallest grid n with >=0.90 power on both endpoints at the observed plug-in
rates AND >=0.80 power on both endpoints when both event rates are halved
(p_both 0.25 -> 0.125, p_discordant 0.30 -> 0.15). Unconditional burden is
reported for context only; it is not powered or selected on.

Usage (S3 is read directly; AWS_PROFILE=picard for the campaign bucket):
    AWS_PROFILE=picard python3 campaigns/covid/platform_fidelity_02/power_analysis.py \
        --out campaigns/covid/platform_fidelity_02/power_analysis.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import binom
from scipy.stats import t as tdist

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_PF01B_READOUT = _REPO_ROOT / "campaigns/covid/platform_fidelity_01b/readout.py"
_BUCKET = "crusherbucket-994254241749-us-east-1-an"
_DEFAULT_PROXY_PREFIX = f"s3://{_BUCKET}/campaign/covid_platform_fidelity_01/dp_t7e6_proxy/"
_DEFAULT_DEDICATED_PREFIX = f"s3://{_BUCKET}/campaign/covid_platform_fidelity_01b/dp_t7e6_dedicated/"
_TAKEOFF = 10
_ALPHA = 0.05
_GRID = (20, 40, 60, 80, 100, 120, 160, 200, 240, 300, 400, 600, 800)
_BURDEN_GRID = (20, 60, 100, 200, 400, 600, 800)
_BURDEN_REPS = 3000
_MAX_CONDITIONAL_M = 80
_CONDITIONAL_REPS = 10000


def _load_readout() -> Any:
    spec = importlib.util.spec_from_file_location("pf01b_readout", _PF01B_READOUT)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {_PF01B_READOUT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _paired_arrays(
    proxy: dict[int, dict[str, Any]], dedicated: dict[int, dict[str, Any]],
) -> tuple[list[int], np.ndarray, np.ndarray]:
    seeds = sorted(set(proxy) & set(dedicated))
    proxy_on = np.array([int(proxy[s]["obs"].get("recorded_onsets", 0)) for s in seeds])
    dedicated_on = np.array([int(dedicated[s]["obs"].get("recorded_onsets", 0)) for s in seeds])
    return seeds, proxy_on, dedicated_on


def _observed(proxy_on: np.ndarray, dedicated_on: np.ndarray) -> dict[str, Any]:
    p_take = proxy_on >= _TAKEOFF
    d_take = dedicated_on >= _TAKEOFF
    both = p_take & d_take
    proxy_only = int(np.sum(p_take & ~d_take))
    dedicated_only = int(np.sum(~p_take & d_take))
    discordant = proxy_only + dedicated_only
    deltas = (dedicated_on - proxy_on)[both]
    return {
        "n_seeds": int(len(proxy_on)),
        "P_takeoff_proxy": float(np.mean(p_take)),
        "P_takeoff_dedicated": float(np.mean(d_take)),
        "n_both_takeoff": int(np.sum(both)),
        "p_both_takeoff": float(np.mean(both)),
        "proxy_only_takeoff": proxy_only,
        "dedicated_only_takeoff": dedicated_only,
        "n_discordant": discordant,
        "p_discordant": float(discordant / len(proxy_on)),
        "p_proxy_only_given_discordant": (proxy_only / discordant) if discordant else float("nan"),
        "both_takeoff_deltas": [float(x) for x in deltas],
        "both_takeoff_delta_mean": float(np.mean(deltas)) if len(deltas) else float("nan"),
        "both_takeoff_delta_sd": float(np.std(deltas, ddof=1)) if len(deltas) > 1 else float("nan"),
        "unconditional_onset_mean_proxy": float(np.mean(proxy_on)),
        "unconditional_onset_mean_dedicated": float(np.mean(dedicated_on)),
        "unconditional_onset_total_proxy": float(np.sum(proxy_on)),
        "unconditional_onset_total_dedicated": float(np.sum(dedicated_on)),
    }


def _takeoff_power(n: int, p_discordant: float, p_proxy_only: float) -> float:
    rng = np.random.default_rng(20261108 + n)
    reps = 20000
    k = rng.binomial(n, p_discordant, size=reps)
    x = rng.binomial(k, p_proxy_only)
    cdf = binom.cdf(x, k, 0.5)
    sf = binom.sf(x - 1, k, 0.5)
    p = np.minimum(1.0, 2.0 * np.minimum(cdf, sf))
    p = np.where(k == 0, 1.0, p)
    return float(np.mean(p < _ALPHA))


def _conditional_power_by_m(deltas: np.ndarray) -> list[float]:
    powers = [0.0] * (_MAX_CONDITIONAL_M + 1)
    for m in range(2, _MAX_CONDITIONAL_M + 1):
        rng = np.random.default_rng(20261109 + m)
        x = rng.choice(deltas, size=(_CONDITIONAL_REPS, m), replace=True)
        mean = x.mean(axis=1)
        sd = x.std(axis=1, ddof=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            stat = mean / (sd / np.sqrt(m))
            p = 2.0 * tdist.sf(np.abs(stat), m - 1)
        reject = np.where(sd == 0.0, mean != 0.0, p < _ALPHA)
        powers[m] = float(np.mean(reject))
    return powers


def _size_power(n: int, p_both: float, power_by_m: list[float]) -> float:
    m = np.arange(0, n + 1)
    pmf = binom.pmf(m, n, p_both)
    values = np.array([
        power_by_m[int(count)] if int(count) < len(power_by_m) else 1.0
        for count in m
    ])
    return float(np.dot(pmf, values))


def _welch_power(proxy: np.ndarray, dedicated: np.ndarray, n: int) -> float:
    rng = np.random.default_rng(20261110 + n)
    xp = rng.choice(proxy, size=(_BURDEN_REPS, n), replace=True)
    xd = rng.choice(dedicated, size=(_BURDEN_REPS, n), replace=True)
    return _welch_t_reject(xp, xd)


def _paired_power(proxy: np.ndarray, dedicated: np.ndarray, n: int) -> float:
    rng = np.random.default_rng(20261111 + n)
    idx = rng.integers(0, len(proxy), size=(_BURDEN_REPS, n))
    diff = dedicated[idx] - proxy[idx]
    mean = diff.mean(axis=1)
    sd = diff.std(axis=1, ddof=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        stat = mean / (sd / np.sqrt(n))
        p = 2.0 * tdist.sf(np.abs(stat), n - 1)
    reject = np.where(sd == 0.0, mean != 0.0, p < _ALPHA)
    return float(np.mean(reject))


def _welch_t_reject(xp: np.ndarray, xd: np.ndarray) -> float:
    m1 = xp.mean(axis=1)
    m2 = xd.mean(axis=1)
    v1 = xp.var(axis=1, ddof=1)
    v2 = xd.var(axis=1, ddof=1)
    se2 = v1 / xp.shape[1] + v2 / xd.shape[1]
    with np.errstate(invalid="ignore", divide="ignore"):
        stat = (m2 - m1) / np.sqrt(se2)
        df = se2**2 / ((v1 / xp.shape[1])**2 / (xp.shape[1] - 1)
                       + (v2 / xd.shape[1])**2 / (xd.shape[1] - 1))
        p = 2.0 * tdist.sf(np.abs(stat), df)
    return float(np.mean(p < _ALPHA))


def _grid_rows(
    observed: dict[str, Any], power_by_m: list[float],
    proxy: np.ndarray, dedicated: np.ndarray,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    p_disc = float(observed["p_discordant"])
    p_split = float(observed["p_proxy_only_given_discordant"])
    p_both = float(observed["p_both_takeoff"])
    rows = []
    burden_rows = []
    for n in _GRID:
        rows.append({
            "seeds_per_arm": n,
            "cells_both_arms": 2 * n,
            "power_takeoff_observed": _takeoff_power(n, p_disc, p_split),
            "power_size_observed": _size_power(n, p_both, power_by_m),
            "power_takeoff_halved_rates": _takeoff_power(n, p_disc / 2.0, p_split),
            "power_size_halved_both_rate": _size_power(n, p_both / 2.0, power_by_m),
        })
    for n in _BURDEN_GRID:
        burden_rows.append({
            "seeds_per_arm": n,
            "power_welch_unconditional_onsets": _welch_power(proxy, dedicated, n),
            "power_paired_t_unconditional_onsets": _paired_power(proxy, dedicated, n),
        })
    return rows, burden_rows


def _select_n(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in rows:
        if (row["power_takeoff_observed"] >= 0.90
                and row["power_size_observed"] >= 0.90
                and row["power_takeoff_halved_rates"] >= 0.80
                and row["power_size_halved_both_rate"] >= 0.80):
            return {"selected_seeds_per_arm": row["seeds_per_arm"],
                    "selected_cells_both_arms": row["cells_both_arms"],
                    "rule": ("smallest grid n with >=0.90 power on P(takeoff) and "
                             "both-takeoff paired size at observed plug-in rates, "
                             "and >=0.80 on both under halved event rates"),
                    "feasible_within_batch_budget": True}
    return {"selected_seeds_per_arm": None, "selected_cells_both_arms": None,
            "rule": "no grid n met the frozen rule", "feasible_within_batch_budget": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy-prefix", default=_DEFAULT_PROXY_PREFIX)
    parser.add_argument("--dedicated-prefix", default=_DEFAULT_DEDICATED_PREFIX)
    parser.add_argument("--proxy-dir", default=None)
    parser.add_argument("--dedicated-dir", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    readout = _load_readout()
    proxy = readout._load_cells(args.proxy_prefix, args.proxy_dir)
    dedicated = readout._load_cells(args.dedicated_prefix, args.dedicated_dir)
    seeds, proxy_on, dedicated_on = _paired_arrays(proxy, dedicated)
    observed = _observed(proxy_on, dedicated_on)
    deltas = np.array(observed["both_takeoff_deltas"], dtype=float)
    power_by_m = _conditional_power_by_m(deltas)
    rows, burden_rows = _grid_rows(observed, power_by_m, proxy_on, dedicated_on)
    result = {
        "campaign": "covid_platform_fidelity_02",
        "analysis_only": True,
        "inputs": {
            "proxy_source": args.proxy_dir or args.proxy_prefix,
            "dedicated_source": args.dedicated_dir or args.dedicated_prefix,
            "takeoff_recorded_onsets": _TAKEOFF,
            "alpha": _ALPHA,
        },
        "observed_01b": observed,
        "grid": rows,
        "unconditional_burden_report_only": burden_rows,
        "selection": _select_n(rows),
    }
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"WROTE {out}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
