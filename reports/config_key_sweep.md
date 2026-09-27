# config.yaml key sweep

- config leaves examined: **229**
- resolved key reads recorded: **1069**
- consumed by orchestrator_*/crusher_labs/sanity_checker (direct): 83
- consumed via bulk access (`.items()`, splat, model_validate): 41
- consumed only downstream (engines/picard/scripts/tests): 33
- weak evidence (name matches a dict access or model field somewhere): 59
- weakest evidence (name appears only as a bare string literal): 12
- **UNREFERENCED — candidates for removal: 1**

> Report-only. Review `UNREFERENCED` and `indirect-name-match` rows
> before deleting anything; static analysis cannot see keys built
> dynamically (f-strings, getattr) or read by external tooling.

## Unreferenced keys

| key | value | evidence |
|---|---|---|
| `grumb_seeding.kingdoms` | `["Bacteria", "Archaea", "Fungi", "Virus"]` | section read crusher_labs/__init__.py:139 (get); key never |

## Weak-evidence keys (name matches somewhere; path unresolved)

| key | value | evidence |
|---|---|---|
| `agent_behavior.dining_rotation_probability` | `0.0` | engines/infection_dynamics_bridge.py, tests/test_s3776_extracted_helpers.py |
| `agent_behavior.free_zone_rotation_probability` | `0.0` | engines/infection_dynamics_bridge.py |
| `agent_behavior.schedule_jitter_hours.crew` | `1.0` | engines/infection_dynamics_bridge.py, engines/initiation.py, engines/transmission_core.py |
| `agent_behavior.schedule_jitter_hours.passenger` | `2.0` | engines/initiation.py, orchestrator_init.py, orchestrator_record.py |
| `clinical_diagnostics.description` | `"Correlated measurement noise across clinical_rdt, clinical_` | .agents/skills/download-deepwiki/fetch_deepwiki.py, _epoch_timing/time_epochs.py, api/app.py |
| `clinical_rdt.cadence` | `1` | picard_framework/simulation/ship_simulation.py, tests/test_sanity_checker.py |
| `clinical_rdt.description` | `"Rapid Diagnostic Test (antigen lateral-flow)"` | .agents/skills/download-deepwiki/fetch_deepwiki.py, _epoch_timing/time_epochs.py, api/app.py |
| `crew_duty_exclusion.compliance_fraction` | `1.0` | engines/crew_duty_exclusion.py, tests/test_crew_duty_exclusion.py |
| `crew_duty_exclusion.enabled` | `false` | crusher_labs/diagnostic_cascade.py, crusher_labs/long_read_escalation.py, crusher_labs/modalities/long_read_sequencing.py |
| `crew_duty_exclusion.food_employee_symptom_free_hours` | `48` | engines/crew_duty_exclusion.py |
| `crew_duty_exclusion.medical_clearance_delay_hours` | `0` | engines/crew_duty_exclusion.py, tests/test_crew_duty_exclusion.py |
| `crew_duty_exclusion.nonfood_crew_symptom_free_hours` | `24` | engines/crew_duty_exclusion.py |
| `decision_engine.command_threshold.ois_escalation_threshold` | `15.0` | tests/test_decision_engine.py |
| `escalation.decision_latency.alert_delay_hours` | `0` | tests/test_tier_iterators.py |
| `escalation.decision_latency.confirmed_delay_hours` | `0` | tests/test_outbreak_response_architecture.py, tests/test_tier_iterators.py |
| `escalation.decision_latency.lockdown_delay_hours` | `0` | tests/test_tier_iterators.py |
| `long_read_sequencing.description` | `"Oxford Nanopore long-read verification and pathogen typing"` | .agents/skills/download-deepwiki/fetch_deepwiki.py, _epoch_timing/time_epochs.py, api/app.py |
| `long_read_sequencing.escalation_triggers.discordant_modalities` | `true` | crusher_labs/long_read_escalation.py, crusher_labs/modalities/long_read_sequencing.py |
| `long_read_sequencing.escalation_triggers.mixed_infection_suspected` | `true` | crusher_labs/long_read_escalation.py, crusher_labs/modalities/long_read_sequencing.py |
| `long_read_sequencing.escalation_triggers.special_circumstance` | `false` | crusher_labs/long_read_escalation.py |
| `long_read_sequencing.escalation_triggers.unexpected_pathogen` | `true` | crusher_labs/long_read_escalation.py, crusher_labs/modalities/long_read_sequencing.py |
| `long_read_sequencing.special_circumstance_flag` | `false` | crusher_labs/long_read_escalation.py |
| `microflora.enable_dual_signal` | `true` | picard_framework/simulation/ship_simulation.py |
| `multi_pathogen.enable_coinfection` | `true` | tests/test_decision_config_resolution.py |
| `sequencing.cadence` | `4` | picard_framework/simulation/ship_simulation.py, tests/test_sanity_checker.py |
| `sequencing.description` | `"Metagenomic shotgun sequencing of environmental samples"` | .agents/skills/download-deepwiki/fetch_deepwiki.py, _epoch_timing/time_epochs.py, api/app.py |
| `ship_graph.agent_roles.crew_fraction` | `0.3` | engines/infection_dynamics_bridge.py, tests/test_sentinel_attribution.py, tests/test_sentinel_exposure.py |
| `ship_graph.counter_confinement_enabled` | `true` | picard_framework/simulation/ship_simulation.py, tests/test_mega_cruise_campaign.py |
| `syndromic.cadence` | `1` | picard_framework/simulation/ship_simulation.py, tests/test_sanity_checker.py |
| `syndromic.description` | `"Symptom-based screening (fever, GI distress, etc.)"` | .agents/skills/download-deepwiki/fetch_deepwiki.py, _epoch_timing/time_epochs.py, api/app.py |
| `targeted_pcr.cadence` | `4` | picard_framework/simulation/ship_simulation.py, tests/test_sanity_checker.py |
| `targeted_pcr.description` | `"RT-qPCR panel for environmental / surface wipe samples"` | .agents/skills/download-deepwiki/fetch_deepwiki.py, _epoch_timing/time_epochs.py, api/app.py |
| `transmission.activity_contacts.enabled` | `true` | crusher_labs/diagnostic_cascade.py, crusher_labs/long_read_escalation.py, crusher_labs/modalities/long_read_sequencing.py |
| `transmission.surface_cleaning.outbreak_response.by_zone_class.cabin.events_per_day` | `1.0` | engines/transmission_core.py, telemetry_buffer/observation_model/cleaning_schedule_sweep.py, tests/test_hand_occupancy_readout.py |
| `variant_surveillance.surface_sampling.default_recovery` | `0.25` | crusher_labs/modalities/surface_strain_recovery.py |
| `variant_surveillance.surface_sampling.enabled` | `false` | crusher_labs/diagnostic_cascade.py, crusher_labs/long_read_escalation.py, crusher_labs/modalities/long_read_sequencing.py |
| `variant_surveillance.surface_sampling.min_lineage_abundance` | `0.0` | crusher_labs/modalities/surface_strain_recovery.py |
| `variant_surveillance.surface_sampling.min_lineage_fraction` | `0.02` | crusher_labs/modalities/surface_strain_recovery.py, picard_framework/analysis/sentinel/wastewater_assays.py, tests/test_surface_strain_recovery.py |
| `variant_surveillance.surface_sampling.recovery_by_surface_type.Dining` | `0.75` | tests/test_cabin_corridor_transmission.py, tests/test_clock_units.py |
| `wastewater_sequencing.description` | `"Dirichlet-multinomial metagenomic sampling from wastewater ` | .agents/skills/download-deepwiki/fetch_deepwiki.py, _epoch_timing/time_epochs.py, api/app.py |
| `wastewater_surveillance.assay_mode` | `"metagenomic"` | picard_framework/analysis/sentinel/observations.py, picard_framework/analysis/sentinel/wastewater_ops.py, picard_framework/runs/mega_cruise_campaign/campaign_runner.py |
| `wastewater_surveillance.background_read_fraction` | `0.9999` | picard_framework/analysis/sentinel/wastewater_ops.py |
| `wastewater_surveillance.collection_points` | `["aft_main"]` | picard_framework/analysis/sentinel/wastewater_ops.py, picard_framework/runs/mega_cruise_campaign/campaign_runner.py, tests/test_wastewater_assay_modes.py |
| `wastewater_surveillance.enabled` | `false` | crusher_labs/diagnostic_cascade.py, crusher_labs/long_read_escalation.py, crusher_labs/modalities/long_read_sequencing.py |
| `wastewater_surveillance.holding_tank_residence_hours` | `4.0` | picard_framework/analysis/sentinel/wastewater_ops.py, picard_framework/runs/mega_cruise_campaign/campaign_runner.py, tests/test_wastewater_assay_modes.py |
| `wastewater_surveillance.pathogen` | `"norovirus"` | deploy/aws/boundary_analysis_entrypoint.py, deploy/aws/sentinel_recovery_analysis_entrypoint.py, engines/initiation.py |
| `wastewater_surveillance.pathogen_id` | `"norwalk_gi"` | crusher_labs/diagnostic_cascade.py, crusher_labs/lab_notebook.py, crusher_labs/modalities/clinical_strain_typing.py |
| `wastewater_surveillance.pathogen_shedding_to_reads_scale` | `1.0` | picard_framework/analysis/sentinel/wastewater_ops.py |
| `wastewater_surveillance.sampling_interval_epochs` | `6` | picard_framework/analysis/sentinel/wastewater_ops.py, picard_framework/runs/mega_cruise_campaign/campaign_runner.py, tests/test_wastewater_assay_modes.py |
| `wastewater_surveillance.sequencing_depth` | `250000` | picard_framework/analysis/sentinel/wastewater_assays.py, picard_framework/analysis/sentinel/wastewater_ops.py, picard_framework/runs/mega_cruise_campaign/campaign_runner.py |
| `wastewater_surveillance.strain_deconvolution.dirichlet_concentration` | `200.0` | crusher_labs/__init__.py, crusher_labs/lab_notebook.py, orchestrator_init.py |
| `wastewater_surveillance.strain_deconvolution.enabled` | `false` | crusher_labs/diagnostic_cascade.py, crusher_labs/long_read_escalation.py, crusher_labs/modalities/long_read_sequencing.py |
| `wastewater_surveillance.strain_deconvolution.min_lineage_fraction` | `0.02` | crusher_labs/modalities/surface_strain_recovery.py, picard_framework/analysis/sentinel/wastewater_assays.py, tests/test_surface_strain_recovery.py |
| `wastewater_surveillance.strain_deconvolution.min_lineage_reads` | `20` | picard_framework/analysis/sentinel/wastewater_assays.py, tests/test_wastewater_deconvolution.py |
| `wastewater_surveillance.strain_deconvolution.min_pathogen_reads` | `100` | picard_framework/analysis/sentinel/wastewater_assays.py, tests/test_wastewater_deconvolution.py |
| `wearable_monitoring.anomaly_detection.confounder_match_threshold` | `0.7` | engines/wearable_anomaly_scorer.py, tests/test_wearable_anomaly_scorer.py |
| `wearable_monitoring.anomaly_detection.fleet_anomaly_downweight` | `0.1` | engines/wearable_anomaly_scorer.py, tests/test_wearable_anomaly_scorer.py |
| `wearable_monitoring.anomaly_detection.fleet_anomaly_floor` | `0.15` | engines/wearable_anomaly_scorer.py, tests/test_wearable_anomaly_scorer.py |
| `wearable_monitoring.detection_sensitivity_sweep.enabled` | `false` | crusher_labs/diagnostic_cascade.py, crusher_labs/long_read_escalation.py, crusher_labs/modalities/long_read_sequencing.py |

## Literal-only keys (name appears in a string literal; likely a dynamic-key table — verify before removing)

| key | value | evidence |
|---|---|---|
| `decision_engine.command_threshold.infected_rate_threshold` | `0.05` | decision_engine/policy.py |
| `decision_engine.threshold_belief.hide_severity_ceiling` | `0.25` | decision_engine/policy.py |
| `decision_engine.threshold_belief.hide_trust_ceiling` | `0.35` | decision_engine/policy.py |
| `decision_engine.threshold_belief.severity_report_threshold` | `0.35` | decision_engine/policy.py, tests/test_decision_config_resolution.py |
| `decision_engine.threshold_belief.trust_report_floor` | `0.4` | decision_engine/policy.py, tests/test_decision_config_resolution.py |
| `emod_progression.phase_durations_days` | `[3, 5, 4]` | tools/sanity_checker.py |
| `escalation.decision_latency.suspected_delay_hours` | `0` | orchestrator_init.py, picard_framework/runs/mega_cruise_campaign/tier_iterators.py, tests/test_clock_units.py |
| `variant_surveillance.surface_sampling.recovery_by_surface_type.Cabin_Corridor` | `0.4` | crusher_labs/modalities/surface_strain_recovery.py, engines/infection_dynamics_bridge.py, engines/transmission_core.py |
| `variant_surveillance.surface_sampling.recovery_by_surface_type.Engineering` | `0.6` | crusher_labs/modalities/surface_strain_recovery.py, engines/transmission_core.py, scripts/build_enterprise_platforms.py |
| `variant_surveillance.surface_sampling.recovery_by_surface_type.Free` | `0.25` | crusher_labs/modalities/sequencing.py, crusher_labs/modalities/surface_strain_recovery.py, dashboard/deck_geometry.py |
| `variant_surveillance.surface_sampling.recovery_by_surface_type.Medical` | `0.85` | crusher_labs/modalities/surface_strain_recovery.py, engines/transmission_core.py, scripts/cruise_platform_recipes.py |
| `variant_surveillance.surface_sampling.recovery_by_surface_type.Room` | `0.5` | crusher_labs/modalities/sequencing.py, crusher_labs/modalities/surface_strain_recovery.py, engines/infection_dynamics_bridge.py |

## Keys read only outside orchestrator_*/crusher_labs/sanity_checker

| key | value | evidence |
|---|---|---|
| `decision_engine.command_policy` | `` | decision_engine/policy.py:139 (get) |
| `decision_engine.medical_policy` | `` | decision_engine/policy.py:140 (get) |
| `decision_engine.population_policy` | `` | decision_engine/policy.py:138 (get) |
| `epoch_duration_hours` | `` | engines/sim_clock.py:132 (get) |
| `hvac.contamx.binary_path` | `` | engines/contamx_runner.py:123 (get) |
| `hvac.contamx.prj_path` | `` | tools/contam_outcome_compare.py:75 (subscript) |
| `hvac.pathogen_pool_transport` | `` | tests/test_pathogen_pool_transport.py:56 (subscript) |
| `hvac.transport_engine` | `` | picard_framework/analysis/parse_run_id.py:245 (get) |
| `long_read_sequencing.enabled` | `` | tests/test_sequencing_config.py:64 (subscript) |
| `natural_history_clock` | `` | picard_framework/runs/mega_cruise_campaign/campaign_runner.py:1277 (get) |
| `num_epochs` | `` | picard_framework/run_spec.py:156 (get) |
| `service_surface_knockout.enabled` | `` | engines/transmission_core.py:1792 (get) |
| `ship_graph.air_flow_paths` | `` | picard_framework/run_spec.py:141 (get) |
| `transmission.activity_contacts.rates_per_hour.other` | `` | tests/test_contact_architecture.py:629 (subscript) |
| `transmission.activity_contacts.rates_per_hour.work_service` | `` | tests/test_contact_architecture.py:628 (subscript) |
| `transmission.blackwater_plumbing` | `` | engines/transmission_core.py:1378 (get) |
| `transmission.cabin_air_mode` | `` | engines/transmission_core.py:1261 (get) |
| `transmission.contact_mode` | `` | tests/test_density_contact.py:313 (subscript) |
| `transmission.heterogeneous_zone_dose.default_sigma` | `` | engines/transmission_core.py:1874 (get) |
| `transmission.heterogeneous_zone_dose.sigma_service` | `` | engines/transmission_core.py:1871 (get) |
| `transmission.sanitary_visit_mode` | `` | engines/transmission_core.py:1271 (get) |
| `transmission.surface_cleaning.enabled` | `` | engines/transmission_core.py:1916 (get) |
| `transmission.surface_cleaning.outbreak_response.coverage` | `` | engines/transmission_core.py:1902 (get) |
| `transmission.surface_cleaning.outbreak_response.events_per_day` | `` | engines/transmission_core.py:1909 (get) |
| `transmission.surface_cleaning.outbreak_response.log10_reduction` | `` | engines/transmission_core.py:1928 (get) |
| `transmission.surface_cleaning.routine.coverage` | `` | engines/transmission_core.py:1947 (get) |
| `transmission.surface_cleaning.routine.log10_reduction` | `` | engines/transmission_core.py:1957 (get) |
| `variant_surveillance.census_interval_hours` | `` | tests/test_strain_state.py:475 (subscript) |
| `wearable_monitoring.deployment_profile` | `` | engines/wearable_monitor.py:885 (get) |
| `wearable_monitoring.detection_sensitivity_scale` | `` | tests/test_wearable_enhanced.py:849 (subscript) |
| `wearable_monitoring.detection_sensitivity_sweep.num_epochs` | `` | scripts/wearable_sensitivity_sweep.py:72 (get) |
| `wearable_monitoring.detection_sensitivity_sweep.values` | `` | scripts/wearable_sensitivity_sweep.py:37 (get) |
| `wearable_monitoring.scale_fever_sensitivity` | `` | engines/wearable_monitor.py:1046 (get) |

