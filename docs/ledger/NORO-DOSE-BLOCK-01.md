# NORO-DOSE-BLOCK-01
**Date:** 2026-09-19
**Commit:** 5870c74
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 5870c74

`NORO-EMESIS-SIZE-01` withdrew, as hull-level statements, every norovirus dose
magnitude and hazard bound that rests on the 8105/8106 pair alone: over seeds
8000–8019 the credited scaled dose spans 4.42e-45 to 1.81e4 GEC, and the pair
sits two or more decades below the tail. What it did **not** do is replace the
withdrawn quantities — `NORO-DOSE-01`'s route attribution (fomite 93.5% of
credited dose), its 2.17 log10 surface→hand and 1.93 log10 hand→mouth terms,
and its 0.101 GEC voyage total are still pair figures. This entry restates each
of them as a distribution over a seed block.

`NORO-REINFECT-IMPACT-01` established the second reason to run: `REINFECT-01`
(merged at `d62f10d`) shifts the RNG stream in 10 of the 20 seeds, so the
`e83aa06` dumps are pinned to pre-repair `main` and cannot be compared
bit-for-bit against anything measured now. This block is therefore measured on
post-repair `main` and becomes the current-`main` baseline for the hull.

## Question

For `classic_cruise_1900` at its declared complement, over a seed block rather
than a pair:

1. **Route attribution.** What is the distribution of each pathway's share of
   credited norovirus dose, and is fomite dominance a hull property or a
   pair property?
2. **Transfer terms.** What are the surface→hand and hand→mouth log10 losses
   per voyage, and how wide is their spread?
3. **Magnitude.** What is the distribution of credited scaled dose and of
   dose concentration (hosts holding 90% of it)?
4. **Pair position.** Measured at one commit, where do 8105 and 8106 sit
   inside that block?

## Instrument

`tools/noro_diag/per_host_dose_challenge.py`, unmodified, with no `--alpha`, so
no override is written and the run differs from a shipped run only by the
read-only wrappers. Every quantity above is already a witness the instrument
records — `reconciliation.pathway_dose_gec` / `pathway_calls` for route
attribution, and `fomite_witness` (`surface_mass_offered_gec`,
`mass_requested_gec`, `mass_delivered_to_hands_gec`, `hand_load_seen_gec`,
`hand_to_mouth_dose_gec`) for the transfer chain — so this entry adds no
instrumentation and no engine path.

Nothing here touches `dose_response.alpha` or `.beta`, so
`RNG-FRAILTY-STREAM-01` does not apply *within* this block; it does apply
between this block and the `e83aa06` block, which is the reason for the
re-baseline and is treated as expected, not as a finding.

## Cells, frozen before any cell runs

| Hull | Seeds | Agents | Epochs | Cells |
| --- | --- | --- | --- | --- |
| `classic_cruise_1900` | 8000–8019 | 1,910 | 288 | 20 |
| `classic_cruise_1900` | 8105, 8106 | 1,910 | 288 | 2 |

Shipped default `active_profiles` bundle at its declared complement, no
override, measured at post-repair `main`. The pair is included so that
"the pair is a low-tail pair" becomes a within-commit statement rather than a
comparison across two engines. Output:
`docs/norovirus/noro_dose_block_01/classic_cruise_1900/`.

## Criteria, declared before any cell runs

**Admissibility.** A cell is *void* if the run raises or records zero
`norwalk_gi` accumulate calls. Void cells are reported and excluded, never
replaced by another seed. More than 4 void of 22 makes the study **NO-GO** and
it reports the voiding cause instead of a distribution.

**Reconciliation gate.** Per cell, `sum_credited_scaled_gec`,
`sum_dose_read_at_challenge_gec` and `sum_effective_dose_evaluated_gec` must
agree to a relative difference below 1e-9, as they did in every cell of
`NORO-EMESIS-SIZE-01`. A cell that fails this gate is reported as a defect
before any distribution is quoted.

**Route attribution.** Per cell, each pathway's `pathway_dose_gec` as a share
of the sum over pathways, reported as median and full range across admissible
cells. `NORO-DOSE-01`'s 93.5% fomite share is *confirmed as a hull property*
only if the block's median fomite share is within 10 percentage points of it
**and** the interquartile range is narrower than 20 points; otherwise the
figure is restated as a distribution and the pair figure stays withdrawn.
Cells whose total credited dose is below 1e-6 GEC are reported separately in
the share table: a share of a vanishing total is arithmetic, not attribution.

**Transfer terms.** Per cell, surface→hand as
`log10(surface_mass_offered_gec / mass_delivered_to_hands_gec)` and hand→mouth
as `log10(hand_load_seen_gec / hand_to_mouth_dose_gec)`, each reported as
median and full range. `NORO-DOSE-01`'s 2.17 and 1.93 are *confirmed* if each
block median is within 0.5 log10 of the pair value; otherwise they are
restated. Both are chain terms measured at the same witnesses as that entry —
no term is combined with the emesis route's bolus→hands loss, which
`NORO-EMESIS-SIZE-01` showed sits at the same stage as surface→hand.

**Magnitude and concentration.** Median and full range of
`sum_credited_scaled_gec`, and the distribution of `concentration.hosts_for_90pct`.
The declared reading is that a *hull-level* dose magnitude may be quoted only
as this distribution; no single value replaces the withdrawn 0.101 GEC.

**Pair position.** 8105 and 8106 are located as percentiles of the 20-seed
block on credited dose and on Σ evaluated hazard. If either sits above the
block's 25th percentile on both, "the pair is a low-tail pair" is **withdrawn**
in turn and the discrepancy is reported before anything else.

**Repair stability.** Block totals at this commit are compared to the
`e83aa06` block as an *unpaired* check only: per-seed equality is not expected
and its absence is not a finding. A block-level move in summed hazard of more
than 10× against `NORO-REINFECT-IMPACT-01`'s predicted 4.2e-6 effect is
reported immediately as a possible second consequence of the repair.

**Report immediately if:** any cell fails the reconciliation gate; the pair
position criterion fails; summed hazard moves more than 10× across the repair;
or any cell raises.

## Non-goals

No constant, profile, platform, engine path, test or instrument is changed. No
`--alpha` arm — α and β stay closed, and `NORO-SUSCEPT-03`'s exclusion of the
sourced α interval as an *explanation* is not revisited. `NORO-EMESIS-SHARE-01`,
`NORO-PATCH-SATURATION-01`, `NORO-HAND-STATIONARY-01`,
`NORO-SURFACE-CONSUME-01`, `NORO-CARRIER-REDEPOSIT-01` and
`NORO-TRANSFER-PRODUCT-01` remain filed and unstarted; this entry does not
proceed into any of them.

## Readout

Measured at `5870c74`, 22/22 cells admissible, 0 void. Cells in
`docs/norovirus/noro_dose_block_01/classic_cruise_1900/`; aggregation by
`tools/noro_diag/dose_block_readout.py` into
`docs/norovirus/noro_dose_block_01/dose_block_cells.json`.

### 0. Reconciliation gate — FAILED at the declared 1e-9, cause identified

The gate frozen above **fails**: 9 of 22 cells exceed 1e-9 relative, worst
8.400e-3 (seed 8019). It is reported here before any distribution is quoted,
as the criterion requires.

The failure is one-sided and localised to one of the three sums.
`sum_dose_read_at_challenge_gec` equals `sum_credited_scaled_gec` **exactly**
in all 22 cells, so nothing is lost in the chain up to the challenge;
`sum_effective_dose_evaluated_gec` is the sum that is short, and it is short
in every failing cell and never long (`any_negative_gap` false). That is the
signature of `REINFECT-01`, not of a conservation defect: the challenge
resolver returns at `protection >= 1.0` before the dose is evaluated, so a
fully protected host's credited dose is read and then never evaluated. The
pre-repair `e83aa06` block reconciles at exactly 0.000e+00 in all 20 cells,
which dates the change to the repair.

| | value |
| --- | --- |
| cells over 1e-9 | 9 of 22 (8000, 8002, 8005, 8007, 8009, 8011, 8014, 8019, 8105) |
| worst per-cell fraction | 8.400e-3 (8019) |
| block credited scaled | 29,826.2629 GEC |
| block evaluated | 29,826.2598 GEC |
| block unevaluated | 3.117e-3 GEC, **1.045e-7** of credited |

**Reading: the gate's 1e-9 threshold is the wrong gate on post-repair `main`,
not a defect it caught.** A threshold written for an engine in which every
credited dose was evaluated cannot survive an engine that deliberately skips
evaluation for immune hosts. The quantity that matters — how much dose the
skip removes — is 1.0e-7 of the block, four orders below the smallest effect
this study reports, so no distribution below is affected. A successor study
should declare the gate as `sum_dose_read_at_challenge == sum_credited` exact,
plus a bound on the credited-minus-evaluated gap, and should treat a
*negative* gap (evaluated exceeding credited) as the real defect signature.

### 4. Pair position — criterion FAILED, "low-tail pair" withdrawn

Measured at one commit, the pair is an **ordinary** voyage, not a low-tail one:

| Seed | Credited scaled (GEC) | Dose percentile in block | Σ hazard | Hazard percentile |
| --- | --- | --- | --- | --- |
| 8105 | 0.0844 | 60 | 3.104e-4 | 60 |
| 8106 | 2.635e-3 | 25 | 1.080e-5 | 35 |

8105 is above the declared 25th-percentile threshold on both axes, so by the
criterion frozen above, **`NORO-EMESIS-SIZE-01`'s reading that 8105/8106 is a
low-tail pair is withdrawn** and is replaced by the statement it should have
made: the block is extraordinarily skewed, not the pair unusually low. Block
credited scaled dose has median 0.0584 GEC against a mean of 1,491 GEC and a
maximum of 1.81e4 GEC — five orders between the middle and the mean — and
8105's 0.084 GEC is 1.4× the median voyage. The earlier reading compared the
pair to the block *maximum* and called the difference tail position; the
correct statement is that a median classic voyage credits a tenth of a GEC and
a small minority of voyages credit four to five orders more.

This matters beyond bookkeeping: `NORO-DOSE-01` was not run on an unluckily
quiet voyage. Its ~0.1 GEC total is what a typical `classic_cruise_1900`
voyage delivers, and the hull's expected secondaries come almost entirely from
the few voyages that are nothing like it.

### 1. Route attribution — fomite dominance holds, the point figure does not

Dose-weighted over the block (sum of `pathway_dose_gec` across the 20 seeds,
97,022 GEC): fomite 97.73%, direct contact 1.56%, emesis aerosol 0.67%, HVAC
airborne 0.039%, food 0.006%, droplet 0.000% (norovirus has no continuous
droplet emission by construction).

Per voyage, the share distribution is wide:

| Pathway | min | p25 | median | p75 | max |
| --- | --- | --- | --- | --- | --- |
| fomite | 3.4e-79 | 0.666 | 0.891 | 0.970 | 0.9998 |
| direct_contact | 6.4e-8 | 0.0086 | 0.092 | 0.334 | 1.000 |
| emesis_aerosol | 0 | 0 | 0 | 6.9e-5 | 0.116 |
| food | 0 | 0 | 1.9e-4 | 9.0e-4 | 0.033 |
| hvac_airborne | 0 | 0 | 0 | 6.8e-7 | 5.4e-3 |

Median fomite share 0.891 is within the declared 10-point tolerance of
`NORO-DOSE-01`'s 0.935, but the interquartile range is 0.304, well over the
declared 0.20 ceiling, so the criterion's *confirmation* clause is not met.
Four voyages (8007, 8010, 8015, 8017) are direct-contact dominated; all four
are in the bottom quartile of credited dose, so the voyages that carry the
hull's dose are fomite voyages and the voyages that do not are the ones where
attribution moves. **Reading: fomite dominance is a hull property; 93.5% is
not a hull constant, and the honest statement is a median of 0.89 with a
0.67–0.97 interquartile range, or 97.7% dose-weighted.**

### 2. Transfer terms — hand→mouth confirmed, surface→hand restated

| Term | min | median | max | `NORO-DOSE-01` pair | Verdict |
| --- | --- | --- | --- | --- | --- |
| surface→hand log10 loss | 7.1e-7 | 0.840 | 2.673 | 2.17 | not confirmed |
| hand→mouth log10 loss | 1.595 | 1.960 | 2.576 | 1.93 | confirmed |

Hand→mouth is a narrow hull constant: the whole block lies inside one log10,
and the median is 0.03 log10 from the pair value.

Surface→hand is not. The block median loses 0.84 log10 where the pair lost
2.17, and the spread is 2.7 log10 wide. This is *not* an effect of the
reinfection repair: the same statistic computed on the pre-repair `e83aa06`
block gives median 0.925, so the gap is the pair's, not the engine's. The pair
happened to sit 1.3 log10 above the typical surface→hand loss, which means
`NORO-DOSE-01`'s "4.1 log10 across the fomite chain" overstated the hull's
attenuation by more than a decade. **The combined chain loss on this hull is
about 2.8 log10 (median 0.84 + 1.96), not 4.1.**

### 3. Magnitude

| Quantity | min | p25 | median | p75 | max |
| --- | --- | --- | --- | --- | --- |
| credited scaled dose (GEC) | 9.56e-7 | 4.09e-3 | 0.0584 | 328.1 | 1.806e4 |
| Σ evaluated hazard | 2.13e-12 | 5.26e-6 | 1.34e-4 | 3.75e-3 | 1.691 |
| hosts holding 90% of dose | 1 | 1 | 7 | 89.5 | 218 |

Block totals: 29,830 GEC credited, Σ hazard 2.9450, 87 imports, 3 secondaries
(8016: 2, 8018: 1). Dose concentration is itself a function of voyage size: a
median voyage's dose sits on 7 hosts, while the two secondary-bearing voyages
spread it over dozens. No single value replaces the withdrawn 0.101 GEC; the
hull-level statement is this distribution.

### Repair stability

Unpaired block comparison across `REINFECT-01`, as declared:

| | pre-repair `e83aa06` | post-repair `5870c74` |
| --- | --- | --- |
| Σ hazard over 20 seeds | 3.0046 | 2.9450 |
| credited scaled, block sum (GEC) | 3.462e4 | 2.983e4 |
| credited scaled, median (GEC) | 0.0576 | 0.0584 |
| surface→hand log10, median | 0.925 | 0.840 |
| hand→mouth log10, median | 2.001 | 1.960 |
| secondaries | 3 (8016: 2, 8018: 1) | 3 (8016: 2, 8018: 1) |

The block moved 2.0% in summed hazard, far inside the declared 10× report
trigger, and the same two seeds produced the same three secondaries. That is
consistent with `NORO-REINFECT-IMPACT-01`'s prediction that the repair removes
4.2e-6 of the block's hazard in expectation and otherwise only shifts draws.
Per-seed values do differ (block sum moves 14% while the median moves 1.4%,
because the sum is set by a few heavy voyages whose streams moved), which is
the expected `RNG-FRAILTY-STREAM-01` behaviour and is not a finding.

## Recommendation

**Adopt this block as the current-`main` norovirus baseline for
`classic_cruise_1900`, and quote the hull only as a distribution.** Concretely:
fomite 97.7% dose-weighted (median voyage share 0.89, IQR 0.67–0.97);
hand→mouth 1.96 log10 (a genuine constant); surface→hand 0.84 log10 median with
a 2.7-log10 spread (not a constant, and not 2.17); median voyage 0.058 GEC with
a mean four orders above it.

Two consequences worth acting on, in this order:

1. **The fomite chain loses ~2.8 log10, not 4.1.** Every argument that treated
   the pair's 4.1 as the hull's attenuation — including the intuition that made
   the α interval look irrelevant — was working with a figure 1.3 log10 too
   pessimistic. This does not re-open α (`NORO-SUSCEPT-03`'s exclusion is an
   argument about a *shortfall of orders of magnitude*, and 1.3 log10 does not
   close it), but `NORO-TRANSFER-PRODUCT-01` — comparing the hull's measured
   transfer product against the literature's — is now the highest-value
   follow-on, because the term to compare has changed by more than a decade.
2. **Surface→hand is the variable term, and its spread is unexplained.** Its
   2.7-log10 range across seeds, against hand→mouth's 1.0, points at the same
   hand reservoir `NORO-EXP-FOMITE-RECONCILE-01` found spiking and crashing, so
   `NORO-HAND-STATIONARY-01` is the mechanism study behind it.

3. **Retire the 1e-9 three-sum reconciliation gate.** It now fails on a
   correct engine (§0) and would fail in every successor study that reuses it.
   Replace it with the exact read-equals-credited identity plus a bound on the
   credited-minus-evaluated gap, and keep a negative gap as the defect
   signature. This is a one-line criterion change in the next ledger entry, not
   a study.

Not started here, and none should start automatically: `NORO-TRANSFER-PRODUCT-01`,
`NORO-HAND-STATIONARY-01`, `NORO-EMESIS-SHARE-01`, `NORO-PATCH-SATURATION-01`,
`NORO-SURFACE-CONSUME-01`, `NORO-CARRIER-REDEPOSIT-01`.
