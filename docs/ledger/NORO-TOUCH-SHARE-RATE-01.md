# NORO-TOUCH-SHARE-RATE-01
**Date:** 2026-09-25
**Commit:** 89809781
**Pathogens:** norwalk_gi
**Status:** measured

**Measured at:** 411b0dbe

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

**Block.** AWS Batch array `fc21e752-3a4c-4b57-8dac-3c365cc99c19`
(240 children = 3 arms × seeds 8020–8099), submitted 2026-09-25 ~22:26
UTC on `picard-campaign-queue`; **all 240 children SUCCEEDED, zero Spot
or OOM failures**, ~18 min wall. Measured ~237 s/run on 1 vCPU
(~15 CPU-h total). 240 dumps synced to
`docs/norovirus/touch_share_rate_01/arm_<tag>/`; readouts in
`readouts/`. The n = 100 set pools these 80 seeds with the committed
8000–8019 dumps from `NORO-COINCIDENCE-CELL-01`.

### 3.1 Stop conditions — all clear

| condition | result |
|---|---|
| canary child fails / no dump | 3-cell canary `7019e447` passed: all SUCCEEDED, dumps valid (arm witnesses `per_surface`/`declared`, 493 hosts, 226 s) |
| DISAGG-01 fails any seed | **holds on all 80 new seeds** — worst rel dev 1.8e-14 (`hosts[].credited_scaled_gec`, seed 8035); every event count exact |
| any declared class > 10% capped | none — worst `capped_share_declared` 0.0286 (`crew_mess.*`, seed 8086) |
| Spot/OOM makes seeds unreachable | 0 failures; full 80-seed block landed |

### 3.2 Expression rate (the measured quantity)

`H_A ≠ H_D` ⇔ credited-host Jaccard < 1:

| population | expressed | rate | Wilson 95% |
|---|---|---|---|
| all 100 seeds | 49 | **0.490** | [0.394, 0.587] |
| viable (areal arm ≥1 fomite host; 8 extinct seeds excluded: 8001, 8018, 8021, 8054, 8059, 8079, 8085, 8094) | 49/92 | **0.533** | [0.431, 0.631] |

The declared table is bit-inert on ~half of seeds — the n = 20 estimate
(~44% of viable) sits inside the interval.

### 3.3 Distributions

| statistic | all 100 | viable 92 |
|---|---|---|
| median Jaccard | 1.0000 | 0.9908 (min 0.1642) |
| Jaccard < 0.90 | 37/100 | 37/92 |
| median focus-share gain | 0.392 | 0.394 |
| gain > 0.10 | 73/100 | 73/92 |
| deposit events aligned | 46/100 | 38/92 |

The two rule clauses pull against each other: the gain bar (needs
≥15/20) is met by a 73% base rate, but the median-Jaccard bar needs
≥11/20 seeds with J < 0.90 against a 37% base rate — and both must land
on the same draw.

### 3.4 Firing probability of a fresh n = 20 canary

Bootstrap (B = 100 000, sampling 20 seeds with replacement from the
measured 100-seed joint (Jaccard, gain) distribution):

- **Pr[fires] ≈ 0.11** over all seeds (fresh canary includes extinct
  draws, as the frozen rule scores all 20 seeds).
- **Pr[fires] ≈ 0.19** if the canary were scored on viable seeds only.

At n = 20 the frozen rule resolves only ~1 draw in 9; even a
viable-seed-restricted score resolves ~1 in 5. The n = 20 indeterminate
is therefore structural, not cell-specific: no fresh 20-seed canary of
this design at this cell can be expected to resolve the rule.

### 3.5 Per-class `hosts_credited` deltas D − A (100-seed totals)

| zone_class.item_class | Δ hosts |
|---|---|
| public.button_or_dispenser | −2896 |
| public.door_lever | −1813 |
| public.grab_rail_m | −1813 |
| dining.utensil | +1728 |
| dining.button_or_dispenser / door_lever / tap_set | +1635 each |
| crew_mess.button_or_dispenser / door_lever / tap_set / utensil | +512 each |
| galley.button_or_dispenser / door_lever / tap_set / utensil / work_plane | +412 each |
| cabin.* (10 classes) | +8 each |

Same reallocation direction as the n = 20 block (public → dining /
galley / crew_mess), consistent in sign and rough magnitude per seed.
Cap shares all ≤ 0.0286 — no class near 10%.

### 3.6 DISAGG-01 identity

Holds on all 80 new seeds (areal vs pooled): worst relative deviation
1.8e-14 on `hosts[].credited_scaled_gec`; every event count (`deliver`,
`hand_to_mouth`, `surface_deposit`, `transmission.secondaries`,
`attack_rate`) exactly equal. Combined with the 20 committed seeds the
identity now holds on **100/100 seeds** at this cell. Runtime
per_surface/pooled median 1.005 (below the 1.5–4× envelope).

### 3.7 Conclusion

Measured, not hypothesised: the declared table expresses on
**49/100 seeds (0.490, Wilson [0.394, 0.587])**. A fresh n = 20 canary
at this cell fires the frozen rule with probability ≈ 0.11 — the
indeterminate verdict of `NORO-COINCIDENCE-CELL-01` cannot be resolved
by re-running 20-seed canaries. Resolving the coincidence question
needs either a rule re-specified on an n ≳ 100 block (out of scope —
the rule is frozen) or a different measured quantity (e.g.
route-attributed infections rather than credited-host coincidence).
The declared table itself behaves as designed: bit-inert where no
pickup sits near the gate, hard divergence (J down to 0.164) where one
does, with secondaries within ±1 of the areal arm on every seed.
