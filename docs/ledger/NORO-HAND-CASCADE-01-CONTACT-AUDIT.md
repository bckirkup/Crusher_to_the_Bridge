# NORO-HAND-CASCADE-01-CONTACT-AUDIT
**Date:** 2026-11-14
**Commit:** 0bcfca80
**Pathogens:** norwalk_gi
**Status:** open
**Measured at:** 0bcfca80

Scope: audit the constants a per-contact / fast-chain continuous-event
contamination solver would need, after the DS-M posted pilot showed fixed-M
substeps are not converged through M=12 and after the CE comparator proposal was
written. This entry changes no engine code, adds no constant, and fits nothing
to VSP, Park, attack-rate, or passenger/crew anchors. It re-reads the parameter
provenance register and the contact/food/fomite literature tranches; it does
not make new literature claims.

## Bottom line

The transfer-efficiency legs are comparatively well sourced. The binding gaps
for a literal per-contact CE are **geometric and behavioural**, not the
hand/surface transfer fractions:

1. **Areal/contact geometry is the dominant unmeasured layer.** The summed
   high-touch area per room is still a declared assumption, the shipped
   per-zone-class values are internally inconsistent under the two observational
   readings of "high touch", and the per-person denominator varies by ~40x across
   the table. Per-item touch shares for ship zone classes are mostly unretrieved.
2. **Food contact is the weakest rate leg.** Bare-hand contacts with communal
   food per person per unit time remain a narrowed literature null; the handler
   multiplier is inferred across contact type; there is no per-shift food-handler
   shedding probability and no commodity/serving/gram structure outside the
   common-source arm.
3. **If CE agrees with M=1, the next suspect is upstream contact architecture.**
   Person-to-person contact rates are not cruise-measured under ordinary
   operations; the uniform fallback is POLYMOD 13.4/day, and activity-specific
   rates require run declaration because no engine defaults exist.

Measured/inferred: staged aggregate CE can reuse the existing kernels without
new fitted constants. Hypothesis: a literal per-contact CE cannot be implemented
faithfully without either new Grade C declarations or an explicit structural
choice; do not implement it yet.

## What is already sourced enough to reuse

| Layer | Current shipped form | Status in tree / register |
|---|---|---|
| surface → hand transfer efficiency | `SURFACE_TO_HAND_LOGNORMAL(-2.1, 1.4)` | Grade B interval for non-porous donors; no maritime setting and no human-NoV infectivity measurement anywhere, so B is the ceiling. Tranche 12/44 and register §3.1. |
| hand → surface transfer efficiency | `HAND_TO_SURFACE_LOGNORMAL(-2.1, 1.4)` | Same Grade B ceiling; splits wet vs dried by orders of magnitude, and the shipped distribution is a wet-contact parameterisation. Tranche 12/44. |
| hand → mouth transfer efficiency | `HAND_TO_MOUTH_NORMAL(0.339, 0.132)` | Mean traces to Rusin 2002 PRD-1; SD is untraced (F44-1). Grade B ceiling. |
| mouth-contact used fraction / hand area | `MOUTH_CONTACT_FRACTION_RANGE`, `HAND_AREA_CM2_RANGE` | F44-2/F44-3: mouth fraction reconstructs as an adult fingertip derivation ~10x below the only measured child FSA; hand area is a male-only band biased ~10-15% high for a mixed population. |
| shared-surface touch rates | `SURFACE_CONTACTS_PER_HOUR` by zone class; `CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR = 545.4` | Grade B restaurant/lobby/dormitory analogues for cabin/public/dining/galley/crew_mess; `sanitary` is a borrowed public rate, Grade C. Jin 2022 staff:diner shared-surface ratio is 12.7x. |
| mouth contacts | `NON_EATING_MOUTH_CONTACTS_PER_HOUR`, `EATING_MOUTH_CONTACTS_PER_HOUR` | Wilson 2020 observation, Grade B for hand-to-mouth during eating; used as the ingestion leg, not as a food-contact rate. |
| per-surface inventory | `engines/fomite_surfaces.py` item classes/counts/areas; `fomite_touch_share = areal|declared` | Item areas are partly measured/QMRA and partly declared; default touch share is areal (`count*area/total`), with an optional declared share table. This is item-class state, not an event process. |
| sanitary dwell/void rates | `SANITARY_DWELL_SECONDS`, `SANITARY_VOIDS_PER_DAY/NIGHT` | Grade B airport/public-restroom analogues; fixture choice, queuing, and within-visit touch sequence are structural, not measured. |

## Missing or blocking constants for per-contact CE

| Needed quantity | Current evidence state | Consequence for CE |
|---|---|---|
| Summed high-touch area per room / zone class | **∅nr/∅lit** after tranche 45/46. No retrieved source reports summed high-touch area for any room. The shipped `HIGH_TOUCH_AREA_M2` is Grade C declared; the derived envelope is not adopted. Hardware vs broad readings leave the table internally inconsistent: cabin is ~0.12x hardware but ~1.28x broad; shared zones are ~0.56-1.03x hardware but ~11.7-14.5x broad; per-person area varies ~40x. | The areal denominator dominates fomite dose (`dose ∝ 1/A`). A per-contact CE cannot choose item areas or pinch-point pools without either adopting a declared inventory or sweeping a frozen Grade C interval. |
| Per-item / per-class touch shares by ship zone class | Mostly **?nr/∅**. Jin 2022 gives restaurant T/R class rates; Ackerley 2025 gives partial lobby shares (elevator button/front desk 32%/22%); tranche 47 found no usable per-class shares for sanitary, cabin, galley, or crew_mess. | The engine knows aggregate contacts/hour and an optional declared share table, but not which surfaces those contacts hit. Without shares, a per-contact solver must invent the assignment of 42.8 dining or 545.4 service contacts/h to specific items. |
| Contact event order and sequential depletion | **Structural, unmeasured.** Current pooled path computes simultaneous requests and scales by `_delivery_scale`; per-contact CE needs an order/tie rule and atomic depletion. No literature measures contact order within a zone-hour. | This is a model-structure choice, not a constant. It requires a paired-seed witness comparing simultaneous rationing vs sequential/permuted depletion before adoption. |
| Hand wet/dry state dynamics | Transfer efficiency is strongly moisture-dependent (~100x drying lever on hand→surface). Shipped `HAND_TO_SURFACE_DRYING_MULTIPLIER = 1.0` is neutral; the hygiene-cycle arm has wash/stool/self-contact rates, but per-contact moisture state after each touch is not measured. | A per-contact CE needs a state transition rule for hand wetness/drying between events. That rule can be declared, but it is Grade C unless bounded by the existing drying axis. |
| Bare-hand food-contact rate | **∅ null, narrowed.** `FOOD_HAND_CONTACTS_PER_DAY = 0.6` is a declared sweep axis, plausibly low by ~10-20x against hand-to-mouth during eating and hand-hygiene occasions; neither analogue measures hand→food contact. | The food leg of the fast chain cannot be sized from evidence. Per-contact CE would need diner and handler food-contact rates per meal/shift, plus item/serving structure. |
| Food-handler shedding/work-while-ill probability | **Bounded, not adoptable.** Work-while-ill prevalence is Grade B in analogous food service (Sumner 2011, Carpenter 2013, Norton 2015), but it is 12-month worker-level recall, not per-shift; the model has no food-handler shift concept. `FOOD_HANDLER_CONTACT_MULTIPLIER = 12.7` is inferred across contact type. | A handler-amplified CE arm needs a per-shift probability or a declared shift state; without it, the handler channel is a multiplier on an already-null contact rate. |
| Food item / serving / provisioning structure | Commodity prevalence and titre exist for source-contaminated product (EFSA/Dirks/produce rows), but servings, grams per serving, and per-zone food inventory are model-side and absent outside `FOOD-COMMON-SOURCE-01`. | Per-contact food CE needs a food-pool item structure (pan/serving/item mass) or it remains a well-mixed pool with a declared ingestion/turnover rate. |
| Sanitary fixture assignment and within-visit touch sequence | Dwell and void rates are Grade B; sanitary surface touch rate is borrowed public Grade C; per-WC high-touch area is declared; no queuing or fixture-choice measurement was retrieved. | Sanitary CE events need declared rules for which fixture a visit touches and in what order; the aggregate dwell share is not a per-contact process. |
| Upstream person-contact architecture | `POLYMOD_CONTACTS_PER_DAY = 13.4` is a general-population control, Grade C for this setting. `activity_contacts` has no engine defaults and requires all eight activity rates to be declared. Pung 2022 is the only cruise sensor record and is a COVID-era floor (passengers ~20/day, crew ~10/day); cabin, corridor/transit, and covers-per-server rates remain null. | If the residual is behavioural rather than solver error, the binding constants are these contact counts and schedules, not the contamination transfer efficiencies. |

## Stop rule and next decision

Stop escalating solver resolution. The fixed-M pilot already showed no
convergence through M=12; CE should not be implemented as a per-contact model
until the gaps above are resolved one of two ways:

- **Declared-design route:** freeze a bounded per-contact representation —
  item inventory, touch shares, hand wetness state, food-contact rates,
  sequential-depletion rule — as Grade C/declaration axes with provenance
  comments, paired-seed witnesses, and no anchor fitting; or
- **Binding-constant route:** first measure which upstream contact/behaviour
  constants are binding (active-set size, event counts, hand occupancy vs Liu,
  carrier mass entering food/pan, sanitary visits/dwell realised, food-handler
  vs diner split, per-route delivered mass) before adding a new contamination
  representation.

Recommended next decision: do **not** implement per-contact CE yet. Choose
between the declared-design route and the binding-constant diagnostic route;
either way the audit's central result is that the missing layer is mostly
geometry/behaviour/food-contact structure, not the hand-transfer efficiencies.
