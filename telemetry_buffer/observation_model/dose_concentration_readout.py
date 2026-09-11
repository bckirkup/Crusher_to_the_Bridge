"""Where the exposure stream is patchy, and whether the model can respond to it.

Usage: dose_concentration_readout.py [epochs] [agents] [platform] [seed] [adj]
Findings: dose_concentration_findings.md

The model carries dispersion in several places (a persistent per-host shedding
multiplier, lognormal surface/hand transfer factors, an optional mean-one
within-zone exposure multiplier) and none of them has moved a readout. This
harness measures the two properties that decide whether any of that dispersion
can matter, on the realised exposure stream of one instrumented voyage:

1. **Curvature utilisation.** Establishment is ``1 - exp(-s D)`` on a
   persistent per-host beta-frailty ``s``. When ``s D << 1`` the map is linear,
   so a mean-preserving redistribution of dose across host-epochs leaves
   ``sum_i P_i`` unchanged to first order: dispersion is inert *by
   construction*, not by measurement. The readout reports
   ``sum(1 - exp(-s D)) / sum(s D)`` — 1.0 is the linear limit, and the deficit
   below 1.0 is the whole budget any variance mechanism has to work with.

2. **Concentration and coincidence.** The Lorenz top-share of dose over
   host-epochs, per route, says how patchy the delivered dose already is; the
   same statistic over (epoch, zone) cells says whether the patches are
   *shared* — one release reaching many hosts at once — or independent noise on
   separate hosts. Independent noise averages out in the linear limit;
   correlated exposure does not, because it puts the dose where a second host
   is standing.

Nothing here scores an anchor, and no constant is read off it: both statistics
are properties of the shipped model, measured so a proposed variance mechanism
can be predicted to do something before it is built.

The hook records the effective dose at the establishment draw, i.e. after route
efficiencies, protection and superinfection scaling, which is the dose the
dose-response actually sees.
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engines.transmission_core import TransmissionCore  # noqa: E402
from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    resolve_child_path,
    resolve_repo_path,
    validated_open,
)

TOP_SHARES = (0.001, 0.01, 0.1)

EXPOSURES: list[dict[str, object]] = []
_EPOCH = {"value": -1}

_original_execute = TransmissionCore.execute_transmission
_original_hazard = TransmissionCore._dose_response_hazard


def _instrumented_execute(self, epoch, *args, **kwargs):
    _EPOCH["value"] = int(epoch)
    return _original_execute(self, epoch, *args, **kwargs)


def _instrumented_hazard(self, agent, pathogen_id, effective_dose):
    hazard = _original_hazard(self, agent, pathogen_id, effective_dose)
    susceptibility = self._dose_response_susceptibility(agent, pathogen_id)
    EXPOSURES.append({
        "epoch": _EPOCH["value"],
        "agent_id": int(agent.agent_id),
        "agent_class": str(getattr(agent, "agent_class", "unknown")),
        "zone": str(agent.current_location),
        "pathogen_id": str(pathogen_id),
        "dose": float(effective_dose),
        "susceptibility": float(susceptibility),
        "hazard": float(hazard),
        "routes": {
            k: float(v)
            for k, v in self._effective_route_doses(
                agent.agent_id, pathogen_id, effective_dose,
            ).items()
        },
    })
    return hazard


def instrument() -> None:
    """Install the recording hooks.

    Called from ``main`` rather than at import, so that importing the analysis
    helpers (for tests, or from another harness) leaves ``TransmissionCore``
    untouched.
    """
    TransmissionCore.execute_transmission = _instrumented_execute
    TransmissionCore._dose_response_hazard = _instrumented_hazard


@dataclass
class Concentration:
    """Lorenz top-shares of a nonnegative quantity, plus its Gini."""

    count: int
    total: float
    top_shares: dict[float, float] = field(default_factory=dict)
    gini: float = float("nan")


def concentration(values: list[float]) -> Concentration:
    """Top-share and Gini of *values*, the patchiness of one dose stream."""
    positive = sorted((v for v in values if v > 0.0), reverse=True)
    total = sum(positive)
    out = Concentration(count=len(positive), total=total)
    if not positive or total <= 0.0:
        return out
    for q in TOP_SHARES:
        k = max(1, int(math.ceil(q * len(positive))))
        out.top_shares[q] = sum(positive[:k]) / total
    ascending = positive[::-1]
    n = len(ascending)
    weighted = sum((i + 1) * v for i, v in enumerate(ascending))
    out.gini = (2.0 * weighted) / (n * total) - (n + 1.0) / n
    return out


def curvature_utilisation(events: list[dict[str, object]]) -> dict[str, float]:
    """How much of the dose-response's nonlinearity the stream actually uses.

    ``sum(1 - exp(-sD)) / sum(sD)`` is 1.0 exactly in the linear limit. At 1.0
    a mean-preserving reallocation of dose across these host-epochs cannot
    change the expected number of establishments at all.
    """
    linear = sum(
        float(e["susceptibility"]) * float(e["dose"]) for e in events
    )
    realised = sum(float(e["hazard"]) for e in events)
    sd = [float(e["susceptibility"]) * float(e["dose"]) for e in events]
    sd_positive = sorted((v for v in sd if v > 0.0), reverse=True)
    return {
        "events": float(len(events)),
        "sum_sD": linear,
        "sum_hazard": realised,
        "utilisation": (realised / linear) if linear > 0.0 else float("nan"),
        "max_sD": sd_positive[0] if sd_positive else 0.0,
        "median_sD": (
            sd_positive[len(sd_positive) // 2] if sd_positive else 0.0
        ),
        "share_sD_above_1": (
            sum(1 for v in sd_positive if v >= 1.0) / len(sd_positive)
            if sd_positive else float("nan")
        ),
        # The band where the dose-response is neither wasted (sD >> 1, the
        # host is certain to be infected and the surplus dose does nothing)
        # nor arithmetically absent (sD << 1, the draw can never fire).
        "share_sD_informative": (
            sum(1 for v in sd_positive if 0.01 <= v <= 10.0) / len(sd_positive)
            if sd_positive else float("nan")
        ),
        "hazard_share_from_sD_above_1": (
            sum(-math.expm1(-v) for v in sd_positive if v >= 1.0) / realised
            if realised > 0.0 else float("nan")
        ),
    }


def route_streams(events: list[dict[str, object]]) -> dict[str, list[float]]:
    """Per-route dose, one entry per host-epoch that route reached."""
    streams: dict[str, list[float]] = defaultdict(list)
    for e in events:
        for route, dose in dict(e["routes"]).items():
            if float(dose) > 0.0:
                streams[route].append(float(dose))
    return dict(streams)


def route_sd_streams(
    events: list[dict[str, object]],
) -> dict[str, list[float]]:
    """Per-route ``sD``, the quantity the establishment draw is a function of."""
    streams: dict[str, list[float]] = defaultdict(list)
    for e in events:
        s = float(e["susceptibility"])
        for route, dose in dict(e["routes"]).items():
            if float(dose) > 0.0:
                streams[route].append(s * float(dose))
    return dict(streams)


def patchiness_cost(sd_values: list[float]) -> dict[str, float]:
    """What the realised allocation of ``sD`` costs against a flat one.

    ``sum(1 - exp(-sD_i))`` for the stream as delivered, against the same total
    spread evenly over the same host-epochs. Below 1.0 the concentration is
    destroying establishment probability by saturating a few hosts; at 1.0 the
    allocation is irrelevant because every draw is in the linear limit.
    """
    positive = [v for v in sd_values if v > 0.0]
    if not positive:
        return {}
    n = len(positive)
    total = sum(positive)
    realised = sum(-math.expm1(-v) for v in positive)
    flat = n * -math.expm1(-total / n)
    return {
        "n": float(n),
        "sum_sD": total,
        "realised_establishments": realised,
        "flat_establishments": flat,
        "realised_over_flat": (realised / flat) if flat > 0.0 else float("nan"),
        "utilisation": realised / total,
    }


def cell_streams(events: list[dict[str, object]]) -> tuple[
    dict[tuple[int, str], float], dict[tuple[int, str], int],
]:
    """Dose and exposed-host count per (epoch, zone) cell."""
    dose: dict[tuple[int, str], float] = defaultdict(float)
    hosts: dict[tuple[int, str], set[int]] = defaultdict(set)
    for e in events:
        key = (int(e["epoch"]), str(e["zone"]))
        dose[key] += float(e["dose"])
        hosts[key].add(int(e["agent_id"]))
    return dict(dose), {k: len(v) for k, v in hosts.items()}


def coincidence(events: list[dict[str, object]]) -> dict[str, float]:
    """Whether the heavy cells are shared by many hosts or carried by one.

    A patch that only ever reaches one host is indistinguishable from
    independent per-host noise; a patch several hosts share is the correlated
    exposure that survives the linear limit.
    """
    dose, hosts = cell_streams(events)
    if not dose:
        return {}
    ranked = sorted(dose.items(), key=lambda kv: -kv[1])
    k = max(1, int(math.ceil(0.01 * len(ranked))))
    top = ranked[:k]
    total = sum(dose.values())
    return {
        "cells": float(len(ranked)),
        "top1pct_dose_share": sum(v for _, v in top) / total,
        "top1pct_mean_hosts": sum(hosts[key] for key, _ in top) / len(top),
        "all_mean_hosts": sum(hosts.values()) / len(hosts),
        "single_host_cell_share": sum(
            1 for v in hosts.values() if v == 1
        ) / len(hosts),
    }


def build_run_spec(
    epochs: int, agents: int, platform: str, seed: int, adj: float | None,
) -> dict:
    """The Picard run spec the harness drives the instrumented voyage with."""
    overrides: dict[str, object] = {"ship_graph": {"num_agents": agents}}
    pathogen_overrides: dict[str, object] = {}
    if adj is not None:
        pathogen_overrides["norwalk_gi"] = {
            "environmental_faecal_release_log10_g_per_epoch": float(adj),
            "dose_adjustment": float(adj),
        }
    return {
        "pathogen_overrides": pathogen_overrides,
        "schema_version": "1.0.0",
        "description": "dose_concentration_readout",
        "catalog": {
            "platform_id": platform,
            "pathogen_bundle_id": "active_profiles",
        },
        "run": {
            "random_seed": seed,
            "num_epochs": epochs,
            "write_ground_truth": False,
            "history_retention": "compact",
        },
        "legacy_yaml": "crusher_labs/config.yaml",
        "actors": [],
        "incentives": {},
        "config_overrides": overrides,
    }


def _concentration_lines(label: str, conc: Concentration) -> list[str]:
    """One report row for a dose stream's concentration."""
    shares = "  ".join(
        f"top{q:g}={conc.top_shares.get(q, float('nan')):.3f}"
        for q in TOP_SHARES
    )
    return [
        f"{label:24} n={conc.count:7d} total={conc.total:12.4g} "
        f"gini={conc.gini:6.3f}  {shares}",
    ]


def report(events: list[dict[str, object]], pathogen_id: str) -> list[str]:
    """The full readout for one pathogen's exposure stream."""
    subset = [e for e in events if str(e["pathogen_id"]) == pathogen_id]
    lines = [f"\n=== {pathogen_id}: {len(subset)} dose-response draws ==="]
    if not subset:
        return lines
    curv = curvature_utilisation(subset)
    lines.append(
        "curvature: sum(1-exp(-sD))/sum(sD) = "
        f"{curv['utilisation']:.6f}  (1.0 = linear, dispersion inert)",
    )
    lines.append(
        f"  sD: median={curv['median_sD']:.4g} max={curv['max_sD']:.4g} "
        f"share>=1: {curv['share_sD_above_1']:.4f} "
        f"share in [0.01, 10]: {curv['share_sD_informative']:.4f} "
        f"hazard from sD>=1: {curv['hazard_share_from_sD_above_1']:.4f}",
    )
    lines.append("\nconcentration of effective dose:")
    lines.extend(_concentration_lines(
        "all host-epochs", concentration([float(e["dose"]) for e in subset]),
    ))
    for route, stream in sorted(
        route_streams(subset).items(), key=lambda kv: -sum(kv[1]),
    ):
        lines.extend(_concentration_lines(f"  route {route}", concentration(stream)))
    lines.append(
        "\nwhat the allocation costs (sD as delivered vs spread flat over the "
        "same host-epochs):",
    )
    for route, stream in sorted(
        route_sd_streams(subset).items(), key=lambda kv: -sum(kv[1]),
    ):
        cost = patchiness_cost(stream)
        lines.append(
            f"  route {route:18} n={cost['n']:7.0f} sum sD={cost['sum_sD']:11.4g} "
            f"establishments: as delivered={cost['realised_establishments']:9.3f} "
            f"flat={cost['flat_establishments']:9.3f} "
            f"ratio={cost['realised_over_flat']:7.4f} "
            f"utilisation={cost['utilisation']:.6f}",
        )
    dose_cells, _ = cell_streams(subset)
    lines.extend(_concentration_lines(
        "(epoch, zone) cells", concentration(list(dose_cells.values())),
    ))
    coin = coincidence(subset)
    if coin:
        lines.append("\ncoincidence (is a patch shared?):")
        lines.append(
            f"  cells={coin['cells']:.0f} "
            f"top1% dose share={coin['top1pct_dose_share']:.3f} "
            f"hosts/cell: top1%={coin['top1pct_mean_hosts']:.2f} "
            f"all={coin['all_mean_hosts']:.2f} "
            f"single-host cells={coin['single_host_cell_share']:.3f}",
        )
    return lines


def report_saved(path: str) -> int:
    """Re-report a saved exposure stream without re-running the voyage."""
    root = str(Path(path).resolve().parent)
    with validated_open(
        path, allowed_roots=(root,), encoding="utf-8",
    ) as handle:
        events = json.load(handle)
    print(f"{len(events)} saved dose-response draws from {path}")
    for pathogen_id in sorted({str(e["pathogen_id"]) for e in events}):
        for line in report(events, pathogen_id):
            print(line)
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1].endswith(".json"):
        return report_saved(sys.argv[1])
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 168
    agents = int(sys.argv[2]) if len(sys.argv) > 2 else 450
    platform = sys.argv[3] if len(sys.argv) > 3 else "expedition_cruise_450"
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 500
    adj = float(sys.argv[5]) if len(sys.argv) > 5 else None
    instrument()
    spec = build_run_spec(epochs, agents, platform, seed, adj)
    with tempfile.TemporaryDirectory() as tmp:
        path = resolve_repo_path(tmp, "run_spec.json")
        with validated_open(
            path, "w", allowed_roots=(tmp,), encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(spec))
        picard = PicardRunSpec.from_picard_json(str(ROOT), str(path))
        ShipSimulation(picard, display=False).run()

    print(
        f"epochs={epochs} agents={agents} platform={platform} "
        f"seed={seed} adj={adj}",
    )
    for pathogen_id in sorted({str(e["pathogen_id"]) for e in EXPOSURES}):
        for line in report(EXPOSURES, pathogen_id):
            print(line)

    temp_root = tempfile.mkdtemp(prefix="dose_concentration_")
    out = resolve_child_path(
        temp_root, f"exposures_{platform}_s{seed}.json",
    )
    with validated_open(
        out, "w", allowed_roots=(temp_root,), encoding="utf-8",
    ) as handle:
        handle.write(json.dumps(EXPOSURES))
    print(f"\n{len(EXPOSURES)} dose-response draws written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
