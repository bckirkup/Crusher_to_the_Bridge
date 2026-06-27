"""Numeric and RNG helpers for deterministic, Sonar-safe simulation code."""

from __future__ import annotations

import math

import numpy as np

DEFAULT_SIMULATION_SEED = 42


def default_simulation_rng(seed: int | None = None) -> np.random.Generator:
    """Return a seeded NumPy Generator for reproducible stochastic draws."""
    return np.random.default_rng(DEFAULT_SIMULATION_SEED if seed is None else seed)


def float_eq(
    left: float,
    right: float,
    *,
    rel_tol: float = 1e-9,
    abs_tol: float = 0.0,
) -> bool:
    """Compare floating-point values with tolerance instead of exact equality."""
    return math.isclose(left, right, rel_tol=rel_tol, abs_tol=abs_tol)


def float_ne(
    left: float,
    right: float,
    *,
    rel_tol: float = 1e-9,
    abs_tol: float = 0.0,
) -> bool:
    """Return True when two floats differ beyond tolerance."""
    return not float_eq(left, right, rel_tol=rel_tol, abs_tol=abs_tol)


def is_zero(value: float, *, rel_tol: float = 1e-9, abs_tol: float = 0.0) -> bool:
    """Return True when *value* is effectively zero."""
    return float_eq(value, 0.0, rel_tol=rel_tol, abs_tol=abs_tol)


def is_nonzero(value: float, *, rel_tol: float = 1e-9, abs_tol: float = 0.0) -> bool:
    """Return True when *value* is not effectively zero."""
    return float_ne(value, 0.0, rel_tol=rel_tol, abs_tol=abs_tol)
