# CONTAM-DUCT-EXCLUDE-01
**Date:** 2026-11-17
**Commit:** 63210391
**Pathogens:** all
**Status:** measured
**Measured at:** 63210391

## Scope

Implements the owner ruling of 2026-11-17, option **B — exclude spines,
per-hull `skip_duct_spines` on the 9 hulls** from
[`../proposals/duct_transport_contract_audit_and_fix_plan.md`](../proposals/duct_transport_contract_audit_and_fix_plan.md)
§4, over the inventory in
[`../audits/2026-11-17_duct_spine_fleet_inventory/fleet_inventory.csv`](../audits/2026-11-17_duct_spine_fleet_inventory/fleet_inventory.csv)
and the audit record
[`CONTAM-DUCT-TRANSPORT-01`](CONTAM-DUCT-TRANSPORT-01.md). This is per-hull
only: the exporter default is unchanged, option A/C are not taken, and no hull
is adjudicated as having intended duct physics.

Data commit `63210391` adds `"skip_duct_spines": true` to the eight existing
hobbyist override files and creates the missing
`diamond_princess/contam/hobbyist_overrides.json` with the same gate, then
regenerates the nine commissioned-mode `contam/platform.prj` bundles. Every
target bundle now has `0 ! duct elements:`, `0 ! duct junctions:`, `0 !
initial junction concentrations:` and `0 ! duct segments:`; the PRJ diffs are
the duct-section records/headers only. `contam/path_map.json` is byte-identical
on all nine hulls, so the field transport contract is unchanged.

Six cruise `air_flow_paths.json` files re-declare the stage-4 D5
`exchange_m3h` values from spine-free commissioned-lane solves (table below).
No `flow_rate_m3h`, `spatial_layout.json`, schema, exporter constant, leak area,
wind declaration or epidemiological constant changed. A hash check of 395
platform `spatial_layout.json` / `air_flow_paths.json` / `contam/*.json` /
`contam/platform.prj` files against `HEAD` found changes only in the 24
expected files: nine `platform.prj`, nine `hobbyist_overrides.json`, and six
`air_flow_paths.json`; the other 68 bundles are byte-identical.

Owner decision 5 from the proposal (§6, readout annotation) remains deferred:
no committed readout is annotated in this change.

## Bounded ContamX witnesses

Local binary only: `third_party/contamx/contamx3`, ContamX `3.4.0.3 64 bit`
(binary sha256 `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`,
tarball sha256 `3612798dff9a4f1ea4f0279c4c7b526b244b88875dea425fafd868f3570df4fa`,
the pin in `tests/test_contam_phase2_cruise_contrasts_campaign.py`). Witness:
`tools/diag/contam_pressure_balance_diagnostic.py` over the nine hulls in the
`authored`, `commissioned` and `design` lanes with `--all-paths`; scratch
report `telemetry_buffer/duct_exclude_pressure/results.json` (27 rows, 0
unsolved). For the regenerated bundles `authored` and `commissioned` are the
same solve; the table reports commissioned (= authored) and design.

| hull | commissioned max \|ΔP\| Pa (class) | commissioned balance residual m³/h | design max \|ΔP\| Pa (class) | design balance residual m³/h |
|---|---:|---:|---:|---:|
| classic_cruise_1900 | 782.867 (prescribed_link) | -0.0046633 | 1,078.780 (prescribed_link) | -0.000195819 |
| diamond_princess | 43.107 (envelope_leak) | 0.000598408 | 12,658.647 (prescribed_link) | 0.00987305 |
| expedition_cruise_450 | 89.188 (envelope_leak) | 0.00106787 | 9.718 (envelope_leak) | 0.000982568 |
| greg_mortimer | 19.176 (envelope_leak) | -0.000737543 | 9.611 (envelope_leak) | -0.000664385 |
| mega_cruise_5000 | 290.365 (envelope_leak) | -0.0504114 | 57.827 (prescribed_link) | 0.0634645 |
| spirit_cruise_3000 | 32.808 (envelope_leak) | -0.00518848 | 10.749 (passive_opening) | 0.00519992 |
| enterprise_constitution_tos | 13.577 (prescribed_link) | -4.45514e-05 | 13.571 (prescribed_link) | 0.000178205 |
| enterprise_galaxy_tng | 73.596 (passive_opening) | -0.000512341 | 73.596 (passive_opening) | -0.000356411 |
| destroyer_baseline | 81,561.180 (envelope_leak) | -5.57692e-06 | 1.052 (envelope_leak) | 1.08924e-08 |

Balance residuals stay at solver-noise level for these boundary flows (max
|residual| 0.0634645 m³/h, `mega_cruise_5000` design). These are the spine-free
absolute values that replace the spine-inclusive stage-3/4 absolutes called out
in the proposal §5 caveat; the stage-3/4 ledgers remain the historical
spine-inclusive record.

## Attribution checks

- The six cruise D5 re-derivations are small and monotone in sign with the
  removed interior redistribution: 23 records, largest move `classic_cruise_1900`
  `PoolDeck` +1.752%, all within ±2%. No value was fitted to the old spine-inclusive
  number; the spine-free commissioned-lane outward `Flow0` sum is the declared
  value.
- `diamond_princess` has the only large absolute design-lane move found in the
  bounded witnesses. An in-memory paired control at `63210391` (same hull JSON,
  spine-inclusive overrides vs `skip_duct_spines`) gives design max |ΔP|
  13.009 Pa → 12,658.647 Pa and commissioned 12.914 Pa → 43.107 Pa. The maxima
  are pre-existing mapped `Cabin_Relief_D8` prescribed links and envelope leaks,
  not duct records; the move is therefore attributed to removing the interior
  duct-spine redistribution, and the spine-free value is recorded here rather
  than treated as a D5/native-exchange anomaly.
- `destroyer_baseline` commissioned/design maxima are unchanged by the gate in
  the same paired control (commissioned 81,561.179688 Pa both ways; design
  1.052284 Pa spine-inclusive vs 1.052368 Pa spine-free). The 81.5 kPa
  commissioned envelope-leak residual on `HD_UPPER_M` is pre-existing, not
  introduced by this change.
- No merged stage-3/4 *conclusion* is invalidated: the witnesses are boundary
  budgets/comparative measurements, the path maps are unchanged, and the only
  large absolute move is the already-scoped stage-3 design-lane re-derivation
  recorded above.

## D5 `exchange_m3h` re-derivation (six cruise hulls)

Method: pair each `ambient_openings` record to its two
`kind == "ambient_opening"` path-map legs in order, sum the commissioned-lane
positive outward `Flow0` legs, and round to 0.1 m³/h. `flow_rate_m3h` was not
edited.

| hull | zone | old exchange_m3h | new exchange_m3h | Δ |
|---|---|---:|---:|---:|
| classic_cruise_1900 | PoolDeck | 101,803.4 | 103,587.5 | +1.752% |
| diamond_princess | OceanFront | 63,357.9 | 63,794.4 | +0.689% |
| diamond_princess | TerracePool | 83,348.9 | 83,327.1 | -0.026% |
| diamond_princess | NeptunePool | 113,501.0 | 113,419.8 | -0.072% |
| diamond_princess | CalypsoPool | 96,535.9 | 96,503.1 | -0.034% |
| diamond_princess | HorizonTerrace | 55,963.4 | 55,916.3 | -0.084% |
| diamond_princess | OpenAirCinema | 64,061.5 | 64,454.8 | +0.614% |
| diamond_princess | SportsCourt | 55,834.0 | 55,861.8 | +0.050% |
| diamond_princess | CenterCourt | 45,416.9 | 45,384.5 | -0.071% |
| expedition_cruise_450 | PoolDeck | 73,376.0 | 73,493.4 | +0.160% |
| greg_mortimer | ZodiacPlatforms | 34,039.3 | 34,021.0 | -0.054% |
| greg_mortimer | ActivityPlat | 30,893.5 | 30,877.9 | -0.050% |
| greg_mortimer | ViewPlatforms | 27,471.5 | 27,441.6 | -0.109% |
| greg_mortimer | SunDeck | 39,351.8 | 39,348.8 | -0.008% |
| greg_mortimer | TopDeck | 35,887.5 | 35,875.1 | -0.035% |
| mega_cruise_5000 | Main_Pool_Deck | 211,952.4 | 212,766.1 | +0.384% |
| mega_cruise_5000 | Sports_Court | 96,737.7 | 96,819.7 | +0.085% |
| mega_cruise_5000 | Waterpark | 137,197.9 | 137,280.0 | +0.060% |
| mega_cruise_5000 | CentralPark | 421,507.5 | 421,387.1 | -0.029% |
| mega_cruise_5000 | Aqua_Theater | 309,439.7 | 309,433.6 | -0.002% |
| spirit_cruise_3000 | MainPool | 111,163.1 | 111,611.8 | +0.404% |
| spirit_cruise_3000 | AftPool | 79,104.8 | 78,893.6 | -0.267% |
| spirit_cruise_3000 | SportsDeck | 96,141.5 | 97,030.1 | +0.924% |

## `destroyer_baseline.sim` fixture decision

Keep `tests/fixtures/contam/destroyer_baseline.sim` unchanged. It is a binary
SIM-reader regression fixture (header `npath=44`, `nafpt=52`, `njct=5`,
`ndct=3`, record sizes `(32, 832, 272, 204)`) for the embedded path-record `nr`
contract: `SimResults.path_volumetric_flow_m3h` must key `Flow0` by the `nr`
inside each path record, not by the unreliable header xref, and the test pins
`Fan_25`/`Fan_26`/`Fan_27` at ≈16.67/13.33/10 m³/h. The spine-free PRJ removes
only duct sections outside `path_map.json`; it does not change the SIM reader,
the embedded-`nr` join, or the fixture's historical xref regression. The current
`destroyer_baseline` `path_map.json` remains 69 entries.

## Test-pin updates

`tests/test_contam_hobbyist_{classic,constitution,destroyer,expedition,galaxy,mega,spirit}.py`
now assert `duct elements`, `duct junctions` and `duct segments` are zero on
both the fresh export and the committed bundle; the destroyer ContamX-grammar
check no longer expects duct-terminal `vf_node_name` lines because the bundle
has no duct junctions. `tests/test_contamw34_commissioned.py` still reproduces
the destroyer and expedition commissioned bundles byte-for-byte.

## Follow-ups

If any hull's spines are later ruled intended physics, that hull needs option A
(duct records represented in the field adapter) instead of this exclusion.
Until then, field-adapter source-to-receptor numbers on these nine hulls carry
the audit caveat from `CONTAM-DUCT-TRANSPORT-01`; proposal §6 decision 5
(readout annotation) is still owner-deferred.
