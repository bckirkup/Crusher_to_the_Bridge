# first_paper_scalar — Phase B report: red-fps01-b2 (8,000 vectors)

**Status: measured live result (2026-10-31), attempt `red-fps01-b2`,
Batch job `ce371bf1-8b37-43fb-b195-cacf00c828ce` on
`picard-reducer:6` (image `reducer-v4`, `sha256:cc77ee28…`, merged
main `40e0f622` + #1123 `collect_all_pages`/`vector_checks`).**

Deliverable: `first_paper_vectors` for 8,000 declared executions under
`campaign/_derived/reducer/v1/attempts/red-fps01-b2/`
(RECEIPT/COMMIT/MANIFEST/status + bounded page layer), collected
through the bounded return path and delivered to Edison, plus the
verification layer (hash-manifest, precomputed checks, helper tools).

Acceptance was bound by `DEVIN_PR1119_FOLLOWUP.md` items 1–6; §5 maps
each item to its disposition.

## 1. Expected vs recovered cohort

| measure | declared | recovered |
|---|---|---|
| cells (hull × arm) | 8 | 8 |
| runs per cell | 1,000 | 1,000 (all 8 cells) |
| runs total | 8,000 | 8,000 `first_paper_vectors` rows |
| source objects | 8,008 (8,000 zips + 8 scan files) | 8,008 |
| catalog partitions | — | 882 |
| data gaps | 0 allowed unaccounted | 0 |
| scan_join_conflicts | — | 0 |
| scan_key_conflicts | — | 0 |
| duplicate run_uids | — | 0 |

Missingness (null-valued `values` columns, measured from the 304
published pages — `missing[]` is empty on every row, so nulls here are
null-emitted fields, not unrecovered data):

| column | null count (of 8,000) | reading |
|---|---|---|
| `detection_epoch` | 794–940 per cell | detection surveillance did not fire in most runs |
| `detection_lag` | 794–940 per cell | same event family |
| `confirmation_epoch` | 986–1000 per cell | confirmation almost never fired within 288 epochs |
| `vsp_trigger_epoch` | 988–1000 per cell | VSP trigger almost never fired |
| `infections_by_route_sum_by_role` | 8,000 | check aux column — see §3 |
| `r_effective_at_peak` | 68 off / 69 ps_ship, exp cells only | `null_emitted` in provenance: no secondary peak in those runs |
| `scan_burst48_centre` | 16, exp cells only | scan-row field absent for 16 exp runs |

These nulls are cohort characterization, not extraction gaps — each
carries a per-field provenance record (`null_emitted` /
`operand_status`) in the vector row.

## 2. Paired-seed reconciliation

Pair rule: within `hull_id`, join arms on `seed` only (full-key scan
joins upstream; `(hull,seed)` fallback removed in #1121).

| hull | seeds | full pairs (off + ps_ship) | orphans |
|---|---|---|---|
| expedition_cruise_450 | 1,000 | 1,000 | 0 |
| classic_cruise_1900 | 1,000 | 1,000 | 0 |
| spirit_cruise_3000 | 1,000 | 1,000 | 0 |
| mega_cruise_5000 | 1,000 | 1,000 | 0 |
| **total** | | **4,000** | **0** |

Status columns (evidence-derived, not archive-readable inference):
`completion_status` `completed` 8,000/8,000; `clock_status` `complete`
8,000/8,000 (emitted epochs = declared `num_epochs` = 288);
`follow_up_status` `posted` 36 / `unposted` 7,964 (`posted` follows the
scan-row flag — kept distinct from trigger/status fields).

## 3. Sum-check consistency (role-nested and flat)

| check | result |
|---|---|
| `reported_by_channel_consistent` | `true` 8,000/8,000 |
| `reported_by_route_consistent` | `true` 8,000/8,000 |
| `infections_by_route_consistent` | **`false` 8,000/8,000** — measured, see below |

`infections_by_dominant_route_json` sums to a strict subset of
`cumulative_ever_infected` in every row (dominant-route tags cover
routed infections only), so the consistency flag is systematically
`false` — `sum_divergent` in provenance. That is a property of the
summary field, not an extraction defect; reported as measured.

Known profile gap (minor): the `*_by_role` aux column is written but
never gets a provenance record (provenance covers `sum_column` and
`column` only). Flagged for a later contract bump — the aux is null
anywhere the dict is flat.

## 4. Ceiling-vs-actual metering (item 5)

All counters are measured from `RECEIPT.json` `budget_spent` /
`budget_remaining` — nothing is inferred from billing (see §4.2 for
what remains unknown).

### 4.1 Request counters vs ceilings

| counter | spent | ceiling | headroom |
|---|---|---|---|
| GET requests | 40,017 | 100,000 | 60% unused |
| HEAD requests | 8,008 | 30,000 | 73% |
| total API calls | 40,450 | 120,000 | 66% |
| compressed bytes read | 737,965,815 (738 MB) | 2 GB | 63% |
| uncompressed member bytes | 3,160,384,326 (3.16 GB) | 16 GB | 80% |
| output bytes | 663,447,728 (663 MB) | 1 GB | 34% |
| source objects | 8,008 | 12,000 | 33% |
| checkpoint reserve bytes | 118,375,907 (118 MB) | 200 MB | 41% |
| jobs | 1 | 1 | 0 |
| retries | 0 | — | — |
| max_cost_usd (declared) | — | $100 | see §4.2 |

### 4.2 Allocated vs runtime compute

| measure | value | basis |
|---|---|---|
| jobdef allocation | 2 vCPU / 8,192 MiB | `picard-reducer:6` |
| Batch runtime | 2,652.6 s (44.2 min), 1 attempt, 0 retries | `describe-jobs` 17:08:27→17:52:40Z |
| queue wait | 204 s | created→started |
| vCPU-seconds (allocated = runtime here) | 5,305 vs 28,800 ceiling | single-job allocation |
| memory-seconds | ~21.7M MiB·s allocated | runtime RSS unknown — not metered, labelled unknown |
| dollar cost | **unknown** — no billing counter is emitted | ceiling $100, not a zero |

### 4.3 Quote repair (item 5)

- **GET model:** 40,017 GET / 8,008 objects = **4.997 GET + 1.0 HEAD
  per zip** — matches the repaired ~4 GET + 1 HEAD estimate (the
  original 53-GET panel measured a ranged probe, not this path).
- **Decode volume:** measured 3.16 GB uncompressed for 8k runs
  (~395 kB/summary) vs the repaired estimate 3.27–3.42 GB
  (409–428 kB/summary) — the panel band ran ~3–6% high.
- **Compute:** predicted 15–20 vCPU-min; actual 88.4 vCPU-min —
  4.4–5.9× over the Phase A quote. Driver: the worker decodes and
  validates the full 3.16 GB summary corpus (per-field provenance +
  sum checks), not just index tails. Callers quoting future phases
  should scale from 88 vCPU-min / 8k runs, not the panel figure.

## 5. Correction-spec dispositions

| item | disposition |
|---|---|
| 1 join safety | full-key only (#1121); 0 join/key conflicts measured |
| 2 completion status | evidence columns emitted; §2–§3 counts |
| 3 seams | 304 unique ≤1MiB pages + pages manifest + asset index; collector consumed page manifest, not partitions |
| 4 resume | b2 is a fresh approved attempt; stopped/partial attempts are terminal by contract |
| 5 quote repair | §4 — measured model confirmed; unknown counters labelled unknown |
| 6 sequence | canary gate passed before tranche: run 41226283169 collected `page-00001.jsonl` (sha `08fbae0d…` == manifest entry) → Edison ingest → durable ack `ack-4efb0d1b954b0f95` |

## 6. Verification layer (delivered with the vectors)

- **Pages + manifest:** 304 `page-NNNNN.jsonl` + sha256/bytes/rows
  manifest; verified 304/304 locally, 0 mismatches.
- **Precomputed checks:** `phase_b/red-fps01-b2-checks.json` — per-cell
  quartiles on 10 fields + per-hull paired contrasts (off−vs−ps_ship
  delta mean 0.0000–0.0003 ill-pax; ps_ship ≈ off at this dose).
- **Helper tools:** `vector_checks.py` — `verify_page`,
  `recompute_aggregate`, `paired_contrast`; each reads only the
  published pages (single-pass, bounded), never the source corpus.
  Exercised receipts: page verify 304/304; `mean
  attack_rate_ill_pax_recomputed` = 0.014478 (n=8,000);
  `paired_contrast(classic_cruise_1900, 8105)` delta = 0.0 (early-exit
  after 38 pages / 1,009 rows).
- **Register:** `phase_b/red-fps01-b2-cohort.json`.
- Edison never decodes the 3.4 GB corpus: checks doc + page hashes +
  point-recompute helpers are its surface.

## 7. Delivery receipts

- **Canary (run 41226283169):** 4 files → 4 Edison
  `project_asset_ids` (`ed5e32c4…`, `ed56a620…`, `b689619f…`,
  `1f3028e1…`); durable ack `ack-4efb0d1b954b0f95` on S3.
- **Tranche (run 41236389179; first dispatch 41230241834):**
  307 collected files → 307 Edison `project_asset_ids`
  (`85f966f8-b4e0-46fc-b106-43233076e30c` …
  `77e3f3ca-a049-4268-8998-c8918c1865b0`); durable ack
  `ack-2055c785cc113516` on S3 (sha256 `90e81438…`, 96 KiB,
  verbatim id lists) with a 916-byte bounded issue envelope —
  `accepted_page_ids` count 307 (sha `8759cbbe…`),
  `project_asset_ids` count 307 (sha `9a5e7c9a…`). The first
  dispatch completed poll → collect → ingest but the
  acknowledge leg exited on the typed `budget_exceeded`
  32 KiB issue-envelope bound; PR #1124 (merged) bound the
  envelope id lists to digests and the redispatch finished
  green end-to-end.

## ISSUE-COMMENT

```
ISSUE-COMMENT for the Phase B tracking thread (post on the Edison
follow-up thread / DEVIN_PR1119_FOLLOWUP tracking issue):

Phase B executed end-to-end at attempt red-fps01-b2 (supersedes
red-fps01-b; earlier attempt left in place, unaccepted, per resume
semantics).

Cohort: 8,000/8,000 declared vectors recovered — 8 cells × 1,000, 4,000
within-hull seed pairs, 0 orphans, 0 duplicates, 0 data gaps, 0 join or
key conflicts. completion_status completed 8,000; clock_status complete
8,000; follow_up posted 36 / unposted 7,964. Sum checks:
reported_by_channel/route consistent 8,000; infections_by_route
consistently divergent 8,000 (dominant-route dict is a strict subset —
measured property of the summary field).

Metering (measured, no inference): 40,017 GET + 8,008 HEAD (≈5+1 per
zip, matches the repaired adapter model), 738 MB compressed / 3.16 GB
uncompressed read, 663 MB output, 118 MB checkpoint reserve. Compute:
88.4 vCPU-min (2 vCPU × 44.2 min, 1 attempt) vs the 15–20 vCPU-min
panel quote — callers should scale from the measured figure. Dollar
cost not metered: reported unknown under the $100 ceiling, not zero.

Sequence: item-6 canary gate passed (run 41226283169 — page-00001
sha-pinned end-to-end into Edison + durable ack) before the tranche
collect. Tranche delivered end-to-end under run 41236389179: 307
Edison project_asset_ids (see §7), durable ack
ack-2055c785cc113516 with a bounded digest envelope — the first
tranche dispatch had surfaced the 32 KiB issue-envelope bound at
acknowledge, fixed by binding the envelope id lists to digests
(PR #1124).

Verification layer shipped: 304 sha256-manifested ≤1MiB pages,
precomputed per-cell/per-hull checks doc, and validated single-point
helper tools (verify_page / recompute_aggregate / paired_contrast) that
read only the published pages — Edison confirms, never bulk-decodes.

Register + report committed under docs/campaign_reduction/
(phase_b/red-fps01-b2-*.json + FIRST_PAPER_PHASE_B_REPORT.md).
```
