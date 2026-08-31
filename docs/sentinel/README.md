# Sentinel surveillance, port health, and economics

> **Status:** Living. Implementation is under
> `picard_framework/analysis/sentinel/`, `analysis/shore/`, and
> `analysis/economics/`.

Cruise ships as port-of-call sentinels: what port authorities observe, what
wastewater assays recover, and who would pay for it.

| Doc | Status | Implementation evidence |
|-----|--------|-------------------------|
| [sentinel_surveillance_spec.md](sentinel_surveillance_spec.md) | Partially implemented | `analysis/sentinel/` (observations, attribution, incubation, export_line_list, figures, report, wastewater_assays, wastewater_ops), ~20 `tests/test_sentinel_*.py`. Deferred by the spec itself: the genomics/amplicon phase, and shore exposure — `shore_infection_probability` is still a stub |
| [sentinel_port_health.md](sentinel_port_health.md) | Implemented | `sentinel/port_health.py`, `port_profiles.py`, `port_ledger.py`, `schemas/port_surveillance*.schema.json`, `tests/test_port_health_surveillance.py` |
| [port_health_surveillance_spec.md](port_health_surveillance_spec.md) | Implemented — earlier spec for the same layer | Same paths. The spec's `PortHealthAuthority` is realised as `generate_port_signals` plus profile objects; behaviourally equivalent, not a class-name match |
| [sentinel_design_power.md](sentinel_design_power.md) | Implemented | `sentinel/design_power.py`, `design_nuts.py`, `stan/fit_sentinel_fleet.py`; `tests/test_sentinel_design_power.py`, `test_sentinel_design_nuts.py` |
| [sentinel_design_separability.md](sentinel_design_separability.md) | Implemented | `sentinel/separability.py`, `tests/test_sentinel_separability.py` |
| [sentinel_wastewater_ops_scan.md](sentinel_wastewater_ops_scan.md) | Implemented | `sentinel_ww_ops_scan_v1_design.json` + `_manifest.json`, `_iter_sentinel_recovery_runs` in the campaign runner, `tests/test_wastewater_ops_scan.py`. Code and design exist; campaign outputs not verified as materialised |
| [sentinel_ww_ops_scan_spec.md](sentinel_ww_ops_scan_spec.md) | Implemented — earlier spec for the doc above | Same design/manifest pair, plus `sentinel_recovery.py` postprocess |
| [shore_side_model.md](shore_side_model.md) | Implemented | `analysis/shore/{importation,renewal,counterfactual,detection,scenarios,sweep}.py`, four `tests/test_shore_*.py`. `R_shore` and the generation interval stay caller-supplied by design |
| [surveillance_economics.md](surveillance_economics.md) | Implemented, **numbers not quotable** | `analysis/economics/` + `tests/test_economics_*.py`. The doc states the dollar levels in `valuations.py` are unanchored placeholders |

Related, filed elsewhere because their artifact does not match the document:

- [`../proposals/sentinel_stan_fix_spec.md`](../proposals/sentinel_stan_fix_spec.md)
  — its four required edits target `sentinel_attribution.stan`; only the
  wastewater likelihood landed, and in `sentinel_fleet.stan` instead.
- [`../proposals/wastewater_mode_switch_spec.md`](../proposals/wastewater_mode_switch_spec.md)
  — the capability was delivered in a different shape and location than
  prescribed.
