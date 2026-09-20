# NORO-EMESIS-SIZE-01
**Date:** 2026-09-19
**Commit:** a44d4c4
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** e83aa06

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

## Readout

Measured at `e83aa06` on `classic_cruise_1900`, 1,910 agents, 288 epochs,
seeds 8000–8019, shipped bundle, no override. Dumps:
`docs/norovirus/noro_emesis_size_01/classic_cruise_1900/`; aggregate:
`docs/norovirus/noro_emesis_size_01/emesis_size_cells.json`, written by
`tools/noro_diag/emesis_size_readout.py`.

**Admissibility.** 20 of 20 cells admissible, 0 void, against a declared void
ceiling of 4: **GO**. The reconciliation gate passes exactly — credited
scaled dose, dose read at challenge and effective dose evaluated agree to a
worst relative difference of 0.0e0 in every cell, against the declared 1e-9.

| seed | imports | secondaries | emesis events | patch mass (GEC) | patch pickups | mass delivered from patches (GEC) | credited scaled (GEC) | Σ evaluated hazard |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8000 | 5 | 0 | 1 | 218,617 | 1 | 218,617 | 631.001 | 1.20828e-1 |
| 8001 | 5 | 0 | 0 | 0 | 0 | 0 | 1.44742e-1 | 1.61869e-4 |
| 8002 | 7 | 0 | 6 | 9.48444e7 | 404 | 3.70352e6 | 14,139.6 | 9.43096e-3 |
| 8003 | 2 | 0 | 0 | 0 | 0 | 0 | 4.84496e-4 | 2.97987e-6 |
| 8004 | 2 | 0 | 0 | 0 | 0 | 0 | 3.13219e-6 | 3.40004e-9 |
| 8005 | 5 | 0 | 0 | 0 | 0 | 0 | 3.92733e-2 | 1.41820e-4 |
| 8006 | 3 | 0 | 1 | 272,424 | 41 | 65,872.5 | 360.407 | 5.23970e-3 |
| 8007 | 7 | 0 | 0 | 0 | 0 | 0 | 6.10892e-4 | 1.47641e-7 |
| 8008 | 3 | 0 | 0 | 0 | 0 | 0 | 9.57901e-3 | 4.78649e-6 |
| 8009 | 10 | 0 | 2 | 1.18480e6 | 109 | 63,547.2 | 328.333 | 2.18939e-2 |
| 8010 | 1 | 0 | 0 | 0 | 0 | 0 | 6.86194e-5 | 1.31901e-8 |
| 8011 | 4 | 0 | 0 | 0 | 0 | 0 | 2.41374e-3 | 6.89125e-6 |
| 8012 | 6 | 0 | 0 | 0 | 0 | 0 | 6.97073e-1 | 2.19338e-3 |
| 8013 | 3 | 0 | 0 | 0 | 0 | 0 | 2.22830e-2 | 3.11229e-5 |
| 8014 | 5 | 0 | 0 | 0 | 0 | 0 | 7.58275e-2 | 4.21191e-5 |
| 8015 | 1 | 0 | 0 | 0 | 0 | 0 | 4.41805e-45 | 9.05101e-51 |
| 8016 | 4 | **2** | 1 | 1.18435e7 | 1 | 189,211 | 1,094.12 | **1.69133** |
| 8017 | 2 | 0 | 0 | 0 | 0 | 0 | 12.4612 | 4.80611e-2 |
| 8018 | 6 | **1** | 4 | 4.85354e7 | 7 | 4.26135e6 | 18,055.7 | **1.10517** |
| 8019 | 6 | 0 | 0 | 0 | 0 | 0 | 1.12833e-2 | 9.43232e-5 |

### 1. Incidence

Emesis fires in **6 of 20 voyages (30%)**. Conditional on firing, the event
count per voyage is 1, 1, 1, 2, 4, 6 (median 1.5, mean 2.5). Six event-bearing
voyages clears the declared floor of three, so the mechanism is sizeable at
this n; a per-event rate is not.

### 2. Size

Across the six event-bearing voyages, patch mass spans 2.19e5 to 9.48e7 GEC
(median 6.51e6) and mass delivered from patches to hands spans 6.35e4 to
4.26e6 GEC (median 2.04e5). The delivered/filed ratio spans 0.0160 to **1.00**
(median 0.0707), i.e. a **median 1.16 log10 loss** between a bolus and the
hands it reaches, range −0.0 to 1.80 log10.

The instrument's `patch_pickup_dose_gec` counter records
`_emesis_patch_pickup_one`'s return, which is mass *delivered to hands*, not
ingested dose; it is named as delivered mass everywhere in this readout. It is
therefore **not** comparable to `NORO-DOSE-01`'s 1.93 log10 hand→mouth term,
and the two are not combined: the emesis route's measured loss sits at the
same stage as that entry's 2.17 log10 surface→hand term, and is about one log
smaller because a bolus is deposited where susceptibles already are.

Seed 8000's ratio of exactly 1.00 is the saturation case: demand at
`_deliver_fomite_requests` met or exceeded supply, so a single susceptible
removed the entire 218,617 GEC bolus onto its hands in one epoch. The delivery
scale caps the set at the patch mass but imposes no per-host ceiling. Whether
one pair of hands can remove a whole bolus is a **provenance question, not a
measured defect**; filed below.

### 3. Share

Mass delivered from patches exceeds the voyage's *credited* scaled dose in
every event-bearing cell, by 173× to 346× (median 215×). The declared
upper-bound reading is therefore uninformative as a share — it is > 1 — and
what it actually measures is the **2.24–2.54 log10 attenuation between hand
delivery and credited dose**, which is the hand→mouth and route-efficiency
product acting downstream. That is consistent with `NORO-DOSE-01`'s 1.93 log10
hand→mouth term plus route efficiency, and is reported here as a consistency
check rather than as a share. A true emesis share needs the accumulator's own
per-pathway split, which this instrument does not separate for patch pickups;
filed below.

### 4. Consequence — this is the result that moves a prior conclusion

Σ evaluated hazard over the 20 voyages totals **3.0046**, and the block
produced **3 secondary infections**: expectation 3.00, observed 3. Per voyage
the hazard spans 9.05e-51 to **1.691** (median 1.18e-4); three cells exceed the
declared *plausible* threshold 0.105 and two exceed the declared *likely*
threshold 0.693. The maximum gives P(≥1) = 0.816.

The acquisitions are witnessed individually. Seed 8016: agent 228 at epoch 5,
dose 747.373 GEC, frailty 3.823e-3, hazard 0.9426 — an ordinary infection at a
high dose; and agent 630 at epoch 6, dose 5.538e-4 GEC, hazard 6.438e-5 — a
tail draw. Seed 8018: agent 900 at epoch 31, dose 15,639.182 GEC, frailty
1.170e-4, hazard 0.8395. Both secondary-producing voyages carried emesis
events.

So the declared confirmation condition **fails, and in the informative
direction**: `NORO-SUSCEPT-03`'s "maximum Σ hazard anywhere is 1.186e-2" is not
a property of the classic hull at this engine. It is a property of the
8105/8106 seed pair, which this block shows to be a low-tail pair — credited
dose across 20 seeds spans 4.42e-45 to 1.81e4 GEC, and the pair sits at 0.101
and 0.0027 GEC. Secondary transmission is not absent on `classic_cruise_1900`;
it occurs at about **0.15 secondaries per voyage**, concentrated in the
minority of voyages that carry an emesis event.

This does **not** re-open α. Nothing here touched `dose_response.alpha` or
`.beta`, and the measurement is orthogonal to the α interval: the hazard
distribution is set by which voyages get a bolus near susceptibles, not by the
dose-response slope.

### 5. Association (labelled, not a paired contrast)

The six voyages with an event carry median credited dose 862.561 GEC and
median Σ hazard 7.136e-2; the fourteen without carry median 1.043e-2 GEC and
median 1.901e-5. This is **associational across seeds**: seeds differ in every
draw, not only in whether a host vomited, and the event-bearing seeds also
carried more imports on average. A paired emesis-on/emesis-off contrast needs
a labelled suppression arm, which is a configuration change and was out of
scope.

## Verdict

The emesis mechanism is **sized at n = 20 and is the dominant source of
norovirus dose variance on this hull**: 30% of voyages carry it, those voyages
hold the whole upper tail of credited dose and all of the secondaries, and it
loses a median 1.16 log10 between bolus and hands. The study's own
zero-secondary confirmation condition is not met because the model does produce
secondaries here — three in twenty voyages, exactly the summed hazard's
expectation.

## Recommendation

1. **Re-measure anything that rests on the 8105/8106 pair alone.** The pair is
   a low-tail pair by two decades or more. `NORO-DOSE-01`'s mechanism findings
   (route attribution, the carrier dead end, absence of a host blocker) stand —
   they are structural — but its dose magnitudes and `NORO-SUSCEPT-03`'s hazard
   bound describe the pair, not the hull. This is the highest-value next step
   and it is cheap: the instrument and the block already exist.
2. **`NORO-EMESIS-SHARE-01`** — split credited dose by pathway for patch
   pickups so the emesis share can be stated as a share rather than as an
   upper bound above 1.
3. **`NORO-PATCH-SATURATION-01`** — provenance for the per-host pickup
   ceiling: whether one susceptible removing an entire bolus in one epoch
   (seed 8000) is intended, and what the literature bounds a single contact's
   removal at.
4. `NORO-HAND-STATIONARY-01`, `NORO-SURFACE-CONSUME-01`,
   `NORO-CARRIER-REDEPOSIT-01` and `NORO-TRANSFER-PRODUCT-01` remain filed and
   unstarted.

## Non-goals

No constant, profile, platform, or engine path is changed. No `--alpha` arm.
The truncated carrier mass (`NORO-CARRIER-REDEPOSIT-01`), the fomite transfer
product against literature (`NORO-TRANSFER-PRODUCT-01`), the hand reservoir's
stationary initialisation (`NORO-HAND-STATIONARY-01`) and the
`_consume_surface_mass` ratio mismatch (`NORO-SURFACE-CONSUME-01`) are all
filed and remain unstarted. This entry does not proceed into any of them.
