# Migration Feasibility Report: Within-Host Integration Seams

> **Status:** Complete — establishment is not a drop-in replacement as written

**Repository examined:** `/workspace/Crusher_to_the_Bridge_canonical`  
**Snapshot identity:** `d557f39f1692f72ff26b67b4074a5ae68e03b4c2`, `branch=main`, from `CANONICAL_SOURCE_SHA.txt`  
**Audit examined:** `/workspace/478cd23a-468e-4074-bc13-d6a5b8938ee3.md`  
**Specification examined:** `/workspace/formal_spec_v1.md`, especially §12  
**Date:** 2026-08-30

## Executive conclusion

The five seams are usable migration boundaries, but §12 understates two compatibility hazards.

1. **Dose delivery, shedding, and immunity are feasible as compatibility-preserving changes** if their current signatures, units, and serialized output remain unchanged.
2. **Establishment is not a drop-in replacement as written.** Current `_establish()` is a side-effecting installer with six effective inputs (`agent`, pathogen, strain, dose, epoch, resident flag), updates strain and legacy state, and returns only whether a new lineage was installed. The proposed `challenge(dose, strain) -> (bool, float)` does not say who owns those side effects, what the float means, or how source attribution, superinfection, and event emission are preserved.
3. **Progression does not currently “emit” a cleared list to its caller.** `_advance_agent_pathogen_infections()` creates a local `cleared` list, passes it to `advance_resident_strains()`, and immediately consumes it in `_record_cleared_immunity()`; it returns `None`. The statement “already does” in §12.1 is therefore only true internally.
4. **The dual state machine has broad reach.** I found 23 production functions/methods directly touching the per-pathogen `infections` container and 24 production functions/methods directly reading or writing the legacy agent-level fields, plus serialized consumers in labs, dashboards, reports, decision logic, and Sentinel exports. A hard removal would break these consumers and many fixtures; a read-only computed projection can preserve them.
5. **Finding 8.3 has no existing regression test.** Only one test function asserts `cumulative_exposure`, and its pool is already zero when recovery is manually forced. Reset-on-recovery changes no current assertion; it requires a new regression test rather than rebaselining an existing expected value.

### Risk and test-impact summary

Counts are **test function definitions**, not parametrized pytest node IDs. I counted a test when its body, or a same-module helper/fixture reachable from it, explicitly references the seam entry point or managed state. This is reproducible static dependency counting, not a claim that every end-to-end test transitively affected by biology has been enumerated.

| Seam | Explicit/helper-transitive tests | Production risk | Would §12 migration break consumers? |
|---|---:|---|---|
| Dose delivery | **47** in 11 files | **Low** | No, because §12 proposes no shape/signature change. Yes if the dictionary stops being populated before dose response or loses susceptibility/route weighting. |
| Establishment | **8** in 3 files for the challenge/dose-response contract | **High** | **Yes if literal.** The proposed two-argument contract omits required context and side effects. |
| Progression | **48** in 8 files | **High** | **Potentially.** Keeping in-place record mutation is compatible; changing return/ownership semantics or dropping projection breaks observation and telemetry. |
| Shedding | **21** in 7 files | **Medium** | No if signature and particles-per-epoch units remain stable. A per-day return or route-shaped return breaks transmission, mass deposition, and wastewater. |
| Immunity | **41** in 5 files | **Medium** | No if `ImmuneRecord`, legacy `immune`, genotype weighting, unnamed-dose denominator, and strain-dose attribution remain stable. |

The establishment count deliberately excludes tests that merely call `infect_with_pathogen()` to construct an infected fixture. Including every such setup would measure fixture prevalence, not the `_establish`/challenge seam. The progression and immunity counts overlap because clearance writes immune memory.

## 1. Seam: dose delivery

### Managed state and code inventory

The seam state is the epoch-local `agent_pathogen_doses: dict[int, dict[str, float]]` at the exit of pathway execution. It is not an agent field and is not serialized.

| File / function | Access | Role |
|---|---|---|
| `engines/transmission_core.py:1429` `TransmissionCore.execute_transmission()` | create, retain alias, read | Creates the dictionary at line 1483, aliases it as `_last_pathogen_doses` at 1488, then reads `(agent_id, pathogen_id)` at 1507 for challenge. |
| `engines/transmission_core.py:1606` `_execute_pathogen_pathways()` | pass-through | Collects direct, droplet, HVAC, fomite, food, and environmental contributions, applies route weights, and passes the accumulator to `_merge_pathogen_doses()`. |
| `engines/transmission_core.py:1579` `_merge_pathogen_doses()` | write | Applies `susceptibility_multiplier`, adds to aggregate `agent_doses`, and writes the per-pathogen value at lines 1602–1603. |
| `engines/transmission_core.py:462` `TransmissionCore.__init__()` | initialize shadow | Initializes `_last_pathogen_doses` (line 486). There is no production reader of this shadow in this snapshot. |
| `tests/test_dose_accumulation.py:63` `_inject_fixed_dose()` | test write | Replaces `_execute_pathogen_pathways()` and directly populates the dictionary to isolate dose-response behavior. |

Pathway-specific helpers write the upstream `p_agent_doses` and `p_agent_pw` inputs through `_accumulate()`; they do not directly access `agent_pathogen_doses`. The merge is therefore the single writer to the seam object in production.

### Downstream consumers

- `execute_transmission()` reads the value for immune scaling, superinfection scaling, cumulative exposure, and dose-response hazard.
- `TransmissionEvent.dose` and `ContactTracingMatrix.transmission_events[*].total_dose` receive the **unprotected pooled dose** (`p_dose`), while the infection record receives cumulative **effective** dose. Dashboard transmission-pathway views consume the tracing/event representation, not `agent_pathogen_doses` itself.
- `_strain_doses` is a strain-resolved shadow assembled by `_fold_strain_doses()`; `_draw_source()` and `_challenge_protection()` rely on it remaining numerically aligned with pooled doses.
- No visualization, report, telemetry, or export module directly reads `agent_pathogen_doses` or `_last_pathogen_doses`.

### Migration assessment

§12 says “no change needed”; that is feasible and **low risk**. Preserve all of these invariants:

1. one value per `(agent_id, pathogen_id)` after route and host-susceptibility scaling;
2. route weights applied before merge;
3. `_strain_doses` and pooled dose on the same scale;
4. public event dose remains the current pre-protection dose;
5. no extra random-number generator (RNG) draws before challenge.

Moving protection or pre-establishment clearance into pathway accumulation would silently change tracing-dose semantics and strain attribution even if infection totals looked plausible.

## 2. Seam: establishment

### Managed state and code inventory

| File / function | Access | State or side effect |
|---|---|---|
| `engines/transmission_core.py:1429` `execute_transmission()` | read/write | Reads dose, protection, resident state and persistent susceptibility; accumulates and resets `agent.cumulative_exposure`; invokes `_establish`; creates `TransmissionEvent` and tracing row. |
| `engines/transmission_core.py:1120` `_dose_response_susceptibility()` | read/write | Lazily writes persistent `agent.dose_response_susceptibility[pathogen_id]`. |
| `engines/transmission_core.py:1139` `_dose_response_hazard()` | read | Calculates `-expm1(-r * effective_dose)`. |
| `engines/transmission_core.py:1071` `_challenge_protection()` | read | Supplies immune scaling before establishment. |
| `engines/transmission_core.py:1149` `_superinfection_susceptibility()` and `:1163` `_superinfection_open()` | read | Gate and scale a resident-host challenge. |
| `engines/transmission_core.py:1173` `_establish()` | write | Clears legacy `immune` on breakthrough, writes legacy `infection_status`, dispatches to new infection or superinfection, and returns whether a new lineage was installed. |
| `engines/infection_dynamics_bridge.py:605` `KorkinAgent.infect_with_pathogen()` | write | Replaces `infections[pathogen_id]`; writes status, illness, clock, inoculum, epoch, shedding multiplier and strain fields; mirrors first active episode to legacy fields. |
| `engines/infection_dynamics_bridge.py:661` `superinfect_with_strain()` | read/write | Absorbs same-lineage dose or adds a `StrainInfection`; intentionally does not restart host illness clock. |
| `engines/infection_dynamics_bridge.py:837` `_write_strain()` | write | Installs primary strain fields and the resident strain dictionary. |
| `orchestrator_epoch.py:237` `step_mid_cruise_introductions()` | write through installer | Alternative establishment entry point, bypassing `TransmissionCore._establish()`. |
| `orchestrator_epoch.py:284` `step_shore_introductions()` | write through installer | Alternative establishment entry point, bypassing `TransmissionCore._establish()`. |
| `orchestrator_init.py:1205` `init_multi_pathogen()` | write through installer | Seeds each configured pathogen, bypassing `TransmissionCore._establish()`. |
| `engines/infection_dynamics_bridge.py:1423`, `:1435`, `:1571` | legacy write | `_seed_initial_infection()`, `_initialize_agents_legacy()`, and legacy internal transmission establish agent-level-only infections without a per-pathogen record. |

### Downstream consumers

The established record is read by:

- progression: `_advance_agent_pathogen_infections()`, incubation/onset helpers, resident-strain clocks;
- shedding and transmission: `get_pathogen_shedding()`, `resident_strains()`, `_get_shedders()`, source attribution, mutation/recombination, extinct-strain collection;
- host effects: `update_microflora_disruption()`, chronic severity lookup, wearable infection response;
- telemetry/export: `KorkinAgent.to_schema_dict()`, `orchestrator_record._multi_pathogen_summary()`, `record_epoch()`, simulation-history JSON;
- observation/labs: clinical presentation, clinical instrument parameter selection, syndromic modality, diagnostic cascade, observation core, long-read sequencing, and lab notebook;
- visualization/reporting: `dashboard.agent_explorer.render_agent_explorer()` and all downstream plots based on serialized `infection_state` / `pathogen_infections`;
- Sentinel export: `picard_framework.analysis.sentinel.line_list.active_pathogen()`;
- wastewater: `picard_framework.simulation.ship_simulation._agent_is_shedding()` and `_agent_wastewater_lineages()`.

### Migration assessment

**High risk.** A literal replacement by `challenge(dose, strain) -> (bool, float)` breaks the call contract and leaves at least these questions unanswered: host/pathogen identity, epoch, profile, RNG, resident/superinfection status, acquired-particle meaning, same-lineage absorption, shedding multiplier, strain phenotype, source attribution, and event ownership.

Use a context-rich result instead, for example a `ChallengeResult` carrying `established`, `effective_dose`, `cumulative_inoculum`, `resident`, `new_lineage`, and strain/source identity, while retaining installation and event emission in an adapter. Route seeding, shore, and mid-cruise introductions through the same installer after the adapter exists; they currently bypass `_establish()`.

## 3. Seam: progression

### Managed state and code inventory

| File / function | Access | Role |
|---|---|---|
| `orchestrator_epoch.py:452` `_advance_agent_pathogen_infections()` | read/write | Iterates active per-pathogen records; increments `time_infected`; triggers onset; writes recovered status/illness; advances strains and records immunity. Returns `None`. |
| `orchestrator_epoch.py:363` `_incubation_days()` and `:391` `_onset_day()` | read/write | Read inoculum/host state, cache `incubation_days`, apply strain modifier. |
| `orchestrator_epoch.py:410` `_draw_symptom_onset()` | write | Writes per-pathogen illness, onset clock, severity, and also writes legacy illness directly. |
| `orchestrator_epoch.py:335` `_record_cleared_immunity()` | write | Converts local cleared strain IDs into `ImmuneRecord` entries. |
| `engines/infection_dynamics_bridge.py:708` `advance_resident_strains()` | read/write | Increments each resident lineage clock, deletes cleared residents, appends IDs to caller-owned list. |
| `orchestrator_epoch.py:500` `_project_legacy_illness()` | read/write | Projects active per-pathogen records onto legacy status/illness/time fields. |
| `orchestrator_epoch.py:533` `step_infection_progression()` | orchestrate | Calls progression, projection, microflora update, and then deposits per-pathogen shedding into zone mass. |
| `engines/infection_dynamics_bridge.py:1526` `_advance_illness_and_recovery()` | read/write legacy | Separate fallback progression for hosts with no records; still increments agent clock for record-carrying hosts. |
| `engines/wearable_monitor.py:159` `_compute_infection_delta()` and `:699` `_apply_detection_profile()` | read | Consume active status, onset/time, and clock. |
| `orchestrator_record.py:46` `_multi_pathogen_summary()` | read | Counts infection and illness states by pathogen. |

### Downstream consumers

Progression fields are serialized by `to_schema_dict()` into `infection_state`, `symptom_presentation`, and `pathogen_infections`. Those are then consumed by:

- **Labs/observation:** `clinical_correlation.run_agent_tests`, `clinical_instrument_params.active_pathogen_ids`, `clinical_presentation.annotate_agent_clinical_presentation`, `diagnostic_cascade._agent_active_pathogen_ids`, syndromic helpers, five `ObservationCore.test_agent()` implementations and associated batch methods, long-read clinical mass, and lab notebook summaries.
- **Visualization:** dashboard agent timeline/explorer, charts, deck geometry, spatial maps, and tactical grid.
- **Reporting/export:** `orchestrator_record.record_epoch`, compact `multi_pathogen` summary, simulation-history JSON, Sentinel line list, and telemetry schema.
- **Decision logic:** lived experience, policy, local views, quarantine requirements, VSP trigger/projection.

### Migration assessment

**High risk**, mostly from state ownership rather than the transition math. Preserve in-place record mutation and serialized field meanings. If the new module must “emit” cleared lineages, make the return explicit (for example `ProgressionResult(cleared=...)`) but keep an adapter that records immunity exactly once. Do not both return and internally consume the same cleared IDs without an idempotence guard.

The spec should correct §12.1: the current implementation has an internal list but does not emit it across the seam.

## 4. Seam: shedding

### Managed state and code inventory

| File / function | Access | Role |
|---|---|---|
| `engines/infection_dynamics_bridge.py:863` `KorkinAgent.get_pathogen_shedding()` | read | Reads per-pathogen status, illness, clocks, curves, host multiplier, strain multiplier and residents; returns particles **per epoch**. |
| `engines/infection_dynamics_bridge.py:904` `strain_shedding_shares()` | read | Produces lineage shares for attribution. |
| `engines/infection_dynamics_bridge.py:934` `_resident_emissions()` and `:977` `_shedding_age()` | read | Partition by inoculum, apply lineage clocks and `clock.amount_per_epoch()`. |
| `engines/infection_dynamics_bridge.py:447` `current_shedding` | read legacy | Legacy single-channel projection; uses agent-level state and the first infection record. |
| `engines/transmission_core.py:2632` `_get_shedders()` | read | Feeds direct/droplet/fomite pathway calculations. |
| `orchestrator_epoch.py:533` `step_infection_progression()` | read/write downstream mass | Deposits shedding into per-pathogen zone mass. |
| `picard_framework/simulation/ship_simulation.py:133` `_agent_wastewater_lineages()` | read | Multiplies genotype shares by emitted shedding. |
| `KorkinAgent.to_schema_dict()` | read legacy | Exports `shedding_rate` from `current_shedding`, not a per-pathogen shedding map. |

### Downstream consumers

Transmission pathways, HVAC/air and surface mass, wastewater concentration and lineage composition, contact/source attribution, telemetry `shedding_rate`, and all analyses based on those exported masses.

### Migration assessment

**Medium risk.** The spec’s clock-scaling constraint is correct but incomplete. Preserve:

- return unit = particles per epoch;
- scalar return and method signature;
- symptomatic/asymptomatic curve selection;
- realized-onset, virtual-onset, and legacy fallback behavior;
- presymptomatic window;
- co-resident inoculum conservation and strain multiplier;
- zero for recovered records.

A route-specific or tissue-specific future return must be introduced under a new API and summed by a compatibility adapter; changing this method to return a mapping would immediately break three production consumers.

## 5. Seam: immunity

### Managed state and code inventory

| File / function | Access | Role |
|---|---|---|
| `engines/transmission_core.py:1071` `_challenge_protection()` | read | Reads legacy `immune`, prior exposures, `_strain_doses`, cross-immunity config and registry; returns weighted protection. |
| `engines/transmission_core.py:974` `_embarkation_genotype()` | read/write adjacent state | Resolves and retains standing genotype in `prior_genotypes`. |
| `engines/transmission_core.py:998` `_resolved_exposure_ages()` | read | Reads `immune_history` for waning/refractory protection. |
| `engines/transmission_core.py:1035` `_prior_exposures()` | read | Combines history, resident genotypes, and embarkation genotype. |
| `engines/infection_dynamics_bridge.py:761` `record_immunity()` | write | Appends an `ImmuneRecord`. |
| `engines/infection_dynamics_bridge.py:770` `immune_genotypes()` | read | Returns distinct resolved genotypes. |
| `orchestrator_epoch.py:335` `_record_cleared_immunity()` | write | Creates records on lineage clearance. |
| `engines/transmission_core.py:1173` `_establish()` | read/write legacy | Clears `agent.immune` on a breakthrough and reopens legacy susceptible state before install. |
| `engines/transmission_core.py:2650` `_get_susceptible()` | read | Excludes legacy immune hosts unless genotype-aware challenge is enabled. |
| `orchestrator_init.py:1205`, `orchestrator_epoch.py:237`, `:284`, `orchestrator_chronic.py:68` | read | Use `immune` to select seeding/introduction/chronic assignment candidates. |

### Downstream consumers

Protection affects effective dose, establishment, strain selection, and transmission events. `immune_genotypes()` also conditions incubation (`prior_immunity`). Legacy `immune` is exported to `infection_state` and is therefore consumed by summaries, dashboard color/state, decision logic, and reports. `ImmuneRecord` itself is not currently exported in the normal agent payload, but its telemetry serialization is tested in the strain-state/history suite.

### Migration assessment

**Medium risk.** The proposed genotype-aware and stable-record constraints are necessary. Also preserve:

1. legacy absolute protection when variant surveillance/cross-immunity is off;
2. refractory-window treatment of unattributed dose;
3. unattributed dose remaining in the weighting denominator;
4. resident lineages counting as priors;
5. duplicate exposure records but distinct-genotype protection semantics;
6. no immunity record for an untracked cleared infection;
7. RNG order for embarkation genotype assignment.

## 6. Finding 8.1: complete dual-state map and minimum unification

### Agent-level state: production read/write map

| File | Functions/methods | Access |
|---|---|---|
| `engines/infection_dynamics_bridge.py` | `KorkinAgent.__init__`, `infect_with_pathogen`, `KorkinShipEngine._seed_initial_infection`, `_initialize_agents_legacy`, `step`, `_advance_illness_and_recovery`, `_draw_fallback_onset` | Direct writers. |
| same | `is_infected`, `is_symptomatic`, `is_recovered`, `days_post_infection`, `current_shedding`, `to_schema_dict`, `KorkinShipEngine._advance_illness_and_recovery`, `_draw_fallback_onset`, `step`, `_check_vsp_trigger`, `get_summary` | Direct/property readers. |
| `engines/transmission_core.py` | `_establish` | Direct writer on immune breakthrough. |
| same | `_get_susceptible` | Direct reader for `_default`/legacy mode. |
| `orchestrator_epoch.py` | `_draw_symptom_onset`, `_project_legacy_illness` | Direct writers; projection also reads prior legacy status. |
| same | `step_mid_cruise_introductions`, `step_shore_introductions` | Direct readers. |
| `orchestrator_init.py` | `init_multi_pathogen` | Direct reader for candidate selection. |
| `tools/contam_outcome_compare.py` | `extract_outcome` | Generic `getattr(..., "infection_status")` reader used by comparison tooling. |

`to_schema_dict()` turns these fields into the serialized `infection_state`, `symptom_presentation`, `days_post_infection`, and `shedding_rate`. Serialized-state readers add 27 functions for `infection_state` and 22 for `symptom_presentation`, across `crusher_labs/`, `dashboard/`, `decision_engine/`, `orchestrator_*`, `telemetry_buffer/`, and `picard_framework/`.

### Per-pathogen state: production read/write map

| File | Functions/methods | Access |
|---|---|---|
| `engines/infection_dynamics_bridge.py` | `__init__`, `infect_with_pathogen`, `superinfect_with_strain`, `_write_strain`, `advance_resident_strains`, `_promote_primary_strain`, `replace_strain` | Writers/mutators. |
| same | `resident_strains`, `is_infected_with`, `strain_id_for`, `assign_strain`, `get_pathogen_shedding`, `strain_shedding_shares`, `current_shedding`, `active_pathogen_ids`, `update_microflora_disruption`, `to_schema_dict`, `_advance_illness_and_recovery` | Readers (some also mutate nested data). |
| `orchestrator_epoch.py` | `_incubation_days`, `_onset_day`, `_draw_symptom_onset`, `_advance_agent_pathogen_infections`, `_project_legacy_illness`, `step_infection_progression` | Read/write progression and projection. |
| `engines/transmission_core.py` | `register_seeded_founders`, `collect_extinct_strains`, `execute_transmission`, `_get_shedders`, `_get_susceptible`, mutation/recombination/source helpers | Read active records and resident strains. |
| `engines/wearable_monitor.py` | `_compute_infection_delta`, `_apply_detection_profile` | Read status and timing. |
| `orchestrator_record.py` | `_multi_pathogen_summary` | Read status and illness. |
| `picard_framework/simulation/ship_simulation.py` | `_agent_is_shedding`, `_agent_wastewater_lineages` | Read active pathogen and shedding. |

The serialized `pathogen_infections` map has 24 production consumer functions. Direct consumers are in `crusher_labs/clinical_correlation.py`, `clinical_instrument_params.py`, `clinical_presentation.py`, `diagnostic_cascade.py`, `lab_notebook.py`, `crusher_labs/modalities/long_read_sequencing.py`, `crusher_labs/modalities/syndromic.py`, `observation_core.py`, `dashboard/agent_explorer.py`, `orchestrator_record.py`, and `picard_framework/analysis/sentinel/line_list.py`.

### Minimum safe change set

A true single source of truth cannot leave legacy-only hosts. The minimum production changes are:

1. **Represent every infection as a record.** Convert `_seed_initial_infection()`, both branches of `_initialize_agents_legacy()`, and legacy internal transmission in `KorkinShipEngine.step()` to call `infect_with_pathogen("_default", ...)` (or the configured default pathogen). This removes agent-level-only infections.
2. **Make the legacy fields computed, read-only projections.** Keep the public names `infection_status`, `illness_status`, and `time_infected` so downstream code does not change. Compute them from all records with the current precedence: any active infection → `INFECTED`; any active symptomatic record → `SYMPTOMATIC`; otherwise records all recovered → `RECOVERED`; no records + `immune` → `IMMUNE`; else `SUSCEPTIBLE`; projected time = maximum active record clock.
3. **Remove direct mirror writes.** Delete legacy writes from `infect_with_pathogen()`, `_establish()`, `_draw_symptom_onset()`, and `_project_legacy_illness()`. Retain `_project_legacy_illness()` temporarily as a compatibility assertion/no-op so call ordering need not change in the first migration.
4. **Delete the fallback state machine only after step 1.** `_advance_illness_and_recovery()` should progress `_default` records or become a compatibility wrapper; it must no longer own separate transitions.
5. **Keep serialization stable.** `to_schema_dict()` and all serialized keys stay unchanged. No dashboard, observation, report, or export consumer then needs a code change.
6. **Provide one mutation API for tests and bootstrap code.** Fixtures should call `infect_with_pathogen()` and mutate `agent.infections[pid]`, not assign projected properties.

This is smaller and safer than updating every reader to traverse `infections`, and it meets §12.3’s requirement to preserve the legacy projection.

## 7. Finding 8.3: cumulative exposure reset impact

### All production accesses

- `KorkinAgent.__init__()` initializes `cumulative_exposure = {}`.
- `TransmissionCore.execute_transmission()` reads the prior value, writes cumulative effective dose, and resets it to `0.0` after successful establishment.
- No telemetry, visualization, reporting, observation, or export consumer reads it.
- There is currently no recovery-path write.

### All test assertions

Only `tests/test_dose_accumulation.py::test_cumulative_inoculum_is_passed_to_infection_and_resets` asserts the field:

- line 177: `~1.0` after one failed challenge;
- line 181: `~0.0` after establishment;
- line 189: `~0.0` after a later establishment.

The test manually changes both per-pathogen and legacy recovery fields at lines 183–185, but at that point cumulative exposure is already zero from establishment. Therefore:

- **Existing assertions requiring updates if reset-on-recovery is added: 0.**
- **Existing test functions that mention the field: 1.**
- **Required new coverage: at least 2 regression cases.**
  1. Put a nonzero pool on a host, execute the real transition to `RECOVERED`, and assert exact zero for that pathogen.
  2. Confirm recovery of pathogen A does not clear pathogen B’s pool.

If SPEC-CLEAR-01 also resets at protection `== 1.0`, add a third test for that branch. A challenge skipped before accumulation currently leaves any prior pool untouched, so this is a separate behavior change from recovery reset.

## 8. Recommended migration order

1. **Add characterization tests and a state invariant checker.** Add recovery-reset, cross-pathogen isolation, protection-equals-one reset, and projection-equals-records tests before changing code.
2. **Fix SPEC-CLEAR-01 on recovery.** Put the reset exactly beside `inf["status"] = RECOVERED` in `_advance_agent_pathogen_infections()`. This is low implementation risk and has no current expected-value rebaseline.
3. **Extract cumulative exposure update with zero-default clearance.** Add `update_cumulative_exposure()` and schema validation for `inoculum_clearance_rate_per_day=0.0`; keep RNG order unchanged. Do not yet replace establishment.
4. **Stabilize dose delivery as a typed adapter.** Characterize pooled-vs-strain dose equality and event-dose semantics. This creates a reliable input boundary for challenge.
5. **Extract challenge calculation but retain the installer.** First separate pure calculation from side-effecting installation; introduce `ChallengeResult`. Keep `_establish()` as an adapter so source attribution, superinfection, and current tests survive.
6. **Unify the state machine behind computed legacy projections.** Convert all legacy-only establishment paths to records, update fixtures, then make projections read-only and retire fallback mutation.
7. **Make progression’s cleared-lineage output explicit.** Only after single-source state is stable; add exactly-once immune-record tests.
8. **Refactor immunity behind its current contract.** Keep genotype/waning behavior and RNG order fixed.
9. **Refactor shedding last.** It has the broadest quantitative downstream effects on transmission, environment, wastewater, and exported trajectories; preserve scalar particles-per-epoch adapter even if richer internal output is added.

## 9. Specific fixtures and tests requiring updates

### For read-only legacy projections

The following fixture helpers directly assign agent-level projection fields and must instead call `infect_with_pathogen()` or mutate a per-pathogen record:

- `tests/test_cabin_corridor_transmission.py:16` `_agent`
- `tests/test_density_contact.py:17` `_agent`
- `tests/test_dose_pathway_invariants.py:49` `_agent`; `:111` `_aging_engine`
- `tests/test_env_pool_strains.py:83` `_agent`
- `tests/test_multi_pathogen_model_phase_a.py:24` `_agent`
- `tests/test_multi_pathogen_model_phase_b.py:16` `_agent`
- `tests/test_shedding_variance_cabin_mates.py:20` `_agent`
- `tests/test_sim_clock.py:530` `_engine_with_a_legacy_only_host` (this test should be removed or recast as a `_default`-record compatibility test)
- `tests/test_strain_dose_ledger.py:55` `_agent`
- `tests/test_surface_strain_recovery.py:61` `_agent`
- `tests/test_zone_contact_summary.py:23` `_agent`

The following test bodies directly assign projected fields and need re-expression through records or need to assert that the properties are read-only:

- `tests/test_dose_accumulation.py:169` `test_cumulative_inoculum_is_passed_to_infection_and_resets`
- `tests/test_immune_waning.py:538`, `:547`, `:558`, `:566` four legacy-projection tests
- `tests/test_phenotype_consumption.py:147` `test_strain_shedding_moves_emitted_dose`
- `tests/test_sim_clock.py:338` `test_downstream_consumers_are_handed_days_not_epoch_counts`
- `tests/test_transmission_infection_expanded.py:249` `test_execute_transmission_with_infected_agent`
- `tests/test_vsp_trigger.py:38`, `:56` both trigger-rule tests

Assignments to `resident_strains(...)[sid].time_infected` in co-infection/history tests are per-lineage state, not legacy projection, and do **not** need updating.

### For the establishment adapter

Update or preserve via compatibility wrapper:

- `tests/test_env_pool_strains.py:398` directly calls private `_establish()` and will fail if the method is removed or its signature changes.
- `tests/test_dose_accumulation.py:63` monkeypatches `_execute_pathogen_pathways()` with the full current positional signature; changing dose seam parameters breaks the fixture.
- `tests/test_dose_accumulation.py:143`, `:169`, `:192` exercise persistent susceptibility, cumulative inoculum transfer/reset, and exponential hazard.
- dashboard pathway tests at `tests/test_dashboard.py:37`, `:58`, `:73`, `:226` consume current event/tracing shapes and must remain unchanged unless export schemas are versioned.

### For progression cleared-output changes

Keep or update the immunity/progression fixtures in `tests/test_immune_history.py`, particularly `test_resolved_infection_leaves_one_record`, `test_coinfected_host_remembers_every_lineage`, `test_lineages_clearing_on_different_days_record_separately`, `test_history_grows_only_with_resolved_exposures`, and `test_repeat_exposure_appends_a_record_per_exposure`. These are the exactly-once guard against double recording.

### For cumulative exposure recovery reset

No current expected value needs updating. Add a new test beside `tests/test_dose_accumulation.py:169`; do not alter its three existing expectations except to stop manually writing read-only legacy projection fields after the state-machine migration.

## Appendix A. Exact seam-dependent test inventories

The lists below use the counting method stated above and may overlap.

### A1. Dose delivery — 47 test functions

- `tests/test_cabin_corridor_transmission.py:85` — `test_confined_shedder_attenuates_shared_droplet_emission`
- `tests/test_cabin_corridor_transmission.py:90` — `test_confined_shedder_preserves_cabin_mate_droplet_dose`
- `tests/test_cabin_corridor_transmission.py:98` — `test_confined_target_receipt_attenuation_is_preserved`
- `tests/test_cabin_corridor_transmission.py:103` — `test_unconfined_shedder_and_confined_cabin_mate_share_full_dose`
- `tests/test_cabin_corridor_transmission.py:115` — `test_confined_shedder_and_confined_cabin_mate_are_not_double_attenuated`
- `tests/test_cabin_corridor_transmission.py:125` — `test_confined_shedder_and_non_mate_target_apply_both_factors`
- `tests/test_cabin_corridor_transmission.py:130` — `test_aerosol_pool_records_attenuated_shared_emission`
- `tests/test_cabin_corridor_transmission.py:135` — `test_shared_droplet_dose_is_monotonic_in_isolation_factor`
- `tests/test_cabin_corridor_transmission.py:157` — `test_droplet_dose_halves_when_zone_volume_doubles`
- `tests/test_cabin_corridor_transmission.py:163` — `test_droplet_dose_does_not_depend_on_susceptible_count`
- `tests/test_cabin_corridor_transmission.py:170` — `test_droplet_dose_scales_with_clock_epoch_duration`
- `tests/test_cabin_corridor_transmission.py:182` — `test_quarantined_agent_receives_reduced_direct_contact`
- `tests/test_cabin_corridor_transmission.py:222` — `test_quarantine_in_non_cabin_zone_unchanged`
- `tests/test_cabin_corridor_transmission.py:249` — `test_quarantined_agent_skips_fomite_pickup`
- `tests/test_cabin_corridor_transmission.py:270` — `test_balcony_ventilation_reduces_droplet_dose`
- `tests/test_cabin_corridor_transmission.py:296` — `test_quarantined_agent_hvac_dose_not_reduced_by_confinement`
- `tests/test_coinfection.py:427` — `test_no_superinfection_at_zero_susceptibility`
- `tests/test_coinfection.py:430` — `test_frequency_rises_with_susceptibility`
- `tests/test_density_contact.py:73` — `test_legacy_contact_mode_unchanged`
- `tests/test_density_contact.py:236` — `test_exponent_sensitivity_changes_r0_draw`
- `tests/test_density_contact.py:332` — `test_heterogeneous_records_exposure_factor`
- `tests/test_density_contact.py:360` — `test_density_mode_omits_exposure_factor`
- `tests/test_density_contact.py:374` — `test_heterogeneous_changes_doses_vs_density`
- `tests/test_density_contact.py:511` — `test_records_sampled_sources_and_contact_count`
- `tests/test_dose_accumulation.py:119` — `test_epoch_invariance_for_one_twenty_four_and_168_slices`
- `tests/test_dose_accumulation.py:133` — `test_single_exposure_matches_beta_poisson_closed_form`
- `tests/test_dose_accumulation.py:169` — `test_cumulative_inoculum_is_passed_to_infection_and_resets`
- `tests/test_dose_accumulation.py:204` — `test_more_total_dose_increases_infection_and_illness_rates`
- `tests/test_env_pool_strains.py:448` — `test_two_thousand_agents_stay_within_a_step_budget`
- `tests/test_phenotype_consumption.py:147` — `test_strain_shedding_moves_emitted_dose`
- `tests/test_recombination.py:460` — `test_recombinants_appear_once_co_infection_does`
- `tests/test_recombination.py:464` — `test_no_recombinants_without_co_infection`
- `tests/test_recombination.py:470` — `test_recombination_off_reproduces_the_co_infection_run`
- `tests/test_recombination.py:480` — `test_every_recombinant_traces_to_two_resident_parents`
- `tests/test_recombination.py:490` — `test_a_recombination_event_never_widens_a_hosts_mixture`
- `tests/test_shedding_variance_cabin_mates.py:97` — `test_confined_non_mate_receives_minimal_direct_contact`
- `tests/test_shedding_variance_cabin_mates.py:136` — `test_confined_cabin_mate_receives_full_direct_contact`
- `tests/test_strain_dose_ledger.py:214` — `test_strain_doses_sum_to_pooled_dose`
- `tests/test_strain_dose_ledger.py:235` — `test_shedders_get_founder_strains_and_events_name_a_parent`
- `tests/test_strain_dose_ledger.py:286` — `test_absent_and_disabled_blocks_agree_over_24_epochs`
- `tests/test_strain_dose_ledger.py:297` — `test_flag_off_consumes_no_extra_rng_draws`
- `tests/test_strain_dose_ledger.py:307` — `test_flag_off_events_carry_no_strain`
- `tests/test_transmission_infection_expanded.py:237` — `test_execute_transmission_returns_matrix_and_events`
- `tests/test_transmission_infection_expanded.py:249` — `test_execute_transmission_with_infected_agent`
- `tests/test_zone_contact_summary.py:47` — `test_golden_colocation_summary`
- `tests/test_zone_contact_summary.py:81` — `test_sensitivity_relocation_changes_zone_counts`
- `tests/test_zone_contact_summary.py:120` — `test_sick_call_does_not_relocate_agents_to_medbay`

### A2. Establishment challenge contract — 8 test functions

- `tests/test_dashboard.py:37` — `test_pathway_breakdown_keys`
- `tests/test_dashboard.py:58` — `test_dominant_pathway_fallback`
- `tests/test_dashboard.py:73` — `test_none_pathway_excluded`
- `tests/test_dashboard.py:226` — `test_per_epoch_pathways`
- `tests/test_dose_accumulation.py:143` — `test_dose_response_susceptibility_is_persistent_and_host_specific`
- `tests/test_dose_accumulation.py:169` — `test_cumulative_inoculum_is_passed_to_infection_and_resets`
- `tests/test_dose_accumulation.py:192` — `test_exponential_model_keeps_its_closed_form_hazard`
- `tests/test_env_pool_strains.py:398` — `test_an_unresolved_superinfection_founds_a_nameable_lineage`

### A3. Progression — 48 test functions

- `tests/test_clinical_strain_typing.py:455` — `test_recovered_host_sheds_nothing_to_type`
- `tests/test_coinfection.py:278` — `test_single_resident_recovers_after_incubation_plus_recovery`
- `tests/test_coinfection.py:291` — `test_a_later_lineage_holds_the_infection_open`
- `tests/test_coinfection.py:300` — `test_the_pathogen_recovers_when_the_last_lineage_clears`
- `tests/test_coinfection.py:307` — `test_a_surviving_lineage_inherits_the_pathogen_level_fields`
- `tests/test_coinfection.py:315` — `test_lineage_clocks_advance_independently`
- `tests/test_coinfection.py:323` — `test_untracked_infection_progresses_unchanged`
- `tests/test_dose_pathway_invariants.py:143` — `test_airborne_mass_converges_instead_of_accumulating`
- `tests/test_dose_pathway_invariants.py:168` — `test_airborne_mass_decays_without_a_shedder`
- `tests/test_dose_pathway_invariants.py:178` — `test_confined_shedder_airborne_deposition_is_attenuated`
- `tests/test_immune_history.py:157` — `test_resolved_infection_leaves_one_record`
- `tests/test_immune_history.py:174` — `test_coinfected_host_remembers_every_lineage`
- `tests/test_immune_history.py:192` — `test_lineages_clearing_on_different_days_record_separately`
- `tests/test_immune_history.py:214` — `test_untracked_infection_records_nothing`
- `tests/test_immune_history.py:222` — `test_history_grows_only_with_resolved_exposures`
- `tests/test_immune_history.py:232` — `test_cleared_ids_are_reported_without_changing_the_count`
- `tests/test_immune_history.py:242` — `test_repeat_exposure_appends_a_record_per_exposure`
- `tests/test_immune_history.py:257` — `test_homologous_rechallenge_is_more_protected_than_cross`
- `tests/test_immune_history.py:269` — `test_history_survives_the_lineage_being_collected`
- `tests/test_immune_history.py:282` — `test_escape_grades_protection_down_monotonically`
- `tests/test_immune_history.py:298` — `test_two_resolved_genotypes_are_scored_on_the_best_match`
- `tests/test_immune_history.py:322` — `test_repeat_exposures_do_not_stack_protection`
- `tests/test_immune_history.py:347` — `test_embarkation_immunity_is_recorded_as_such`
- `tests/test_immune_history.py:366` — `test_flag_off_keeps_immunity_absolute_and_history_empty`
- `tests/test_immune_waning.py:396` — `test_an_embarkation_prior_is_ageless_rather_than_freshly_recovered`
- `tests/test_immune_waning.py:538` — `test_an_active_symptomatic_record_shows_at_the_agent_level`
- `tests/test_immune_waning.py:547` — `test_the_projection_unlatches_a_host_whose_records_cleared`
- `tests/test_immune_waning.py:558` — `test_an_asymptomatic_active_record_is_not_reported_ill`
- `tests/test_immune_waning.py:566` — `test_a_host_without_records_keeps_the_fallback_state`
- `tests/test_immune_waning.py:573` — `test_a_second_episode_reopens_the_legacy_fields`
- `tests/test_incubation_distributions.py:350` — `test_immune_history_counts_as_prior_immunity`
- `tests/test_incubation_distributions.py:432` — `test_a_fixed_onset_day_is_still_honoured_without_a_distribution`
- `tests/test_incubation_distributions.py:465` — `test_faster_variants_are_live_for_a_slow_pathogen`
- `tests/test_phenotype_consumption.py:221` — `test_graded_modifiers_shift_onset_monotonically`
- `tests/test_phenotype_consumption.py:227` — `test_zero_modifier_reproduces_the_legacy_onset_day`
- `tests/test_phenotype_consumption.py:238` — `test_faster_onset_cannot_precede_the_first_evaluated_day`
- `tests/test_phenotype_consumption.py:242` — `test_faster_onset_bites_when_the_baseline_onset_is_later`
- `tests/test_phenotype_consumption.py:249` — `test_slower_onset_can_outlast_the_observation_window`
- `tests/test_phenotype_consumption.py:334` — `test_prior_genotype_comes_from_a_resolved_infection`
- `tests/test_phenotype_consumption.py:386` — `test_shedding_does_not_move_onset`
- `tests/test_sim_clock.py:238` — `test_hourly_clock_clears_after_incubation_plus_three_symptomatic_days`
- `tests/test_sim_clock.py:246` — `test_legacy_clock_clears_after_incubation_plus_three_symptomatic_days`
- `tests/test_sim_clock.py:254` — `test_recovery_tracks_the_configured_epoch_duration`
- `tests/test_sim_clock.py:263` — `test_onset_waits_for_a_day_of_incubation_on_the_hourly_grid`
- `tests/test_sim_clock.py:296` — `test_the_illness_draw_is_per_day_not_per_epoch`
- `tests/test_sim_clock.py:449` — `test_onset_is_not_rounded_up_to_a_whole_voyage_day`
- `tests/test_sim_clock.py:471` — `test_late_incubation_extends_recovery_and_resets_symptom_day`
- `tests/test_sim_clock.py:591` — `test_the_sentinel_visible_onset_is_the_hosts_own_incubation_period`

### A4. Shedding — 21 test functions

- `tests/test_coinfection.py:198` — `test_single_resident_sheds_exactly_the_legacy_amount`
- `tests/test_coinfection.py:211` — `test_co_infection_conserves_total_shedding_at_equal_ages`
- `tests/test_coinfection.py:225` — `test_total_equals_the_sum_of_per_strain_curves`
- `tests/test_coinfection.py:235` — `test_shares_follow_the_establishing_inoculum`
- `tests/test_coinfection.py:242` — `test_a_higher_shedding_lineage_takes_over_the_mixture`
- `tests/test_coinfection.py:253` — `test_single_resident_has_no_shares_to_report`
- `tests/test_dose_pathway_invariants.py:388` — `test_emitted_and_direct_contact_dose_are_clock_invariant`
- `tests/test_infection_dynamics_bridge.py:83` — `test_shedding_is_zero_before_presymptomatic_window`
- `tests/test_infection_dynamics_bridge.py:95` — `test_presymptomatic_shedding_uses_first_curve_value`
- `tests/test_infection_dynamics_bridge.py:108` — `test_curve_peak_is_indexed_from_realized_onset`
- `tests/test_infection_dynamics_bridge.py:120` — `test_curve_index_scales_with_epoch_duration`
- `tests/test_infection_dynamics_bridge.py:148` — `test_virtual_onset_index_uses_elapsed_fractional_days`
- `tests/test_infection_dynamics_bridge.py:160` — `test_absent_presymptomatic_field_means_no_shedding_before_onset`
- `tests/test_phenotype_consumption.py:87` — `test_shedding_scales_with_strain_multiplier`
- `tests/test_phenotype_consumption.py:102` — `test_graded_sweep_is_monotone_and_spans_the_range`
- `tests/test_phenotype_consumption.py:118` — `test_host_and_strain_factors_compose_without_replacing`
- `tests/test_phenotype_consumption.py:134` — `test_untracked_infection_sheds_the_legacy_value`
- `tests/test_phenotype_consumption.py:371` — `test_transmissibility_does_not_move_shedding`
- `tests/test_shedding_variance_cabin_mates.py:54` — `test_multiplier_scales_get_pathogen_shedding`
- `tests/test_sim_clock.py:313` — `test_shedding_curve_index_is_held_across_a_day`
- `tests/test_transmission_infection_expanded.py:121` — `test_initial_susceptible`

### A5. Immunity — 41 test functions

- `tests/test_immune_history.py:157` — `test_resolved_infection_leaves_one_record`
- `tests/test_immune_history.py:174` — `test_coinfected_host_remembers_every_lineage`
- `tests/test_immune_history.py:192` — `test_lineages_clearing_on_different_days_record_separately`
- `tests/test_immune_history.py:214` — `test_untracked_infection_records_nothing`
- `tests/test_immune_history.py:222` — `test_history_grows_only_with_resolved_exposures`
- `tests/test_immune_history.py:242` — `test_repeat_exposure_appends_a_record_per_exposure`
- `tests/test_immune_history.py:257` — `test_homologous_rechallenge_is_more_protected_than_cross`
- `tests/test_immune_history.py:269` — `test_history_survives_the_lineage_being_collected`
- `tests/test_immune_history.py:282` — `test_escape_grades_protection_down_monotonically`
- `tests/test_immune_history.py:298` — `test_two_resolved_genotypes_are_scored_on_the_best_match`
- `tests/test_immune_history.py:322` — `test_repeat_exposures_do_not_stack_protection`
- `tests/test_immune_history.py:339` — `test_resident_lineage_still_counts_as_a_prior`
- `tests/test_immune_history.py:347` — `test_embarkation_immunity_is_recorded_as_such`
- `tests/test_immune_history.py:360` — `test_naive_host_has_no_history_and_no_protection`
- `tests/test_immune_history.py:366` — `test_flag_off_keeps_immunity_absolute_and_history_empty`
- `tests/test_immune_history.py:381` — `test_distinct_genotypes_keep_first_seen_order`
- `tests/test_immune_history.py:391` — `test_unnamed_genotype_is_not_a_prior`
- `tests/test_immune_history.py:397` — `test_telemetry_round_trips_the_fields`
- `tests/test_immune_history.py:411` — `test_invalid_records_are_rejected`
- `tests/test_immune_waning.py:372` — `test_a_voyage_of_epochs_is_days_through_the_clock`
- `tests/test_immune_waning.py:380` — `test_the_legacy_arm_reads_the_same_epochs_as_days`
- `tests/test_immune_waning.py:388` — `test_the_most_recent_exposure_to_a_genotype_wins`
- `tests/test_immune_waning.py:396` — `test_an_embarkation_prior_is_ageless_rather_than_freshly_recovered`
- `tests/test_immune_waning.py:409` — `test_a_recovered_host_is_protected_for_the_rest_of_the_voyage`
- `tests/test_immune_waning.py:419` — `test_the_same_host_is_challengeable_a_year_later`
- `tests/test_immune_waning.py:430` — `test_escape_gets_through_a_window_a_matched_strain_does_not`
- `tests/test_immune_waning.py:445` — `test_unnamed_dose_inside_the_window_does_not_leak`
- `tests/test_immune_waning.py:466` — `test_unnamed_dose_past_the_window_is_still_unprotected`
- `tests/test_immune_waning.py:483` — `test_a_resident_only_prior_gives_unnamed_dose_nothing`
- `tests/test_incubation_distributions.py:350` — `test_immune_history_counts_as_prior_immunity`
- `tests/test_incubation_distributions.py:357` — `test_immunity_to_another_pathogen_does_not_count`
- `tests/test_phenotype_consumption.py:276` — `test_escape_grades_protection_down`
- `tests/test_phenotype_consumption.py:288` — `test_heterologous_challenge_is_less_protected_than_homologous`
- `tests/test_phenotype_consumption.py:300` — `test_unattributed_dose_is_not_credited_with_protection`
- `tests/test_phenotype_consumption.py:314` — `test_pre_immune_agent_is_absolutely_protected_without_genotypes`
- `tests/test_phenotype_consumption.py:327` — `test_flag_off_keeps_immunity_absolute`
- `tests/test_phenotype_consumption.py:334` — `test_prior_genotype_comes_from_a_resolved_infection`
- `tests/test_phenotype_consumption.py:353` — `test_pre_immune_prior_genotype_is_drawn_once_and_kept`
- `tests/test_phenotype_consumption.py:361` — `test_naive_agent_has_no_prior_and_no_protection`
- `tests/test_strain_state.py:311` — `test_cross_immunity_lookup_and_escape_discount`
- `tests/test_strain_state.py:324` — `test_escape_monotonically_erodes_protection`

## Appendix B. Verification and limitations

- Static analysis covered all 430 Python files found under the snapshot (159 under `tests/`; 271 outside tests, including tooling and vendored/project support code). I excluded `.agents` helper code from production-state counts.
- Full pytest collection was blocked by the absent optional `boto3` package after collecting 3,157 tests. A first captured collection attempt also hit an environment capture-file error.
- I ran the union of 22 seam-related test files: **590 passed and 19 failed**. Every failure was in `tests/test_dashboard.py` and was caused at import time by absent optional `streamlit`; no executed seam test failed. Thus the runtime check is strong for core biology but incomplete for dashboard consumers.
- The snapshot directory contains no `.git` metadata, so I verified identity from `CANONICAL_SOURCE_SHA.txt`; I could not independently run `git status` or compare the tree to remote Git from this directory.
- “All files/functions” here means Python production and test code. JSON/YAML pathogen profiles and schemas configure behavior but do not execute reads/writes; they should still be extended for the new clearance parameter.

## Discretionary analytical decisions

- I counted test function definitions rather than parametrized cases because that is stable under parameter-list changes and maps directly to fixtures that need edits.
- I expanded dependencies through same-module helper calls to avoid undercounting tests that exercise seams through `_run_exposure`, `_agent`, or similar fixtures.
- I kept the establishment count narrow to the proposed challenge contract; generic uses of `infect_with_pathogen()` solely to create test state were not counted as establishment-contract dependencies.
- I graded progression high despite a backwards-compatible route because the current spec incorrectly describes the cleared-list boundary and because progression feeds clinical observation, immune history, and legacy projection simultaneously.
- I recommend computed legacy properties rather than rewriting all downstream readers because the spec explicitly requires legacy projection compatibility and this is the minimum-change route to a single source of truth.
