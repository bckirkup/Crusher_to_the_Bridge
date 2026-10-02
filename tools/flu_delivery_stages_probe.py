#!/usr/bin/env python3
"""FLU-DELIVERY-01: stage-resolved emitted→delivered dose for confined flu mates.

Companion to ``tools/flu_confined_dose_probe.py``: same isolated voyage,
same paired seeds and declared SOP-017 confinement — but where that probe
reports only the delivered copies per confined-mate slot, this one
decomposes the delivery chain that produces them:

    emitted copies
      → confinement emission factor (shedder-side withholding)
      → branch split (droplet emission_fraction / airborne deposit fraction)
      → room-air partition (far share to pool / near share to plume)
      → HVAC deposit → survival ageing → CONTAM transport → cabin partition
      → room concentration → breathing uptake (V_inh) → vent × residence
      → target-side factors (confinement × cabin presence) + mate addback
      → delivered dose → protection → effective dose → hazard

Every stage's attenuation factor is *measured* off the engine's own
intermediate quantities, never inferred: the wrappers read the unit state
the pathway just built, the deposit delta the accumulator just wrote, the
per-block partition maps the transport step just returned, and the dose
records the matrix just appended. No wrapped call draws RNG itself and no
RNG-drawing helper is invoked a second time — the RNG stream and the
baseline arm are identical to ``tools/flu_confined_dose_probe.py``'s run.

A readout only: it fits nothing and moves no constant.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import orchestrator_epoch as _orch  # noqa: E402
import picard_framework.simulation.ship_simulation as _ship  # noqa: E402
from engines.infection_dynamics_bridge import (  # noqa: E402
    KorkinShipEngine,
)
from engines.transmission_core import TransmissionCore  # noqa: E402
from simulation_utils import asset_defaults  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    resolve_repo_path,
    validated_open,
)
from tools.covid_route_attribution import (  # noqa: E402
    CabinPairChallengeLedger,
    cabin_compartment_key,
    cabin_pair_challenge_table,
)
from tools.flu_confined_dose_probe import (  # noqa: E402
    _slot_member_ids,
)
from tools.smalln_diag.confined_challenge_trace import (  # noqa: E402
    ChallengeRecorder,
    _install_recorder,
)

ACTIVE = asset_defaults.DEFAULT_PATHOGEN_BUNDLE_ID
PATHOGEN = "influenza_a"


class StageRecorder:
    """Pure-observation wrappers over one run's confined delivery chain."""

    def __init__(self, pathogen_id: str) -> None:
        self.pathogen_id = pathogen_id
        self.epoch = -1
        self.unit_rows: list[dict[str, Any]] = []
        self.target_rows: list[dict[str, Any]] = []
        self.hvac_rows: list[dict[str, Any]] = []
        self.deposits_pending: list[dict[str, Any]] = []
        self.deposits: list[dict[str, Any]] = []
        self.transport_pending: list[dict[str, Any]] = []
        self.transport_rows: list[dict[str, Any]] = []
        self.challenge = ChallengeRecorder(pathogen_id)
        self._restore: list[tuple[Any, str, Any]] = []

    # ── per-stage wrappers ──────────────────────────────────────────

    def _wrap_deposit(self, original: Any) -> Any:
        def wrapper(agent: Any, pid: str, prof: dict, masses: dict,
                    dep_frac: float, confinement_core: Any) -> None:
            if pid != self.pathogen_id:
                return original(
                    agent, pid, prof, masses, dep_frac, confinement_core,
                )
            loc = agent.current_location
            sv = agent.get_pathogen_shedding(pid, prof)
            ef = (
                confinement_core.confinement_emission_factor(agent)
                if confinement_core is not None else 1.0
            )
            key = (
                confinement_core.airborne_deposit_key(agent, loc)
                if confinement_core is not None else loc
            )
            before = masses.get(key, 0.0)
            original(agent, pid, prof, masses, dep_frac, confinement_core)
            self.deposits_pending.append({
                "agent_id": int(agent.agent_id),
                "location": loc,
                "deposit_key": key,
                "shedding_copies": sv,
                "deposited_copies": masses.get(key, 0.0) - before,
                "skipped": sv > 0.0 and loc not in masses,
                "confinement_emission_factor": ef,
                "deposit_fraction": dep_frac,
            })
        return wrapper

    def _wrap_droplet_unit(self, original: Any) -> Any:
        def wrapper(core: Any, epoch: int, unit_name: str, shedders: list,
                    susceptible: list, agent_doses: dict, matrix: Any,
                    agent_pathway_doses: Any, pathogen_id: str,
                    ledger: Any, **unit_kwargs: Any) -> None:
            if (pathogen_id == self.pathogen_id
                    and core._is_cabin_compartment(unit_name)):
                zone = core.compartment_parent(unit_name)
                emitted = [
                    sv * core.confinement_emission_factor(s)
                    for s, sv in shedders
                ]
                partition = (
                    core.droplet_field_split.active
                    and unit_kwargs["near_field_on"]
                )
                pool_share = (
                    core.droplet_field_split.far_field_share
                    if partition else 1.0
                )
                aerosol = (
                    sum(emitted) * unit_kwargs["emission_fraction"]
                )
                volume = core._air_unit_volume(unit_name)
                self.unit_rows.append({
                    "epoch": epoch,
                    "unit": unit_name,
                    "zone": zone,
                    "shedder_ids": [int(s.agent_id) for s, _ in shedders],
                    "emitted_raw": sum(sv for _, sv in shedders),
                    "emitted_post_confinement": sum(emitted),
                    "aerosol_total": aerosol,
                    "aerosol_pool": aerosol * pool_share,
                    "aerosol_plume": aerosol * (1.0 - pool_share),
                    "volume_m3": volume,
                    "concentration": aerosol * pool_share / max(volume, 1.0),
                    "vent_factor": core._aerosol_ventilation_factor(zone),
                    "residence": core._room_air_residence_factor(unit_name),
                    "emission_fraction": unit_kwargs["emission_fraction"],
                    "pool_share": pool_share,
                    "n_susceptible": len(susceptible),
                })
            return original(
                core, epoch, unit_name, shedders, susceptible, agent_doses,
                matrix, agent_pathway_doses, pathogen_id, ledger,
                **unit_kwargs,
            )
        return wrapper

    def _wrap_droplet_target(self, original: Any) -> Any:
        def wrapper(core: Any, st: Any, target: Any) -> tuple:
            dose, near, pool, addback = original(core, st, target)
            if (st.pathogen_id == self.pathogen_id and st.in_compartment):
                tf = core._confinement_factor(target)
                presence = core._cabin_presence_share(target, st.epoch)
                addback = core._cabin_mate_droplet_addback(
                    target, st.shedders, st.volume, st.vent_factor, tf,
                    st.emission_fraction * st.pool_share, st.epoch,
                    st.residence,
                )
                self.target_rows.append({
                    "epoch": st.epoch,
                    "unit": st.unit_name,
                    "target_id": int(target.agent_id),
                    "dose_total": dose,
                    "plume_dose": near,
                    "addback_dose": addback,
                    "pool_dose": dose - near - addback,
                    "inhaled_pre_target": (
                        st.concentration
                        * core.inhaled_air_volume_m3_per_epoch
                    ),
                    "target_factor": tf,
                    "presence_share": presence,
                    "concentration": st.concentration,
                    "inhaled_volume_m3": core.inhaled_air_volume_m3_per_epoch,
                    "vent_factor": st.vent_factor,
                    "residence": st.residence,
                })
            return dose, near, pool, addback
        return wrapper

    def _wrap_hvac(self, original: Any) -> Any:
        def wrapper(core: Any, target_zone: str, source_zones: list,
                    shedder_ids: list, mass_in_target: float, occupants: list,
                    agent_doses: dict, matrix: Any, agent_pathway_doses: Any,
                    pathogen_id: str, source_attribution: Any = None,
                    **kwargs: Any) -> None:
            air_unit = kwargs.get("air_unit")
            epoch = int(kwargs.get("epoch", 0))
            watched = (
                pathogen_id == self.pathogen_id and air_unit is not None
            )
            n_before = len(matrix.hvac_downstream_exposures) if watched else 0
            original(
                core, target_zone, source_zones, shedder_ids, mass_in_target,
                occupants, agent_doses, matrix, agent_pathway_doses,
                pathogen_id, source_attribution=source_attribution,
                **kwargs,
            )
            if watched:
                self.hvac_rows.append({
                    "epoch": int(epoch),
                    "air_unit": air_unit,
                    "target_zone": target_zone,
                    "mass_in_target": mass_in_target,
                    "source_zones": sorted(source_zones),
                    "target_doses": [
                        {
                            "target_id": int(r["target_id"]),
                            "dose": float(r.get("dose") or 0.0),
                        }
                        for r in matrix.hvac_downstream_exposures[n_before:]
                    ],
                })
        return wrapper

    def _wrap_transmission(self, original: Any) -> Any:
        def wrapper(core: Any, epoch: int, agents: list,
                    zone_pathogen_mass: dict, **kwargs: Any) -> Any:
            self.epoch = int(epoch)
            if self.deposits_pending:
                for dep in self.deposits_pending:
                    dep["epoch"] = self.epoch
                self.deposits.extend(self.deposits_pending)
                self.deposits_pending = []
            return original(
                core, epoch, agents, zone_pathogen_mass, **kwargs,
            )
        return wrapper

    def _wrap_partition(self, original: Any) -> Any:
        def wrapper(pre: dict, post: dict, shares_by_block: dict,
                    outflow_rate_by_block: dict, dt: float) -> dict:
            new = original(
                pre, post, shares_by_block, outflow_rate_by_block, dt,
            )
            for block, shares in shares_by_block.items():
                if not shares or block not in post:
                    continue
                self.transport_pending.append({
                    "epoch": self.epoch,
                    "block": block,
                    "mass_in_pre_block": sum(
                        pre.get(k, 0.0) for k in shares
                    ),
                    "mass_post_block": float(post[block]),
                    "outflow_rate_per_h": float(
                        outflow_rate_by_block.get(block, 0.0)
                    ),
                    "compartment_mass": {
                        k: float(new.get(k, 0.0)) for k in shares
                    },
                    "compartment_mass_pre": {
                        k: float(pre.get(k, 0.0)) for k in shares
                    },
                })
            return new
        return wrapper

    def _wrap_set_mass(self, original: Any) -> Any:
        def wrapper(engine: Any, pathogen_id: str, masses: dict) -> None:
            for row in self.transport_pending:
                row["pathogen_id"] = pathogen_id
            self.transport_rows.extend(self.transport_pending)
            self.transport_pending = []
            return original(engine, pathogen_id, masses)
        return wrapper

    # ── install / restore ───────────────────────────────────────────

    def _patch(self, owner: Any, name: str, wrapper_fn: Any) -> None:
        original = getattr(owner, name)
        self._restore.append((owner, name, original))
        setattr(owner, name, wrapper_fn(original))

    def install(self) -> None:
        self._patch(
            _orch, "_deposit_agent_emission", self._wrap_deposit,
        )
        self._patch(
            TransmissionCore, "_droplet_unit_doses", self._wrap_droplet_unit,
        )
        self._patch(
            TransmissionCore, "_droplet_target_dose",
            self._wrap_droplet_target,
        )
        self._patch(
            TransmissionCore, "_apply_hvac_downstream_doses", self._wrap_hvac,
        )
        self._patch(
            TransmissionCore, "execute_transmission", self._wrap_transmission,
        )
        self._patch(_ship, "partition_block_air", self._wrap_partition)
        self._patch(
            KorkinShipEngine, "set_pathogen_zone_mass",
            self._wrap_set_mass,
        )
        self._restore.append((
            TransmissionCore, "_resolve_pathogen_challenge",
            _install_recorder(self.challenge),
        ))

    def restore(self) -> None:
        for owner, name, original in reversed(self._restore):
            setattr(owner, name, original)
        self._restore = []


def _in_window(row: dict[str, Any], window: tuple[int, int]) -> bool:
    return window[0] <= row["epoch"] <= window[1]


def _slot_stage_rows(
    members: tuple[int, ...], target: int, cabin_key: str,
    window: tuple[int, int], rec: StageRecorder, agents: dict[int, Any],
) -> dict[str, Any]:
    """Stage-resolved sums for one confined-mate slot over its window."""
    member_set = set(members)
    units = [
        u for u in rec.unit_rows
        if u["unit"] == cabin_key and _in_window(u, window)
    ]
    targets = [
        t for t in rec.target_rows
        if t["unit"] == cabin_key and t["target_id"] == target
        and _in_window(t, window)
    ]
    hvac = [
        h for h in rec.hvac_rows
        if h["air_unit"] == cabin_key and _in_window(h, window)
    ]
    deps = [
        d for d in rec.deposits
        if d["deposit_key"] == cabin_key and _in_window(d, window)
    ]
    # Member emission is attributed from the deposit channel's per-agent
    # shedding (per-agent raw sv), not the unit row's pooled sum.
    emitted_member = sum(
        d["shedding_copies"] for d in deps if d["agent_id"] in member_set
    )
    hvac_dose = sum(
        t["dose"] for h in hvac for t in h["target_doses"]
        if t["target_id"] == target
    )
    ch = rec.challenge.by_agent.get(target, {})
    infected = bool(
        agents.get(target) is not None
        and PATHOGEN in getattr(agents[target], "infections", {})
    )
    return {
        "members": list(members),
        "target_id": target,
        "cabin_key": cabin_key,
        "infected": infected,
        "confined_window": list(window),
        "n_unit_rows": len(units),
        "emitted_member_copies": emitted_member,
        "emitted_raw_total": sum(u["emitted_raw"] for u in units),
        "emitted_post_confinement": sum(
            u["emitted_post_confinement"] for u in units
        ),
        "aerosol_pool_copies": sum(u["aerosol_pool"] for u in units),
        "aerosol_plume_copies": sum(u["aerosol_plume"] for u in units),
        "hvac_deposited_copies": sum(
            d["deposited_copies"] for d in deps
            if d["agent_id"] in member_set
        ),
        "hvac_mass_delivered": sum(h["mass_in_target"] for h in hvac),
        "hvac_dose_copies": hvac_dose,
        "pool_dose_copies": sum(t["pool_dose"] for t in targets),
        "addback_dose_copies": sum(t["addback_dose"] for t in targets),
        "plume_dose_copies": sum(t["plume_dose"] for t in targets),
        "droplet_dose_copies": sum(t["dose_total"] for t in targets),
        "inhaled_pool_pre_target": sum(
            t["inhaled_pre_target"] for t in targets
        ),
        "delivered_p_dose": float(ch.get("p_dose", 0.0)),
        "effective_dose": float(ch.get("effective_dose", 0.0)),
        "sum_hazard": float(ch.get("sum_hazard", 0.0)),
        "susceptibility": ch.get("susceptibility"),
        "max_protection": float(ch.get("max_protection", 0.0)),
        "challenge_count": int(ch.get("challenges", 0)),
        "pathway_dose": dict(ch.get("pathway_dose", {})),
    }


def _cell_report(
    ledger: CabinPairChallengeLedger, rec: StageRecorder, sim: Any,
    meta: dict[str, Any],
) -> dict[str, Any]:
    table = cabin_pair_challenge_table(ledger, sim)
    agents = {a.agent_id: a for a in sim.engine.agents}
    rows = table["rows"]
    confined = [r for r in rows if r["confined_epochs"] > 0]
    member_sets = {tuple(r["cabin_members"]) for r in confined}
    slots = []
    for members in member_sets:
        window = (
            ledger.confined_first[members],
            ledger.confined_last.get(members, 10**9),
        )
        for target in _slot_member_ids(members, agents, ledger.confined_first):
            key = cabin_compartment_key(agents.get(target)) or ""
            slots.append(_slot_stage_rows(
                members, target, key, window, rec, agents,
            ))
    totals = defaultdict(float)
    for s in slots:
        for field in (
            "emitted_member_copies", "emitted_raw_total",
            "emitted_post_confinement", "aerosol_pool_copies",
            "aerosol_plume_copies", "hvac_deposited_copies",
            "hvac_mass_delivered", "hvac_dose_copies", "pool_dose_copies",
            "addback_dose_copies", "plume_dose_copies",
            "droplet_dose_copies", "inhaled_pool_pre_target",
            "delivered_p_dose", "effective_dose", "sum_hazard",
        ):
            totals[field] += s[field]
    delivered = (
        totals["pool_dose_copies"] + totals["addback_dose_copies"]
        + totals["plume_dose_copies"] + totals["hvac_dose_copies"]
    )
    return {
        **meta,
        "n_slots": len(slots),
        "stage_totals": dict(totals),
        "delivered_dose_copies": delivered,
        "capture_ratio_delivered_per_emitted": (
            delivered / totals["emitted_member_copies"]
            if totals["emitted_member_copies"] > 0 else None
        ),
        "confined_secondaries": table["confined_secondaries"],
        "confined_slots": table["confined_slots"],
        "observed_mate_case_attack_confined": (
            table["observed_mate_case_attack_confined"]
        ),
        "slot_rows": slots,
    }


def run_stage_cell(*, bundle: str, seed: int, platform: str, epochs: int,
                   confinement: str) -> dict[str, Any]:
    """One instrumented cell; spec identical to flu_confined_dose_probe's."""
    import tempfile as _tempfile  # noqa: PLC0415

    from picard_framework.pathogen_overrides import (  # noqa: PLC0415
        isolate_arm_overrides,
        load_pathogen_bundle,
    )
    from picard_framework.run_spec import PicardRunSpec  # noqa: PLC0415
    from picard_framework.simulation.ship_simulation import (  # noqa: PLC0415
        ShipSimulation,
    )
    from simulation_utils.platform_complement import (  # noqa: PLC0415
        declared_total,
    )
    from tools.noro_diag.per_host_dose_challenge import (  # noqa: PLC0415
        build_spec,
    )

    profiles = load_pathogen_bundle(
        resolve_repo_path(
            str(REPO_ROOT), asset_defaults.pathogen_bundle_rel(bundle),
        ),
    )
    profile = profiles[PATHOGEN]
    spec_dict = build_spec(
        seed=seed, platform=platform, bundle=bundle,
        epochs=epochs, num_agents=declared_total(platform),
        pathogen_id=PATHOGEN, alpha=None, beta=0.0,
        high_touch_area_scale=None, high_touch_area_scale_by_zone_class=None,
        fomite_representation=None, fomite_touch_share=None,
        fomite_touch_share_table=None,
    )
    spec_dict["pathogen_overrides"] = isolate_arm_overrides(
        bundle, PATHOGEN, {PATHOGEN: {"initial_infected": None}},
    )
    party = (profile.get("boarding") or {}).get("party") or {}
    spec_dict["config_overrides"]["initiation"] = {
        "explicit_seeds": [{
            "pathogen": PATHOGEN,
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
    rec = StageRecorder(PATHOGEN)
    ledger = CabinPairChallengeLedger()
    with _tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        spec_path = Path(tmp) / "run_spec.json"
        with validated_open(
            spec_path, "w", allowed_roots=(tmp,), encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(spec_dict))
        picard_spec = PicardRunSpec.from_picard_json(
            str(REPO_ROOT), str(spec_path),
        )
        sim = ShipSimulation(picard_spec, display=False)
        sim.epoch_observer = ledger.observe
        rec.install()
        try:
            sim.run()
        finally:
            rec.restore()
    return _cell_report(
        ledger, rec, sim,
        {"bundle": bundle, "seed": seed, "platform": platform,
         "confinement": confinement, "pathogen_id": PATHOGEN},
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", default="classic_cruise_1900")
    parser.add_argument("--epochs", type=int, default=288)
    parser.add_argument("--seeds", type=int, nargs="+", default=[8105, 8106])
    parser.add_argument(
        "--confinement", choices=("organic", "declared"), default="declared",
    )
    parser.add_argument("--bundles", nargs="+", default=[ACTIVE])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    results = [
        run_stage_cell(
            bundle=bundle, seed=seed, platform=args.platform,
            epochs=args.epochs, confinement=args.confinement,
        )
        for bundle in args.bundles
        for seed in args.seeds
    ]
    out = args.out.resolve()
    if not out.is_relative_to(REPO_ROOT):
        out = REPO_ROOT / out.name
    with validated_open(
        out, "w", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        handle.write(json.dumps(results, indent=1, default=str))
    for row in results:
        t = row["stage_totals"]
        print(
            f"{row['bundle']} seed {row['seed']}: slots={row['n_slots']} "
            f"emitted={t.get('emitted_member_copies', 0):.3g} "
            f"delivered={row['delivered_dose_copies']:.4g} "
            f"capture={row['capture_ratio_delivered_per_emitted']}",
            flush=True,
        )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
