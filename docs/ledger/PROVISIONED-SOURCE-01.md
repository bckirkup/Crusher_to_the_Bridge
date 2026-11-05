# PROVISIONED-SOURCE-01
**Date:** 2026-10-15
**Commit:** #1019
**Pathogens:** all
**Status:** open

The fiat `lot_mode: "object"` voyage gate — one Bernoulli on
`lot_object_probability` plus a geometric `extra_lot_probability`
tail — made objects-per-voyage a per-hull rate-ladder estimate, while
the physical quantity is upstream: each voyage provisions
`N_lots = served-Dining-venues x COMMON_SOURCE_LOT_ITEM_LINES`
stations (21/35/63/70 on exp/cls/spr/mega), each independently
contaminated with prevalence `q_source`. This leg lands the
`lot_mint_model: "provisioned_source"` mechanism of
`docs/provisioned_source_01_design.md` plus its witnesses.

What landed:

- `transmission.common_source.lot_mint_model` —
  `"provisioned_source"` (per-station Bernoulli census mint) |
  `"fiat"` (labelled baseline). **Absent resolves
  `"provisioned_source"`** — the shipped default per contract §1.1
  and the standing default-ON rule: every unmarked config takes the
  census grammar. `"fiat"` spelled out keeps the pre-mechanism draw
  sequence bit-identical; the measured object-arm cells are pinned
  `"fiat"` in the frozen manifests
  (`noro_{mint_rate_01,food_score_01,food_shapes_01,entrain_01}`,
  `mega_smoke_manifest`), their `design/build.py` `_OBJECT_MODES`,
  and `tools/noro_diag/food_shapes_01_report.py`. The shipped config
  (`crusher_labs/config.yaml`) spells `"provisioned_source"` — the
  same explicit-key pattern the eval arms use.
- `transmission.common_source.provisioned_source.{source_id,
  q_source}` — the platform-level covariate block. `source_id`
  resolves through the new registry
  `data/config/provisioning_sources.json` (schema
  `schemas/provisioning_sources.schema.json`; shipped entry
  `generic_cruise_port`, U(2e-4, 5e-4), Grade C, unfitted);
  `q_source` scalar|[lo,hi] follows the `_COMMON_SOURCE_SPECS`
  grammar (block > registry > profile-block > module default).
- RNG contract (contract §2): `q_source` draws once per voyage on the
  `_cs_rng` stream at the first lot-rate slot — handler/diner rate
  draws shift one stream position earlier vs fiat at shared seeds
  (declared); per-station uniforms consume one `random()` each in
  canonical (served-zone, item-line) order, so scalar rungs share the
  identical sequence and contaminated-station sets nest; realization
  mints through the same `_cs_realize_lot_object` minus the zone/item
  draws (the station binds both). Scalar `q_source` consumes no
  uniform, matching every other common-source scalar spec.
- Witnesses (contract §3): voyage block
  `common_source.provisioned_source = {source_id, q_source_drawn,
  n_stations, n_contaminated}` per armed pathogen, emitted in the
  census payload (`tools/noro_diag/growth_chain_census.py`); object
  rows carry `provisioned_source_id` (null on fiat-minted and agent
  objects) into `matrix.common_source_objects`;
  `schemas/simulation_history.schema.json` updated. Lot strains mint
  with `source_location = source_id` (issue #1004).
- `tools/sanity_checker.py` hook (`_check_common_source`, issue
  #1006): `lot_mint_model` enum, `source_id` resolution against the
  registry (incl. `default_source`), `q_source` scalar|[lo,hi]∈[0,1]
  ordered grammar, warning when `provisioned_source` is armed on a
  platform with no Dining zones (census resolves N_lots = 0).
- §4 integrity gates pinned in
  `tests/test_common_source_provisioned_source.py`: absent→
  provisioned_source and absent≡explicit-provisioned identical
  objects; fiat voyage rates replay verbatim
  on a twin stream; `q_source` at the first lot-rate slot; nested
  contaminated sets across scalar rungs (with the exact
  station-uniform sequence replayed); Binomial(N,q) mean over 120
  seeds; station-bound (no duplicate-station) mints; row/strain
  witnesses; mode-off and independent-mode no-ops; worker arms
  untouched.
- `data/config/provisioning_sources.json` registered in the
  schema-validation map; `q_source` admitted to
  `CommonSourceEvents` per-pathogen overrides; `q_source` shipped
  interval registered Grade C in
  `docs/parameter_provenance_register.md` §3.12.

Not in this leg (deliberate): sentinel import-channel vocabulary
(#1008), founders-census split (#1010), source-keyed genotype priors
(#1011 — the registry carries `q_source` only), the
NORO-PROVISIONED-SOURCE-01 eval array itself.

Since then: #1008 closed via `reported_cases_by_channel` (#1018);
#1010 closed via `founders_by_origin` (#1024); #1011 closed via the
`genotype_distribution` extension — an optional per-pathogen genotype
mix on each registry source (block > registry > boarding
`prior_genotype_distribution`; a source or pathogen with no declared
mix keeps the prior). The shipped `generic_cruise_port` entry
declares no mix pending the sourcing leg — fallback is the
reason-to-be-the-same, not a hole.

The contract/prompt wording note: §1.1 calls `"provisioned_source"`
"the shipped default once the mechanism lands" while the leg brief
asked the fiat sequence to stay bit-identical for unmarked configs.
The first implementation resolved absent→`"fiat"` and armed the
shipped config explicitly; the user then settled it the other way —
absent→`"provisioned_source"`, with `"fiat"` pinned on every
artifact whose measured cells ran the fiat grammar. This file
records that resolution so a later reader does not re-litigate it.

Sourcing leg (2026-11-05, tranche 55 —
`docs/literature/consensus_tranche_55_provisioned_lot_prevalence.md`):
the `generic_cruise_port` registry interval moves from the declared
U(2e-4, 5e-4) to the sourced composite **U(8.6e-4, 4.7e-3)** —
q = (1/7) Σ per-item-line dispatch/retail norovirus RNA prevalence
(shellfish [0.039, 0.144]: Woods 2010, EFSA 2019 dispatch batches
10.8%; salad_leaf [0, 0.053]: Terio 2017 0/911, Cook 2019 5.3%;
fresh_produce [0.0036, 0.036]: Steele 2022 0.36%, Cook 2019 3.6%,
Miotti 2024 pooled 2.12%; deli/bakery/dairy/garnish ∅ for the
high-income stratum, carried at 0) × the implicated-titre share
f = 0.141 (Lowther 2018: 9.7% of 68.7% POS oysters >100 copies/g),
because the shipped `titre_draw_mode: two_mode` mints every lot at
implicated titre. Measured overcorrection, reported not corrected:
the RNA-detection rung lands [6.1e-3, 3.3e-2] (30–67× declared), the
shipped implicated rung 4–9× declared; its lower edge touches the
measured mega in-band window [8e-4, 1.5e-3] and its centre is the q30
rung, so the small-hull in-band window [2e-4, 5e-4] is **below** every
sourced rung. Plausibility (inferred): at q = 3.1e-3 with the measured
P(post|minted) ladder, ~6% of small-hull voyages would post from food
alone, vs ~3–7e-4 food-vehicle outbreak voyages implied by VSP
(133/29,107 × Mouchtouri 2024 3/45–6/41). Stratification reported
rather than averaged: oyster prevalence runs 3.9% (US market) →
10.8% (EU dispatch) → 68.7% (UK POS); UK/IE-origin shellfish belongs
to a separate source id. Not touched: the module fallback
`COMMON_SOURCE_Q_SOURCE_RANGE` (engine constant, out of this leg's
scope — registry outranks it), every frozen campaign manifest (all pin
`q_source` explicitly), and the fiat baseline. The per-item-line
registry extension (`q_source_by_item_line`, log-uniform shape,
shared-lot correlation per Rispens 2020) is proposed in tranche 55 §7;
the grammar reads a scalar|[lo, hi] only today.

