# Paper 3: variant surveillance and phylodynamics

> **Status:** Partially implemented. Strain mechanics and observables are
> in-tree behind `variant_surveillance.enabled` in `crusher_labs/config.yaml`;
> the campaigns are defined but gated.

| Doc | Status | Implementation evidence |
|-----|--------|-------------------------|
| [variant_surveillance_spec.md](variant_surveillance_spec.md) | Partially implemented | `engines/strain_state.py`, `strain_mutation.py`, `strain_dose_ledger.py`; `crusher_labs/modalities/clinical_strain_typing.py`, `surface_strain_recovery.py`; wastewater deconvolution; Federation port profiles. Recombination deferred to v2 by the spec (needs co-infection mechanics) |
| [variant_surveillance_plan.md](variant_surveillance_plan.md) | Partially implemented — **its own header is stale** | Line 5 says "Nothing here is implemented yet". That was true on 2026-08-20 and is false now: the same file carries "*As built*" notes, and the PR 1–3, 11 and 13 artifacts all exist. Do not file or reason from the header |
| [phylodynamic_observables.md](phylodynamic_observables.md) | Implemented | `analysis/phylodynamics/` (artifact, campaign, compare, detection, diversity, figures, information, report), campaign arming via `_arm_lineage_census` / `_arm_sentinel_line_list`, `tests/test_phylodynamic_observables.py` |
| [surface_strain_recovery.md](surface_strain_recovery.md) | Implemented | `crusher_labs/modalities/surface_strain_recovery.py`, ShipSimulation wiring, `tests/test_surface_strain_recovery.py`. This is spec §2.3 |
| [paper3_campaign_designs.md](paper3_campaign_designs.md) | Designs implemented, campaigns **gated** | All five `paper3_*_v1_manifest.json` exist with `variant_campaign.py` and `tests/test_paper3_variant_campaigns.py`, but every tier is `deferred: true`, so `--tier all` will not sweep them. Release is blocked on the `c1_*` dose refit — see [`../norovirus/norovirus_open_ledger.md`](../norovirus/norovirus_open_ledger.md) |
