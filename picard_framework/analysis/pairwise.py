"""Pairwise native/ContamX and surveillance-ladder comparisons."""

from __future__ import annotations

import os
from collections import defaultdict
from statistics import median
from typing import Any

from picard_framework.analysis._io import write_csv

PAIRWISE_COLUMNS: tuple[str, ...] = (
    "comparison_id",
    "run_id_a",
    "run_id_b",
    "platform_id",
    "pathogen",
    "dose_adjustment",
    "seed",
    "epoch_match_rate_infected",
    "epoch_match_rate_recovered",
    "epoch_match_rate_new_infections",
    "max_abs_delta_infected",
    "max_abs_delta_recovered",
    "delta_attack_rate",
    "delta_peak_prevalence",
    "delta_peak_epoch",
    "delta_detection_epoch",
    "delta_total_quarantine_person_epochs",
    "mass_ratio_median",
    "mass_ratio_iqr_low",
    "mass_ratio_iqr_high",
)

# Match keys that must be equal for a fair pair (aside from the contrasted factor).
_MATCH_KEYS = (
    "platform_id",
    "pathogen",
    "dose_adjustment",
    "seed",
    "density_exponent",
    "immunity_fraction",
    "num_agents",
)

_SURV_LADDER = (
    ("none_true", "syndromic"),
    ("syndromic", "cascade"),
    ("cascade", "cascade_mpx"),
    ("cascade", "wearable"),
    ("cascade", "wastewater"),
    ("syndromic", "wearable"),
    ("none", "syndromic"),
    ("none_true", "cascade"),
)


def _key_tuple(row: dict[str, Any], keys: tuple[str, ...]) -> tuple[Any, ...]:
    return tuple(row.get(k) for k in keys)


def _safe_div(a: Any, b: Any) -> float | None:
    try:
        af = float(a)
        bf = float(b)
    except (TypeError, ValueError):
        return None
    if bf == 0:
        return None
    return af / bf


def _percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _trajectory_stats(
    rows_a: list[dict[str, Any]],
    rows_b: list[dict[str, Any]],
) -> dict[str, Any]:
    by_epoch_a = {int(r["epoch"]): r for r in rows_a if r.get("epoch") is not None}
    by_epoch_b = {int(r["epoch"]): r for r in rows_b if r.get("epoch") is not None}
    common = sorted(set(by_epoch_a) & set(by_epoch_b))
    if not common:
        return {
            "epoch_match_rate_infected": None,
            "epoch_match_rate_recovered": None,
            "epoch_match_rate_new_infections": None,
            "max_abs_delta_infected": None,
            "max_abs_delta_recovered": None,
            "mass_ratio_median": None,
            "mass_ratio_iqr_low": None,
            "mass_ratio_iqr_high": None,
        }

    def _match_rate(field: str) -> float:
        matches = 0
        for ep in common:
            if by_epoch_a[ep].get(field) == by_epoch_b[ep].get(field):
                matches += 1
        return round(matches / len(common), 6)

    max_d_inf = 0
    max_d_rec = 0
    mass_ratios: list[float] = []
    for ep in common:
        ia = int(by_epoch_a[ep].get("infected", 0) or 0)
        ib = int(by_epoch_b[ep].get("infected", 0) or 0)
        ra = int(by_epoch_a[ep].get("recovered", 0) or 0)
        rb = int(by_epoch_b[ep].get("recovered", 0) or 0)
        max_d_inf = max(max_d_inf, abs(ia - ib))
        max_d_rec = max(max_d_rec, abs(ra - rb))
        ratio = _safe_div(
            by_epoch_a[ep].get("total_pathogen_mass"),
            by_epoch_b[ep].get("total_pathogen_mass"),
        )
        if ratio is not None:
            mass_ratios.append(ratio)

    mass_ratios.sort()
    return {
        "epoch_match_rate_infected": _match_rate("infected"),
        "epoch_match_rate_recovered": _match_rate("recovered"),
        "epoch_match_rate_new_infections": _match_rate("new_infections"),
        "max_abs_delta_infected": max_d_inf,
        "max_abs_delta_recovered": max_d_rec,
        "mass_ratio_median": (
            round(median(mass_ratios), 6) if mass_ratios else None
        ),
        "mass_ratio_iqr_low": (
            round(_percentile(mass_ratios, 0.25), 6) if mass_ratios else None
        ),
        "mass_ratio_iqr_high": (
            round(_percentile(mass_ratios, 0.75), 6) if mass_ratios else None
        ),
    }


def _scalar_deltas(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    def _delta(key: str) -> Any:
        av, bv = a.get(key), b.get(key)
        if av is None or bv is None:
            return None
        try:
            return float(av) - float(bv)
        except (TypeError, ValueError):
            return None

    return {
        "delta_attack_rate": _delta("attack_rate"),
        "delta_peak_prevalence": _delta("peak_prevalence"),
        "delta_peak_epoch": _delta("peak_epoch"),
        "delta_detection_epoch": _delta("detection_epoch"),
        "delta_total_quarantine_person_epochs": _delta(
            "total_quarantine_person_epochs"
        ),
    }


def _pair_row(
    *,
    comparison_id: str,
    a: dict[str, Any],
    b: dict[str, Any],
    epochs_by_run: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    stats = _trajectory_stats(
        epochs_by_run.get(str(a["run_id"]), []),
        epochs_by_run.get(str(b["run_id"]), []),
    )
    row: dict[str, Any] = {
        "comparison_id": comparison_id,
        "run_id_a": a.get("run_id"),
        "run_id_b": b.get("run_id"),
        "platform_id": a.get("platform_id"),
        "pathogen": a.get("pathogen"),
        "dose_adjustment": a.get("dose_adjustment"),
        "seed": a.get("seed"),
    }
    row.update(stats)
    row.update(_scalar_deltas(a, b))
    return row


def build_pairwise_deltas(
    run_rows: list[dict[str, Any]],
    epoch_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build pairwise comparison rows from standardized bundle tables."""
    epochs_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in epoch_rows:
        epochs_by_run[str(row["run_id"])].append(row)

    by_engine: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_surv: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in run_rows:
        engine = str(row.get("transport_engine") or "native").lower()
        by_engine[engine].append(row)
        surv = str(row.get("surveillance_strategy") or "none")
        by_surv[surv].append(row)

    out: list[dict[str, Any]] = []

    # 1) native vs contamx
    native_index = {
        _key_tuple(r, _MATCH_KEYS + ("surveillance_strategy",)): r
        for r in by_engine.get("native", [])
    }
    for contam in by_engine.get("contamx", []):
        key = _key_tuple(contam, _MATCH_KEYS + ("surveillance_strategy",))
        native = native_index.get(key)
        if native is None:
            continue
        out.append(
            _pair_row(
                comparison_id="native_vs_contamx",
                a=native,
                b=contam,
                epochs_by_run=epochs_by_run,
            )
        )

    # 2) surveillance ladder (same engine)
    for left, right in _SURV_LADDER:
        left_index = {
            _key_tuple(r, _MATCH_KEYS + ("transport_engine",)): r
            for r in by_surv.get(left, [])
        }
        for row_b in by_surv.get(right, []):
            key = _key_tuple(row_b, _MATCH_KEYS + ("transport_engine",))
            row_a = left_index.get(key)
            if row_a is None:
                continue
            out.append(
                _pair_row(
                    comparison_id=f"{left}_vs_{right}",
                    a=row_a,
                    b=row_b,
                    epochs_by_run=epochs_by_run,
                )
            )

    return out


def write_pairwise_csv(out_dir: str, rows: list[dict[str, Any]]) -> str:
    """Write ``pairwise_deltas.csv`` and return the basename."""
    path = os.path.join(out_dir, "pairwise_deltas.csv")
    write_csv(path, rows, PAIRWISE_COLUMNS)
    return "pairwise_deltas.csv"
