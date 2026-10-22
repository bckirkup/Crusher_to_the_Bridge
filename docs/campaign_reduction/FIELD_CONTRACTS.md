# Full field contract index

**Authority:** [`FIELD_CONTRACTS.json`](FIELD_CONTRACTS.json), contract `crusher-campaign-distributions/1.0-proposed`. **NOT YET IMPLEMENTED.**

This is a generated reading view, not an additional schema. JSON/Parquet type, nullable status, unit, definition and native enums are preserved. Row-envelope schema: [`TABLE_ROWS.schema.json`](TABLE_ROWS.schema.json).

## `campaign_catalog`
Grain: one declared campaign/stage registration. Primary key: `campaign_id`, `stage_id`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `campaign_id` | `utf8` | False | 1 | Canonical namespaced stable campaign ID; aliases in campaign_aliases_json |
| `stage_id` | `utf8` | False | 1 | Distinct staged design/reanalysis/canary block; do not infer from directory |
| `campaign_aliases_json` | `json` | False | 1 | Historical directory/ledger/manifest names, with alias evidence |
| `family` | `utf8` | False | 1 | Pathogen/mechanistic/diagnostic/wearable/wastewater/boundary/economics/sentinel/variant/multi-pathogen family |
| `pathogen_ids` | `list<utf8>` | False | 1 | Explicit pathogens; synthetic flagged, not assumed norovirus |
| `catalog_state` | `utf8` | False | 1 | Documentation/execution state Allowed: declared, outcomes_reported, assets_verified, partially_recovered, reduced, withdrawn, blocked, unknown |
| `design_uri` | `utf8` | True | 1 | Frozen input or source-local URI |
| `ledger_uri` | `utf8` | True | 1 | Controlling chronological entry not stale front matter |
| `documentation_sha` | `utf8` | True | 1 | Documentation revision distinct from simulation/reducer |
| `declared_slots` | `int64` | True | run | Declared design slots, not verified completed executions |
| `reported_completed` | `int64` | True | run | Ledger asserted completed cells, not independently verified |
| `verified_unique_completed` | `int64` | True | run | Exact asset-linked selected completed executions |
| `validity_axes_json` | `json` | False | 1 | Independent hull, fleet weighting, total population, crew/passenger statuses and evidence |
| `claim_use` | `utf8` | False | 1 | Candidate use only; historical or quarantined rows remain queryable |
| `coverage_note` | `utf8` | False | 1 | Known omissions, scope and status basis |

## `attempts`
Grain: one immutable scientific attempt. Primary key: `campaign_id`, `stage_id`, `attempt_id`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `campaign_id` | `utf8` | False | 1 | Campaign FK |
| `stage_id` | `utf8` | False | 1 | Stage FK |
| `attempt_id` | `utf8` | False | 1 | Exploratory/confirmatory/revision/review-response/canary identity |
| `attempt_kind` | `utf8` | False | 1 | Scientific lifecycle Allowed: exploratory, confirmatory, revision, review_response, canary, smoke, reanalysis, unknown |
| `parent_attempt_ids` | `list<utf8>` | False | 1 | Explicit parentage; empty means root, not missing history |
| `design_hash` | `utf8` | True | 1 | Frozen design contents identity |
| `analysis_plan_hash` | `utf8` | True | 1 | Frozen estimands and rules, if existing |
| `selected_run_policy` | `utf8` | False | 1 | Predetermined retry/result selection, never most favorable result |
| `scientific_approval_state` | `utf8` | False | 1 | Existing approval evidence, not a new per-download human gate |
| `supersedes_scope_json` | `json` | False | 1 | Target/run/claim-specific supersession; none does not erase history |

## `runs`
Grain: one actual or declared run execution. Primary key: `run_uid`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `run_uid` | `utf8` | False | 1 | Globally unique scientific execution key |
| `campaign_id` | `utf8` | False | 1 | Campaign ID |
| `stage_id` | `utf8` | False | 1 | Stage ID |
| `attempt_id` | `utf8` | False | 1 | Attempt ID |
| `case_id` | `utf8` | False | 1 | Design-cell + replicate identity independent of retry packaging |
| `execution_id` | `utf8` | False | 1 | Actual execution/retry identity; unresolved gets explicit provisional ID |
| `original_run_id` | `utf8` | False | 1 | Emitted identifier unmodified |
| `seed` | `uint64` | True | 1 | Exact RNG seed; never float |
| `rng_streams_json` | `json` | False | 1 | Saved RNG algorithm/substream identities and pairing scope; unknown explicitly |
| `replicate_id` | `utf8` | True | 1 | Within-design scientific replicate |
| `arm_id` | `utf8` | True | 1 | Nominal arm identifier |
| `vessel_id` | `utf8` | True | 1 | Stable template/vessel identifier, not inferred from population |
| `pathogen_ids` | `list<utf8>` | False | 1 | Pathogens represented in this execution |
| `engine_sha` | `utf8` | True | 1 | Actually executed source SHA; documentation SHA is not a substitute |
| `image_digest` | `utf8` | True | 1 | Actually executed container digest; tag may be stored in metadata only |
| `input_hash` | `utf8` | True | 1 | Resolved input content hash |
| `execution_state` | `utf8` | False | 1 | Execution state Allowed: declared, completed, partial, failed, cancelled, unknown |
| `selection_state` | `utf8` | False | 1 | Eligible replicate state Allowed: selected, duplicate_alias, retry_not_selected, identity_conflict, quarantined, pending |
| `selection_reason` | `utf8` | False | 1 | Explicit dedup/retry/claim use basis |
| `clock_mode` | `utf8` | True | 1 | Actual natural-history/physical clock mode |
| `configured_epoch_hours` | `float64` | True | h | Saved configured step length, not necessarily effective |
| `effective_epoch_hours` | `float64` | True | h | Effective conversion proved from actual run version/config |
| `epoch_origin_kind` | `utf8` | True | 1 | Origin convention: pre-step/post-step/time-zero/etc. |
| `epoch_origin_hours` | `float64` | True | h | Elapsed hours at epoch zero relative to voyage departure |
| `voyage_start_utc` | `utf8` | True | 1 | Calendar origin only when actually saved; otherwise elapsed-only |
| `requested_duration_hours` | `float64` | True | h | Intended horizon |
| `actual_followup_hours` | `float64` | True | h | Observed/simulated completed follow-up |
| `last_complete_epoch` | `int64` | True | epoch | Last complete epoch; incomplete tail excluded |
| `retention_profile` | `utf8` | False | 1 | Full/compact/lean/mixed/unknown; capability finer than this label |
| `metadata_json` | `json` | False | 1 | Original run tags, image tag, launch IDs and optional environment metadata |

## `assets`
Grain: one object/member/sidecar instance. Primary key: `asset_id`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `asset_id` | `utf8` | False | 1 | Stable asset ID |
| `campaign_id` | `utf8` | False | 1 | Campaign ID; unmapped assets receive inventory namespace |
| `attempt_id` | `utf8` | False | 1 | Attempt or unresolved inventory attempt |
| `run_uid` | `utf8` | True | 1 | Mapped execution; null for fused container or not-yet-mapped |
| `s3_uri` | `utf8` | False | 1 | Existing authorized source URI; local evidence URI also allowed |
| `object_version` | `utf8` | True | 1 | S3 version if present; not mandatory for unversioned historical objects |
| `object_etag` | `utf8` | True | 1 | ETag only cache identity, NOT promised content SHA |
| `asset_kind` | `utf8` | False | 1 | Container or member Allowed: container, member, sidecar, parquet, manifest, log, local_source |
| `parent_asset_id` | `utf8` | True | 1 | Container FK for a member |
| `member_path` | `utf8` | True | 1 | Exact path inside per-run/fused archive |
| `compression` | `utf8` | False | 1 | ZIP/gzip/none etc. |
| `bytes_stored` | `int64` | True | byte | Stored bytes |
| `bytes_uncompressed` | `int64` | True | byte | Member uncompressed bytes |
| `content_sha256` | `utf8` | True | 1 | Hash of exact object OR uncompressed member as stated in hash_scope |
| `hash_scope` | `utf8` | False | 1 | Container hashes never compared as member hashes Allowed: container_bytes, uncompressed_member, file_bytes, not_computed |
| `read_state` | `utf8` | False | 1 | Listing vs actual parse evidence Allowed: listed, indexed, read, parsed, malformed, unreachable, missing, not_requested |
| `adapter_id` | `utf8` | True | 1 | Versioned source adapter used or proposed |
| `source_sha` | `utf8` | True | 1 | Writer/engine identity only when known |

## `capabilities`
Grain: one run or stage capability. Primary key: `scope_id`, `capability_id`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `scope_id` | `utf8` | False | 1 | run_uid or campaign/stage ID; scope_kind disambiguates |
| `scope_kind` | `utf8` | False | 1 | Scope type Allowed: run, stage, campaign |
| `capability_id` | `utf8` | False | 1 | Metric/table/join capability ID |
| `availability` | `utf8` | False | 1 | Typed scientific recoverability Allowed: available_exact, available_rounded, recoverable_unread, derivable_exact, partial, not_saved, dropped_by_profile, not_applicable, unknown, blocked_identity, malformed, unreachable |
| `evidence_detail` | `utf8` | False | 1 | Saved member/schema/version proof; no global flag inferred from one sample |
| `row_coverage` | `int64` | True | 1 | Rows or executions inspected, stated in coverage_unit |
| `coverage_unit` | `utf8` | False | 1 | run/member/row |
| `required_members` | `list<utf8>` | False | 1 | Targeted member paths |
| `recoverability_action` | `utf8` | False | 1 | Read/reduce/reconcile/retain unavailable/pilot proposal |

## `data_gaps`
Grain: one unavailable value or range. Primary key: `row_id`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `table_name` | `utf8` | False | 1 | Affected normalized table |
| `target_row_id` | `utf8` | True | 1 | Affected row, or range selector JSON in selector_json |
| `field_name` | `utf8` | False | 1 | Column or metric |
| `selector_json` | `json` | False | 1 | Explicit affected slice; empty object for single row |
| `reason` | `utf8` | False | 1 | Never silently map to zero Allowed: not_saved, dropped_by_profile, member_missing, not_applicable, unknown_schema, malformed, unreachable, not_requested, identity_unresolved, incompatible_definition, denominator_zero, no_events, not_observed, not_identifiable, rounded_only, time_origin_unknown, partial_followup, unsupported_join |
| `detail` | `utf8` | False | 1 | Evidence and recovery instructions |
| `recoverability` | `utf8` | False | 1 | Recoverability state Allowed: read_existing, derive_existing, reconcile_identity, irrecoverable_existing, pending_inventory, not_applicable |
| `blocks_claim_ids` | `list<utf8>` | False | 1 | Only affected claims blocked, not the entire catalog |

## `design_values`
Grain: one run parameter at specified design layer. Primary key: `run_uid`, `parameter_path`, `value_layer`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `run_uid` | `utf8` | False | 1 | Exact scientific execution identity, never filename alone |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `parameter_path` | `utf8` | False | 1 | Canonical and original configuration path via metadata |
| `value_layer` | `utf8` | False | 1 | Do not substitute nominal for realized Allowed: nominal_design, resolved_config, realized_draw, realized_exposure, measured_outcome |
| `value_json` | `json` | False | 1 | Exact original scalar/structured value, no float seed conversion |
| `value_numeric` | `float64` | True | 1 | Numeric projection when lossless enough for analysis |
| `value_unit` | `utf8` | False | 1 | Physical/probability/log scale units |
| `distribution_family` | `utf8` | True | 1 | Nominal distribution family if draw |
| `correlation_group_id` | `utf8` | True | 1 | Shared draw/correlation design identifier |
| `parameter_provenance_json` | `json` | False | 1 | Source grade/assumed/fitted/transcribed plus transform/version |

## `pair_links`
Grain: one explicitly justified pair/contrast. Primary key: `pair_id`, `contrast_id`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `pair_id` | `utf8` | False | 1 | Pairing identity within contrast, not seed alone |
| `contrast_id` | `utf8` | False | 1 | Frozen contrast recipe ID |
| `left_run_uid` | `utf8` | False | 1 | Reference selected run FK |
| `right_run_uid` | `utf8` | False | 1 | Treatment/other selected run FK |
| `shared_seed` | `uint64` | True | 1 | Seed equality is necessary only for declared CRN scheme, not sufficient |
| `pairing_basis` | `utf8` | False | 1 | Matched cell, random stream and source bridge evidence |
| `pair_state` | `utf8` | False | 1 | Eligibility Allowed: exact_design_pair, version_bridge_pair, partial_pair, unmatched, incompatible |
| `bridge_id` | `utf8` | True | 1 | Source/image/parameter equivalence table reference for version comparison |
| `differing_parameter_paths` | `list<utf8>` | False | 1 | Explicit actual differences incl hull bundle |
| `unmatched_reason` | `utf8` | True | 1 | Structurally optional for exact pairs |

## `role_dictionary`
Grain: one versioned role concept. Primary key: `role_definition_id`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `role_definition_id` | `utf8` | False | 1 | Stable explicit ontology ID with version |
| `role_label` | `utf8` | False | 1 | Human label |
| `role_axis` | `utf8` | False | 1 | Orthogonal role axes Allowed: primary_population, occupation, response_function, duty_state, source_eligibility, clinical_state, observation_state, spatial_context |
| `membership_rule` | `utf8` | False | 1 | Exact predicate including writer version and input fields |
| `exclusive_within_axis` | `bool` | False | 1 | True only for proved exhaustive disjoint primary role partition |
| `time_varying` | `bool` | False | 1 | Requires interval/event-time membership |
| `source_mapping_json` | `json` | False | 1 | Original role/class values and explicit fallback/unresolved handling |

## `agents`
Grain: one saved agent identity per run. Primary key: `run_uid`, `agent_id`. Tier: `conditional_saved`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `run_uid` | `utf8` | False | 1 | Exact scientific execution identity, never filename alone |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `agent_id` | `utf8` | False | 1 | Stable within-run ID, not cross-seed person |
| `roster_scope` | `utf8` | False | 1 | Full roster vs infected subset Allowed: full_at_risk, infected_only, observed_only, event_participant_only, partial |
| `boarding_state` | `utf8` | True | 1 | Saved infection/import and presence state |
| `primary_role_id` | `utf8` | True | 1 | Explicit role dictionary FK; unresolved not inferred crew/passenger |
| `attributes_json` | `json` | False | 1 | Only saved stable subgroup attributes, no generated demographics |

## `memberships`
Grain: one agent-role/context membership interval. Primary key: `run_uid`, `membership_id`. Tier: `conditional_saved`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `run_uid` | `utf8` | False | 1 | Exact scientific execution identity, never filename alone |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `membership_id` | `utf8` | False | 1 | Distinct membership interval ID |
| `agent_id` | `utf8` | False | 1 | Within-run agent FK |
| `role_definition_id` | `utf8` | False | 1 | Dictionary FK |
| `start_hours` | `float64` | False | h | Inclusive start, elapsed voyage hours |
| `end_hours` | `float64` | False | h | Exclusive end; clipped to complete followup |
| `context_id` | `utf8` | True | 1 | Zone/work/team/host recipient context |
| `membership_basis` | `utf8` | False | 1 | Saved role, explicit predicate or verified derived interval; never nominal crew JSON alone |

## `population_intervals`
Grain: one run × population/window denominator. Primary key: `run_uid`, `population_id`, `window_id`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `run_uid` | `utf8` | False | 1 | Exact scientific execution identity, never filename alone |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `population_id` | `utf8` | False | 1 | Versioned set rule, with role/eligibility/clinical exclusion |
| `window_id` | `utf8` | False | 1 | Versioned followup window |
| `role_definition_id` | `utf8` | True | 1 | Optional role-specific set |
| `window_start_hours` | `float64` | False | h | Inclusive beginning |
| `window_end_hours` | `float64` | False | h | Exclusive end |
| `population_basis` | `utf8` | False | 1 | Denominator semantics Allowed: boarding_complement, unique_ever_aboard, susceptible_at_start, eligible_course_cohort, eligible_onboard, dynamic_at_risk, test_eligible, source_eligible, response_eligible, observed_roster |
| `n_unique` | `int64` | True | person | Distinct eligible persons; not episodes |
| `n_at_start` | `int64` | True | person | Eligible present at start |
| `n_at_end` | `int64` | True | person | Eligible present at end |
| `person_hours` | `float64` | True | person*h | Integral of union of eligible presence intervals |
| `susceptible_person_hours` | `float64` | True | person*h | Integral of infection-risk eligibility; reinfection rule explicit |
| `risk_set_rule` | `utf8` | False | 1 | Arrivals/departures, immunity, infection, competing exit, attribution membership time |
| `count_evidence` | `utf8` | False | 1 | Emitted complete roster, emitted counts, reconstruction, or nominal-only warning |

## `run_scalars`
Grain: one exact native scalar path per run and source member. Primary key: `run_uid`, `source_asset_id`, `native_path`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `run_uid` | `utf8` | False | 1 | Exact scientific execution identity, never filename alone |
| `source_asset_id` | `utf8` | False | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `native_path` | `utf8` | False | 1 | JSON Pointer / row+column to original scalar |
| `native_type` | `utf8` | False | 1 | Original primitive Allowed: null, boolean, integer, number, string |
| `native_value_json` | `utf8` | False | 1 | Exact lexical JSON token where possible; original member retained otherwise |
| `canonical_metric_id` | `utf8` | True | 1 | Validated mapping only; unmapped scalar still accessible |
| `mapping_state` | `utf8` | False | 1 | Mapping status Allowed: verified, native_only, ambiguous, rounded_source |
| `unit` | `utf8` | False | 1 | As emitted or unknown; never infer route dose unit from field name |

## `metrics`
Grain: one exact run × estimand × population × condition/window. Primary key: `run_uid`, `metric_id`, `population_id`, `condition_id`, `window_id`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `run_uid` | `utf8` | False | 1 | Exact scientific execution identity, never filename alone |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `metric_id` | `utf8` | False | 1 | Versioned estimand dictionary ID |
| `population_id` | `utf8` | False | 1 | Denominator population ID |
| `condition_id` | `utf8` | False | 1 | Unconditional or explicit predicate on post/outbreak/channel/etc. |
| `window_id` | `utf8` | False | 1 | Versioned observation/clinical/acquisition window |
| `numerator` | `float64` | True | metric-dependent | Exact count/integral numerator projection; native token retained |
| `denominator` | `float64` | True | metric-dependent | Matching population/person-time/exposure opportunity denominator |
| `value` | `float64` | True | metric-dependent | Unrounded recomputation only where numerator/denominator defined |
| `value_status` | `utf8` | False | 1 | Value evidence Allowed: exact_emitted, exact_derived, rounded_emitted, partial, undefined, unavailable |
| `unit` | `utf8` | False | 1 | Count/proportion/person^-hour/dose/event etc. |
| `endpoint_domain` | `utf8` | False | 1 | Truth, clinical, observation, policy, economic distinct Allowed: latent_truth, symptomatic_course, onboard_symptoms, reported, tested, lab_confirmed, response, mechanism, economic, external_observed |
| `definition_version` | `utf8` | False | 1 | Source/analysis definition identity |
| `membership_time_rule` | `utf8` | False | 1 | At boarding/acquisition/onset/report/event/time-integrated |
| `numerator_exact_json` | `utf8` | True | 1 | Exact count/integral JSON token when numeric projection is lossy; structurally optional when numerator absent |
| `denominator_exact_json` | `utf8` | True | 1 | Exact denominator token; structurally optional when denominator absent |

## `epoch_metrics`
Grain: one run × metric × population × time bin. Primary key: `run_uid`, `metric_id`, `population_id`, `bin_start_hours`, `bin_end_hours`. Tier: `conditional_saved`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `run_uid` | `utf8` | False | 1 | Exact scientific execution identity, never filename alone |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `metric_id` | `utf8` | False | 1 | Versioned curve metric |
| `population_id` | `utf8` | False | 1 | Explicit role/risk set |
| `source_epoch` | `int64` | True | epoch | Original epoch; keep exact axis |
| `bin_start_hours` | `float64` | False | h | Inclusive elapsed time |
| `bin_end_hours` | `float64` | False | h | Exclusive elapsed time |
| `value` | `float64` | True | metric-dependent | Count/state/increment/integral; metric defines type |
| `denominator` | `float64` | True | metric-dependent | Actual bin population or person-time |
| `series_kind` | `utf8` | False | 1 | Series semantics Allowed: state, incidence, cumulative, rate, integral, flag |
| `value_status` | `utf8` | False | 1 | Exact/rounded/estimated/missing |

## `times_to_event`
Grain: one subject/run × endpoint × followup window. Primary key: `run_uid`, `subject_kind`, `subject_id`, `endpoint_id`, `window_id`. Tier: `conditional_saved`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `run_uid` | `utf8` | False | 1 | Exact scientific execution identity, never filename alone |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `subject_kind` | `utf8` | False | 1 | Unit at risk Allowed: run, agent, episode, object, test, port_call |
| `subject_id` | `utf8` | False | 1 | Stable ID at this grain |
| `endpoint_id` | `utf8` | False | 1 | Acquisition/onset/report/test/result/trigger/recovery/etc. |
| `window_id` | `utf8` | False | 1 | Followup window definition |
| `time_origin_id` | `utf8` | False | 1 | Voyage start/acquisition/onset/specimen/etc. |
| `origin_hours` | `float64` | True | h | Origin on elapsed voyage axis |
| `entry_hours` | `float64` | True | h | Risk entry relative to time origin (delayed entry supported) |
| `lower_hours` | `float64` | True | h | Lower event bound; null means negative infinity only for explicitly left censored |
| `upper_hours` | `float64` | True | h | Upper event bound; null means positive infinity only for explicitly right censored |
| `censor_type` | `utf8` | False | 1 | Event-time observation Allowed: exact, right, left, interval, structural_nonoccurrence, not_at_risk, unknown |
| `exit_hours` | `float64` | True | h | Actual end of observation relative origin |
| `competing_endpoint_id` | `utf8` | True | 1 | Disembarkation/death/recovery/etc.; must distinguish administrative censor |
| `event_domain` | `utf8` | False | 1 | Observed/latent/estimated Allowed: latent, observed, scheduled, inferred_interval |
| `event_observed` | `bool` | True | 1 | True iff endpoint was directly observed within relevant domain |
| `original_time_json` | `json` | False | 1 | Raw epoch, unit, bounds and writer convention |

## `events`
Grain: one saved event or establishment episode. Primary key: `run_uid`, `event_id`. Tier: `conditional_saved`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `run_uid` | `utf8` | False | 1 | Exact scientific execution identity, never filename alone |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `event_id` | `utf8` | False | 1 | Native ID, or deterministic source-member+array-index ID |
| `event_type` | `utf8` | False | 1 | Exposure/contact/acquisition/onset/report/care/delivery/etc. |
| `episode_id` | `utf8` | True | 1 | Infection episode FK if saved |
| `start_hours` | `float64` | True | h | Inclusive event time/beginning |
| `end_hours` | `float64` | True | h | Exclusive end for duration; instant events start=end |
| `zone_id` | `utf8` | True | 1 | Saved spatial context |
| `object_id` | `utf8` | True | 1 | Saved mechanism object FK |
| `entry_channel` | `utf8` | True | 1 | Boarding/imported supply/shore/aboard/unknown per version |
| `dose_route` | `utf8` | True | 1 | Dose accounting route, distinct from entry |
| `dominant_route` | `utf8` | True | 1 | Establishment argmax/tie/fallback definition, never source identity |
| `dose_delivered` | `float64` | True | declared_dose_unit | Delivered dose, not automatically acquired dose |
| `dose_acquired` | `float64` | True | declared_dose_unit | Credited/acquired dose with source units |
| `event_weight` | `float64` | False | event | 1 for each event unless saved aggregated event explicitly labeled |
| `payload_json` | `json` | False | 1 | All unmapped original event fields preserved server-side |

## `event_participants`
Grain: one event × agent × participation kind. Primary key: `run_uid`, `event_id`, `agent_id`, `participation_kind`. Tier: `conditional_saved`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `run_uid` | `utf8` | False | 1 | Exact scientific execution identity, never filename alone |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `event_id` | `utf8` | False | 1 | Saved event FK |
| `agent_id` | `utf8` | False | 1 | Stable within-run ID |
| `participation_kind` | `utf8` | False | 1 | Directed and multi-person participation Allowed: actor, source, recipient, exposed, responder, caregiver, service_provider, reporter, specimen_donor, tested, observer |
| `role_definition_id` | `utf8` | True | 1 | Event-time role if recoverable, otherwise null gap |
| `membership_id` | `utf8` | True | 1 | Event-time interval membership evidence |
| `dose_share` | `float64` | True | 1 | Only when saved and meaningful; not imputed equal shares |
| `participation_status` | `utf8` | False | 1 | Saved/derived/partial; count unique IDs separately from event rows |

## `mechanism_objects`
Grain: one saved physical/source object. Primary key: `run_uid`, `object_id`. Tier: `conditional_saved`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `run_uid` | `utf8` | False | 1 | Exact scientific execution identity, never filename alone |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `object_id` | `utf8` | False | 1 | Stable within-run object ID |
| `object_kind` | `utf8` | False | 1 | Provisioned lot/pan/event source/air compartment/etc. |
| `source_id` | `utf8` | True | 1 | Saved source identity; scenario label not necessarily routed itinerary |
| `source_kind` | `utf8` | True | 1 | Boarding/agent/provisioned/shore/environmental etc. |
| `zone_id` | `utf8` | True | 1 | Saved location |
| `station_id` | `utf8` | True | 1 | Stable source station if saved or deterministic zone+item mapping |
| `start_hours` | `float64` | True | h | Seeded/available time |
| `end_hours` | `float64` | True | h | Removal/end/censor time |
| `end_reason` | `utf8` | True | 1 | Exhaustion/extent_met/horizon/etc. |
| `attributes_json` | `json` | False | 1 | All saved titre/servings/pans/window/source witnesses with units |

## `observations`
Grain: one saved observation/specimen/result/report. Primary key: `run_uid`, `observation_id`. Tier: `conditional_saved`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `run_uid` | `utf8` | False | 1 | Exact scientific execution identity, never filename alone |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `observation_id` | `utf8` | False | 1 | Unique observation ID; repeated tests remain distinct |
| `subject_id` | `utf8` | True | 1 | Agent/site/zone/port subject |
| `subject_kind` | `utf8` | False | 1 | agent/sample/zone/ship/port |
| `modality` | `utf8` | False | 1 | Syndromic/clinical/lab/wearable/wastewater/sequencing/etc. |
| `specimen_id` | `utf8` | True | 1 | Specimen identity |
| `parent_observation_id` | `utf8` | True | 1 | Reflex/cascade lineage |
| `collection_hours` | `float64` | True | h | Actual sample/observation time |
| `result_hours` | `float64` | True | h | Availability time not collection time |
| `result_json` | `json` | False | 1 | Categorical/numeric result and original unit/LOD/LOQ/censor flags |
| `latent_truth_json` | `json` | False | 1 | Saved simulation truth linkage, labeled and never used as observed fit input |
| `eligibility_population_id` | `utf8` | True | 1 | Who could be tested/reported |
| `feedback_action_id` | `utf8` | True | 1 | Policy/clinical action caused by observation if saved |

## `weights`
Grain: one analysis target × unit weight. Primary key: `weight_set_id`, `unit_id`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `weight_set_id` | `utf8` | False | 1 | Named immutable target/date weight definition |
| `unit_kind` | `utf8` | False | 1 | Weight unit Allowed: run, seed_block, design_cell, vessel, voyage, person, posterior_draw, external_record |
| `unit_id` | `utf8` | False | 1 | Matching ID at declared unit |
| `target_id` | `utf8` | False | 1 | Finite fleet, bounded class, design distribution, population etc. |
| `weight` | `float64` | False | 1 | Nonnegative finite analysis weight; zero weight reported not deleted |
| `weight_kind` | `utf8` | False | 1 | Simulation design/fleet/population/inverse probability/posterior separately Allowed: equal_run, design, fleet, person, selection, posterior |
| `normalization_scope` | `utf8` | False | 1 | Within vessel/cell/target normalization |
| `provenance_json` | `json` | False | 1 | Named/date fleet source, selection rule, uncertainty, bounds and approval |
| `validity_status` | `utf8` | False | 1 | Qualified/unqualified/blocked; no weights borrowed silently across targets |

## `distributions`
Grain: one exact mass/support point or censored-time contribution per group. Primary key: `query_id`, `distribution_id`, `support_id`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `query_id` | `utf8` | False | 1 | Reproducible query/analysis ID |
| `distribution_id` | `utf8` | False | 1 | Metric/conditioning/weight domain ID |
| `support_id` | `utf8` | False | 1 | Stable sorted support/bound record ID |
| `group_json` | `json` | False | 1 | Exact user-selected dimensions and target |
| `metric_id` | `utf8` | False | 1 | Versioned metric |
| `support_value` | `float64` | True | metric-dependent | Exact observed scalar support; null for censor/time category only |
| `mass_count` | `int64` | False | run | Number of distinct selected independent run contributions |
| `weight_sum` | `float64` | False | 1 | Sum declared valid weights at support |
| `cdf` | `float64` | True | 1 | Right-continuous scalar ECDF when meaningful; not for arbitrary censor records |
| `n_eligible` | `int64` | False | run | Runs eligible before value missingness |
| `n_observed` | `int64` | False | run | Nonmissing value runs |
| `n_missing` | `int64` | False | run | Unavailable/undefined separate via missing_reason_counts_json |
| `n_effective` | `float64` | True | run | Kish weight diagnostic, not independent replicate count |
| `missing_reason_counts_json` | `json` | False | 1 | Typed reason counts incl structural zero/event absence |
| `distribution_payload_json` | `json` | False | 1 | Censor/risk-set/CIF table, atom metadata, histogram bounds or approximation disclosure |

## `aggregate_estimates`
Grain: one analysis estimand × target/group. Primary key: `query_id`, `estimate_id`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `query_id` | `utf8` | False | 1 | Recipe/query identity |
| `estimate_id` | `utf8` | False | 1 | Output ID |
| `estimand_id` | `utf8` | False | 1 | Mean run rate/pooled person rate/mixture contrast etc. |
| `group_json` | `json` | False | 1 | All conditioning, populations, hulls and parameter dimensions |
| `target_id` | `utf8` | False | 1 | Named target distribution or bounded vessel claim |
| `weight_set_id` | `utf8` | False | 1 | Explicit weights or equal-run definition |
| `estimate` | `float64` | True | estimand-dependent | Unrounded estimate |
| `lower` | `float64` | True | estimand-dependent | Interval lower bound |
| `upper` | `float64` | True | estimand-dependent | Interval upper bound |
| `interval_method` | `utf8` | False | 1 | Seed-block bootstrap/binomial/exact/survival/posterior etc. |
| `interval_level` | `float64` | True | 1 | Coverage or posterior probability |
| `n_independent_blocks` | `int64` | False | block | Actual independent seed/design blocks |
| `n_runs` | `int64` | False | run | Selected complete runs contributing |
| `numerator` | `float64` | True | estimand-dependent | Pooled numerator if appropriate |
| `denominator` | `float64` | True | estimand-dependent | Pooled denominator if appropriate |
| `analysis_version` | `utf8` | False | 1 | Deterministic recipe, code and environment version |
| `limitations_json` | `json` | False | 1 | Vacuity, missingness, multiplicity, identity and validity restrictions |
| `numerator_exact_json` | `utf8` | True | 1 | Exact count/integral JSON token when numeric projection is lossy; structurally optional when numerator absent |
| `denominator_exact_json` | `utf8` | True | 1 | Exact denominator token; structurally optional when denominator absent |

## `external_targets`
Grain: one external observed endpoint/stratum. Primary key: `external_target_id`. Tier: `external_separate`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `external_target_id` | `utf8` | False | 1 | Stable target/version |
| `dataset_id` | `utf8` | False | 1 | Dataset and extraction date |
| `endpoint_id` | `utf8` | False | 1 | AGE/norovirus-specific/reported/lab etc. |
| `population_definition` | `utf8` | False | 1 | Passengers/crew/fleet/tonnage/duration/eligibility |
| `time_window_json` | `json` | False | 1 | Calendar era, voyage duration and observation boundaries |
| `observed_numerator` | `float64` | True | declared | Actual observed count or estimate |
| `observed_denominator` | `float64` | True | declared | Matching observed exposure denominator |
| `estimate_json` | `json` | False | 1 | Uncertainty, ascertainment, norovirus fraction model and external-only transformation |
| `provenance_json` | `json` | False | 1 | Local source/citation/extraction grade and limitations |
| `comparison_qualification` | `utf8` | False | 1 | Matched/partially matched/withheld, endpoint-specific |

## `analysis_artifacts`
Grain: one generated query/reduction export. Primary key: `artifact_id`. Tier: `core`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `artifact_id` | `utf8` | False | 1 | Stable catalog ID |
| `query_id` | `utf8` | False | 1 | Query ID |
| `uri` | `utf8` | False | 1 | AWS full table or compact Edison artifact pointer |
| `format` | `utf8` | False | 1 | Parquet/JSON/CSV/PNG/PDF/Markdown etc. |
| `row_count` | `int64` | False | row | Exact rows exported |
| `bytes` | `int64` | False | byte | Artifact size |
| `content_sha256` | `utf8` | False | 1 | Ordinary scientific reproducibility checksum |
| `source_partition_ids` | `list<utf8>` | False | 1 | Exact catalog snapshot inputs |
| `query_json` | `json` | False | 1 | Filters/groupings/metric/window/weight/paging/revision |
| `reducer_version` | `utf8` | False | 1 | Actual reducer code version or proposed marker |
| `analysis_version` | `utf8` | False | 1 | Actual analysis code version or proposed marker |
| `truncated` | `bool` | False | 1 | True only for explicitly labeled preview |
| `continuation_token` | `utf8` | True | 1 | Page token tied to immutable query+sort+catalog snapshot |

## `posterior_draws`
Grain: one saved fit × chain × draw × scalar parameter. Primary key: `fit_id`, `chain_id`, `draw_id`, `parameter_path`. Tier: `conditional_saved`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable deterministic row identity within table |
| `reduction_id` | `utf8` | False | 1 | Versioned reduction invocation/catalog identity |
| `source_asset_id` | `utf8` | True | 1 | Exact member/derived-input evidence anchor; null only for declared-only or purely derived rows |
| `fit_id` | `utf8` | False | 1 | Fit identity tied to exact reduced inputs/model/source |
| `chain_id` | `int64` | False | 1 | Saved MCMC chain |
| `draw_id` | `int64` | False | 1 | Post-warmup draw index |
| `parameter_path` | `utf8` | False | 1 | Parameter including array index |
| `value` | `float64` | False | parameter-dependent | Actual saved draw; no reconstructed draws from quantiles |
| `diagnostics_json` | `json` | False | 1 | Divergences/Rhat/ESS/treedepth/model validity and warmup handling |
| `input_lineage_json` | `json` | False | 1 | Simulation/observation fitting inputs and model version |

## `source_objects`
Grain: one observed physical object version/pin in one listing snapshot. Primary key: `snapshot_id`, `object_id`. Tier: `operational_catalog`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable row identity |
| `reduction_id` | `utf8` | False | 1 | Reducer invocation identity, not scientific attempt |
| `snapshot_id` | `utf8` | False | 1 | Frozen non-atomic listing snapshot |
| `object_id` | `utf8` | False | 1 | Hash of bucket/key and version or ETag identity |
| `bucket` | `utf8` | False | 1 | Actual source bucket |
| `key` | `utf8` | False | 1 | Full object key, not basename |
| `prefix_family` | `utf8` | False | 1 | Discovered family; explicit unregistered/unknown allowed |
| `version_id` | `utf8` | True | 1 | Non-null immutable version if verified by HEAD; literal null is not immutable |
| `etag` | `utf8` | True | 1 | Opaque conditional-read identity; not assumed MD5 |
| `pin_kind` | `utf8` | False | 1 | version_id, if_match_etag, or unpinned_blocked |
| `bytes_stored` | `int64` | True | byte | HEAD/list stored bytes |
| `last_modified_utc` | `utf8` | True | UTC | Observed object modification timestamp |
| `storage_class` | `utf8` | True | 1 | Observed storage class |
| `listing_start_utc` | `utf8` | False | UTC | Snapshot observation window start |
| `listing_end_utc` | `utf8` | False | UTC | Snapshot observation window end |
| `discovery_root` | `utf8` | False | 1 | Authorized root listing used to discover this object |
| `identity_evidence_json` | `json` | False | 1 | HEAD/list metadata and provenance; no credentials |
| `read_state` | `utf8` | False | 1 | Typed read/blocked status Allowed: available, missing_member, missing_object, access_denied, archived_unrestored, corrupt_archive, crc_failure, decode_failure, source_changed, unsupported_schema, unsupported_compression, resource_limit, not_yet_read |
| `scope_delta` | `bool` | False | 1 | New versus dated scope |

## `source_links`
Grain: one justified directed provenance/dedup edge. Primary key: `link_id`. Tier: `operational_catalog`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable row identity |
| `reduction_id` | `utf8` | False | 1 | Reducer invocation identity, not scientific attempt |
| `link_id` | `utf8` | False | 1 | Stable edge ID |
| `from_table` | `utf8` | False | 1 | Canonical table |
| `from_row_id` | `utf8` | False | 1 | Input row |
| `to_table` | `utf8` | False | 1 | Canonical table |
| `to_row_id` | `utf8` | False | 1 | Output row |
| `relation` | `utf8` | False | 1 | derived_from, contains, same_execution, conflicts_with, supersedes_target, or source_equivalent |
| `evidence_json` | `json` | False | 1 | Exact object/member/adapter/key mapping evidence |
| `confidence` | `utf8` | False | 1 | direct, documentary, inferred, unresolved |
| `selection_effect` | `utf8` | False | 1 | No discard unless an explicit selection rule authorizes it |

## `coverage_cells`
Grain: one declared/discovered design cell and execution selection scope. Primary key: `scope_id`. Tier: `operational_catalog`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable row identity |
| `reduction_id` | `utf8` | False | 1 | Reducer invocation identity, not scientific attempt |
| `scope_id` | `utf8` | False | 1 | Campaign/stage/scientific-attempt/cell selection |
| `campaign_id` | `utf8` | False | 1 | Canonical campaign |
| `stage_id` | `utf8` | False | 1 | Stage |
| `attempt_id` | `utf8` | False | 1 | Scientific attempt |
| `cell_id` | `utf8` | False | 1 | Logical design coordinate, not an object |
| `declared_runs` | `int64` | True | run | Ledger/design expected runs; null if unknown |
| `landed_physical_objects` | `int64` | True | object | Distinct physical source objects, not members |
| `indexed_run_members` | `int64` | True | run_member | Logical run groups indexed inside objects |
| `parsed_execution_rows` | `int64` | True | execution | Successfully parsed executions |
| `duplicate_copies` | `int64` | True | copy | Proved duplicate copies, not reruns |
| `conflicting_rows` | `int64` | True | row | Ambiguous duplicates/versions |
| `selected_unique_runs` | `int64` | True | run | Selected logical runs under frozen policy |
| `eligible_runs` | `int64` | True | run | Metric-specific eligible runs, or null pending metric |
| `missing_or_unread_runs` | `int64` | True | run | Expected minus accounted when comparable; otherwise unknown |
| `coverage_status` | `utf8` | False | 1 | complete, partial, absent, unsupported, blocked, or unassessable Allowed: complete, partial, absent, unsupported, blocked, unassessable |
| `metric_scope_json` | `json` | False | 1 | Per-family availability, reason and numerator/denominator accounting |
| `evidence_json` | `json` | False | 1 | Expected/observed scopes and reconciliation equation |

## `catalog_partitions`
Grain: one immutable derived Parquet/export partition. Primary key: `partition_id`. Tier: `operational_catalog`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable row identity |
| `reduction_id` | `utf8` | False | 1 | Reducer invocation identity, not scientific attempt |
| `partition_id` | `utf8` | False | 1 | Partition identity |
| `catalog_snapshot_id` | `utf8` | False | 1 | Published immutable catalog |
| `table_name` | `utf8` | False | 1 | Canonical table |
| `uri` | `utf8` | False | 1 | S3 derived object URI |
| `sha256` | `utf8` | False | 1 | Actual derived-file hash |
| `rows` | `int64` | False | row | Logical table rows |
| `bytes_stored` | `int64` | False | byte | Stored partition size |
| `schema_version` | `utf8` | False | 1 | Exact schema |
| `adapter_version` | `utf8` | False | 1 | Exact adapter registry version |
| `min_key_json` | `json` | False | 1 | Stable sort lower bound |
| `max_key_json` | `json` | False | 1 | Stable sort upper bound |
| `statistics_json` | `json` | False | 1 | Column bounds/nulls/coverage at valid table grain |
| `committed` | `bool` | False | 1 | Visible only through finalized COMMIT |

## `reduction_attempts`
Grain: one immutable reduction or query execution request. Primary key: `reduction_id`. Tier: `operational_catalog`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable row identity |
| `reduction_id` | `utf8` | False | 1 | Reducer invocation identity, not scientific attempt |
| `fingerprint` | `utf8` | False | 1 | Request+inventory+code+image+adapter+scope identity |
| `parent_reduction_id` | `utf8` | True | 1 | Resume/supersession parent |
| `request_sha256` | `utf8` | False | 1 | Frozen request |
| `inventory_sha256` | `utf8` | True | 1 | Frozen input scope |
| `implementation_sha` | `utf8` | False | 1 | Reducer source; distinct from engine SHA |
| `image_digest` | `utf8` | False | 1 | Reducer image digest |
| `adapter_registry_sha256` | `utf8` | False | 1 | Adapter versions |
| `phase` | `utf8` | False | 1 | Admitted phase |
| `admission_id` | `utf8` | True | 1 | Scope/budget authorization reference |
| `status` | `utf8` | False | 1 | Lifecycle status Allowed: planned, blocked, admitted, queued, running, checkpointed, budget_stopped, source_changed, quarantined, partial, completed, failed, cancelled, return_blocked, unknown |
| `budget_json` | `json` | False | 1 | Reserved/spent/remaining including retries |
| `checkpoint_uri` | `utf8` | True | 1 | Immutable checkpoint |
| `coverage_json` | `json` | False | 1 | Declared/landed/parsed/selected/failed/unsupported |
| `start_utc` | `utf8` | True | UTC | Phase start |
| `end_utc` | `utf8` | True | UTC | Phase end |

## `receipts`
Grain: one durable attempt/status receipt revision. Primary key: `receipt_id`. Tier: `operational_catalog`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable row identity |
| `reduction_id` | `utf8` | False | 1 | Reducer invocation identity, not scientific attempt |
| `receipt_id` | `utf8` | False | 1 | Stable immutable receipt |
| `request_id` | `utf8` | False | 1 | Request correlation |
| `github_run_id` | `utf8` | True | 1 | Workflow ID |
| `github_attempt` | `int64` | True | 1 | Workflow attempt |
| `batch_job_ids_json` | `json` | False | 1 | Bounded inline IDs or pinned child-page index |
| `status` | `utf8` | False | 1 | Qualified attempt status, not blanket success Allowed: planned, blocked, admitted, queued, running, checkpointed, budget_stopped, source_changed, quarantined, partial, completed, failed, cancelled, return_blocked, unknown |
| `receipt_uri` | `utf8` | False | 1 | Durable S3 receipt |
| `receipt_sha256` | `utf8` | False | 1 | Receipt hash |
| `catalog_uri` | `utf8` | True | 1 | Frozen catalog if present |
| `catalog_sha256` | `utf8` | True | 1 | Catalog hash |
| `continuation_json` | `json` | False | 1 | Phase/query/page continuation or explicit null |
| `error_json` | `json` | False | 1 | Typed failures and owner/fallback |
| `budget_json` | `json` | False | 1 | Spent and remaining |
| `created_utc` | `utf8` | False | UTC | Receipt timestamp |

## `query_pages`
Grain: one bounded deterministic query page. Primary key: `query_id`, `page_id`. Tier: `operational_catalog`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable row identity |
| `reduction_id` | `utf8` | False | 1 | Reducer invocation identity, not scientific attempt |
| `query_id` | `utf8` | False | 1 | Frozen query hash/ID |
| `page_id` | `utf8` | False | 1 | Stable page ID |
| `catalog_snapshot_id` | `utf8` | False | 1 | Frozen catalog |
| `query_sha256` | `utf8` | False | 1 | Query AST and estimand hash |
| `uri` | `utf8` | False | 1 | Derived JSONL/Parquet export |
| `sha256` | `utf8` | False | 1 | Export bytes hash |
| `returned_rows` | `int64` | False | row | Returned rows |
| `scanned_rows` | `int64` | True | row | Actual query scan accounting |
| `scanned_bytes` | `int64` | False | byte | Actual scanned bytes |
| `complete` | `bool` | False | 1 | End of frozen query selection |
| `next_cursor_json` | `json` | False | 1 | Bound query/catalog/order/key token or null |
| `selection_counts_json` | `json` | False | 1 | Eligible/observed/missing/censored/selected units and weights |
| `oversized_rows_json` | `json` | False | 1 | Explicit ROW_TOO_LARGE; never omitted silently |

## `acknowledgments`
Grain: one qualified automated Edison ingestion acknowledgment. Primary key: `ack_id`. Tier: `operational_catalog`.

| Field | Type | Nullable | Unit | Definition / enum |
|---|---|---|---|---|
| `row_id` | `utf8` | False | 1 | Stable row identity |
| `reduction_id` | `utf8` | False | 1 | Reducer invocation identity, not scientific attempt |
| `ack_id` | `utf8` | False | 1 | Idempotent acknowledgement identity |
| `receipt_id` | `utf8` | False | 1 | Receipt acknowledged |
| `query_id` | `utf8` | True | 1 | Query if applicable |
| `page_ids_json` | `json` | False | 1 | Exact accepted page IDs |
| `project_asset_ids_json` | `json` | False | 1 | Durable Edison assets; not ephemeral URLs |
| `accepted_hashes_json` | `json` | False | 1 | Verified artifact and member hashes |
| `qualification_json` | `json` | False | 1 | Exact status, coverage/missingness/scientific limits accepted |
| `next_cursor_json` | `json` | False | 1 | Saved resumable client cursor |
| `acknowledged_utc` | `utf8` | False | UTC | Durable ingestion time |

## Scientific metric definitions

All 33 versioned definitions below retain the original scientific lane values exactly.

### `infection_ever_person_risk.v1`
- Numerator: distinct eligible agents ever infected within defined followup, including imported infection if named
- Denominator: distinct eligible agents in specified ever-aboard or boarding cohort
- Unit: proportion; domain: latent_truth; condition: unconditional
- Definition notes: First infection/person risk, not sum episodes; imported and aboard-acquired can overlap. Cannot substitute final I+R in an open/reinfection/multipathogen run.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `infection_aboard_person_risk.v1`
- Numerator: distinct agents with >=1 aboard-acquired episode during window
- Denominator: agents eligible for aboard acquisition under explicit susceptibility/reinfection rule
- Unit: proportion; domain: latent_truth; condition: unconditional
- Definition notes: If denominator includes already-infected imports, label total-cohort risk; susceptible-at-start risk is a distinct estimand. Epoch-zero fiat seeds follow writer convention and must not silently become imports.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `infection_import_person_fraction.v1`
- Numerator: distinct agents carrying an infection at entry, with entry definition
- Denominator: distinct entrants in entry cohort
- Unit: proportion; domain: latent_truth; condition: unconditional
- Definition notes: Boarding imports, later shore imports and supply-origin exposure are different channels. One person may import and reacquire; no subtraction to obtain acquired count without overlap.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `infection_episode_incidence_rate.v1`
- Numerator: number of new infection episodes during window, excluding specified imported episodes
- Denominator: susceptible person-hours using episode eligibility
- Unit: episode/person*h; domain: latent_truth; condition: unconditional
- Definition notes: Episodes != unique persons; recurrent-risk eligibility/version mandatory.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `symptomatic_course_risk.v1`
- Numerator: distinct infected course-cohort persons whose complete relevant clinical course becomes symptomatic
- Denominator: distinct infected eligible course-cohort persons
- Unit: proportion; domain: symptomatic_course; condition: unconditional
- Definition notes: Needs saved future course/completed followup; incomplete courses censored or unavailable. Never infer from symptomatic epochs at voyage end.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `symptomatic_onboard_person_risk.v1`
- Numerator: distinct eligible persons with >=1 symptomatic period while aboard during window
- Denominator: matching at-risk aboard cohort
- Unit: proportion; domain: onboard_symptoms; condition: unconditional
- Definition notes: Separate any-cause syndrome from pathogen-specific attributed symptoms. Boarding-symptomatic prevalence is separately labeled.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `symptomatic_onboard_burden.v1`
- Numerator: symptomatic eligible person-hours aboard
- Denominator: eligible person-hours aboard
- Unit: proportion; domain: onboard_symptoms; condition: unconditional
- Definition notes: 
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `reported_true_person_risk.v1`
- Numerator: distinct eligible symptomatic true-case persons ever reported during window
- Denominator: explicit aboard or infected or symptomatic eligible cohort
- Unit: proportion; domain: reported; condition: unconditional
- Definition notes: Source symptomatic true-positive ID set is not all syndromic signals; observation feedback may change disease and test availability. Keep noise reports separate.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `report_capture_given_symptoms.v1`
- Numerator: distinct symptomatic eligible persons reported
- Denominator: distinct symptomatic report-eligible persons
- Unit: proportion; domain: reported; condition: symptomatic_and_report_eligible
- Definition notes: Condition set must be evaluated in the same window. Eventual symptomatic course does not equal report-eligible while aboard.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `reported_noise_count.v1`
- Numerator: distinct noise-case IDs or noise report events, explicitly named
- Denominator: 1
- Unit: person or event; domain: reported; condition: unconditional
- Definition notes: Do not add unique noise persons to true-case persons unless disjoint IDs proved; raw observation count kept separately.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `tested_person_fraction.v1`
- Numerator: distinct eligible persons tested during window
- Denominator: distinct test-eligible persons during window
- Unit: proportion; domain: tested; condition: unconditional
- Definition notes: Tests, specimens, assays, positives and tested persons all separate; repeat tests do not add people.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `lab_confirmed_person_fraction.v1`
- Numerator: distinct persons with qualifying lab-positive rule
- Denominator: explicit test-eligible OR tested OR cohort population
- Unit: proportion; domain: lab_confirmed; condition: unconditional
- Definition notes: Denominator choice creates separate metric IDs/condition IDs; turnaround, LOD, equivocal and repeat testing rules explicit.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `test_positive_assay_fraction.v1`
- Numerator: positive qualifying assays
- Denominator: valid assays with known result by cutoff
- Unit: proportion; domain: tested; condition: unconditional
- Definition notes: Not agent AR; pending/censored/invalid tests listed separately.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `posting_probability.v1`
- Numerator: selected completed voyages meeting exact either-role reported-case threshold policy
- Denominator: all eligible selected completed voyages
- Unit: proportion; domain: reported; condition: unconditional
- Definition notes: Threshold/source version explicit; evaluate unrounded count >= ceil(threshold*N) for >= rule only when exact predicate agrees. Unknown passenger/crew complement blocks derived post, not zero.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `outbreak_probability.v1`
- Numerator: selected eligible voyages meeting versioned takeoff/outbreak predicate
- Denominator: all eligible selected completed voyages
- Unit: proportion; domain: latent_truth; condition: unconditional
- Definition notes: Not interchangeable with posted, any infection, seed establishment, or VSP response trigger.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `conditional_metric.v1`
- Numerator: metric evaluated among units satisfying named post/outbreak/entry channel/minted/excursion conjunction
- Denominator: matching eligible conditioned units
- Unit: metric-dependent; domain: mechanism; condition: explicit Boolean AST with conditioning grain
- Definition notes: Always publish unconditional alongside conditioned, P(condition), count eligible/observed/missing and policy feedback context; empty condition undefined not zero.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `case_entry_channel_fraction.v1`
- Numerator: distinct qualifying cases in saved entry-channel category
- Denominator: distinct qualifying cases across explicit exhaustive channel set
- Unit: proportion; domain: mechanism; condition: unconditional
- Definition notes: Boarding_import/supply_chain/aboard is reported-case mass-dominance classifier in current source, NOT a causal counterfactual fraction. Supply vs aboard ties follow writer; mixed fractions retained if saved.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `case_dominant_route_fraction.v1`
- Numerator: distinct established/reported cases assigned selected dominant route by saved rule
- Denominator: matching assigned plus explicit unknown/unattributed cases as declared
- Unit: proportion; domain: mechanism; condition: unconditional
- Definition notes: Argmax acquired dose at establishment; route/channel and progression distinct. Retain tie/fallback/missing classification, and case counts not only percentages.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `route_dose_share.v1`
- Numerator: sum credited/acquired dose in route under one unit/pathogen definition
- Denominator: sum credited/acquired dose over declared routes
- Unit: proportion; domain: mechanism; condition: unconditional
- Definition notes: Delivered vs credited separate; noncausal share. GEC/copies/PFU/aerosol mass incomparable absent validated conversion. Withdrawn absolute dose remains historical/qualified.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `mechanism_event_rate.v1`
- Numerator: saved qualifying events
- Denominator: eligible person-hours or source opportunity count
- Unit: event/declared exposure; domain: mechanism; condition: unconditional
- Definition notes: Event count versus unique actors/recipients/source objects distinct. Multiple recipients per event not multiple independent voyages.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `role_participation_fraction.v1`
- Numerator: distinct role-members participating as actor/recipient/caregiver/etc. during window
- Denominator: distinct role-members eligible for that activity during window
- Unit: proportion; domain: mechanism; condition: unconditional
- Definition notes: Role at event-time plus occupation and primary role; time-varying overlap unioned. Role complements alone cannot establish source/responder eligibility.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `role_participation_rate.v1`
- Numerator: role-specific qualifying event participations
- Denominator: eligible role-member person-hours
- Unit: participation/person*h; domain: mechanism; condition: unconditional
- Definition notes: One person can occupy several functions; no summing functional-role denominators as total crew.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `source_realization_probability.v1`
- Numerator: voyages or stations with >=1 realized source/object, separate units
- Denominator: eligible voyages or source stations
- Unit: proportion; domain: mechanism; condition: unconditional
- Definition notes: Save nominal q, actual drawn q, station uniforms/witness if saved, realized counts and source IDs. No causal reclassification from infection endpoint.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `conversion_post_given_excursion.v1`
- Numerator: voyages posted AND exact excursion predicate holds
- Denominator: voyages with exact excursion predicate
- Unit: proportion; domain: reported; condition: excursion
- Definition notes: Legacy operational excursion is >=1 infection dominant-routed common_source_food. Minted object, nonzero delivered dose and early shared-dose exposure are DIFFERENT predicates.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `ps01_D2_frozen_relative.v1`
- Numerator: median posted passenger AR per in-band rung/hull
- Denominator: in-campaign ind median at same hull/endpoint
- Unit: ratio; domain: reported; condition: posted AND in_band_rung
- Definition notes: Frozen interval [0.5,2]. Compute per-rung and any separately predeclared pooling. Source E25; operational absolute 0.04 table remains separate.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `ps01_D2_operational_absolute.v1`
- Numerator: median posted passenger AR per arm/hull
- Denominator: 1
- Unit: proportion; domain: reported; condition: posted
- Definition notes: Legacy reporter >=0.04 edge. Does NOT resolve frozen D2; endpoint mapping of pax-AR must be confirmed in source version.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `ps01_D3_frozen_converted_AR.v1`
- Numerator: median converted-pax-AR among posted voyages pooled in-band per hull
- Denominator: ind counterpart median
- Unit: ratio; domain: reported; condition: posted AND in_band
- Definition notes: BLOCKED_DEFINITION: design does not fully specify converted-pax-AR numerator/population. Do NOT substitute excursion->posting probability or guess aboard/food-route AR. Preserve candidate raw counts and obtain explicit definition adjudication; report unresolved gate.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `ps01_D3_operational_conversion.v1`
- Numerator: P(post|legacy excursion,object arm,hull)
- Denominator: P(post|legacy excursion,ind,hull)
- Unit: ratio; domain: reported; condition: legacy excursion
- Definition notes: Empty excursion or zero ind conversion -> undefined reason; no 0/0 default. Separate probability components and paired changes.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `burst_acquisition_closed_W.v1`
- Numerator: maximum number acquisitions within [t,t+W] over saved acquisition times
- Denominator: number acquisitions included in same exact filter
- Unit: proportion; domain: latent_truth; condition: unconditional
- Definition notes: Legacy closed span <=W includes both endpoints; W=48 epochs is not necessarily 48h. Unit/clock and e>0 filter explicit. Ties choose earliest maximizing left boundary. If no acquisitions: undefined/no_events, retain legacy zero in native scalar only. Count episodes vs persons follows saved acquisition schema.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `burst_observed_onset_halfopen_W.v1`
- Numerator: maximum number qualifying observed onsets in [t,t+W)
- Denominator: all qualifying observed onsets
- Unit: proportion; domain: onboard_symptoms; condition: unconditional
- Definition notes: New proposed physical-hour endpoint, NOT a rename of acquisition burst. Inferred interval onsets yield bounds/interval method not invented exact times. Window type, alignment and minimum count frozen.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `response_delay.v1`
- Numerator: endpoint time minus named origin
- Denominator: 1
- Unit: h; domain: response; condition: unconditional
- Definition notes: Endpoint exact/left/right/interval censor and competing events retained. peak_epoch-detection_epoch is lead-time-to-peak, NOT onset-to-detection delay; negative values can be meaningful.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `economic_cost_per_case_averted.v1`
- Numerator: paired incremental cost
- Denominator: paired difference in versioned cases
- Unit: currency/case; domain: economic; condition: unconditional
- Definition notes: Use exact cost currency year, opportunity units and paired seeds. Zero/negative denominator reported, not infinity hidden or favorable-only ratios; effect requires valid intervention contrast.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

### `surveillance_detection_probability.v1`
- Numerator: eligible voyages/lineages detected by deadline under observed channel
- Denominator: all eligible latent-introduction or risk-set units at stated grain
- Unit: proportion; domain: reported; condition: unconditional
- Definition notes: Observed vs truth channels, specimen sampling and information feedback explicit; lineage census and observed sequence line list not merged as observations.
- Aggregate rule: Keep exact per-run numerator/denominator/value; define mean-run versus pooled versus hierarchy explicitly.

## Status namespace authority

See [STATUS_NAMESPACES.json](STATUS_NAMESPACES.json) and its [reading view](STATUS_NAMESPACES.md). The 26 scientific tables/382 fields and 33 metric definitions remain exactly unchanged. Four existing operational fields gain strict enums; no fields or tables are added. Narrative value aliases are not metric-value enum literals; precise read failures use canonical `data_gaps.reason` plus `detail`.
