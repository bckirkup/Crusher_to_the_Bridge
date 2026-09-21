> **Status:** Living — literature record for ledger NORO-HIGH-TOUCH-AREA-01; adopts nothing

# Tranche 45 — the fomite areal denominator: what is measured, what is enumerable, and what the hull declares

**Read first.** `NORO-TRANSFER-PRODUCT-01` measured the per-touch chain and
found the two microbiological efficiencies defensible and essentially
uncapped (8 truncations in 170,023 pickups), which leaves the areal
denominator `HIGH_TOUCH_AREA_M2` as the factor that sets the hull's fomite
dose: `request ∝ 1/A`. This tranche asks what the literature can say about
`A`.

It **changes the null label**. The in-code comment said the quantity "has
never been measured by anybody (∅lit)". That is too strong on one side and
not strong enough on the other:

* **Too strong:** total object-plus-material surface area *per room* has been
  measured twice at object resolution, and high-touch *item sets* have been
  enumerated repeatedly, by observation and by tracer. An upper bound and an
  item list both exist.
* **Not strong enough:** none of that is the model's quantity. No retrieved
  source reports the total high-touch area of a cruise stateroom, main dining
  room, lounge, galley or head. The denominator is therefore not
  *unmeasurable* — it is **underived**: the ingredients are published and
  nobody had multiplied them out.

Nothing here changes a constant. The envelope in §4 is a *derived bound*, is
labelled Grade C, and is used only to frame the sweep arms of ledger
`NORO-HIGH-TOUCH-AREA-01`. No arm of that sweep is an adoption.

**Register rows fed.** Amends the `HIGH_TOUCH_AREA_M2` / `∅lit` null claim and
the `SANITARY_HIGH_TOUCH_AREA_M2_PER_WC` row of
[`../parameter_provenance_register.md`](../parameter_provenance_register.md).

**Retrieval.** Consensus MCP, full-text chunks on, nine differently-phrased
queries (§5). Each number below records where in the paper it was read.

---

## 1. The quantity the model needs

`_fomite_surface_area(zone)` returns one number per zone class, and the pool's
mass enters a touch only as `mass / A`:

```
request = contacts × (used_fraction × hand_area_m2 / A) × efficiency × mass
```

So `A` must be: **the total area of the surfaces a zone's occupants actually
touch, over which the zone's deposited mass is assumed uniformly spread.**
Three things it is not: floor area, total room surface area, and the swabbed
area of a sample. The shipped table is cabin 1.5, dining 8.0, public 6.0,
galley 10.0, crew_mess 4.0 m², sanitary 0.5 m² per water closet.

An important structural fact about how it is *applied*: `cabin` is resolved
per **stateroom compartment** (2 berths → 0.75 m²/person), while `dining` and
`public` are resolved per **zone** — a 400-seat main dining room and a
444-occupant lounge each get one 8.0 / 6.0 m² pool (0.02 / 0.014 m²/person).
The declared table is therefore not scale-consistent: the same class constant
spans units differing by two orders of magnitude in occupancy.

## 2. What has been measured — three kinds, none of them `A`

### 2.1 Total room surface area (an upper bound, measured)

* **Manuja et al. 2019**, *Environmental Science: Processes & Impacts*, DOI
  10.1039/c9em00157c. Surface area, volume, shape and material of objects in
  **10 bedrooms, 9 kitchens, 3 offices** at ~1 cm resolution. Surface-to-volume
  ratio **3.2 ± 1.2 m⁻¹ with contents**, **1.8 ± 0.3 m⁻¹** without; contents
  add ~78 % (**Abstract**; `Ab`).
* **Hodgson et al. 2005**, LBNL, DOI 10.2172/861239. **33 rooms in 9
  residences**, objects ≥ 300 cm² measured by category; bedroom S/V
  **2.3–4.7 m²/m³** (**Abstract/Results**; `Ab`).

These are *total* surface, residential, not maritime. They bound `A` from
above and nothing more: a room cannot present more touchable area than it has
area.

### 2.2 High-touch item sets (a countable list, observed)

* **Huslage et al. 2010**, DOI 10.1086/655016 — 50 observed HCW–patient
  interactions yield **five** high-touch surfaces (bed rails, bed surface,
  supply cart, over-bed table, IV pump) (**Abstract**; `Ab`).
* **Murphy et al. 2011**, DOI 10.1071/hi11024 — **seven** predefined
  high-touch objects per room, 37 rooms, 986 fluorescent marks (**Abstract**;
  `Ab`).
* **Heo et al. 2023**, DOI 10.53713/nhsj.v3i2.242 — a **38-item** high-touch
  list compiled from prior studies and guidelines, ranked by *self-reported*
  frequency by 122 nurses and 56 patients (**Abstract**; `Ab`). Questionnaire,
  not observation: it bounds the *list*, not the frequency.
* **Cheng et al. 2015**, DOI 10.1016/j.jhin.2014.12.024 — 6,144 contact
  episodes over 66 h in a six-bed cubicle; 93.1 episodes/h; bedside rails
  13.6/h, tables 12.3/h (**Abstract**; `Ab`).
* **Jin et al. 2022**, DOI 10.1016/j.ijid.2022.05.047 — **41,042 touches**
  video-coded in a Guangzhou restaurant; diners 449.9 touches/h, staff 761.0;
  the surface *classes* (personal private, table public-use, common
  public-use) are the restaurant analogue of a dining zone's item set
  (**Methods, Results**; `R`).
* **Lei et al. 2017**, DOI 10.1038/s41598-017-13840-z — an explicit touchable
  surface **inventory** for a public seating space: **422 surfaces** in a
  21-row 737 economy cabin (42 aisle seatbacks, 84 non-aisle seatbacks, 126
  tray tables, 168 armrests, 2 toilets) = **3.3 touchable surfaces per seat**
  (**Methods/Table 1**; `R`).
* **Carling et al. 2009**, DOI 10.1086/606058 — the only shipboard count:
  **8,344 objects in 273 public restrooms on 56 cruise ships** = **30.6
  evaluated objects per shipboard public restroom** (already in the register
  for its 37 % thoroughness figure).
* **Spitzer 2025** (DOI 10.1016/j.ijheh.2025.114586) and **Ackerley 2025**
  (DOI 10.1177/17579139251371964) — hotel-lobby tracer and 30 h of
  observation; hospitality-setting hotspot identification, item lists again,
  no areas.

### 2.3 Per-item areas (measured for a handful of objects)

* **Park et al. 2015**, DOI 10.1128/aem.01657-15 — norovirus swab protocol
  development **and a cruise-ship field campaign** (92 samples, 3 case cabins
  + common areas, 18.5 % GII positive). Sampling surfaces: stainless coupons
  **645.0 cm²**, **toilet seat 700 cm²**, swabbed areas **25.8–645 cm²**
  (**Abstract, Results**; `R`). The 700 cm² toilet seat is the one high-touch
  *object* area in this tranche measured on the kind of fixture the hull
  models.
* **Gerba et al. 2025** — restroom sampling areas from **10 cm²** (toilet
  flush handle) to **385–500 cm²** (restroom floor), normalised per 100 cm²
  (**Methods**; `Ab`).
* **Weir et al. 2016**, DOI 10.1021/acs.est.5b06275 — a fomite QMRA that
  *declares* its object areas: aluminium **0.017 ft² = 15.8 cm²**, plastic
  laminate **0.638 ft² = 593 cm²**, wood laminate **11.25 ft² = 1.05 m²**;
  fingertip-per-touch area **0.0108 ft² = 10.0 cm²** over ten fingers
  (**Methods, eqs for hand↔fomite loss**; `R`). Their sensitivity analysis
  ranks **fomite surface area the second most influential parameter** in the
  model, after initial loading (**Discussion**; `R`) — an independent
  corroboration of this repository's own finding that the denominator, not
  the efficiencies, carries the dose.
* **Zambrana et al. 2023**, DOI 10.1021/acsenvironau.3c00025 — across **275
  data sets**, 26 % swabbed **< 50 cm²**, 23 % **50–100 cm²**, 12 % **> 100
  cm²**, 39 % unreported (**Results**; `R`). Swabbed area is a protocol
  choice, not an object area, but it fixes the *scale* at which fomites are
  treated as units: tens to hundreds of cm².
* **Wilson et al. 2021**, DOI 10.1038/s41370-021-00398-2 — spatial averaging
  of contamination: dose is greatest when hands and surfaces are each two
  compartments, and increasing the surface area over which contamination is
  averaged **dilutes concentration and lowers estimated dose** (**Abstract**;
  `Ab`). This is the model-structure statement of the same `1/A`
  sensitivity, and a caution that the hull's *uniform* zone pool is itself an
  assumption on top of the value of `A`.

## 3. What is absent

No retrieved source reports the summed area of the touched surfaces of a
room, in any setting — hospital, hotel, restaurant, aircraft or ship. Nine
queries (§5), including two phrasings aimed directly at it ("area of high
touch surfaces per hospital patient room square metres", "whole surface area
of each fomite … entire surface swabbed"), returned item lists, touch
frequencies, swab areas and total room areas, and no summed high-touch area.
Recorded as **∅nr** (not reported) for the general quantity and **∅lit** for
the cruise-hull zone classes specifically — not as "never measured", which is
what the code said and what this tranche retires.

## 4. The derived envelope

`tools/noro_diag/high_touch_area_envelope.py` multiplies the enumerated item
sets of §2.2 by the item areas of §2.3, evaluated against the actual
`classic_cruise_1900` zone occupancies and volumes, under two readings of
"high touch":

* **hardware** — hand-contact hardware only (handles, switches, taps, flush
  actuators, seats, rails, remotes, buttons, utensils, place settings). This
  is the reading the shipped sanitary constant's own comment uses.
* **broad** — hardware plus the touched planes of furniture (table tops, chair
  seats and backs, desks, counters): what an observational study marks as
  touched at least once.
* **ceiling** — §2.1's S/V 3.2 m⁻¹ on the zone's declared air volume. Not a
  target; an impossibility bound.

| zone class | unit | rep. occ. | shipped A (m²) | hardware (m²) | broad (m²) | ceiling (m²) | × to hardware | × to broad |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| cabin | one stateroom compartment (2 berths) | 2 | 1.50 | 0.17 | 1.92 | 128 | 0.12 | 1.28 |
| sanitary | one water closet | 1 | 0.50 | 0.14 | 0.46 | 85 | 0.29 | 0.92 |
| dining | one dining zone | 365 | 8.00 | 7.46 | 105.99 | 4088 | 0.93 | 13.25 |
| crew_mess | one crew mess zone | 200 | 4.00 | 4.12 | 58.12 | 2240 | 1.03 | 14.53 |
| public | one public zone | 444 | 6.00 | 3.37 | 69.90 | 7535 | 0.56 | 11.65 |
| galley | one galley zone | 60 | 10.00 | 0.50 | 19.31 | 2880 | 0.05 | 1.93 |

Seven of the seventeen item areas are `declared` (this repository's geometry
for an object nobody measured); the rest are `measured` or `qmra`. That
declared share is the residual Grade C content of the envelope and the reason
it is reported as a range with two readings rather than as a value.

**Finding F45-1 — the shipped table is not internally consistent in its
definition of "high touch".** Read as *hardware*, the shared zones are
approximately right (dining ×0.93, crew_mess ×1.03, public ×0.56) and the
cabin is ~8× too large (×0.12). Read as *broad*, the cabin and sanitary
constants are approximately right (×1.28, ×0.92) and the shared zones are
an order of magnitude too small (×11.7–14.5). There is no single definition
of "high touch" under which the whole table is defensible. Since dose ∝ 1/A,
the choice of definition is worth a factor of ~10 on the fomite dose in the
zones where most contacts happen.

**Finding F45-2 — every entry sits far below its ceiling** (shipped/ceiling
0.0002–0.012), so no entry is refuted by the measured room inventories. The
envelope is bounded below by enumeration, not above by geometry.

**Finding F45-3 — the per-person denominator varies ~40× across the table**
(cabin 0.75 m²/person vs dining 0.022, public 0.014). Under any item-based
reading, area scales with occupants and fittings; a per-zone-class constant
applied to units spanning 1–444 occupants cannot do that. This is a structural
property of the declaration, not a calibration error, and it is what makes a
*per-zone-class* sweep arm necessary rather than a single global multiplier.

Nothing in §4 is adopted. The engine's constants are unchanged; the sweep
knobs `transmission.high_touch_area_scale` and
`transmission.high_touch_area_scale_by_zone_class` default to the shipped
declaration.

## 5. Retrieval record

| Query | Filters | Outcome |
|---|---|---|
| "total surface area indoor environments measured objects rooms m2" | full-text chunks | Manuja 2019 `Ab`, Hodgson 2005 `Ab` — total area, not high-touch |
| "quantitative approach defining high touch surfaces hospitals" | full-text chunks | Huslage 2010 `Ab` — 5 surfaces, no areas |
| "hand-touch contact high touch mutual touch surfaces healthcare workers patients visitors" | full-text chunks | Cheng 2015 `Ab` — frequencies, no areas |
| "high touch object cleaning thoroughness fluorescent marker hospitals" | full-text chunks | Murphy 2011 `Ab` — 7 objects/room |
| "surface transmission Markov model restaurant surface areas of each object … Zhang 2021" | full-text chunks | Jin 2022 `R` — 41,042 touches, surface *classes*, no areas |
| "area of high touch surfaces per hospital patient room square meters UV disinfection surface area treated" | full-text chunks | Resendiz 2023 `R` — surface *types* only; **no summed area** |
| "whole surface area of each fomite sampled toilet seat flush handle light switch door handle cm2 entire surface swabbed" | full-text chunks | Zambrana 2023 `R` (swab-area distribution), Park 2015 `R` (toilet seat 700 cm²) |
| "surface area of touched objects in aircraft cabin train public transport high touch square centimeters inventory" | full-text chunks | Lei 2017 `R` — 422-surface inventory, counts not areas |
| "QMRA fomite model assumed total surface area of fomite square meters … parameter value" | full-text chunks | Weir 2016 `R` — declared object areas + area is 2nd-ranked sensitivity |
| "cruise ship cabin stateroom surfaces sampled norovirus outbreak fomite inventory objects per cabin" | full-text chunks | Park 2015 `R` cruise campaign; Mouchtouri 2024 (review, no areas) |

`Ab` = abstract only; `R` = retrieved full-text chunk; `∅nr` = searched, not
reported; `∅lit` = no literature for this exact quantity.
