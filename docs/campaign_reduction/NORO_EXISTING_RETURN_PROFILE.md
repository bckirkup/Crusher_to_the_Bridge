# `noro_existing_return` Extraction Profile (`noro_existing_return/1.0.0`)

Reducer extraction profile for returning completed voyage results from three existing norovirus campaigns on `s3://crusherbucket-994254241749-us-east-1-an`:

| Cohort | Campaign ID | S3 Prefix | Expected Voyages | Excluded Objects / Members |
|---|---|---|---:|---|
| `explorer_reconstruction` | `noro_explorer_reconstruction_01` | `campaign/noro_explorer_reconstruction_01/` | 600 | `sentinel_line_list.json` (not required for voyage rows) |
| `paper1_joint_eval` | `noro_paper1_joint_eval_01` | `campaign/noro_paper1_joint_eval_01/` | 896 | 800 `census_*` JSONL chunks + root `manifest.json` |
| `supply_solver_reference` | `noro_supply_solver_screen_01_bf0` | `campaign/noro_supply_solver_screen_01_bf0/` | 16 | `growth_census.json.gz` (~85 MB uncompressed/seed) and `rss_samples.json` |

Total intended voyage rows: **1,512** (600 + 896 + 16), emitted to `noro_existing_return_vectors.jsonl` via `campaign_reduction.yml` and returned via `campaign_return.yml`.

## Field Dictionary

| Column (`values.<col>`) | Explorer | Joint Eval | Solver Ref (`bf0`) | Notes / Provenance |
|---|---|---|---|---|
| `cohort`, `campaign`, `tier`, `arm`, `seed`, `platform`, `design_stratum`, `attempt_outcome` | Present | Present | Present | `design_stratum` separates `diagnostic`, `evaluation`, `reproduction`, Explorer tiers, and `solver_reference_bf0`. |
| `engine_git_sha` | Present | Present | Present | Recorded in `summary.json` / `joint_eval.json.gz`. |
| `image_digest` | Absent | Absent | Absent | `availability: not_recorded_in_run_archive` unless populated on `SourceSpec`. |
| `effective_modes` | `effective_state` | `effective_config` | `initiation.resolved` | Resolved effective mode block as archived. |
| `total_passengers`, `total_crew` | Present | Present | Present | Realized ship complements. |
| `initial_infected_total` | `len(initially_infected_agent_ids)` | Absent | `census.n_imports` | `null` + `not_recorded_in_archive` where absent. |
| `initial_infected_by_role` | `initiation_manifest.drawn_by_role` | `preboarding_declared_*` (`scope: preboarding_declared_only`) | Absent | Distinguishes realized drawn role counts from preboarding-declared counts. |
| `initial_disease_states` | `initiation_manifest.drawn_by_state` | Absent | Absent | Never inferred. |
| `burden` | Present | Present | Present (incl. `acquired_total`) | Explicit definitions embedded in `burden.definitions`. |
| `thresholds`, `first_role`, `final_role_category`, `role_checkpoints` | Present (`first_role` derived from `timeseries`) | Present (`first_role` explicit) | Present (`role_checkpoints` if archived) | `vsp_trigger_epoch`, `vsp_posted`, `trigger_status`. |
| `daily_onset_curves` | `onsets_by_day` (`all`, `excluding_declared_seeds`, `incident`) | `onsets_daily` + `day0_label` + `line_list_channels` | Absent | Named exclusions preserved verbatim. |
| `cumulative_reporting_curves` | `reporting_by_day` | `reported_daily_*` + cumulative sums + `day0_label` | Daily terminal counts from hourly `timeseries` | Preserves reporting trajectory without inventing unrecorded days. |
| `environment_summary` | Absent | Present (`joint_eval.json.gz`) | Absent | Voyage-level swab & tank counts, detections, censoring below LOD, quantifiable counts, units, `swab_rows_rule`, zones/instruments/streams, LOD/LOQ, and quantitative min/median/max/mean summaries. |
| `route_aggregates` | Present | Present | Present | Voyage-level `infections_by_dominant_route` and `infection_dose_share_by_route` (`granularity: voyage_aggregate_only`). |
| `acquisition_event_timestamps`, `sequencing_observations`, `zero_recovery_swab_rows` | Typed absence | Typed absence | Typed absence | Explicit `availability_fields` in `NORO_EXISTING_RETURN.json`. |

## Unchanged Design Metadata to Bundle at Return Time

- `campaigns/noro/paper1_joint_eval_01/design/seed_selection.json` (census counts, 20k frame, purposive diagnostic labels, independent-evaluation inclusion probabilities/weights, paired-seed blocks)
- Campaign `manifest.json` files for each of the three cohorts
