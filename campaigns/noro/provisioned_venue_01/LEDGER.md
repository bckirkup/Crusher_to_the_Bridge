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

**Submit gate:** NO cells submit until the venue-pin seam merges to
main and the image pins a SHA containing it (campaign-preflight).
Canary 8 cells then STOP — user gates the 32-cell array.

## Waves

| wave | blocks | cells | status |
|---|---|---|---|
| canary | 4 hulls × 2 arms × 1 seed | 8 | not submitted |
| 1 | 4 hulls × 2 arms × 4 seeds | 32 | not submitted |

## Readout log

(none yet)
