"""Multiphase fleet analysis: add one surveillance channel at a time.

The question the Sentinel design has to answer is not "can the model fit?" but
"what does each channel buy?". That is a staircase, not a single fit: clinical
line list alone, then the shipboard wastewater channel, then each port channel,
then everything. Each phase is a *separate* fit of the same fleet, so the change
in an interval is attributable to the channel that was added and nothing else.

Two invariants hold across every phase.

1. Port surveillance never enters the shipboard likelihood. Only the fleet
   manifest and the wastewater switch reach :func:`fit_sentinel_fleet`; the port
   ledger is read *after* sampling and used as an external comparison. A port
   signal that fed the fit could not then validate it, and no observation may
   acquire a port label of its own (spec §1.3).
2. A channel a port does not run, or that this phase ablated, is *excluded* from
   a comparison rather than scored as zero. Zero-filling would manufacture
   agreement at exactly the surveillance-desert ports the argument is about.
"""

from __future__ import annotations

import argparse
import math
import os
from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

from picard_framework.analysis._fit_exit import fit_exit_code, worst_exit_code
from picard_framework.analysis._io import (
    ensure_out_dir,
    read_json,
    safe_path,
    write_csv,
    write_json,
)
from picard_framework.analysis.sentinel.port_health import (
    CHANNEL_GENOTYPING,
    CHANNEL_LAB,
    CHANNEL_SYNDROMIC,
    CHANNEL_WBE,
    CHANNELS,
)
from picard_framework.analysis.sentinel.port_ledger import (
    ablate_ledger,
    port_signal_table,
)
from picard_framework.analysis.stan._sampler_options import SamplerOptions
from picard_framework.analysis.stan.fit_sentinel_fleet import fit_sentinel_fleet

PHASE_CLINICAL_ONLY = "clinical_only"
PHASE_CLINICAL_WASTEWATER = "clinical_wastewater"
PHASE_PORT_SYNDROMIC = "clinical_port_syndromic"
PHASE_PORT_WBE = "clinical_port_wbe"
PHASE_PORT_LAB = "clinical_port_laboratory"
PHASE_PORT_GENOTYPING = "clinical_port_genotyping"
PHASE_FULL = "full_surveillance"

MIN_CORRELATION_PORTS = 3
"""Two points define a line; a correlation over two ports is not evidence."""

# The port-side summary each channel is compared against. A channel with no
# numeric summary would be a name in a report and nothing else.
CHANNEL_SIGNALS: dict[str, str] = {
    CHANNEL_SYNDROMIC: "mean_syndromic_rate_per_100k",
    CHANNEL_WBE: "mean_observed_log10_gc_per_l",
    CHANNEL_LAB: "mean_lab_confirmed_cases",
    CHANNEL_GENOTYPING: "genotyped_day_fraction",
}

COMPARISON_COLUMNS = (
    "phase",
    "channel",
    "signal",
    "n_ports",
    "pearson_r",
    "spearman_rho",
    "excluded_ports",
)

_HAZARD_FLOOR = 1e-12


@dataclass(frozen=True)
class SurveillancePhase:
    """One rung of the staircase.

    ``wastewater`` is the only switch that changes the *fit*; ``port_channels``
    changes what the fit is compared against.
    """

    name: str
    wastewater: bool
    port_channels: tuple[str, ...]
    respect_capability: bool = True
    description: str = ""

    def __post_init__(self) -> None:
        unknown = [c for c in self.port_channels if c not in CHANNELS]
        if unknown:
            raise ValueError(f"phase {self.name} names unknown channels {unknown}")

    def to_metadata(self) -> dict[str, Any]:
        return {
            "phase": self.name,
            "shipboard_wastewater": bool(self.wastewater),
            "port_channels": list(self.port_channels),
            "respect_capability": bool(self.respect_capability),
            "description": self.description,
        }


DEFAULT_PHASES: tuple[SurveillancePhase, ...] = (
    SurveillancePhase(
        name=PHASE_CLINICAL_ONLY,
        wastewater=False,
        port_channels=(),
        description="clinical line list only; the baseline every gain is measured from",
    ),
    SurveillancePhase(
        name=PHASE_CLINICAL_WASTEWATER,
        wastewater=True,
        port_channels=(),
        description="adds the shipboard holding-tank channel to the likelihood",
    ),
    SurveillancePhase(
        name=PHASE_PORT_SYNDROMIC,
        wastewater=True,
        port_channels=(CHANNEL_SYNDROMIC,),
        description="port syndromic reporting as an external check on inferred hazards",
    ),
    SurveillancePhase(
        name=PHASE_PORT_WBE,
        wastewater=True,
        port_channels=(CHANNEL_WBE,),
        description="municipal wastewater concentration as the external check",
    ),
    SurveillancePhase(
        name=PHASE_PORT_LAB,
        wastewater=True,
        port_channels=(CHANNEL_LAB,),
        description="laboratory confirmations as the external check",
    ),
    SurveillancePhase(
        name=PHASE_PORT_GENOTYPING,
        wastewater=True,
        port_channels=(CHANNEL_GENOTYPING,),
        description="genotyping availability as the external check",
    ),
    SurveillancePhase(
        name=PHASE_FULL,
        wastewater=True,
        port_channels=CHANNELS,
        description="every channel retained, capability still respected",
    ),
)

PHASE_NAMES: tuple[str, ...] = tuple(p.name for p in DEFAULT_PHASES)


def phase_by_name(name: str) -> SurveillancePhase:
    """Look up a default phase, or say which names exist."""
    for phase in DEFAULT_PHASES:
        if phase.name == name:
            return phase
    raise ValueError(f"unknown phase {name!r}; known: {list(PHASE_NAMES)}")


def resolve_phases(
    names: Sequence[str] | None,
    *,
    respect_capability: bool = True,
) -> tuple[SurveillancePhase, ...]:
    """Phases to run, in the given order (``None`` runs the full staircase)."""
    chosen = DEFAULT_PHASES if not names else tuple(phase_by_name(n) for n in names)
    if respect_capability:
        return chosen
    return tuple(replace(p, respect_capability=False) for p in chosen)


def _ranks(values: Sequence[float]) -> list[float]:
    """Average ranks, so ties do not invent an ordering."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        stop = start + 1
        while stop < len(order) and values[order[stop]] == values[order[start]]:
            stop += 1
        shared = (start + stop - 1) / 2.0 + 1.0
        for idx in order[start:stop]:
            ranks[idx] = shared
        start = stop
    return ranks


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """``None`` when the sample is too small or a series has no spread."""
    n = len(xs)
    if n < MIN_CORRELATION_PORTS or n != len(ys):
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    denom = math.sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    if denom <= 0.0:
        return None
    return float(sum(a * b for a, b in zip(dx, dy)) / denom)


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Rank correlation: the hazard-to-signal link is monotone, not linear."""
    if len(xs) < MIN_CORRELATION_PORTS or len(xs) != len(ys):
        return None
    return pearson(_ranks(xs), _ranks(ys))


@dataclass(frozen=True)
class ChannelComparison:
    """Agreement between the inferred hazards and one port channel."""

    channel: str
    signal: str
    n_ports: int
    pearson_r: float | None
    spearman_rho: float | None
    excluded_ports: tuple[str, ...]

    def as_row(self, phase: str) -> dict[str, Any]:
        return {
            "phase": phase,
            "channel": self.channel,
            "signal": self.signal,
            "n_ports": self.n_ports,
            "pearson_r": self.pearson_r,
            "spearman_rho": self.spearman_rho,
            "excluded_ports": ";".join(self.excluded_ports),
        }


def _paired(
    hazard_mean: Mapping[str, float],
    table: Sequence[Mapping[str, Any]],
    signal: str,
) -> tuple[list[float], list[float], list[str]]:
    """Log10 hazards paired with a signal, plus the ports that dropped out."""
    xs: list[float] = []
    ys: list[float] = []
    excluded: list[str] = []
    for row in table:
        port_id = str(row.get("port_id") or "")
        hazard = hazard_mean.get(port_id)
        value = row.get(signal)
        if hazard is None or value is None:
            excluded.append(port_id)
            continue
        xs.append(math.log10(max(float(hazard), _HAZARD_FLOOR)))
        ys.append(float(value))
    return xs, ys, excluded


def compare_channel(
    hazard_mean: Mapping[str, float],
    table: Sequence[Mapping[str, Any]],
    channel: str,
) -> ChannelComparison:
    """Correlate inferred log10 λ_p against one channel's port summary."""
    signal = CHANNEL_SIGNALS[channel]
    xs, ys, excluded = _paired(hazard_mean, table, signal)
    return ChannelComparison(
        channel=channel,
        signal=signal,
        n_ports=len(xs),
        pearson_r=pearson(xs, ys),
        spearman_rho=spearman(xs, ys),
        excluded_ports=tuple(sorted(excluded)),
    )


def compare_phase(
    phase: SurveillancePhase,
    hazard_mean: Mapping[str, float],
    table: Sequence[Mapping[str, Any]],
) -> list[ChannelComparison]:
    """One comparison per channel this phase retained."""
    return [compare_channel(hazard_mean, table, c) for c in phase.port_channels]


def truth_comparison(
    hazard_mean: Mapping[str, float],
    table: Sequence[Mapping[str, Any]],
) -> ChannelComparison:
    """Inferred λ_p against the latent prevalence — never observable, always available.

    This is the recovery check the observable channels are then judged against:
    a phase whose channel correlation beats this ceiling is reading noise.
    """
    xs, ys, excluded = _paired(hazard_mean, table, "true_community_prevalence")
    return ChannelComparison(
        channel="truth",
        signal="true_community_prevalence",
        n_ports=len(xs),
        pearson_r=pearson(xs, ys),
        spearman_rho=spearman(xs, ys),
        excluded_ports=tuple(sorted(excluded)),
    )


def _hazard_mean(status: Mapping[str, Any]) -> dict[str, float]:
    summary = status.get("summary")
    if not isinstance(summary, dict):
        return {}
    hazards = summary.get("hazard_mean")
    if not isinstance(hazards, dict):
        return {}
    return {str(k): float(v) for k, v in hazards.items()}


def run_phase(
    phase: SurveillancePhase,
    *,
    manifest_path: str,
    ledger: Mapping[str, Any],
    out_dir: str,
    pathogen: str | None = None,
    engine: str = "auto",
    sampler: SamplerOptions | None = None,
    smoke: bool = False,
) -> dict[str, Any]:
    """Fit one phase and compare it against the port channels it kept.

    The fit receives the manifest and the wastewater switch only: no argument
    here can carry a port signal into the likelihood.
    """
    out = ensure_out_dir(out_dir)
    status = fit_sentinel_fleet(
        manifest_path,
        out,
        pathogen=pathogen,
        engine=engine,
        sampler=sampler,
        smoke=smoke,
        wastewater=phase.wastewater,
    )
    view = ablate_ledger(
        ledger,
        channels=phase.port_channels or (),
        respect_capability=phase.respect_capability,
    )
    table = port_signal_table(view)
    write_json(os.path.join(out, "port_analysis_view.json"), view)
    write_json(os.path.join(out, "port_signal_table.json"), table)
    hazards = _hazard_mean(status)
    comparisons = compare_phase(phase, hazards, table)
    payload = {
        **phase.to_metadata(),
        "fit_status": status.get("status"),
        "fit_reason": status.get("reason"),
        "engine": status.get("engine"),
        "n_ports_inferred": len(hazards),
        "ports_inferred": sorted(hazards),
        "ports_in_ledger": sorted(r["port_id"] for r in table),
        "truth": truth_comparison(hazards, table).as_row(phase.name),
        "comparisons": [c.as_row(phase.name) for c in comparisons],
    }
    write_json(os.path.join(out, "phase_summary.json"), payload)
    return payload


def run_multiphase(
    *,
    manifest_path: str,
    ledger_path: str,
    out_dir: str,
    phases: Sequence[SurveillancePhase] | None = None,
    pathogen: str | None = None,
    engine: str = "auto",
    sampler: SamplerOptions | None = None,
    smoke: bool = False,
) -> dict[str, Any]:
    """Run the staircase, one fit per phase, into ``out_dir/<phase>/``."""
    ledger = read_json(ledger_path)
    if not isinstance(ledger, dict):
        raise ValueError(f"port ledger must be an object: {ledger_path}")
    chosen = tuple(phases if phases is not None else DEFAULT_PHASES)
    out = ensure_out_dir(out_dir)
    rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for phase in chosen:
        summary = run_phase(
            phase,
            manifest_path=manifest_path,
            ledger=ledger,
            out_dir=os.path.join(out, phase.name),
            pathogen=pathogen,
            engine=engine,
            sampler=sampler,
            smoke=smoke,
        )
        summaries.append(summary)
        rows.append(summary["truth"])
        rows.extend(summary["comparisons"])
    payload = {
        "manifest": manifest_path,
        "ledger": ledger_path,
        "pathogen": ledger.get("pathogen"),
        "phases": summaries,
    }
    write_json(os.path.join(out, "multiphase_summary.json"), payload)
    write_csv(
        os.path.join(out, "multiphase_comparisons.csv"),
        rows,
        list(COMPARISON_COLUMNS),
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="fleet manifest of itinerary/observation pairs")
    parser.add_argument(
        "--ledger",
        required=True,
        help="port surveillance ledger written by port_ledger",
    )
    parser.add_argument("--out", default="sentinel_multiphase")
    parser.add_argument(
        "--phase",
        action="append",
        default=[],
        choices=PHASE_NAMES,
        help="run only these phases, in this order (default: all)",
    )
    parser.add_argument(
        "--pathogen",
        default=None,
        help="delay-catalog key; defaults to the catalog's default_pathogen",
    )
    parser.add_argument("--engine", choices=("auto", "stan", "numpy"), default="auto")
    parser.add_argument("--chains", type=int, default=4)
    parser.add_argument("--iter-sampling", type=int, default=1000)
    parser.add_argument("--iter-warmup", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--ignore-capability",
        action="store_true",
        help="keep a phase's channels even where the port runs no programme",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_multiphase(
        manifest_path=safe_path(args.manifest),
        ledger_path=safe_path(args.ledger),
        out_dir=safe_path(args.out),
        phases=resolve_phases(
            args.phase or None,
            respect_capability=not args.ignore_capability,
        ),
        pathogen=args.pathogen,
        engine=args.engine,
        sampler=SamplerOptions(
            chains=args.chains,
            iter_sampling=args.iter_sampling,
            iter_warmup=args.iter_warmup,
            seed=args.seed,
            show_progress=False,
        ),
        smoke=args.smoke,
    )
    # A staircase with a missing rung must not read as a successful comparison,
    # so the worst phase sets the exit code.
    codes: list[int] = []
    for phase in payload["phases"]:
        print(f"{phase['phase']}: {phase['fit_status']}", flush=True)
        codes.append(
            fit_exit_code(
                {
                    "status": phase["fit_status"],
                    "reason": phase.get("fit_reason"),
                },
            ),
        )
    return worst_exit_code(codes)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
