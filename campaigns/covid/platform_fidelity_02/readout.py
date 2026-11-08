#!/usr/bin/env python3
"""PLATFORM-FIDELITY-02 readout: the 200-seed DP hull-fidelity contrast.

Loads the PF-02 proxy and dedicated cell payloads, pairs them on seed, and
reports the pre-registered primary endpoints plus the report-only context
quantities. q05-q95 values are seedwise spreads, NOT confidence intervals;
unconditional onset burden is reported alongside the conditional endpoint;
no platform-equivalence conclusion is drawn from an interval crossing zero.

Usage:
    python3 campaigns/covid/platform_fidelity_02/readout.py
    python3 campaigns/covid/platform_fidelity_02/readout.py --out out/pf02.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

from scipy.stats import binomtest, ttest_ind
from scipy.stats import t as student_t

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_PF01B_READOUT = _REPO_ROOT / "campaigns/covid/platform_fidelity_01b/readout.py"
_DESIGN = _REPO_ROOT / "picard_framework/runs/covid_platform_fidelity_02_dp_design.json"
_PROTOCOLS_REL = "data/config/protocols_covid_pf_dp_01b.json"
_BUCKET = "crusherbucket-994254241749-us-east-1-an"
_DEFAULT_PROXY_PREFIX = f"s3://{_BUCKET}/campaign/covid_platform_fidelity_02/dp_t7e6_proxy/"
_DEFAULT_DEDICATED_PREFIXES = [
    f"s3://{_BUCKET}/campaign/covid_platform_fidelity_02/dp_t7e6_dedicated_canary/",
    f"s3://{_BUCKET}/campaign/covid_platform_fidelity_02/dp_t7e6_dedicated_rest/",
]
_TAKEOFF = 10


def _load_pf01b() -> Any:
    spec = importlib.util.spec_from_file_location("pf01b_readout", _PF01B_READOUT)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {_PF01B_READOUT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_PF = _load_pf01b()


def _expected_seeds() -> list[int]:
    try:
        raw = json.loads(_DESIGN.read_text(encoding="utf-8"))
        base = int(raw["seed_base"])
        count = int(raw["seeds"])
        return [base + i for i in range(count)]
    except Exception:
        return [20200205 + i for i in range(200)]


def _load_arm(prefixes: list[str], directory: str | None, pf: Any) -> dict[int, dict[str, Any]]:
    if directory:
        return pf._load_cells("", directory)
    cells: dict[int, dict[str, Any]] = {}
    for prefix in prefixes:
        cells.update(pf._load_cells(prefix, None))
    return cells


def _onsets(cells: dict[int, dict[str, Any]]) -> dict[int, int]:
    return {seed: int(cell["obs"].get("recorded_onsets", 0)) for seed, cell in cells.items()}


def _mcnemar_p(proxy_only: int, dedicated_only: int) -> float:
    n = proxy_only + dedicated_only
    if n == 0:
        return 1.0
    return float(binomtest(proxy_only, n, 0.5, alternative="two-sided").pvalue)


def _one_sample_t(deltas: list[int]) -> dict[str, Any]:
    n = len(deltas)
    if n < 2:
        return {"n": n, "mean": float("nan"), "sd": float("nan"), "p_two_sided": float("nan"),
                "ci95": [float("nan"), float("nan")]}
    mean = sum(deltas) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in deltas) / (n - 1))
    if sd == 0.0:
        p = 1.0 if mean == 0.0 else 0.0
        half = 0.0
    else:
        stat = mean / (sd / math.sqrt(n))
        df = n - 1
        p = float(2.0 * student_t.sf(abs(stat), df))
        half = float(student_t.ppf(0.975, df) * sd / math.sqrt(n))
    return {"n": n, "mean": mean, "sd": sd, "p_two_sided": p,
            "ci95": [mean - half, mean + half]}


def _proxy_audit(cell: dict[str, Any], protocols_sha: str) -> list[str]:
    problems = []
    pf = cell["pf"]
    if pf.get("resolved_platform_id") != "mega_cruise_5000":
        problems.append(f"resolved_platform_id={pf.get('resolved_platform_id')}")
    if pf.get("scenario_declared_platform_id") != "mega_cruise_5000":
        problems.append(f"scenario_declared_platform_id={pf.get('scenario_declared_platform_id')}")
    if pf.get("fired_protocol_ids") != ["SOP-017-MESSBOX"]:
        problems.append(f"fired={pf.get('fired_protocol_ids')}")
    if pf.get("close_zones_fired_flag"):
        problems.append("close_zones fired")
    hashes = pf.get("input_hashes") or {}
    if hashes.get("protocols_sha256") != protocols_sha:
        problems.append("protocols_sha256 mismatch")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy-prefix", action="append", default=None)
    parser.add_argument("--dedicated-prefix", action="append", default=None)
    parser.add_argument("--proxy-dir", default=None)
    parser.add_argument("--dedicated-dir", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    proxy_prefixes = args.proxy_prefix or [_DEFAULT_PROXY_PREFIX]
    dedicated_prefixes = args.dedicated_prefix or _DEFAULT_DEDICATED_PREFIXES
    proxy = _load_arm(proxy_prefixes, args.proxy_dir, _PF)
    dedicated = _load_arm(dedicated_prefixes, args.dedicated_dir, _PF)
    seeds = sorted(set(proxy) & set(dedicated))
    proxy_on = _onsets({s: proxy[s] for s in seeds})
    dedicated_on = _onsets({s: dedicated[s] for s in seeds})

    p_take_proxy = [s for s in seeds if proxy_on[s] >= _TAKEOFF]
    p_take_ded = [s for s in seeds if dedicated_on[s] >= _TAKEOFF]
    both = [s for s in seeds if proxy_on[s] >= _TAKEOFF and dedicated_on[s] >= _TAKEOFF]
    deltas = [dedicated_on[s] - proxy_on[s] for s in both]
    proxy_only = [s for s in p_take_proxy if s not in set(p_take_ded)]
    dedicated_only = [s for s in p_take_ded if s not in set(p_take_proxy)]
    rho = _PF._pearson([float(proxy_on[s]) for s in both], [float(dedicated_on[s]) for s in both])
    size = _one_sample_t(deltas)

    protocols_sha = _PF._sha256_file(_REPO_ROOT / _PROTOCOLS_REL)
    witness = {str(s): _PF._witness_audit(dedicated[s], protocols_sha) for s in seeds}
    proxy_audit = {str(s): _proxy_audit(proxy[s], protocols_sha) for s in seeds}
    witness_failures = {**{k: v for k, v in witness.items() if v},
                        **{k: v for k, v in proxy_audit.items() if v}}
    failed_comparisons = [
        key for key, cell in list(proxy.items()) + list(dedicated.items())
        if cell["pf"].get("close_zones_fired_flag")
    ]
    missing_echo = [s for s in seeds if not proxy[s]["pf"].get("resolved_platform_id")
                    or not dedicated[s]["pf"].get("resolved_platform_id")]
    expected = _expected_seeds()
    missing_cells = sorted(set(expected) - set(seeds))
    n_in_scope = len(seeds)
    failure_rate = (len(missing_cells) + len(failed_comparisons)) / max(n_in_scope, 1)

    proxy_burden = [proxy_on[s] for s in seeds]
    dedicated_burden = [dedicated_on[s] for s in seeds]
    welch = ttest_ind(dedicated_burden, proxy_burden, equal_var=False) if seeds else None
    summary = {
        "campaign": "covid_platform_fidelity_02",
        "note": ("q05-q95 are seedwise spreads, NOT confidence intervals; "
                 "unconditional onset burden is reported alongside the "
                 "takeoff-conditional endpoint; no platform-equivalence "
                 "conclusion from an interval crossing zero."),
        "proxy_source": args.proxy_dir or proxy_prefixes,
        "dedicated_source": args.dedicated_dir or dedicated_prefixes,
        "n_seeds_paired": len(seeds),
        "primary": {
            "P_takeoff_proxy": len(p_take_proxy) / len(seeds) if seeds else float("nan"),
            "P_takeoff_dedicated": len(p_take_ded) / len(seeds) if seeds else float("nan"),
            "takeoff_difference_dedicated_minus_proxy": (
                (len(p_take_ded) - len(p_take_proxy)) / len(seeds) if seeds else float("nan")
            ),
            "proxy_only_takeoff": len(proxy_only),
            "dedicated_only_takeoff": len(dedicated_only),
            "mcnemar_exact_p_two_sided": _mcnemar_p(len(proxy_only), len(dedicated_only)),
            "n_both_takeoff": len(both),
            "both_takeoff_size": size,
            "both_takeoff_delta_median": _PF._quantile(deltas, 0.5) if deltas else float("nan"),
            "both_takeoff_delta_q05": _PF._quantile(deltas, 0.05) if deltas else float("nan"),
            "both_takeoff_delta_q95": _PF._quantile(deltas, 0.95) if deltas else float("nan"),
            "crn_rho_both_takeoff": rho,
        },
        "reported_never_selected": {
            "unconditional_onset_median_proxy": _PF._quantile(proxy_burden, 0.5) if seeds else float("nan"),
            "unconditional_onset_median_dedicated": _PF._quantile(dedicated_burden, 0.5) if seeds else float("nan"),
            "unconditional_onset_total_proxy": float(sum(proxy_burden)),
            "unconditional_onset_total_dedicated": float(sum(dedicated_burden)),
            "unconditional_onset_mean_proxy": float(sum(proxy_burden) / len(seeds)) if seeds else float("nan"),
            "unconditional_onset_mean_dedicated": float(sum(dedicated_burden) / len(seeds)) if seeds else float("nan"),
            "unconditional_welch_p_two_sided": float(welch.pvalue) if welch is not None else float("nan"),
            "asym_share_proxy_takeoff": _PF._asym_share([proxy[s] for s in p_take_proxy]),
            "asym_share_dedicated_takeoff": _PF._asym_share([dedicated[s] for s in p_take_ded]),
        },
        "audit": {
            "witness_failures": witness_failures,
            "failed_comparisons": failed_comparisons,
            "missing_echo": missing_echo,
            "missing_cells": missing_cells,
            "technical_failure_rate": failure_rate,
        },
    }
    text = json.dumps(summary, indent=2, sort_keys=True) + "\n"
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
