# NORO-HIGH-TOUCH-DEFINITION-01
**Date:** 2026-09-22
**Commit:** 97b6af7
**Pathogens:** norwalk_gi
**Status:** open
**Measured at:** 25eaa17

Nothing here is a new measurement. The only measured input is the `g0.25`
canary of `NORO-HIGH-TOUCH-AREA-01` (20 seeds 8000–8019, 288 epochs,
measured at `25eaa17`), which established that per touch the areal knob is
exact: area ratio 0.250000, log10 `f_touch` shift +0.60 against a predicted
+0.602. Everything below is arithmetic on that relation and on enumerated
item sets. **No constant changes in this entry and nothing is adopted.**

## 1. Question

`NORO-TRANSFER-PRODUCT-01` (measured at `bd462c5`) left `HIGH_TOUCH_AREA_M2`
as the factor that sets the hull's fomite dose: the chain either side of it
is defensible and essentially uncapped (8 truncations in 170,023 pickups),
and `f_touch` spans 6.1e-5 to 7.5e-4 almost entirely on the denominator.
`NORO-HIGH-TOUCH-AREA-01` then bounded `A` between two *readings* of the
phrase "high touch" — `hardware` and `broad` — and found that no single
reading made the shipped table consistent: the shipped values sat at 0.05×
to 1.03× of `hardware` and 0.92× to 14.53× of `broad`, differently per zone
class, with per-person denominators spread ~40× across the table.

That is not a measurement problem. It is a **definition** problem: a table
whose entries answer different questions cannot be made consistent by
choosing a multiplier for it. This entry asks what "high touch" means for
this hull, once, and then does the arithmetic that definition implies.

## 2. The definition

> **A zone's high-touch area is the summed touched extent of its
> multi-user surfaces: the surfaces that more than one of the zone's
> occupants contacts by hand over one occupancy cycle.**

Two clauses, each doing work. *Multi-user* excludes surfaces one occupant
touches and nobody else does. *Touched extent* counts the part of an object
hands reach, not the object's total surface.

**This definition is not chosen; it is forced by the numerator already
shipped.** `SURFACE_CONTACTS_PER_HOUR` declares itself, in its own comment,
to be "public/shared-surface rates, not all-surface rates: the studies
separate touches of one's own belongings from touches of shared fomites".
Its dining and galley entries are literally Jin 2022's T + R classes
(diners 38.5 + 4.3 = 42.8/h; staff 245.8 + 299.6 = 545.4/h), with the PP
and PT classes — personal objects and the per-diner place setting —
excluded. A rate counted over a surface set and a density computed over a
different surface set do not compose. Numerator and denominator must
enumerate the same surfaces, and the numerator got there first.

**It is also the partition observation actually uses.** Tranche 46
(`../literature/consensus_tranche_46_touch_behaviour.md`) records that every
video-coded touch study partitions surfaces by how many people touch them,
never by object kind:

* Zhang 2018, 1,490 coded surfaces and 120,000+ touches in an office —
  the touch network is scale-free and **76.9% of surfaces have degree 1**.
  A degree-1 surface cannot carry transfer between two people; it is in the
  room but not in the denominator.
* Zhang 2021, same office, 98,000+ touch actions — **public surfaces carry
  53% of fomite transmission** despite being the rare class; never touching
  others' personal surfaces would cut exposure 80%.
* Jin 2022, 41,042 restaurant touches — the seven-class coding scheme
  (M, H, B, PP, PT, T, R) is exactly this partition, and it is a *norovirus*
  study.
* Zhang 2024, 25,925 airport touches over 108 surfaces — "private surfaces
  (e.g., phones, boarding passes)" against "public surfaces (e.g., check-in
  counters, restaurant tables)".

And it dissolves the hardware-vs-planes axis rather than picking a side:
every enumerated shared set in the literature mixes the two. Lei 2017's 422
aircraft surfaces are tray tables *and* armrests; Huslage 2010's five are bed
surface and over-bed table *and* rails and an IV pump; Ackerley 2025's 13
lobby fomites are counter tops *and* door handles; Zhang 2024 files a
restaurant table as a public surface next to a check-in counter. No
observational protocol has ever split hardware from planes. Tranche 45's two
readings were an artefact of enumeration, and this entry retires them.

**What the definition excludes, concretely:** a berth's own bedding and
linen (single-user within the stateroom), and the dining place setting —
Jin's PT class, provided by the room but personal to one diner. **What it
newly includes:** the touched planes the `hardware` reading dropped — table
tops, chair backs and seats, the stateroom desk, the galley work planes —
because observation counts touches on them.

## 3. Why the *unweighted* sum, given that touch is heavy-tailed

Touch over the shared set is far from uniform: two of Ackerley's 13 lobby
fomites take 54% of all touches; Zhang 2018's office has a degree-14 hub.
It is tempting to shrink `A` towards the hot surfaces. The engine's own
structure says not to, and the reason is worth stating because it is the
part of this that is not a judgement call.

Let the shared set be surfaces `i` with areas `a_i`, and let `p_i` be the
share of touches landing on `i`. A touch picks up in proportion to the local
areal density `m_i / a_i`, so the mean density a random touch encounters is
`Σ p_i · m_i / a_i`. The uniform-pool model the engine implements delivers
`M / A` instead, with `M = Σ m_i`. Equating them fixes what `A` has to be,
and the answer depends on how mass arrives:

* **Deposition proportional to touch** (hand-mediated contamination), i.e.
  `m_i = M p_i`: the mean density is `M Σ p_i² / a_i`, so the consistent
  denominator is `A = 1 / Σ (p_i² / a_i)` — a touch-weighted harmonic area
  that collapses onto the hot surfaces.
* **Deposition uniform over area** (settling, spatter, aerosol — what the
  engine actually does: `HIGH_TOUCH_AREA_M2`'s own comment states "the
  density is uniform over the zone"), i.e. `m_i = M a_i / Σ a_j`: the mean
  density is `Σ p_i · M / Σ a_j = M / Σ a_j`, **for any touch distribution
  whatever**. The consistent denominator is the plain unweighted sum.

The engine deposits uniformly, so the engine's consistent denominator is the
unweighted sum of the shared touched extent. Touch weighting is the
correction that would apply to a model that tracked per-surface mass, and
this model does not. Recording the alternative here so that nobody
re-litigates it: adopting a touch-weighted `A` *with* uniform deposition
would be a second inconsistency, not a refinement.

## 4. The re-derivation, and the granularity the shipped table mixes

Derived by `tools/noro_diag/high_touch_area_envelope.py` (reading `shared`),
which multiplies the enumerated item sets by the per-item areas of
`ITEM_AREA_M2` against the actual `classic_cruise_1900` zone occupancies.
Item areas are unchanged from tranche 45 — `measured` (Park 2015 toilet seat
700 cm², Gerba 2025 flush handle 10 cm²), `qmra` (Weir 2016 fomite areas), or
`declared` geometry. The definition changed the *membership* of the sets,
not the areas. Grade C, derived, adopted nowhere.

**The shipped table's granularities do not match each other.** `cabin` is
per stateroom compartment; `dining`, `public`, `galley` and `crew_mess` are
per layout zone; `sanitary` is per water closet, scaled by fixture count.
That is defensible only if each unit's number answers the same question,
and it does not: a 365-seat main dining room and a 2-berth stateroom are
given 8.0 m² and 1.5 m², i.e. 0.022 and 0.750 m² per occupant — a 34× gap
between two entries of one table, and 54× across the table.

| zone class | unit | rep. occ. | shipped `A` (m²) | derived `A` (m²) | ×shipped | shipped m²/occ | derived m²/occ |
|---|---|---:|---:|---:|---:|---:|---:|
| cabin | one stateroom compartment (2 berths) | 2 | 1.50 | 1.319 | 0.88 | 0.750 | 0.659 |
| sanitary | one water closet | 1 | 0.50 | 0.458 | 0.92 | 0.500 | 0.458 |
| galley | one galley zone | 60 | 10.00 | 19.314 | 1.93 | 0.167 | 0.322 |
| dining | one dining zone | 365 | 8.00 | 98.695 | **12.34** | 0.022 | 0.270 |
| crew_mess | one crew mess zone | 200 | 4.00 | 54.120 | **13.53** | 0.020 | 0.271 |
| public | one public zone | 444 | 6.00 | 69.905 | **11.65** | 0.014 | 0.158 |

Every derived value is far below the measured total-room-surface ceiling
(Manuja 2019 / Hodgson 2005): dining 98.7 against 4,088 m², public 69.9
against 7,535 m², cabin 1.3 against 128 m². Nothing here is geometrically
impossible.

**The headline is the last two columns, not the fourth.** Under one
definition the per-occupant denominator tightens from a **54× spread**
(0.014–0.750 m²/occupant) to a **4.2× spread** (0.158–0.659), and the
residual spread is interpretable: a stateroom's two occupants share a fixed
inventory of fittings, so their per-head share is large; a lounge seat is
mostly the chair itself. For the first time the six entries answer the same
question.

**Where the change lands, and why.** The three classes that move by more
than 3× — dining 12.3×, crew_mess 13.5×, public 11.7× — are exactly the
three whose shipped value is flat in occupancy. Observation says the shared
set of a seated space scales with seats (Lei 2017: 3.3 shared surfaces per
seat; Jin 2022's T class is populated per diner), and the shipped table gives
a 365-seat dining room one small room's worth of hardware. `cabin`,
`sanitary` and `galley` — the three whose shipped values were sized as fixed
inventories — come out within a factor of two, which is the closest thing to
independent corroboration this exercise can produce: three entries derived
from published item sets and areas reproduce three declared assumptions.

## 5. What adoption would cost, analytically

Per touch, the canary measured `dose ∝ 1/A` exactly (area ratio 0.250000,
log10 shift +0.60 vs +0.602 predicted, in cabin/public/dining/crew_mess).
Adopting the derived table therefore multiplies per-touch pickup by
`A_shipped / A_derived`:

| zone class | per-touch dose × | Δ log10 per-touch dose |
|---|---:|---:|
| cabin | 1.14 | +0.06 |
| sanitary | 1.09 | +0.04 |
| galley | 0.52 | −0.29 |
| dining | 0.081 | −1.09 |
| crew_mess | 0.074 | −1.13 |
| public | 0.086 | −1.07 |

So the definition costs roughly **one order of magnitude of per-touch fomite
dose in the three shared passenger/crew zones**, leaves the stateroom and the
head where they are, and halves the galley.

Three qualifications, all of them load-bearing:

1. **This is per touch, not per voyage.** The same canary measured that
   whole-voyage dose does *not* scale as `1/A`: median arm/base ratio 7.7
   against a ±10% criterion, per-seed ratios spanning 0.01 to 7e5, because a
   per-touch change of this size re-routes the outbreak rather than rescaling
   a fixed deposition history. Nothing in this table predicts a voyage
   outcome, and no voyage-level number may be inferred from it.
2. **The direction is the benign one for the cap.** At 0.25× area the canary
   censored capped pool pickups in the shared zones (galley 8.4%, crew_mess
   2.6%, dining 1.2%). This change moves `A` the other way in exactly those
   zones, lowering areal density and reducing capping, so the per-touch
   relation applies uncensored — unlike the canary's galley row, which
   departed only because of censoring.
3. **`A` is not only the pickup denominator.** Per the sweep-axis comment at
   `_fomite_surface_area`, it also sets the emesis `touchable_fraction`, the
   `EmesisPatch` area, and the surface-swab density denominator. Adoption
   moves all four together; only the first is covered by the `1/A` relation
   above. The swab channel in particular is an *observation* denominator
   (`observation.surface_swab_source: surface_pool_density`), so adoption
   would move simulated swab positivity as well as dose.

Every dose figure in the repository remains withdrawn pending the norovirus
refit (`../norovirus/norovirus_open_ledger.md`); the multipliers above are
ratios against a withdrawn baseline and are not themselves dose results.

## 6. The decision, for Benjamin

The entry adopts nothing. Three options, stated so the choice is explicit:

**(a) Adopt the derived table.** `HIGH_TOUCH_AREA_M2` becomes cabin 1.32,
dining 98.7, public 69.9, galley 19.3, crew_mess 54.1;
`SANITARY_HIGH_TOUCH_AREA_M2_PER_WC` becomes 0.46. The table becomes
internally consistent under one stated definition matching the numerator's
surface set. Cost: ~1 log10 of per-touch fomite dose in three zone classes,
into a model whose norovirus attack rate is already being refit, and the
change rests on `declared` per-item geometry for the two items that dominate
the shared zones (`table_top_per_seat` 0.12 m², `chair_touched` 0.15 m²).
Nothing independent pins those two numbers, and dining/crew_mess/public are
~99% of their derived area.

**(b) Adopt the definition, not yet the numbers.** Record the definition at
the constant, keep the shipped values, and let the eight-arm area campaign
run with the derived table as one of its arms. This is the option that does
not spend the refit's credibility on two declared geometries, and it is the
one this entry's author would take.

**(c) Reject and re-open.** If the ~1 log10 is unacceptable on prior grounds,
the disagreement is with the *definition*, and the place to argue it is §2 —
not the item table. The only ways out are to re-admit per-diner place
settings and own-berth bedding to the shared set (which contradicts the
numerator's own classes), or to hold that the denominator should not scale
with occupancy (which contradicts Lei 2017 and Jin 2022).

The one thing this entry asserts unconditionally: **the shipped table cannot
be defended as it stands**, because its six entries are not answers to the
same question. Whichever of (a)–(c) is taken, that is now on the record.

## 7. Out of scope, recorded so it is not lost

`SURFACE_CONTACTS_PER_HOUR["cabin"]` = 17.9/h cites Yuan 2024 for "primary
shared surfaces", but the four surfaces Yuan names are desks, cellphones,
keyboards and computer mice — three personal objects and a personal desk in
a dormitory. That is an all-surface rate for a residential occupant, and the
comment's "shared" label is a numerator-side provenance defect. It is not
repaired here (this entry changes no constant) and it does not affect §4 or
§5, which concern the denominator only. Tranche 46 §2 carries the excerpt.

## 8. What this entry did not do

No campaign, no sweep arm, no AWS Batch, no re-run of the `g0.25` canary. No
change to `HIGH_TOUCH_AREA_M2` or `SANITARY_HIGH_TOUCH_AREA_M2_PER_WC`. No
constant fitted to VSP, to Park 2015, to an attack rate or to the
passenger/crew ratio — the derivation takes occupancies from the platform
layout and areas from published per-item measurements, and never consults an
epidemiological target. The `∅nr`/`∅lit` null of tranche 45 is re-tested and
stands: no retrieved source reports a summed high-touch area for any room.

The eight-arm area campaign remains un-run and out of scope. Its criterion 2b
must be rescored as a paired per-seed dose distribution with censored shares
before it is submitted; a ±10% median ratio is not a usable criterion against
per-seed ratios spanning 0.01–7e5.
