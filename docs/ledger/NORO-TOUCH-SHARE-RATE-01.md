# NORO-TOUCH-SHARE-RATE-01
**Date:** 2026-09-25
**Commit:** 89809781
**Pathogens:** norwalk_gi
**Status:** declared

`NORO-COINCIDENCE-CELL-01` (measured `995746e4`) fixed the host-coverage
deficiency — 18/20 seeds carry ≥1 fomite-credited host at the frozen cell —
and the frozen coincidence rule still read **indeterminate**: the declared
touch-share table expressed (any A-vs-D divergence) on only ~44% of viable
seeds (8/18), short of the rule's joint bar (median Jaccard `< 0.90` and
`≥ 15/20` expressing seeds). The remaining unknown is the **expression rate
itself**: what fraction of seeds does the declared table move at all, and
with what Jaccard/gain distribution? At n = 20 the rule samples that rate;
this entry measures it at n = 100 on AWS Batch.

The frozen coincidence rule is not changed and is not re-scored here — the
n = 20 verdict is already recorded in `NORO-COINCIDENCE-CELL-01` §4. This
entry measures the quantity that determines whether an n = 20 canary of
this design can ever resolve the rule.

## 0. Settled inputs (quoted, not re-derived)

- **Frozen cell** (`NORO-COINCIDENCE-CELL-01` §2): `spirit_cruise_3000` ×
  `--bundle norwalk_only` × 168 epochs, chosen so most seeds carry ≥1
  fomite-credited host.
- **Frozen rule** (`NORO-TOUCH-SHARE-01` §4): over 20 seeds, changes
  coincidence iff median credited-host Jaccard `< 0.90` and `≥ 15` seeds
  show `public.button_or_dispenser` share gain `> 0.10`; inert iff
  `H_A == H_D` all seeds; else indeterminate.
- **n = 20 readout** (`NORO-COINCIDENCE-CELL-01` §4, measured `995746e4`):
  18/20 viable; 12/20 aligned; median Jaccard 1.000; focus-gain `> 0.10`
  on 12/20 (gains 0.386–0.868); diverged on 8/20; DISAGG-01 identity
  holds; cap shares ≤ 0.52%.
- **Mechanism** (`NORO-GATE-FLOOR-02`, merged): every A-vs-D divergence is
  the declared table's own reallocation tipping a pickup across the 1-GEC
  gate; deposits draw no RNG (inferred). Gate repairs are exhausted.
- **Operator decisions:** declared table stays pathogen-agnostic; pooled
  stays default; no constant changes; `HIGH_TOUCH_AREA_M2` untouched;
  `per_surface`/`declared` stay non-default. No dose or attack-rate
  selection anywhere in this entry — absolute dose figures are withdrawn.

## 1. Design (declared before submit)

**Cell:** the frozen `spirit_cruise_3000` × `norwalk_only` × 168 epochs,
unchanged.

**Seeds:** 8000–8099 (n = 100). Seeds 8000–8019 reuse the committed dumps
from `NORO-COINCIDENCE-CELL-01` (measured `995746e4`, this entry's parent
main — the engine between them is byte-identical, so the same seed is the
same run). The AWS block covers only the 80 new seeds, 8020–8099.

**Arms:** the frozen triad per seed — `per_surface_areal`,
`per_surface_declared` (table
`data/config/fomite_touch_share_declared.json`), and `pooled` for the
DISAGG-01 identity re-check.

**Submission:** AWS Batch EC2 Spot array on `picard-campaign-queue`,
240 children = 3 arms × 80 seeds, worker
`deploy/aws/dose_challenge_entrypoint.py` (one cell per child, dump
uploaded to `s3://<BUCKET>/campaign/touch_share_rate_01/arm_<tag>/`),
image `picard-boundary-analysis:dose-challenge-v1` (design image +
`tools/noro_diag/`), 1 vCPU / 4096 MB per child, job def
`picard-dose-challenge`. Cost ≈ 26 CPU-h at the measured ~6.4 CPU-min/run;
wall ≈ 30–60 min at the queue's Spot ceiling.

**Stop conditions (frozen).**

| condition | action |
|---|---|
| canary child (3-cell smoke array) fails or writes no dump | stop, fix, report |
| DISAGG-01 identity fails on any seed (areal vs pooled, rel ≤ 1e-9, event counts exact) | stop, report — implementation defect |
| any declared class > 10% capped calls in arm D | report immediately |
| Spot/OOM failure rate makes 80 seeds unreachable in the session | sync what completed, report the partial rate with its CI |

## 2. Readout (frozen)

Over the pooled 100-seed set (20 committed + 80 new), all paired/relative:

1. **Expression rate**: fraction of seeds with `H_A ≠ H_D`
   (credited-set Jaccard < 1), with the Wilson 95% interval; and the same
   restricted to viable seeds (≥1 fomite-credited host in arm A).
2. **Distribution**: per-seed Jaccard, focus-share gain, deposit-alignment
   flag; medians and the viable-seed medians.
3. **Firing probability**: Pr[a fresh 20-seed canary at this cell fires
   the frozen rule] under the measured expression/gain rates — the number
   that decides whether any n = 20 canary of this design can resolve the
   rule.
4. Per-class `hosts_credited` deltas D − A (zone-class totals).
5. Event-alignment fraction (§4.2 witness, treatment effect included) and
   cap shares (any class > 10% → stop-report).
6. DISAGG-01 identity on all 80 new seeds (areal vs pooled).

## 3. Measured

<!-- measured -->
