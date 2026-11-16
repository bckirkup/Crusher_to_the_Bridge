# NORO-HAND-REDEPOSIT-STREAM-01-WITNESS
**Date:** 2026-11-16
**Commit:** bae0d181
**Pathogens:** norwalk_gi
**Status:** open
**Measured at:** bae0d181

Paired-seed witness for the stream-preserving `carriers` repair merged in PR
#1261. Command:

```bash
python3 tools/noro_diag/hand_cascade_witness.py \
  --platform classic_cruise_1900 --epochs 288 \
  --seeds 8105 8106 --arms legacy carriers \
  --out reports/noro_diag/hand_cascade_witness_stream01
```

Run at `bae0d181` with `hand_reservoir_mode=hygiene_cycle`,
`intra_epoch_causal_order=legacy`, and `intra_epoch_substeps=1`.

Measured rows (`legacy` is `hand_redeposit_mode=shedders_only`):

| arm | seed | infected | symptomatic | delivered GEC | dose GEC | deposited GEC | carrier surface GEC / calls | carrier food GEC | carrier sanitary GEC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| legacy | 8105 | 6 | 1 | 533,716.071 | 1,658.507 | 139.463 | 0 / 0 | 0 | 0 |
| legacy | 8106 | 2 | 0 | 687.295 | 8.976 | 2,295.755 | 0 / 0 | 0 | 0 |
| carriers | 8105 | 7 | 2 | 835,635.286 | 31,332.203 | 6,527.787 | 2,319.185 / 178 | 20.402 | 0 |
| carriers | 8106 | 2 | 0 | 729.264 | 11.607 | 2,825.575 | 16.186 / 31 | 1.053 | 0 |

Paired deltas (`carriers - legacy`, same seed): seed 8105 deposited
+6,388.324 GEC, delivered +301,919.214 GEC, dose +29,673.696 GEC,
infected +1, symptomatic +1; seed 8106 deposited +529.820 GEC, delivered
+41.969 GEC, dose +2.630 GEC, infected 0, symptomatic 0.

Measured: the repaired `carriers` arm now produces nonzero carrier
hand→surface and hand→food deposits on both seeds, with no carrier sanitary
deposits observed, and both seeds show higher delivered/dose mass. The
epidemic count moves only on seed 8105. Inferred: the arm is acting as a
hand-mediated amplification path rather than the suppressed bundled arm from
`FOOD-SUPPLY-01-REDEPOSIT-WORST`. Hypothesis: carrier deposit draws still
consume the shared RNG stream and this is only two seeds, so this witness is
directional evidence, not yet a default-flip gate; `ordered`/substep arms and
a larger seed block are the next witnesses before flipping
`hand_redeposit_mode`.
