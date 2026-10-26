"""Reducer readout helpers — NA/no-denominator semantics (ticket D1).

The legacy ``tools/diag/readout_common.py::wilson_centered`` returns
``(0, 0, 0)`` for ``n <= 0``, which fabricates a confident zero rate for a
measurement that never happened. The reducer layer must emit
NA/no-denominator instead: ``wilson_interval`` returns ``None`` below a
positive denominator, and ``rate_row`` emits the row only when a
denominator exists. The legacy helper keeps its signature and its
behaviour — nothing in tools/ is patched.
"""
from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

Z95 = 1.959963984540054


def inclusive_endpoint_hit(native_token: str, threshold_token: str) -> bool:
    """Inclusive endpoint comparison on native lexical tokens.

    The legacy reporter's floating ``0.90 pp`` endpoint rejection compared
    parsed floats, so an emitted token like ``"0.8999999999999999"`` for a
    semantic ``0.90`` boundary could land on the wrong side. Endpoints are
    compared exactly — ``Decimal`` on the stored token, inclusive.
    """
    return Decimal(native_token) >= Decimal(threshold_token)


def wilson_interval(k: int, n: int, z: float = Z95) -> tuple[float, float, float] | None:
    """Wilson (center, lo, hi) for k/n, or None for n <= 0.

    Unlike the legacy ``wilson_centered``, a missing/zero denominator is NA
    here — the caller emits a ``data_gaps`` row with ``denominator_zero``
    rather than a rate of 0.0.
    """
    if n <= 0:
        return None
    p = k / n
    center = p + z * z / (2 * n)
    span = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    norm = 1 + z * z / n
    return (center / norm, (center - span) / norm, (center + span) / norm)


def rate_row(k: int, n: int, z: float = Z95) -> dict[str, Any]:
    """A rate summary row: ``None`` columns when the denominator is absent.

    Zero observed events against a real denominator is a measurement
    (k=0 → nonzero upper bound); a missing denominator is not.
    """
    interval = wilson_interval(k, n, z)
    if interval is None:
        return {
            "numerator": k,
            "denominator": n,
            "rate": None,
            "center": None,
            "lo": None,
            "hi": None,
            "denominator_status": "no_denominator",
        }
    center, lo, hi = interval
    return {
        "numerator": k,
        "denominator": n,
        "rate": k / n,
        "center": center,
        "lo": lo,
        "hi": hi,
        "denominator_status": "measured",
    }
