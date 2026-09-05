"""
Steppable ship simulation extracted from orchestrator.py.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from crusher_labs import build_modalities
from crusher_labs.modalities.clinical_strain_typing import (
    specimen_genotype_mixture,
    typed_genotypes,
)
from crusher_labs.modalities.surface_strain_recovery import (
    SurfaceRecoveryConfig,
    recover_surface_mixture,
)
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
from engines.scenario_schedule import ScenarioSchedule, resolve_scenario_schedule
from engines.sim_clock import SimClock
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
    apply_outbreak_surface_disinfection,
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
    step_shore_introductions,
    step_wearable_monitoring,
    surveillance_is_active,
)
from orchestrator_init import (
    apply_voyage_dining_meal_weights,
    apply_voyage_medical_response,
    assign_cabin_mates,
    build_engine,
    check_escalation,
    compute_group_rates_for_ids,
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
    update_ever_infected_ids,
    update_ever_reported_ids,
)
from orchestrator_record import finalize_simulation, record_epoch
from orchestrator_types import (
    REPO_ROOT,
    STATUS_ALERT,
    STATUS_CONFIRMED,
    STATUS_RANK,
    STATUS_SUSPECTED,
    SimulationState,
)
from picard_framework.analysis.sentinel.line_list import SentinelLedger
from picard_framework.analysis.sentinel.wastewater_ops import (
    WastewaterOpsConfig,
    WastewaterOpsSampler,
    assign_collection_points,
)
from picard_framework.run_spec import PicardRunSpec
from picard_framework.simulation.action_applier import apply_action_envelope
from picard_framework.simulation.step_result import StepResult
from picard_framework.world_state import WorldState
from telemetry_buffer.schema import make_ground_truth, read_ground_truth, write_ground_truth

# Keeps wastewater read draws from consuming the transmission stream, so turning
# the channel on cannot change the epidemic it observes.
_WASTEWATER_SEED_OFFSET = 977
# Keeps surface lineage draws from consuming the transmission or swab streams.
_SURFACE_RECOVERY_SEED_OFFSET = 978


def _agent_is_shedding(agent: Any, pathogen_id: str) -> bool:
    """Whether an agent is shedding the sampled pathogen into the plumbing."""
    if pathogen_id:
        return bool(agent.is_infected_with(pathogen_id))
    return bool(agent.is_infected)


def _agent_wastewater_lineages(
    agent: Any,
    pathogen_id: str,
    profile: dict[str, Any],
    registry: Any,
) -> dict[str, float]:
    """Genotype mass one host contributes to the plumbing this epoch.

    Weighted by emitted shedding rather than per capita: a host at peak sheds
    orders of magnitude more than one on its last day, and a tank's composition
    is set by what arrived in it, not by how many people contributed.
    """
    mixture = specimen_genotype_mixture(agent, pathogen_id, profile, registry)
    if not mixture:
        return {}
    emitted = float(agent.get_pathogen_shedding(pathogen_id, dict(profile)))
    if emitted <= 0.0:
        return {}
    return {genotype: emitted * share for genotype, share in mixture.items()}


@dataclass
class RunResult:
    num_epochs: int
    final_trigger_status: str
    history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class _EpochWork:
    """Scratch pad for one ``ShipSimulation.step`` so phase helpers share locals."""

    epoch: int
    state: Any
    cfg: dict[str, Any]
    syndromic: Any
    rdt: Any
    pcr: Any
    seq: Any
    dr: Any
    applied: dict[str, Any]
    epoch_voyage: Any = None
    tracing_matrix: Any = None
    zone_microflora_shifts: dict[str, dict[str, float]] = field(default_factory=dict)
    agents: list[dict[str, Any]] = field(default_factory=list)
    spaces: list[Any] = field(default_factory=list)
    payload: Any = None
    truth: Any = None
    wearable_result: Any = None
    information_state: dict[str, Any] = field(default_factory=dict)
    syn_result: Any = None
    cascade_result: Any = None
    rdt_result: Any = None
    pcr_result: Any = None
    seq_result: Any = None
    air_results: Any = None
    swab_results: Any = None
    ww_results: Any = None
    clin_rdt_results: Any = None
    clin_qpcr_results: Any = None
    clin_microbio_results: Any = None
    long_read_results: Any = None
    long_read_ordered_count: int = 0
    prev_status: str = ""
    stoplights: dict[str, Any] = field(default_factory=dict)
    active_mods: Any = None
    merged_mods: Any = None
    counter_results: Any = None
    epoch_record: dict[str, Any] = field(default_factory=dict)


def _merge_applied(current: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    if not extra:
        return current
    return extra if not current else {**current, **extra}


def _beliefs_from_information(information_state: dict[str, Any]) -> dict[int, dict[str, float]]:
    beliefs: dict[int, dict[str, float]] = {}
    agent_inf = information_state.get("agents", information_state)
    if not isinstance(agent_inf, dict):
        return beliefs
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
    return beliefs


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
        self.wastewater_sampler: WastewaterOpsSampler | None = None
        self._wastewater_routing: dict[str, str] = {}
        self.surface_recovery_config: SurfaceRecoveryConfig | None = None
        self.surface_recovery_rng: np.random.Generator | None = None
        self.scenario_schedule = ScenarioSchedule()


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
            clock=self.clock,
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
        ship = initialize_ship_graph(cfg)
        self.zone_names = ship["zone_names"]
        self.high_traffic = ship["high_traffic_zones"]
        self.graph_cfg = cfg.get("ship_graph", {})

        # One clock for the whole run: the itinerary sets the epoch length and
        # the natural history reads it, so the two cannot drift apart.
        self.clock = SimClock.for_run(cfg, voyage_cfg)
        self.scenario_schedule = resolve_scenario_schedule(cfg)
        self.pathogen_profiles = load_pathogen_profiles(cfg)
        self.modalities = build_modalities(
            cfg,
            self.rng,
            total_epochs=self.num_epochs,
            clock=self.clock,
            pathogen_profiles=self.pathogen_profiles,
        )
        self.engine = build_engine(cfg, seed=self.seed, clock=self.clock)
        if self.display:
            from orchestrator_display import print_korkin_engine
            print_korkin_engine(self.engine)

        assign_cabin_mates(self.engine.agents, ship["zones"])

        self.contam_engine = build_transport_engine(
            self.repo_root, cfg, clock=self.clock,
        )
        if self.contam_engine is not None:
            self.engine.enable_external_transport()
        if self.display:
            from orchestrator_display import print_contam_engine
            print_contam_engine(self.contam_engine, self.engine, cfg)

        self.mp_cfg = cfg.get("multi_pathogen", {})
        self.mf_cfg = cfg.get("microflora", {})
        self.enable_dual_signal = self.mf_cfg.get("enable_dual_signal", True)
        init_multi_pathogen(self.engine, self.pathogen_profiles, cfg, self.rng)

        if self.display:
            from orchestrator_display import print_multi_pathogen
            print_multi_pathogen(
                self.pathogen_profiles, set(), self.engine, self.enable_dual_signal,
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
        if self.tx_core is not None:
            self.tx_core.register_seeded_founders(self.engine.agents)

        self.obs = init_observation_engine(
            cfg,
            self.seed,
            pathogen_profiles=self.pathogen_profiles,
            clock=self.clock,
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

        cascade_engine = build_cascade_engine(
            cfg, repo_root=self.repo_root, clock=self.clock,
        )
        sim_state = SimulationState(
            isolation_unit_capacity=load_isolation_unit_capacity(cfg),
            cascade_engine=cascade_engine,
            chronic_assignments=self.chronic_assignments,
            chronic_behavioral_mods=self.chronic_behavioral_mods,
            voyage_config=voyage_cfg,
        )
        self.state = sim_state
        self._init_sentinel_ledger(voyage_cfg)
        self._init_wastewater_ops(voyage_cfg)
        self._init_surface_strain_recovery()
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

    def _init_wastewater_ops(self, voyage_cfg: dict[str, Any] | None) -> None:
        """Arm shipboard wastewater sampling when the run asks for the channel.

        Tied to the sentinel ledger: the samples exist to be written into the
        observation bundle, so a run that collects no bundle draws no samples.
        """
        if self.sentinel_ledger is None:
            return
        config = WastewaterOpsConfig.from_mapping(self.cfg.get("wastewater_surveillance"))
        if not config.enabled:
            return
        voyage = (voyage_cfg or {}).get("voyage") or {}
        self.wastewater_sampler = WastewaterOpsSampler(
            config,
            epoch_duration_hours=float(voyage.get("epoch_duration_hours", 1) or 1),
            rng=np.random.default_rng(int(self.seed) + _WASTEWATER_SEED_OFFSET),
        )
        self._wastewater_routing = assign_collection_points(
            self.zone_names, config.collection_points,
        )

    def _init_surface_strain_recovery(self) -> None:
        """Arm surface lineage recovery when configured and strains are tracked.

        Surface recovery reads the PR-4 reservoir composition after the swab
        instrument has drawn its sample, so the disabled channel adds no draws
        to the transmission or existing swab streams.
        """
        if self.tx_core is None or self.tx_core.strain_registry is None:
            return
        variant_cfg = self.cfg.get("variant_surveillance", {}) or {}
        config = SurfaceRecoveryConfig.from_mapping(
            variant_cfg.get("surface_sampling"),
        )
        if not config.enabled:
            return
        self.surface_recovery_config = config
        self.surface_recovery_rng = np.random.default_rng(
            int(self.seed) + _SURFACE_RECOVERY_SEED_OFFSET,
        )

    def _observe_wastewater(self, epoch: int) -> None:
        """Mix this epoch's shedder prevalence into the holding tanks.

        Agents ashore are excluded: they are not using the ship's plumbing, so
        counting them would dilute the very port-call epochs the channel is
        supposed to inform.
        """
        sampler = self.wastewater_sampler
        if sampler is None or self.engine is None:
            return
        pathogen_id = sampler.config.pathogen_id
        fallback = sampler.config.collection_points[0]
        registry = self._wastewater_strain_registry()
        profile = (self.pathogen_profiles or {}).get(pathogen_id) or {}
        aboard: dict[str, float] = {}
        shedders: dict[str, float] = {}
        composition: dict[str, dict[str, float]] = {}
        for agent in self.engine.agents:
            if agent.ashore:
                continue
            point = self._wastewater_routing.get(agent.home_zone, fallback)
            aboard[point] = aboard.get(point, 0.0) + 1.0
            if not _agent_is_shedding(agent, pathogen_id):
                continue
            shedders[point] = shedders.get(point, 0.0) + 1.0
            if registry is None:
                continue
            tap = composition.setdefault(point, {})
            for genotype, mass in _agent_wastewater_lineages(
                agent, pathogen_id, profile, registry,
            ).items():
                tap[genotype] = tap.get(genotype, 0.0) + mass
        sampler.observe_epoch(
            epoch,
            shedders_by_point=shedders,
            population_by_point=aboard,
            composition_by_point=composition,
        )

    def _wastewater_strain_registry(self) -> Any | None:
        """Strain registry the wastewater channel deconvolves against, if any.

        ``None`` when strains are untracked or deconvolution is not configured:
        without a registry there are no lineages in the tank, and the pathogen
        call is the whole result.
        """
        sampler = self.wastewater_sampler
        if sampler is None or not sampler.config.strain_deconvolution.enabled:
            return None
        if self.tx_core is None or not sampler.config.pathogen_id:
            return None
        return self.tx_core.strain_registry

    def _sentinel_port_id(self, port_name: str) -> str:
        """Configured ``port_id`` for a port name, or a slug of it."""
        from picard_framework.analysis.sentinel.itinerary import slugify_port

        if not port_name:
            return ""
        return self._sentinel_port_ids.get(port_name) or slugify_port(port_name)

    def _note_shore_introductions(
        self,
        introductions: list[dict[str, Any]],
    ) -> None:
        """Record port-acquired infections as validation ground truth."""
        ledger = self.sentinel_ledger
        if ledger is None:
            return
        for rec in introductions:
            ledger.note_introduction(
                person_id=str(rec["agent_id"]),
                epoch=int(rec["epoch"]),
                port_id=self._sentinel_port_id(str(rec.get("port") or "")),
                pathogen=rec.get("pathogen"),
            )

    def _channel_ids(self, values: Any) -> list[int]:
        return [int(agent) for agent in values or []]

    def _sentinel_detections(
        self,
        syn_result: dict[str, Any] | None,
        cascade_result: dict[str, Any] | None,
        wearable_result: dict[str, Any] | None,
    ) -> dict[str, list[int]]:
        syn = syn_result or {}
        screening = self._channel_ids(syn.get("crew_screening_ids"))
        screening_set = set(screening)
        cascade = cascade_result or {}
        channels = {
            "sick_call": [
                agent
                for agent in self._channel_ids(syn.get("sick_call_agents"))
                if agent not in screening_set
            ],
            "screening": screening,
            "cascade": [
                int(agent)
                for key in ("new_tier0_agents", "new_tier1_agents")
                for agent in cascade.get(key) or []
            ],
            "wearable": self._channel_ids(
                (wearable_result or {}).get("staff_visible_agents"),
            ),
        }
        return {name: ids for name, ids in channels.items() if ids}

    def _observe_sentinel(
        self,
        epoch: int,
        agents: list[dict[str, Any]],
        syn_result: dict[str, Any] | None,
        cascade_result: dict[str, Any] | None,
        wearable_result: dict[str, Any] | None,
        long_read_results: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Fold this epoch's per-person state into the sentinel ledger."""
        ledger = self.sentinel_ledger
        if ledger is None or self.engine is None:
            return
        epoch_voyage = self.state.epoch_voyage if self.state else None
        port_name = str(epoch_voyage.port or "") if epoch_voyage else ""
        ledger.observe_epoch(
            epoch,
            agents,
            port_id=self._sentinel_port_id(port_name),
            ashore_ids=[a.agent_id for a in self.engine.agents if a.ashore],
            detections=self._sentinel_detections(
                syn_result, cascade_result, wearable_result,
            ),
            genotypes=typed_genotypes(long_read_results),
        )
        self._observe_wastewater(epoch)

    def _write_sentinel_line_list(self) -> None:
        """Write the sentinel observation bundle, if one was collected."""
        ledger = self.sentinel_ledger
        paths = self.run_spec.telemetry
        if ledger is None or paths is None or not paths.sentinel_line_list:
            return
        from picard_framework.analysis._io import safe_path, write_json

        agents = self.engine.agents if self.engine else []
        n_crew = sum(1 for a in agents if a.role == "crew")
        sampler = self.wastewater_sampler
        payload = ledger.to_payload(
            voyage_id=str(self.cfg.get("voyage_id") or f"seed{self.seed}"),
            ship_id=self.run_spec.platform_id,
            n_passengers=len(agents) - n_crew,
            n_crew=n_crew,
            platform_class=self.run_spec.platform_id,
            observation_end_epoch=max(self._epoch, 1),
            wastewater_samples=() if sampler is None else sampler.samples(),
        )
        write_json(safe_path(paths.sentinel_line_list), payload)

    def _write_lineage_census(self) -> None:
        """Write the run's lineage census artifact, if one was asked for.

        The phylodynamic truth channel, and the reason it is its own file: the
        per-epoch census is attached to the epoch record, which a ``compact``
        campaign run never persists, so at campaign scale the observed lineages
        had nothing to be compared against. Carries the clock with it, because
        every phylodynamic observable is a rate per physical hour.
        """
        paths = self.run_spec.telemetry
        registry = None if self.tx_core is None else self.tx_core.strain_registry
        if paths is None or not paths.lineage_census or registry is None:
            return
        from picard_framework.analysis._io import safe_path, write_json
        from picard_framework.analysis.phylodynamics.artifact import (
            LINEAGE_CENSUS_SCHEMA_VERSION,
        )

        clock = self.clock
        payload = {
            "schema_version": LINEAGE_CENSUS_SCHEMA_VERSION,
            "voyage_id": str(self.cfg.get("voyage_id") or f"seed{self.seed}"),
            "ship_id": self.run_spec.platform_id,
            "random_seed": self.seed,
            "num_epochs": self.num_epochs,
            "observation_end_epoch": max(self._epoch, 1),
            "epoch_duration_hours": clock.hours_per_epoch,
            "natural_history_clock": clock.mode,
            **registry.to_telemetry(),
        }
        write_json(safe_path(paths.lineage_census), payload)

    def step(self, actions: ActionEnvelope | None = None) -> StepResult:
        work = self._begin_epoch(actions)
        self._step_biology(work)
        self._step_export_truth(work)
        self._step_information(work)
        self._step_surveillance(work)
        self._step_labs(work)
        self._step_escalation(work)
        self._step_command(work)
        self._step_protocols(work)
        self._step_record(work)
        return StepResult(
            epoch=work.epoch,
            trigger_status=work.state.trigger_status,
            stoplights=work.stoplights,
            epoch_record=work.epoch_record,
            ground_truth=work.payload,
            active_protocols=work.active_mods,
            merged_modifiers=work.merged_mods,
            decisions=work.applied,
        )

    def _begin_epoch(self, actions: ActionEnvelope | None) -> _EpochWork:
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
        dr = self.decision_runtime
        state.agent_behavioral_overrides.clear()
        cfg.pop("_picard_epoch_overrides", None)
        if dr is not None:
            dr.decision_ctx.reset_ephemeral()

        applied = apply_action_envelope(
            actions,
            state,
            cfg,
            decision_ctx=dr.decision_ctx if dr else None,
            valid_zones=set(self.zone_names),
        )
        self.scenario_schedule.apply(epoch, self.clock, state.forced_protocol_ids)
        fred_agents = [
            {
                "agent_id": a.agent_id,
                "agent_class": a.agent_class,
                "symptom_presentation": (
                    "symptomatic" if a.is_symptomatic else "asymptomatic"
                ),
            }
            for a in self.engine.agents
        ]
        step_fred_compliance(epoch, state, syndromic, agents=fred_agents)
        step_mid_cruise_introductions(
            epoch, self.engine, self.pathogen_profiles, self.rng,
        )

        from engines.voyage_itinerary import resolve_epoch_state

        epoch_voyage = resolve_epoch_state(state.voyage_config, epoch)
        state.epoch_voyage = epoch_voyage
        self.engine.voyage_epoch_state = epoch_voyage
        self.tx_core.voyage_contact_multiplier = (
            float(epoch_voyage.contact_multiplier)
            if epoch_voyage.effects_active
            else 1.0
        )
        return _EpochWork(
            epoch=epoch,
            state=state,
            cfg=cfg,
            syndromic=syndromic,
            rdt=self.modalities["clinical_rdt"],
            pcr=self.modalities["targeted_pcr"],
            seq=self.modalities["sequencing"],
            dr=dr,
            applied=applied,
            epoch_voyage=epoch_voyage,
        )

    def _step_biology(self, work: _EpochWork) -> None:
        assert self.engine is not None
        assert self.tx_core is not None
        state = work.state
        self.engine.isolated_ids = set(state.isolated_ids)
        self.engine.quarantined_ids = set(state.quarantined_ids)
        self.engine.vsp_reported_case_fraction = state.vsp_reported_case_fraction
        self.engine.step()
        self._note_shore_introductions(
            step_shore_introductions(
                work.epoch,
                self.engine,
                self.pathogen_profiles,
                self.rng,
                work.epoch_voyage,
            ),
        )
        step_infection_progression(
            self.engine,
            self.pathogen_profiles,
            self.tx_core.strain_registry,
            work.epoch,
            self.tx_core,
        )
        work.tracing_matrix, _tx_events = self.tx_core.execute_transmission(
            epoch=work.epoch,
            agents=self.engine.agents,
            zone_pathogen_mass=self.engine.zone_pathogen_mass,
            hvac_downstream_zones=self.hvac_downstream,
            multi_pathogen_mass=(
                self.engine.multi_pathogen_mass if self.pathogen_profiles else None
            ),
            quarantined_ids=set(state.quarantined_ids),
        )
        if self.contam_engine is not None:
            self.engine.zone_pathogen_mass = self.contam_engine.transport_step(
                self.engine.zone_pathogen_mass,
            )
        if self.pathogen_profiles and self.enable_dual_signal:
            work.zone_microflora_shifts = compute_zone_microflora_shifts(
                self.engine.agents, self.pathogen_profiles, work.cfg,
            )

    def _step_export_truth(self, work: _EpochWork) -> None:
        assert self.engine is not None
        engine_payload = self.engine._export_payload()
        work.agents, work.spaces = engine_payload_to_schema(
            engine_payload,
            work.state.isolated_ids,
            work.state.quarantined_ids,
            work.state.quarantine_refusers,
            pathogen_profiles=self.pathogen_profiles,
        )
        if self.chronic_assignments:
            apply_chronic_severity_escalation(work.agents, self.engine, self.rng)
        work.payload = make_ground_truth(
            epoch=work.epoch, agents=work.agents, spaces=work.spaces,
        )
        gt_path = self.run_spec.telemetry.ground_truth if self.run_spec.telemetry else None
        if not self.run_spec.write_ground_truth:
            work.truth = work.payload
        elif gt_path:
            write_ground_truth(work.payload, path=gt_path)
            work.truth = read_ground_truth(path=gt_path)
            assert work.truth is not work.payload, "Shared-memory leak!"
        else:
            write_ground_truth(work.payload)
            work.truth = read_ground_truth()
            assert work.truth is not work.payload, "Shared-memory leak!"
        work.wearable_result = step_wearable_monitoring(
            work.epoch, self.engine, self.wearable_monitor, self.wearable_modality,
            work.truth, self.pathogen_profiles,
        )

    def _step_information(self, work: _EpochWork) -> None:
        dr = work.dr
        if dr is None:
            return
        dr.contact_graph.update(
            work.agents, work.tracing_matrix.to_dict(), dr.class_matrix,
        )
        conf_rate = len(work.state.quarantined_ids) / max(1, len(work.agents))
        agent_classes = {
            int(a["agent_id"]): a.get("agent_class", "unknown") for a in work.agents
        }
        work.information_state = dr.information_engine.step(
            dr.contact_graph.agent_adjacency,
            agent_classes,
            work.state.trigger_status,
            conf_rate,
        )
        if dr.stackelberg is None:
            return
        pop_applied = apply_action_envelope(
            dr.stackelberg.solve_population(
                work.epoch,
                {
                    "epoch": work.epoch,
                    "agents": work.agents,
                    "summary": self._build_summary(work.agents, syn_result=None),
                    "trigger_status": work.state.trigger_status,
                    "high_traffic_zones": self.high_traffic,
                },
                work.information_state,
                self.decision_experience,
            ),
            work.state,
            work.cfg,
            dr.decision_ctx,
            set(self.zone_names),
        )
        work.applied = _merge_applied(work.applied, pop_applied)

    def _step_surveillance(self, work: _EpochWork) -> None:
        from crusher_labs.clinical_presentation import apply_noise_syndromes_to_agents

        beliefs = _beliefs_from_information(work.information_state)
        if surveillance_is_active(work.epoch, work.cfg, self.clock):
            work.syn_result = work.syndromic.query_ground_truth(
                work.truth,
                behavioral_overrides=work.state.agent_behavioral_overrides,
                information_beliefs=beliefs,
                chronic_behavioral_mods=self.chronic_behavioral_mods,
                include_episode_telemetry=(
                    work.epoch + 1 >= self.num_epochs
                ),
                # Surveillance runs before escalation, so this is the prior
                # epoch's recognition state by design.
                outbreak_recognized=(
                    STATUS_RANK.get(work.state.trigger_status, 0)
                    >= STATUS_RANK[STATUS_SUSPECTED]
                ),
            )
            work.cascade_result = step_diagnostic_cascade(
                work.epoch, work.state, work.agents, work.syn_result,
                work.wearable_result, self.obs,
                wearable_monitor=self.wearable_monitor,
                syndromic=work.syndromic,
                cfg=work.cfg,
                clock=self.clock,
            )
        else:
            work.syn_result = inactive_syndromic_result(
                work.epoch, n_agents=len(work.agents),
            )
            work.cascade_result = None
        apply_noise_syndromes_to_agents(
            work.agents,
            work.syn_result,
            work.cfg.get("fred_behavior", {}).get("healthy_noise_categories"),
        )
        step_cascade_cost_accounting(work.epoch, self.proto_ctx, work.cascade_result)
        work.rdt_result = work.rdt.query_ground_truth(
            work.truth, sick_call_ids=work.syn_result["sick_call_agents"],
        )
        if work.dr is not None:
            work.dr.lived_store.update(
                work.epoch, work.agents, work.syn_result,
                [], work.state.quarantined_ids, work.state.isolated_ids,
                work.dr.contact_graph.agent_adjacency,
                work.wearable_result, work.dr.profiles,
            )
        if work.syn_result is None:
            return
        update_ever_reported_ids(
            work.agents,
            work.syn_result,
            work.state.ever_reported_ids,
            work.state.ever_reported_noise_ids,
        )
        reported_rates = compute_group_rates_for_ids(
            work.agents, work.state.ever_reported_ids,
        )
        work.state.vsp_reported_case_fraction = reported_rates["passenger"]

    def _query_pcr_seq(self, work: _EpochWork) -> None:
        overrides = work.cfg.get("_picard_epoch_overrides", {})
        pcr_cadence = overrides.get(
            "pcr_cadence", work.cfg.get("targeted_pcr", {}).get("cadence", 4),
        )
        seq_cadence = overrides.get(
            "sequencing_cadence", work.cfg.get("sequencing", {}).get("cadence", 8),
        )
        verify_zones = [
            str(q["zone"]) for q in work.state.verification_test_queue
            if int(q.get("epoch", 0)) <= work.epoch
        ]
        work.state.verification_test_queue = [
            q for q in work.state.verification_test_queue
            if int(q.get("epoch", 0)) > work.epoch
        ]
        if not work.cfg.get("observation", {}).get("enabled", True):
            return
        status_rank = STATUS_RANK.get(work.state.trigger_status, 0)
        if status_rank >= STATUS_RANK[STATUS_CONFIRMED]:
            wipe = list(dict.fromkeys(self.zone_names + verify_zones))
            work.pcr_result = work.pcr.query_ground_truth(
                work.truth, surface_wipe_zones=wipe,
            )
        elif status_rank >= STATUS_RANK[STATUS_ALERT]:
            wipe = list(dict.fromkeys(self.high_traffic + verify_zones))
            work.pcr_result = work.pcr.query_ground_truth(
                work.truth, surface_wipe_zones=wipe,
            )
        elif work.epoch % int(pcr_cadence) == 0:
            if verify_zones:
                work.pcr_result = work.pcr.query_ground_truth(
                    work.truth, surface_wipe_zones=verify_zones,
                )
            else:
                work.pcr_result = work.pcr.query_ground_truth(work.truth)
        if work.epoch % int(seq_cadence) == 0:
            work.seq_result = work.seq.query_ground_truth(
                work.truth, zone_microflora_shifts=work.zone_microflora_shifts,
            )

    def _step_labs(self, work: _EpochWork) -> None:
        self._query_pcr_seq(work)
        (
            work.air_results, work.swab_results, work.ww_results,
            work.clin_rdt_results, work.clin_qpcr_results, work.clin_microbio_results,
            work.long_read_results, work.long_read_ordered_count,
        ) = run_observation_sampling(
            work.epoch, self.obs, work.agents, work.spaces, self.zone_names,
            self.zone_volumes, work.zone_microflora_shifts,
            work.state.trigger_status, self.high_traffic, work.syn_result,
            self.engine, self.pathogen_profiles, work.cfg,
            strain_registry=(
                None if self.tx_core is None else self.tx_core.strain_registry
            ),
        )
        self._attach_surface_strain_recovery(work)

    def _recover_zone_surface_strains(
        self,
        work: _EpochWork,
        zone_name: str,
        swab: dict[str, Any],
    ) -> None:
        recovered_mass = float(swab.get("recovered_mass", 0.0))
        aggregate = float(self.tx_core.surface_pools.get(zone_name, 0.0))
        if recovered_mass <= 0.0 or aggregate <= 0.0:
            return
        by_pathogen: dict[str, dict[str, float]] = {}
        for pathogen_id in self.pathogen_profiles:
            mixture_row = self._recover_pathogen_surface_mixture(
                work, zone_name, pathogen_id, recovered_mass, aggregate,
            )
            if mixture_row is not None:
                by_pathogen[pathogen_id] = mixture_row
        if by_pathogen:
            swab["strain_recovery"] = by_pathogen

    def _recover_pathogen_surface_mixture(
        self,
        work: _EpochWork,
        zone_name: str,
        pathogen_id: str,
        recovered_mass: float,
        aggregate: float,
    ) -> dict[str, float] | None:
        composition = self.tx_core.surface_lineage_masses(
            pathogen_id, zone_name,
        )
        pathogen_mass = sum(composition.values())
        if pathogen_mass <= 0.0:
            return None
        epochs = self.tx_core.surface_epochs_since_deposition(
            pathogen_id, zone_name, work.epoch,
        )
        if not composition or epochs is None:
            return None
        pathogen_share = min(pathogen_mass / aggregate, 1.0)
        sampled = recovered_mass * pathogen_share
        mixture = recover_surface_mixture(
            sampled,
            composition,
            surface_type=self.zone_types.get(zone_name, ""),
            epochs_since_deposition=epochs,
            config=self.surface_recovery_config,
            rng=self.surface_recovery_rng,
            clock=self.clock,
        )
        return mixture.as_row()

    def _attach_surface_strain_recovery(self, work: _EpochWork) -> None:
        """Attach conserved lineage payloads without changing swab fields."""
        if (
            self.surface_recovery_config is None
            or self.surface_recovery_rng is None
            or self.tx_core is None
        ):
            return
        for zone_name, swab in work.swab_results.items():
            self._recover_zone_surface_strains(work, zone_name, swab)

    def _log_pending_escalation(
        self,
        work: _EpochWork,
        prev_status: str,
        new_pending: dict[str, Any] | None,
    ) -> None:
        if new_pending is None or prev_status != work.state.trigger_status:
            return
        pending_to = new_pending.get("to")
        already = any(
            e.get("pending_to") == pending_to
            and e.get("epoch_triggered") == new_pending.get("epoch_triggered")
            for e in work.state.escalation_log
        )
        if already:
            return
        work.state.escalation_log.append({
            "epoch": work.epoch,
            "from": work.state.trigger_status,
            "to": pending_to,
            "pending": True,
            "pending_to": pending_to,
            "epoch_triggered": new_pending.get("epoch_triggered"),
        })

    def _step_escalation(self, work: _EpochWork) -> None:
        update_ever_infected_ids(work.agents, work.state.ever_infected_ids)
        n_confirmed = update_cumulative_confirmed_cases(
            work.clin_qpcr_results, work.clin_rdt_results,
            work.state.cumulative_confirmed_case_ids,
        )
        work.prev_status = work.state.trigger_status
        new_status, new_pending, _rates = check_escalation(
            work.state.trigger_status, work.syn_result, work.pcr_result, work.cfg,
            agents=work.agents,
            ever_ill_ids=work.state.ever_ill_ids,
            cumulative_confirmed_cases=n_confirmed,
            epoch=work.epoch,
            escalation_pending=work.state.escalation_pending,
            respiratory_mode=pathogen_profiles_are_respiratory(self.pathogen_profiles),
            clock=self.clock,
        )
        work.state.escalation_pending = new_pending
        work.state.trigger_status = new_status
        if work.state.trigger_status != work.prev_status:
            work.state.escalation_log.append({
                "epoch": work.epoch,
                "from": work.prev_status,
                "to": work.state.trigger_status,
            })
            if self.obs.lab_notebook_enabled:
                self.obs.notebook.log_trigger_transition(
                    work.epoch, work.prev_status, work.state.trigger_status,
                )
        else:
            self._log_pending_escalation(work, work.prev_status, new_pending)
        work.stoplights = compute_stoplights(
            work.air_results, work.swab_results, work.ww_results,
            work.clin_rdt_results, work.clin_qpcr_results, work.clin_microbio_results,
            wearable_result=work.wearable_result,
            syndromic_result=work.syn_result,
            long_read_results=work.long_read_results,
            cfg=work.cfg,
        )

    def _step_command(self, work: _EpochWork) -> None:
        dr = work.dr
        if dr is None:
            return
        for msg in dr.decision_ctx.sop_announcements + dr.lived_store.sop_announcements:
            dr.information_engine.seed_public_message(msg)
        dr.information_engine.reputation.on_corporate_stance(
            dr.decision_ctx.corporate_communication_stance,
        )
        if dr.stackelberg is None:
            return
        eligible = eligible_protocol_ids(
            self.proto_ctx.standing_protocols, work.stoplights,
            trigger_status=work.state.trigger_status,
        )
        cmd_applied = apply_action_envelope(
            dr.stackelberg.solve_command_medical(
                work.epoch,
                {
                    "epoch": work.epoch,
                    "agents": work.agents,
                    "trigger_status": work.state.trigger_status,
                    "summary": self._build_summary(work.agents, work.syn_result),
                    "reactive_protocols": {"stoplights": work.stoplights},
                    "observation_engine": {
                        "air_sniffer": work.air_results,
                        "surface_swab": work.swab_results,
                    },
                    "cost_accounting": {
                        "operational_impact_cumulative": (
                            self.proto_ctx.cost_ledger.operational_impact_cumulative
                        ),
                    },
                    "high_traffic_zones": self.high_traffic,
                },
                dr.decision_ctx,
                dr.lived_store,
                work.information_state,
                dr.information_engine.reputation,
                dr.global_health_timeline,
                self.decision_experience,
                eligible,
            ),
            work.state,
            work.cfg,
            dr.decision_ctx,
            set(self.zone_names),
        )
        work.applied = _merge_applied(work.applied, cmd_applied)

    def _authorized_sop_ids(self, work: _EpochWork) -> list[str] | None:
        """Command's SOP authorization, with the scenario calendar's entries added.

        A scheduled protocol replays something that historically happened; it
        is an event fact, not a proposal the simulated command may decline.
        """
        authorized = work.dr.decision_ctx.authorized_sop_ids if work.dr else None
        if authorized is None:
            return None
        scheduled = self.scenario_schedule.protocol_ids & work.state.forced_protocol_ids
        return list(authorized) + sorted(scheduled - set(authorized))

    def _step_protocols(self, work: _EpochWork) -> None:
        reset_modifiers(
            self.contam_engine, self.tx_core, self.proto_ctx.original_filter_eff,
        )
        authorized = self._authorized_sop_ids(work)
        work.active_mods = self.proto_ctx.protocol_engine.evaluate_epoch(
            work.epoch,
            work.stoplights,
            forced_protocol_ids=work.state.forced_protocol_ids,
            authorized_sop_ids=authorized,
            cascade_context=build_cascade_context(work.state, work.cascade_result),
            trigger_status=work.state.trigger_status,
        )
        if authorized is not None:
            work.active_mods = filter_active_modifiers(work.active_mods, authorized)
        work.merged_mods = self.proto_ctx.protocol_engine.get_merged_modifiers(
            work.active_mods,
        )
        if not work.merged_mods:
            return
        apply_hvac_modifiers(self.contam_engine, work.merged_mods)
        apply_transmission_modifiers(self.tx_core, work.merged_mods)
        if "close_zones" in work.merged_mods:
            apply_zone_closures(self.engine, work.merged_mods["close_zones"])
        if "surface_disinfection_log10_reduction" in work.merged_mods:
            apply_outbreak_surface_disinfection(
                self.tx_core,
                work.merged_mods["surface_disinfection_log10_reduction"],
            )

    def _attach_strain_census(self, work: _EpochWork) -> None:
        """Record this epoch's lineage census, once per tracked pathogen.

        A census, not an event log: a mutating voyage mints a lineage per
        transmission, so the per-epoch carrier counts are what keeps a
        thousand-run campaign's telemetry finite. Absent entirely when strains
        are untracked, so a run without ``variant_surveillance`` writes the
        same record it always did — and it survives ``compact`` retention,
        because the census *is* the aggregate.
        """
        registry = None if self.tx_core is None else self.tx_core.strain_registry
        if registry is None or self.engine is None or not self.tx_core.strain_configs:
            return
        census: list[dict[str, Any]] = []
        for pathogen_id in sorted(self.tx_core.strain_configs):
            counts: dict[str, int] = {}
            for agent in self.engine.agents:
                for strain_id in agent.resident_strains(pathogen_id):
                    counts[strain_id] = counts.get(strain_id, 0) + 1
            snapshot = registry.take_snapshot(work.epoch, pathogen_id, counts)
            census.append(snapshot.to_telemetry())
        work.epoch_record["strain_census"] = census

    def _attach_decision_telemetry(self, work: _EpochWork) -> None:
        dr = work.dr
        if dr is None:
            return
        if self.run_spec.history_retention == "compact":
            dr.capture_sop_events(self.proto_ctx.protocol_engine, work.epoch)
            return
        dr.capture_sop_events(self.proto_ctx.protocol_engine, work.epoch)
        work.epoch_record.setdefault("reactive_protocols", {})["sop_events"] = (
            dr.sop_events_buffer
        )
        work.epoch_record["information_state"] = work.information_state
        if dr.decision_detail_telemetry and work.wearable_result:
            work.epoch_record["wearable_agent_snapshot"] = (
                work.wearable_result.get("agent_results", {})
            )
        for ag in work.epoch_record.get("agents", []):
            pid = dr.profiles.get(int(ag.get("agent_id", -1)))
            if pid:
                ag["profile_id"] = pid.profile_id
        work.epoch_record.setdefault("contact_tracing", {})["agent_adjacency"] = (
            dr.contact_graph.to_dict().get("agent_adjacency", {})
        )

    def _step_record(self, work: _EpochWork) -> None:
        step_cost_accounting(
            work.epoch, self.proto_ctx,
            work.air_results, work.swab_results, work.ww_results,
            work.clin_rdt_results, work.clin_qpcr_results, work.clin_microbio_results,
        )
        step_long_read_cost_accounting(
            work.epoch, self.proto_ctx, work.long_read_ordered_count,
        )
        step_quarantine_confinement(
            work.epoch, work.agents, work.merged_mods, work.state.trigger_status,
            work.state, work.syndromic,
        )
        counter_defs = self.graph_cfg.get("infection_counters", [])
        work.counter_results = compute_infection_counters(
            work.agents,
            counter_defs,
            ever_reported_ids=work.state.ever_reported_ids,
        )
        step_counter_thresholds(
            work.epoch, work.agents, work.counter_results, counter_defs,
            work.state, work.syndromic,
            confinement_enabled=self.graph_cfg.get(
                "counter_confinement_enabled", True,
            ),
        )
        step_operational_impact_accounting(
            work.epoch, work.state, work.agents, work.merged_mods, self.proto_ctx,
            zone_type_by_id=self.zone_types,
        )
        work.state.agent_behavioral_overrides.clear()
        work.epoch_record = record_epoch(
            epoch=work.epoch,
            trigger_status=work.state.trigger_status,
            agents=work.agents,
            spaces=work.spaces,
            engine=self.engine,
            contam_engine=self.contam_engine,
            pathogen_profiles=self.pathogen_profiles,
            zone_names=self.zone_names,
            zone_microflora_shifts=work.zone_microflora_shifts,
            syn_result=work.syn_result,
            rdt_result=work.rdt_result,
            pcr_result=work.pcr_result,
            seq_result=work.seq_result,
            tracing_matrix=work.tracing_matrix,
            state=work.state,
            obs=self.obs,
            active_mods=work.active_mods,
            merged_mods=work.merged_mods,
            stoplights=work.stoplights,
            epoch_cost=self.proto_ctx.cost_ledger.get_epoch_summary(work.epoch),
            cfg=work.cfg,
            air_results=work.air_results,
            swab_results=work.swab_results,
            ww_results=work.ww_results,
            clin_rdt_results=work.clin_rdt_results,
            clin_qpcr_results=work.clin_qpcr_results,
            clin_microbio_results=work.clin_microbio_results,
            wearable_result=work.wearable_result,
            infection_counters=work.counter_results,
            long_read_results=work.long_read_results,
            cascade_result=work.cascade_result,
            history_retention=self.run_spec.history_retention,
            final_epoch=(work.epoch + 1 >= self.num_epochs),
        )
        if work.applied and self.run_spec.history_retention != "compact":
            work.epoch_record["decisions"] = work.applied
        if work.state.epoch_voyage is not None:
            work.epoch_record["voyage_epoch"] = work.state.epoch_voyage.to_telemetry()
        self._attach_decision_telemetry(work)
        self._attach_strain_census(work)
        work.state.simulation_history.append(work.epoch_record)
        self._observe_sentinel(
            work.epoch, work.agents, work.syn_result, work.cascade_result,
            work.wearable_result, work.long_read_results,
        )
        self._epoch = work.epoch
        if not self.display:
            return
        from orchestrator_display import print_progress
        total_spent = (
            self.proto_ctx.cost_ledger.starting_financial_usd
            - self.proto_ctx.cost_ledger.financial_balance
        )
        print_progress(
            work.epoch, self.num_epochs, work.state.trigger_status,
            len(work.active_mods), total_spent, work.prev_status,
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
        counts = {
            "sick_call_count": syn_result.get("sick_call_count", 0) if syn_result else 0,
            "susceptible": 0,
            "infected": 0,
            "recovered": 0,
            "immune": 0,
            "symptomatic": 0,
        }
        for ag in agents:
            inf, _, _ = resolve_agent_axes(ag)
            if inf in counts:
                counts[inf] += 1
            if agent_has_symptomatic_presentation(ag):
                counts["symptomatic"] += 1
        return counts

    def run(self, n_epochs: int | None = None) -> RunResult:
        if not self._initialized:
            self.initialize()
        target = n_epochs if n_epochs is not None else self.num_epochs
        while self._epoch + 1 < target:
            self.step()
        assert self.state is not None
        self._write_sentinel_line_list()
        self._write_lineage_census()
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
        self._write_lineage_census()
