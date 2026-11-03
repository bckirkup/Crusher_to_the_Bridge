# NORO-PROVISIONED-VENUE-01 — campaign ledger

**Status: declared — design frozen, no cells submitted.** Edison
PHASE2_PILOT_SPEC (approved scope, 2026-11-02): provisioned-lot venue
placement counterfactual — does relocating provisioned food-source
lots from crew-mess venues to the largest passenger dining venue
reverse the crew-heavy threshold-crossing pattern? Mechanism seam:
`provisioned_source.station_zone_pin` +
`provisioned_source.source_venue_arm` in
`engines/transmission_core.py`; voyage witness fields
(`station_zone_pin`, `source_venue_arm`, `n_lots_placed`,
`actual_venues_used`) surfaced on `summary.json` `mechanisms` for
ranged extraction. Extraction contract:
`first_paper_scalar/1.4.0`. Mega spec:
`campaigns/noro/provisioned_venue_01_mega/` (same manifest, elevated
memory — AGE-FOOD split precedent).

**Grid:** 4 hulls × 2 arms × 4 seeds = 32 cells + 8 canary cells
(1 seed × both arms per hull). Seeds per hull picked from delivered
q30 native-crossers nearest posting-conditional medians — rule and
full rows in `SEED_MANIFEST.json` (Edison verifies on delivery).

**Fixed coordinates:** identical to the delivered
NORO-PROVISIONED-SOURCE-01 q30 baseline — shipped bp
0.0325/0.0185, nsf 0.29, 288 epochs, syndromic_comp65, dose 7.57,
embarkation 2026-01-10, rung shipped. Only delta:
`station_zone_pin` + `source_venue_arm`.

**Submit gate:** PASSED — seam merged 2026-11-03 (PR #1147,
merge `13fa0f2f`); image `picard-campaign:noro-provisioned-venue01`
built FROM that SHA, pushed digest
`sha256:c5e7037aac8497898b15161b779dc552053798c3841eceb22f9395807853d260`,
ENGINE_GIT_SHA `13fa0f2f`. Manifest mirrored to
`s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_provisioned_venue_01/manifest.json`.
Canary 8 cells submitted 2026-11-03 — STOP until readout; user
gates the 32-cell array.

## Waves

| wave | blocks | cells | status |
|---|---|---|---|
| canary | 4 hulls × 2 arms × 1 seed | 8 | 8/8 SUCCEEDED, gates pass 2026-11-03 |
| 1 | 4 hulls × 2 arms × 4 seeds | 32 | awaiting user gate after canary |

### canary — submitted 2026-11-03

Image `picard-campaign:noro-provisioned-venue01` @ `13fa0f2f`
(digest `sha256:c5e7037a`). Jobdef `picard-noro-provisioned-venue-01`
revs 1–6 + `…-mega` revs 1–2 (fresh rev per submit, per convention).

| cell | jobdef | seeds | job id |
|---|---|---|---|
| canary_exp_crewv | :1 | 8869 | 26dde641-bb8c-4946-a4e2-45fe8433d4c2 |
| canary_exp_paxv | :2 | 8869 | 6a9d238d-295c-4c0c-9b29-af6d3f17f253 |
| canary_cls_crewv | :3 | 8892 | 0e993f17-2d76-435c-bc93-cab10dc02741 |
| canary_cls_paxv | :4 | 8892 | 860790f1-8ef8-4737-a370-adc76f8ee13f |
| canary_spr_crewv | :5 | 8620 | 3d291ec5-b164-48fa-bd4b-c86b1a6e9e1e |
| canary_spr_paxv | :6 | 8620 | f28385dd-2399-48b8-a7b5-51c7aa25ba61 |
| canary_meg_crewv | mega:1 | 8548 | 88d1f680-882f-4cb4-8158-457b54945984 |
| canary_meg_paxv | mega:2 | 8548 | 66bf8c42-b1cc-47d9-bce1-52048918e447 |

### canary readout — 2026-11-03, all measured at image `13fa0f2f`

All 8 children SUCCEEDED; per-cell summary.json `mechanisms.provisioned_source.norwalk_gi`
witness verified — `actual_venues_used` ⊆ pin set and
`n_lots_placed` == `n_contaminated` on every cell (placement moved,
count preserved; multi-zone pins round-robin index 0 → first venue).

| cell | pin resolved to | n_lots | trigger_status |
|---|---|---|---|
| exp/crewv s8869 | CrewMess | 1/1 | LOCKDOWN |
| exp/paxv s8869 | MainDining | 1/1 | BASELINE |
| cls/crewv s8892 | CrewMess | 2/2 | LOCKDOWN |
| cls/paxv s8892 | MainDining_L | 2/2 | CONFIRMED |
| spr/crewv s8620 | CrewMessMain | 1/1 | LOCKDOWN |
| spr/paxv s8620 | MainDining_L | 1/1 | SUSPECTED |
| meg/crewv s8548 | Crew_Mess_Main | 1/1 | CONFIRMED |
| meg/paxv s8548 | MainDining_L | 1/1 | SUSPECTED |

**Canary verdict:** gates pass (venue ⊆ pin, lot count preserved,
witness on summary.json, image SHA stamped). Observed pattern on the
single canary seed per hull — hypothesis-grade only: crew-mess
placement lands a strictly more severe trigger than passenger-venue
placement on all four hulls.

## Readout log

### wave-1 array — 2026-11-03, measured at image `13fa0f2f`

All 32 cells SUCCEEDED (jobdefs `picard-noro-provisioned-venue-01`
revs 7–12 + `…-mega` revs 3–4; 30 zips under
`campaign/noro_provisioned_venue_01/`, 10 under `…_mega/` incl.
canary cells). Scan jobdef `picard-noro-scan-readout-ec2:7` wrote 8
`_scan_rows` files under the parent prefix, 4 rows each, 0 dupes.

Scan-row comparison (`posted` = trigger crossing; `rep_*_ar` = report
attack rate by role; `rep_*_n` = report counts). MEASURED:

| hull/seed | crewv posted | paxv posted | crewv split p/c | paxv split p/c |
|---|---|---|---|---|
| exp 8326 | yes | yes | 0.00/0.06 | 0.05/0.01 |
| exp 8494 | yes | yes | 0.00/0.11 | 0.09/0.01 |
| exp 8557 | no | no | 0.02/0.01 | 0.02/0.01 |
| exp 8869 | yes | yes | 0.01/0.10 | 0.05/0.01 |
| cls 8452 | yes | yes | 0.01/0.07 | 0.04/0.02 |
| cls 8498 | yes | yes | 0.00/0.07 | 0.05/0.02 |
| cls 8892 | yes | yes | 0.00/0.06 | 0.03/0.02 |
| cls 8983 | yes | yes | 0.01/0.06 | 0.05/0.03 |
| spr 8143 | yes | yes | 0.02/0.04 | 0.03/0.02 |
| spr 8620 | yes | no | 0.02/0.05 | 0.02/0.02 |
| spr 8869 | yes | yes | 0.01/0.05 | 0.05/0.03 |
| spr 8894 | yes | yes | 0.02/0.04 | 0.03/0.03 |
| meg 8199 | no | no | 0.02/0.03 | 0.02/0.01 |
| meg 8461 | yes | no | 0.01/0.05 | 0.03/0.01 |
| meg 8548 | yes | no | 0.02/0.04 | 0.02/0.02 |
| meg 8577 | yes | no | 0.01/0.05 | 0.02/0.02 |

Readout (measured; Edison owns acceptance analysis):

- Posted: crewv 14/16 vs paxv 10/16.
- Role split inverts on 15/16 paired seeds: crewv lands crew-heavy
  report rates, paxv lands passenger-heavy. Exception — exp/8557:
  identical pax-heavy split (0.019/0.0075) in BOTH arms; placement-
  invariant non-poster (inferred: no lot-driven exposure on that seed).
- Counterfactual trigger answer is hull-dependent: on meg, moving the
  source to `MainDining_L` drops 4/4 seeds below the trigger while
  still inverting the role split; on exp/cls the crossing survives
  with the inverted split; spr splits (8620 crosses only under crewv).
- Non-posters: exp/8557 (both arms), meg/8199 (both arms),
  spr/8620 (paxv only), meg/8461+8548+8577 (paxv only).

Reducer leg: request `red-fps02-venue` uploaded under
`campaign/_derived/reducer/v1/requests/` (canonical request sha
`eec0bcf2b54f02f4c93404daac755425d13ad41f5e7e7de21a425259d2114f33`,
sources manifest sha `6f93a4468aee70f248706f350740c83a3c1f4fac2bf39e50d9b540e75c000164`,
40 sources = 32 run zips + 8 scan-row files). `picard-reducer:11`
registered on `picard-boundary-analysis:reducer-v8` (image digest
`sha256:9e6d48bcf57c7821c5f330556015d6ddf0b849cde52d5a34035306468c249911`,
contract `first_paper_scalar/1.4.0`). Materialize dispatch:
`campaign-reduction-dispatch` run 41563269750.
