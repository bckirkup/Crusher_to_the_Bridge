"""
Steppable ship simulation extracted from orchestrator.py.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from crusher_labs import build_modalities
from crusher_labs.protocol_engine import (
    apply_hvac_modifiers,
    apply_transmission_modifiers,
    compute_stoplights,
    reset_modifiers,
)
from decision_engine.actions import ActionEnvelope
from engines.py_contam_bridge import build_transport_engine, load_air_flow_paths
from engines.transmission_core import TransmissionCore, build_hvac_downstream_map
from orchestrator_chronic import (
    assign_chronic_diseases,
    get_chronic_behavioral_modifiers,
    get_chronic_wearable_offsets,
    load_chronic_disease_config,
    print_chronic_disease_summary,
)
from orchestrator_epoch import (
    apply_chronic_severity_escalation,
    apply_surface_decontamination,
    apply_zone_closures,
    build_cascade_context,
    compute_infection_counters,
    compute_zone_microflora_shifts,
    run_observation_sampling,
    step_cost_accounting,
    step_diagnostic_cascade,
    step_long_read_cost_accounting,
    step_counter_thresholds,
    step_fred_compliance,
    step_infection_progression,
    step_mid_cruise_introductions,
    step_quarantine_confinement,
    step_operational_impact_accounting,
    step_wearable_monitoring,
)
from orchestrator_init import (
    build_engine,
    check_escalation,
    engine_payload_to_schema,
    init_multi_pathogen,
    init_observation_engine,
    init_protocol_engine,
    init_wearable_monitors,
    initialize_grumb_seeding,
    initialize_ship_graph,
    load_isolation_unit_capacity,
    load_pathogen_profiles,
)
from orchestrator_record import finalize_simulation, record_epoch
from orchestrator_types import (
    REPO_ROOT,
    STATUS_CONFIRMED,
    STATUS_SUSPECTED,
    SimulationState,
)
from picard_framework.run_spec import PicardRunSpec
from picard_framework.simulation.action_applier import apply_action_envelope
from decision_engine.runtime import DecisionRuntime
from decision_engine.protocol_filter import eligible_protocol_ids, filter_active_modifiers
from decision_engine.experience import ExperienceStore
from picard_framework.simulation.step_result import StepResult
from picard_framework.world_state import WorldState
from telemetry_buffer.schema import make_ground_truth, read_ground_truth, write_ground_truth


@dataclass
class RunResult:
    num_epochs: int
    final_trigger_status: str
    history: list[dict[str, Any]] = field(default_factory=list)


class ShipSimulation:
    """One ship cruise: init, step, run, finalize."""

    def __init__(
        self,
        run_spec: PicardRunSpec,
        *,
        display: bool = False,
        repo_root: str | None = None,
    ) -> None:
        self.run_spec = run_spec
        self.display = display
        self.repo_root = repo_root or run_spec.repo_root or REPO_ROOT
        self._epoch = -1
        self._initialized = False

        self.cfg = run_spec.inject_into_cfg()
        self.seed = run_spec.random_seed
        self.rng = np.random.default_rng(self.seed)
        self.num_epochs = run_spec.num_epochs

        self.state: SimulationState | None = None
        self.world: WorldState | None = None
        self.engine = None
        self.contam_engine = None
        self.tx_core = None
        self.obs = None
        self.proto_ctx = None
        self.pathogen_profiles: dict[str, dict[str, Any]] = {}
        self.zone_names: list[str] = []
        self.high_traffic: list[str] = []
        self.zone_volumes: dict[str, float] = {}
        self.zone_types: dict[str, str] = {}
        self.hvac_downstream: dict[str, list[str]] = {}
        self.modalities: dict[str, Any] = {}
        self.wearable_monitor = None
        self.wearable_modality = None
        self.enable_dual_signal = True
        self.mp_cfg: dict[str, Any] = {}
        self.mf_cfg: dict[str, Any] = {}
        self.graph_cfg: dict[str, Any] = {}
        self.decision_runtime: DecisionRuntime | None = None
        self.decision_experience = ExperienceStore("")
        self.chronic_config: dict[str, dict[str, Any]] = {}
        self.chronic_assignments: dict[int, list[str]] = {}
        self.chronic_behavioral_mods: dict[int, dict[str, float]] = {}


    @property
    def epoch(self) -> int:
        return self._epoch

    def initialize(self) -> WorldState:
        if self._initialized:
            return self.world  # type: ignore[return-value]

        cfg = self.cfg
        self.modalities = build_modalities(cfg, self.rng, total_epochs=self.num_epochs)
        ship = initialize_ship_graph(cfg)
        self.zone_names = ship["zone_names"]
        self.high_traffic = ship["high_traffic_zones"]
        self.graph_cfg = cfg.get("ship_graph", {})

        self.engine = build_engine(cfg, seed=self.seed)
        if self.display:
            from orchestrator_display import print_korkin_engine
            print_korkin_engine(self.engine)

        self.contam_engine = build_transport_engine(self.repo_root, cfg)
        if self.contam_engine is not None:
            self.engine.enable_external_transport()
        if self.display:
            from orchestrator_display import print_contam_engine
            print_contam_engine(self.contam_engine, self.engine, cfg)

        self.pathogen_profiles = load_pathogen_profiles(cfg)
        self.mp_cfg = cfg.get("multi_pathogen", {})
        self.mf_cfg = cfg.get("microflora", {})
        self.enable_dual_signal = self.mf_cfg.get("enable_dual_signal", True)
        init_multi_pathogen(self.engine, self.pathogen_profiles, cfg, self.rng)

        if self.display:
            from orchestrator_display import print_multi_pathogen
            imm_mult = self.mp_cfg.get("immunocompromised_multiplier", 2.0)
            print_multi_pathogen(
                self.pathogen_profiles, set(), self.engine, imm_mult, self.enable_dual_signal,
            )

        # Chronic disease assignment
        self.chronic_config = load_chronic_disease_config(cfg, repo_root=self.repo_root)
        self.chronic_assignments = assign_chronic_diseases(
            self.engine, self.chronic_config, self.pathogen_profiles, cfg, self.rng,
        )
        chronic_wearable_offsets = get_chronic_wearable_offsets(
            self.chronic_config, self.chronic_assignments,
        )
        self.chronic_behavioral_mods = get_chronic_behavioral_modifiers(
            self.chronic_config, self.chronic_assignments,
        )
        if self.display:
            print_chronic_disease_summary(
                self.chronic_config, self.chronic_assignments, len(self.engine.agents),
            )

        airflow_data = load_air_flow_paths(self.repo_root, cfg)
        self.zone_volumes = {
            z["name"]: z.get("volume_m3", 100.0) for z in ship.get("zones", [])
        }
        zone_types = {z["name"]: z.get("type", "") for z in ship.get("zones", [])}
        self.zone_types = zone_types
        self.hvac_downstream = (
            build_hvac_downstream_map(airflow_data) if airflow_data else {}
        )
        self.tx_core = TransmissionCore(
            rng=np.random.default_rng(self.seed),
            zone_volumes=self.zone_volumes,
            pathogen_profiles=self.pathogen_profiles,
            zone_types=zone_types,
        )
        self.tx_core.initialize_zones(self.zone_names)
        self.engine.enable_external_transmission()
        if self.display:
            from orchestrator_display import print_transmission_core
            print_transmission_core(self.hvac_downstream, self.pathogen_profiles)

        self.obs = init_observation_engine(cfg, self.seed)
        self.proto_ctx = init_protocol_engine(
            cfg,
            self.contam_engine,
            protocols_path=self.run_spec.protocols_path,
            resource_costs_path=self.run_spec.resource_costs_path,
            logging_profile_path=self.run_spec.logging_profile_path,
        )
        self.wearable_monitor, self.wearable_modality = init_wearable_monitors(
            self.engine, cfg, self.seed,
            chronic_wearable_offsets=chronic_wearable_offsets,
        )
        if self.display:
            from orchestrator_display import print_wearable_monitoring
            print_wearable_monitoring(self.wearable_monitor)

        seq = self.modalities["sequencing"]
        grumb_seeds = initialize_grumb_seeding(seq, ship["zones"])
        if self.display:
            from orchestrator_display import print_initialization
            print_initialization(ship, grumb_seeds, cfg)

        from crusher_labs.diagnostic_cascade import build_cascade_engine

        cascade_engine = build_cascade_engine(cfg, repo_root=self.repo_root)
        sim_state = SimulationState(
            isolation_unit_capacity=load_isolation_unit_capacity(cfg),
            cascade_engine=cascade_engine,
            chronic_assignments=self.chronic_assignments,
            chronic_behavioral_mods=self.chronic_behavioral_mods,
        )
        self.state = sim_state
        self.world = WorldState(
            simulation=sim_state,
            observation=self.obs,
            protocol=self.proto_ctx,
        )
        self.decision_runtime = DecisionRuntime.from_run_spec(
            self.run_spec, self.engine, self.proto_ctx,
        )
        exp_path = self.run_spec.social_config.get("experience_store", "")
        if exp_path:
            ep = exp_path if os.path.isabs(exp_path) else os.path.join(self.repo_root, exp_path)
            self.decision_experience = ExperienceStore(ep)
            self.decision_experience.load()
        self._initialized = True
        return self.world

    def step(self, actions: ActionEnvelope | None = None) -> StepResult:
        if not self._initialized:
            self.initialize()
        assert self.state is not None
        assert self.engine is not None
        assert self.tx_core is not None
        assert self.obs is not None
        assert self.proto_ctx is not None

        epoch = self._epoch + 1
        if epoch >= self.num_epochs:
            raise RuntimeError(f"Simulation complete ({self.num_epochs} epochs)")

        state = self.state
        cfg = self.cfg
        syndromic = self.modalities["syndromic"]
        rdt = self.modalities["clinical_rdt"]
        pcr = self.modalities["targeted_pcr"]
        seq = self.modalities["sequencing"]

        state.agent_behavioral_overrides.clear()
        cfg.pop("_picard_epoch_overrides", None)
        dr = self.decision_runtime
        if dr is not None:
            dr.decision_ctx.reset_ephemeral()

        applied = apply_action_envelope(
            actions,
            state,
            cfg,
            decision_ctx=dr.decision_ctx if dr else None,
            valid_zones=set(self.zone_names),
        )

        step_fred_compliance(epoch, state, syndromic)
        step_mid_cruise_introductions(epoch, self.engine, self.pathogen_profiles, self.rng)

        self.engine.isolated_ids = set(state.isolated_ids)
        self.engine.quarantined_ids = set(state.quarantined_ids)
        self.engine.step()

        step_infection_progression(self.engine, self.pathogen_profiles)

        tracing_matrix, _tx_events = self.tx_core.execute_transmission(
            epoch=epoch,
            agents=self.engine.agents,
            zone_pathogen_mass=self.engine.zone_pathogen_mass,
            hvac_downstream_zones=self.hvac_downstream,
            multi_pathogen_mass=(
                self.engine.multi_pathogen_mass if self.pathogen_profiles else None
            ),
        )

        if self.contam_engine is not None:
            updated = self.contam_engine.transport_step(self.engine.zone_pathogen_mass)
            self.engine.zone_pathogen_mass = updated

        zone_microflora_shifts: dict[str, dict[str, float]] = {}
        if self.pathogen_profiles and self.enable_dual_signal:
            zone_microflora_shifts = compute_zone_microflora_shifts(
                self.engine.agents, self.pathogen_profiles, cfg,
            )

        engine_payload = self.engine._export_payload()
        agents, spaces = engine_payload_to_schema(
            engine_payload,
            state.isolated_ids,
            state.quarantined_ids,
            state.quarantine_refusers,
        )

        if self.chronic_assignments:
            apply_chronic_severity_escalation(agents, self.engine, self.rng)

        payload = make_ground_truth(epoch=epoch, agents=agents, spaces=spaces)
        gt_path = self.run_spec.telemetry.ground_truth if self.run_spec.telemetry else None
        if self.run_spec.write_ground_truth:
            if gt_path:
                write_ground_truth(payload, path=gt_path)
                truth = read_ground_truth(path=gt_path)
            else:
                write_ground_truth(payload)
                truth = read_ground_truth()
            assert truth is not payload, "Shared-memory leak!"
        else:
            truth = payload

        wearable_result = step_wearable_monitoring(
            epoch, self.engine, self.wearable_monitor, self.wearable_modality,
            truth, self.pathogen_profiles,
        )

        information_state: dict = {}
        pop_envelope: ActionEnvelope | None = None
        if dr is not None:
            tracing_dict = tracing_matrix.to_dict()
            dr.contact_graph.update(agents, tracing_dict, dr.class_matrix)
            pop = max(1, len(agents))
            conf_rate = len(state.quarantined_ids) / pop
            agent_classes = {
                int(a["agent_id"]): a.get("agent_class", "unknown") for a in agents
            }
            information_state = dr.information_engine.step(
                dr.contact_graph.agent_adjacency,
                agent_classes,
                state.trigger_status,
                conf_rate,
            )
            pre_snapshot = {
                "epoch": epoch,
                "agents": agents,
                "summary": self._build_summary(agents, syn_result=None),
                "trigger_status": state.trigger_status,
                "high_traffic_zones": self.high_traffic,
            }
            if dr.stackelberg is not None:
                pop_envelope = dr.stackelberg.solve_population(
                    epoch, pre_snapshot, information_state, self.decision_experience,
                )
                pop_applied = apply_action_envelope(
                    pop_envelope, state, cfg, dr.decision_ctx, set(self.zone_names),
                )
                if pop_applied:
                    applied = pop_applied if not applied else {**applied, **pop_applied}

        beliefs: dict[int, dict[str, float]] = {}
        agent_inf = information_state.get("agents", information_state)
        if isinstance(agent_inf, dict):
            for aid_str, inf in agent_inf.items():
                if not isinstance(inf, dict):
                    continue
                try:
                    beliefs[int(aid_str)] = {
                        "severity_belief": float(inf.get("severity_belief", 0.1)),
                        "trust_medical": float(inf.get("trust_medical", 0.75)),
                    }
                except (TypeError, ValueError):
                    continue

        syn_result = syndromic.query_ground_truth(
            truth,
            behavioral_overrides=state.agent_behavioral_overrides,
            information_beliefs=beliefs,
            chronic_behavioral_mods=self.chronic_behavioral_mods,
        )

        cascade_result = step_diagnostic_cascade(
            epoch, state, agents, syn_result, wearable_result, self.obs,
            wearable_monitor=self.wearable_monitor,
        )

        sick_call_ids = syn_result["sick_call_agents"]
        rdt_result = rdt.query_ground_truth(truth, sick_call_ids=sick_call_ids)

        if dr is not None:
            dr.lived_store.update(
                epoch, agents, syn_result,
                [], state.quarantined_ids, state.isolated_ids,
                dr.contact_graph.agent_adjacency,
                wearable_result, dr.profiles,
            )

        overrides = cfg.get("_picard_epoch_overrides", {})
        pcr_cadence = overrides.get(
            "pcr_cadence", cfg.get("targeted_pcr", {}).get("cadence", 4),
        )
        seq_cadence = overrides.get(
            "sequencing_cadence", cfg.get("sequencing", {}).get("cadence", 8),
        )

        verify_zones = [
            str(q["zone"]) for q in state.verification_test_queue
            if int(q.get("epoch", 0)) <= epoch
        ]
        state.verification_test_queue = [
            q for q in state.verification_test_queue
            if int(q.get("epoch", 0)) > epoch
        ]

        pcr_result = None
        if state.trigger_status == STATUS_SUSPECTED:
            wipe = list(dict.fromkeys(self.high_traffic + verify_zones))
            pcr_result = pcr.query_ground_truth(truth, surface_wipe_zones=wipe)
        elif state.trigger_status == STATUS_CONFIRMED:
            wipe = list(dict.fromkeys(self.zone_names + verify_zones))
            pcr_result = pcr.query_ground_truth(truth, surface_wipe_zones=wipe)
        elif epoch % int(pcr_cadence) == 0:
            if verify_zones:
                pcr_result = pcr.query_ground_truth(
                    truth, surface_wipe_zones=verify_zones,
                )
            else:
                pcr_result = pcr.query_ground_truth(truth)

        seq_result = None
        if epoch % int(seq_cadence) == 0:
            seq_result = seq.query_ground_truth(
                truth, zone_microflora_shifts=zone_microflora_shifts,
            )

        (air_results, swab_results, ww_results,
         clin_rdt_results, clin_qpcr_results, clin_microbio_results,
         long_read_results, long_read_ordered_count) = (
            run_observation_sampling(
                epoch, self.obs, agents, spaces, self.zone_names, self.zone_volumes,
                zone_microflora_shifts, state.trigger_status, self.high_traffic,
                syn_result, self.engine, self.pathogen_profiles, cfg,
            )
        )

        prev_status = state.trigger_status
        state.trigger_status = check_escalation(
            state.trigger_status, syn_result, pcr_result, cfg,
        )
        if state.trigger_status != prev_status:
            state.escalation_log.append({
                "epoch": epoch, "from": prev_status, "to": state.trigger_status,
            })
            self.obs.notebook.log_trigger_transition(
                epoch, prev_status, state.trigger_status,
            )

        stoplights = compute_stoplights(
            air_results, swab_results, ww_results,
            clin_rdt_results, clin_qpcr_results, clin_microbio_results,
            wearable_result=wearable_result,
            syndromic_result=syn_result,
            long_read_results=long_read_results,
            cfg=cfg,
        )

        cmd_envelope: ActionEnvelope | None = None
        if dr is not None:
            for msg in dr.decision_ctx.sop_announcements + dr.lived_store.sop_announcements:
                dr.information_engine.seed_public_message(msg)
            dr.information_engine.reputation.on_corporate_stance(
                dr.decision_ctx.corporate_communication_stance,
            )
            eligible = eligible_protocol_ids(
                self.proto_ctx.standing_protocols, stoplights,
            )
            epoch_snapshot = {
                "epoch": epoch,
                "agents": agents,
                "trigger_status": state.trigger_status,
                "summary": self._build_summary(agents, syn_result),
                "reactive_protocols": {"stoplights": stoplights},
                "observation_engine": {
                    "air_sniffer": air_results,
                    "surface_swab": swab_results,
                },
                "cost_accounting": {
                    "operational_impact_cumulative": (
                        self.proto_ctx.cost_ledger.operational_impact_cumulative
                    ),
                },
                "high_traffic_zones": self.high_traffic,
            }
            if dr.stackelberg is not None:
                cmd_envelope = dr.stackelberg.solve_command_medical(
                    epoch,
                    epoch_snapshot,
                    dr.decision_ctx,
                    dr.lived_store,
                    information_state,
                    dr.information_engine.reputation,
                    dr.global_health_timeline,
                    self.decision_experience,
                    eligible,
                )
                cmd_applied = apply_action_envelope(
                    cmd_envelope, state, cfg, dr.decision_ctx, set(self.zone_names),
                )
                if cmd_applied:
                    applied = cmd_applied if not applied else {**applied, **cmd_applied}

        reset_modifiers(
            self.contam_engine, self.tx_core, self.proto_ctx.original_filter_eff,
        )
        cascade_ctx = build_cascade_context(state, cascade_result)
        authorized = dr.decision_ctx.authorized_sop_ids if dr else None
        active_mods = self.proto_ctx.protocol_engine.evaluate_epoch(
            epoch,
            stoplights,
            forced_protocol_ids=state.forced_protocol_ids,
            authorized_sop_ids=authorized,
            cascade_context=cascade_ctx,
        )
        if dr is not None and dr.decision_ctx.authorized_sop_ids is not None:
            active_mods = filter_active_modifiers(
                active_mods, dr.decision_ctx.authorized_sop_ids,
            )
        merged_mods = self.proto_ctx.protocol_engine.get_merged_modifiers(active_mods)

        if merged_mods:
            apply_hvac_modifiers(self.contam_engine, merged_mods)
            apply_transmission_modifiers(self.tx_core, merged_mods)
            if "close_zones" in merged_mods:
                apply_zone_closures(self.engine, merged_mods["close_zones"])
            if "surface_decontamination_factor" in merged_mods:
                apply_surface_decontamination(
                    self.engine, merged_mods["surface_decontamination_factor"],
                )

        step_cost_accounting(
            epoch, self.proto_ctx,
            air_results, swab_results, ww_results,
            clin_rdt_results, clin_qpcr_results, clin_microbio_results,
        )
        step_long_read_cost_accounting(epoch, self.proto_ctx, long_read_ordered_count)
        step_quarantine_confinement(
            epoch, agents, merged_mods, state.trigger_status, state, syndromic,
        )

        counter_defs = self.graph_cfg.get("infection_counters", [])
        counter_results = compute_infection_counters(agents, counter_defs)
        step_counter_thresholds(
            epoch, agents, counter_results, counter_defs, state, syndromic,
        )

        step_operational_impact_accounting(
            epoch, state, agents, merged_mods, self.proto_ctx,
            zone_type_by_id=self.zone_types,
        )

        state.agent_behavioral_overrides.clear()

        epoch_cost = self.proto_ctx.cost_ledger.get_epoch_summary(epoch)
        epoch_record = record_epoch(
            epoch=epoch,
            trigger_status=state.trigger_status,
            agents=agents,
            spaces=spaces,
            engine=self.engine,
            contam_engine=self.contam_engine,
            pathogen_profiles=self.pathogen_profiles,
            zone_names=self.zone_names,
            zone_microflora_shifts=zone_microflora_shifts,
            syn_result=syn_result,
            rdt_result=rdt_result,
            pcr_result=pcr_result,
            seq_result=seq_result,
            tracing_matrix=tracing_matrix,
            state=state,
            obs=self.obs,
            active_mods=active_mods,
            merged_mods=merged_mods,
            stoplights=stoplights,
            epoch_cost=epoch_cost,
            cfg=cfg,
            air_results=air_results,
            swab_results=swab_results,
            ww_results=ww_results,
            clin_rdt_results=clin_rdt_results,
            clin_qpcr_results=clin_qpcr_results,
            clin_microbio_results=clin_microbio_results,
            wearable_result=wearable_result,
            infection_counters=counter_results,
            long_read_results=long_read_results,
            cascade_result=cascade_result,
        )
        if applied:
            epoch_record["decisions"] = applied
        if dr is not None:
            dr.capture_sop_events(self.proto_ctx.protocol_engine, epoch)
            epoch_record.setdefault("reactive_protocols", {})["sop_events"] = dr.sop_events_buffer
            epoch_record["information_state"] = information_state
            if dr.decision_detail_telemetry and wearable_result:
                epoch_record["wearable_agent_snapshot"] = wearable_result.get("agent_results", {})
            for ag in epoch_record.get("agents", []):
                pid = dr.profiles.get(int(ag.get("agent_id", -1)))
                if pid:
                    ag["profile_id"] = pid.profile_id
            epoch_record.setdefault("contact_tracing", {})["agent_adjacency"] = (
                dr.contact_graph.to_dict().get("agent_adjacency", {})
            )
        state.simulation_history.append(epoch_record)
        self._epoch = epoch

        if self.display:
            from orchestrator_display import print_progress
            total_spent = (
                self.proto_ctx.cost_ledger.starting_financial_usd
                - self.proto_ctx.cost_ledger.financial_balance
            )
            print_progress(
                epoch, self.num_epochs, state.trigger_status,
                len(active_mods), total_spent, prev_status,
            )

        return StepResult(
            epoch=epoch,
            trigger_status=state.trigger_status,
            stoplights=stoplights,
            epoch_record=epoch_record,
            ground_truth=payload,
            active_protocols=active_mods,
            merged_modifiers=merged_mods,
            decisions=applied,
        )

    @staticmethod
    def _build_summary(
        agents: list[dict[str, Any]],
        syn_result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        from telemetry_buffer.agent_axes import (
            agent_has_symptomatic_presentation,
            resolve_agent_axes,
        )
        summary: dict[str, Any] = {
            "sick_call_count": syn_result.get("sick_call_count", 0) if syn_result else 0,
        }
        for key in ("susceptible", "infected", "recovered", "immune", "symptomatic"):
            summary[key] = 0
        for ag in agents:
            inf, _, _ = resolve_agent_axes(ag)
            if inf == "susceptible":
                summary["susceptible"] += 1
            elif inf == "infected":
                summary["infected"] += 1
            elif inf == "recovered":
                summary["recovered"] += 1
            elif inf == "immune":
                summary["immune"] += 1
            if agent_has_symptomatic_presentation(ag):
                summary["symptomatic"] += 1
        return summary

    def run(self, n_epochs: int | None = None) -> RunResult:
        if not self._initialized:
            self.initialize()
        target = n_epochs if n_epochs is not None else self.num_epochs
        while self._epoch + 1 < target:
            self.step()
        assert self.state is not None
        return RunResult(
            num_epochs=target,
            final_trigger_status=self.state.trigger_status,
            history=list(self.state.simulation_history),
        )

    def finalize(self, *, display: bool | None = None) -> None:
        if not self._initialized or self.state is None:
            return
        show = self.display if display is None else display
        paths = self.run_spec.telemetry
        history_path = paths.simulation_history if paths else None
        logging_path = self.run_spec.logging_profile_path

        finalize_simulation(
            state=self.state,
            engine=self.engine,
            obs=self.obs,
            proto_ctx=self.proto_ctx,
            pathogen_profiles=self.pathogen_profiles,
            zone_names=self.zone_names,
            num_agents=len(self.engine.agents) if self.engine else 0,
            num_epochs=self.num_epochs,
            contam_engine=self.contam_engine,
            cfg=self.cfg,
            history_path=history_path,
            logging_profile_path=logging_path,
            display=show,
        )
