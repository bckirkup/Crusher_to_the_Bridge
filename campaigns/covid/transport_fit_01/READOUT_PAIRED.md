# TRANSPORT-FIT-01 — paired provider readout (descriptive)

Date 2026-11-20. Source cells measured at `106a3583` (three blocks) and
`8de77294` (`dp_contamx_canary`). No cell was run for this readout. It
re-reads the 140 existing payloads, the 140 AWS Batch child records and
fleet-workup package 02, and replaces the "solver indistinguishability"
wording of `LEDGER.md` §5 with what the pairs show.

**Reading:** native and ContamX gave the same takeoff classification in
all 70 seed pairs and close voyage-wide counts in most, but not the same
voyage in every seed. One Diamond Princess pair differs by 39 recorded
onsets and 50 confirmations. Nothing here is an equivalence test (no
margin was declared before the runs), a statement about delivered dose,
or an attribution to any airflow repair.

## Method

- Δ is ContamX minus native within a seed. The independent unit is a
  seed: 20 pairs on the DP replay (`diamond_princess_2020` on the
  declared `mega_cruise_5000` substitution hull), 50 on the GM replay
  (`greg_mortimer_2020` on `expedition_cruise_450`). The replays differ
  in hull, scenario, Θ and policy and are never pooled.
- Interval: mean(Δ) ± t(0.975, n−1) · sd(Δ)/√n, sample sd, t = 2.093024
  (n = 20), 2.009575 (n = 50), 2.131450 (n = 16). Pointwise, unadjusted
  for the number of endpoints, conditional on these seeds and this
  configuration. With 17 of 20 DP differences exactly zero and one large
  one, the DP interval is a rough description, not coverage-calibrated.
- "Range" is the observed minimum and maximum. The bracketed pairs in
  `LEDGER.md` and `readout.py` are that script's nearest-rank q05–q95
  (sorted index `round(q·(n−1))`), which at n = 20 drops the largest
  value: they are not ranges.
- A share with a zero denominator is undefined and left out of that
  endpoint only; it is never counted as zero. Four DP seeds per arm (the
  same four) have no confirmation, so DP shares have 16 pairs.
- Takeoff is ≥ 10 recorded onsets, the campaign's own threshold.

## Coverage audit (all pass)

- 140 payloads, exactly the declared block × seed set, no duplicate.
- Every payload: design id, scenario, Θ, infection age, imports,
  sanitary mode, declared engine and resolved engine class match the
  design and arm; the ContamX binary echo is present on ContamX cells
  only.
- Inside every seed pair the delivery echo (engine keys aside), dose
  response, aboard total, immune graph, propensity draw, index onset
  day, onset eligibility and seeding spec are equal.
- 140 Batch children `SUCCEEDED`, one attempt, exit 0, array index i ↔
  seed 20200205 + i, matching the seed list in each submitted command.
- Two image identities, kept apart: `dp_contamx_canary` ran job
  definition `:2`, `sha256:7023d963…19a0` (code `8de77294`); the other
  three blocks ran `:3`/`:4`/`:5`, `sha256:56f860c8…f485` (code
  `106a3583`). Between those commits nothing under `engines/` or
  `picard_framework/` changed except `funnel_echo` in the GM design;
  image contents were not compared. The DP pair therefore differs in
  image as well as provider.

## Paired endpoints

| Replay | Endpoint | Pairs | Native median (range) | ContamX median (range) | Mean Δ [95% CI] | Δ range | − / 0 / + |
|---|---|---:|---|---|---|---|---|
| DP | recorded onsets | 20 | 8 (0–454) | 8 (0–493) | +1.70 [−2.54, +5.94] | −9 to +39 | 1 / 17 / 2 |
| DP | lab confirmations | 20 | 10.5 (0–540) | 10.5 (0–590) | +2.90 [−2.43, +8.23] | −3 to +50 | 1 / 17 / 2 |
| DP | campaign positives | 20 | 10 (0–273) | 10 (0–308) | +2.20 [−1.53, +5.93] | 0 to +35 | 0 / 18 / 2 |
| DP | infections | 20 | 31 (0–774) | 31 (0–833) | +3.45 [−5.64, +12.54] | −39 to +59 | 1 / 17 / 2 |
| DP | attack share | 20 | 0.0084 (0–0.209) | 0.0084 (0–0.224) | +0.0009 [−0.0015, +0.0034] | −0.011 to +0.016 | 1 / 17 / 2 |
| DP | dated share (onsets / confirmations) | 16 | 0.835 (0.636–1) | 0.807 (0.636–1) | −0.0083 [−0.0212, +0.0045] | −0.092 to 0 | 3 / 13 / 0 |
| DP | asymptomatic share, final | 16 | 0.217 (0–0.364) | 0.237 (0–0.364) | +0.0064 [−0.0043, +0.0170] | 0 to +0.080 | 0 / 13 / 3 |
| DP | crew share of confirmations | 16 | 0.752 (0–1) | 0.747 (0–1) | +0.0064 [−0.0042, +0.0170] | −0.010 to +0.065 | 1 / 13 / 2 |
| GM | campaign positives (of 217) | 50 | 110 (1–135) | 110.5 (1–135) | −0.48 [−1.83, +0.87] | −15 to +10 | 12 / 26 / 12 |
| GM | recorded onsets | 50 | 50.5 (1–74) | 49.5 (1–77) | −0.40 [−1.41, +0.61] | −9 to +8 | 16 / 20 / 14 |
| GM | lab confirmations | 50 | 112 (1–136) | 111 (1–136) | −0.50 [−1.92, +0.92] | −17 to +10 | 12 / 26 / 12 |
| GM | infections (of 223) | 50 | 180 (89–216) | 180 (90–215) | +0.06 [−0.71, +0.83] | −9 to +5 | 13 / 20 / 17 |
| GM | positive share | 50 | 0.507 (0.005–0.622) | 0.509 (0.005–0.622) | −0.0022 [−0.0084, +0.0040] | −0.069 to +0.046 | 12 / 26 / 12 |
| GM | asymptomatic share of positives | 50 | 0.240 (0–0.667) | 0.241 (0–0.667) | +0.0003 [−0.0076, +0.0081] | −0.062 to +0.124 | 15 / 23 / 12 |
| GM | first recorded onset day | 50 | 9 (6–19) | 9 (6–19) | −0.06 [−0.24, +0.12] | −3 to +1 | 4 / 42 / 4 |

DP first recorded onset day is identical in all 16 pairs where it is
defined. Aboard totals (3,711; 223) and specimens (3,894; 217) are
identical by design.

**DP is three pairs.** The nonzero DP differences (onsets,
confirmations) are seed 20200212 (−9, −3), 20200218 (+4, +11) and
20200223 (+39, +50: 454 → 493 onsets, 540 → 590 confirmations). The
other 17 pairs agree on onsets, confirmations, positives and infections.
Seed 20200223 carries 0.75 of Σ|Δ| for onsets and 0.78 for
confirmations. Dropping any one pair moves the onset mean Δ anywhere in
−0.26 to +2.26, so its sign rests on that one seed; the confirmation
mean stays in +0.42 to +3.21. The 20-pair mean is not a stable summary.

**GM is many small differences.** 37 of 50 pairs differ on at least one
of the four counts, in both directions; no single pair carries more than
0.12 of Σ|Δ| for positives.

## Takeoff (≥ 10 recorded onsets), paired

| Replay | Both | Native only | ContamX only | Neither | Pairs |
|---|---:|---:|---:|---:|---:|
| DP | 9 | 0 | 0 | 11 | 20 |
| GM | 48 | 0 | 0 | 2 | 50 |

Discordance: DP 0 of 9 native takeoffs lost and 0 of 11 gained; GM 0 of
48 lost and 0 of 2 gained. Zero observed flips does not show a zero flip
rate: the one-sided exact 95% upper limit on any discordance is 0.139
(DP, 20 pairs) and 0.058 (GM, 50 pairs), and the GM "gained" direction
has two pairs behind it.

## Timing (wall time only; no billing figure)

Two different measurements, not to be combined.

**Batch child run time**, `stoppedAt − startedAt`, one attempt each,
from container `RUNNING` to exit. It excludes queue time and the image
pull (both before `startedAt`) and includes everything else in the job
(interpreter start, design load, ContamX binary fetch on ContamX cells,
upload). The four parents are the ledger's original arrays, not
resubmissions.

| Block | n | Hosts | Median s | Range s |
|---|---:|---:|---:|---|
| DP native | 20 | 2 | 1,199.3 | 1,052.9–1,632.4 |
| DP ContamX (canary image) | 20 | 2 | 1,212.3 | 1,090.9–1,763.9 |
| GM native | 50 | 4 | 53.1 | 39.3–59.3 |
| GM ContamX | 50 | 4 | 53.6 | 38.7–58.4 |

Blocks ran at different times on shared hosts with other children; the
DP arms also differ in image. This is not a matched speed experiment.

**Engineering microbenchmark**, fleet-workup package 02
(`CONTAM-FLEET-WORKUP-FLEET-01`), matched outdoor-air baseline, native
prescribed vs ContamX commissioned fresh export, five measured repeats
after one warm-up, no timeout, median ms native / ContamX. Each hull ran
in its own cohort on its own host; compare within a row only.

| Hull (cohort, instance) | Cold pipeline | Whole cold process | Repeated aggregate | ContamX solve | ContamX import |
|---|---|---|---|---:|---:|
| expedition_cruise_450 (canary_run2, c7a.8xlarge) | 15.2 / 70.6 | 839.7 / 900.5 | 6.2 / 5.3 | 6.0 | 44.6 |
| classic_cruise_1900 (fleet_cohort1, c7a.4xlarge) | 37.6 / 157.8 | 864.4 / 984.3 | 27.6 / 23.5 | 11.8 | 103.1 |
| spirit_cruise_3000 (fleet_cohort7, c7a.4xlarge) | 89.4 / 316.6 | 923.1 / 1,151.6 | 74.6 / 71.7 | 25.2 | 194.5 |
| mega_cruise_5000 (fleet_cohort4, c7i.8xlarge) | 203.3 / 588.7 | 1,101.0 / 1,477.3 | 198.4 / 179.9 | 60.7 | 311.5 |

The cold pipeline excludes interpreter start-up; the whole process
includes it. The repeated aggregate reuses a built engine and recomputes
the matrix exponential each repeat. Import (decoding results and
building the Python transport model) is 5 to 9 times the solve on every
hull. The native cold pipeline's fastest repeat on Expedition (8.0 ms)
is about half its median (15.2 ms). The replay's ContamX arm used the
committed hull bundle, not the fresh export timed here, and Classic and
Spirit have no respiratory replay.

What this supports: on these four hulls a single cold ContamX transport
build costs 55 to 385 ms more than native, against per-voyage job times
of 53 s and 1,200 s whose medians differ by under 1.1% between arms.
"Use whichever is cheaper" in the source ledger had no timing evidence
behind it and is withdrawn; these tables do not settle it either.

## Receipts

- Canonical offline packet (the only archive; held by the campaign
  owner, not in this repository): `provider_packet_01.tar.gz`, 33,306
  bytes, SHA-256
  `b59451741fdd70437606809c279f0f84cb27e8b8bf7b9291fe39a3f01aa11adb`.
  Its verifier passes, and its 140 object receipts (key, bytes,
  SHA-256), 140 job rows, 560 seed-level arm values, eight endpoint
  summaries, takeoff table, four Batch medians and 32 timing medians
  equal this readout's independent recomputation.
- Fleet-workup package 02: SHA-256
  `3bc0e40f4d7a03082bbb6caf01ff76257163d7da8daee672f55a80c406f9684d`,
  4,575,643 bytes.
- Source payloads are pinned by key, byte count and SHA-256 in the
  packet. The read role cannot list S3 object versions, so no version
  id is recorded.
- Rebuild from sources (payloads are private; they hold per-host
  records and are not committed):

  ```sh
  python3 campaigns/covid/transport_fit_01/paired_readout.py build \
    --cells-dir <synced prefix> --batch-dir <describe-jobs JSON> \
    --package02 <unpacked package 02> --out <dir>
  python3 campaigns/covid/transport_fit_01/paired_readout.py verify \
    --dir <dir> --campaign campaigns/covid/transport_fit_01/campaign.json
  ```

  `--batch-dir` holds `parent_<block>.json` and `children_<block>.json`
  as returned by `aws batch describe-jobs`. `verify` uses the standard
  library only and recomputes every statistic from the base tables (21
  checks). Table digests from this rebuild:

  ```text
  0a990ce55e71776b054c1d403ef6dac01be5c83df1fde67ddd47a9f2723cd8c8  seed_endpoints.csv
  329359aec8d82a9b3f4e32055b2e60439fbbbf360c10cd286e1a1f29509a1966  source_cells.csv
  01265430f1d8f1f56cea737a50e2a33ae14e484cb18dc0ad67ab4dc25f2622d2  batch_children.csv
  628f0ee21d99017015635d9766922e1ba2e5d1d462046dea18512a9d87a0bd72  microbench.csv
  1ef8024adc2be98026d5154cd483c19568b87929d48b64d1e0aa58cdd08b1555  microbench_cohorts.csv
  dc4cf71eb67df40d1a5417cb4037745d27d10baca6d0d66d6df9686242860f25  paired_summary.json
  ```

## Not established

Equivalence of the providers; equal delivered dose; which airflow repair
changed DP takeoff; any takeoff probability for a real ship; behaviour
on Classic or Spirit voyages; cost in dollars.
