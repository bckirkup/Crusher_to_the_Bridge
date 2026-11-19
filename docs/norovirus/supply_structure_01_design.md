# SUPPLY-STRUCTURE-01 — cruise food-supply structure design (frozen contract)

**Status: Stage A census support implemented; Stage B not started.** This is
the mechanism contract plus the implemented supply-side census leg:
`provisioned_source.supply_structure` carries the labelled
`source_cluster` / `venue_menu` / `lot_scale` arms over the shipped station
census, with supply-side witnesses and no posting endpoint. Flat remains
the default and the absent block is bit-identical. The Stage B targeted
ABM confirmation campaign has not been run.
It extends `PROVISIONED-SOURCE-01`
([provisioned_source_01_design.md](../provisioned_source_01_design.md)),
`FOOD-SUPPLY-01`
([food_supply_01_design.md](../food_supply_01_design.md)), and the
sourcing survey
([cruise_food_supply_sourcing_survey_2026_11_18.md](cruise_food_supply_sourcing_survey_2026_11_18.md);
literature tranche
[consensus_tranche_57_cruise_food_supply_chain.md](../literature/consensus_tranche_57_cruise_food_supply_chain.md)).

**Branches:** design off `origin/main` at `1721539b` (#1318); Stage A
implementation off `origin/main` after #1318.

## Stage A implementation status

- Implemented in `engines/transmission_core.py`:
  `provisioned_source.supply_structure` resolution, `venue_menu`
  service-class station filtering, `source_cluster` cluster-level
  Bernoulli draws, and `lot_scale.servings_multiplier` on provisioned
  lots; witnesses are emitted on `provisioned_source` and closed
  `common_source_objects` rows.
- `tools/noro_diag/supply_seed_scan.py --structure` selects the census
  arm (`flat` default plus the declared rungs below); the seed-scan
  campaign argv hook passes `structure` with a flat default.
- v1 boundary: supply-structure arms run on the `station_lots` census;
  combining an active arm with `single_line_receipt` or
  `declared_receipts` raises explicitly rather than mislabeling the arm.
- Validation: `tests/test_supply_structure_01.py` pins flat identity,
  declared-null echo, venue masks, cluster correlation/all-or-nothing,
  lot-scale serving scaling, and the receipt-layer guard.
- Not done: Stage B ABM cells, fleet posting census, receipt-layer
  composition, cross-voyage correlation, and any default flip.

## 0. The question this contract answers

The supply solver screens showed that the shipped flat supply census is
posting-preserving but solver-unresolved on exp/cls/spr and uninformative
on mega because the frozen burden-quantile seeds rarely cross the
7,000-agent posting threshold. The open modeling question is whether the
real cruise food supply chain changes the *shape* of supply-driven
outbreaks across hull classes through three structural hypotheses:

- **H1 — lot scale:** vendor lots scale with ship size or venue class, so
  a contaminated lot on mega carries more servings/quantity than the
  shipped hull-invariant `lot_servings` draw.
- **H2 — shared upstream source:** lots are bridged by a common upstream
  source/vendor, so contamination correlates across venues, item lines,
  and possibly voyages instead of drawing independently per station.
- **H3 — venue/menu incidence:** high-risk item lines are not served
  uniformly by every Dining venue; buffet/specialty/MDR/crew venues
  differ in which raw/RTE lines they carry, changing where a contaminated
  lot can be served.

The sourcing survey found exactly one measured shared-upstream-lot event
(Rispens 2020: one ~22,000 lb frozen-raspberry lot supplied to an entire
cruise fleet and produced synchronous outbreaks), descriptive industry
evidence that provisioning is centralized and self-sufficient, and no
peer-reviewed measurement of per-venue menu incidence, vendor-sharing
rates, or cruise-specific lot-size distributions. Those unmeasured
quantities are the reason this design is a *structure* contract: it
declares arms and gates, not fitted values.

## 1. Measured inputs (locked, do not re-derive)

- `PROVISIONED-SOURCE-01` mechanism: objects-per-voyage =
  `Binomial(N_lots, q_source)` with `N_lots` = 21/35/63/70 on
  exp/cls/spr/mega and hull-invariant `q_source`; small hulls were
  in-band at one q ≈ 3e-4, mega needed a higher per-lot prevalence window
  (`docs/ledger/PROVISIONED-SOURCE-01.md`,
  `docs/norovirus/norovirus_open_ledger.md`).
- `FOOD-SUPPLY-01` layer: per-item-line prevalence, raw/RTE preparation
  eligibility, `scale_class` labels, and receipt-count modes
  (`station_lots`, `single_line_receipt`, `declared_receipts`). It
  records the residual gaps this design addresses: every venue serves
  every line, stations are independent across venues, and lots are
  independent across voyages.
- Solver screens: `noro_supply_solver_screen_01/02/03` paired
  `discrete` vs `continuous` on stratified supply seeds; posting was
  preserved on exp/cls/spr, quiet controls stayed 0/8, and mega posted
  only 1/16 `station_lots` per solver arm with receipts 0/10.
- Sourcing survey: consumption-side venue diversity rises with hull
  size; procurement is centralized/self-sufficient with turnaround
  loading and at-sea restocking; Rispens 2020 is the measured
  shared-lot bridge; per-venue menu incidence, vendor sharing, and
  cruise lot-size distributions are unmeasured.

## 2. Design principle: partial decoupling

The expensive object is the full-voyage ABM. The supply-structure
question can be decomposed into:

1. **Supply-structure layer** — which receipts/lots exist, how they
   correlate, which venue/role classes can serve them, and how large each
   lot is. This layer is cheap to census and is where H1/H2/H3 live.
2. **In-voyage exposure realization** — the shipped `provisioned_lot`
   object → pan cohort/take-share → food-pool/hand/surface → infection
   → reporting → VSP wire. This stays in the ABM and is not re-derived
   by the supply layer.

SUPPLY-STRUCTURE-01 therefore has two stages:

- **Stage A — supply-structure census/surrogate.** Sample structure arms
  and seeds, emit supply-side witnesses and exposure proxies, and rank
  which hypotheses move the supply-side tail *without* changing the mean
  introduction rate. No posting endpoint is required.
- **Stage B — targeted ABM confirmation.** Run only the arms/hulls that
  Stage A marks as informative, on selected seeds near the posting
  threshold, with the campaign-preflight gate. Quiet controls stay small;
  the goal is AR/timing/role confirmation, not a fleet posting census.

This is the credible alternative to "massive campaigns of quiet mega
cruises": the AR/timing *shape* is learned in Stage A from supply-side
proxies and conditional witnesses, and the ABM is spent only where the
supply side says posting is plausible.

## 3. Mechanism contract (for the later implementation leg)

The existing `provisioned_source` block gains an optional
`supply_structure` sub-block. All three sub-arms are **labelled arms**;
the shipped default remains the current flat census until witnesses and
a canary justify a flip.

```json
"transmission": {
  "common_source": {
    "lot_mint_model": "provisioned_source",
    "provisioned_source": {
      "source_id": "generic_cruise_port",
      "q_source": [0.00086, 0.0047],
      "supply_structure": {
        "mode": "flat",
        "source_cluster": {"scope": "voyage", "item_line_set": "single", "venues_per_cluster": 1},
        "venue_menu": {"service_class_mask": "flat"},
        "lot_scale": {"servings_multiplier": 1.0}
      }
    }
  }
}
```

- `mode: "flat"` is the shipped baseline and must remain bit-identical
  to current main at shared seeds.
- `mode: "declared"` enables the sub-arms below. Sub-arms may be
  combined only in a later factorial design after Stage A shows the
  one-at-a-time effects; v1 arms change one structural axis at a time.

### 3.1 `source_cluster` — H2 shared upstream source

Purpose: represent Rispens-style bridging where one upstream source can
contaminate multiple venues/item lines coherently instead of independent
station draws.

Declared structural rungs (counts are arm labels, not sourced rates):

| rung | meaning |
|---|---|
| `independent` | current baseline: contamination drawn per station/receipt |
| `line_shared` | one contaminated draw per item line shared across that line's venues (already bounded by FOOD-SUPPLY-01 `single_line_receipt`; kept as the reference arm) |
| `venue_group_shared` | contamination drawn per declared venue group × item line, shared across venues in the group |
| `fleet_shared` | bounding arm: one source draw can bridge the voyage's served venues and item lines coherently, the within-voyage analogue of the Rispens fleet lot |

Expectation matching: `q_source` remains the per-*lot* prevalence scale.
For cluster arms, the implementation derives a cluster-level
contamination probability so the **expected contaminated-lot count**
matches the flat arm at the same `q_source` within binomial tolerance.
Correlation may change variance and venue co-occurrence; it may not
change the mean introduction rate. This is a normalization against the
model's own baseline, not a fit to VSP/AR anchors.

### 3.2 `venue_menu` — H3 venue/menu incidence

Purpose: represent the unmeasured fact that high-risk lines are probably
not served uniformly by every Dining venue.

Declared service-class masks (structural, not prevalence values). The
service-eligible infectious lines are `shellfish`, `salad_leaf`, and
`fresh_produce`; `garnish` remains class-eligible but null-prevalence,
and `deli`/`bakery`/`dairy` remain prepared/pasteurized census lines.

| mask | passenger buffet | passenger specialty | passenger MDR | crew mess |
|---|---|---|---|---|
| `flat` | shellfish, salad_leaf, fresh_produce | shellfish, salad_leaf, fresh_produce | shellfish, salad_leaf, fresh_produce | shellfish, salad_leaf, fresh_produce |
| `passenger_raw` | shellfish, salad_leaf, fresh_produce | shellfish, salad_leaf, fresh_produce | shellfish, salad_leaf, fresh_produce | none service-eligible |
| `buffet_specialty` | shellfish, salad_leaf, fresh_produce | shellfish, salad_leaf, fresh_produce | salad_leaf, fresh_produce | none service-eligible |

The masks change **where** service-eligible stations exist, not the
per-line prevalence registry. `none service-eligible` means the venue may
still have census stations, but no infectious provisioned lot can be
served there under `raw_rte_only`.

Expectation accounting: because the infectious line vocabulary is only
those three lines, a mask that removes a venue class necessarily changes
the service-eligible census. V1 therefore treats `venue_menu` as a
structure+frequency arm: Stage A must report
`n_service_eligible_stations`, `E[n_contaminated_lots]`, and allocation
metrics conditional on realized contaminated-lot count, and must not
call a posting/AR move a structure effect unless the frequency component
is separated. A later `menu_normalized` rung may hold service-eligible
incidence fixed, but v1 does not invent that normalization.

### 3.3 `lot_scale` — H1 lot size / servings scale

Purpose: test whether mega's posting dilution is a per-lot yield
problem rather than an introduction-frequency problem.

Declared arm: `servings_multiplier` scales the realized
`lot_servings` draw for contaminated provisioned lots, with
`quantity_g = lot_servings × serving_mass_g` derived as today. Rungs
are arm labels: `{1, 2, 5, 10}`. Multiplier 1 is the shipped baseline.
No absolute serving count is adopted; the multiplier is a sensitivity
axis until commodity/hull lot-size data are sourced.

Expectation matching: contaminated-lot count and per-line prevalence are
unchanged; only per-lot yield changes. This is the cleanest test of the
"lot size scales with ship" hypothesis because it does not touch
introduction frequency.

## 4. RNG / stream contract

- All supply draws stay on the dedicated common-source stream. Baseline
  `flat` must remain bit-identical to current main at shared seeds.
- Structure arms that change *which* lots mint will shift downstream
  realization draws; that is declared and handled by paired-seed
  readout, not bit-identity. Arms that only rescale `lot_servings`
  should avoid consuming extra uniforms so the minted set is unchanged
  at shared seeds.
- Where a scalar rung family exists, contaminated sets must nest in the
  same way the PROVISIONED-SOURCE-01 q-rung gate required: a lower rung
  must not lose a contaminated lot that a higher rung keeps at the same
  seed.
- Paired-seed attribution remains the floor for any Stage B readout; a
  diff that reorders draws is attributed to stream disruption unless a
  predeclared witness isolates the structural change.

## 5. Witness fields

Voyage block `common_source.provisioned_source` gains a
`supply_structure` echo: `{mode, source_cluster, venue_menu, lot_scale}`
plus realized summaries `n_sources`, `n_contaminated_sources`,
`n_receipts`, `n_lots`, `n_contaminated_lots`,
`contaminated_by_item_line`, `contaminated_by_service_type`, and
`contaminated_by_source_cluster`.

Lot/receipt rows gain `source_cluster_id`, `menu_service_type`,
`menu_mask`, `servings_multiplier`, and the existing
`venues_served`/`quantity_servings`/`quantity_g` fields. Receipt rows
already carry `source_id`; cluster arms add the cluster id so a shared
source is visible across venues/item lines.

Stage A telemetry must emit enough to compute the exposure proxies in §6
without running postings.

## 6. Stage A — supply-structure census/surrogate

Stage A is a cheap census, not a posting campaign. It reuses the
seed-scan precedent (`noro_supply_seed_scan_01` one-epoch scans) and may
run a supply-planning-only probe where the engine exposes it; either way
it must emit supply witnesses for every arm/seed/hull.

Per scenario, record at minimum:

- `n_sources`, `n_contaminated_sources`, `n_receipts`, `n_lots`,
  `n_contaminated_lots`;
- contaminated-lot composition by `item_line`, `preparation_class`,
  `supply_stratum`, `service_type`, and `source_cluster_id`;
- `venues_served` distribution per contaminated lot (count, max share,
  passenger-vs-crew split);
- `quantity_servings` / `quantity_g` per contaminated lot and the voyage
  total;
- declared exposure proxies, computed from witnesses only:
  `minted_lot_load = Σ contaminated lots quantity_servings ×
  service_eligible × venue_demand_share`, `venue_concentration = max
  venues_served share`, and `source_correlation = mean pairwise lot
  correlation within source_cluster`.

Stage A readout ranks arms by whether they move the tail proxies
(`venue_concentration`, `source_correlation`, `minted_lot_load` on mega).
For `source_cluster` and `lot_scale`, the ranking requires
`E[contaminated_lots]` to stay matched to the flat baseline; an arm that
only changes introduction frequency is a prevalence result and belongs
to the existing `q_source`/receipt-mode sweeps. For `venue_menu`, the
ranking uses allocation metrics conditional on contaminated-lot count and
reports any census/frequency delta separately rather than treating the
arm as expectation-matched.

Stage A must first reproduce the flat baseline witnesses already
committed for the seed scan and solver screens; a mismatch there is a
census defect, not a finding.

## 7. Stage B — targeted ABM confirmation

Stage B runs only after Stage A names the informative arms/hulls. It is
a small paired-seed screen, not a fleet census:

- default solver `continuous`; `discrete` only if a later solver-
  interaction question is explicitly reopened;
- endpoints: posting frequency (`vsp_trigger_epoch is not None`),
  posted-conditional passenger/crew reported-case AR, VSP timing, and
  role partition;
- seeds: contaminated strata selected from Stage A exposure-proxy
  quantiles plus a small quiet control set per hull (the screen03
  precedent used 8 quiet controls per solver arm; Stage B should not
  grow that into a quiet-mega campaign);
- cell budget: declared before submission and capped by the
  campaign-preflight gate; no array submits until local smoke, dry-run
  count, pinned image digest, manifest, canary inspection, and ETA are
  recorded.

The Stage B question is narrow: does a structure arm change posting
frequency or posted-conditional AR/timing relative to the flat arm at
matched mean introduction? It is not a request to reproduce the whole
VSP fleet distribution.

## 8. Integrity gates and admissibility

1. **Baseline bit-identity** — `mode: "flat"` and the existing
   `station_lots`/`single_line_receipt`/`declared_receipts` paths remain
   bit-identical to current main at shared seeds.
2. **Expectation accounting** — `source_cluster` and `lot_scale` arms are
   expectation-matched to the flat arm and realized contaminated-lot
   counts must agree within binomial tolerance. `venue_menu` arms must
   declare the service-eligible census delta and Stage A must separate
   allocation effects from introduction-frequency effects; no arm may
   silently change mean introduction.
3. **Nested rungs** — scalar or threshold rungs preserve contaminated-set
   nesting at shared seeds where the draw grammar allows it.
4. **Witness completeness** — every contaminated lot carries
   `source_cluster_id`, `menu_service_type`, `servings_multiplier`,
   `venues_served`, `quantity_servings`, and `quantity_g`; clean receipts
   are emitted for census reconciliation.
5. **External checks, not targets** — report food-involved outbreak share
   against Mouchtouri 2024's bound and food-vehicle voyage frequency
   against the VSP/Freeland bound as external checks only. No constant may
   be moved to make those checks pass.
6. **No anchor fitting** — no VSP, Park, attack-rate, or passenger/crew
   anchor may select a structure rung, mask, multiplier, or cluster size.

## 9. Non-goals

- No engine implementation in this PR.
- No default flip: `supply_structure.mode` ships as `flat` until Stage A
  witnesses and a Stage B canary justify otherwise.
- No per-venue menu inference from ship names or marketing pages;
  `venue_menu` masks are declared structural scenarios, not measured
  menus.
- No mid-voyage restock cadence; receipts/lots board at embarkation
  inside the existing lot window unless a later design adds provisioning
  events.
- No preparation-survival numeric factor; `raw_rte_only` remains the
  conservative service-eligibility rule.
- No fleet-wide posting campaign and no massive quiet-mega census; Stage
  B is targeted confirmation only.
- No cross-voyage/fleet correlation in v1; `fleet_shared` is a
  within-voyage bounding arm for the Rispens mechanism, not a fleet
  simulation.
- No VSP-score-to-parameter mapping; food-safety posture remains a
  mechanism observable, not a fitted covariate.
