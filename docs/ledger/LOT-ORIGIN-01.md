# LOT-ORIGIN-01
**Date:** 2026-10-15
**Commit:** 3b2a80c6
**Pathogens:** all
**Status:** closed
**Measured at:** 3b2a80c6

`_cs_lot_mix` (`engines/transmission_core.py`) mints every provisioned-lot
strain with `origin="imported:lot"` — the tag the PROVISIONED-SOURCE-01
contract (`docs/provisioned_source_01_design.md` §2) names — but
`STRAIN_ORIGINS` in `engines/strain_state.py` admitted only
`{founder, transmission, within_host, recombination, shore_import}`.
`StrainState.__post_init__` validates `origin in STRAIN_ORIGINS`, so the
first lot minted under `variant_surveillance.enabled: true` raised
`StrainConfigError` (`unknown strain origin 'imported:lot'` — reproduced
at the measured SHA by direct `StrainRegistry.mint` call).

Reachability: `variant_surveillance.enabled` + `lot_mode: "object"`
(shipped default) + `common_source_events.enabled` (norwalk_gi ships on)
+ any minted `provisioned_lot` — the mint fires at object realization
(`_cs_realize_lot_object` → `_cs_lot_mix`) unconditionally, genotype
prior or not. The v1 `lot_mode: "independent"` path mints per fired pan
through the same helper and crashes identically.

Why it was latent: no test composed the two flags — the common-source
suite never armed `variant_surveillance` and the strain suite never
armed common-source — and GENO-02's 2,880 cells ran image engine
`4f5e7fbe`, which predates `4a210a69` (the commit that introduced the
`imported:lot` mint) so it could not hit the raise. Under the shipped
fiat gate (~1% of voyages mint) the crash was a rare killer; under
`lot_mint_model: "provisioned_source"` the census mints E[objects] =
N·q per voyage — up to ~21 objects/voyage on mega powered rungs — i.e.
near-certain death on every strain-armed provisioned-source cell.

Fix (this change): `"imported:lot"` added to `STRAIN_ORIGINS`. Origin
consumers audited: `is_founder` files parentless mints under
`_founders` (supply-chain founders enter the founders census by
construction — whether consumers should split founders by origin is
issue #1010); mutation-rate dispatch keys `TRANSMISSION_ORIGIN` only,
so descendants of lot strains are unaffected; `to_telemetry` passes
`origin` through to the lineage artifact unchanged. Composition
regression tests added in `tests/test_common_source_lot_objects.py`
(object-mode mints with no genotype prior; independent-mode pans mint
with a declared prior).

Related: issue #1003 (this defect); #1007 (`imported:lot` founders
inflate `genotypes_emerged` — origin-aware emergence split needed);
#1004 (`provisioned_source_id` witness and `source_location` on lot
strains).
