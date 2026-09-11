# The fomite pool denominator, reconciled against the seeded-flush literature

**Status: measurement and analysis of the shipped model. Nothing adopted; no
constant changed; `environmental_faecal_release_log10_g_per_epoch` is not
narrowed.** Written because
[tranche 38](../literature/consensus_tranche_38_environmental_release.md)
assembled a toilet-event release chain whose deposition factor is reported per
100 cm² of swabbed surface, and that denominator had to be reconciled with the
model's fomite pool before any of it could become a parameter.

The reconciliation returns three findings, and the first of them corrects
tranche 38.

---

## 1. The release scalar does not reach the surface pool at all

Tranche 38 proposed the event chain as a *replacement for* the release scalar
`environmental_faecal_release_log10_g_per_epoch` (`adj`). It cannot be one.
They act on disjoint routes.

In the profiled path (`_pathway_fomite`, `engines/transmission_core.py`), the
surface pool has exactly two inputs:

- **hands** — `deposit = contacts × used_fraction × transfer × hand_load`,
  capped at the hand load, where the hand load is `get_pathogen_hand_target`:
  `10^HAND_LOAD_LOG10_GEC` (Liu 2013, 3.86 log10 gc per hand, Grade B) scaled by
  the shedding curve against its reference peak. `adj` appears nowhere in it.
- **emesis** — `_deposit_emesis`, an absolute per-event load
  (`EMESIS_TOTAL_SHED_GEC_RANGE`), also untouched by `adj`.

The food route takes its deposit from the same hand load (FOOD-ARCH-01). The
one place a shedding value still reaches a surface is
`_pathway_fomite_legacy_default` (`deposit = shedding × SURFACE_DEPOSITION_FRACTION`),
and it is entered only when a run declares **no pathogen profiles at all** —
the unprofiled test harnesses, never a campaign or a norovirus voyage. So
`adj` scales only **direct contact, short-range aerosol, HVAC drift, the
environmental reservoir and wastewater** — the routes that read
`get_pathogen_shedding`. The faecal-hand-fomite-food chain is already on an
absolute, independently measured scale and is invariant to the whole [4, 24]
box.

Two consequences, both of which change what the box's `adj` scan meant:

1. A seeded-flush deposition measurement **cannot** be used to set, narrow or
   justify `adj`. It is evidence about a surface channel that `adj` does not
   feed.
2. The switch measured at `adj ≈ 6–7` is a switch in the *direct-contact and
   air* routes. Above it, what remains running is the fully sourced fomite
   chain — and it produces essentially no onward transmission. That is a
   statement about the measured chain, not about the void scalar.

## 2. The two denominators are commensurable, and the common unit is an areal density

The model's pool mass enters a pickup only through `mass / area`:

```
request = contacts × (used_fraction × hand_area / A) × transfer × mass
        = contacts ×  used_fraction × hand_area      × transfer × σ,
          σ = mass / A
```

so the pool is, arithmetically, an areal-density model whose state variable
happens to be stored as a mass. `A` is `HIGH_TOUCH_AREA_M2` — a permanent
Grade C declaration (register null class ∅lit: high-touch area per room in m²
has never been measured by anybody), now labelled as such at its definition.

Goforth 2023 and Sassi 2018 report σ directly, as log10 PFU per 100 cm² of
sponge-stick-swabbed surface. Same dimension. The denominators reconcile
without a conversion factor, which is the one good piece of news here.

The conversion that is **not** licensed is PFU → genome copies. It is not
needed: both sides of the deposition ratio are MS2 PFU, so

```
f_dep = σ_surface / bowl_load
```

is dimensionless and can be carried across to genome copies **only** under the
assumption that MS2 and human norovirus partition identically at flush. That
assumption is unmeasured — Grade C — and is declared here rather than buried.

## 3. On that common denominator the model's surfaces are 2 to 7.6 logs below a flush

Both sides evaluated at the shipped symptomatic curve peak (11.0 log10 gc/g).

**Model, hand-mediated deposition — a ceiling.** Computed from the shipped
constants with no decay, no cleaning, no depletion by pickup, and a full day of
touching, so the real pool is lower:

| zone class | touches/h | A (cm²) | baseline, 1.0 events/day | diarrhoeal, 5.63 events/day |
|---|---|---|---|---|
| cabin | 17.9 | 15,000 | 1.68 | 2.43 |
| crew_mess | 42.8 | 40,000 | 1.26 | 2.01 |
| dining | 42.8 | 80,000 | 0.96 | 1.71 |
| public | 21.0 | 60,000 | 1.08 | 1.83 |
| galley | 545.4 | 100,000 | 0.86 | 1.61 |

(log10 gc per 100 cm² per **day**, at the two shipped stool-event arms
`BASELINE_STOOL_EVENTS_PER_DAY` = 1.0 and `DIARRHOEAL_STOOL_EVENTS_PER_DAY` =
5.63. The ceiling binds in every cell: a day's deposition cannot exceed the
number of events times the Liu hand ceiling, because the hand is refilled only
at an event. Touch rate therefore drops out — even the galley's 545/h cannot
put more on a surface than the hand holds.)

For scale, the hand itself carries 3.17 log10 gc per 100 cm² of skin — so the
model's surfaces sit **1.5 to 2.3 logs below the hand that contaminates them**,
which is what an 0.8–25% used fraction and a ~3% mean transfer efficiency
spread over 1.5–10 m² must give.

**Literature, one flush — per event.** Bowl load at peak = 11.0 log10 gc/g ×
107 g (Rose 2015 median wet mass per defecation, via Boles 2021) = 13.03 log10
gc, times the seeded deposition fraction:

| condition | f_dep (log10) | σ (log10 gc/100 cm²) |
|---|---|---|
| public toilet, seat top | −3.65 | 9.38 |
| public toilet, seat underside | −3.90 | 9.13 |
| home toilet, seat top | −5.18 | 7.85 |
| home toilet, seat underside | −6.35 | 6.68 |
| home toilet, lid down, seat top | −8.79 | 4.24 |

**Against the cabin — the zone that actually contains a toilet — the gap is 1.8
to 7.7 logs, and it is worse than that: the model column is a whole day's
ceiling and the literature column is one event.** Even the most
contained condition in the literature — a domestic toilet flushed with the lid
down — deposits more on 100 cm² of seat in one flush than the model's cabin
accumulates over a day of touching in its own upper bound.

This is not a claim that the model's hand route is mis-sourced. Each of its
factors is measured. It is a statement that **the hand is the wrong-sized
reservoir to carry a faecal channel**: Liu's hand holds 10^3.86 copies, while
the bowl the flush aerosolizes holds 10^13.

## 4. What still does not reconcile, and why nothing is adopted

1. **The patch is not the zone.** Goforth's value is a density on one object —
   and seat top versus underside differ by 0.25–1.2 log within the same trial,
   so the within-restroom field is not flat. The model has no within-zone
   spatial structure: a pool gain is immediately available at the zone-mean
   density to a touch anywhere in the zone. Entering a seat measurement as a
   cabin pool gain therefore requires an area to deposit it over, and any
   choice smears a hotspot across 1.5 m² the moment it lands. **That is the
   recurring defect archetype** (a well-mixed pool standing in for a small
   number of concentrated events) reproduced on arrival, so the reconciliation
   does not license the deposit in this form.
2. **The touchable toilet area is `?nr`.** The projection the model already has
   for events is `touchable_fraction = HIGH_TOUCH_AREA_M2 / A_event`
   (`_deposit_emesis`), which is mass-conserving and would take a flush event
   unchanged — but it needs the seat/rim/handle area, and this repository has
   no sourced value for it. A declaration would be a fourth Grade C in a chain
   that already has three.
3. **MS2 is not norovirus.** §2's ratio is carried across on an unmeasured
   partition assumption.
4. **The titre is the curve peak.** A host off peak deposits less by the
   curve; the table is the maximum, not a typical host-day.

So: denominators reconciled, magnitudes compared, and **no constant adopted,
no interval narrowed, no value chosen**. The one code change in this record is
a provenance comment at `HIGH_TOUCH_AREA_M2` stating what it is and that the
field has never measured it.

## 5. What the reconciliation says the next change is

Not a re-normalisation. `adj` is the wrong lever for this evidence (§1), and
scaling the hand route to close a 1.8–7.7 log gap would be fitting.

The structural reading is that the faecal chain is missing its **concentrated
event deposition**: the model represents defecation only as a hand
recontamination (SYMP-EFF-01) and vomiting only as an emesis event, and has no
channel by which the bowl's 10^13 copies reach a surface at all. The
literature measures exactly that channel, on the right denominator, with a
containment lever (lid down, −3.6 log) that is an operator-adjustable control.
Building it requires the spatial answer in §4.1 first — a toilet-scoped pool
distinct from the cabin's high-touch pool, so a seat's density is not the
light-switch's — and that is a design question, not a parameter.

Recorded, not implemented.
