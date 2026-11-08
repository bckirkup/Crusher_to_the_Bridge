# first_paper_scalar — Paper-1 sensitivity screen report: NORO-PROVISIONED-SENSITIVITY-01 (12,672 vectors)

**Status: materialized — attempts `red-fps01-sens01-scout3` (1,536
vectors, Edison ack `ack-9523d1856c0a43cb`) and `red-fps01-sens01-main`
(11,136 vectors) both `completed`, 0 data gaps; main return leg to
Edison in flight (run 42495909835) — §6 is updated when the ack lands.**

Deliverable: `first_paper_vectors` on the `first_paper_scalar/1.5.0`
definition (cumulative role checkpoints days 3/7/10/12, PR #1156) for
all 12,672 nominal runs of the 2^(5-1) Resolution-V sensitivity screen
on the venue-02 spec — 16 Res-V profiles × 4 hulls × 3 venue arms = 192
cells, seed-paired with venue-02 — under
`campaign/_derived/reducer/v1/attempts/red-fps01-sens01-{scout3,main}/`
(RECEIPT/COMMIT/MANIFEST/status + bounded page layer), collected through
the bounded return path and delivered to Edison. Devin delivers raw
per-cell vectors; **Edison owns the factorial / effect analysis**,
including aliasing and sparse-event uncertainty. No COVID/flu, no engine
or config change beyond the seed-manifest sizing.

Operational record of every dispatch, job id, digest and measurement:
`campaigns/noro/provisioned_sensitivity_01/LEDGER.md`. Design of
record: `campaigns/noro/provisioned_sensitivity_01/DESIGN.md`
(factors, E = ABCD generator, `PROFILE_TABLE.md`, `SEED_MANIFEST.json`).

## 1. Design and sizing (settled inputs, not re-derived here)

| factor | parameter | (-) | (+) |
|---|---|---|---|
| A | `provisioned_source.q_source` | 0.00086 | 0.0047 |
| B | boarding passenger prevalence | 0.025 | 0.040 |
| C | boarding crew prevalence | 0.007 | 0.030 |
| D | `norwalk_gi.illness_duration.draw` | `point` | `empirical_survival` |
| E | `norwalk_gi.route_efficiency_multipliers` joint scale | ×0.5 | ×2.0 |

Half-fraction E = ABCD (I = ABCDE), rows p01–p16 in standard order.
Per-hull replication (PI decision 2026-11-07, cls raised 64 → 96 to
match exp; the scout's first 8 seeds per cell are nested inside n):

| hull | platform | n / cell | scout runs | remainder runs | nominal | reserve seeds |
|---|---|---|---|---|---|---|
| exp | expedition_cruise_450 | 96 | 384 | 4,224 | 4,608 | 8096–8097 |
| cls | classic_cruise_1900 | 96 | 384 | 4,224 | 4,608 | 8201–8202 |
| spr | spirit_cruise_3000 | 48 | 384 | 1,920 | 2,304 | 8153–8154 |
| meg | mega_cruise_5000 | 24 | 384 | 768 | 1,152 | 8129–8130 |
| **total** | | | **1,536** | **11,136** | **12,672** | 384 (untouched) |

Dry-run before submit: manifest `--tier all` 13,056 = 12,672 main + 384
reserve; `scripts/campaign list` 288 blocks / 11,520 cells (small hulls)
+ 96 blocks / 1,152 cells (mega). Sizing PR #1164; image pin PR #1165.

## 2. Execution (AWS Batch, `scripts/campaign submit`, one array per block)

| wave | blocks | children | image | jobdefs | window (UTC) | FAILED |
|---|---|---|---|---|---|---|
| scout (all hulls, 8 seeds/cell) | 192 | 1,536 | `noro-provisioned-sensitivity01` @ `sha256:354ddfda…` (main 71794db5) | small :1–:145, mega :1–:49 | 11-07 00:20 → 05:11 | 0 |
| remainder 1: meg → exp → spr | 144 | 6,912 | same scout image (tier specs byte-identical) | mega :50–:97, small :146–:241 | 11-07 14:27 → 11-08 ~01:55 | 0 |
| cls canary (seed 8113) | 1 | 1 | `…-r2` @ `sha256:efc18c7d…` (main 7f935df2) | small :242 | 11-08 ~02:00, 5.3 min | 0 |
| remainder 2: cls | 48 | 4,224 | `…-r2` @ `sha256:efc18c7d…` | small :243–:290 | 11-08 02:01 → ~13:00 | 0 |

- 384 arrays + 1 canary, 12,673 children, **0 FAILED**, reserve never consumed. S3
  verified per block: every one of the 192 nominal block prefixes holds
  exactly its scout 8 + remainder (88 / 88 / 40 / 16) zips.
- The cls remainder needed a second image because seeds 8171–8200 were
  not in the manifest baked into the scout image (`campaign_entrypoint`
  resolves seeds against the in-image manifest). The r2 image was built
  from merged main, verified in-container, smoked at seed 8171 (first
  unresolvable seed on the scout image; zip member list identical to the
  scout's), and digest-pinned in `campaign.json` before the canary.
- Wall clock: mega remainder is memory-bound (8 GiB children pack ~4
  per 2 GiB/vCPU host → ~50 concurrent at the 256-vCPU Spot cap, ~7 h
  for 768 children); exp/spr drained in ~2.5 h behind it; cls 4,224
  children in ~11 h.
- Cost basis (scout-measured child wall × count, mega as 4 slots by
  memory): remainder 2,234 slot-h, ≈562 GB of zips, $45–89 at
  $0.02–0.04 per vCPU-h Spot (pricing API is denied to the deploy role);
  +6 % over the pre-cls-bump projection, not material.

## 3. Expected vs recovered cohort

| attempt | sources | expected runs | first_paper_vectors | coverage cells | data_gaps | scan-join conflicts | disqualifiers |
|---|---|---|---|---|---|---|---|
| `red-fps01-sens01-scout3` | 1,728 (192 scan-row files + 1,536 zips) | 1,536 | **1,536** | 192 | 0 | 0 | [] |
| `red-fps01-sens01-main` | 11,328 (192 + 11,136) | 11,136 | **11,136** | 192 | 0 | 0 | [] |
| **total** | 13,056 | **12,672** | **12,672** | 192 | **0** | 0 | |

Scan rows (`tools/noro_diag/food_shapes_01_scan.py --no-census`): 11,136
unique keys, every row `num_epochs` 288, per hull exp 4,224 / cls 4,224 /
spr 1,920 / meg 768. Cohort check on the main request: 11,136 expected /
11,136 unique / 0 duplicates. Every nominal run has exactly one 1.5.0
vector; nothing is published as missing.

## 4. Ceiling-vs-actual metering (main attempt, RECEIPT `budget_spent`)

| dimension | ceiling | spent | scout3 ×7.25 projection |
|---|---|---|---|
| api calls total | 120,000 | 57,356 | ~70k |
| get requests | 100,000 | 56,065 | ~58k |
| head requests | 30,000 | 11,328 | ~12.5k |
| compressed bytes read | 2 GB | 995.5 MB | ~1.0 GB |
| uncompressed bytes | 16 GB | 4.417 GB | ~4.4 GB |
| source objects | 12,000 | 11,328 | 11,328 |
| output bytes | 6 GB | 2.316 GB | ~2.4 GB |
| checkpoint reserve | 300 MB | 135.9 MB | — |
| wall | 14,400 s | ~3,735 s (14:34:13 → 15:36:29) | ~4,200 s |

Batch job `b4410d76-0a3c-48ca-9fa9-89a9ca32ff50` on `picard-reducer:13`
(`reducer-v10` @ `sha256:006954a6…`), exit 0. Reads are summary.json-only
member reads: ~1 GB compressed out of ~560 GB of archives. Scout3
(`494785f3-…`): 584 s wall, 141 MB compressed / 612 MB uncompressed,
326.6 MB output. The ×7.25 linear projection from the scout held within
~5 % on every dimension — the scout-then-remainder pattern sized this
leg correctly.

## 5. Page layer

- `red-fps01-sens01-main/pages/first_paper_vectors/`: **1,114 pages,
  11,136 rows, 1,126,917,839 bytes** (≤1 MiB/page, row-aligned,
  shard-partition order). Pages manifest at
  `attempts/red-fps01-sens01-main/pages/first_paper_vectors.pages_manifest.json`
  (321,035 B); `status.json` (557 B) and `asset_index.json` (353,735 B,
  1,116 assets) at the attempt root — all three HEAD-checked before the
  return leg (reducer-dispatch-pins §5). 177 checkpoints, 1,236 shard
  objects, 1,233 catalog partitions, snapshot `snap-62ac4c76743c485e`.
- `red-fps01-sens01-scout3/pages/first_paper_vectors/`: 154 pages,
  1,536 rows, 158.65 MB; 27 checkpoints, 186 shard objects.

## 6. Edison delivery receipts

- **Scout3** (return run 42373863829, `attempt_id=red-fps01-sens01-scout3`,
  bootstrap
  `requests/red-fps01-sens01-scout3-bootstrap.json` raw sha `0b6f3a15…`,
  `edison_ingest=true`): poll, collect, ingest, acknowledge all
  `completed`. 154 pages + RECEIPT + MANIFEST + COMMIT collected
  (158.65 MB); Edison **157 project asset ids** (`files_uploaded: 157`),
  listed in `campaigns/noro/provisioned_sensitivity_01/EDISON_SCOUT3_ASSETS.json`.
  Ack `ack-9523d1856c0a43cb` at
  `campaign/_derived/reducer/v1/requests/acks/ack-9523d1856c0a43cb.json`
  (accepted_page_ids 157, deduplicated false).
- **Main** (return run 42495909835, `attempt_id=red-fps01-sens01-main`,
  bootstrap `requests/red-fps01-sens01-main-bootstrap.json` raw sha
  `bb4be7bf40a69bee31a91a3bb339c16e236b38ceb9778920b320fdcc55affca3`,
  request_id `req-fps01-sens01-main-return`, `collect_all_pages: true`,
  `max_return_bytes` 4 GiB, admission `adm-fps01-sens01-main-return`
  $60, scope sha `3f73b584…`, `edison_ingest=true`): **in flight —
  asset ids and ack recorded here when the acknowledge job completes.**

## 7. Observations and incidents (for Edison's reading of the vectors)

- **Non-ignited exp runs (observation, not a defect):** the scan flags
  957 / 4,224 exp remainder runs `ignited=false` (scout exp: 0 / 384 at
  the first 8 seeds). 30 of them (seed 8011, one per block in 30 of the
  48 exp blocks — the lower-boarding arms) are 0.16 MB zips: complete
  288-epoch voyages with `infected=0`, i.e. no imported case at boarding
  and no provisioned-source hit. All are published as-is with their
  1.5.0 vector; nothing was reseeded (non-goal). Expect zero-count cells
  on the 450-agent hull at the low boarding levels — Edison's
  sparse-event handling applies.
- **No effect analysis here.** The 12,672 rows are raw per-run vectors
  keyed by profile/hull/arm/seed; aliasing structure is in
  `PROFILE_TABLE.md`.
- **cls image rebuild** (§2): recorded with its interim mis-push (a
  root-Dockerfile-only image briefly carried the r2 tag, never
  registered in a jobdef, overwritten; untagged layers remain until the
  ECR lifecycle policy expires them — the deploy role lacks
  `ecr:BatchDeleteImage`).
- **Return-leg dry run cancelled, not spent:** `campaign_return.yml`
  gates every job on the `aws-campaign` environment even with
  `dry_run=true`, so a dry run costs the approver a click for no AWS
  call; inputs were verified locally instead (raw sha of the S3
  bootstrap object, attempt_id = reduction id).
- **Dispatch gates:** materialize (run 42486056392) and return legs run
  on `aws-campaign` with the repo owner as required reviewer; both
  waited on approval by design. CloudWatch `logs:GetLogEvents` is denied
  to the deploy role; job health was read from Batch state and the S3
  attempt prefix (checkpoints advanced ~3/min throughout).
