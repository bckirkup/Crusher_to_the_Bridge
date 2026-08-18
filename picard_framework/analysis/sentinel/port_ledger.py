"""Port surveillance ledgers: generate for every port, ablate at analysis time.

A ledger is the port-side counterpart of a ship's observation bundle. It is
written once per voyage (or per itinerary), holds every channel for every port
whether or not that port runs a programme, and carries the capability metadata
next to the signals so a later analysis can decide what to believe.

Generation is driven by the *same* per-port shore hazard the simulation used to
infect passengers ashore, so the latent prevalence behind a port signal and the
latent prevalence behind a ship infection are one number, not two draws. That is
what makes ``corr(inferred λ_p, port signal)`` a validation rather than a
coincidence.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import asdict
from datetime import date
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from picard_framework.analysis._io import ensure_out_dir, safe_path, write_json
from picard_framework.analysis.sentinel.port_health import (
    CHANNELS,
    PortEpidemiologicalState,
    PortSurveillanceCapability,
    PrevalenceLink,
    ablate_series,
    generate_port_series,
    resolve_channels,
    state_from_dict,
)
from picard_framework.analysis.sentinel.port_profiles import capability_or_default

LEDGER_SCHEMA_VERSION = "1.0"
DEFAULT_LEDGER_DAYS = 7
DEFAULT_SEED = 1701


def _port_rng(seed: int, port_id: str) -> np.random.Generator:
    """A per-port stream so adding a port cannot renumber another port's draws."""
    digest = sum((index + 1) * ord(ch) for index, ch in enumerate(port_id))
    return np.random.default_rng([int(seed), int(digest)])


def _prevalence_curve(
    prevalence: float,
    n_days: int,
) -> tuple[float, ...]:
    """A flat community prevalence over the window.

    Flat because the campaign's port hazards are themselves constant per port:
    inventing a community epidemic curve here would put structure in the port
    signal that the ship-side truth does not have.
    """
    return tuple(float(prevalence) for _ in range(max(int(n_days), 0)))


def build_port_ledger(
    *,
    port_hazards: Mapping[str, float],
    pathogen: str,
    n_days: int = DEFAULT_LEDGER_DAYS,
    seed: int = DEFAULT_SEED,
    link: PrevalenceLink | None = None,
    start_date: date | None = None,
    capabilities: Mapping[str, PortSurveillanceCapability] | None = None,
    genotype: str | None = None,
) -> dict[str, Any]:
    """Signals for every port in ``port_hazards``, all channels, every day."""
    model = link or PrevalenceLink()
    rows: list[dict[str, Any]] = []
    caps: dict[str, Any] = {}
    for port_id in sorted(port_hazards):
        capability = (capabilities or {}).get(port_id) or capability_or_default(port_id)
        prevalence = model.prevalence_from_hazard(float(port_hazards[port_id]))
        states = generate_port_series(
            capability,
            pathogen=pathogen,
            prevalence_by_day=_prevalence_curve(prevalence, n_days),
            rng=_port_rng(seed, port_id),
            link=model,
            start_date=start_date,
            genotype=genotype,
        )
        rows.extend(state.as_row() for state in states)
        caps[port_id] = capability.to_metadata()
    return {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "pathogen": str(pathogen),
        "n_days": int(n_days),
        "seed": int(seed),
        "start_date": None if start_date is None else start_date.isoformat(),
        "prevalence_link": asdict(model),
        "port_hazards": {k: float(v) for k, v in port_hazards.items()},
        "capabilities": caps,
        "observations": rows,
    }


def hazards_from_itinerary(days: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    """Per-port shore hazard from voyage itinerary day slots.

    Repeated calls at one port (the home port is called twice) collapse to the
    single hazard that port carries, since the hazard is a property of the
    community and not of the visit.
    """
    hazards: dict[str, float] = {}
    for day in days:
        port_id = str(day.get("port_id") or "")
        if not port_id:
            continue
        hazard = float(day.get("shore_infection_probability") or 0.0)
        hazards[port_id] = max(hazards.get(port_id, 0.0), hazard)
    return hazards


def ledger_from_itinerary(
    days: Sequence[Mapping[str, Any]],
    *,
    pathogen: str,
    seed: int = DEFAULT_SEED,
    link: PrevalenceLink | None = None,
    start_date: date | None = None,
    n_days: int | None = None,
    genotype: str | None = None,
) -> dict[str, Any]:
    """Ledger for the ports of one voyage itinerary."""
    hazards = hazards_from_itinerary(days)
    return build_port_ledger(
        port_hazards=hazards,
        pathogen=pathogen,
        n_days=int(n_days if n_days is not None else len(days)),
        seed=seed,
        link=link,
        start_date=start_date,
        genotype=genotype,
    )


def _ledger_capability(ledger: Mapping[str, Any], port_id: str) -> PortSurveillanceCapability:
    block = (ledger.get("capabilities") or {}).get(port_id)
    if block is None:
        return capability_or_default(port_id)
    return PortSurveillanceCapability.from_mapping(block, port_id=port_id)


def states_by_port(
    ledger: Mapping[str, Any],
) -> dict[str, tuple[PortEpidemiologicalState, ...]]:
    """Ledger rows grouped back into per-port series."""
    grouped: dict[str, list[PortEpidemiologicalState]] = {}
    for row in ledger.get("observations") or ():
        state = state_from_dict(row)
        grouped.setdefault(state.port_id, []).append(state)
    return {
        port_id: tuple(sorted(states, key=lambda s: s.day_index))
        for port_id, states in grouped.items()
    }


def ablate_ledger(
    ledger: Mapping[str, Any],
    *,
    channels: Iterable[str] | None = None,
    respect_capability: bool = True,
) -> dict[str, Any]:
    """Fleet-analysis view of a ledger: keep the channels this analysis uses.

    The generated ledger is never edited in place — an ablation is a *view*, so
    the same ledger supports a WBE-only arm, a syndromic-only arm, and a
    no-port-data arm without regenerating anything.
    """
    kept = resolve_channels(channels)
    rows: list[dict[str, Any]] = []
    for port_id, states in states_by_port(ledger).items():
        capability = _ledger_capability(ledger, port_id)
        rows.extend(
            state.as_row()
            for state in ablate_series(
                states,
                capability,
                channels=kept,
                respect_capability=respect_capability,
            )
        )
    view = dict(ledger)
    view["observations"] = sorted(rows, key=lambda r: (r["port_id"], r["day_index"]))
    view["ablation"] = {
        "channels": list(kept),
        "respect_capability": bool(respect_capability),
    }
    return view


def _mean(values: Sequence[float]) -> float | None:
    return float(sum(values) / len(values)) if values else None


def port_signal_table(ledger: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One row per port: the summaries a hazard correlation consumes.

    ``None`` marks a port that contributes nothing to a given comparison — an
    ablated or uninstrumented channel is excluded from the correlation instead
    of being scored as a zero, which would fabricate agreement at exactly the
    ports the argument is about.
    """
    table: list[dict[str, Any]] = []
    for port_id, states in sorted(states_by_port(ledger).items()):
        rates = [
            s.syndromic_rate_per_100k
            for s in states
            if s.syndromic_rate_per_100k is not None
        ]
        sampled = [
            s for s in states if s.wbe_sampled and s.wbe_gc_per_l_observed is not None
        ]
        detections = [1.0 if s.wbe_detected else 0.0 for s in sampled]
        log_gc = [math.log10(max(s.wbe_gc_per_l_observed or 0.0, 1e-3)) for s in sampled]
        confirmed = [
            float(s.lab_confirmed_cases)
            for s in states
            if s.lab_confirmed_cases is not None
        ]
        table.append({
            "port_id": port_id,
            "n_days": len(states),
            "true_community_prevalence": _mean(
                [s.true_community_prevalence for s in states],
            ),
            "true_log10_gc_per_l": _mean(
                [math.log10(max(s.true_ww_gc_per_l, 1e-3)) for s in states],
            ),
            "mean_syndromic_rate_per_100k": _mean(rates),
            "mean_lab_confirmed_cases": _mean(confirmed),
            "n_wbe_samples": len(sampled),
            "wbe_detection_fraction": _mean(detections),
            "mean_observed_log10_gc_per_l": _mean(log_gc),
            "alert_levels": sorted({s.alert_level for s in states}),
        })
    return table


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hazard",
        action="append",
        default=[],
        metavar="PORT=LAMBDA",
        help="per-port shore hazard per person-hour, repeatable",
    )
    # Required, not defaulted: the pathogen decides which authorities report at
    # all, so guessing it would silently change the ledger (Law 2).
    parser.add_argument("--pathogen", required=True)
    parser.add_argument("--days", type=int, default=DEFAULT_LEDGER_DAYS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--start-date", default=None)
    parser.add_argument(
        "--channels",
        default=",".join(CHANNELS),
        help="analysis-time ablation applied to the written view",
    )
    parser.add_argument(
        "--ignore-capability",
        action="store_true",
        help="keep selected channels even where the port runs no programme",
    )
    parser.add_argument("--out", default="tmp_port_health_out")
    return parser


def _parse_hazards(items: Sequence[str]) -> dict[str, float]:
    hazards: dict[str, float] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--hazard expects PORT=LAMBDA, got {item!r}")
        port_id, _, value = item.partition("=")
        hazards[port_id.strip().upper()] = float(value)
    if not hazards:
        raise SystemExit("at least one --hazard PORT=LAMBDA is required")
    return hazards


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = ensure_out_dir(safe_path(args.out))
    ledger = build_port_ledger(
        port_hazards=_parse_hazards(args.hazard),
        pathogen=args.pathogen,
        n_days=args.days,
        seed=args.seed,
        start_date=None if args.start_date is None else date.fromisoformat(args.start_date),
    )
    view = ablate_ledger(
        ledger,
        channels=[c for c in str(args.channels).split(",") if c],
        respect_capability=not args.ignore_capability,
    )
    write_json(f"{out}/port_surveillance_ledger.json", ledger)
    write_json(f"{out}/port_surveillance_analysis.json", view)
    write_json(f"{out}/port_signal_table.json", port_signal_table(view))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
