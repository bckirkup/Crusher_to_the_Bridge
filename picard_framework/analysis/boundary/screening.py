"""Wearable adoption, anomaly signals, confirmatory testing, boarding policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

POLICIES = ("P0", "P1", "P2", "P3", "P4", "P5")

# P4 uses P2 boarding mechanics with higher adoption.
P4_BOARDING_POLICY = "P2"


@dataclass(frozen=True)
class ScreeningResult:
    """Per-voyage screening outcomes after policy application."""

    adopted: np.ndarray
    flagged: np.ndarray
    confirmed_pos: np.ndarray
    denied: np.ndarray
    n_fp: int  # denied and not infectious
    n_tp: int  # denied and infectious
    n_secondary: int
    k_board: int
    intercepted: int


def adoption_draw(
    *,
    is_crew: np.ndarray,
    adoption_pax: float,
    adoption_crew: float,
    policy: str,
    rng: np.random.Generator,
) -> np.ndarray:
    """Bernoulli adoption; P0/P1 have no operational adoption draws.

    P1 is advisory-only in v1 (self-delay rate 0): skip adoption/signal RNG
    so the boarding path matches P0 voyage-for-voyage under the same seed.
    """
    n = len(is_crew)
    if n == 0 or policy in ("P0", "P1"):
        return np.zeros(n, dtype=np.int8)

    a_pax = float(adoption_pax)
    a_crew = float(adoption_crew)
    if policy == "P4":
        a_pax = max(a_pax, 0.70)
    if policy == "P5":
        a_crew = 1.0

    a = np.where(is_crew, a_crew, a_pax).astype(float)
    return rng.binomial(1, a).astype(np.int8)


def wearable_signal(
    *,
    z: np.ndarray,
    adopted: np.ndarray,
    se_w: float,
    sp_w: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Anomaly flag W_i among adopters (0 if not adopted)."""
    n = len(z)
    w = np.zeros(n, dtype=np.int8)
    mask = adopted.astype(bool)
    if not mask.any():
        return w
    infectious = z.astype(bool) & mask
    non_inf = (~z.astype(bool)) & mask
    if infectious.any():
        w[infectious] = rng.binomial(1, float(se_w), size=int(infectious.sum())).astype(
            np.int8
        )
    if non_inf.any():
        w[non_inf] = rng.binomial(1, 1.0 - float(sp_w), size=int(non_inf.sum())).astype(
            np.int8
        )
    return w


def confirmatory_test(
    *,
    z: np.ndarray,
    flagged: np.ndarray,
    se_confirm: float,
    sp_confirm: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Confirmatory test result for flagged passengers (0 if not tested)."""
    n = len(z)
    t = np.zeros(n, dtype=np.int8)
    mask = flagged.astype(bool)
    if not mask.any():
        return t
    infectious = z.astype(bool) & mask
    non_inf = (~z.astype(bool)) & mask
    if infectious.any():
        t[infectious] = rng.binomial(
            1, float(se_confirm), size=int(infectious.sum())
        ).astype(np.int8)
    if non_inf.any():
        t[non_inf] = rng.binomial(
            1, 1.0 - float(sp_confirm), size=int(non_inf.sum())
        ).astype(np.int8)
    return t


def apply_policy(
    *,
    policy: str,
    z: np.ndarray,
    flagged: np.ndarray,
    confirmed_pos: np.ndarray,
) -> np.ndarray:
    """Return deny mask (1 = denied boarding)."""
    boarding = policy
    if policy == "P4":
        boarding = P4_BOARDING_POLICY

    if boarding in ("P0", "P1"):
        return np.zeros_like(z, dtype=np.int8)
    if boarding == "P2":
        # Deny only if confirmatory positive.
        return (flagged.astype(bool) & confirmed_pos.astype(bool)).astype(np.int8)
    if boarding == "P3":
        return flagged.astype(np.int8)
    if boarding == "P5":
        # Crew+passenger: same as P2 for denied boarding.
        return (flagged.astype(bool) & confirmed_pos.astype(bool)).astype(np.int8)
    raise ValueError(f"Unknown policy: {policy}")


def needs_confirmation(policy: str) -> bool:
    if policy == "P4":
        return True  # P4 uses P2 mechanics
    return policy in ("P2", "P5")


def run_screening(
    *,
    z: np.ndarray,
    is_crew: np.ndarray,
    policy: str,
    adoption_pax: float,
    adoption_crew: float,
    se_w: float,
    sp_w: float,
    se_confirm: float,
    sp_confirm: float,
    rng: np.random.Generator,
) -> ScreeningResult:
    """Full adoption → signal → optional confirm → deny pipeline."""
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy: {policy}")

    adopted = adoption_draw(
        is_crew=is_crew,
        adoption_pax=adoption_pax,
        adoption_crew=adoption_crew,
        policy=policy,
        rng=rng,
    )
    flagged = wearable_signal(
        z=z, adopted=adopted, se_w=se_w, sp_w=sp_w, rng=rng
    )

    if needs_confirmation(policy):
        confirmed = confirmatory_test(
            z=z,
            flagged=flagged,
            se_confirm=se_confirm,
            sp_confirm=sp_confirm,
            rng=rng,
        )
        n_secondary = int(flagged.sum())
    else:
        confirmed = np.zeros_like(z, dtype=np.int8)
        n_secondary = 0

    denied = apply_policy(
        policy=policy, z=z, flagged=flagged, confirmed_pos=confirmed
    )
    boarded_infectious = z.astype(bool) & ~denied.astype(bool)
    intercepted = int((z.astype(bool) & denied.astype(bool)).sum())
    n_tp = intercepted
    n_fp = int((~z.astype(bool) & denied.astype(bool)).sum())

    return ScreeningResult(
        adopted=adopted,
        flagged=flagged,
        confirmed_pos=confirmed,
        denied=denied,
        n_fp=n_fp,
        n_tp=n_tp,
        n_secondary=n_secondary,
        k_board=int(boarded_infectious.sum()),
        intercepted=intercepted,
    )


def screening_params_from_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "policy": str(scenario["policy"]),
        "adoption_pax": float(scenario.get("adoption_pax", 0.43)),
        "adoption_crew": float(scenario.get("adoption_crew", 1.0)),
        "se_w": float(scenario.get("Se_w", 0.65)),
        "sp_w": float(scenario.get("Sp_w", 0.85)),
        "se_confirm": float(scenario.get("Se_confirm", 0.90)),
        "sp_confirm": float(scenario.get("Sp_confirm", 0.98)),
    }
