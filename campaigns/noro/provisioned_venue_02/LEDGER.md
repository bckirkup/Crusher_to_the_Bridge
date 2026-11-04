# NORO-PROVISIONED-VENUE-02 — campaign ledger

**Status: declared — design frozen, no cells submitted.** Edison
Phase-2 calibration: stable conditional distributions for the
venue-placement counterfactual piloted in NORO-PROVISIONED-VENUE-01.
4 hulls × 3 arms (crew_venue / passenger_venue / mixed_venue) × the
full 1,000-seed q30 set per hull = 12,000 cells + 12 canary cells.
Mechanism seam: `provisioned_source.station_zone_pin_weights`
(capacity-weighted per-station placement on a parallel SeedSequence)
added alongside `station_zone_pin` + `source_venue_arm` in
`engines/transmission_core.py`; voyage witness gains
`station_zone_pin_weights`. Extraction contract:
`first_paper_scalar/1.4.0`. Mega spec:
`campaigns/noro/provisioned_venue_02_mega/` (same manifest, elevated
memory — VENUE-01 precedent).

**Reuse verdict (measured, decides the arm count):** the delivered
4,000 q30 runs distribute lots ~uniformly across served venues —
measured shares vs capacity shares deviate up to 25 pp (full table
in DESIGN.md §0) — so the q30 cohort is the *distributed* arm and
`mixed_venue` runs fresh on the weighted pin. All three conditions
run: 12k cells, not 8k.

**Grid:** 4 hulls × 3 arms × 1,000 seeds = 12,000 cells + 12 canary
cells (1 max-lot q30 seed × 3 arms per hull: exp 8169, cls 8169,
spr 8152, meg 8152). Seeds = the full delivered
NORO-PROVISIONED-SOURCE-01 q30 sets (exp 8000–8999; cls/spr/meg
8105–9104), seed-paired across arms and to baseline —
`SEED_MANIFEST.json` is the execution manifest Edison verifies.

**Fixed coordinates:** identical to the delivered
NORO-PROVISIONED-SOURCE-01 q30 baseline and the VENUE-01 pilot —
shipped bp 0.0325/0.0185, nsf 0.29, 288 epochs, syndromic_comp65,
dose 7.57, embarkation 2026-01-10, rung shipped. Only delta:
`station_zone_pin` (+ `station_zone_pin_weights` on mixed_venue) +
`source_venue_arm`.

**Submit gate:** seam merged 2026-11-03 as `526cf856` (#1149); image
`picard-campaign:noro-provisioned-venue02` built FROM that SHA, pushed
digest `sha256:12293ea9e4b9714cf4c2ee128805ec240678fa2960a5c998366daa18b806a3f2`,
ENGINE_GIT_SHA `526cf856`, verified to contain the seam + this design.
Manifest mirrored to
`s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_provisioned_venue_02/manifest.json`.
Canary 12 cells submitted + read out 2026-11-03 — **STOP until the
user gates the 12k array.**

## Waves

| wave | blocks | cells | status |
|---|---|---|---|
| canary | 4 hulls × 3 arms × 1 seed | 12 | 12/12 SUCCEEDED, gates pass 2026-11-03 |
| 1 | 4 hulls × 3 arms × 1,000 seeds | 12,000 | submitted 2026-11-03 (user gate passed) |

### wave-1 array — submitted 2026-11-03, user gate passed

Jobdef `picard-noro-provisioned-venue-02` revs 11–19 + `…-mega`
revs 4–6, image `picard-campaign:noro-provisioned-venue02` @
`526cf856` (digest `sha256:12293ea9`), Spot queue
`picard-campaign-queue`.

| block | jobdef | job id |
|---|---|---|
| fl_exp_12d_scr_q30_crewv | :11 | 6cd6dccd-3d75-4715-bb0b-365f651a1783 |
| fl_exp_12d_scr_q30_paxv | :12 | 9e6970cc-4d1a-4bb0-a800-5136a1388192 |
| fl_exp_12d_scr_q30_mixv | :13 | 273f24e6-ea88-4c90-9df1-5b8dddcf7cd9 |
| fl_cls_12d_scr_q30_crewv | :14 | 3e2bb318-404b-4c26-adfe-737b5f3a10f5 |
| fl_cls_12d_scr_q30_paxv | :15 | 5d5b9760-42cc-4ec5-81c1-e2100b7b391f |
| fl_cls_12d_scr_q30_mixv | :16 | 11a03212-2f3b-4a2d-8aae-dd7d5673959a |
| fl_spr_12d_scr_q30_crewv | :17 | e6e1e1a0-28dc-4e22-847b-73c793bb901f |
| fl_spr_12d_scr_q30_paxv | :18 | 09034887-4f9a-49cb-8145-72612699b68f |
| fl_spr_12d_scr_q30_mixv | :19 | 393a62f3-959c-4b9d-ba56-7cc489e8edf0 |
| fl_meg_12d_scr_q30_crewv | mega:4 | 855d2141-772a-4b4a-bb5f-727ee2707c47 |
| fl_meg_12d_scr_q30_paxv | mega:5 | 4297ab72-6a6d-4200-80cd-cfc0c2f32326 |
| fl_meg_12d_scr_q30_mixv | mega:6 | 144d9aa6-8210-4ba0-8f76-804b2a18941e |

### canary — submitted 2026-11-03

Image `picard-campaign:noro-provisioned-venue02` @ `526cf856`
(digest `sha256:12293ea9`). Jobdef `picard-noro-provisioned-venue-02`
revs 2–10 + `…-mega` revs 1–3 (fresh rev per submit, per convention).

| cell | jobdef | seed | job id |
|---|---|---|---|
| canary_exp_crewv | :2 | 8169 | e6b124fa-28c7-484f-b32a-beadc7b7cac8 |
| canary_exp_paxv | :3 | 8169 | 36f71a58-275c-4452-bbc8-207138f730b5 |
| canary_exp_mixv | :4 | 8169 | 5bcf73fd-4aa9-44c4-84c5-62bc21cb8322 |
| canary_cls_crewv | :5 | 8169 | 20c9eb5d-5fc0-4fa7-b79b-8f3d13ab32d1 |
| canary_cls_paxv | :6 | 8169 | a7c77a24-71df-4cec-97f6-3f9f32ce1d95 |
| canary_cls_mixv | :7 | 8169 | 575b4f8a-c794-4128-ba99-c364726f8807 |
| canary_spr_crewv | :8 | 8152 | 7a06e94f-155a-4523-ba17-f6f6cb22512c |
| canary_spr_paxv | :9 | 8152 | 6d6b0c68-51b7-483a-9b02-36430ca6c7cd |
| canary_spr_mixv | :10 | 8152 | 8ec8738d-1626-46bd-b220-a10a5681aaa8 |
| canary_meg_crewv | mega:1 | 8152 | 8dfefe3f-6f64-4a2d-a21b-0c536c305d3b |
| canary_meg_paxv | mega:2 | 8152 | 52bbf6b6-e2a9-42af-ab08-7e6714f81702 |
| canary_meg_mixv | mega:3 | 8152 | 984f27af-714f-4cd9-845b-ca87e2cfba7b |

### canary readout — 2026-11-03, measured at image `526cf856`

All 12 children SUCCEEDED; per-cell summary.json
`mechanisms.provisioned_source.norwalk_gi` witness verified —
`actual_venues_used` ⊆ pin set and `n_lots_placed` ==
`n_contaminated` on every cell (placement moved, count preserved;
seed-paired with the q30 baseline: every canary seed carried 2
lots in the baseline and places 2 here).

| cell | venues used | n_lots |
|---|---|---|
| exp/crewv s8169 | CrewMess | 2/2 |
| exp/paxv s8169 | MainDining | 2/2 |
| exp/mixv s8169 | CrewMess, MainDining | 2/2 |
| cls/crewv s8169 | CrewMess | 2/2 |
| cls/paxv s8169 | MainDining_L | 2/2 |
| cls/mixv s8169 | CrewMess, MainDining_U | 2/2 |
| spr/crewv s8152 | CrewMessMain, CrewMessOff | 2/2 |
| spr/paxv s8152 | MainDining_L | 2/2 |
| spr/mixv s8152 | MainDining_L, SpecialtyB | 2/2 |
| meg/crewv s8152 | CrewMess_Fwd, Crew_Mess_Main | 2/2 |
| meg/paxv s8152 | MainDining_L | 2/2 |
| meg/mixv s8152 | ComedyClub, MainDining_L | 2/2 |

**Canary verdict:** gates pass on every hull — venue ⊆ pin, lot
count preserved vs the seed-paired baseline, weights echoed in the
witness on the mixed arm, and the mixed arm spreads each seed's 2
lots across distinct venues (weighted placement, not round-robin:
indices would have pinned MainDining+CasualDining on exp, not
CrewMess+MainDining).

## Readout log

Wave 1 complete as of 2026-11-04 ~22:10 UTC — **12,000/12,000 cells
SUCCEEDED, 0 failed cells** across all 12 array jobs (9 small-hull
blocks + 3 mega). Mega legs were the wall-clock tail (vCPU-bound at
the 256-vCPU Spot CE cap, ~50 concurrent ~28-min cells, ~95 cells/hr
on the last arm).

### Scan rows (2026-11-04)

- 12/12 `_scan_rows` files delivered under
  `campaign/noro_provisioned_venue_02/_scan_rows/` — 1,000 rows each,
  0 errors; meg rows under the parent prefix per convention.
- **Decision:** rows generated with `--no-census` (summary.json only).
  Census-member decode measured ~2 h/tier (~400–800 MB member per
  zip); the reducer's `observation_jsonl` adapter only indexes rows,
  so census content is not consumed downstream — venue fields come
  from the run zips' summary.json via the extraction profile. Row
  `cs_echo` retains the full venue witness (pin + weights +
  `source_venue_arm`).

### Delivery-leg preparation (2026-11-03)

- `deploy/aws/build_first_paper_venue02.py` — sources/request/cohort
  builder for `red-fps02-venue02`: 12 arms (4 hulls × crewv/paxv/mixv),
  `first_paper_scalar`/1.4.0 extraction, shard_size 64, Phase-B-scale
  budgets (~12k sources, $100 cap).
- `docs/campaign_reduction/phase_venue02/red-fps02-venue02-return-request.json`
  — `crusher-campaign-distributions/1.0-proposed` collect request,
  allowlist = `attempts/red-fps02-venue02/`, scope register
  `3f73b584…`, budgets scaled for the ~190-shard page set.
- Scan-row producer: `tools/noro_diag/food_shapes_01_scan.py` per tier
  prefix (same tool as the venue pilot); canary cells excluded by
  prefix (`canary_*` prefixes never match `fl_*` tier prefixes); meg
  rows upload under the PARENT `_scan_rows/` prefix per convention.

### Materialize dispatch (2026-11-04)

- Cohort built clean: 12,012 sources (12,000 zips + 12 scan files),
  12,000 unique run keys, 0 duplicates, seed spans 8000–8999 (exp) /
  8105–9104 (cls/spr/meg) as designed.
- **Attempt A** `red-fps02-venue02` (request sha `01418a88…`,
  sources `2c8bff77…`): materialize `budget_stopped` at shard 0 —
  `checkpoint_reserve_bytes` 100 MB under-sized vs the 142 MB
  cohort-delta checkpoint (see report §7). Objects under
  `attempts/red-fps02-venue02/` are inert strays.
- **Attempt B** `red-fps02-venue02-b` (request sha `abe0960c…`,
  sources `38641803…`): same cohort, reserve raised to 300 MB /
  3600 s; dispatched on `picard-analysis-queue`,
  `picard-reducer:11`, `dry_run=false`, `aws-campaign` env approval.
- Return request `red-fps02-venue02-b-return-request.json`
  (allowlist `attempts/red-fps02-venue02-b/`); return-leg sha =
  raw `sha256sum` of the file body
  `691f9b9b1724a286e422079f94772587af0b29c10c664cf91f4f9ecf728eecb5`
  (the workflow verifies raw bytes, materialize verifies canonical —
  per `reducer-dispatch-pins`).
