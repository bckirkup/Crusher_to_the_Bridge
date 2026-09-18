# FLUSH-S3
**Date:** 2026-09-17
**Commit:** 71a5aae
**Pathogens:** norwalk_gi
**Status:** open

The `s2r` and `s2e` flush archives are superseded. Both were taken at engine
`585ad89`; four changes have landed since that move the routes those arms dosed
through, so no arm of either campaign — including its `off` baseline — is
re-readable on the current engine, and the crossing they located is historical.

## What moved

**HVAC downstream dose is structurally lower, not scaled lower.**
`_pathway_hvac_airborne` looped over each upstream source and applied the full
target mass once per source, so a target zone fed by *N* shedding upstream
zones received *N* whole doses; the current code builds the target-to-source
mapping once and doses each target once (`924351c`), and deduplicates route
sources so several stateroom keys on one block collapse to their parent block
(`ff767a9`). The reduction is approximately `1/N` and varies with source
topology, not by a single factor. PR #583 additionally multiplies the
downstream dose by `_confinement_factor`, `confinement_isolation_factor = 0.05`
for a confined target. `s2r` found HVAC drift to be the dominant norovirus
route, so this is the largest single mover of the flush contrast, and its
direction on the crossing is *upward* — more `f_aero` needed to resolve.

**Stateroom airborne pools are per-stateroom.** PR #591 with `646c7a0` credits
event mass to the compartment key itself under `cabin_air_mode =
cabin_compartment` and partitions block air so each stateroom retains its own
mass preferentially, distributing only the pooled remainder by berth share
(`engines/stateroom_air.py::partition_block_air`). Where the mass sits between
epochs changes; the same-epoch dilution volume does not.

**The emesis source term is one to one-and-a-half decades higher.** PR #595
replaced the equal-partitioned illness total with a per-illness host titre
times per-episode volume. The flush-`off` baseline therefore now carries an
emesis-aerosol infection contribution it did not have when the emesis emission
sat four decades below N50. Direction on the `off` arm's secondaries is
*upward*, independently of any flush term.

**Environmental observers read physical pools.** PR #589 and #590 give the
surface swab a per-area density with a sourced LOD and route excreta to a
blackwater tank with a stated assay LOD. Both are default-off and are not
enabled in these arms; they are recorded here because they are the reason the
source term matters beyond the attack rate.

## The same-epoch dose paths, and what the closed form can and cannot say

`sanitary_visit_mode` is `dwell_weighted` in every arm, so two same-epoch
paths are live: a visitor's dwell-weighted dose in a shared head
(`_dose_flush_sanitary`) and an occupant's whole-epoch dose in the venue of a
host's own cabin fittings (`_dose_flush_cabin`). Neither has changed since
`585ad89` — the cabin path still dilutes into `_air_unit_volume`'s berth-share
partition — and every read of `flush_aerosol_fraction` is a bare
multiplication (`aerosol_load = bowl_copies * f`, residual
`bowl_copies * (1 - f)`, with `f <= 0` a separate disabled path), so the
emitted mass remains exactly linear in the swept fraction and the `off` arm
remains a distinct disabled path rather than the limit of the sweep.

Evaluating those two closed forms at the shipped constants
(`FLUSH_STOOL_MASS_G = 107`, `BREATHING_RATE_M3_PER_DAY = 14.4` at 1-hour
epochs, sanitary exhaust 19.15 ACH, `SANITARY_DWELL_SECONDS = 155`, the
beta-Poisson `alpha = 0.111` / `beta = 32.81` whose N50 is 16,871) puts the
cabin path far above the sanitary path per exposure: a peak shedder's roommate
in a ~41 m³ stateroom crosses N50 at `f_aero` ≈ 1e-7 and still takes
P(infection) ≈ 0.12–0.18 per flush epoch at 1e-9, whereas one visit to a
6.2 m³ head crosses N50 only near 7e-6 and is P ≈ 0.008 at 1e-9. The shallow
`alpha` is why the low decades are not negligible.

What the closed form cannot predict is the voyage-level outcome, and that is
the recorded lesson of stage 1: the per-exposure saturation argument was
correct and the voyage-level conclusion drawn from it was falsified, because
saturating each exposure multiplies exposures and every new infection flushes
too. The two movers above push the voyage-level crossing in opposite
directions. No prediction of its location is declared here.

## Declared arms

A single re-bracket, tagged `s3`, replaces the un-run downward stage 3 and
supersedes stages 1 and 2 as the measurement of record:

| Arm | `flush_aerosol_fraction` | Role |
|---|---|---|
| `off_s3` | 0.0 (disabled path) | matched baseline on the current engine |
| `1e-9_s3` | 1e-9 | Johnson 2013 floor |
| `1e-7_s3` | 1e-7 | the decade every cell resolved at in `s2r` |
| `1e-5_s3` | 1e-5 | saturation falsifier, retained deliberately |

Six cells (expedition, classic, spirit × 7 d, 12 d), seeds 8000–8099 — the
first 100 of the matched block, a prefix and never a resample — 600 runs per
arm, 2,400 total. `cabin_air_mode: cabin_compartment` and
`hvac.pathogen_pool_transport: airflow` are pinned in every manifest rather
than inherited, and every archived run now stamps
`parameters.engine_git_sha` (PR #580), so this campaign is the first flush
measurement that is self-describing.

The frozen `[1e-9, 1e-3]` refusal band is not narrowed. No arm may be adopted
because it matches A9, A4, VSP or MIDRS; comparator values are reported as
external contrasts only.

## Declared decision rule

Fixed before the archives land, so the follow-up arms are placed by the shape
of the contrast and not by distance to a comparator:

- `1e-9` resolves a paired contrast → extend downward with `3e-10` and `1e-10`.
- `1e-9` is a null and `1e-7` resolves → place half-decade arms inside that
  interval.
- secondaries still rise from `1e-7` to `1e-5` → the saturation argument is
  falsified again at voyage level and is not to be reasserted; the fine arms go
  below `1e-7` regardless.

The two arms straddling the measured crossing are then re-run at the full 200
paired seeds.
