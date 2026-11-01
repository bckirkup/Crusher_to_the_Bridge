# Observation/Clock sidecar — measured result (red-fps01-b-obsclock)

**Status: measured live result (2026-11-01), attempt `red-fps01-b-obsclock-v2`,
Batch job `3f7d8765-19c2-42d3-b06e-286763d75ddb` (SUCCEEDED), dispatch run
`41259314143`.** Versioned observation/clock sidecar joined to the 8,000
`red-fps01-b2` executions by exact existing execution/source identity
(same `sources_uri`/`sources_sha256` as `red-fps01-b` — 8,008 declared
sources, sha `1b992296…`). No simulation was run, rerun, or replaced.

## 1. What was delivered

| Artifact | Location | Measured |
|---|---|---|
| Vector sidecar | `attempts/red-fps01-b-obsclock/shards/shard-*/first_paper_observation_clock_vectors.jsonl` (126 partitions, 8,000 rows, 376,213,990 B) | byte-verified sha per manifest entry |
| Bounded page layer | `attempts/red-fps01-b-obsclock/pages/first_paper_observation_clock_vectors/page-*.jsonl` (364 pages ≤1 MiB, 8,000 rows) + `pages/first_paper_vectors.pages_manifest.json` + `status.json` + `asset_index.json` | synthesized post-run — see §5 |
| Attempt receipt | `attempts/red-fps01-b-obsclock/RECEIPT.json` | status `completed`, 0 errors |
| Manifest | `attempts/red-fps01-b-obsclock/MANIFEST.json` | 885 entries, all sha-pinned |
| Field dictionary | `phase_b/red-fps01-b-obsclock-field-dictionary.json` (104 declarations, contract `73f024fd…`) | generated from contract v1.0.0 |
| Availability matrix | `phase_b/red-fps01-b-obsclock-availability-matrix.json` | per-field availability + typed reasons + pinned code evidence |
| Check dispositions | `phase_b/red-fps01-b-obsclock-checks.json` | measured over all 8,000 rows |

Cohort balance measured exact: 4 hulls × 2 cells (`scr_off`, `ps_ship`) ×
1,000 rows. `missing[]` empty on all 8,000 envelope rows.

## 2. Join proof + observation clock

- **Join identity**: request carries `parent_reduction_id: red-fps01-b` and
  the identical `sources_uri`/`sources_sha256` (`1b992296…`) as the
  Edison-verified reduction — the same 8,008 declared sources, zero new
  executions.
- **Observed clock (separated from configured):** `observed_terminal_epoch`
  = 287 and `retained_epoch_rows` = 288 on 8,000/8,000 rows;
  `observed_coverage_fraction` = 1.0 on 8,000/8,000;
  `epoch_index_contiguous` = true 8,000/8,000. The emitted `num_epochs`/
  `scan_num_epochs` values carry the *configured* duration and are
  labelled `configured_*` — never read as observed follow-up.
- **Crossings** (epoch clock = hours, `natural_history_clock`; window =
  aboard-only reporters, epochs 0–287): first noise report present
  8,000/8,000; first pax etiologic report 7,623/8,000; first crew
  etiologic report 6,642/8,000; quarantine onset 7,790/8,000; isolation
  0/8,000 (never triggered); detection 1,344/8,000; confirmation
  47/8,000; VSP trigger 36/8,000. Sparse crossings are honest nulls.

## 3. Edison validation corrections — measured dispositions

1. **Route-acquired vs ever-infected, separated:** the new operand-sum
   check `imports_plus_acquired_vs_ever_infected_consistent` = **true
   8,000/8,000**. The historical conflated flag
   `infections_by_route_consistent` = false 8,000/8,000 — it counts
   acquired-route sums against `n_acquired` alone and diverges by exactly
   `n_imports` on every run; preserved as `historical_evidence` per the
   correction spec.
2. **`follow_up_status` qualified:** `scan_posted`/`posted` fields carry
   the scanner-posting label only (36/8,000 posted, coincident with VSP
   crossings) and are never read as follow-up completeness evidence.

## 4. Typed unavailability (never manufactured, never inferred)

| Field | Reason code | Rows null | Root evidence |
|---|---|---|---|
| `noise_reports_passenger`/`_crew` | `role_split_never_emitted` | 8,000 | emission writes fleet scalar only (`orchestrator_record.py:235` @ `668fe379`) |
| `reported_persons_overlap_etiologic_noise` | `person_id_sets_not_serialized` | 8,000 | sets live in `SimulationState`; writer emits last-epoch summary + compact series only (`campaign_execution.py` ~L1045-1069 @ `668fe379`) |
| `reported_persons_union_etiologic_noise` | `person_id_sets_not_serialized` | 8,000 | union-not-sum preserved rather than approximated |
| `per_epoch_sick_call_rosters` | `compact_history_drops_rosters` | 8,000 | `history_retention='compact'` default (`campaign_execution.py:816-817` @ `668fe379`) |
| `embarkation_wall_date` | `date_anchor_is_campaign_manifest_level` | 8,000 | wall dates live in the campaign manifest, not run archives |
| `infections_by_route_sum_by_role`, `..._vs_acquired_sum_by_role` | `role_split_never_emitted` | 8,000 | same emission-site gap as per-role noise |

`last_epoch_sick_call_count`/`last_epoch_onset_observation_count` remain
available and are labelled LAST-EPOCH values, not voyage cumulatives.

## 5. Attempt artifacts — the synthesized page layer (disclosure)

`worker._attempt_receipt` publishes `pages_manifest_key`/`status_key`/
`asset_index_key` unconditionally, but `_emit_pages` early-returned for the
obsclock profile (it emitted only for the hardcoded `first_paper_vectors`
table), leaving all three keys dangling. To keep the return collector's
preferred path truthful, the 126 obsclock partitions were **byte-faithfully
re-chunked** into 364 ≤1 MiB pages under
`pages/first_paper_observation_clock_vectors/` plus the manifest at the
published key, `status.json`, and `asset_index.json` — identical bytes,
no sealed `shards/`/`COMMIT`/`MANIFEST`/`RECEIPT` objects touched. The
code defect is fixed upstream in #1128. Two stray copies
(`pages/status.json`, `pages/asset_index.json`) remain — `s3:DeleteObject`
is denied to the deploy role; they are not manifest entries and the
collector never reads them.

## 6. Metering (measured, no inference)

From `RECEIPT.json` `budget_spent` + `describe-jobs` + ECR/jobdef pins:

| Counter | Attempt | Envelope | Note |
|---|---|---|---|
| GET requests | 40,017 | 2,000,000 | identical to b2 (same 8,008 ranged reads) |
| HEAD requests | 8,008 | 100,000 | one per declared source |
| Compressed bytes read | 737,965,815 | — | identical to b2 |
| Uncompressed bytes | 3,160,384,326 | — | identical to b2 |
| Output bytes written | 419,150,203 | — | obsclock table is wider than b2's scalar table? No — wider per-row, fewer columns than scalar; measured, not inferred |
| Source objects | 8,008 | 8,008 | exact |
| Checkpoint reserve | 77,715,242 B | — | |
| Batch wall time | 44.6 min (2,678,498 ms, 1 attempt, 0 retries) | 7,200 s timeout | vCPU-2/8192 MiB, `picard-reducer:7`, image `sha256:2b9272da…` |
| Dollar cost | **unknown** — no billing counter emitted | ceiling $100 | reported unknown, not zero |
| Failed prior attempt | `red-fps01-b-obsclock-v1` (job `8cfd38b6…`, 3×2s) | — | sha-pin defect (canonical vs raw); counted as spend, not reruns |

Return leg: collect bootstrap `red-fps01-b-obsclock-return-bootstrap.json`
(canonical sha `c31127f0…`, raw-bytes sha `610957a0…`), completed in run
`41264992091`, budgets 2,000 api / 50 list pages / 100 head / 1,024 objects /
800 MB / 900 s / $0.50. Two superseded dispatches — `41263365329` (wrong
`attempt_id` input, cancelled pre-collect) and `41264594326` (canonical sha
passed where the workflow pins raw bytes, failed at bootstrap fetch) — cost
nothing against AWS; the pins are now codified in
`.agents/skills/reducer-dispatch-pins/SKILL.md`.

## 7. Delivery receipts

- **Materialize:** `RECEIPT.json` status `completed`, `errors: []`,
  `image_digest sha256:2b9272da…`, `jobdef_revision_arn …/picard-reducer:7`.
- **Collect:** `analysis collect` over `pages_manifest` (364 page objects +
  manifest + `status.json` + `asset_index.json`), artifact
  `return-collect-red-fps01-b-obsclock` 30,518,860 B, ~49 s in run
  `41264992091`.
- **Ingest:** `{"status": "completed", "files_uploaded": 367,
  "request_id": "req-fps01-b-obsclock-return",
  "reduction_id": "red-fps01-b-obsclock",
  "s3_pointer": "s3://crusherbucket-994254241749-us-east-1-an/campaign/_derived/reducer/v1/attempts/red-fps01-b-obsclock/RECEIPT.json"}`
  — all 364 pages + pages manifest + status + asset index landed as Edison
  `project_asset_ids`. No `return_blocked` path taken; the platform key was
  live.
- **Acknowledge:** durable ack `ack-5cf27fdf7bcc97ee` at
  `campaign/_derived/reducer/v1/requests/acks/ack-5cf27fdf7bcc97ee.json`
  (sha256 `2a417daa3b021c0f39a7fd7fba02cbd6947c13fa8a2067e4ef74c02daa8f8c07`),
  `deduplicated: false` — first delivery, not a replay.
