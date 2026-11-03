# first_paper_scalar — venue-placement counterfactual report: red-fps02-venue (32 vectors)

**Status: measured live result (2026-11-03), attempt `red-fps02-venue`,
Batch job `777cc082-2b6d-438f-b41f-015cf1b35337` on `picard-reducer:11`
(image `reducer-v8`, `sha256:9e6d48bc…`, engine `13fa0f2f` = merged
`#1147` `station_zone_pin` seam, contract `first_paper_scalar/1.4.0`).**

Deliverable: `first_paper_vectors` for the 32 provisioned-venue cells
(4 hulls × `crew_venue`/`passenger_venue` × 4 seeds) under
`campaign/_derived/reducer/v1/attempts/red-fps02-venue/`
(RECEIPT/COMMIT/MANIFEST/status + bounded page layer), collected
through the bounded return path and delivered to Edison, on the
`first_paper_scalar/1.4.0` definition (three additive venue fields;
all 1.3.0 columns unchanged). Edison PHASE2_PILOT_SPEC: does
relocating provisioned food-source lots from crew-mess venues to the
largest passenger dining venue reverse the crew-heavy
threshold-crossing pattern?

## 1. Expected vs recovered cohort

| measure | declared | recovered |
|---|---|---|
| cells (arm-sets) | 8 | 8 `coverage_cells` |
| runs per cell | 4 | 4 (all 8 cells) |
| runs total | 32 | 32 `first_paper_vectors` rows |
| source objects | 40 (32 zips + 8 scan files) | 40 |
| catalog partitions | — | 33 |
| data gaps | 0 allowed unaccounted | 0 |
| duplicate run keys | — | 0 (cohort check, 32 unique keys) |
| capabilities | — | 160 |

Cohort composition — `phase_venue/red-fps02-venue-cohort.json`:
`fl_{exp,cls,spr}_12d_scr_q30_{crewv,paxv}` (6 arms under
`campaign/noro_provisioned_venue_01/`) + `fl_meg_12d_scr_q30_{crewv,paxv}`
(2 arms under `…_mega/`). Pair per (hull, seed): `crewv` pins every
provisioned lot to the hull's crew-mess venue set (baseline mirror of
the q30 allocation grammar); `paxv` pins to the largest documented
passenger dining venue — same draws, same counts, only the zone
re-maps (`Spec §2.7`).

## 2. Definition 1.4.0 venue fields

`first_paper_scalar/1.4.0` adds `source_venue_arm`,
`actual_venues_used` (JSON list), `n_lots_placed` — all native paths
under `mechanisms.provisioned_source.norwalk_gi`, all 32 rows
`exact_emitted` (0 `missing`). Pre-1.4.0 summaries emit `None` +
`status:"missing"` — explicit missingness, never fabricated.

## 3. Counterfactual result (measured; Edison owns acceptance)

Scan rows under
`campaign/noro_provisioned_venue_01/_scan_rows/fl_*_{crewv,paxv}.jsonl`
(4 rows each; `posted` = trigger crossing, `rep_*_ar`/`rep_*_n` =
report attack rate and counts by role). Full table in
`campaigns/noro/provisioned_venue_01/LEDGER.md` (wave-1 readout).

| measure | crew_venue | passenger_venue |
|---|---|---|
| posted | 14/16 | 10/16 |
| role split | crew-heavy on 15/16 seeds | passenger-heavy on 16/16 |
| meg trigger | 3/4 posted | 0/4 posted |

- The crew-heavy pattern reverses under passenger-venue placement on
  every seed where the lots drive exposure (15/16; exp/8557 is a
  placement-invariant non-poster — identical 0.019/0.0075 pax-heavy
  split in both arms, inferred: no lot-driven exposure on that seed).
- Trigger answer is hull-dependent: meg drops 4/4 below the trigger
  under `paxv` while still inverting the split; exp/cls keep crossing
  with the inverted split; spr splits (8620 crosses only under crewv).
- Non-posters: exp/8557 (both arms), meg/8199 (both arms),
  spr/8620 (paxv only), meg/8461+8548+8577 (paxv only).

## 4. Ceiling-vs-actual metering

All counters measured from `RECEIPT.json` `budget_spent` — nothing
inferred from billing.

### 4.1 Request counters vs ceilings

| counter | spent | ceiling | headroom |
|---|---|---|---|
| GET requests | 177 | 40,000 | ~99.6% unused |
| HEAD requests | 40 | 10,000 | ~99.6% |
| total API calls | 186 | 50,000 | ~99.6% |
| compressed bytes read | 3,017,973 (3.0 MB) | 1 GB | ~99.7% |
| uncompressed member bytes | 12,768,009 (12.8 MB) | 4 GB | ~99.7% |
| output bytes | 3,027,090 (3.0 MB) | 500 MB | ~99.4% |
| source objects | 40 | 500 | 92% |
| checkpoint reserve bytes | 595,508 | 100 MB | ~99.4% |
| jobs | 1 | 1 | 0 |
| retries | 0 | 50 | — |
| max_cost_usd (declared) | — | $10 aggregate | see §4.2 |

### 4.2 Allocated vs runtime compute

| measure | value | basis |
|---|---|---|
| jobdef allocation | 2 vCPU / 8,192 MiB | `picard-reducer:11` |
| Batch runtime | ~90 s, 1 attempt, 0 retries | materialize job `777cc082` |
| dollar cost | **unknown** — no billing counter emitted | aggregate ceiling $10 (incl. return leg), not a zero |

### 4.3 Incidents during execution

- **Return-leg request shape:** first return dispatch
  (run 41564206408) exited 4 on `collect` — the workflow's
  `request_uri` expects a `crusher-campaign-distributions/1.0-proposed`
  bootstrap collect request, not the `crusher-reducer-spec/v1`
  materialize request (8 `required_field_missing` on the admission
  envelope). Re-dispatched with
  `requests/red-fps02-venue-return-request.json` (operation `collect`,
  allowlist = the attempt prefix, scope register `3f73b584…`) — all
  four legs then ran green. Recorded as reducer-dispatch-pins §4.
- **Reducer jobdef registration:** `iam:PassRole` on
  `picard-reducer-job-role` is outside the deploy role — rev 11 was
  registered under the operator profile from the committed
  `deploy/aws/reducer_jobdef_spec.json` render.

## 5. Page layer

- 2 `page-NNNNN.jsonl` (23 + 9 rows) + sha256/bytes/rows pages
  manifest; 32 rows total.
- Register: `phase_venue/red-fps02-venue-cohort.json`.

## 6. Edison delivery receipts

- **Collect (run 41565523407):** 5 verified artifacts —
  `RECEIPT.json`, `MANIFEST.json`, `COMMIT.json`,
  `page-00001.jsonl`, `page-00002.jsonl`; 1,439,257 B total,
  `status: completed`.
- **Ingest:** `ingest_status completed`, `files_uploaded` 5 →
  `project_asset_ids`:
  `17656d75-6c99-49b3-ae7d-059cb8106fd7`,
  `687ef97f-09b2-4cea-9da7-816232bdf6d4`,
  `1a766c0a-cb43-4326-b1a0-82336cccfea7`,
  `6edd5894-eecb-48cb-878d-88430503968b`,
  `0422c632-e3dd-4328-a8e3-839e133efb98`.
  `s3_pointer` → `attempts/red-fps02-venue/RECEIPT.json`.
- **Ack:** durable `ack-91cc6608cc903eea` at
  `campaign/_derived/reducer/v1/requests/acks/ack-91cc6608cc903eea.json`
  (sha256 `824ada6c0c126fbc4d6e23e5635945f082ad7b479fb045a44c5b9f48a01f0ed4`,
  `deduplicated: false`).

## ISSUE-COMMENT

```
ISSUE-COMMENT for the Edison program tracking thread:

Venue-placement counterfactual (PHASE2_PILOT_SPEC) executed end-to-end
at attempt red-fps02-venue on first_paper_scalar/1.4.0 — the three
venue fields (source_venue_arm, actual_venues_used, n_lots_placed)
emit exact on all 32 rows.

Cohort: 32/32 declared vectors recovered — 4 hulls × crew_venue/
passenger_venue × 4 seeds, 0 duplicates, 0 data gaps, 160
capabilities. crewv = all provisioned lots pinned to crew-mess
venues; paxv = all pinned to the largest passenger dining venue;
draws/counts preserved (Spec §2.7).

Measured: posted 14/16 crewv vs 10/16 paxv. The crew-heavy report
split inverts under passenger-venue placement on 15/16 seeds (exp
s8557 is placement-invariant — identical pax-heavy split both arms).
On the mega hull the counterfactual drops 4/4 seeds below the trigger
entirely while still inverting the split; exp/cls keep crossing;
spr/8620 crosses only under crewv.

Metering (measured): 186 API calls, 3.0 MB compressed read, 3.0 MB
output — ~99.5% headroom on the declared ceilings. Wall ~90 s,
1 job, 0 retries. Page layer 2 pages / 32 rows; RECEIPT/COMMIT/
MANIFEST under attempts/red-fps02-venue/.

Edison: collect verified 5 artifacts (1.44 MB) → ingest completed —
5 files → 5 project_asset_ids, durable ack ack-91cc6608cc903eea.
```
