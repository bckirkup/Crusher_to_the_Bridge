# NORO supply solver screen 02 readout

**Measured at:** `455f9ff788e85580a8253438fb4137ff69e22146`
S3 prefix: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_02/`
Image: `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign:noro-supply-solver02@sha256:0dea8f12e65108edb995f65e2ade1392c5568c7c53b9672ba4f91af33694a092`
Cells: 176 run zips (176 unique, 0 duplicate).

Endpoints: posting = `vsp_trigger_epoch is not None`; ARs below are posted-conditional unless noted. Days use 24 epochs/day.

## Strata (posted-conditional medians)
| hull | supply arm | solver | n | posted | AR median [range] | pax reported AR median [range] | crew reported AR median [range] | VSP epoch median [range] |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| cls | station_lots | discrete | 16 | 9/16 | 0.1052 [0.0843, 0.1356] | 0.0568 [0.0456, 0.08] | 0.0122 [0.007, 0.0297] | 64 [52, 69] |
| cls | station_lots | continuous | 16 | 10/16 | 0.1028 [0.0691, 0.1492] | 0.0605 [0.0306, 0.0934] | 0.0122 [0.0052, 0.021] | 63.0 [52, 212] |
| cls | station_lots_quiet | discrete | 8 | 0/8 | — — | — — | — — | — — |
| cls | station_lots_quiet | continuous | 8 | 0/8 | — — | — — | — — | — — |
| cls | single_line_receipt | discrete | 10 | 6/10 | 0.0832 [0.0639, 0.1058] | 0.0433 [0.0336, 0.0598] | 0.0114 [0.007, 0.0227] | 62.5 [48, 80] |
| cls | single_line_receipt | continuous | 10 | 5/10 | 0.0948 [0.0691, 0.111] | 0.0561 [0.0359, 0.0628] | 0.014 [0.0035, 0.0192] | 48 [44, 102] |
| cls | declared_receipts | discrete | 10 | 4/10 | 0.1076 [0.0785, 0.1099] | 0.0612 [0.0381, 0.0688] | 0.0113 [0.0052, 0.0175] | 60.5 [51, 72] |
| cls | declared_receipts | continuous | 10 | 4/10 | 0.1084 [0.0743, 0.1168] | 0.0602 [0.0396, 0.0732] | 0.007 [0.0052, 0.0262] | 59.5 [55, 69] |
| spr | station_lots | discrete | 16 | 7/16 | 0.0997 [0.075, 0.116] | 0.0571 [0.0395, 0.0705] | 0.0144 [0.0056, 0.0211] | 59 [35, 88] |
| spr | station_lots | continuous | 16 | 8/16 | 0.0917 [0.0617, 0.1197] | 0.0531 [0.0305, 0.0781] | 0.0138 [0.01, 0.0244] | 58.0 [36, 174] |
| spr | station_lots_quiet | discrete | 8 | 0/8 | — — | — — | — — | — — |
| spr | station_lots_quiet | continuous | 8 | 0/8 | — — | — — | — — | — — |
| spr | single_line_receipt | discrete | 10 | 3/10 | 0.077 [0.063, 0.111] | 0.0352 [0.0324, 0.0552] | 0.0156 [0.0089, 0.0156] | 98 [90, 103] |
| spr | single_line_receipt | continuous | 10 | 4/10 | 0.0765 [0.065, 0.1097] | 0.0364 [0.031, 0.06] | 0.0133 [0.0089, 0.0222] | 97.0 [73, 160] |
| spr | declared_receipts | discrete | 10 | 2/10 | 0.0746 [0.0673, 0.082] | 0.0372 [0.0314, 0.0429] | 0.0117 [0.0111, 0.0122] | 113.5 [107, 120] |
| spr | declared_receipts | continuous | 10 | 2/10 | 0.081 [0.0653, 0.0967] | 0.0424 [0.0324, 0.0524] | 0.0156 [0.0111, 0.02] | 102.5 [100, 105] |

## Paired continuous - discrete (sign test)

| hull | supply arm | pairs | posted both | pax AR median diff (p) | crew AR median diff (p) | AR median diff (p) | VSP epoch median diff (p) |
|---|---|---:|---:|---:|---:|---:|---:|
| cls | declared_receipts | 10 | 4 | 0.003 (p=0.625, n=4) | 0.0001 (p=1.0, n=4) | 0.0014 (p=1.0, n=4) | -1.5 (p=0.625, n=4) |
| cls | single_line_receipt | 10 | 5 | 0.0038 (p=1.0, n=5) | -0.0009 (p=1.0, n=4) | 0.0052 (p=0.375, n=5) | -3.0 (p=0.625, n=4) |
| cls | station_lots | 16 | 9 | 0.0045 (p=0.1797, n=9) | -0.0017 (p=0.5078, n=9) | 0.0026 (p=0.5078, n=9) | -0.5 (p=1.0, n=6) |
| cls | station_lots_quiet | 8 | 0 | — | — | — | — |
| spr | declared_receipts | 10 | 2 | 0.0053 (p=0.5, n=2) | 0.0078 (p=1.0, n=1) | 0.0063 (p=1.0, n=2) | -11.0 (p=0.5, n=2) |
| spr | single_line_receipt | 10 | 3 | 0.0029 (p=0.25, n=3) | -0.0034 (p=1.0, n=3) | 0.002 (p=1.0, n=3) | -4 (p=1.0, n=3) |
| spr | station_lots | 16 | 7 | 0.0024 (p=0.6875, n=6) | 0.0034 (p=0.125, n=7) | 0.0017 (p=0.4531, n=7) | 1 (p=1.0, n=5) |
| spr | station_lots_quiet | 8 | 0 | — | — | — | — |

Interpretation: on the classic and spirit p06 cells the contaminated supply strata do **not** saturate posting — station_lots posted 7–10/16 per solver arm, receipt strata 2–6/10, and quiet controls 0/8 on both hulls. Posted-conditional passenger reported-case AR medians are ~3.5–6.1% and overlap across solver arms; every paired continuous-minus-discrete sign test is unresolved (passenger AR p ≥ 0.1797, VSP epoch p ≥ 0.5). The continuous contamination solver is therefore not separated from the discrete baseline at posting resolution on these hulls; the open decision is whether posting frequency itself, rather than posted-conditional AR, is the supply-solver-sensitive endpoint to sweep next.
