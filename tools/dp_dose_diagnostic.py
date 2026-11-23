#!/usr/bin/env python3
"""DP-REPLAY-DOSE-DIAG-01 — Checkpoint B index-only exposure diagnostic.

From THETA_AFTER_BEHAVIOR §Checkpoint B: four prespecified, non-outcome-
selected movement seeds on the dedicated hull under the accepted replay
behavior; the first 120 hours with one imported source, normalized
shedding and transport, susceptibility-weighted recipient doses, and
**secondary transmission disabled**. The index echoes its location,
status and shedding every epoch; recipients accumulate dose by route,
setting and role without converting.

Secondary transmission is disabled by pinning
``dose_response.susceptibility_scale`` to 1e-30: infection hazards are
~0 while the engine's dose accounting (``cumulative_exposure``,
``cumulative_exposure_by_route``, ``dose_response_susceptibility``)
still records everything a real challenge would. The scale-mapping
ratio is not attempted: there is no old-movement-kernel arm on the
dedicated hull, so per the protocol the bracket decision defers to
Checkpoint C with the labelled historical reference.

Under the implemented Θ convention the cell's ``susceptibility_scale``
is ``theta * (alpha + beta) / alpha``, so a labelled theta multiplies
``dose * draw * age_band * (alpha + beta) / alpha``. The normalized
U·D a reader compares against a labelled θ is therefore
``dose * susceptibility * (alpha + beta) / alpha`` — reported as
``normalized_ud`` alongside ``weighted_dose`` (which carries the host
factor alone).

Readout only — nothing here is scored against an epidemiological anchor.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    PATHOGEN_ID,
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
)
from tools.dp_replay_acceptance import (  # noqa: E402
    MovementLedger,
    build_sim,
    load_zone_meta,
    resolve_arg_paths,
    run_epochs,
    write_json,
)

_SUSPENDED_SCALE = 1e-30
_DEFAULT_SEEDS = (20200205, 20200206, 20200207, 20200208)
_DEFAULT_EPOCHS = 120


def _quantiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    import numpy as np
    q = np.quantile(np.asarray(values, dtype=float), [0.5, 0.9, 0.99])
    return {"p50": float(q[0]), "p90": float(q[1]), "p99": float(q[2])}


def _suspend_secondary_transmission(raw: dict) -> None:
    """Pin the cell's susceptibility scale near zero: hazards ~0 while
    dose accounting still runs — index-only exposure, no conversions."""
    overrides = raw.setdefault("pathogen_overrides", {})
    dr = overrides.setdefault(PATHOGEN_ID, {}).setdefault("dose_response", {})
    if "susceptibility_scale" not in dr:
        raise SystemExit(
            "no dose_response.susceptibility_scale to pin — "
            "the cell's theta arm did not resolve"
        )
    dr["susceptibility_scale"] = _SUSPENDED_SCALE


def _theta_scale_ratio(overrides: dict) -> float:
    """(alpha + beta) / alpha on the resolved dose_response — the factor
    the engine folds into susceptibility_scale = theta * ratio."""
    dr = overrides.get(PATHOGEN_ID, {}).get("dose_response", {})
    alpha = dr.get("alpha")
    beta = dr.get("beta")
    if not alpha or not beta:
        raise SystemExit(
            "no dose_response alpha/beta to normalize U·D against"
        )
    return (float(alpha) + float(beta)) / float(alpha)


class DoseLedger:
    """Epoch observer: per-setting dose deltas + index source echo."""

    def __init__(
        self,
        zone_meta: dict[str, str],
        home_zones: dict[int, str],
        seed_ids: set[int],
    ) -> None:
        self._classifier = MovementLedger(zone_meta, home_zones)
        self.seed_ids = seed_ids
        self._source_agents: dict[int, object] = {}
        self._prev_exposure: dict[int, float] = {}
        self.dose_epochs: dict[int, int] = {}
        self.dose_by_setting: dict[str, float] = {}
        self.dose_by_role: dict[str, float] = {}
        self.source_trace: list[dict] = []

    def observe(self, sim: object, work: object) -> None:
        engine = sim.engine
        profiles = getattr(sim, "pathogen_profiles", None) or getattr(
            engine, "pathogen_profiles", {}
        )
        profile = profiles.get(PATHOGEN_ID, {})
        epoch = int(getattr(sim, "epoch", getattr(engine, "epoch", 0)))
        if not self._source_agents:
            self._source_agents = {
                int(a.agent_id): a
                for a in engine.agents
                if int(a.agent_id) in self.seed_ids
            }
        for agent in engine.agents:
            aid = int(agent.agent_id)
            if aid in self.seed_ids:
                continue
            now = float(
                getattr(agent, "cumulative_exposure", {}).get(PATHOGEN_ID, 0.0)
            )
            delta = now - self._prev_exposure.get(aid, 0.0)
            self._prev_exposure[aid] = now
            if delta > 0.0:
                self.dose_epochs[aid] = self.dose_epochs.get(aid, 0) + 1
                loc = str(getattr(agent, "current_location", ""))
                setting = self._classifier.classify(loc, agent)
                self.dose_by_setting[setting] = (
                    self.dose_by_setting.get(setting, 0.0) + delta
                )
                role = str(getattr(agent, "role", "crew"))
                self.dose_by_role[role] = (
                    self.dose_by_role.get(role, 0.0) + delta
                )
        for aid in sorted(self.seed_ids):
            agent = self._source_agents.get(aid)
            if agent is None:
                continue
            self.source_trace.append({
                "epoch": epoch,
                "agent_id": aid,
                "location": str(getattr(agent, "current_location", "")),
                "infection_status": str(
                    getattr(agent, "infection_status", "")
                ),
                "illness_status": str(getattr(agent, "illness_status", "")),
                "current_shedding": float(
                    getattr(agent, "current_shedding", 0.0)
                ),
                "pathogen_shedding": float(
                    agent.get_pathogen_shedding(PATHOGEN_ID, profile)
                ),
                "ashore": bool(getattr(agent, "ashore", False)),
            })


def _run_seed(
    design, cell, args, zone_meta: dict[str, str],
) -> dict:
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=args.num_epochs, repo_root=str(_REPO_ROOT),
    )
    theta_scale_ratio = _theta_scale_ratio(raw.get("pathogen_overrides", {}))
    _suspend_secondary_transmission(raw)
    sim = build_sim(raw)
    engine = sim.engine
    seed_ids = set(getattr(engine, "explicit_seed_agent_ids", []) or [])
    if not seed_ids:
        raise SystemExit(
            f"seed {cell.seed}: no explicit seed agents were initiated"
        )
    home_zones = {
        int(a.agent_id): str(getattr(a, "home_zone", "") or "")
        for a in engine.agents
    }
    ledger = DoseLedger(zone_meta, home_zones, seed_ids)
    sim.epoch_observer = ledger.observe
    run_epochs(sim)

    recipients: list[dict] = []
    route_totals: dict[str, float] = {}
    for agent in engine.agents:
        aid = int(agent.agent_id)
        if aid in seed_ids:
            continue
        dose = float(
            getattr(agent, "cumulative_exposure", {}).get(PATHOGEN_ID, 0.0)
        )
        if dose <= 0.0:
            continue
        # dose_response_susceptibility stores draw * scale * age_band;
        # the normalized convention wants the host factor alone, so the
        # pinned scale divides out.
        susceptibility = float(
            getattr(agent, "dose_response_susceptibility", {}).get(
                PATHOGEN_ID, 0.0,
            )
        ) / _SUSPENDED_SCALE
        by_route = getattr(agent, "cumulative_exposure_by_route", {}).get(
            PATHOGEN_ID, {},
        )
        for route, rd in by_route.items():
            route_totals[route] = route_totals.get(route, 0.0) + float(rd)
        recipients.append({
            "agent_id": aid,
            "role": str(getattr(agent, "role", "crew")),
            "dose": dose,
            "weighted_dose": dose * susceptibility,
            "normalized_ud": dose * susceptibility * theta_scale_ratio,
            "susceptibility": susceptibility,
            "dose_epochs": ledger.dose_epochs.get(aid, 0),
        })

    role_counts: dict[str, int] = {}
    for r in recipients:
        role_counts[r["role"]] = role_counts.get(r["role"], 0) + 1
    doses = [r["dose"] for r in recipients]
    weighted = [r["weighted_dose"] for r in recipients]
    eligible = sum(
        1 for a in engine.agents if int(a.agent_id) not in seed_ids
    )
    return {
        "seed": int(cell.seed),
        "theta_cell": float(getattr(cell, "theta", 0.0)),
        "susceptibility_scale": _SUSPENDED_SCALE,
        "epochs": int(sim.num_epochs),
        "source_trace": ledger.source_trace,
        "recipients": len(recipients),
        "eligible_agents": eligible,
        "recipient_zero_fraction": (
            round(1.0 - len(recipients) / eligible, 4) if eligible else None
        ),
        "dose_total": sum(doses),
        "dose_quantiles": _quantiles(doses),
        "weighted_dose_mean": (
            sum(weighted) / len(weighted) if weighted else 0.0
        ),
        "weighted_dose_quantiles": _quantiles(weighted),
        "normalized_ud_quantiles": _quantiles(
            [r["normalized_ud"] for r in recipients]
        ),
        "normalized_ud_mean": (
            sum(r["normalized_ud"] for r in recipients) / len(recipients)
            if recipients
            else 0.0
        ),
        "theta_scale_ratio": theta_scale_ratio,
        "dose_epoch_quantiles": _quantiles(
            [float(r["dose_epochs"]) for r in recipients]
        ),
        "dose_by_route": dict(sorted(route_totals.items())),
        "dose_by_role": dict(sorted(ledger.dose_by_role.items())),
        "dose_by_setting": dict(sorted(ledger.dose_by_setting.items())),
        "recipient_role_counts": dict(sorted(role_counts.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--design",
        default="picard_framework/runs/covid_dp_replay_01_design.json",
    )
    parser.add_argument("--arm", default="replay_niid")
    parser.add_argument(
        "--seeds", type=int, nargs="*", default=list(_DEFAULT_SEEDS),
        help="prespecified movement seeds (default: the first four)",
    )
    parser.add_argument(
        "--num-epochs", type=int, default=_DEFAULT_EPOCHS,
        help="observation horizon (default 120h per Checkpoint B)",
    )
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    design_path, out_path = resolve_arg_paths(args)
    design = load_design(str(design_path))
    cells = {
        int(c.seed): c
        for c in enumerate_cells(design)
        if c.arm_id == args.arm
    }
    missing = [s for s in args.seeds if s not in cells]
    if missing:
        raise SystemExit(f"seeds not in arm {args.arm}: {missing}")

    # Zone classes need the platform layout; the arm declares it in the
    # spec overrides, so resolve it the same way as any cell.
    probe = prepare_cell_run_spec(
        design, cells[args.seeds[0]], num_epochs=1,
        repo_root=str(_REPO_ROOT),
    )
    zone_meta = load_zone_meta(probe)

    runs = [
        _run_seed(design, cells[s], args, zone_meta)
        for s in args.seeds
    ]
    readout = {
        "design": args.design,
        "arm": args.arm,
        "seeds": list(args.seeds),
        "runs": runs,
    }
    text = json.dumps(readout, indent=1, sort_keys=True)
    write_json(out_path, text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
