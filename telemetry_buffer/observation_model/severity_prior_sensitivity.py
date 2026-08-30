"""How flexible are the 20 severity/observation numbers?

Propagates the priors Edison supplied (Dirichlet concentration 80 on the severity
simplex; named coherent scenario sets for eligibility and reporting) through to
the derived anchors, and ranks the components by elasticity so unidentifiable
ones can be declared rather than pinned.

Run: python3 telemetry_buffer/observation_model/severity_prior_sensitivity.py
"""

from __future__ import annotations

import numpy as np

STATES = ["asymptomatic", "subclinical", "mild", "moderate", "severe_critical"]

PI = np.array([0.25, 0.55, 0.19, 0.009, 0.001])
Q = np.array([0.0, 0.55, 0.98, 1.0, 1.0])
R_POST = np.array([0.0, 0.50, 0.76, 0.96, 1.0])
R_PRE = np.array([0.0, 0.45, 0.70, 0.94, 1.0])
R_AVOID = np.array([0.0, 0.25, 0.55, 0.95, 1.0])  # isolation-avoidance scenario

CONCENTRATION = 80.0
ASYMP_RANGE = (0.19, 0.35)
MODERATE_RANGE = (0.002, 0.03)
AGE_TRANSFER_RANGE = (0.01, 0.03)
ANCHOR_REPORTED_OVER_ELIGIBLE = (0.55, 0.65)


def anchors(pi: np.ndarray, q: np.ndarray, r: np.ndarray) -> dict[str, float]:
    """Derived observation anchors implied by one coherent parameter set."""
    eligible = float(pi @ q)
    reported = float(pi @ (q * r))
    symptomatic = float(1.0 - pi[0])
    return {
        "eligible/infected": eligible,
        "reported/infected": reported,
        "reported/eligible": reported / eligible,
        "reported/symptomatic": reported / symptomatic,
    }


def _shift_moderate(pi: np.ndarray, target_moderate: float) -> np.ndarray:
    """Move mass into moderate from the leftward symptomatic states, coherently."""
    out = pi.copy()
    delta = target_moderate - pi[3]
    donor = np.array([0.0, pi[1], pi[2], 0.0, 0.0])
    out = out - delta * donor / donor.sum()
    out[3] = target_moderate
    return out / out.sum()


def _rescale_asymptomatic(pi: np.ndarray, target_asymp: float) -> np.ndarray:
    """Hold the symptomatic shape, move the asymptomatic fraction."""
    out = pi.copy()
    out[1:] = pi[1:] * (1.0 - target_asymp) / (1.0 - pi[0])
    out[0] = target_asymp
    return out / out.sum()


def scenario_set() -> dict[str, dict[str, float]]:
    """Named coherent scenarios, not component-by-component sweeps."""
    scenarios: dict[str, dict[str, float]] = {
        "central (post-recognition)": anchors(PI, Q, R_POST),
        "pre-recognition": anchors(PI, Q, R_PRE),
        "isolation-avoidance post-recognition": anchors(PI, Q, R_AVOID),
    }
    for label, value in (("low", ASYMP_RANGE[0]), ("high", ASYMP_RANGE[1])):
        scenarios[f"asymptomatic {label} ({value:.2f})"] = anchors(
            _rescale_asymptomatic(PI, value), Q, R_POST,
        )
    for label, value in (("low", MODERATE_RANGE[0]), ("high", MODERATE_RANGE[1])):
        scenarios[f"moderate {label} ({value:.3f})"] = anchors(
            _shift_moderate(PI, value), Q, R_POST,
        )
    for value in AGE_TRANSFER_RANGE:
        scenarios[f"cruise-age transfer {value:.2f} into moderate"] = anchors(
            _shift_moderate(PI, PI[3] + value), Q, R_POST,
        )
    return scenarios


def dirichlet_spread(draws: int, seed: int) -> dict[str, np.ndarray]:
    """Propagate Dirichlet(mean * concentration) through the anchors."""
    rng = np.random.default_rng(seed)
    samples = rng.dirichlet(PI * CONCENTRATION, size=draws)
    eligible = samples @ Q
    reported = samples @ (Q * R_POST)
    return {
        "eligible/infected": eligible,
        "reported/infected": reported,
        "reported/eligible": reported / eligible,
        "reported/symptomatic": reported / (1.0 - samples[:, 0]),
        "asymptomatic/infected": samples[:, 0],
    }


def elasticities() -> list[tuple[str, float, float]]:
    """d ln(anchor) / d ln(component), simplex-respecting for severity."""
    step = 0.01
    base = anchors(PI, Q, R_POST)
    rows: list[tuple[str, float, float]] = []

    for i, state in enumerate(STATES):
        if PI[i] <= 0.0:
            continue
        bumped = PI.copy()
        bumped[i] = PI[i] * (1.0 + step)
        bumped = bumped / bumped.sum()
        moved = anchors(bumped, Q, R_POST)
        rows.append((
            f"pi[{state}]",
            (moved["reported/eligible"] / base["reported/eligible"] - 1.0) / step,
            (moved["reported/infected"] / base["reported/infected"] - 1.0) / step,
        ))

    for name, vec, is_q in (("q", Q, True), ("r_post", R_POST, False)):
        for i, state in enumerate(STATES):
            if vec[i] <= 0.0:
                continue
            bumped = vec.copy()
            bumped[i] = min(1.0, vec[i] * (1.0 + step))
            actual = bumped[i] / vec[i] - 1.0
            if actual <= 0.0:
                rows.append((f"{name}[{state}]", 0.0, 0.0))
                continue
            moved = anchors(PI, bumped if is_q else Q, R_POST if is_q else bumped)
            rows.append((
                f"{name}[{state}]",
                (moved["reported/eligible"] / base["reported/eligible"] - 1.0) / actual,
                (moved["reported/infected"] / base["reported/infected"] - 1.0) / actual,
            ))
    return rows


def main() -> None:
    print("=" * 78)
    print("Central case")
    for key, value in anchors(PI, Q, R_POST).items():
        print(f"  {key:24s} {value:.4f}")

    print("=" * 78)
    print("Coherent scenario set (eligibility/reporting/severity, no naked sweeps)")
    print(f"  {'scenario':40s} {'elig/inf':>9s} {'rep/inf':>9s} "
          f"{'rep/elig':>9s} {'rep/sym':>9s}")
    for label, vals in scenario_set().items():
        print(f"  {label:40s} {vals['eligible/infected']:9.4f} "
              f"{vals['reported/infected']:9.4f} "
              f"{vals['reported/eligible']:9.4f} "
              f"{vals['reported/symptomatic']:9.4f}")

    print("=" * 78)
    print(f"Dirichlet(mean x {CONCENTRATION:.0f}) propagation, 40k draws")
    spread = dirichlet_spread(40_000, seed=20260829)
    print(f"  {'quantity':24s} {'2.5%':>8s} {'50%':>8s} {'97.5%':>8s} {'width/med':>10s}")
    for key, arr in spread.items():
        lo, mid, hi = np.percentile(arr, [2.5, 50, 97.5])
        print(f"  {key:24s} {lo:8.4f} {mid:8.4f} {hi:8.4f} {(hi - lo) / mid:10.3f}")

    inside = np.mean(
        (spread["reported/eligible"] >= ANCHOR_REPORTED_OVER_ELIGIBLE[0])
        & (spread["reported/eligible"] <= ANCHOR_REPORTED_OVER_ELIGIBLE[1]),
    )
    print(f"  P(reported/eligible inside the 0.60 +/- 0.05 anchor) = {inside:.3f}")

    print("=" * 78)
    print("Elasticity, d ln(anchor) / d ln(component)")
    rows = sorted(elasticities(), key=lambda r: -abs(r[2]))
    print(f"  {'component':26s} {'rep/elig':>10s} {'rep/inf':>10s}")
    for name, e_elig, e_inf in rows:
        flag = "  <- unidentifiable" if abs(e_inf) < 0.01 else ""
        print(f"  {name:26s} {e_elig:10.4f} {e_inf:10.4f}{flag}")


if __name__ == "__main__":
    main()
