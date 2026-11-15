# FOOD-SUPPLY-01 — provisioning receipt/lot layer design

**Status: frozen design — declared before implementation.** This is a
mechanism contract for a later implementation leg; this PR contains no
engine change. It extends `PROVISIONED-SOURCE-01`
([provisioned_source_01_design.md](provisioned_source_01_design.md)) and
`FOOD-COMMON-SOURCE-02`
([food_common_source_02_design.md](food_common_source_02_design.md)); the
pan remains the bounded exposure unit and the `common_source_events`
row contract is unchanged.

**Branch:** off `origin/main` at `191c4ce9`.

## 0. The question this contract answers

Benjamin's framing (2026-11-15): how many supply classes are boarded by
ships of different sizes, what is the distribution of scales, how many
are subject to norovirus contamination that would survive meal
preparation under realistically imperfect food safety, and how to model
that process effectively.

The measured current state is narrower than that process:

- The provisioned-lot mint is a **station census**: served Dining
  venues × `COMMON_SOURCE_LOT_ITEM_LINES` = 21/35/63/70 stations on
  exp/cls/spr/mega. Ship size changes venue count, not supply-class
  composition. The seven item lines are traceability labels with no
  rate effect. `engines/transmission_core.py::_cs_station_census`
- `q_source` is one hull-invariant scalar applied to every station. The
  shipped registry entry is a sourced composite for
  `generic_cruise_port`, [8.6e-4, 4.7e-3], built as mean per-line RNA
  prevalence × implicated-titre share f = 0.141. `data/config/provisioning_sources.json`
- Tranche 55 already shows the scalar is a mean, not a composition:
  shellfish/salad-leaf/fresh-produce have sourced high-income
  prevalences; deli/bakery/dairy/garnish are ∅ and carried at zero.
  It also records the three residual gaps this design must close:
  every venue serves every line, stations are independent across
  venues, and lots are independent across voyages. [`consensus_tranche_55_provisioned_lot_prevalence.md`](literature/consensus_tranche_55_provisioned_lot_prevalence.md)
- The food-handler channel is real and common but has no shift
  representation; the operational food-service literature measures
  imperfect hygiene, not perfect compliance. [`consensus_tranche_30_food_deposition_channels.md`](literature/consensus_tranche_30_food_deposition_channels.md)

Inferred defect: the current provisioned-lot arm can represent "some
food arrives contaminated" but cannot represent *which* supply class,
*what scale*, *whether one receipt feeds several venues*, or *whether
the item is the kind that remains infectious after normal meal
preparation*. That is exactly the upstream-tail question for the mega
cruise: the tail may need per-line prevalence, shared/multi-item
receipts, and service-eligible preparation classes, not more total
mass.

## 1. Supply vocabulary

The item-line vocabulary stays the shipped seven:

`shellfish`, `salad_leaf`, `fresh_produce`, `deli`, `bakery`, `dairy`,
`garnish`.

Each line is annotated with two **categorical** attributes. These are
not rates and carry no fitted value:

| attribute | values | meaning |
|---|---|---|
| `supply_stratum` | `raw_produce`, `shellfish`, `prepared_rte`, `garnish_unit` | procurement/handling stratum for witnesses and source-id mapping |
| `preparation_class` | `raw_or_rte_no_kill`, `prepared_or_pasteurized` | whether the item’s normal meal-preparation path has a kill step that could reduce a provisioned lot’s infectious dose |

Proposed mapping, Grade C declared classification (not a prevalence or
survival measurement):

| item_line | supply_stratum | preparation_class | provisioned-lot service eligibility |
|---|---|---|---|
| `shellfish` | `shellfish` | `raw_or_rte_no_kill` | eligible — sourced implicated items are oysters served raw/undercooked; cooked-shellfish service would need a menu/preparation attribute and a sourced survival factor |
| `salad_leaf` | `raw_produce` | `raw_or_rte_no_kill` | eligible |
| `fresh_produce` | `raw_produce` | `raw_or_rte_no_kill` | eligible |
| `garnish` | `garnish_unit` | `raw_or_rte_no_kill` | class eligible, prevalence ∅ for the high-income stratum — mints only if a source declares a nonzero per-line prevalence |
| `deli` | `prepared_rte` | `prepared_or_pasteurized` | not eligible for infectious provisioned lots unless a preparation-survival factor is sourced |
| `bakery` | `prepared_rte` | `prepared_or_pasteurized` | not eligible for infectious provisioned lots unless a preparation-survival factor is sourced |
| `dairy` | `prepared_rte` | `prepared_or_pasteurized` | not eligible for infectious provisioned lots unless a preparation-survival factor is sourced |

This is the "survive meal preparation" filter. It is deliberately
conservative: provisioned lots mint infectious `provisioned_lot`
objects only for raw/RTE-no-kill classes with nonzero sourced
prevalence. Prepared/pasteurized lines remain reachable through the
existing `ill_handler` / `ill_diner` arms, which is where the
literature puts most RTE-food norovirus risk anyway
(47 food-handler vs 27 source-contaminated outbreaks in Hardstaff’s
review; ~40% of retail foodborne outbreaks with identified factors
implicated an ill/infectious worker). [`consensus_tranche_30_food_deposition_channels.md`](literature/consensus_tranche_30_food_deposition_channels.md)

Ship size still enters only through the venue footprint: more served
Dining venues means more service points and more chances for a receipt
to be allocated, but there is no evidence for hull-specific supply
classes. Per-venue menu data does not exist in the platform JSON;
recorded as a gap, not filled by assumption.

## 2. Mechanism: receipts and lots, not only stations

FOOD-SUPPLY-01 adds a supply layer upstream of the existing
`provisioned_lot` object. The object remains the thing that emits pans;
the new objects are **receipts** and **lots**.

- **Receipt** — one provisioning delivery for an `item_line` at
  embarkation, carrying `receipt_id`, `source_id`, `source_stratum`,
  `item_line`, `scale_class`, `quantity_servings`, `quantity_g`,
  `venues_served`, `shelf_life_days`, and contamination state.
- **Lot** — the contaminated or clean batch inside a receipt. One
  receipt may carry one lot per item line; a contaminated lot mints one
  `provisioned_lot` object. Clean lots mint nothing, as today.

`scale_class` is a categorical witness/stratification label, proposed
as `bulk_raw` for shellfish/salad_leaf/fresh_produce, `prepared_rte`
for deli/bakery/dairy, and `garnish_unit` for garnish. It has no rate
effect. Quantity remains `lot_servings` log-U[30, 600] servings
(Grade C documentary placeholder) until commodity-specific quantity
distributions are sourced; `quantity_g` is derived as
`lot_servings × serving_mass_g` for mass-conservation witnesses, not a
new independent draw.

Receipt count is the honest gap. Real provisioning is not one lot per
venue×line: Rispens 2020 documents one frozen-raspberry lot supplied an
entire fleet for months, but that is an outbreak record, not a
per-receipt distribution. The design therefore declares receipt-count
modes rather than inventing a procurement census:

| mode | meaning | status |
|---|---|---|
| `station_lots` | current PROVISIONED-SOURCE-01 semantics: one lot per served venue×item station | shipped baseline |
| `single_line_receipt` | one receipt per service-eligible item_line per voyage, shared across that line’s venues | bounding arm for shared-lot correlation |
| `declared_receipts` | N receipts per item_line drawn from a declared Grade C interval | sweep arm until procurement data exists |

Venue allocation for a shared receipt is deterministic in v1 of this
layer: the receipt’s `venues_served` is the set of served Dining zones
whose station census includes the item line, and emission chooses among
those venues by the existing served-window demand order. Weighted
venue allocation is a later arm if witnesses show allocation matters.

## 3. Prevalence: per-line composition, same total expectation

The registry gains an optional per-line block alongside the legacy
scalar:

```json
"q_source_by_item_line": {
  "shellfish":     {"prevalence": [0.039, 0.144], "implicated_share": 0.141},
  "salad_leaf":    {"prevalence": [0.0,   0.053], "implicated_share": 0.141},
  "fresh_produce": {"prevalence": [0.0036,0.036], "implicated_share": 0.141},
  "deli": null, "bakery": null, "dairy": null, "garnish": null
}
```

`null` means no shipped high-income prevalence; the line does not mint
infectious provisioned lots. A source may declare a nonzero value for a
currently-null line only with new evidence and a register entry.

Per-line service-eligible prevalence is

```
q_line = prevalence_line × implicated_share_line
```

drawn once per voyage per line in canonical item-line order. Under the
shipped common f = 0.141, `Σ_line q_line` equals `7 × q_source` for the
current composite interval, so the **total expected contaminated-station
count is preserved**; the change is compositional — shellfish and
produce carry the risk, null lines stop minting by accident. If a
future source declares line-specific `implicated_share` values, the
expectation is preserved only after re-checking the aggregate; that
re-check is an integrity gate, not a fit.

Campaign rungs sweep a dimensionless `prevalence_scale` multiplier on
all `q_line` values, not the absolute per-line intervals. Absolute
per-line intervals are sourced composition; the scale is the declared
sweep axis. This keeps nested-draw integrity: at shared seeds, a lower
scale rung’s contaminated set is a subset of a higher scale rung’s set
when per-line uniforms are consumed in canonical (receipt/lot, item_line)
order.

## 4. Preparation-survival filter

`preparation_class` decides whether a contaminated lot is
service-eligible, not how much titre survives. Two modes:

- `raw_rte_only` (proposed shipped mode for `receipts`): only
  `raw_or_rte_no_kill` lines mint infectious `provisioned_lot` objects.
  `prepared_or_pasteurized` lots may be witnessed as RNA-positive
  receipts but mint no infectious object.
- `declared_factors`: a later arm may apply a sourced per-line
  `preparation_survival_factor` to `lot_titre_gec_per_g` before service.
  No such factor is shipped here; cooking/pasteurization kill-step
  values for norovirus are not commensurately sourced in tree, and
  tranche 29 records persistence on produce but not a preparation
  reduction factor. [`consensus_tranche_29_food_and_environmental_deposition.md`](literature/consensus_tranche_29_food_and_environmental_deposition.md)

This filter is the model’s answer to "would survive meal preparation":
raw/RTE items pass by construction; prepared/pasteurized items are
excluded from the supply-chain infectious mint until a kill-step or
survival measurement exists. It is not a fitted reduction.

## 5. Food-safety realism boundary

This layer does not make food safety perfect or imperfect by itself.
Imperfect implementation enters through the existing arms and their
declared limits:

- `ill_handler` / `ill_diner` objects carry the RTE-food risk that the
  provisioned-lot arm should not double-count.
- `food_safety_posture` remains a per-platform modifier, but the usable
  covariate is violation content / mechanism observables — bare-hand
  RTE contact, handwash compliance, ill-worker exclusion — not the VSP
  numeric score, which Taylor 2018/Dahl 2018 record as null for
  norovirus outbreaks. [`consensus_tranche_30_food_deposition_channels.md`](literature/consensus_tranche_30_food_deposition_channels.md)
- Crew duty exclusion and quarantine/compliance stay in the existing
  outbreak-response layer; tranche 33 records the compliance share as
  ∅ null and the maritime arm as unmeasured, so it remains a swept
  bounded axis, not a value. [`consensus_tranche_33_crew_duty_exclusion.md`](literature/consensus_tranche_33_crew_duty_exclusion.md)

## 6. Witness fields

Existing `common_source_events` / `common_source_exposures` rows stay
unchanged. The supply layer adds:

- Voyage block `common_source.provisioned_source` gains
  `lot_layer_mode`, `n_receipts`, `n_lots`, `n_contaminated`, and
  `contaminated_by_item_line` / `contaminated_by_preparation_class`.
- Lot object rows gain `receipt_id`, `lot_id`, `item_line`,
  `supply_stratum`, `preparation_class`, `scale_class`,
  `quantity_servings`, `quantity_g`, `venues_served`,
  `preparation_survival_mode`, and `service_eligible`.
- Receipt rows are emitted for clean and contaminated receipts alike:
  `receipt_id`, `source_id`, `source_stratum`, `item_line`,
  `quantity_servings`, `quantity_g`, `venues_served`, `contamination`
  ∈ {`none`, `rna_positive_noninfectious`, `infectious`}.
- Telemetry adds counts by `item_line`, `supply_stratum`,
  `preparation_class`, `scale_class`, and receipt-count mode, plus the
  derived `q_source_equivalent = (1/7) Σ_line q_line` for continuity
  with PROVISIONED-SOURCE-01 readouts.

## 7. Integrity gates and admissibility

1. **Baseline bit-identity** — `lot_layer_mode: "station_lots"` and the
   existing `"fiat"` path remain bit-identical to current main at
   shared seeds; `mode: "off"` draws nothing.
2. **Expectation preservation** — under common `implicated_share`,
   `Σ_line q_line = 7 × q_source` for the shipped composite interval;
   per-line witnesses must show the same total contaminated-station
   expectation within binomial tolerance while changing the item-line
   composition.
3. **Nested rungs** — `prevalence_scale` rungs preserve contaminated-set
   nesting at shared seeds; a lower-scale contaminated lot absent at a
   higher scale is a stream-layout defect.
4. **Mass conservation** — for every lot object,
   `Σ credited dose ≤ lot_titre × serving_mass × quantity_servings`;
   receipt rows must reconcile clean/contaminated counts to the voyage
   census.
5. **External checks, not targets** — report food-involved outbreak
   share against Mouchtouri 2024’s 7.3–32% bound and food-vehicle
   voyage frequency against the VSP/Freeland bound (~3–7e-4/voyage),
   plus the tranche-55 plausibility warning that RNA-positive is not
   synonymous with infectious/implicated. No constant may be moved to
   make those checks pass.
6. **Invariants** — handler/diner arms, pan cohort/take-share/pan
   serving mechanics, dose-response, reporting, quarantine, and all
   non-food routes are unchanged; medians should not move, only the
   supply-chain tail composition.

## 8. Non-goals

- No engine implementation in this PR.
- No anchor fitting and no default flip: `lot_layer_mode` ships as a
  labelled arm until witnesses and the canary readout justify a default.
- No per-venue menu inference; `venues_served` comes only from the
  existing served-Dining census.
- No mid-voyage restock cadence; receipts board at embarkation inside
  the existing lot window unless a later design adds provisioning
  events.
- No commodity-specific quantity distribution until sourced; `scale_class`
  is a label, not a rate.
- No preparation-survival numeric factor until a kill-step or survival
  measurement is sourced; `raw_rte_only` is the conservative default.
- No VSP-score-to-parameter mapping; violation content may inform
  declared mechanism observables only.
