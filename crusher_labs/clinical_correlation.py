"""
Gaussian-copula correlation between clinical diagnostic instruments.

Draws a correlated latent standard-normal vector per patient per panel run,
maps each component to a uniform via the normal CDF, and passes those uniforms
into ``ClinicalRapidDiagnostic``, ``ClinicalQPCR``, and ``ClinicalMicrobiology``.

When the autocorrelation matrix is identity (default off-diagonal 0), draws are
independent and behavior matches the legacy uncorrelated path.
"""

from __future__ import annotations

import math
from statistics import NormalDist
from dataclasses import dataclass
from typing import Any

import numpy as np

from telemetry_buffer.agent_axes import agent_is_infected, resolve_agent_axes

CLINICAL_TEST_KEYS: tuple[str, ...] = (
    "clinical_rdt",
    "clinical_qpcr",
    "clinical_microbiology",
)

DEFAULT_AUTOCORRELATION_MATRIX: list[list[float]] = [
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
]


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _normal_ppf(u: float) -> float:
    clipped = float(np.clip(u, 1e-12, 1.0 - 1e-12))
    return float(NormalDist().inv_cdf(clipped))


def parse_autocorrelation_matrix(
    raw: Any,
    *,
    test_order: tuple[str, ...] = CLINICAL_TEST_KEYS,
) -> np.ndarray:
    """Parse config into an ``n x n`` correlation matrix with unit diagonal."""
    n = len(test_order)
    if raw is None:
        return np.eye(n, dtype=np.float64)

    if isinstance(raw, list) and raw and isinstance(raw[0], list):
        matrix = np.asarray(raw, dtype=np.float64)
        if matrix.shape != (n, n):
            raise ValueError(
                f"autocorrelation_matrix must be {n}x{n}, got {matrix.shape}",
            )
        return matrix

    if isinstance(raw, dict):
        matrix = np.eye(n, dtype=np.float64)
        key_to_idx = {key: idx for idx, key in enumerate(test_order)}
        for row_key, row_vals in raw.items():
            if row_key not in key_to_idx:
                raise ValueError(f"unknown clinical test key: {row_key}")
            i = key_to_idx[row_key]
            if isinstance(row_vals, dict):
                for col_key, value in row_vals.items():
                    if col_key not in key_to_idx:
                        raise ValueError(f"unknown clinical test key: {col_key}")
                    matrix[i, key_to_idx[col_key]] = float(value)
            else:
                raise ValueError(
                    f"autocorrelation_matrix row '{row_key}' must be a mapping",
                )
        return matrix

    raise ValueError(
        "autocorrelation_matrix must be a square list-of-lists or nested mapping",
    )


def validate_autocorrelation_matrix(matrix: np.ndarray) -> None:
    """Raise ``ValueError`` when *matrix* is not a valid correlation matrix."""
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("autocorrelation_matrix must be square")
    if not np.allclose(np.diag(matrix), 1.0, atol=1e-6):
        raise ValueError("autocorrelation_matrix diagonal entries must be 1.0")
    if not np.allclose(matrix, matrix.T, atol=1e-6):
        raise ValueError("autocorrelation_matrix must be symmetric")
    sym = 0.5 * (matrix + matrix.T)
    try:
        np.linalg.cholesky(sym)
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            "autocorrelation_matrix must be positive semi-definite",
        ) from exc


@dataclass
class ClinicalTestCorrelation:
    """Correlated uniform sampler for the three sick-call clinical instruments."""

    correlation_matrix: np.ndarray
    test_order: tuple[str, ...] = CLINICAL_TEST_KEYS
    rng: np.random.Generator | None = None
    _cholesky: np.ndarray | None = None

    def __post_init__(self) -> None:
        validate_autocorrelation_matrix(self.correlation_matrix)
        sym = 0.5 * (self.correlation_matrix + self.correlation_matrix.T)
        self._cholesky = np.linalg.cholesky(sym)
        if self.rng is None:
            self.rng = np.random.default_rng()

    @classmethod
    def from_config(
        cls,
        cfg: dict[str, Any] | None,
        *,
        seed: int = 42,
    ) -> ClinicalTestCorrelation:
        block = (cfg or {}).get("clinical_diagnostics", {})
        test_order = tuple(block.get("test_order", CLINICAL_TEST_KEYS))
        if tuple(test_order) != CLINICAL_TEST_KEYS:
            raise ValueError(
                f"clinical_diagnostics.test_order must be {list(CLINICAL_TEST_KEYS)}",
            )
        matrix = parse_autocorrelation_matrix(
            block.get("autocorrelation_matrix"),
            test_order=CLINICAL_TEST_KEYS,
        )
        return cls(
            correlation_matrix=matrix,
            test_order=CLINICAL_TEST_KEYS,
            rng=np.random.default_rng(seed + 11),
        )

    @property
    def is_independent(self) -> bool:
        off_diag = self.correlation_matrix.copy()
        np.fill_diagonal(off_diag, 0.0)
        return bool(np.allclose(off_diag, 0.0, atol=1e-12))

    def sample_uniforms(self) -> dict[str, float]:
        """Draw one correlated uniform per clinical test for a single patient."""
        assert self._cholesky is not None
        z = self.rng.standard_normal(len(self.test_order))
        correlated = self._cholesky @ z
        return {
            key: _normal_cdf(float(correlated[idx]))
            for idx, key in enumerate(self.test_order)
        }

    def run_agent_tests(
        self,
        obs: Any,
        agent: dict[str, Any],
        *,
        test_keys: tuple[str, ...] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Run selected clinical tests on one agent with correlated noise."""
        keys = test_keys or CLINICAL_TEST_KEYS
        uniforms = self.sample_uniforms()
        aid = int(agent["agent_id"])
        infection, presentation, compliance = resolve_agent_axes(agent)
        location = agent.get("location", "unknown")
        results: dict[str, dict[str, Any]] = {}

        for key in keys:
            if key in ("clinical_rdt", "clinical_multiplex_panel"):
                results[key] = obs.clin_rdt.test_agent(
                    aid,
                    agent.get("shedding_rate", 0.0),
                    agent_is_infected(agent),
                    infection,
                    presentation,
                    compliance,
                    location,
                    uniform_draw=uniforms["clinical_rdt"],
                )
            elif key == "clinical_qpcr":
                results[key] = obs.clin_qpcr.test_agent(
                    aid,
                    agent.get("shedding_rate", 0.0),
                    infection,
                    presentation,
                    compliance,
                    location,
                    uniform_draw=uniforms["clinical_qpcr"],
                )
            elif key == "clinical_microbiology":
                results[key] = obs.clin_microbio.test_agent(
                    aid,
                    agent.get("microflora_disruption", 0.0),
                    infection,
                    presentation,
                    compliance,
                    location,
                    agent.get("pathogen_infections"),
                    uniform_draw=uniforms["clinical_microbiology"],
                )
        return results


def run_correlated_clinical_panel(
    obs: Any,
    agents: list[dict[str, Any]],
    correlation: ClinicalTestCorrelation,
) -> tuple[dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
    """Run the full sick-call clinical panel with per-agent correlated draws."""
    clin_rdt_results: dict[int, dict[str, Any]] = {}
    clin_qpcr_results: dict[int, dict[str, Any]] = {}
    clin_microbio_results: dict[int, dict[str, Any]] = {}

    for agent in agents:
        aid = int(agent["agent_id"])
        panel = correlation.run_agent_tests(obs, agent)
        clin_rdt_results[aid] = panel["clinical_rdt"]
        clin_qpcr_results[aid] = panel["clinical_qpcr"]
        clin_microbio_results[aid] = panel["clinical_microbiology"]

    return clin_rdt_results, clin_qpcr_results, clin_microbio_results


def clinical_diagnostics_params(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve ``clinical_diagnostics`` block from *cfg*."""
    block = (cfg or {}).get("clinical_diagnostics", {})
    return {
        "test_order": tuple(block.get("test_order", CLINICAL_TEST_KEYS)),
        "autocorrelation_matrix": block.get(
            "autocorrelation_matrix", DEFAULT_AUTOCORRELATION_MATRIX,
        ),
    }
