# Status namespaces — proposed contract, not implementation

I preserve the original 26 scientific tables, 382 fields and 33 metric definitions. Only four existing operational fields gain strict enums. [Machine authority](STATUS_NAMESPACES.json) maps aliases with evidence requirements; source census findings are unchanged.

## Separate field namespaces

| Table.field | Allowed literals / constraint | Meaning |
|---|---|---|
| `campaign_catalog.catalog_state` | `declared`, `outcomes_reported`, `assets_verified`, `partially_recovered`, `reduced`, `withdrawn`, `blocked`, `unknown` | catalog evidence |
| `attempts.attempt_kind` | `exploratory`, `confirmatory`, `revision`, `review_response`, `canary`, `smoke`, `reanalysis`, `unknown` | Scientific lifecycle |
| `attempts.scientific_approval_state` | Original open field preserved; no invented enum | historical scientific approval evidence, not job lifecycle or fresh query approval |
| `runs.execution_state` | `declared`, `completed`, `partial`, `failed`, `cancelled`, `unknown` | historical simulation execution |
| `runs.selection_state` | `selected`, `duplicate_alias`, `retry_not_selected`, `identity_conflict`, `quarantined`, `pending` | scientific replicate selection |
| `runs.selection_reason` | Original open field preserved; no invented enum | Explicit dedup/retry/claim use basis |
| `assets.asset_kind` | `container`, `member`, `sidecar`, `parquet`, `manifest`, `log`, `local_source` | Container or member |
| `assets.hash_scope` | `container_bytes`, `uncompressed_member`, `file_bytes`, `not_computed` | Container hashes never compared as member hashes |
| `assets.read_state` | `listed`, `indexed`, `read`, `parsed`, `malformed`, `unreachable`, `missing`, `not_requested` | scientific asset read/parse evidence |
| `capabilities.scope_kind` | `run`, `stage`, `campaign` | Scope type |
| `capabilities.availability` | `available_exact`, `available_rounded`, `recoverable_unread`, `derivable_exact`, `partial`, `not_saved`, `dropped_by_profile`, `not_applicable`, `unknown`, `blocked_identity`, `malformed`, `unreachable` | scoped scientific recoverability |
| `data_gaps.reason` | `not_saved`, `dropped_by_profile`, `member_missing`, `not_applicable`, `unknown_schema`, `malformed`, `unreachable`, `not_requested`, `identity_unresolved`, `incompatible_definition`, `denominator_zero`, `no_events`, `not_observed`, `not_identifiable`, `rounded_only`, `time_origin_unknown`, `partial_followup`, `unsupported_join` | canonical missing-value reason; precise operational reason remains in detail |
| `data_gaps.recoverability` | `read_existing`, `derive_existing`, `reconcile_identity`, `irrecoverable_existing`, `pending_inventory`, `not_applicable` | Recoverability state |
| `design_values.value_layer` | `nominal_design`, `resolved_config`, `realized_draw`, `realized_exposure`, `measured_outcome` | Do not substitute nominal for realized |
| `pair_links.pair_state` | `exact_design_pair`, `version_bridge_pair`, `partial_pair`, `unmatched`, `incompatible` | Eligibility |
| `pair_links.unmatched_reason` | Original open field preserved; no invented enum | Structurally optional for exact pairs |
| `role_dictionary.role_axis` | `primary_population`, `occupation`, `response_function`, `duty_state`, `source_eligibility`, `clinical_state`, `observation_state`, `spatial_context` | Orthogonal role axes |
| `agents.roster_scope` | `full_at_risk`, `infected_only`, `observed_only`, `event_participant_only`, `partial` | Full roster vs infected subset |
| `agents.boarding_state` | Original open field preserved; no invented enum | Saved infection/import and presence state |
| `population_intervals.population_basis` | `boarding_complement`, `unique_ever_aboard`, `susceptible_at_start`, `eligible_course_cohort`, `eligible_onboard`, `dynamic_at_risk`, `test_eligible`, `source_eligible`, `response_eligible`, `observed_roster` | Denominator semantics |
| `run_scalars.native_type` | `null`, `boolean`, `integer`, `number`, `string` | Original primitive |
| `run_scalars.mapping_state` | `verified`, `native_only`, `ambiguous`, `rounded_source` | Mapping status |
| `metrics.value_status` | `exact_emitted`, `exact_derived`, `rounded_emitted`, `partial`, `undefined`, `unavailable` | metric value evidence; six original literals only |
| `metrics.endpoint_domain` | `latent_truth`, `symptomatic_course`, `onboard_symptoms`, `reported`, `tested`, `lab_confirmed`, `response`, `mechanism`, `economic`, `external_observed` | Truth, clinical, observation, policy, economic distinct |
| `epoch_metrics.series_kind` | `state`, `incidence`, `cumulative`, `rate`, `integral`, `flag` | Series semantics |
| `epoch_metrics.value_status` | Original open field preserved; no invented enum | legacy time-series value evidence; no new enum imposed |
| `times_to_event.subject_kind` | `run`, `agent`, `episode`, `object`, `test`, `port_call` | Unit at risk |
| `times_to_event.censor_type` | `exact`, `right`, `left`, `interval`, `structural_nonoccurrence`, `not_at_risk`, `unknown` | clinical event-time censoring, not missingness or job failure |
| `times_to_event.event_domain` | `latent`, `observed`, `scheduled`, `inferred_interval` | Observed/latent/estimated |
| `event_participants.participation_kind` | `actor`, `source`, `recipient`, `exposed`, `responder`, `caregiver`, `service_provider`, `reporter`, `specimen_donor`, `tested`, `observer` | Directed and multi-person participation |
| `event_participants.participation_status` | Original open field preserved; no invented enum | Saved/derived/partial; count unique IDs separately from event rows |
| `mechanism_objects.end_reason` | Original open field preserved; no invented enum | Exhaustion/extent_met/horizon/etc. |
| `weights.unit_kind` | `run`, `seed_block`, `design_cell`, `vessel`, `voyage`, `person`, `posterior_draw`, `external_record` | Weight unit |
| `weights.weight_kind` | `equal_run`, `design`, `fleet`, `person`, `selection`, `posterior` | Simulation design/fleet/population/inverse probability/posterior separately |
| `weights.validity_status` | Original open field preserved; no invented enum | Qualified/unqualified/blocked; no weights borrowed silently across targets |
| `distributions.missing_reason_counts_json` | Original open field preserved; no invented enum | Typed reason counts incl structural zero/event absence |
| `source_objects.read_state` | `available`, `missing_member`, `missing_object`, `access_denied`, `archived_unrestored`, `corrupt_archive`, `crc_failure`, `decode_failure`, `source_changed`, `unsupported_schema`, `unsupported_compression`, `resource_limit`, `not_yet_read` | typed physical read operation result/reason |
| `coverage_cells.coverage_status` | `complete`, `partial`, `absent`, `unsupported`, `blocked`, `unassessable` | scope accounting, independent of lifecycle and exactness |
| `reduction_attempts.status` | `planned`, `blocked`, `admitted`, `queued`, `running`, `checkpointed`, `budget_stopped`, `source_changed`, `quarantined`, `partial`, `completed`, `failed`, `cancelled`, `return_blocked`, `unknown` | reducer job lifecycle only |
| `receipts.status` | `planned`, `blocked`, `admitted`, `queued`, `running`, `checkpointed`, `budget_stopped`, `source_changed`, `quarantined`, `partial`, `completed`, `failed`, `cancelled`, `return_blocked`, `unknown` | durable qualified operational lifecycle only |

## Source/read aliases

| Operation reason | assets.read_state | data_gaps.reason | Precise reason retained in detail |
|---|---|---|---|
| `available` | `read` | None — no read gap | `available` |
| `missing_member` | `missing` | `member_missing` | `missing_member` |
| `missing_object` | `missing` | `unreachable` | `missing_object` |
| `access_denied` | `unreachable` | `unreachable` | `access_denied` |
| `archived_unrestored` | `unreachable` | `unreachable` | `archived_unrestored` |
| `corrupt_archive` | `malformed` | `malformed` | `corrupt_archive` |
| `crc_failure` | `malformed` | `malformed` | `crc_failure` |
| `decode_failure` | `malformed` | `malformed` | `decode_failure` |
| `source_changed` | `unreachable` | `identity_unresolved` | `source_changed` |
| `unsupported_schema` | `malformed` | `unknown_schema` | `unsupported_schema` |
| `unsupported_compression` | `unreachable` | `unreachable` | `unsupported_compression` |
| `resource_limit` | `unreachable` | `unreachable` | `resource_limit` |
| `not_yet_read` | `not_requested` | `not_requested` | `not_yet_read` |

`source_objects.read_state` uses the operation reasons above, not the asset enum. `available` establishes a read, not an exact metric or parsed asset. Successful parse evidence may upgrade the asset to `parsed`. Never directly assign `crc_failure`, `source_changed`, `resource_limit` or another incompatible read reason to `assets.read_state` or `data_gaps.reason`.

## Evidence-qualified narrative conversion

- `available` becomes capability `available_exact` only with exact-value evidence, `available_rounded` only with rounded evidence, `recoverable_unread` only with verified member identity and supported read access; otherwise `unknown`.
- `documented_unverified` / `known_saved` become capability `recoverable_unread` only with verified member identity and supported read access; otherwise `unknown`, never presumed exact.
- `count_not_retained` / `counted_not_retained` become capability `not_saved` only with verified retention loss; otherwise `unknown`. `corrupt` requires verified parse failure to become `malformed`.
- Narrative `observed` requires exact/rounded evidence to become metric `exact_emitted`/`rounded_emitted`; `derived_supported` requires verified derivation for `exact_derived`. All other cases remain `unavailable` unless separately proved; a zero denominator is `undefined` with a gap, not zero.
- Clinical `censored` belongs in `times_to_event.censor_type` with the actual right/left/interval evidence. It does not create a seventh `metrics.value_status`. The long narrative alias list is not a canonical table enum.
- Generic missingness stays in `data_gaps.reason`; the precise read reason stays in `data_gaps.detail`. Clinical censoring, job lifecycle and historical approval are independent.
- A historical stopped job is not proof of data loss. Preserve historical scientific approval/source labels and evidence; do not turn unknown execution into completed or unknown approval into approved. Operational `completed` requires explicit completion evidence and does not certify coverage/scientific validity.

## Admission and implementation boundaries

Within a preapproved scientific scope/budget envelope, queries, pages, resumes, phases and campaigns receive automatic remaining-budget reservations and receipts. Human escalation is only for new scientific scope, budget-envelope exceptions or credential/permission exceptions. All proposed operations remain NOT_YET_IMPLEMENTED; no AWS work or production acceptance is claimed.
