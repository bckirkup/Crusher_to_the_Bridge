# first_paper_scalar — venue-placement sweep report: red-fps02-venue02 (12,000 vectors)

**Status: _(pending Edison ack — materialize complete, return leg
`red-fps02-venue02-b2-return` dispatched; §6 fills on ack. Attempts
`red-fps02-venue02` budget_stopped and `red-fps02-venue02-b`
publish-tail crash + repair — see §7)_**

Deliverable: `first_paper_vectors` for the 12,000 provisioned-venue-02
cells (4 hulls × `crew_venue`/`passenger_venue`/`mixed_venue` × 1,000
seeds, q = 0.003) under
`campaign/_derived/reducer/v1/attempts/red-fps02-venue02-b/`
(RECEIPT/COMMIT/MANIFEST/status + bounded page layer), collected
through the bounded return path and delivered to Edison, on the
`first_paper_scalar/1.4.0` definition (three additive venue fields;
all 1.3.0 columns unchanged). Edison Phase-2 ask: stable conditional
distributions over the three venue-placement conditions for the paper.

## 0. Reuse verdict (decided before any submit — measurement, not inference)

Edison asked whether the existing 4,000 q30 runs could serve as the
`mixed_venue` arm. **Measured answer: no.** Across the full q30 cohort
(`_scan_rows/fl_*_12d_scr_q30.jsonl`, `census.lot_objects` zones; 575
provisioned lots over 529 lot-carrying voyages) the realized venue
allocation tracks 1/N_venues — uniform-by-construction (every served
dining venue contributes the same station count, each minting i.i.d.
Bernoulli(q)) — not capacity-proportional:

| hull | capacity shares (top venues) | measured shares | max Δ (pp) |
|---|---|---|---|
| exp | MainDining 58.8, CasualDining 29.4, CrewMess 11.8 | ~33/32/34 | 25.0 |
| cls | MD_L 28.0, MD_U 28.0, LidoBuffet 24.5, Specialty 5.6, CrewMess 14.0 | ~17–24 flat | 17.0 |
| spr | MD_L 24.2, MD_U 24.2, Lido 19.3, rest small | ~9–15 flat | 13.0 |
| meg | Windjammer 23.4, MD_L 20.4, MD_U 16.1, rest small | ~8–14 flat | 10.8 |

Total-variation distance vs capacity-proportional ≈ 0.22–0.35 per hull
— no declared tolerance rescues it. → Implemented a capacity-weighted
`station_zone_pin_weights` seam (merged #1149) and ran all 3
conditions × 4 hulls × 1k seeds = **12,000 runs**. The mixed pin
draws weighted placement on a spawned `SeedSequence` sub-stream —
n_lots and the `_cs_rng` stream stay seed-paired with the unpinned
baseline by construction (canary-verified 12/12).

## 1. Expected vs recovered cohort

_(rows measured; receipt fields from the repaired `completed` RECEIPT — see §7)_

| measure | declared | recovered |
|---|---|---|
| cells (arm-sets) | 12 | 12 arrays SUCCEEDED (0 failed cells) |
| runs per cell | 1,000 | 1,000 per arm (scan rows, 0 errors) |
| runs total | 12,000 | 12,000 unique run keys |
| source objects | 12,012 (12,000 zips + 12 scan files) | 12,012 |
| data gaps | 0 allowed unaccounted | 0 |
| duplicate run keys | — | 0 (cohort reconciliation) |

Cohort composition — `red-fps02-venue02-b-cohort.json` (identical under attempt A's id):
`fl_{exp,cls,spr}_12d_scr_q30_{crewv,paxv,mixv}` (9 arms under
`campaign/noro_provisioned_venue_02/`) + `fl_meg_12d_scr_q30_{crewv,paxv,mixv}`
(3 arms under `…_mega/`). All three arms reuse the q30 seed set —
pair per (hull, seed): `crewv` pins to the hull's crew-mess venue set,
`paxv` pins to the main passenger dining venue, `mixv` is the
capacity-weighted allocation across all dining venues (the realistic
default). Same draws, same counts, only the zone placement differs.

## 2. Definition 1.4.0 venue fields

`first_paper_scalar/1.4.0` adds `source_venue_arm`,
`actual_venues_used` (JSON list), `n_lots_placed` — all native paths
under `mechanisms.provisioned_source.norwalk_gi`. Pre-1.4.0 summaries
emit `None` + `status:"missing"` — explicit missingness, never
fabricated.

## 3. Delivery scope

Per the Edison ask this leg commits **raw per-arm distributions
only** — no acceptance analysis vs the empirical 194/182 postings
(Kosmos/Edison owns the paper-facing comparison), no COVID/flu arms,
no parameter changes outside venue placement, no census extraction,
no re-verification of Phase-1 strata.

Venue pins + mixed weights (merged `campaigns/noro/provisioned_venue_02/design/build.py`):

| hull | crew_venue | passenger_venue | mixed_venue (weights) |
|---|---|---|---|
| exp | CrewMess | MainDining | MainDining 300, CasualDining 150, CrewMess 60 |
| cls | CrewMess | MainDining_L | MD_L 400, MD_U 400, LidoBuffet 350, Specialty 80, CrewMess 200 |
| spr | CrewMessMain+ CrewMessOff | MainDining_L | MD_L 500, MD_U 500, Lido 400, Pizza 120, SpecA/B/C 80 each, CM_Main 250, CM_Off 60 |
| meg | Crew_Mess_Main+ CrewMess_Fwd | MainDining_L | WJ 1600, MD_L 1400, MD_U 1100, SpecA 450, SpecB 400, Pool 300, Comedy 300, Cafe 250, CrewMain 700, CrewFwd 350 |

## 4. Ceiling-vs-actual metering

Measured `budget_spent` on `attempts/red-fps02-venue02-b-pub/RECEIPT.json`
(attempt-B ledger — the blocked retry inherited attempt-1's charges):

| dimension | ceiling | spent |
|---|---|---|
| api calls total | 120,000 | 60,025 |
| get requests | 100,000 | 60,025 |
| head requests | 30,000 | 12,012 |
| compressed bytes read | 2 GB | 1.09 GB |
| uncompressed bytes | 16 GB | 4.73 GB |
| source objects | 13,000 | 12,012 |
| output bytes | 1 GB | 586 MB |
| checkpoint reserve | 300 MB | 145.9 MB |

Headroom everywhere after the attempt-B reserve bump — the attempt-A
failure was the reserve, not the workload (§7).

## 5. Page layer

`pages/first_paper_vectors/`: **504 pages, 12,000 rows,
521,963,762 bytes** (≤1 MiB/page, row-aligned, shard-partition order).
Pages manifest at
`attempts/red-fps02-venue02-b/pages/first_paper_vectors.pages_manifest.json`
(`first_paper_pages_manifest`, per-entry `page_id`/`uri`/`sha256`/`rows`/`bytes`);
`status.json` + `asset_index.json` at the attempt root. The first 398
pages were written by the materialize job; pages 399–504 and the three
publish objects were synthesized post-hoc by a byte-faithful re-chunk
of the shard partitions — verified identical to the job-written pages
for all 398 (§7 incident).

## 6. Edison delivery receipts

_(pending — collect artifact list, ingest `project_asset_ids`, ack hex
under `campaign/_derived/reducer/v1/requests/acks/`)_

## 7. Incidents during execution

- **Scan-row census leg descoped (decision, not a defect):** the
  census-member decode measured ~2 h/tier (~400–800 MB member per
  zip, ~18 h projected for 12 tiers) while the reducer's
  `observation_jsonl` adapter only indexes rows — venue fields are
  extracted from each run zip's summary.json by
  `first_paper_scalar/1.4.0`. Rows were produced with `--no-census`;
  `census` is null in the scan files, `cs_echo` retains the venue
  witness.
- **Mega-leg wall clock:** the three mega arrays ran ~24 h behind the
  small hulls — vCPU-bound at the 256-vCPU Spot CE cap (~50
  concurrent ~28-min cells, ~95 cells/hr), not a Spot drought.
- **Dispatch gate:** `campaign_reduction.yml` jobs run on the
  `aws-campaign` GitHub environment (required reviewer: repo owner);
  the materialize dispatch waited on approval, by design.
- **Dispatch input trap avoided:** `dry_run` is a required input
  defaulting to `true`; the first dispatch was cancelled and
  re-submitted with `dry_run=false` before it consumed a run.
- **Attempt B publish-tail crash + repair (2026-11-05):** attempt-1
  (Batch `3199014b-…`, ~82 min) wrote all 185 checkpoints, 1,295 shard
  objects, COMMIT.json (`completed`, snapshot `snap-f8f09d4e47939619`,
  12,000 vectors, 0 errors), MANIFEST.json and 398 of 504 vector
  pages, then died exit-1 inside `_emit_pages` before writing the
  pages manifest, `status.json` and `asset_index.json`. Retries 2–3
  re-finalized into a `DerivedConflict` (the committed COMMIT already
  carried `completed` with a different `utc`) and wrote a `blocked`
  RECEIPT via the create-only `put_if_absent` — permanent at that
  key. CloudWatch `logs:GetLogEvents` is denied to the deploy role,
  so the exit-1 cause is undiagnosed (not budgets: the ledger shows
  headroom in every dimension).
  **Repair (create-only store — no overwrites):** the 188
  `first_paper_vectors` shard partitions were re-chunked at the
  documented ≤1 MiB/page rule; the regenerated sequence matched all
  398 job-written pages byte-for-byte, so tail pages 399–504 were
  written as new keys, then `first_paper_vectors.pages_manifest.json`,
  `status.json` and `asset_index.json` at the canonical attempt keys,
  and a truthful `completed` RECEIPT at the sibling prefix
  `attempts/red-fps02-venue02-b-pub/RECEIPT.json` (the `blocked`
  receipt remains as an inert stray). The `-b` return request also
  lacked `collect_all_pages` — required above the collector's
  20-file cap — so a corrected request
  `requests/red-fps02-venue02-b2-return-request.json` carries
  `collect_all_pages: true` + scaled budgets; the return leg runs
  with `attempt_id=red-fps02-venue02-b-pub`.
- **Attempt A `budget_stopped` (2026-11-04 23:09 UTC):** shard 0
  processed 64 sources (52 vectors emitted) then stopped —
  `checkpoint_reserve_bytes: charge 142,472,112 exceeds remaining
  100,000,000`. The shard-0 checkpoint carries the cohort-wide
  accumulator delta (~142 MB at 12k sources; the b-obsclock
  precedent shows it scales with source count — 75 MB at 8k — and
  that every later shard checkpoint is ~18–25 KB). Attempt A's
  objects under `attempts/red-fps02-venue02/` are inert strays
  (create-only store). Attempt B re-dispatched as
  `red-fps02-venue02-b` with `checkpoint_reserve_bytes` 300 MB /
  `checkpoint_reserve_seconds` 3600 (the Phase-B2 values); sources
  manifest and cohort unchanged.
