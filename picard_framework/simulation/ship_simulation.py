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
from decision_engine.experience import ExperienceStore
from decision_engine.protocol_filter import eligible_protocol_ids, filter_active_modifiers
from decision_engine.runtime import DecisionRuntime
from engines.py_contam_bridge import (
    build_transport_engine,
    load_air_flow_paths,
)
from engines.py_contam_bridge import (
    load_spatial_layout as load_platform_layout,
)
from engines.transmission_core import (
    DEFAULT_CONFINEMENT_ISOLATION_FACTOR,
    DEFAULT_CORRIDOR_DIRECT_CONTACT_FACTOR,
    TransmissionCore,
    build_hvac_downstream_map,
)
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
    inactive_syndromic_result,
    run_observation_sampling,
    step_cascade_cost_accounting,
    step_cost_accounting,
    step_counter_thresholds,
    step_diagnostic_cascade,
    step_fred_compliance,
    step_infection_progression,
    step_long_read_cost_accounting,
    step_mid_cruise_introductions,
    step_operational_impact_accounting,
    step_quarantine_confinement,
    step_wearable_monitoring,
    surveillance_is_active,
)
from orchestrator_init import (
    apply_voyage_dining_meal_weights,
    apply_voyage_medical_response,
    assign_cabin_mates,
    build_engine,
    check_escalation,
    engine_payload_to_schema,
    init_multi_pathogen,
    init_observation_engine,
    init_protocol_engine,
    init_wearable_monitors,
    initialize_grumb_seeding,
    initialize_ship_graph,
    load_and_merge_voyage_config,
    load_isolation_unit_capacity,
    load_pathogen_profiles,
    pathogen_profiles_are_respiratory,
    update_cumulative_confirmed_cases,
)
from orchestrator_record import finalize_simulation, record_epoch
from orchestrator_types import (
    REPO_ROOT,
    STATUS_ALERT,
    STATUS_CONFIRMED,
    STATUS_RANK,
    SimulationState,
)
from picard_framework.analysis.sentinel.line_list import SentinelLedger
from picard_framework.run_spec import PicardRunSpec
from picard_framework.simulation.action_applier import apply_action_envelope
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
        self.sentinel_ledger: SentinelLedger | None = None
        self._sentinel_port_ids: dict[str, str] = {}


    @property
    def epoch(self) -> int:
        return self._epoch

    def _init_transmission_core(
        self,
        ship: dict[str, Any],
        airflow_data: dict[str, Any] | None,
        platform_layout: dict[str, Any],
    ) -> None:
        self.zone_volumes = {
            z["name"]: z.get("volume_m3", 100.0) for z in ship.get("zones", [])
        }
        zone_types = {z["name"]: z.get("type", "") for z in ship.get("zones", [])}
        zone_ventilation: dict[str, str] = {}
        food_zone_multipliers: dict[str, float] = {}
        for z in platform_layout.get("zones", []):
            zid = z["id"]
            vent = z.get("cabin_ventilation_type")
            if vent:
                zone_ventilation[zid] = vent
            if z.get("type") == "Dining":
                mult = z.get("food_contamination_multiplier")
                if mult is None:
                    stype = str(z.get("dining_service_type") or "")
                    from engines.infection_dynamics_bridge import (
                        DEFAULT_FOOD_CONTAMINATION_MULTIPLIER,
                    )
                    mult = DEFAULT_FOOD_CONTAMINATION_MULTIPLIER.get(stype, 1.0)
                food_zone_multipliers[zid] = float(mult)
        self.zone_types = zone_types
        self.hvac_downstream = (
            build_hvac_downstream_map(airflow_data) if airflow_data else {}
        )
        self.tx_core = TransmissionCore(
            rng=np.random.default_rng(self.seed),
            zone_volumes=self.zone_volumes,
            pathogen_profiles=self.pathogen_profiles,
            zone_types=zone_types,
            zone_ventilation=zone_ventilation,
            confinement_isolation_factor=float(
                platform_layout.get(
                    "confinement_isolation_factor",
                    DEFAULT_CONFINEMENT_ISOLATION_FACTOR,
                )
            ),
            corridor_direct_contact_factor=float(
                platform_layout.get(
                    "corridor_direct_contact_factor",
                    DEFAULT_CORRIDOR_DIRECT_CONTACT_FACTOR,
                )
            ),
            cfg=self.cfg,
            food_zone_multipliers=food_zone_multipliers,
        )
        self.tx_core.initialize_zones(self.zone_names)
        self.engine.enable_external_transmission()
        if self.display:
            from orchestrator_display import print_transmission_core
            print_transmission_core(self.hvac_downstream, self.pathogen_profiles)

    def initialize(self) -> WorldState:
        if self._initialized:
            return self.world  # type: ignore[return-value]

        cfg = self.cfg
        voyage_cfg = load_and_merge_voyage_config(
            cfg,
            repo_root=self.repo_root,
            platform_id=self.run_spec.platform_id,
        )
        cfg = apply_voyage_dining_meal_weights(cfg, voyage_cfg)
        cfg = apply_voyage_medical_response(cfg, voyage_cfg)
        # Keep local cfg and run_spec in sync for downstream helpers
        self.cfg = cfg
        self.run_spec.legacy_cfg = cfg
        self.modalities = build_modalities(cfg, self.rng, total_epochs=self.num_epochs)
        ship = initialize_ship_graph(cfg)
        self.zone_names = ship["zone_names"]
        self.high_traffic = ship["high_traffic_zones"]
        self.graph_cfg = cfg.get("ship_graph", {})

        self.engine = build_engine(cfg, seed=self.seed)
        if self.display:
            from orchestrator_display import print_korkin_engine
            print_korkin_engine(self.engine)

        assign_cabin_mates(self.engine.agents, ship["zones"])

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
        platform_layout = load_platform_layout(self.repo_root, cfg) or {}
        self._init_transmission_core(ship, airflow_data, platform_layout)

        self.obs = init_observation_engine(
            cfg, self.seed, pathogen_profiles=self.pathogen_profiles,
        )
        # Compact retention skips lab-notebook accumulation (campaign never finalizes it).
        if self.run_spec.history_retention == "compact":
            self.obs.lab_notebook_enabled = False
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
            chronic_assignments=self.chronic_assignments,
            repo_root=self.repo_root,
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
            voyage_config=voyage_cfg,
        )
        self.state = sim_state
        self._init_sentinel_ledger(voyage_cfg)
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
            self.decision_experience = ExperienceStore(
                ep,
                allowed_roots=(self.repo_root,),
            )
            self.decision_experience.load()
        self._initialized = True
        return self.world

    def _init_sentinel_ledger(self, voyage_cfg: dict[str, Any] | None) -> None:
        """Arm the sentinel ledger when a line-list output path is configured.

        Off by default: per-person onset and ashore hours are only collected
        when someone asked for them, so ``compact`` runs stay compact.
        """
        paths = self.run_spec.telemetry
        if paths is None or not paths.sentinel_line_list:
            return
        from picard_framework.analysis.sentinel.export_line_list import port_id_lookup

        voyage = (voyage_cfg or {}).get("voyage") or {}
        self.sentinel_ledger = SentinelLedger(
            epoch_duration_hours=float(voyage.get("epoch_duration_hours", 1) or 1),
        )
        self._sentinel_port_ids = port_id_lookup(voyage_cfg)

    def _observe_sentinel(
        self,
        epoch: int,
        agents: list[dict[str, Any]],
        syn_result: dict[str, Any] | None,
        cascade_result: dict[str, Any] | None,
        wearable_result: dict[str, Any] | None,
    ) -> None:
        """Fold this epoch's per-person state into the sentinel ledger."""
        ledger = self.sentinel_ledger
        if ledger is None or self.engine is None:
            return
        from picard_framework.analysis.sentinel.itinerary import slugify_port

        epoch_voyage = self.state.epoch_voyage if self.state else None
        port_name = str(epoch_voyage.port or "") if epoch_voyage else ""
        port_id = self._sentinel_port_ids.get(port_name) or (
            slugify_port(port_name) if port_name else ""
        )
        ashore = [a.agent_id for a in self.engine.agents if a.ashore]

        detections: dict[str, list[int]] = {}
        syn = syn_result or {}
        screening = [int(a) for a in syn.get("crew_screening_ids") or []]
        sick_call = [
            int(a)
            for a in syn.get("sick_call_agents") or []
            if int(a) not in set(screening)
        ]
        if sick_call:
            detections["sick_call"] = sick_call
        if screening:
            detections["screening"] = screening
        cascade = cascade_result or {}
        tiers = [
            int(a)
            for key in ("new_tier0_agents", "new_tier1_agents")
            for a in cascade.get(key) or []
        ]
        if tiers:
            detections["cascade"] = tiers
        visible = [int(a) for a in (wearable_result or {}).get("staff_visible_agents") or []]
        if visible:
            detections["wearable"] = visible

        ledger.observe_epoch(
            epoch,
            agents,
            port_id=port_id,
            ashore_ids=ashore,
            detections=detections,
        )

    def _write_sentinel_line_list(self) -> None:
        """Write the sentinel observation bundle, if one was collected."""
        ledger = self.sentinel_ledger
        paths = self.run_spec.telemetry
        if ledger is None or paths is None or not paths.sentinel_line_list:
            return
        from picard_framework.analysis._io import safe_path, write_json

        agents = self.engine.agents if self.engine else []
        n_crew = sum(1 for a in agents if a.role == "crew")
        payload = ledger.to_payload(
            voyage_id=str(self.cfg.get("voyage_id") or f"seed{self.seed}"),
            ship_id=self.run_spec.platform_id,
            n_passengers=len(agents) - n_crew,
            n_crew=n_crew,
            platform_class=self.run_spec.platform_id,
            observation_end_epoch=max(self._epoch, 1),
        )
        write_json(safe_path(paths.sentinel_line_list), payload)

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

        # Lightweight agent view for reluctant→symptomatic re-checks (pre-step)
        _fred_agents = [
            {
                "agent_id": a.agent_id,
                "agent_class": a.agent_class,
                "symptom_presentation": (
                    "symptomatic" if a.is_symptomatic else "asymptomatic"
                ),
            }
            for a in self.engine.agents
        ]
        step_fred_compliance(epoch, state, syndromic, agents=_fred_agents)
        step_mid_cruise_introductions(epoch, self.engine, self.pathogen_profiles, self.rng)

        from engines.voyage_itinerary import resolve_epoch_state

        epoch_voyage = resolve_epoch_state(state.voyage_config, epoch)
        state.epoch_voyage = epoch_voyage
        self.engine.voyage_epoch_state = epoch_voyage
        self.tx_core.voyage_contact_multiplier = (
            float(epoch_voyage.contact_multiplier)
            if epoch_voyage.effects_active
            else 1.0
        )

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
            quarantined_ids=set(state.quarantined_ids),
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
            pathogen_profiles=self.pathogen_profiles,
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

        if surveillance_is_active(epoch, cfg):
            syn_result = syndromic.query_ground_truth(
                truth,
                behavioral_overrides=state.agent_behavioral_overrides,
                information_beliefs=beliefs,
                chronic_behavioral_mods=self.chronic_behavioral_mods,
            )
            cascade_result = step_diagnostic_cascade(
                epoch, state, agents, syn_result, wearable_result, self.obs,
                wearable_monitor=self.wearable_monitor,
                syndromic=syndromic,
                cfg=cfg,
            )
        else:
            syn_result = inactive_syndromic_result(epoch, n_agents=len(agents))
            cascade_result = None
        from crusher_labs.clinical_presentation import apply_noise_syndromes_to_agents

        apply_noise_syndromes_to_agents(
            agents,
            syn_result,
            cfg.get("fred_behavior", {}).get("healthy_noise_categories"),
        )

        step_cascade_cost_accounting(epoch, self.proto_ctx, cascade_result)

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
        seq_result = None
        observation_enabled = cfg.get("observation", {}).get("enabled", True)
        status_rank = STATUS_RANK.get(state.trigger_status, 0)
        if observation_enabled:
            if status_rank >= STATUS_RANK[STATUS_CONFIRMED]:
                wipe = list(dict.fromkeys(self.zone_names + verify_zones))
                pcr_result = pcr.query_ground_truth(truth, surface_wipe_zones=wipe)
            elif status_rank >= STATUS_RANK[STATUS_ALERT]:
                wipe = list(dict.fromkeys(self.high_traffic + verify_zones))
                pcr_result = pcr.query_ground_truth(truth, surface_wipe_zones=wipe)
            elif epoch % int(pcr_cadence) == 0:
                if verify_zones:
                    pcr_result = pcr.query_ground_truth(
                        truth, surface_wipe_zones=verify_zones,
                    )
                else:
                    pcr_result = pcr.query_ground_truth(truth)

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

        n_confirmed = update_cumulative_confirmed_cases(
            clin_qpcr_results, clin_rdt_results,
            state.cumulative_confirmed_case_ids,
        )
        prev_status = state.trigger_status
        new_status, new_pending, _rates = check_escalation(
            state.trigger_status, syn_result, pcr_result, cfg,
            agents=agents,
            ever_ill_ids=state.ever_ill_ids,
            cumulative_confirmed_cases=n_confirmed,
            epoch=epoch,
            escalation_pending=state.escalation_pending,
            respiratory_mode=pathogen_profiles_are_respiratory(self.pathogen_profiles),
        )
        state.escalation_pending = new_pending
        state.trigger_status = new_status
        if state.trigger_status != prev_status:
            state.escalation_log.append({
                "epoch": epoch, "from": prev_status, "to": state.trigger_status,
            })
            if self.obs.lab_notebook_enabled:
                self.obs.notebook.log_trigger_transition(
                    epoch, prev_status, state.trigger_status,
                )
        elif new_pending is not None and (
            prev_status == state.trigger_status
        ):
            # Log queued (not-yet-effective) transitions once
            pending_to = new_pending.get("to")
            already = any(
                e.get("pending_to") == pending_to
                and e.get("epoch_triggered") == new_pending.get("epoch_triggered")
                for e in state.escalation_log
            )
            if not already:
                state.escalation_log.append({
                    "epoch": epoch,
                    "from": state.trigger_status,
                    "to": pending_to,
                    "pending": True,
                    "pending_to": pending_to,
                    "epoch_triggered": new_pending.get("epoch_triggered"),
                })

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
                trigger_status=state.trigger_status,
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
            trigger_status=state.trigger_status,
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
            confinement_enabled=self.graph_cfg.get(
                "counter_confinement_enabled", True,
            ),
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
            history_retention=self.run_spec.history_retention,
        )
        if applied and self.run_spec.history_retention != "compact":
            epoch_record["decisions"] = applied
        if state.epoch_voyage is not None:
            epoch_record["voyage_epoch"] = state.epoch_voyage.to_telemetry()
        if dr is not None and self.run_spec.history_retention != "compact":
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
        elif dr is not None:
            # Still capture SOP events for runtime, but do not retain in history.
            dr.capture_sop_events(self.proto_ctx.protocol_engine, epoch)
        state.simulation_history.append(epoch_record)
        self._observe_sentinel(
            epoch, agents, syn_result, cascade_result, wearable_result,
        )
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
            history_path=history_path,
            logging_profile_path=logging_path,
            display=show,
        )
        self._write_sentinel_line_list()
