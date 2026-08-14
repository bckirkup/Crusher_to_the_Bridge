"""Posterior draws -> port hazard estimates.

Deliberately separate from the Stan runner: the summary path has to work from a
committed fixture posterior so CI can exercise it without a CmdStan toolchain,
exactly as ``boundary.run_decision_model --smoke`` does.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Any, Mapping, Sequence

import numpy as np

from picard_framework.analysis._io import read_json

_FIXTURE_FILE = "attribution_posterior.json"

CLINICAL_CHANNEL = "clinical"


@dataclass(frozen=True)
class PortHazardEstimate:
    """Posterior summary for one port's introduction hazard."""

    port_id: str
    port_visit_key: str | None
    pathogen: str
    hazard_mean: float
    hazard_q05: float
    hazard_q95: float
    n_attributed_cases: float
    evidence_loglik: Mapping[str, float]
    censoring_corrected: bool
    port_resolution_adequate: bool

    @property
    def attribution_share(self) -> float | None:
        """Placeholder for the fleet model's share; single ship reports None."""
        return None


def parameter_draws(posterior: Mapping[str, Sequence[float]], name: str) -> np.ndarray:
    """Draws for one parameter, refusing an absent or empty column.

    Public because the fleet summaries need the same refusal: a missing column
    means the posterior and the meta disagree about the model, and quietly
    treating that as zero would report a hazard nobody estimated.
    """
    values = posterior.get(name)
    if values is None:
        raise KeyError(f"posterior has no parameter {name!r}")
    array = np.asarray(list(values), dtype=float)
    if array.size == 0:
        raise ValueError(f"posterior parameter {name!r} has no draws")
    return array


def load_fixture_posterior() -> dict[str, list[float]]:
    """Bundled posterior draws for the CI smoke path (no CmdStan needed)."""
    root = resources.files("picard_framework.analysis.sentinel")
    raw = (root / "fixtures" / _FIXTURE_FILE).read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("fixture posterior must be an object")
    draws = payload.get("draws")
    if not isinstance(draws, dict) or not draws:
        raise ValueError("fixture posterior has no draws")
    return {str(k): [float(v) for v in values] for k, values in draws.items()}


def load_posterior(path: str) -> dict[str, list[float]]:
    """Load a posterior document written by ``fit_sentinel_attribution``."""
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"posterior document must be an object: {path}")
    draws = payload.get("draws")
    if not isinstance(draws, dict) or not draws:
        raise ValueError(f"posterior document has no draws: {path}")
    return {str(k): [float(v) for v in values] for k, values in draws.items()}


def summarize_port_hazards(
    posterior: Mapping[str, Sequence[float]],
    meta: Mapping[str, Any],
    *,
    pathogen: str,
) -> tuple[PortHazardEstimate, ...]:
    """Per-port posterior summaries, in the port order recorded in ``meta``.

    ``n_attributed_cases`` is the posterior mean of ``lambda_p x person-hours``,
    i.e. expected *imported* cases at that port — not a share of the observed
    cases, which is the quantity the original spec's model could actually
    identify (1.4).
    """
    ports = [str(p) for p in meta.get("ports") or []]
    if not ports:
        raise ValueError("meta carries no port order; posterior indices are meaningless")
    visit_keys = meta.get("port_visit_keys") or {}
    loglik = channel_loglik(posterior)
    censored = bool(meta.get("censoring_corrected"))
    resolved = bool(meta.get("port_resolution_adequate"))

    estimates: list[PortHazardEstimate] = []
    for i, port_id in enumerate(ports, start=1):
        hazard = parameter_draws(posterior, f"lambda_port[{i}]")
        cases = parameter_draws(posterior, f"imported_cases[{i}]")
        estimates.append(
            PortHazardEstimate(
                port_id=port_id,
                port_visit_key=(
                    str(visit_keys[port_id]) if port_id in visit_keys else None
                ),
                pathogen=pathogen,
                hazard_mean=float(hazard.mean()),
                hazard_q05=float(np.quantile(hazard, 0.05)),
                hazard_q95=float(np.quantile(hazard, 0.95)),
                n_attributed_cases=float(cases.mean()),
                evidence_loglik=loglik,
                censoring_corrected=censored,
                port_resolution_adequate=resolved,
            ),
        )
    return tuple(estimates)


def channel_loglik(posterior: Mapping[str, Sequence[float]]) -> dict[str, float]:
    """Per-channel evidence contribution (clinical only until PR 7)."""
    values = posterior.get("loglik_clinical")
    if values is None:
        return {}
    return {CLINICAL_CHANNEL: float(np.asarray(list(values), dtype=float).mean())}


def onboard_summary(posterior: Mapping[str, Sequence[float]]) -> dict[str, float]:
    """Onboard transmission summary: the split the port hazards compete with.

    ``R_onboard`` is a sampled parameter, so its interval is reported rather
    than asserted — the spec's original design passed it in as data, which would
    have made every port interval narrower than the evidence supports (1.5).
    """
    r = parameter_draws(posterior, "R_onboard")
    share = parameter_draws(posterior, "import_share")
    aboard = parameter_draws(posterior, "aboard_cases")
    return {
        "r_onboard_mean": float(r.mean()),
        "r_onboard_q05": float(np.quantile(r, 0.05)),
        "r_onboard_q95": float(np.quantile(r, 0.95)),
        "import_share_mean": float(share.mean()),
        "import_share_q05": float(np.quantile(share, 0.05)),
        "import_share_q95": float(np.quantile(share, 0.95)),
        "aboard_cases_mean": float(aboard.mean()),
    }


def hazard_rows(estimates: Sequence[PortHazardEstimate]) -> list[dict[str, Any]]:
    """Flatten estimates for CSV output."""
    return [
        {
            "port_id": e.port_id,
            "port_visit_key": e.port_visit_key or "",
            "pathogen": e.pathogen,
            "hazard_mean": e.hazard_mean,
            "hazard_q05": e.hazard_q05,
            "hazard_q95": e.hazard_q95,
            "n_attributed_cases": e.n_attributed_cases,
            "censoring_corrected": e.censoring_corrected,
            "port_resolution_adequate": e.port_resolution_adequate,
            "loglik_clinical": e.evidence_loglik.get(CLINICAL_CHANNEL, ""),
        }
        for e in estimates
    ]


HAZARD_COLUMNS = (
    "port_id",
    "port_visit_key",
    "pathogen",
    "hazard_mean",
    "hazard_q05",
    "hazard_q95",
    "n_attributed_cases",
    "censoring_corrected",
    "port_resolution_adequate",
    "loglik_clinical",
)
