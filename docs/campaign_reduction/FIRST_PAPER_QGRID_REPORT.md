# first_paper_scalar — q-grid report: red-fps01-qgrid (38,000 vectors)

**Status: measured live result (2026-11-01), attempt `red-fps01-qgrid`,
Batch job `971eb514-15b0-4bad-b007-301b3170e48c` on
`picard-reducer:10` (image `reducer-v7`, `sha256:bd6fd44d…`, merged
main `#1137` profile 1.3.0 + `#1139` sources-manifest cap).**

Deliverable: `first_paper_vectors` for 38,000 declared executions under
`campaign/_derived/reducer/v1/attempts/red-fps01-qgrid/`
(RECEIPT/COMMIT/MANIFEST/status + bounded page layer), collected
through the bounded return path and delivered to Edison, on the
`first_paper_scalar/1.3.0` definition (observed-window witness fields
added; 1.1.0/1.2.0 rows untouched).

## 1. Expected vs recovered cohort

| measure | declared | recovered |
|---|---|---|
| cells (arm-sets) | 38 | 38 `coverage_cells` |
| runs per cell | 1,000 | 1,000 (all 38 cells) |
| runs total | 38,000 | 38,000 `first_paper_vectors` rows |
| source objects | 38,038 (38,000 zips + 38 scan files) | 38,038 |
| catalog partitions | — | 4,165 |
| data gaps | 0 allowed unaccounted | 0 |
| duplicate run_uids | — | 0 (cohort check, 38,000 unique keys) |
| capabilities | — | 152,152 |

Cohort composition (measured from the 38 scan-row files before
submission — `docs/campaign_reduction/phase_qgrid/red-fps01-qgrid-cohort.json`):
`fl_{exp,cls,spr}_12d_scr_{q01…mint}` (30 arms) +
`fl_meg_12d_scr_{q01…ind}` (8 arms); off/ps_ship (8,000 vectors)
excluded — already accepted under `red-fps01-b2`. Scientific groups
stay separable via `tier_id`/`platform_id` on each row.

## 2. Definition 1.3.0 witness fields

`first_paper_scalar/1.3.0` adds four compact observed-window witness
fields derived from `summary.timeseries` via the same derive path as
`first_paper_observation_clock`'s observation_fields (no obsclock
re-emission): `observed_first_epoch`, `observed_terminal_epoch`,
`retained_epoch_rows`, `epoch_index_contiguous`, plus `observed` /
`timeseries_absent` status vocabulary. New rows cite the 1.3.0
definition hash; the accepted b2 rows keep their 1.1.0 identity.

## 3. Ceiling-vs-actual metering

All counters measured from `RECEIPT.json` `budget_spent` —
nothing inferred from billing.

### 3.1 Request counters vs ceilings

| counter | spent | ceiling | headroom |
|---|---|---|---|
| GET requests | 190,077 | 500,000 | 62% unused |
| HEAD requests | 38,038 | 120,000 | 68% |
| total API calls | 192,208 | 600,000 | 68% |
| compressed bytes read | 3,509,519,622 (3.51 GB) | 8 GB | 56% |
| uncompressed member bytes | 15,020,208,661 (15.0 GB) | 40 GB | 62% |
| output bytes | 3,345,807,723 (3.35 GB) | 6.5 GB | 48% |
| source objects | 38,038 | 50,000 | 24% |
| checkpoint reserve bytes | 609,758,664 (610 MB) | 1 GB | 41% |
| jobs | 1 | 1 | 0 |
| retries | 0 | 500 | — |
| max_cost_usd (declared) | — | $100 aggregate | see §3.2 |

### 3.2 Allocated vs runtime compute

| measure | value | basis |
|---|---|---|
| jobdef allocation | 2 vCPU / 8,192 MiB | `picard-reducer:10` |
| Batch runtime | 12,373 s (3.44 h), 1 attempt, 0 retries | `describe-jobs` 19:21:25→22:47:39Z |
| vCPU-seconds | 24,746 vs 60,000 ceiling | single-job allocation |
| dollar cost | **unknown** — no billing counter emitted | aggregate ceiling $100 (incl. return leg), not a zero |

### 3.3 Incidents during execution

- **Sources-manifest cap (run 1):** first dispatch (job `98b77ea7`)
  failed in 2 s with a typed `access_denied`: the 38-arm sources
  manifest (24.75 MB) exceeded the worker's Phase-B-scaled 16 MB
  whole-body cap. The job never touched sources — nothing burned.
  Fix shipped via #1139 (`_SOURCES_MANIFEST_MAX_BYTES` 16→64 MB) +
  `reducer-v7` image + jobdef rev 10; the re-dispatched job ran
  clean end-to-end.
- **Return readback cap:** the collect leg of return run
  41359274643 exited typed `budget_exceeded` — the attempt
  `COMMIT.json` (1,908,006 B) exceeded the canonical
  `request_manifest_bytes` readback cap (1,048,576 B, also
  Phase-B-scaled). Raised to 4,194,304 B in the canonical
  interface and the same bootstrap was re-dispatched — the
  manifest hash is unchanged (fetch cap is a resource bound,
  not contract semantics).

## 4. Page layer

- 1,533 `page-NNNNN.jsonl` + sha256/bytes/rows pages manifest;
  38,000 rows total, ~1.57 GB layer.
- Register: `phase_qgrid/red-fps01-qgrid-cohort.json`.

## 5. Edison delivery receipts

- **Return-path verification (before bulk collect):** canary leg
  (run 41341515588) re-collected a single accepted page from
  `red-fps01-b2` and ran the Edison ingest leg — `ingest_status
  completed`, durable ack `ack-67d7610d43640817` on S3. The
  `EDISON_PLATFORM_API_KEY` was verified live; no
  `RETURN_PATH_BLOCKED`.
- **Tranche (run 41370150667; first dispatch 41359274643 /
  41364852372):** 1,536 collected files → 1,536 Edison
  `project_asset_ids` (`6a0baa3b-4d50-4f6f-a0a3-cd4c50f56329` …
  `baa33f0b-d249-46cf-b48c-a6bb778e59dd`), `ingest_status
  completed` per `ingestion_receipt.json`. Durable ack on S3:
  `ack-468e7bc6569211c0` (491,542 B: 1,536
  accepted_page_ids + 1,536 project_asset_ids,
  `ingest_status completed`).
- The first two dispatches stopped on Phase-B-scaled bounds
  (§3.3): collect typed `budget_exceeded` on `COMMIT.json` under
  the 1 MiB `request_manifest_bytes` cap (#1144 → 4 MiB), then
  ingest auto-cancelled at the job's 15-minute `timeout-minutes`
  mid-upload (#1145 → 120 min). The third dispatch ran all four
  legs green. The cancelled ingest may have left a partial upload
  on Edison's side; the module has no dedup, so the completed leg
  re-uploaded the full declared set — Edison dedup policy is
  server-side.

## ISSUE-COMMENT

```
ISSUE-COMMENT for the Edison program tracking thread:

Q-grid executed end-to-end at attempt red-fps01-qgrid on
first_paper_scalar/1.3.0 (observed-window witness fields emitted on
the same summary.json-only pass; accepted b2 rows keep 1.1.0).

Cohort: 38,000/38,000 declared vectors recovered — 38 arm-sets ×
1,000, 0 duplicates, 0 data gaps, 152,152 capabilities. fl_{exp,cls,
spr} and fl_meg groups remain separable via tier_id/platform_id.

Metering (measured): 190,077 GET + 38,038 HEAD + 192,208 total API
calls; 3.51 GB compressed read, 15.0 GB member bytes, 3.35 GB
output — all inside the resized ceilings (62-68% headroom on calls,
48-62% on bytes). Wall 12,373s, 1 job, 0 retries. Page layer 1,533
pages / 38,000 rows; RECEIPT/COMMIT/MANIFEST under
attempts/red-fps01-qgrid/.

Edison: return path verified live on a canary leg
(ack-67d7610d43640817) before the bulk collect; tranche ingest
completed — 1,536 files → 1,536 project_asset_ids, durable
ack ack-468e7bc6569211c0.

Three Phase-B-scaled bounds surfaced and were fixed along the way
(sources-manifest 16→64MB #1139, request_manifest_bytes 1→4MiB
#1144, ingest timeout 15→120min #1145) — worth noting for future
38k+ cohorts: the collector's per-kind readback caps and job
timeouts are sized to the 8k Phase-B profile.
```
