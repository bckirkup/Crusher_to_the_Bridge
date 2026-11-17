# NORO-HAND-CASCADE-01-SUBSTEPS-M60
**Date:** 2026-11-16
**Commit:** af8dda30
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** af8dda30

Completes the predeclared fixed-M DS-M sweep through M=60 on the posted cell and records the solver-gate branch. It adds `carriers_ordered_sub24` and `carriers_ordered_sub60` to `tools/noro_diag/hand_cascade_witness.py` and re-measures `carriers_ordered` (M=1) for runtime. The M=2/4/12 rows are the committed `NORO-HAND-CASCADE-01-SUBSTEPS-CURRENT` rows measured at `605f9841`; `605f9841..0b79b716` has no diff for `engines/transmission_core.py`, the `expedition_cruise_450` platform, the SENSITIVITY-01 manifest, the campaign spec, or `data/pathogens`, so those rows are reused. The harness commit `af8dda30` only adds arms/runtime timing. No constants were fitted and no default was flipped.

Cell: `fl_exp_12d_sens_p06_paxv`, `expedition_cruise_450`, `norwalk_gi`, 288 epochs. Seeds 8073, 8038, 8046, 8047, and 8077; arms `carriers_ordered` (M=1), `carriers_ordered_sub2`, `carriers_ordered_sub4`, `carriers_ordered_sub12`, `carriers_ordered_sub24`, and `carriers_ordered_sub60`. M=1/24/60 ran at `af8dda30` with `PYTHONHASHSEED=1`, one fresh process per seed; the M=1 numerical outputs reproduce the earlier M=1 rows.

| seed | arm | infected | symptomatic | dose GEC | delivered GEC | deposited GEC | carrier surface GEC / calls | runtime s |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 8038 | `carriers_ordered` | 110 | 60 | 484,763 | 13,366,939 | 1,711,137 | 1,526,451 / 3488 | 71.7 |
| 8038 | `carriers_ordered_sub24` | 120 | 64 | 643,267 | 41,466,114 | 3,572,290 | 3,134,721 / 246063 | 169.9 |
| 8038 | `carriers_ordered_sub60` | 102 | 56 | 550,760 | 26,096,432 | 1,944,152 | 1,536,412 / 372927 | 253.3 |
| 8046 | `carriers_ordered` | 91 | 52 | 786,696 | 28,222,209 | 929,244 | 804,090 / 3707 | 64.5 |
| 8046 | `carriers_ordered_sub24` | 105 | 54 | 1,369,989 | 41,126,202 | 2,224,325 | 1,971,141 / 188066 | 160.8 |
| 8046 | `carriers_ordered_sub60` | 119 | 57 | 743,547 | 31,333,792 | 2,903,840 | 2,559,935 / 427747 | 283.5 |
| 8047 | `carriers_ordered` | 67 | 34 | 528,210 | 13,876,799 | 1,448,296 | 1,080,773 / 1816 | 63.0 |
| 8047 | `carriers_ordered_sub24` | 73 | 40 | 428,590 | 15,806,338 | 531,285 | 442,428 / 93520 | 114.0 |
| 8047 | `carriers_ordered_sub60` | 69 | 32 | 45,984 | 1,569,036 | 143,690 | 60,188 / 129029 | 183.9 |
| 8073 | `carriers_ordered` | 111 | 65 | 1,398,418 | 28,379,117 | 1,539,345 | 1,361,044 / 4329 | 63.1 |
| 8073 | `carriers_ordered_sub24` | 115 | 66 | 1,232,489 | 52,842,578 | 2,601,354 | 2,006,288 / 207036 | 132.3 |
| 8073 | `carriers_ordered_sub60` | 123 | 69 | 1,673,993 | 54,314,924 | 2,317,129 | 2,081,631 / 609380 | 301.8 |
| 8077 | `carriers_ordered` | 76 | 35 | 1,574,473 | 37,454,112 | 2,156,159 | 2,001,629 / 3268 | 59.7 |
| 8077 | `carriers_ordered_sub24` | 78 | 34 | 1,767,382 | 61,958,065 | 1,512,377 | 1,405,311 / 131424 | 153.3 |
| 8077 | `carriers_ordered_sub60` | 79 | 36 | 230,934 | 13,840,503 | 578,631 | 460,170 / 372522 | 220.3 |

Convergence is scored against the solver-gate tolerance: deposited mass, delivered mass, and dose must be within 10% relative error on the same seeds. The table gives the maximum across the five posted seeds of `|later - earlier| / earlier` for each consecutive pair; infection counts are reported above but are not gated at this stage.

| pair | deposited max abs rel | delivered max abs rel | dose max abs rel |
|---|---:|---:|---:|
| M1->M2 | 165.9% | 448.1% | 412.0% |
| M2->M4 | 430.3% | 409.8% | 916.1% |
| M4->M12 | 107.3% | 106.9% | 101.5% |
| M12->M24 | 87.1% | 172.4% | 168.3% |
| M24->M60 | 73.0% | 90.1% | 89.3% |

For the final pair, per-seed dose relative changes are -14.4%, -45.7%, -89.3%, +35.8%, and -86.9% for seeds 8038/8046/8047/8073/8077; no seed is within ±10% on all three gated metrics.

| seed | M24 runtime s | M60 runtime s | M24/M1 | M60/M1 |
|---:|---:|---:|---:|---:|
| 8038 | 169.9 | 253.3 | 2.37 | 3.53 |
| 8046 | 160.8 | 283.5 | 2.49 | 4.39 |
| 8047 | 114.0 | 183.9 | 1.81 | 2.92 |
| 8073 | 132.3 | 301.8 | 2.10 | 4.78 |
| 8077 | 153.3 | 220.3 | 2.57 | 3.69 |

Mass balance: for the re-run M=1/24/60 rows, `deposited == removed + residual` closes with max absolute error 7.1e-9 GEC (relative error ≤ 4.7e-15), and `delivered_to_reservoir_gec` is 0.0 on every row. The witness wrappers are read-only with respect to engine RNG; paired seeds are the floor, and no separate substep RNG-stream probe was run in this sweep.

Measured: fixed-M is not converged through M=60 on the five posted seeds. Every consecutive refinement pair exceeds the 10% tolerance on at least one seed for deposited, delivered, and dose; the smallest worst-seed change is still 73.0% (deposited, M24->M60). The sequence remains non-monotone and seed-dependent, and infection-count movement is likewise non-monotone (reported, not gated). Runtime grows from 59.7–71.7 s/voyage at M=1 to 114.0–169.9 s at M=24 and 183.9–301.8 s at M=60 on this cell.

Inferred: under the solver-gate decision rule, no `M <= 60` converges and the runtime growth makes high-M fixed substeps campaign-prohibitive; the next branch is the CE contamination-loop comparator, not shipping DS-M or flipping `transmission.intra_epoch_substeps` / `transmission.intra_epoch_causal_order` defaults.

Hypothesis: CE can serve as the numerical reference/fallback if it reuses existing rates/kernels with zero new fitted constants and keeps the legacy/discrete paths bit-identical; whether it is cheaper than M=60 is unknown until implemented.
