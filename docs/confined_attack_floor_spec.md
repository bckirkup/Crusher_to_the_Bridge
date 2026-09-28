# Confined-attack floor spec

**Status:** Implemented — recalibrated by `CABIN-FLOOR-03`; supersedes the
15–25% fixed band that `tools/flu_rhythm_ab_readout.py` carried as `FLOOR`
and the ledger verdicts drawn against it (`CABIN-FLOOR-01`, `CABIN-FLOOR-02`,
`FLU-DELIVERY-01`, `FLU-RHYTHM-01`).

## What the band bounds

The band bounds the **expected confined-mate secondary attack rate** — the
mean over confined slots of the per-slot conversion hazard implied by the
declared dose-response constant:

```
E[SAR] = mean over slots of ( 1 − exp(−k · D_slot) )
```

- A **slot** is a confined cabin-mate pair window: the mate was uninfected at
  the pair's first confined epoch, and the window runs while both are
  confined (the `CabinPairChallengeLedger` / stage-probe `slot_rows`
  definition used by `tools/cabin_floor_probe.py` and
  `tools/flu_rhythm_ab_probe.py`).
- `D_slot` is the slot's delivered dose over the window —
  `delivered_p_dose`, the challenge-resolved copies the engine actually
  delivered to the mate. Per-epoch exponential hazards compose exactly, so
  `1 − exp(−k·D_slot)` is the slot's conversion probability under the
  exponential dose-response model. (`sum_hazard` is not this quantity: it
  sums per-epoch probabilities and overcounts when hazard is spread over
  epochs.)
- `k` is the profile's declared `dose_response.k`.

The band does **not** bound the realized pooled attack fraction as a hard
edge. The realized fraction is a binomial draw around the expectation and is
compared n-aware (§4). The withdrawn 15–25% band conflated these: it was
drawn around the noisy n=34 point estimate (20.6%, Wilson ~9.5–38%) of
FLU-DELIVERY-01, not around any declared-constants expectation.

## Band construction

```
band = [ E[SAR](k_lo), E[SAR](k_hi) ]
```

evaluated on the confined-slot dose distribution produced under the declared
conditioning (isolated arm, explicit passenger seed pair at epoch 0,
`scenario_schedule` SOP-017 day 1 → end —
`tools/cabin_floor_probe.py:conditioned_spec`), where `[k_lo, k_hi]` is the
declared sourced interval of the arm's `dose_response.k`.

For `influenza_a`: `[2e-4, 1e-3]` per copy (Alford 1966 aerosol ID50 0.6–3
TCID50 ÷ Van Wesenbeeck 2015 ≥1e3 copies/TCID50; profile `dose_response.notes`,
FLU-DELIVERY-01), shipped midpoint `k = 6e-4`.

Because `1 − exp(−k·D)` is monotone in `k`, a run at declared `k` lands inside
the band by construction — that is the internal-consistency gate, and it is
the only guarantee the band makes. The band is derived from declared
constants and the cabin-mate geometry (which produces `D_slot`); it is not
fitted to measured attack rates and never uses an observed attack as an
input.

## Recomputed band (influenza_a)

Measured on the FLU-RHYTHM-01 cells (declared conditioning, n=100
cells/class/arm; dose distributions measured at `07d9856c`, recomputation at
`27efdbd4`):

| class | arm | slots | band k∈[2e-4,1e-3] | E[SAR] at k=6e-4 | observed attack [Wilson] |
|---|---|---|---|---|---|
| expedition_cruise_450 | off | 368 | [4.0%, 13.0%] | 9.4% | 12.0% [9.0–15.7] |
| expedition_cruise_450 | on | 381 | [3.9%, 13.1%] | 9.4% | 11.3% [8.5–14.9] |
| classic_cruise_1900 | off | 1575 | [3.9%, 12.9%] | 9.2% | 12.5% [11.0–14.2] |
| classic_cruise_1900 | on | 1664 | [4.5%, 14.7%] | 10.6% | 13.6% [12.1–15.4] |
| spirit_cruise_3000 | off | 2529 | [4.6%, 14.7%] | 10.6% | 14.6% [13.3–16.0] |
| spirit_cruise_3000 | on | 2783 | [4.8%, 15.7%] | 11.3% | 14.3% [13.1–15.7] |
| mega_cruise_5000 | off | 4575 | [3.1%, 10.4%] | 7.4% | 10.5% [9.7–11.4] |
| mega_cruise_5000 | on | 5603 | [4.1%, 13.5%] | 9.7% | 12.8% [11.9–13.7] |

Pooled off-arm over all four classes (n=9047): **[3.7%, 12.1%]**, declared-k
expectation 8.7%.

Per-class shape differences are geometry, not constants: mega_cruise_5000's
band sits lowest because its cabins yield the lowest median delivered dose
(6.6 vs 17.8 copies on spirit, off arm).

## Comparison rule

A pooled observed attack is consistent with the band when its Wilson
interval overlaps `[E(k_lo), E(k_hi)]`. Treating a band edge as a hard
threshold on a small-n point estimate is the defect this spec removes — at
n=34 a 13.6% expectation reads 20.6% observed inside its own scatter.

Two residual directions are expected and are not misses:

- **Observed modestly above the declared-k expectation** (~2–4 pp on the
  measured cells). `delivered_p_dose` stops accruing for a mate once it
  converts, so realized doses truncate at conversion and the expectation
  under-reads the counterfactual full-window hazard. Read systematic
  overshoot as that truncation, not as a delivery defect.
- **A slot population dominated by near-zero doses.** ~10–19% of slots carry
  zero delivered dose and the median SAR is ~0.5–1%; the mean is carried by
  long-overlap shedding windows. The band is a mean-over-slots statement;
  per-slot SAR is heavy-tailed by construction.

## Relation to the scored anchor

The literature anchor for confined flu SAR is audit row F1 — Lau 2012
PCR-confirmed household SIR spread **[0.03, 0.38]**
(`docs/literature/non_scored_arms_audit.md`). That is the scored surface:
the arm is compared to literature there. The floor band here is a separate,
internal-consistency check — it verifies that realized confined attack
matches what the declared constants produce on the cabin-mate geometry, and
its whole span sits inside the F1 anchor interval.

## Withdrawn provenance

The 15–25% figure traces to the norovirus shipboard cabinmate pair — Wikswo
2011 (15.4%) and Chimonas 2008 (24.1%) — transplanted into the generic
CABIN-FLOOR check and then onto the flu arm, where CABIN-FLOOR-01's table
documented it as "Lau 3–38%". Lau's interval is 3–38%; the 15–25% numbers
are not derivable from it, and no recomputation from the declared flu `k`
produces them either (the k_hi endpoint gives at most 15.7% pooled). For
norovirus the pair remains that pathogen's own sourced floor; for influenza
the band is withdrawn and replaced by this derivation.
