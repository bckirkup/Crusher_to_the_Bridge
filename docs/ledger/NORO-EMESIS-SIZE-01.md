# NORO-EMESIS-SIZE-01
**Date:** 2026-09-19
**Commit:** a44d4c4
**Pathogens:** norwalk_gi
**Status:** open

`NORO-DOSE-01` established the shape of the classic voyage — Σ evaluated hazard
3.81e-4, P(0 secondaries) = 0.9996, fomite carrying 93.5% of credited dose, and
4.1 log10 lost across surface→hand and hand→mouth — from two seeds. One of
those two seeds carried an emesis event and one did not, which is exactly the
resolution at which the emesis mechanism cannot be sized: a single event moved
the voyage's credited dose by a factor of 37 (0.100952 GEC against 0.002713
GEC), and with n = 1 that is an anecdote.

`NORO-EMESIS-CANARY-01` then established that `expedition_cruise_450` cannot
carry this measurement (one import per voyage, never symptomatic), and
`NORO-EXP-FOMITE-RECONCILE-01` established that this is hull size rather than a
defect. This entry is therefore the classic-only replicated sizing those two
entries left as the next study, and it changes no constant, profile, or engine
path.

## Question

How large is the emesis mechanism's contribution to norovirus dose on
`classic_cruise_1900`, and how variable is it between voyages?

Specifically, across replicate voyages that differ only by seed:

1. **Incidence.** In what fraction of voyages does at least one emesis event
   occur, and how many events occur when they do?
2. **Size.** How much mass does an event file to its patch, how much of that
   mass is picked up as dose, and what is the attenuation between the two?
3. **Share.** What fraction of the voyage's credited dose arrives through the
   emesis patch path rather than through routine sanitary shedding?
4. **Consequence.** Does the emesis contribution move Σ evaluated hazard far
   enough to make a secondary infection likely in any voyage, or is the zero
   secondary count of `NORO-SUSCEPT-03` robust across 20 replicates?

## Instrument

`tools/noro_diag/per_host_dose_challenge.py`, unmodified, with no `--alpha`.
Its exact classic replay of `NORO-DOSE-01` was validated by
`NORO-EMESIS-CANARY-01`, which makes it the control instrument for this hull;
modifying it would void that check. Without `--alpha` the run carries no
override at all, so an arm differs from a shipped run only by the read-only
wrappers. `RNG-FRAILTY-STREAM-01` does not apply: nothing here touches
`dose_response.alpha` or `.beta`, so every cell is comparable at fixed seed.

The witnesses this entry reads out per cell are the ones the instrument already
records: `emesis_witness` (`schedule_draws`, `scheduled_episodes`,
`emesis_events`, `emitting_hosts`, `patch_mass_gec`, `patch_pickup_calls`,
`patch_pickups`, `patch_pickup_dose_gec`, and the phase counters), the
reconciliation chain from accumulated dose to summed evaluated hazard, the
dose-concentration curve, and the run's infection tally.

## Cells, frozen before any cell runs

| Hull | Seeds | Agents | Epochs | Cells |
| --- | --- | --- | --- | --- |
| `classic_cruise_1900` | 8000–8019 | 1,910 | 288 | 20 |

Shipped default `active_profiles` bundle at its declared complement, no
override. Output goes to a hull-specific directory,
`docs/norovirus/noro_emesis_size_01/classic_cruise_1900/`, because this
instrument family names dumps by seed alone and two hulls sharing one directory
overwrite each other — the defect that invalidated the first attempt at this
study.

Two cores, two cells at a time, ~13–25 min per cell: 2–4 h of wall clock. The
20 seeds are a contiguous block declared here, not chosen after inspection.

## Criteria, declared before any cell runs

**Admissibility.** A cell is *void* if the run raises, or if it records zero
`norwalk_gi` accumulate calls (no dose path exists to size). A void cell is
reported as void and excluded from the summary statistics; it is never replaced
by another seed. If more than 4 of 20 cells are void the study is **NO-GO** and
reports the voiding cause instead of a size.

**Incidence.** Reported as the count of voyages with `emesis_events` ≥ 1 out of
the admissible cells, with the per-voyage event count distribution. No
threshold: this is the quantity being measured.

**Size.** Reported as the median and full range across admissible cells of
`patch_mass_gec`, `patch_pickup_dose_gec`, and their ratio. The ratio is the
emesis route's own attenuation and is the number this study exists to produce.
It is reported as a log10 loss alongside `NORO-DOSE-01`'s 2.17 log10 at
surface→hand and 1.93 log10 at hand→mouth, and is **not** combined with them
into a single chain figure unless the instrument shows the paths are disjoint.

**Share.** `patch_pickup_dose_gec` against the voyage's total credited scaled
dose. Because pickup dose is measured at delivery and credited dose after route
efficiency and susceptibility scaling, the ratio is reported as an upper bound
on the emesis share, not as an equality, unless the two are measured on the
same side of the scaling.

**Consequence.** Σ evaluated hazard per cell. A voyage is *likely to produce a
secondary* at Σ hazard ≥ 0.693 (P(≥1) ≥ 0.5) and *plausible* at ≥ 0.105
(P(≥1) ≥ 0.1). The count of cells over each threshold is the readout. If no
admissible cell exceeds 0.105, `NORO-SUSCEPT-03`'s zero-secondary result is
**confirmed at n = 20** and the shortfall is a property of the chain, not of
the 14 voyages it was measured on.

**Emesis attribution.** The difference between voyages with and without an
emesis event is reported as a between-group comparison of credited dose and Σ
hazard, explicitly labelled as *associational across seeds*, not as a paired
contrast: seeds differ in every draw, not only in whether a host vomited. A
paired emesis-on/emesis-off contrast at fixed seed would require suppressing
the mechanism, which is a configuration change and is out of scope here.

**Void rule for the study.** If the admissible cells show fewer than 3 voyages
with an emesis event, the mechanism is too rare at this hull and complement to
size at n = 20; the study reports the incidence bound it can support and
declares what n would be needed, rather than quoting a median over 1–2 events.

## Non-goals

No constant, profile, platform, or engine path is changed. No `--alpha` arm.
The truncated carrier mass (`NORO-CARRIER-REDEPOSIT-01`), the fomite transfer
product against literature (`NORO-TRANSFER-PRODUCT-01`), the hand reservoir's
stationary initialisation (`NORO-HAND-STATIONARY-01`) and the
`_consume_surface_mass` ratio mismatch (`NORO-SURFACE-CONSUME-01`) are all
filed and remain unstarted. This entry does not proceed into any of them.
