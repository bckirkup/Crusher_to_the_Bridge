# NORO-MEGA-01 baseline reanalysis (MEGA-IMPACT design inputs)

Status: measured — per-voyage shape + threshold-distance + pathway-mix descriptors of the existing NORO-MEGA-01 zips. Tool: `tools/noro_diag/mega_baseline_reanalysis.py` (regenerates this file). Complements `noro_onset_curve_01_readout.md`, which established the burst12>0.5 absence on this same cell.

Source: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_mega_01/fl_mega_12d_scr/` — 308 run zips, ranged `summary.json` reads only; census member touched only on the stride sample below.

## Cell

| n | ignited | acquired>0 | posted | VSP triggered | detected |
|---|---|---|---|---|---|
| 308 | 308 | 308 | 0 | 0 | 33 |

## Distance to the posting threshold

Threshold = ceil(3% x channel complement) per voyage.

| channel | median reports | p90 | max | median ratio | p90 | max |
|---|---|---|---|---|---|---|
| pax | 56 | 65 | 106 | 0.381 | 0.442 | 0.721 |
| crew | 18 | 26 | 47 | 0.286 | 0.417 | 0.746 |

Voyages whose best channel ratio reached a fraction of threshold:

| >= 80% | >= 90% | >= 95% | >= 100% (posts) |
|---|---|---|---|
| 0 | 0 | 0 | 0 |

## Onset shape

| measure | median | p90 | max | n |
|---|---|---|---|---|
| burst12 share (12-epoch max window / total acq) | 0.184 | 0.210 | 0.285 | 308 |
| peak epoch | 287.000 | 287.000 | 287.000 | 308 |
| detection epoch (detected voyages) | 282.000 | 286.000 | 287.000 | 33 |

Still-climbing voyages (last acquisition in the final 2 epochs): 291/308.

## Pathway mix (stride sample)

Zips read: 24; acquired-host pathway mentions: 23950 (acquisition row + host row counted once each).

| dominant_pathway | mentions | share |
|---|---|---|
| fomite | 22784 | 0.951 |
| caregiver | 802 | 0.033 |
| direct_contact | 262 | 0.011 |
| emesis_aerosol | 102 | 0.004 |

Measured at campaign SHA + seeds recorded per zip; no parameters were fitted.
