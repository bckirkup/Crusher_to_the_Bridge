# NORO-HAND-CASCADE-01-SUBSTEPS-FIXED
**Date:** 2026-11-14
**Commit:** 94daa3bf
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 94daa3bf

Fixed-engine re-pilot of the posted-cell DS-M arm after `CS-WINDOW-ORDER-01`
canonicalized common-source meal-token order. This supersedes the
uncontrolled-hash ratio check in `NORO-HAND-CASCADE-01-SUBSTEPS` for paired DS-M
comparisons; the pre-fix tables remain as the historical record.

Cell: `fl_exp_12d_sens_p06_paxv`, `expedition_cruise_450`, `norwalk_gi`, 288
epochs. Seeds 8073, 8038, 8046, 8047, and 8077; arms `carriers_ordered` (M=1),
`carriers_ordered_sub2`, `carriers_ordered_sub4`, and `carriers_ordered_sub12`.
All pilot rows ran with `PYTHONHASHSEED=1`; each seed was a fresh process
running the four arms sequentially. Hash-0 spot checks for seed 8073 M=1,
seed 8038 sub2, seed 8038 sub12, and seed 8047 sub12 reproduced the
corresponding hash-1 rows exactly.

| seed | arm | infected | symptomatic | dose GEC | delivered GEC | deposited GEC | carrier surface GEC / calls |
|---:|---|---:|---:|---:|---:|---:|---:|
| 8038 | `carriers_ordered` | 124 | 63 | 302,233 | 10,931,565 | 6,264,823 | 6,095,209 / 6,733 |
| 8038 | `carriers_ordered_sub2` | 106 | 50 | 793,030 | 52,141,252 | 25,008,588 | 24,819,609 / 20,029 |
| 8038 | `carriers_ordered_sub4` | 97 | 54 | 486,683 | 24,769,603 | 10,916,897 | 10,752,567 / 28,658 |
| 8038 | `carriers_ordered_sub12` | 97 | 61 | 770,283 | 39,314,281 | 15,625,049 | 15,476,026 / 99,049 |
| 8046 | `carriers_ordered` | 98 | 49 | 338,642 | 14,423,941 | 7,483,588 | 7,237,821 / 5,643 |
| 8046 | `carriers_ordered_sub2` | 107 | 63 | 920,043 | 47,020,015 | 22,413,170 | 22,052,738 / 15,175 |
| 8046 | `carriers_ordered_sub4` | 105 | 51 | 2,073,157 | 76,223,886 | 36,629,009 | 36,413,060 / 32,167 |
| 8046 | `carriers_ordered_sub12` | 102 | 51 | 702,515 | 40,356,002 | 17,066,664 | 16,705,431 / 140,401 |
| 8047 | `carriers_ordered` | 76 | 38 | 972,162 | 31,772,698 | 16,602,056 | 16,497,637 / 3,054 |
| 8047 | `carriers_ordered_sub2` | 88 | 46 | 415,221 | 18,117,819 | 11,818,652 | 10,419,990 / 11,879 |
| 8047 | `carriers_ordered_sub4` | 72 | 35 | 2,188,529 | 80,239,875 | 34,749,035 | 34,634,302 / 28,866 |
| 8047 | `carriers_ordered_sub12` | 69 | 35 | 125,260 | 9,019,511 | 3,949,886 | 3,833,622 / 82,229 |
| 8073 | `carriers_ordered` | 104 | 54 | 1,461,814 | 49,409,642 | 21,170,528 | 21,020,834 / 6,678 |
| 8073 | `carriers_ordered_sub2` | 108 | 55 | 576,050 | 30,332,525 | 14,906,151 | 14,687,927 / 21,030 |
| 8073 | `carriers_ordered_sub4` | 104 | 59 | 1,476,907 | 72,284,787 | 30,169,618 | 29,936,058 / 46,017 |
| 8073 | `carriers_ordered_sub12` | 118 | 71 | 1,699,772 | 77,311,422 | 34,762,661 | 34,575,753 / 138,813 |
| 8077 | `carriers_ordered` | 74 | 32 | 590,029 | 25,506,373 | 9,978,454 | 9,854,091 / 7,342 |
| 8077 | `carriers_ordered_sub2` | 70 | 23 | 656,180 | 21,223,094 | 10,083,310 | 9,915,245 / 15,894 |
| 8077 | `carriers_ordered_sub4` | 71 | 34 | 660,762 | 38,783,943 | 13,829,451 | 13,721,364 / 31,527 |
| 8077 | `carriers_ordered_sub12` | 87 | 40 | 352,030 | 27,218,796 | 14,824,379 | 14,193,885 / 241,934 |

Ratio check vs fixed M=1 (delivered / dose / deposited): seed 8038 sub2 is
4.77x/2.62x/3.99x, sub4 is 2.27x/1.61x/1.74x, and sub12 is 3.60x/2.55x/2.49x;
seed 8046 sub2 is 3.26x/2.72x/2.99x, sub4 is 5.28x/6.12x/4.89x, and sub12 is
2.80x/2.07x/2.28x; seed 8047 sub2 is 0.57x/0.43x/0.71x, sub4 is
2.53x/2.25x/2.09x, and sub12 is 0.28x/0.13x/0.24x; seed 8073 sub2 is
0.61x/0.39x/0.70x, sub4 is 1.46x/1.01x/1.43x, and sub12 is
1.56x/1.16x/1.64x; seed 8077 sub2 is 0.83x/1.11x/1.01x, sub4 is
1.52x/1.12x/1.39x, and sub12 is 1.07x/0.60x/1.49x.

Measured: fixed-M is still not converged through M=12 on the five posted seeds.
M=2/4/12 are non-monotone within seeds and inconsistent across seeds, and
carrier surface calls grow to ~82k-242k at M=12 without a stable deposited,
delivered, or dose limit.

Inferred: the determinism fix did not turn DS-M into a stable refinement; the
fixed-M residual is not explained by the common-source hash-order leak. Fixed
M=1 baselines also move for seeds whose uncontrolled-hash witness rows were not
canonical, notably 8073 and 8077, so the pre-fix pilot ratios for those seeds
are historical only.

Hypothesis: the next solver branch remains the continuous/event-driven
contamination reference or a redesigned stochastic substep rule; a larger
fixed M is not justified by these data. This entry does not fit constants or
flip defaults.
