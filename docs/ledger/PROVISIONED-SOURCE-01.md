# PROVISIONED-SOURCE-01
**Date:** 2026-10-15
**Commit:** (implementation leg — this change)
**Pathogens:** all armed `common_source_events.enabled` profiles (norwalk_gi ships armed)
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
  `"fiat"` (labelled baseline). Absent resolves `"fiat"` — every
  unmarked config and frozen manifest keeps the pre-mechanism draw
  sequence bit-identical. The shipped config
  (`crusher_labs/config.yaml`) arms `"provisioned_source"`, so the
  mechanism ships ON for shipped runs — the standing default-ON rule
  realized at the config layer, the same explicit-key pattern the
  eval arms use.
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
  `tests/test_common_source_provisioned_source.py`: absent→fiat and
  explicit-fiat identical objects; fiat voyage rates replay verbatim
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

The contract/prompt wording note: §1.1 calls `"provisioned_source"`
"the shipped default once the mechanism lands" while the leg brief
requires the fiat sequence bit-identical when `lot_mint_model` is
absent. Both hold under absent→`"fiat"` engine resolution +
explicit arming in the shipped config; this file records that
resolution so a later reader does not re-litigate it.
