# NORO-HAND-CASCADE-01-SUBSTEPS-CURRENT
**Date:** 2026-11-16
**Commit:** 605f9841
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 605f9841

Current-main re-pilot of the posted-cell fixed-M DS-M arm after the platform/HVAC data changes that made the `94daa3bf` pilot rows historical (`NORO-HAND-CASCADE-01-CONTACT-BINDING`). This is the convergence check for the `transmission.intra_epoch_substeps > 1` default question; it does not fit constants or flip defaults.

Cell: `fl_exp_12d_sens_p06_paxv`, `expedition_cruise_450`, `norwalk_gi`, 288 epochs. Seeds 8073, 8038, 8046, 8047, and 8077; arms `carriers_ordered` (M=1), `carriers_ordered_sub2`, `carriers_ordered_sub4`, and `carriers_ordered_sub12`. All rows ran with `PYTHONHASHSEED=1`; each seed was a fresh process running the four arms sequentially.

| seed | arm | infected | symptomatic | dose GEC | delivered GEC | deposited GEC | carrier surface GEC / calls |
|---:|---|---:|---:|---:|---:|---:|---:|
| 8038 | `carriers_ordered` | 110 | 60 | 484,763 | 13,366,939 | 1,711,137 | 1,526,451 / 3488 |
| 8038 | `carriers_ordered_sub2` | 100 | 59 | 2,482,166 | 73,264,235 | 2,610,203 | 2,409,660 / 8786 |
| 8038 | `carriers_ordered_sub4` | 104 | 47 | 558,995 | 23,489,640 | 1,947,721 | 1,671,027 / 25324 |
| 8038 | `carriers_ordered_sub12` | 117 | 66 | 992,583 | 33,178,515 | 1,909,053 | 1,290,791 / 96718 |
| 8046 | `carriers_ordered` | 91 | 52 | 786,696 | 28,222,209 | 929,244 | 804,090 / 3707 |
| 8046 | `carriers_ordered_sub2` | 103 | 59 | 1,528,558 | 39,329,027 | 2,272,340 | 2,109,154 / 11668 |
| 8046 | `carriers_ordered_sub4` | 100 | 41 | 297,046 | 13,585,371 | 1,349,173 | 860,842 / 24950 |
| 8046 | `carriers_ordered_sub12` | 103 | 50 | 598,639 | 28,107,439 | 1,438,739 | 1,240,258 / 96944 |
| 8047 | `carriers_ordered` | 67 | 34 | 528,210 | 13,876,799 | 1,448,296 | 1,080,773 / 1816 |
| 8047 | `carriers_ordered_sub2` | 68 | 32 | 139,222 | 7,444,174 | 315,221 | 222,870 / 5342 |
| 8047 | `carriers_ordered_sub4` | 77 | 37 | 1,414,650 | 37,951,826 | 1,671,580 | 1,442,219 / 22199 |
| 8047 | `carriers_ordered_sub12` | 68 | 31 | 206,643 | 9,436,809 | 720,347 | 610,320 / 44506 |
| 8073 | `carriers_ordered` | 111 | 65 | 1,398,418 | 28,379,117 | 1,539,345 | 1,361,044 / 4329 |
| 8073 | `carriers_ordered_sub2` | 116 | 72 | 683,249 | 27,663,483 | 4,092,970 | 3,855,424 / 13105 |
| 8073 | `carriers_ordered_sub4` | 106 | 63 | 727,960 | 30,306,012 | 1,370,163 | 1,165,952 / 28183 |
| 8073 | `carriers_ordered_sub12` | 128 | 73 | 534,109 | 22,849,679 | 2,839,744 | 1,963,010 / 114612 |
| 8077 | `carriers_ordered` | 76 | 35 | 1,574,473 | 37,454,112 | 2,156,159 | 2,001,629 / 3268 |
| 8077 | `carriers_ordered_sub2` | 70 | 33 | 731,935 | 27,581,644 | 1,820,880 | 1,697,439 / 7301 |
| 8077 | `carriers_ordered_sub4` | 59 | 27 | 1,078,968 | 37,075,806 | 1,078,231 | 965,416 / 16693 |
| 8077 | `carriers_ordered_sub12` | 90 | 42 | 658,638 | 22,747,941 | 1,376,227 | 1,181,345 / 115301 |

Ratio check vs fixed M=1 (delivered / dose / deposited): seed 8038 sub2 is
5.48x/5.12x/1.53x, sub4 is 1.76x/1.15x/1.14x, and sub12 is 2.48x/2.05x/1.12x;
seed 8046 sub2 is 1.39x/1.94x/2.45x, sub4 is 0.48x/0.38x/1.45x, and sub12 is
1.00x/0.76x/1.55x; seed 8047 sub2 is 0.54x/0.26x/0.22x, sub4 is
2.73x/2.68x/1.15x, and sub12 is 0.68x/0.39x/0.50x; seed 8073 sub2 is
0.97x/0.49x/2.66x, sub4 is 1.07x/0.52x/0.89x, and sub12 is 0.81x/0.38x/1.84x;
seed 8077 sub2 is 0.74x/0.46x/0.84x, sub4 is 0.99x/0.69x/0.50x, and sub12 is
0.61x/0.42x/0.64x.

Measured: fixed-M is still not converged through M=12 on the five posted seeds at `605f9841`. M=2/4/12 are non-monotone within seeds and inconsistent across seeds; carrier surface calls grow from roughly 1.8k-4.3k at M=1 to roughly 44k-115k at M=12 without a stable deposited, delivered, or dose limit. The current M=1 rows also differ from the `94daa3bf` fixed pilot, so the older DS-M ratios are historical only.

Inferred: `transmission.intra_epoch_substeps > 1` is not justified as a default by these data. Making it default would also require `intra_epoch_causal_order="ordered"` and the pooled-fomite restriction, and would ship a solver arm whose refinement direction is seed-dependent.

Hypothesis: the next solver branch remains the continuous/event-driven contamination reference or a redesigned stochastic substep rule; per the solver gate, any `M` should be chosen by convergence to that reference, not by anchor fit.
