"""COVID-PACKET-01 analytic companion: carrier-packet occupancy.

The cooperative dose-law hypothesis (COVID-COOP-01) lives one level
below the host-level dose field: on the *packet* a carrier droplet
delivers to a single cell. A host can accrue a saturating dose while no
cell ever sees >= n virions if every carrier arrives with ~1 copy. This
module convolves each cell's emitted arrival field
(``summary.mechanism.packet_arrivals``) with a declared carrier model
and answers the discriminating question: whether any far-field arrival
packet ever exceeds ~1 RNA copy — and which channels do carry
multi-copy packets.

Declared packet model (all bounds from docs/ledger/COVID-COOP-01):

- one arrival increment (host x epoch x channel, post-efficiency dose
  units) = a stream of carrier droplets; delivered RNA copies =
  dose x EMISSION_BRACKET_COPIES_PER_EPOCH (Grade B bracket, the
  emission-side factor of the Theta composite — reported at both
  ends, never a point);
- carriers per class: occupancy K ~ Poisson(mu_class), the
  stuttering-Poisson emitted-packet field of Bound 3:
    dry  (zone_pool, hvac_airborne, other): mu in [0.004, 0.1]
        copies/carrier — the measured <=5um-dominated spectrum
        (Archer/Coleman/Alsved), i.e. almost every carrier is empty
        or a single;
    wet  (cabin_mate_ring, dining_ring, near_field_plume): mu in
        [0.04, 500] — droplet volume x respiratory titre over the
        20-100um class at saliva titres 1e6-1e9 copies/mL; this is
        the declared envelope, wider than the measured dry bound
        because the >30um class is rarely sampled;
- expected packets carrying >= n copies in an increment =
  (increment copies / mu) * P(Pois(mu) >= n); both asymptotic ends
  are linear in dose, so the emitted per-host dose_sum carries the
  convolution exactly and the log-histogram is a cross-check;
- n* is in *complete virions*, and the complete-genome fraction of
  emitted virions is unbounded (COVID-COOP-01 ?nr-term): a packet of
  K copies carries at most K complete virions, so the reported
  packet counts are strict upper bounds on the cooperative-
  relevant mass — packet >= n copies is necessary, not sufficient,
  for packet >= n complete virions.

Usage:
    python3 tools/covid_packet_analytic.py \
        --cells /path/to/cells_or_cells.json --out packet_read.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from picard_framework.covid_theta_fit import (  # noqa: E402
    EMISSION_BRACKET_COPIES_PER_EPOCH,
    EMISSION_BRACKET_GRADE,
)
from simulation_utils.paths import (  # noqa: E402
    resolve_repo_path,
    validated_open,
)
from tools.covid_rhythm_ab_readout import _cell_summaries  # noqa: E402
from tools.covid_route_attribution import _quantiles  # noqa: E402

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))

# Declared carrier classes over the instrument's channel names.
CHANNEL_CLASS: dict[str, str] = {
    "cabin_mate_ring": "wet",
    "dining_ring": "wet",
    "near_field_plume": "wet",
    "zone_pool": "dry",
    "hvac_airborne": "dry",
    "other": "dry",
    # No carrier semantics: the contact bolus is not an aerosol packet.
    "contact": "contact",
    # Droplet-pathway dose with no measured sub-split: reported as
    # delivered copies, excluded from packet claims.
    "droplet_unattributed": "unresolved",
}
# Mean RNA copies per carrier, declared per class (see docstring).
CARRIER_LOADING_COPIES: dict[str, tuple[float, float]] = {
    "dry": (0.004, 0.1),
    "wet": (0.04, 500.0),
}
# Cooperative-order candidates (COVID-COOP-01 Bound 4: n* in [2, 5]).
N_GRID: tuple[int, ...] = (2, 3, 5)
# Interior mu grid for the E-vs-mu envelope: E(mu) is nonmonotone
# (zero at both ends, peaked near mu ~ n), so endpoints alone would
# understate the achievable packet mass inside the declared range.
MU_GRID_LOG10 = (-3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5)
MU_GRID = tuple(10.0 ** e for e in MU_GRID_LOG10)


def poisson_tail(mu: float, n: int) -> float:
    """P(Pois(mu) >= n), evaluated on the small-n declared grid."""
    if mu <= 0.0:
        return 0.0
    surv = math.exp(-mu)
    term = 1.0
    total = 1.0
    for k in range(1, n):
        term *= mu / k
        total += term
    return 1.0 - surv * total


def _mu_envelope(cls: str) -> list[float]:
    """The declared mu range plus its interior grid points."""
    lo, hi = CARRIER_LOADING_COPIES[cls]
    mus = [m for m in MU_GRID if lo <= m <= hi]
    return [lo, *sorted(set(mus)), hi]


def _packets_per_copy(mu: float, n: int) -> float:
    """E[packets >= n copies] per delivered RNA copy: tail/mu."""
    return poisson_tail(mu, n) / mu


def _interval(vals: list[float]) -> list[float | None]:
    """[min, max] over the declared corners; None on empty."""
    return [min(vals), max(vals)] if vals else [None, None]


def channel_read(dose_sum: float, cls: str, bracket: float,
                 ns: tuple[int, ...] = N_GRID) -> dict[int, dict[str, float]]:
    """Expected >=n-copy packets in one dose-sum, over the mu range."""
    copies = float(dose_sum) * float(bracket)
    out: dict[int, dict[str, float]] = {}
    for n in ns:
        rates = [
            copies * _packets_per_copy(mu, n)
            for mu in _mu_envelope(cls)
        ]
        out[n] = {
            "expected_packets_interval": _interval(rates),
            "p_any_interval": _interval(
                [-math.expm1(-r) for r in rates]
            ),
        }
    return out


def cell_packet_read(cell: dict[str, Any]) -> dict[str, Any]:
    """One cell's packet read across channels x n x declared corners."""
    arrivals = (
        cell.get("summary", {}).get("mechanism", {})
        .get("packet_arrivals")
    )
    if not arrivals:
        raise SystemExit(
            "cell has no summary.mechanism.packet_arrivals — rerun "
            "covid_takeoff_attribution.py with --packet-arrivals"
        )
    brackets = list(EMISSION_BRACKET_COPIES_PER_EPOCH)
    by_channel = arrivals.get("by_channel", {})
    hosts = arrivals.get("by_host_channel", [])

    channels: dict[str, Any] = {}
    for channel, rec in sorted(by_channel.items()):
        cls = CHANNEL_CLASS.get(channel, "unresolved")
        dose_sum = float(rec.get("dose_sum") or 0.0)
        row: dict[str, Any] = {
            "carrier_class": cls,
            "n_increments": int(rec.get("n_increments") or 0),
            "dose_sum": dose_sum,
            "dose_max": float(rec.get("dose_max") or 0.0),
            "delivered_copies_interval": _interval(
                [dose_sum * b for b in brackets]
            ),
        }
        if cls in CARRIER_LOADING_COPIES:
            for n in N_GRID:
                e_bounds = [
                    rate
                    for b in brackets
                    for mu in _mu_envelope(cls)
                    for rate in [dose_sum * b * _packets_per_copy(mu, n)]
                ]
                # Per-host expected >=n packet counts -> share of
                # challenged hosts whose stream ever carries one.
                host_bounds: list[float] = []
                for b in brackets:
                    for mu in _mu_envelope(cls):
                        coef = b * _packets_per_copy(mu, n)
                        host_bounds.append(sum(
                            -math.expm1(
                                -float(h["channels"][channel]["dose_sum"])
                                * coef,
                            )
                            for h in hosts
                            if channel in h.get("channels", {})
                        ))
                row[f"n_ge_{n}"] = {
                    "expected_packets_interval": _interval(e_bounds),
                    "expected_hosts_any_interval": _interval(host_bounds),
                }
        channels[channel] = row

    return {
        "index": cell["cell"].get("index"),
        "class_id": cell["cell"].get("class_id"),
        "seed": cell["cell"].get("seed"),
        "theta": cell["cell"].get("theta"),
        "recorded_onsets": float(
            cell.get("summary", {}).get("recorded_onsets") or 0.0
        ),
        "infections_total": float(
            cell.get("summary", {}).get("infections_total") or 0.0
        ),
        "n_dosed_hosts": len(hosts),
        "channels": channels,
    }


def _channel_totals(reads: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum the per-cell expected-packet intervals per channel x n."""
    totals: dict[str, Any] = {}
    for read in reads:
        for channel, row in read["channels"].items():
            slot = totals.setdefault(channel, {
                "carrier_class": row["carrier_class"],
                "n_increments": 0,
                "dose_sum": 0.0,
            })
            slot["n_increments"] += row["n_increments"]
            slot["dose_sum"] += row["dose_sum"]
            for n in N_GRID:
                key = f"n_ge_{n}"
                if key not in row:
                    continue
                sub = slot.setdefault(key, {
                    "expected_packets_interval": [0.0, 0.0],
                    "expected_hosts_any_interval": [0.0, 0.0],
                })
                for i, v in enumerate(row[key]["expected_packets_interval"]):
                    sub["expected_packets_interval"][i] += float(v or 0.0)
                for i, v in enumerate(
                        row[key]["expected_hosts_any_interval"]):
                    sub["expected_hosts_any_interval"][i] += float(v or 0.0)
    return totals


def pool(cells: list[dict[str, Any]]) -> dict[str, Any]:
    reads = [cell_packet_read(c) for c in cells]
    n_hosts = _quantiles([float(r["n_dosed_hosts"]) for r in reads])
    return {
        "design": "covid_packet_01",
        "declared": {
            "emission_bracket_copies_per_epoch": list(
                EMISSION_BRACKET_COPIES_PER_EPOCH
            ),
            "emission_bracket_grade": EMISSION_BRACKET_GRADE,
            "carrier_class_map": CHANNEL_CLASS,
            "carrier_loading_copies": {
                k: list(v) for k, v in CARRIER_LOADING_COPIES.items()
            },
            "n_grid": list(N_GRID),
        },
        "note": (
            "packet counts are in RNA-copy units: a packet of K copies "
            "carries at most K complete virions (complete-genome "
            "fraction unbounded, COVID-COOP-01 ?nr-term), so every "
            "expected-packet figure is a strict upper bound on the "
            "cooperative-relevant count. Intervals span the Grade-B "
            "emission bracket x the declared carrier-loading range."
        ),
        "cells": reads,
        "pooled": {
            "n_cells": len(reads),
            "n_dosed_hosts_quantiles": n_hosts,
            "channel_totals": _channel_totals(reads),
        },
    }


def _load_cells(path: str) -> list[dict[str, Any]]:
    """A dir of per-cell JSONs, or one file holding the result list."""
    resolved = resolve_repo_path(REPO_ROOT, path)
    if os.path.isdir(resolved):
        return _cell_summaries(path)
    with validated_open(
        resolved, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8",
    ) as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and "summary" in payload:
        return [payload]
    raise SystemExit(f"unrecognized cells payload at {resolved}")


def main() -> None:  # pragma: no cover - CLI driver
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--cells", required=True,
        help="directory of cell JSONs, or one JSON file of cell results",
    )
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    cells = _load_cells(args.cells)
    if not cells:
        raise SystemExit(f"no cell payloads under {args.cells}")
    text = json.dumps(pool(cells), indent=1, default=str)
    if args.out:
        out_path = resolve_repo_path(REPO_ROOT, args.out)
        with validated_open(
            out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as handle:
            handle.write(text)
        print(f"wrote {out_path}")
    else:
        print(text)


if __name__ == "__main__":
    main()
