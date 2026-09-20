# NORO-DOSE-BLOCK-01
**Date:** 2026-09-19
**Commit:** 5870c74
**Pathogens:** norwalk_gi
**Status:** open

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

Pending.
