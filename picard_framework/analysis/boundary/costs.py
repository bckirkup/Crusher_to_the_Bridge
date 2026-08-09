"""Cost accounting and break-even helpers for pre-boarding decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CostParams:
    C_screen: float = 1.0
    C_secondary: float = 75.0
    C_false_positive: float = 2000.0
    C_true_positive: float = 2000.0
    C_case: float = 400.0
    C_outbreak: float = 500000.0
    C_vsp: float = 2000000.0
    C_reputation: float = 2000000.0
    C_missed: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {k: float(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class VoyageCosts:
    screening: float
    secondary: float
    false_positive: float
    true_positive: float
    onboard: float
    reputational: float
    missed: float
    total: float


def cost_params_from_mapping(raw: dict[str, Any] | None) -> CostParams:
    if not raw:
        return CostParams()
    fields = {f.name for f in CostParams.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    kwargs = {k: float(v) for k, v in raw.items() if k in fields}
    return CostParams(**kwargs)


def compute_voyage_costs(
    *,
    params: CostParams,
    n_total: int,
    n_adopted: int,
    n_secondary: int,
    n_fp: int,
    n_tp: int,
    k_missed: int,
    p_trigger: float,
    e_ar: float,
    n_pax_boarded: int,
) -> VoyageCosts:
    """Expected cost components for one voyage realization (onboard terms use expectations)."""
    screening = float(n_adopted) * params.C_screen
    # P1 advisory: no operational screening charge by default (n_adopted may be >0
    # but caller can pass n_adopted=0 for P1). Secondary still 0.
    secondary = float(n_secondary) * params.C_secondary
    false_positive = float(n_fp) * params.C_false_positive
    true_positive = float(n_tp) * params.C_true_positive
    missed = float(k_missed) * params.C_missed

    # Spec: E[C_onboard] = P(VSP)*(C_outbreak + C_vsp + C_reputation) + E[AR]*N*C_case
    # Split reputation for reporting; include it in onboard total per spec equation.
    vsp_bundle = params.C_outbreak + params.C_vsp + params.C_reputation
    reputational = float(p_trigger) * params.C_reputation
    onboard_core = float(p_trigger) * (params.C_outbreak + params.C_vsp)
    case_cost = float(e_ar) * float(n_pax_boarded) * params.C_case
    onboard = onboard_core + reputational + case_cost

    # Equivalent form check: onboard == p_trigger * vsp_bundle + case_cost
    _ = vsp_bundle

    total = (
        screening
        + secondary
        + false_positive
        + true_positive
        + onboard
        + missed
    )
    return VoyageCosts(
        screening=screening,
        secondary=secondary,
        false_positive=false_positive,
        true_positive=true_positive,
        onboard=onboard,
        reputational=reputational,
        missed=missed,
        total=total,
    )


def false_positives_per_true_positive(n_fp: float, n_tp: float) -> float | None:
    if n_tp <= 0:
        return None
    return float(n_fp) / float(n_tp)


def cost_per_vsp_avoided(
    *,
    cost_policy: float,
    cost_baseline: float,
    p_trigger_policy: float,
    p_trigger_baseline: float,
) -> float | None:
    avoided = float(p_trigger_baseline) - float(p_trigger_policy)
    if avoided <= 1e-12:
        return None
    return (float(cost_policy) - float(cost_baseline)) / avoided


def value_of_information_per_pax(
    *,
    cost_baseline: float,
    cost_policy: float,
    n_pax: int,
) -> float | None:
    if n_pax <= 0:
        return None
    return (float(cost_baseline) - float(cost_policy)) / float(n_pax)


def break_even_prevalence(
    *,
    pi_grid: list[float],
    cost_baseline_by_pi: list[float],
    cost_policy_by_pi: list[float],
) -> float | None:
    """Smallest prevalence where policy expected cost <= baseline.

    Returns None if never breaks even on the supplied grid.
    """
    if len(pi_grid) != len(cost_baseline_by_pi) or len(pi_grid) != len(cost_policy_by_pi):
        raise ValueError("break_even_prevalence grid length mismatch")
    for pi, c0, c1 in zip(pi_grid, cost_baseline_by_pi, cost_policy_by_pi):
        if c1 <= c0:
            return float(pi)
    return None
