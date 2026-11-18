# CONTAM-AEOLUS-LADDER-WELL-AUTHOR-01
**Date:** 2026-11-17
**Commit:** 4a3d7a55
**Pathogens:** all
**Status:** measured
**Measured at:** fb2644ff934fcadfd4042039a28cf974bb52a01f

## Scope

Owner-ruled G3 authoring leg for `aeolus_arc3` only, under the 2026-11-17
ruling recorded in `CONTAM-AEOLUS-LADDER-WELL-01.md` and
`docs/proposals/grouped_weather_openings_decision_plan.md` §5.3/§7-G3.
All six ladder-well group links are authored at the bounded Grade C
`ladder_well_0p8` candidate: **0.80 m² total clear-orifice area per group
link**, split uniformly across that link's expanded room-pair paths.
`hatch_0p36` (0.36 m²) and `passageway_2p0` (2.00 m²) remain recorded
sensitivity bounds only; they were not re-authored or re-solved here.

Representation: no `flow_rate_m3h` value, ambient opening, schema, native
bridge, leak area, schedule, wind or filter changed. The committed
`air_flow_paths.json` and `spatial_layout.json` bytes are unchanged. The
authored capacity is carried by the Aeolus hobbyist override
`cross_zone_orifice_total_area_m2` (`ladder_well_1` … `ladder_well_6` =
0.8), consumed by the ContamW34 exporter as a total link area divided by
the emitted room-pair path count. The regenerated commissioned bundle is
`data/platforms/aeolus_arc3/contam/platform.prj` SHA-256
`6cd50ab93e408b7ec2aca4dee71ec37068001f199305a77fff655c88eacef39e`;
`path_map.json` SHA-256 remains
`c35904c78782fba99b0008d6c831a7379a21729d856bb249bd13ebe7e7ffccf0`.

Witnesses used Official ContamX 3.4.0.3 (`third_party/contamx/contamx3`,
SHA-256 `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`,
not committed) on both the commissioned and design lanes; all four solves
had 0 unsolved paths. Commissioned before is the committed pre-change
bundle `b51eb51215cba315c294405ee330a205ba3d3ea0d659c5a4c154861808be38e5`;
commissioned after is the regenerated bundle above. Design before/after
PRJ SHA-256 values are `0bb8c7a31bf6ec2d47af731ce42742e27e85f2fc6a4a31a379729e5391eae7f6`
and `5c53b254c35da4674086db03b8790644ebea3bf50985ff4c8c0259c3c321871d`.

## Witnesses

### Pressure and boundary balance

| Lane | Variant | Envelope max abs ΔP Pa | Interior flowing max abs ΔP Pa | Make-up demand m³/h | Balance residual m³/h |
|---|---|---:|---:|---:|---:|
| commissioned | before | 952.953674 | 434.797516 | 1066.040948 | -0.002823 |
| commissioned | after | 3.382359 | 2.612933 | 1066.040948 | 0.005275 |
| design | before | 3.122410 | 0.071304 | 0.0 | -0.000698 |
| design | after | 3.259515 | 0.000089 | 0.0 | -0.010542 |

Commissioned make-up demand is preserved at 1066.040948 m³/h; the balance
residual remains at solver round-off scale (worst |residual| 0.010542
m³/h on the design lane, 0.005275 m³/h commissioned). The design lane's
make-up demand is 0.0 before and after because that lane's AHS terminal
encoding has no commissioned return-minus-supply imbalance.

### Ladder-well links

Cells are max path abs ΔP (Pa) over each link's expanded room-pair paths.

| Lane | Variant | `ladder_well_1` | `ladder_well_2` | `ladder_well_3` | `ladder_well_4` | `ladder_well_5` | `ladder_well_6` |
|---|---|---:|---:|---:|---:|---:|---:|
| commissioned | before | 173.406006 | 80.075859 | 71.125648 | 135.978653 | 434.797516 | 342.858429 |
| commissioned | after | 0.165521 | 0.163671 | 0.167917 | 0.102688 | 0.391985 | 0.318160 |
| design | before | 0.000294 | 0.000362 | 0.001653 | 0.001317 | 0.066509 | 0.071304 |
| design | after | 0.000007 | 0.000008 | 0.000011 | 0.000016 | 0.000044 | 0.000090 |

## Acceptance evaluation

- Scope: PASS. Exactly the six committed `ladder_well_*` cross-zone links
  on `aeolus_arc3` received the authored total area; no other hull, link
  kind, adjacency edge or ambient opening changed.
- Capacity basis: PASS as a bounded Grade C assumption. The 0.80 m² total
  per group link is the owner-selected `ladder_well_0p8` candidate from
  the hobbyist opening catalog; it is not fitted to solved flow or pressure.
- No forbidden change: PASS. `flow_rate_m3h` remains 50.0 on every link;
  no schema file changed; the native prescribed-flow bridge is untouched.
- Pressure/balance: PASS for the commissioned acceptance. The largest
  commissioned ladder-well residual falls from 434.797516 Pa to
  0.391985 Pa, envelope max |ΔP| falls 952.953674 → 3.382359 Pa, and
  interior flowing max |ΔP| falls 434.797516 → 2.612933 Pa while make-up
  demand is unchanged.
- Fleet isolation: PASS. Fresh commissioned exports for the 76 non-Aeolus
  platforms with committed `contam/platform.prj` files reproduce their
  committed PRJ SHA-256 byte-for-byte after the exporter change.
