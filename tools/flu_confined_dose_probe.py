#!/usr/bin/env python3
"""FLU-DOSE-01: delivered-dose distribution to confined cabinmates, flu arm.

Companion readout to ``tools/cabin_floor_probe.py``: same isolated voyage,
same declared SOP-017 confinement, same paired seeds 8105/8106, but the
report is the *dose* each confined mate absorbed — cumulative copies summed
over the confined window per pair member and channel — against the
exponential-model saturation threshold. The audit's unit-mismatch claim
(docs/literature/non_scored_arms_audit.md §2) predicts confined mates sit
far above ~26 copies, where k = 0.18/copy makes infection ~99% regardless
of route apportionment. This probe measures that prediction.

A readout only: no constant, profile, or engine change. The per-slot dose
is the ledger's own ``channel_dose`` sum; ``implied_sar`` is the hazard the
engine drew against (susceptibility x dose), so the median implied SAR is
what the model assigned, not what the literature floor wants.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from simulation_utils import asset_defaults  # noqa: E402
from tools.diag.conditioned_cell import EDISON  # noqa: E402

ACTIVE = asset_defaults.DEFAULT_PATHOGEN_BUNDLE_ID

# Exponential k sits on the profile; the 99%-saturation dose is read off the
# bundle being measured (k = 6e-4/copy -> ~7,676 copies).
def _saturation_99(profile: dict[str, Any]) -> float:
    return -math.log(0.01) / float(profile["dose_response"]["k"])


def _pair_first_epochs(
    members: tuple[int, ...],
    agents: dict[int, Any],
) -> dict[int, int]:
    """First influenza_a infection epoch for each infected member."""
    out = {}
    for m in members:
        agent = agents.get(m)
        if agent is None or "influenza_a" not in agent.infections:
            continue
        inf = agent.infections["influenza_a"]
        out[m] = inf.get("first_infection_epoch", inf["infection_epoch"])
    return out


def _slot_member_ids(
    members: tuple[int, ...],
    agents: dict[int, Any],
    confined_first: dict[tuple[int, ...], int],
) -> set[int]:
    """Ledger ``_confined_window_counts`` slots, resolved to member ids.

    The cabin needs an index (earliest infected member) and a recorded
    confinement start; a member is a slot when it was uninfected at the
    pair's first confined epoch.
    """
    first_epochs = _pair_first_epochs(members, agents)
    first_confined = confined_first.get(members)
    if not first_epochs or first_confined is None:
        return set()
    index = min(first_epochs, key=first_epochs.get)
    return {
        m for m in members
        if m != index
        and (m not in first_epochs or first_epochs[m] >= first_confined)
    }


def _confined_row_doses(
    rows: list[dict[str, Any]],
    sim: Any,
    confined_first: dict[tuple[int, ...], int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """(all confined dose rows, rows for confined-slot targets, slot count).

    A slot row is the ledger's own ``_confined_window_counts`` definition
    resolved to the member level: the cabin has an index (earliest infected
    member), the pair was confined (``confined_first`` set), and this
    target was uninfected when confinement started. That is exactly the
    conditioning the sourced floors describe.
    """
    agents = {a.agent_id: a for a in sim.engine.agents}
    slot_targets: set[tuple[int, ...]] = set()  # (members..., target)
    for members in {tuple(r["cabin_members"]) for r in rows}:
        for m in _slot_member_ids(members, agents, confined_first):
            slot_targets.add(members + (m,))

    out_all = []
    out_slots = []
    for row in rows:
        if row["confined_epochs"] <= 0:
            continue
        rec = {
            "dose_copies": sum(row["channel_dose"].values()),
            "implied_sar": row["implied_sar"],
            "infected": row["infected"],
            "channels": row["channel_dose"],
        }
        out_all.append(rec)
        if tuple(row["cabin_members"]) + (row["target_id"],) in slot_targets:
            out_slots.append(rec)
    # Slots with zero dose leave no ledger row at all; they are still real
    # measurements of the confined-mate dose distribution.
    return out_all, out_slots, len(slot_targets)


def _quantiles(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {}
    vals = sorted(vals)
    def q(p: float) -> float:
        i = min(len(vals) - 1, max(0, int(round(p * (len(vals) - 1)))))
        return vals[i]
    return {"p10": q(0.1), "p25": q(0.25), "median": q(0.5),
            "p75": q(0.75), "p90": q(0.9), "max": vals[-1]}


def run_dose_arm(*, bundle: str, seed: int, platform: str, epochs: int,
                 confinement: str) -> dict[str, Any]:
    # run_arm returns only aggregates; recompute row-level dose via its own
    # machinery so the measurement is identical to CABIN-FLOOR-02's.
    import json as _json  # noqa: PLC0415
    import tempfile as _tempfile  # noqa: PLC0415

    from picard_framework.pathogen_overrides import (  # noqa: PLC0415
        isolate_arm_overrides,
        load_pathogen_bundle,
    )
    from picard_framework.run_spec import PicardRunSpec  # noqa: PLC0415
    from picard_framework.simulation.ship_simulation import (  # noqa: PLC0415
        ShipSimulation,
    )
    from simulation_utils.paths import (
        resolve_repo_path,  # noqa: PLC0415
        validated_open,  # noqa: PLC0415
    )
    from simulation_utils.platform_complement import (  # noqa: PLC0415
        declared_total,
    )
    from tools.covid_route_attribution import (  # noqa: PLC0415
        CabinPairChallengeLedger,
        cabin_pair_challenge_table,
    )
    from tools.noro_diag.per_host_dose_challenge import (  # noqa: PLC0415
        build_spec,
    )

    profiles = load_pathogen_bundle(
        resolve_repo_path(
            str(REPO_ROOT), asset_defaults.pathogen_bundle_rel(bundle),
        ),
    )
    profile = profiles["influenza_a"]
    spec_dict = build_spec(
        seed=seed, platform=platform, bundle=bundle,
        epochs=epochs, num_agents=declared_total(platform),
        pathogen_id="influenza_a", alpha=None, beta=0.0,
        high_touch_area_scale=None, high_touch_area_scale_by_zone_class=None,
        fomite_representation=None, fomite_touch_share=None,
        fomite_touch_share_table=None,
    )
    spec_dict["pathogen_overrides"] = isolate_arm_overrides(
        bundle, "influenza_a", {"influenza_a": {"initial_infected": None}},
    )
    party = (profile.get("boarding") or {}).get("party") or {}
    spec_dict["config_overrides"]["initiation"] = {
        "explicit_seeds": [{
            "pathogen": "influenza_a",
            "count": int(party.get("size") or 0) or 2,
            "role": "passenger",
            "epoch": 0,
        }],
    }
    if confinement == "declared":
        spec_dict["config_overrides"]["scenario_schedule"] = {
            "protocols": [{
                "protocol_id": "SOP-017", "start_day": 1, "end_day": None,
            }],
        }
    # instrumented_voyage's body, inlined so the ledger's confined_first
    # (not exposed through the table) stays reachable for slot resolution.
    with _tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        spec_path = Path(tmp) / "run_spec.json"
        with validated_open(
            spec_path, "w", allowed_roots=(tmp,), encoding="utf-8",
        ) as handle:
            handle.write(_json.dumps(spec_dict))
        picard_spec = PicardRunSpec.from_picard_json(
            str(REPO_ROOT), str(spec_path),
        )
        sim = ShipSimulation(picard_spec, display=False)
        ledger = CabinPairChallengeLedger()
        sim.epoch_observer = ledger.observe
        sim.run()
    table = cabin_pair_challenge_table(ledger, sim)
    confined, index_mates, slots_total = _confined_row_doses(
        table["rows"], sim, ledger.confined_first,
    )

    sat99 = _saturation_99(profile)

    def block(
        rows: list[dict[str, Any]], total: int | None = None,
    ) -> dict[str, Any]:
        doses = [r["dose_copies"] for r in rows]
        denom = total or len(doses)
        doses_padded = doses + [0.0] * max(0, denom - len(doses))
        sars = [r["implied_sar"] for r in rows]
        channel_totals: dict[str, float] = {}
        for r in rows:
            for c, d in r["channels"].items():
                channel_totals[c] = channel_totals.get(c, 0.0) + d
        return {
            "n_rows_with_dose": len(rows),
            "n_total": denom,
            "dose_quantiles_copies": _quantiles(doses_padded),
            "implied_sar_quantiles": _quantiles(sars),
            "share_above_99pct_saturation": (
                sum(d > sat99 for d in doses) / denom
                if denom else None
            ),
            "channel_dose_totals": channel_totals,
        }

    return {
        "bundle": bundle,
        "seed": seed,
        "platform": platform,
        "confinement": confinement,
        "all_confined": block(confined),
        "index_mates": block(index_mates, slots_total),
        "confined_secondaries": table["confined_secondaries"],
        "confined_slots": table["confined_slots"],
        "observed_mate_case_attack_confined": (
            table["observed_mate_case_attack_confined"]
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", default="classic_cruise_1900")
    parser.add_argument("--epochs", type=int, default=288)
    parser.add_argument("--seeds", type=int, nargs="+", default=[8105, 8106])
    parser.add_argument(
        "--confinement", choices=("organic", "declared"), default="declared",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    results = [
        run_dose_arm(
            bundle=bundle, seed=seed, platform=args.platform,
            epochs=args.epochs, confinement=args.confinement,
        )
        for bundle in (ACTIVE, EDISON)
        for seed in args.seeds
    ]
    out = args.out.resolve()
    if not out.is_relative_to(REPO_ROOT):
        out = REPO_ROOT / out.name
    out.write_text(__import__("json").dumps(results, indent=1))
    for row in results:
        med = row["index_mates"]["dose_quantiles_copies"].get("median")
        print(
            f"{row['bundle']} seed {row['seed']}: "
            f"slots={row['index_mates']['n_total']} median_dose={med} "
            f"obs={row['observed_mate_case_attack_confined']}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
