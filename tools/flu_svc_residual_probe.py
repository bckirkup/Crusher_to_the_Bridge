#!/usr/bin/env python3
"""FLU-SVC-RESIDUAL-01: attribute the residual passenger/droplet surplus
at service ``contact_factor=0`` on the exp ``r200_dec`` seeds
8112/8184/8120.

CAREGIVER-SVC-01's paired probe (docs/ledger/CAREGIVER-SVC-01.md) showed
the R3 service bridge collapsing under any nonzero discount, but left an
open second channel: with the factor at 0 the surplus persists at
+23/+40/+9 onboard-acquired infections vs the r100 baseline. The
standing candidate is confined cabin-mate pooling — CONFIRMED cases are
confined into the cabin they already share, so a susceptible mate is
pooled in a small compartment with a shedder across the confinement
boundary.

Design (paired-attribution locality rule: both arms on THIS checkout,
never Batch-vs-local):

- Arm A: ``r200_dec`` + ``transmission.caregiver.service.contact_factor = 0``
  (hot reporting, service dose dead).
- Arm B: ``r100_dec`` + ``contact_factor = 0`` (shipped reporting, service
  dose dead) — the contrast isolates every confinement-mediated channel
  that is not the steward bridge.
- Seeds: 8112, 8184, 8120 — the three cells where the f=0 surplus
  persisted.
- Platform ``expedition_cruise_450``, 288 epochs, ``confinement="organic"``
  — the VIS-01 cell shape, via ``conditioned_spec`` + that campaign's
  ``_observation_patch``.

Per-agent extraction: infection record (``first_infection_epoch``,
``episode_epochs``, ``acquired_particles_by_route``), quarantine admit /
release intervals replayed from ``state.compliance_log``, cabin cliques
from ``cabin_mate_ids``, role. The surplus is decomposed as agents
onboard-infected in arm A but never onboard-infected in arm B (and the
mirror set), each classified:

- ``co_confined_pooling``: target confined at first onboard epoch AND a
  cabin-clique mate infected earlier AND that mate confined at that
  epoch — locked in the shared cabin with a shedder.
- ``cross_boundary_mate``: target free at infection, but a clique mate
  infected earlier AND was confined by then — the confined shedder's
  cabin addback reaches the still-mobile mate.
- ``free_pair``: cabin mate infected earlier, neither side confined at
  the epoch — cabin-mate link without a confinement gate.
- ``confined_no_mate``: target confined, no earlier-infected clique mate.
- ``crew``: target is crew.
- ``free_no_mate``: none of the above — the free-pool residue.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engines.natural_history import host_age_band  # noqa: E402
from picard_framework.simulation.ship_simulation import (  # noqa: E402
    ShipSimulation,
)
from tools.diag.conditioned_cell import ACTIVE, conditioned_spec  # noqa: E402
from tools.diag.instrument_common import (  # noqa: E402
    materialized_picard_spec,
)

_PATHOGEN = "influenza_a"
_PLATFORM = "expedition_cruise_450"
_EPOCHS = 288
_SEEDS = (8112, 8184, 8120)
_ARMS = {
    "r200_f0": {"report_scale": 2.0, "contact_factor": 0},
    "r100_f0": {"report_scale": 1.0, "contact_factor": 0},
}

# Actions that add an agent to ``state.quarantined_ids``; see
# ``orchestrator_epoch`` admission paths. ``delayed_compliance`` admits
# immediately when no escort delay is configured — signalled by the
# absence of ``escort_order`` actions — and is otherwise pending until
# ``escorted_admission``.
_ADMIT_ACTIONS = {
    "escorted_admission",
    "immediate_compliance",
    "general_confinement",
    "cascade_confinement",
    "vsp_quarantine",
    "self_isolation",
    "enforced_confinement",
}
_DELAYED_ADMIT = "delayed_compliance"
_PENDING_ACTIONS = {"escort_order"}
_RELEASE_ACTIONS = {"crew_age_duty_exclusion_release"}


def _load_vis_cell():
    """Import the VIS-01 cell module by path (campaigns are not a package)."""
    cell_path = (
        _REPO_ROOT / "campaigns" / "flu" / "visibility_01" / "cell.py"
    )
    spec = importlib.util.spec_from_file_location(
        "flu_vis01_cell", cell_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _confinement_intervals(
    compliance_log: list[dict[str, Any]],
) -> dict[int, list[tuple[int, int | None]]]:
    """Replay the compliance log into per-agent confined intervals.

    ``escort_order`` queues an admission; ``delayed_compliance`` admits
    directly unless the run uses an escort delay (any ``escort_order`` in
    the log), in which case it is also pending. Release actions close the
    open interval.
    """
    uses_escort = any(
        e.get("action") in _PENDING_ACTIONS for e in compliance_log
    )
    intervals: dict[int, list[list[int | None]]] = {}
    confined: set[int] = set()
    pending: set[int] = set()
    for entry in compliance_log:
        aid = entry.get("agent_id")
        epoch = entry.get("epoch")
        action = entry.get("action")
        if aid is None or epoch is None:
            continue
        if action in _PENDING_ACTIONS:
            pending.add(aid)
            continue
        if action == _DELAYED_ADMIT and uses_escort:
            pending.add(aid)
            continue
        if action in _ADMIT_ACTIONS or action == _DELAYED_ADMIT:
            if aid in confined:
                pending.discard(aid)
                continue
            confined.add(aid)
            pending.discard(aid)
            intervals.setdefault(aid, []).append([epoch, None])
            continue
        if action in _RELEASE_ACTIONS and aid in confined:
            confined.discard(aid)
            open_iv = intervals.get(aid)
            if open_iv and open_iv[-1][1] is None:
                open_iv[-1][1] = epoch
    return {aid: [tuple(iv) for iv in ivs] for aid, ivs in intervals.items()}


def _confined_at(
    intervals: dict[int, list[tuple[int, int | None]]],
    aid: int,
    epoch: int,
) -> bool:
    """Whether *aid*'s replayed intervals cover *epoch*."""
    return any(
        start <= epoch and (end is None or epoch < end)
        for start, end in intervals.get(aid, ())
    )


def _first_onboard_epoch(inf: dict[str, Any]) -> int | None:
    """Earliest episode epoch > 0 (onboard acquisition), or None."""
    onboard = [e for e in (inf.get("episode_epochs") or []) if e and e > 0]
    return min(onboard) if onboard else None


def _agent_rows(
    agents: list[Any],
    pathogen_id: str,
    state: Any,
) -> dict[int, dict[str, Any]]:
    """Per-agent infection + clique + role record for one cell."""
    ever_ill = set(getattr(state, "ever_ill_ids", set()) or set())
    ever_reported = set(getattr(state, "ever_reported_ids", set()) or set())
    rows: dict[int, dict[str, Any]] = {}
    for ag in agents:
        mates = set(getattr(ag, "cabin_mate_ids", None) or ())
        clique = min({ag.agent_id} | mates)
        row: dict[str, Any] = {
            "id": ag.agent_id,
            "role": getattr(ag, "role", "") or "",
            "agent_class": getattr(ag, "agent_class", "") or "",
            "band": host_age_band(ag) or "unbanded",
            "clique": clique,
            "clique_size": len(mates) + 1,
            "ever_ill": ag.agent_id in ever_ill,
            "ever_reported": ag.agent_id in ever_reported,
        }
        inf = ag.infections.get(pathogen_id)
        if inf is not None:
            routes = dict(inf.get("acquired_particles_by_route") or {})
            row.update(
                {
                    "first_infection_epoch": inf.get("first_infection_epoch"),
                    "infection_epoch": inf.get("infection_epoch"),
                    "episode": inf.get("episode"),
                    "episode_epochs": list(inf.get("episode_epochs") or []),
                    "first_onboard_epoch": _first_onboard_epoch(inf),
                    "routes": routes,
                    "dominant_route": (
                        max(routes, key=routes.get) if routes else None
                    ),
                    "shedding_multiplier": inf.get("shedding_multiplier"),
                }
            )
        rows[ag.agent_id] = row
    return rows


def run_cell(seed: int, arm: str) -> dict[str, Any]:
    """Run one (seed, arm) cell and return the extraction payload."""
    cell = _load_vis_cell()
    arm_cfg = _ARMS[arm]
    spec_dict, profile = conditioned_spec(
        bundle=ACTIVE,
        pathogen_id=_PATHOGEN,
        seed=seed,
        platform=_PLATFORM,
        epochs=_EPOCHS,
        confinement="organic",
    )
    patch = cell._observation_patch(
        profile, arm_cfg["report_scale"], "declared",
    )
    spec_dict["pathogen_overrides"].setdefault(_PATHOGEN, {})[
        "observation_model"
    ] = patch
    spec_dict["config_overrides"].setdefault("transmission", {})[
        "caregiver"
    ] = {"service": {"contact_factor": arm_cfg["contact_factor"]}}
    with materialized_picard_spec(spec_dict, _REPO_ROOT) as picard_spec:
        sim = ShipSimulation(picard_spec, display=False)
        sim.run()
    state = sim.state
    compliance_log = [
        dict(e) for e in (getattr(state, "compliance_log", None) or [])
    ]
    intervals = _confinement_intervals(compliance_log)
    return {
        "seed": seed,
        "arm": arm,
        "agents": _agent_rows(sim.engine.agents, _PATHOGEN, state),
        "compliance_log": compliance_log,
        "quarantined_end": sorted(
            getattr(state, "quarantined_ids", set()) or set()
        ),
        "isolated_end": sorted(
            getattr(state, "isolated_ids", set()) or set()
        ),
        "confinement_intervals": {
            str(k): v for k, v in intervals.items()
        },
        "caregiver_telemetry": dict(
            getattr(sim.tx_core, "caregiver_telemetry", {}) or {}
        ),
    }


def _classify_surplus(
    arm_a: dict[str, Any],
    arm_b: dict[str, Any],
) -> dict[str, Any]:
    """Decompose arm A's onboard-infected set against arm B's."""
    rows_a = arm_a["agents"]
    rows_b = arm_b["agents"]
    onboard_a = {
        aid for aid, r in rows_a.items() if r.get("first_onboard_epoch")
    }
    onboard_b = {
        aid for aid, r in rows_b.items() if r.get("first_onboard_epoch")
    }
    iv_a = {
        int(k): v for k, v in arm_a["confinement_intervals"].items()
    }
    first_inf = {
        aid: r.get("first_infection_epoch")
        for aid, r in rows_a.items()
        if r.get("first_infection_epoch") is not None
    }

    def _admit_epoch(aid: int) -> int | None:
        ivs = iv_a.get(aid)
        return ivs[0][0] if ivs else None

    def _row(aid: int) -> dict[str, Any]:
        rec = rows_a[aid]
        epoch = rec["first_onboard_epoch"]
        target_confined = _confined_at(iv_a, aid, epoch)
        clique_mates = sorted(
            m for m, mrec in rows_a.items()
            if mrec["clique"] == rec["clique"] and m != aid
        )
        earlier = [
            m for m in clique_mates
            if first_inf.get(m) is not None and first_inf[m] < epoch
        ]
        mate_confined = [
            m for m in earlier if _confined_at(iv_a, m, epoch)
        ]
        if rec["role"] == "crew":
            channel = "crew"
        elif target_confined and mate_confined:
            channel = "co_confined_pooling"
        elif target_confined and earlier:
            channel = "confined_target_free_mate"
        elif not target_confined and mate_confined:
            channel = "cross_boundary_mate"
        elif not target_confined and earlier:
            channel = "free_pair"
        elif target_confined:
            channel = "confined_no_mate"
        else:
            channel = "free_no_mate"
        return {
            "id": aid,
            "role": rec["role"],
            "band": rec["band"],
            "clique": rec["clique"],
            "clique_size": rec["clique_size"],
            "epoch": epoch,
            "admit_epoch": _admit_epoch(aid),
            "episodes": rec.get("episode"),
            "dominant_route": rec.get("dominant_route"),
            "routes": rec.get("routes"),
            "confined_at_infection": target_confined,
            "earlier_mates": [
                {
                    "id": m,
                    "first_infection_epoch": first_inf[m],
                    "imported": first_inf[m] == 0,
                    "confined_at_epoch": m in mate_confined,
                    "admit_epoch": _admit_epoch(m),
                }
                for m in earlier
            ],
            "mates_confined_at_epoch": mate_confined,
            "channel": channel,
        }

    return {
        "onboard_a": sorted(onboard_a),
        "onboard_b": sorted(onboard_b),
        "a_only": [_row(aid) for aid in sorted(onboard_a - onboard_b)],
        "b_only_ids": sorted(onboard_b - onboard_a),
        "n_a": len(onboard_a),
        "n_b": len(onboard_b),
    }


def _summarize(
    results: dict[tuple[int, str], dict[str, Any]],
) -> dict[str, Any]:
    """Per-seed decomposition + pooled channel tally."""
    per_seed: dict[str, Any] = {}
    pooled: dict[str, int] = {}
    for seed in _SEEDS:
        pair = _classify_surplus(
            results[(seed, "r200_f0")], results[(seed, "r100_f0")],
        )
        channels: dict[str, int] = {}
        for row in pair["a_only"]:
            channels[row["channel"]] = channels.get(row["channel"], 0) + 1
        for name, n in channels.items():
            pooled[name] = pooled.get(name, 0) + n
        per_seed[str(seed)] = {
            **{k: pair[k] for k in ("n_a", "n_b", "b_only_ids")},
            "surplus": pair["n_a"] - pair["n_b"],
            "a_only_n": len(pair["a_only"]),
            "channels": channels,
            "a_only": pair["a_only"],
            "quarantined_end_a": len(
                results[(seed, "r200_f0")]["quarantined_end"]
            ),
            "quarantined_end_b": len(
                results[(seed, "r100_f0")]["quarantined_end"]
            ),
        }
    return {"seeds": per_seed, "pooled_channels": pooled}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="*", type=int, default=list(_SEEDS))
    parser.add_argument("--out", required=True)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args(argv)

    jobs = [
        (seed, arm) for seed in args.seeds for arm in _ARMS
    ]
    results: dict[tuple[int, str], dict[str, Any]] = {}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(run_cell, seed, arm) for seed, arm in jobs
        ]
        for future in futures:
            cell = future.result()
            results[(cell["seed"], cell["arm"])] = cell
            print(
                f"DONE seed={cell['seed']} arm={cell['arm']} "
                f"onboard={sum(1 for r in cell['agents'].values() if r.get('first_onboard_epoch'))} "
                f"quar_end={len(cell['quarantined_end'])}",
                flush=True,
            )
    summary = _summarize(results)
    out = {
        "schema": "flu_svc_residual_01.v1",
        "seeds": list(args.seeds),
        "arms": _ARMS,
        "platform": _PLATFORM,
        "epochs": _EPOCHS,
        "pathogen_id": _PATHOGEN,
        "summary": summary,
        "cells": {
            f"{seed}:{arm}": results[(seed, arm)]
            for seed in args.seeds for arm in _ARMS
        },
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"WROTE {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
