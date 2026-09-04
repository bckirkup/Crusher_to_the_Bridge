# Exterior and pool-deck zones: what the model currently asserts about them

> **Status:** Proposed. **Nothing here is implemented.** No zone attribute, no
> dilution factor, no inactivation constant, no AHU membership change and no
> occupancy change is made by this document, and none is recommended yet. It
> records the reasoning that is currently missing, and the seams a repair would
> use.

## 1. Why this document exists

[`surface_decay_biphasic_spec.md`](surface_decay_biphasic_spec.md) §4 argues
that the environmental covariates of the influenza surface-decay literature —
relative humidity, temperature — largely collapse on a cruise ship, because the
interior is HVAC-pinned near the condition Qian 2023 measured at. That argument
is sound for the interior and **false for the open decks**, which every cruise
platform in `data/platforms/` has. It was not qualified there because the zone
records carry no attribute that would have made the exception visible.

So the question is not only "what should the model do about open decks" but
"what does it currently assert about them", and the second has a specific
answer that is worse than a neutral one.

## 2. What the tree does today

### 2.1 The zones exist and are named as exterior in their own prose

`mega_cruise_5000` carries `Main_Pool_Deck` (9,000 m³, capacity 1,200),
`Waterpark` (3,600 m³, 700), `Sports_Court` (1,800 m³, 250), `CentralPark`
(36,000 m³, 1,800) and the glazed `Solarium` (4,200 m³, 500). Their own
`description` strings say **"semi-open"**, **"open-air Central Park / atrium
canyon"** and **"outdoor recreation deck"**. `spirit_cruise_3000` has
`MainPool`, `AftPool`, `SportsDeck`; `classic_cruise_1900` and both expedition
platforms have a `PoolDeck`; `messy_cruise_500` mirrors the mega set. The prose
knows; no field does.

### 2.2 No zone record has an environmental attribute

The union of keys over all 129 `mega_cruise_5000` zones is `id`, `type`,
`traffic`, `volume_m3`, `deck`, `max_occupancy`, `description`, `display`,
`dining_service_type`, `food_contamination_multiplier`,
`cabin_ventilation_type`. There is no humidity, temperature, insolation,
exposure or outdoor field on any platform. `type` takes four values —
`Free`, `Dining`, `Cabin_Corridor`, `Medical` — so the pool deck is typed
identically to the casino and the library, and `Pool_Bar_Grill` identically to
the main dining room.

The **only** outdoor-air concept in the engine is
`TransmissionCore._aerosol_ventilation_factor`, which returns
`BALCONY_AEROSOL_REDUCTION = 0.5` when a zone's `cabin_ventilation_type` is
`balcony_partial`. It applies to cabin corridors. So the model already accepts
that outdoor air dilutes aerosol — it just applies the idea to balconies and not
to the pool deck.

### 2.3 The current treatment is not neutral; the sign is reversed

Open decks are members of recirculating AHU networks:

| Platform | Network | ACH | Exterior members it shares air with |
|---|---|---|---|
| `mega_cruise_5000` | `AHU_Network_Aft_Dining_Rec` | 10.0 | `Main_Pool_Deck`, `Sports_Court`, `Waterpark`, `Aqua_Theater` — ducted together with `Windjammer`, `MainDining_L/U`, `Kids_Club`, `Teen_Zone` |
| `mega_cruise_5000` | `AHU_Network_Midship_Atrium` | 6.0 | `CentralPark` (open-air canyon) with `Casino`, `ShopRetail`, `ComedyClub` |
| `spirit_cruise_3000` | `AHU_Public_Aft` | 10.0 | `MainPool`, `AftPool`, `SportsDeck` |
| `classic_cruise_1900` | `AHU_Public_Aft` | 10.0 | `PoolDeck` |
| `expedition_cruise_300` | `AHU_1_Upper` | 8.0 | `Pool_Deck` |

with `oa_fraction: 0.2` — so 80% of that air is recirculated. An agent shedding
on the open pool deck therefore delivers aerosol **into the indoor buffet**
through a shared duct, at 10 ACH. The physical expectation for an open deck is a
sink; the model makes it a source. That is a stronger defect than a missing
decay covariate, and it does not require any new constant to see.

Path A agrees with Path B here rather than correcting it:
`mega_cruise_5000/contam/platform.prj` gives every zone `T0 = 293.15` K
including `Main_Pool_Deck`, with no ambient path — and the ContamX compare job
`data/config/contam_compare/jobs/mega_cruise_transport.json` injects its tracer
at `CentralPark`, i.e. the transport benchmark's source term is an open-air
zone treated as sealed.

### 2.4 Surface decay cannot see the zone at all

`TransmissionCore._surface_survival(profile)` takes a pathogen profile and
nothing else. There is no zone argument, so a sun-exposed, salt-wetted pool-deck
handrail decays at exactly the rate of a cabin doorknob. Whatever the
[biphasic spec](surface_decay_biphasic_spec.md) concludes about drying, it
currently could not be applied differently to a deck that never dries.

### 2.5 How much exterior exposure there is, is currently arbitrary

Leisure location is assigned by `free = rng.choice(self._free_zones)` in
`engines/infection_dynamics_bridge.py` — **uniform over the `Free` zones,
capacity-blind** — and `free_zone_rotation_probability` defaults to `0.0`, so
that single draw is where an agent spends all of its `Free` hours. Dining does
the opposite: `_resolve_dining_location` weights candidates by
`max_occupancy × service-type weight`.

On `mega_cruise_5000` there are 21 `Free` zones with 13,917 total capacity:

| Group | Zones | Uniform draw share | Capacity share |
|---|---|---|---|
| Exterior/semi-open (`Main_Pool_Deck`, `Waterpark`, `Sports_Court`, `CentralPark`, `Solarium`) | 5 | 0.238 | 0.320 |
| Service and control spaces (`Engine_Room_Aft`, `EngControl`, `WasteTreat`, `Laundry_Main`, `Central_Stores`, `Bridge`) | 6 | 0.286 | 0.017 |

So 28.6% of agents — passengers included — are assigned the engine room, waste
treatment, the laundry or the bridge as their leisure venue, against a 1.7%
capacity share: a **17× over-representation** of spaces no passenger enters. The
exterior zones are under-weighted by about 1.3×. **This has to be fixed before
any exterior-zone question can be quantified**, because the exposure share that
would multiply any exterior effect is currently set by how many zones a platform
file happens to list rather than by how big they are.

## 3. The three defensible positions, and what decides between them

The user's framing is right that we may legitimately assert open decks are not
transmission venues — but the assertion has to be written down, and each version
implies a different repair.

**(a) Exterior zones are not meaningful transmission venues.** Continuous
outdoor exchange dilutes aerosol to negligible dose; UV and desiccation
shorten surface persistence; contacts are brief and dispersed over large areas.
If this is the position, then **the defect is the AHU membership, not the decay
rate** — an inert venue must not be ducted into the buffet — and the repair is
to remove exterior zones from recirculating networks, or to give them an
exterior exchange path, and to leave everything else alone. Cheapest of the
three, and it makes the current treatment strictly *less* transmissive rather
than more.

**(b) They are venues with a different environment.** Then `Free` is too coarse:
zones need an exposure attribute, aerosol needs a dilution factor per exposure
class, and surface decay needs the zone. This reopens the environmental axis
[`surface_decay_biphasic_spec.md`](surface_decay_biphasic_spec.md) §4 set aside
— as **zone-conditional** rather than global, which is a different claim than
the one that document makes.

**(c) They are venues where the dominant route changes.** Aerosol dilutes but
the fomite pathway may not: loungers, handrails and wet decks are shared,
high-touch and — critically for the biphasic argument — **may never complete the
drying transition**. If the fast phase is the wet phase, a permanently wet
poolside surface sits in the slow-loss regime the interior only passes through.
That is the one place where the pool deck could plausibly *increase* rather than
decrease transmission, and it is an argument about the wet/dry split rather than
about humidity as a rate covariate.

Which of these holds is an empirical question we have not asked the literature.
Nothing in `docs/literature/` covers outdoor or semi-open transmission, solar
inactivation of our three pathogens, or marine-aerosol effects.

## 4. Pool water itself is not a route

The six pathways carry no recreational-water route: pool and hot-tub water is
not a medium anywhere in `engines/`. For our three arms this is probably the
right answer — but "probably" is the problem, and the reasoning is currently
unwritten rather than settled. The claims that would justify it (chlorine
susceptibility of norovirus at maintained free-chlorine residuals; whether
enveloped respiratory viruses survive treated pool water at all; whether
ingestion volumes reach an infectious dose) are all sourceable and none is
sourced here. The chlorine-tolerant recreational-water pathogens are outside
our three arms, which is a reason to expect the route to be negligible, not a
measurement showing it is.

## 5. Where a repair would wire in

The seam already exists and needs no new architecture: `TransmissionCore`
already receives zone-keyed dictionaries (`zone_volumes`, `zone_types`,
`zone_ventilation`, `food_zone_multipliers`), so an exposure class is a fifth
one, resolved from a new optional zone field in `spatial_layout.json` exactly
as `cabin_ventilation_type` is today. The three touch points, in ascending cost:

1. **AHU membership** — a data audit per platform against each zone's own
   description. No constant required; changes cross-zone airborne transport.
2. **Aerosol dilution by exposure class** — follows the existing
   `_aerosol_ventilation_factor` precedent, and needs one sourced factor per
   class rather than a full environmental model.
3. **Zone-conditioned surface decay** — requires
   `_surface_survival(profile)` → `_surface_survival(profile, zone)`. Note that
   this is *the same signature change* covariate-indexed decay would need, so
   if exterior zones ever get their own rate, R2's environmental axis returns
   through the zone rather than through the pathogen profile. That ordering
   matters: doing R2 first as a profile-level covariate would put the covariate
   on the wrong object.

## 6. What this document does not do

It adopts nothing. No zone is classified, no dilution factor or UV inactivation
rate is proposed, no AHU membership is changed, no occupancy weighting is
changed, and no position in §3 is selected. Every quantity a repair would need
is unsourced: exterior air exchange or dilution, solar inactivation for
norovirus, SARS-CoV-2 and influenza, salt-aerosol effects, wet-surface
persistence poolside, and the recreational-water claims of §4.

## 7. Order of work

1. **Fix the capacity-blind `Free` draw** (§2.5). Until leisure occupancy is
   weighted, no exterior effect can be sized, and the current draw puts a
   quarter of the ship's leisure hours in the engine room and the laundry.
2. **Audit AHU membership** (§2.3). No constant needed, and it is the one item
   that is a defect under all three positions in §3.
3. **Then source**, and only then choose between §3(a), (b) and (c). Position
   (c) should be decided together with
   [`surface_decay_biphasic_spec.md`](surface_decay_biphasic_spec.md), because a
   never-drying surface is the same mechanism seen from the other end.
