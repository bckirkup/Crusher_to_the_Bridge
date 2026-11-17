# NORO supply solver screen 03 readout

**Measured at:** `c6c3c25fbabefa7ed918cba55311ceec231dbba3`
S3 prefix: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_03/`
Image: `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign:noro-supply-solver03@sha256:203536dea284153523e1ea874ad76651efecb34d0458a08d957c8f465277452a`
Cells: 88 run zips (88 unique, 0 duplicate, 0 failed/missing).

Endpoints: posting = `vsp_trigger_epoch is not None`; ARs below are posted-conditional unless noted. Days use 24 epochs/day.

## Strata (posted-conditional medians)
| hull | supply arm | solver | n | posted | AR median [range] | pax reported AR median [range] | crew reported AR median [range] | VSP epoch median [range] |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| meg | station_lots | discrete | 16 | 1/16 | 0.083 [0.083, 0.083] | 0.0455 [0.0455, 0.0455] | 0.0238 [0.0238, 0.0238] | 56 [56, 56] |
| meg | station_lots | continuous | 16 | 1/16 | 0.0821 [0.0821, 0.0821] | 0.0445 [0.0445, 0.0445] | 0.0148 [0.0148, 0.0148] | 75 [75, 75] |
| meg | station_lots_quiet | discrete | 8 | 0/8 | — — | — — | — — | — — |
| meg | station_lots_quiet | continuous | 8 | 0/8 | — — | — — | — — | — — |
| meg | single_line_receipt | discrete | 10 | 0/10 | — — | — — | — — | — — |
| meg | single_line_receipt | continuous | 10 | 0/10 | — — | — — | — — | — — |
| meg | declared_receipts | discrete | 10 | 0/10 | — — | — — | — — | — — |
| meg | declared_receipts | continuous | 10 | 0/10 | — — | — — | — — | — — |

## Paired continuous - discrete (sign test)

| hull | supply arm | pairs | posted both | pax AR median diff (p) | crew AR median diff (p) | AR median diff (p) | VSP epoch median diff (p) |
|---|---|---:|---:|---:|---:|---:|---:|
| meg | declared_receipts | 10 | 0 | — | — | — | — |
| meg | single_line_receipt | 10 | 0 | — | — | — | — |
| meg | station_lots | 16 | 1 | -0.001 (p=1.0, n=1) | -0.009 (p=1.0, n=1) | -0.0009 (p=1.0, n=1) | 19 (p=1.0, n=1) |
| meg | station_lots_quiet | 8 | 0 | — | — | — | — |

## Interpretation

Interpretation: on the mega p06 cell the frozen stratified supply seeds almost never reach the VSP wire. `station_lots` posted 1/16 on each solver arm (the same seed posted on both), `single_line_receipt` and `declared_receipts` posted 0/10, and quiet controls posted 0/8. Because only one seed posted on both solvers, the paired continuous-minus-discrete sign tests are uninformative (n=1), so this screen cannot separate the solvers on mega; the measured mega result is that supply contamination at these burdens is a weak posting driver on the 7000-agent hull. The open decision is whether mega needs a different seed/burden stratum or whether supply contamination should be down-weighted as a posting mechanism at this complement.

## Notes

- This is a screen, not anchor fitting: the frozen rule is an uncertainty-qualified association; overlapping ranges or few posted cells make a stratum uninformative.
- Quiet controls are station_lots seeds with zero contaminated provisioned lots in the census; they test whether the solver arm alone manufactures posting.
