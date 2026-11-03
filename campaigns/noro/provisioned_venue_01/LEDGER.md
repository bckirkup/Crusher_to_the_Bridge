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
| canary | 4 hulls × 2 arms × 1 seed | 8 | submitted 2026-11-03, RUNNABLE |
| 1 | 4 hulls × 2 arms × 4 seeds | 32 | not submitted |

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

## Readout log

(none yet)
