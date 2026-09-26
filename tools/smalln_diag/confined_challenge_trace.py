#!/usr/bin/env python3
"""SMALLN-01: per-challenge trace behind a CABIN-FLOOR-02 cell.

The CABIN-FLOOR-02 arms report the ``CabinPairChallengeLedger`` channel
dose, which is the *emission-side* compartment dose: it is tallied off
``ContactTracingMatrix`` before ``route_efficiency_multipliers``, host
protection or the NPI layer touch it, so ``lambda_confined_median`` in
that ledger is an upper bound on the hazard the engine actually drew
against. This probe reads the drawn quantity instead: it wraps
``TransmissionCore._resolve_pathogen_challenge`` and records, for every
(agent, epoch) challenge the arm ever resolved, the pre-protection dose,
the protection, the post-efficiency pathway split, the host's persistent
``dose_response_susceptibility`` and the per-epoch hazard.

That gives the two hard rules of
``.agents/skills/transmission-blocker-cascade`` directly: the challenge
count is the mechanism-fired witness (Hard rule 1) and the hazard sum is
the summed naive hazard, i.e. the expected infection count from delivered
dose (Hard rule 2, Step 0).

The arm shape — isolated bundle, explicit passenger seeds, declared
SOP-017 confinement, paired seeds 8105/8106 — is
``tools/cabin_floor_probe.run_arm`` unchanged; nothing here edits a
profile or a constant. The wrapper reads the host susceptibility only
*after* the engine resolved the challenge, so no draw is pulled forward
and the RNG stream is the campaign's.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.transmission_core import TransmissionCore  # noqa: E402
from simulation_utils.paths import validated_open  # noqa: E402
from tools import cabin_floor_probe  # noqa: E402

EDISON = "edison_10pathogen_profiles"


class ChallengeRecorder:
    """Per-agent aggregates over every resolved challenge for one pathogen."""

    def __init__(self, pathogen_id: str) -> None:
        self.pathogen_id = pathogen_id
        self.challenges = 0
        self.blocked_by_protection = 0
        self.by_agent: dict[int, dict[str, Any]] = {}
        self.pathway_dose: dict[str, float] = defaultdict(float)
        self.trace: list[dict[str, Any]] = []

    def _slot(self, agent_id: int) -> dict[str, Any]:
        return self.by_agent.setdefault(agent_id, {
            "challenges": 0,
            "p_dose": 0.0,
            "effective_dose": 0.0,
            "sum_hazard": 0.0,
            "max_protection": 0.0,
            "susceptibility": None,
            "pathway_dose": defaultdict(float),
            "infected_epoch": None,
        })

    def record(
        self,
        *,
        epoch: int,
        agent: Any,
        p_dose: float,
        protection: float,
        pathways: dict[str, float],
        became_infected: bool,
    ) -> None:
        """Book one resolved challenge; susceptibility is read post-hoc."""
        slot = self._slot(int(agent.agent_id))
        susceptibility = agent.dose_response_susceptibility.get(self.pathogen_id)
        effective = p_dose * (1.0 - protection)
        hazard = (
            -math.expm1(-float(susceptibility) * effective)
            if susceptibility is not None else 0.0
        )
        self.challenges += 1
        if protection >= 1.0:
            self.blocked_by_protection += 1
        slot["challenges"] += 1
        slot["p_dose"] += p_dose
        slot["effective_dose"] += effective
        slot["sum_hazard"] += hazard
        slot["max_protection"] = max(slot["max_protection"], protection)
        slot["susceptibility"] = susceptibility
        for name, dose in pathways.items():
            slot["pathway_dose"][name] += dose
            self.pathway_dose[name] += dose
        if became_infected:
            slot["infected_epoch"] = epoch
        if len(self.trace) < 40:
            self.trace.append({
                "epoch": epoch,
                "agent_id": int(agent.agent_id),
                "location": agent.current_location,
                "p_dose": p_dose,
                "protection": protection,
                "effective_dose": effective,
                "susceptibility": susceptibility,
                "hazard": hazard,
                "pathway_dose": dict(pathways),
                "infected": became_infected,
            })


def _install_recorder(recorder: ChallengeRecorder) -> Any:
    """Wrap the challenge resolver; returns the original for restoration."""
    original = TransmissionCore._resolve_pathogen_challenge
    pid_under_test = recorder.pathogen_id

    def wrapper(
        self: Any,
        epoch: int,
        agent: Any,
        pathogen_id: str,
        agent_pathogen_doses: dict[int, dict[str, float]],
        agent_pathway_doses: dict[int, dict[str, float]],
        matrix: Any,
        events: list[Any],
    ) -> None:
        p_dose = agent_pathogen_doses.get(agent.agent_id, {}).get(pathogen_id, 0.0)
        watched = pathogen_id == pid_under_test and p_dose > 0.0
        protection = (
            self._challenge_protection(agent, pathogen_id, epoch)
            if watched else 0.0
        )
        pathways = (
            {
                name: dose
                for name, dose in agent_pathway_doses.get(
                    agent.agent_id, {},
                ).items()
                if name.endswith(f":{pathogen_id}")
            } if watched else {}
        )
        was_infected = pathogen_id in agent.infections
        original(
            self, epoch, agent, pathogen_id, agent_pathogen_doses,
            agent_pathway_doses, matrix, events,
        )
        if watched:
            recorder.record(
                epoch=epoch, agent=agent, p_dose=p_dose, protection=protection,
                pathways=pathways,
                became_infected=(
                    not was_infected and pathogen_id in agent.infections
                ),
            )

    TransmissionCore._resolve_pathogen_challenge = wrapper
    return original


def _index_agent_ids(sim: Any, pathogen_id: str) -> set[int]:
    """The arm's planted index cases (explicit epoch-0 passenger seeds)."""
    seeded = getattr(sim.engine, "explicit_seed_agent_ids", None) or ()
    return {int(aid) for aid in seeded}


def _infection_epoch(agent: Any, pathogen_id: str) -> int | None:
    infection = agent.infections.get(pathogen_id)
    if not isinstance(infection, dict):
        return None
    return infection.get(
        "first_infection_epoch", infection.get("infection_epoch"),
    )


def _agent_rows(
    recorder: ChallengeRecorder,
    agent_ids: set[int],
    infection_epochs: dict[int, int | None],
) -> list[dict[str, Any]]:
    rows = []
    for agent_id in sorted(agent_ids):
        slot = recorder.by_agent.get(agent_id)
        if slot is None:
            continue
        rows.append({
            "agent_id": agent_id,
            "challenges": slot["challenges"],
            "p_dose": slot["p_dose"],
            "effective_dose": slot["effective_dose"],
            "sum_hazard": slot["sum_hazard"],
            "max_protection": slot["max_protection"],
            "susceptibility": slot["susceptibility"],
            "pathway_dose": dict(slot["pathway_dose"]),
            "infected_epoch": slot["infected_epoch"],
            "infection_epoch_state": infection_epochs.get(agent_id),
        })
    return rows


def run_cell(
    *,
    pathogen_id: str,
    seed: int,
    bundle: str,
    platform: str,
    epochs: int,
) -> dict[str, Any]:
    """One instrumented arm; returns the CABIN-FLOOR summary plus the trace."""
    recorder = ChallengeRecorder(pathogen_id)
    captured: dict[str, Any] = {}
    voyage = cabin_floor_probe.instrumented_voyage

    def capture(spec_dict: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        sim, table = voyage(spec_dict)
        captured["sim"] = sim
        captured["table"] = table
        return sim, table

    original = _install_recorder(recorder)
    cabin_floor_probe.instrumented_voyage = capture
    try:
        summary = cabin_floor_probe.run_arm(
            bundle=bundle, pathogen_id=pathogen_id, seed=seed,
            platform=platform, epochs=epochs, confinement="declared",
        )
    finally:
        cabin_floor_probe.instrumented_voyage = voyage
        TransmissionCore._resolve_pathogen_challenge = original

    sim = captured["sim"]
    table = captured["table"]
    indexes = _index_agent_ids(sim, pathogen_id)
    confined_targets = {
        int(row["target_id"]) for row in table["rows"]
        if row["confined_epochs"] > 0
    }
    non_index_confined = confined_targets - indexes
    challenged = set(recorder.by_agent)
    infection_epochs = {
        int(agent.agent_id): _infection_epoch(agent, pathogen_id)
        for agent in sim.engine.agents
    }
    infected_ids = {
        aid for aid, ep in infection_epochs.items() if ep is not None
    }
    confined_pairs = {
        tuple(row["cabin_members"]) for row in table["rows"]
        if row["confined_epochs"] > 0
    }
    pairs_with_case = {
        members for members in confined_pairs
        if infected_ids & set(members)
    }
    summary["challenge_diagnostics"] = {
        "confined_pairs_with_channel_dose": len(confined_pairs),
        "confined_pairs_holding_a_case": len(pairs_with_case),
        "challenges_total": recorder.challenges,
        "challenged_agents": len(challenged),
        "challenges_blocked_by_protection": recorder.blocked_by_protection,
        "sum_naive_hazard_all_agents": sum(
            slot["sum_hazard"] for slot in recorder.by_agent.values()
        ),
        "sum_naive_hazard_confined_non_index": sum(
            recorder.by_agent[a]["sum_hazard"]
            for a in non_index_confined & challenged
        ),
        "sum_naive_hazard_confined_never_infected": sum(
            recorder.by_agent[a]["sum_hazard"]
            for a in (non_index_confined - infected_ids) & challenged
        ),
        "effective_dose_total": sum(
            slot["effective_dose"] for slot in recorder.by_agent.values()
        ),
        "pathway_dose_total_post_efficiency": dict(recorder.pathway_dose),
        "index_agents": sorted(indexes),
        "infected_agents": len(infected_ids),
        "confined_cabin_targets": len(confined_targets),
        "confined_non_index_targets": len(non_index_confined),
        "confined_non_index_challenged": len(non_index_confined & challenged),
        "confined_non_index_rows": _agent_rows(
            recorder, non_index_confined, infection_epochs,
        ),
        "index_rows": _agent_rows(recorder, indexes, infection_epochs),
        "first_challenges": recorder.trace,
    }
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pathogen-id", required=True)
    parser.add_argument("--bundle", default=EDISON)
    parser.add_argument("--platform", default="classic_cruise_1900")
    parser.add_argument("--epochs", type=int, default=288)
    parser.add_argument("--seeds", type=int, nargs="+", default=[8105, 8106])
    parser.add_argument("--out", default="smalln_challenge_trace.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    results = [
        run_cell(
            pathogen_id=args.pathogen_id, seed=seed, bundle=args.bundle,
            platform=args.platform, epochs=args.epochs,
        )
        for seed in args.seeds
    ]
    for row in results:
        diag = row["challenge_diagnostics"]
        print(
            f"{row['pathogen_id']} seed={row['seed']} "
            f"confined {row['confined_secondaries']}/{row['confined_slots']} "
            f"challenges={diag['challenges_total']} "
            f"expected_all={diag['sum_naive_hazard_all_agents']:.4g} "
            f"expected_confined_non_index="
            f"{diag['sum_naive_hazard_confined_non_index']:.4g}",
        )
        print(f"  pathway dose: {diag['pathway_dose_total_post_efficiency']}")
    out_path = (REPO_ROOT / args.out).resolve()
    with validated_open(
        out_path, "w", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        handle.write(json.dumps(results, indent=1, default=str))
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
