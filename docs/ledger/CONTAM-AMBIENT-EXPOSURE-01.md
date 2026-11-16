# CONTAM-AMBIENT-EXPOSURE-01
**Date:** 2026-11-16
**Commit:** 15beae6b
**Pathogens:** all
**Status:** measured
**Measured at:** 15beae6b

## Scope

Stage 0 of
[`../proposals/ambient_exposure_audit_and_fix_plan.md`](../proposals/ambient_exposure_audit_and_fix_plan.md):
audit of how open decks, balconies, hatches and exhaust make-up reach
ambient in the airflow layer (native bridge and ContamX export), and a
proposed representation. Changes behaviour: **no**. Docs only; no data,
engine, exporter, schema or constant is touched. Base `origin/main`
`15beae6b968a22a09764c1b5edb47c444a90c905`. Builds on
[`CONTAM-FIELD-PRESSURE-REVIEW-01`](CONTAM-FIELD-PRESSURE-REVIEW-01.md),
[`CONTAM-FIELD-ENVELOPE-BOUNDARY-01`](CONTAM-FIELD-ENVELOPE-BOUNDARY-01.md),
[`CONTAM-FIELD-POOLDECK-OPENINGS-01`](CONTAM-FIELD-POOLDECK-OPENINGS-01.md),
[`CONTAM-FIELD-ADJUDICATION-01`](CONTAM-FIELD-ADJUDICATION-01.md).

Owner hypothesis tested (Benjamin, 2026-11-16): "open decks, for example,
are probably not being modeled as exposed, as well as active ventilation
and routinely open hatches".

## Findings

Measured unless marked. Steady-state ContamX, local binary
`third_party/contamx/contamx3`, no seeds, no AWS. Commands are in the
proposal, Appendix A (inventory) and Appendix B (area sweep).

1. **Inventory (82 platforms).** 243 weather zones on 78 hulls
   (505,255 m³), classified by `tools.hull_audit._is_exterior`; 112 are in
   no HVAC group and 124 have zero outdoor exchange. 153 `balcony_partial`
   corridor zones on 6 hulls (157,340 m³). Opening adjacency edges:
   `open_deck` 17 on 6 hulls, `deck_walkway` 24 on 15, `open_front` 11 on
   5, `open_area` 3 on 1, `hangar_door` 3 on 2, `hatch` 35 on 9,
   `service_hatch` 28 on 15. Every one is zone-to-zone. 12 ambient links
   on 11 hulls, all `zone → ambient` prescribed sinks, none with `ambient`
   as source.
2. **Hypothesis verdict per class.** Weather zones with zero outdoor
   exchange (124): confirmed. Weather zones in an HVAC group with outdoor
   air (119): partial — exposed, but as mechanically ventilated rooms.
   Balconies: confirmed for the airflow layer. Hatches, weather doors,
   hangar doors: confirmed. Mechanical outdoor-air supply: refuted (it is
   modelled in both lanes). Exhaust make-up: confirmed.
3. **Exhaust-sink implausibility is a symptom of missing make-up area, not
   of sink magnitude (8 of 8 cruise/fiction hulls, design lane).** With
   prescribed sinks unchanged and only the shared envelope-leak area
   overridden in memory, max envelope |ΔP| goes from 1.25e5–7.16e5 Pa at
   0.0001 m² to 34.2–1,530 Pa at 0.01 m² and 1.47–5.92 Pa at 1 m². The
   0.0001 m² column reproduces the stage-1 design-lane values. This does
   not validate the sink magnitudes themselves.
4. **Representation (inferred from code, not implemented).** Additive in
   both lanes: a new `ambient_openings` record, a native builder that emits
   it as the existing sink path (exchange with clean ambient is
   mathematically a sink in the fixed-flow linear operator), an exporter
   emitter modelled on the envelope leak, and a new path_map kind. One
   existing predicate must be widened: `boundary_sink` to cover the new
   kind.
5. **Literature.** Wall openings can be bounded to about an order of
   magnitude through the orifice equation with a wind pressure coefficient.
   No measured exchange rate for an open ship deck, a ship balcony door or
   hatch-open duty was retrieved; those are proposed as declared axes.

## Area sweep (design lane)

Max |ΔP| in Pa by path class at each shared envelope-leak area. Exhaust
sink flow is the solved prescribed total and is identical across areas.

| Hull | Sink m³/h | Area m² | Envelope leak | Exhaust sink | Passive opening | Prescribed link |
|---|---|---|---|---|---|---|
| `classic_cruise_1900` | 12,003.0 | 0.0001 | 4.85e5 | 4.84e5 | 4.85e5 | 266 |
| `classic_cruise_1900` | 12,003.0 | 0.01 | 197 | 23.0 | 197 | 174 |
| `classic_cruise_1900` | 12,003.0 | 1 | 3.37 | 0.00266 | 3.56 | 3.36 |
| `diamond_princess` | 18,000.0 | 0.0001 | 2.91e5 | 2.91e5 | 2.91e5 | 32.5 |
| `diamond_princess` | 18,000.0 | 0.01 | 48.8 | 21.8 | 48.9 | 28.7 |
| `diamond_princess` | 18,000.0 | 1 | 3.39 | 0.000959 | 3.39 | 3.39 |
| `expedition_cruise_450` | 8,008.8 | 0.0001 | 7.16e5 | 7.15e5 | 7.16e5 | 446 |
| `expedition_cruise_450` | 8,008.8 | 0.01 | 145 | 21.8 | 145 | 123 |
| `expedition_cruise_450` | 8,008.8 | 1 | 1.54 | 0.439 | 1.54 | 1.1 |
| `greg_mortimer` | 4,943.6 | 0.0001 | 3.36e5 | 928 | 3.36e5 | 3.37e5 |
| `greg_mortimer` | 4,943.6 | 0.01 | 157 | 0.77 | 95.9 | 156 |
| `greg_mortimer` | 4,943.6 | 1 | 1.72 | 2.39 | 3.29 | 1.8 |
| `mega_cruise_5000` | 15,002.8 | 0.0001 | 1.76e5 | 1.76e5 | 1.76e5 | 6.7 |
| `mega_cruise_5000` | 15,002.8 | 0.01 | 34.2 | 34.2 | 34.2 | 6.37 |
| `mega_cruise_5000` | 15,002.8 | 1 | 2.91 | 0.255 | 11.3 | 1.14 |
| `spirit_cruise_3000` | 15,002.6 | 0.0001 | 3.95e5 | 3.94e5 | 3.95e5 | 767 |
| `spirit_cruise_3000` | 15,002.6 | 0.01 | 1,530 | 1,020 | 1,530 | 515 |
| `spirit_cruise_3000` | 15,002.6 | 1 | 5.92 | 0.0183 | 6.52 | 5.91 |
| `enterprise_constitution_tos` | 5,000.0 | 0.0001 | 1.67e5 | 1.67e5 | 1.67e5 | 48.6 |
| `enterprise_constitution_tos` | 5,000.0 | 0.01 | 52.3 | 13.2 | 52.4 | 40.6 |
| `enterprise_constitution_tos` | 5,000.0 | 1 | 1.47 | 0.000165 | 1.48 | 1.48 |
| `enterprise_galaxy_tng` | 8,000.0 | 0.0001 | 1.25e5 | 1.25e5 | 1.25e5 | 115,000 |
| `enterprise_galaxy_tng` | 8,000.0 | 0.01 | 415 | 396 | 417 | 160 |
| `enterprise_galaxy_tng` | 8,000.0 | 1 | 4.95 | 0.0228 | 4.98 | 4.95 |

`expedition_cruise_450`, commissioned lane (make-up demand 12,544.7 m³/h,
sinks 8,008.8): envelope 9.82e5, 174, 1.54 Pa at the three areas.

## Ambient links (all 12)

| Hull | From | To | `flow_rate_m3h` |
|---|---|---|---|
| `classic_cruise_1900` | MainGalley | ambient | 12000 |
| `diamond_princess` | MainGalley | ambient | 18000 |
| `enterprise_constitution_tos` | Galley | ambient | 5000 |
| `enterprise_galaxy_tng` | Galley | ambient | 8000 |
| `expedition_cruise_450` | MainGalley | ambient | 8000 |
| `greg_mortimer` | MainGalley | ambient | 5000 |
| `legend_class_nsc` | HVAC_Medical | ambient | 100 |
| `mega_cruise_5000` | AHU_Network_Aft_Dining_Rec | ambient | 15000 |
| `messy_cruise_500` | AHU_Network_Aft_Dining_Rec | ambient | 15000 |
| `san_antonio_class_lpd` | HVAC_Galley | ambient | 400 |
| `san_antonio_class_lpd` | HVAC_Medical | ambient | 200 |
| `spirit_cruise_3000` | MainGalley | ambient | 15000 |

## Literature retrieved

Consensus `search`, `include_full_text_chunks: true`, five queries,
2026-11-16. "Read from" is where the number was read.

| Source | DOI | Consensus | Read from |
|---|---|---|---|
| Hayati, Mattsson, Sandberg 2018 | 10.1080/14733315.2018.1435027 | <https://consensus.app/papers/details/w:6b205f86-12ad-498f-ae00-b63fd2ff6e13/> | Abstract only |
| Jiang, Kobayashi et al. 2022 | 10.1016/j.buildenv.2022.109248 | <https://consensus.app/papers/details/w:6dbe0264-542f-4d2d-9d43-d3fbb64ee848/> | Abstract |
| Gough, Barlow et al. 2019 | 10.1016/j.buildenv.2019.106556 | <https://consensus.app/papers/details/w:25fa4ce4-b750-46b5-80a4-f6cb21cae7e4/> | Abstract |
| Albuquerque, O'Sullivan, Carrilho da Graça 2021 | 10.1016/j.enbuild.2021.111060 | <https://consensus.app/papers/details/w:27d51dfe-7117-4c66-ab68-fdaae107240e/> | Abstract only |
| Luo, Li et al. 2026 | 10.1063/5.0350831 | <https://consensus.app/papers/details/w:40ef1f33-379e-4fbb-831a-a74e79ba8db8/> | Abstract only (CFD) |
| Cheung, Kumar et al. 2025 | 10.1016/j.scitotenv.2024.178286 | <https://consensus.app/papers/details/w:498bfab4-e958-48ae-89f1-d5183fc7554e/> | Abstract |
| Roberts, Adzic et al. 2025 | 10.1016/j.buildenv.2025.113847 | <https://consensus.app/papers/details/w:cc17548f-5952-4ec7-986b-dea72836944d/> | Abstract |

Retrieval miss recorded: the Warren and Parkins single-sided coefficients
(table named in an excerpt, not rendered). Not found: any measured exchange
rate for an open ship deck, ship balcony door, or hatch-open duty.

## Void or changed by this entry

Nothing. No recorded measurement is invalidated. The stage-1 table in
`CONTAM-FIELD-PRESSURE-REVIEW-01` stands; finding 3 explains its
cruise/fiction rows.

## Open decision

The owner decisions D1–D8 in the proposal §7. The first to unblock work is
D1 (data model). The balcony double-count decision (D3) gates only the
balcony stage.

## Per-hull table

Weather zones, weather zones with zero outdoor exchange, balcony zones.

| Hull | Weather zones | of which zero outdoor exchange | Balcony zones |
|---|---|---|---|
| `aeolus_arc3` | 1 | 1 | 0 |
| `alexander_henry_cgs119` | 1 | 1 | 0 |
| `antietam_cvs36` | 3 | 0 | 0 |
| `apl_24` | 2 | 2 | 0 |
| `assistance_ar17` | 4 | 0 | 0 |
| `astoria_ca34` | 5 | 0 | 0 |
| `battler_acv6` | 2 | 0 | 0 |
| `bolster_ars38` | 3 | 3 | 0 |
| `cannon_de701` | 5 | 4 | 0 |
| `castle_class_corvette` | 3 | 2 | 0 |
| `chicago_cg11` | 8 | 0 | 0 |
| `classic_cruise_1900` | 1 | 1 | 26 |
| `cobalt_k124` | 3 | 3 | 0 |
| `cushing_dd376` | 2 | 2 | 0 |
| `davison_dd618` | 6 | 6 | 0 |
| `diamond_princess` | 1 | 1 | 32 |
| `eagle_pe60` | 3 | 3 | 0 |
| `enterprise_galaxy_tng` | 2 | 0 | 0 |
| `erie_pg50` | 5 | 0 | 0 |
| `esteem_mso438` | 6 | 1 | 0 |
| `expedition_cruise_300` | 1 | 1 | 0 |
| `expedition_cruise_450` | 1 | 1 | 8 |
| `fletcher_dde_dd445` | 2 | 2 | 0 |
| `fort_mandan_lsd21` | 3 | 0 | 0 |
| `fort_william_j311` | 3 | 0 | 0 |
| `gordon_gunter_r338` | 4 | 4 | 0 |
| `gosper_apa170` | 8 | 0 | 0 |
| `greg_mortimer` | 6 | 2 | 5 |
| `hunter_killer_dd692` | 6 | 6 | 0 |
| `idaho_bb42` | 1 | 0 | 0 |
| `independence_cvl26` | 5 | 0 | 0 |
| `jupiter_ac3` | 3 | 0 | 0 |
| `keppler_dd765` | 4 | 4 | 0 |
| `legend_class_nsc` | 2 | 0 | 0 |
| `lexington_cv2` | 1 | 1 | 0 |
| `liberty_cargo_ec2` | 3 | 3 | 0 |
| `lsm_354` | 3 | 3 | 0 |
| `luzon_arg2` | 4 | 0 | 0 |
| `lyon_ap71` | 7 | 7 | 0 |
| `mega_cruise_5000` | 1 | 1 | 54 |
| `mercury_aks20` | 2 | 0 | 0 |
| `messy_cruise_500` | 2 | 2 | 0 |
| `miami_cl89` | 2 | 0 | 0 |
| `middlesex_lst983` | 5 | 3 | 0 |
| `midway_cv41` | 1 | 0 | 0 |
| `missouri_bb63` | 5 | 0 | 0 |
| `montana_acr13` | 2 | 0 | 0 |
| `new_jersey_bb62` | 5 | 0 | 0 |
| `new_york_bb34` | 4 | 4 | 0 |
| `nields_dd616` | 6 | 6 | 0 |
| `olympia_c6` | 4 | 4 | 0 |
| `palmer_dms5` | 1 | 1 | 0 |
| `passumpsic_ao106` | 5 | 4 | 0 |
| `pce_874` | 2 | 2 | 0 |
| `pope_ap110` | 4 | 0 | 0 |
| `pt_564` | 2 | 0 | 0 |
| `puncher_cve53` | 1 | 0 | 0 |
| `ranger_cv4` | 2 | 0 | 0 |
| `raven_am55` | 3 | 3 | 0 |
| `river_class_frigate` | 3 | 2 | 0 |
| `rolla_pc483` | 2 | 2 | 0 |
| `ruchamkin_apd89` | 5 | 4 | 0 |
| `san_antonio_class_lpd` | 3 | 0 | 0 |
| `saratoga_cv3` | 1 | 1 | 0 |
| `saratoga_cv60` | 1 | 0 | 0 |
| `savannah_ns` | 7 | 7 | 0 |
| `sigsbee_dd502` | 4 | 4 | 0 |
| `south_dakota_bb49` | 2 | 2 | 0 |
| `spirit_cruise_3000` | 1 | 1 | 28 |
| `squier_ap130` | 1 | 0 | 0 |
| `texas_bb35` | 4 | 4 | 0 |
| `thetis_bay_cve90` | 1 | 0 | 0 |
| `wasp_cv7` | 1 | 0 | 0 |
| `west_virginia_bb48` | 3 | 3 | 0 |
| `winnipeg_j337` | 3 | 0 | 0 |
| `wisconsin_bb64` | 5 | 0 | 0 |
| `wright_cc2` | 3 | 0 | 0 |
| `yorktown_cv5` | 1 | 0 | 0 |

## Per-zone inventory

Line is the zone's `"id"` line in
`data/platforms/<hull>/spatial_layout.json`. Outdoor exchange is the HVAC
group's `ach × duty × oa_fraction` in 1/h (`-` group means ungrouped).

| Class | Hull | Zone | Line | Volume m³ | HVAC group | Outdoor exchange 1/h |
|---|---|---|---|---|---|---|
| balcony | classic_cruise_1900 | PC_D5_P_A | 413 | 800.0 | AHU_Pax_D5 | 0.6 |
| balcony | classic_cruise_1900 | PC_D5_P_F | 383 | 800.0 | AHU_Pax_D5 | 0.6 |
| balcony | classic_cruise_1900 | PC_D5_S_A | 458 | 800.0 | AHU_Pax_D5 | 0.6 |
| balcony | classic_cruise_1900 | PC_D5_S_F | 428 | 800.0 | AHU_Pax_D5 | 0.6 |
| balcony | classic_cruise_1900 | PC_D6_P_A | 503 | 800.0 | AHU_Pax_D6 | 0.6 |
| balcony | classic_cruise_1900 | PC_D6_P_F | 473 | 800.0 | AHU_Pax_D6 | 0.6 |
| balcony | classic_cruise_1900 | PC_D6_S_A | 548 | 800.0 | AHU_Pax_D6 | 0.6 |
| balcony | classic_cruise_1900 | PC_D6_S_F | 518 | 800.0 | AHU_Pax_D6 | 0.6 |
| balcony | classic_cruise_1900 | PC_D7_P_A | 593 | 800.0 | AHU_Pax_D7 | 0.6 |
| balcony | classic_cruise_1900 | PC_D7_P_F | 563 | 800.0 | AHU_Pax_D7 | 0.6 |
| balcony | classic_cruise_1900 | PC_D7_P_M | 578 | 800.0 | AHU_Pax_D7 | 0.6 |
| balcony | classic_cruise_1900 | PC_D7_S_A | 638 | 800.0 | AHU_Pax_D7 | 0.6 |
| balcony | classic_cruise_1900 | PC_D7_S_F | 608 | 800.0 | AHU_Pax_D7 | 0.6 |
| balcony | classic_cruise_1900 | PC_D7_S_M | 623 | 800.0 | AHU_Pax_D7 | 0.6 |
| balcony | classic_cruise_1900 | PC_D8_P_A | 683 | 800.0 | AHU_Pax_D8 | 0.6 |
| balcony | classic_cruise_1900 | PC_D8_P_F | 653 | 800.0 | AHU_Pax_D8 | 0.6 |
| balcony | classic_cruise_1900 | PC_D8_P_M | 668 | 800.0 | AHU_Pax_D8 | 0.6 |
| balcony | classic_cruise_1900 | PC_D8_S_A | 728 | 800.0 | AHU_Pax_D8 | 0.6 |
| balcony | classic_cruise_1900 | PC_D8_S_F | 698 | 800.0 | AHU_Pax_D8 | 0.6 |
| balcony | classic_cruise_1900 | PC_D8_S_M | 713 | 800.0 | AHU_Pax_D8 | 0.6 |
| balcony | classic_cruise_1900 | PC_D9_P_A | 773 | 800.0 | AHU_Pax_D9 | 0.6 |
| balcony | classic_cruise_1900 | PC_D9_P_F | 743 | 800.0 | AHU_Pax_D9 | 0.6 |
| balcony | classic_cruise_1900 | PC_D9_P_M | 758 | 800.0 | AHU_Pax_D9 | 0.6 |
| balcony | classic_cruise_1900 | PC_D9_S_A | 818 | 800.0 | AHU_Pax_D9 | 0.6 |
| balcony | classic_cruise_1900 | PC_D9_S_F | 788 | 800.0 | AHU_Pax_D9 | 0.6 |
| balcony | classic_cruise_1900 | PC_D9_S_M | 803 | 800.0 | AHU_Pax_D9 | 0.6 |
| balcony | diamond_princess | PC_D10_P_A | 1144 | 1300.0 | AHU_Pax_D10 | 0.6 |
| balcony | diamond_princess | PC_D10_P_F | 1114 | 1300.0 | AHU_Pax_D10 | 0.6 |
| balcony | diamond_princess | PC_D10_P_M | 1129 | 1300.0 | AHU_Pax_D10 | 0.6 |
| balcony | diamond_princess | PC_D10_S_A | 1189 | 1300.0 | AHU_Pax_D10 | 0.6 |
| balcony | diamond_princess | PC_D10_S_F | 1159 | 1300.0 | AHU_Pax_D10 | 0.6 |
| balcony | diamond_princess | PC_D10_S_M | 1174 | 1300.0 | AHU_Pax_D10 | 0.6 |
| balcony | diamond_princess | PC_D11_P_A | 1234 | 1300.0 | AHU_Pax_D11 | 0.6 |
| balcony | diamond_princess | PC_D11_P_F | 1204 | 1300.0 | AHU_Pax_D11 | 0.6 |
| balcony | diamond_princess | PC_D11_P_M | 1219 | 1300.0 | AHU_Pax_D11 | 0.6 |
| balcony | diamond_princess | PC_D11_S_A | 1279 | 1300.0 | AHU_Pax_D11 | 0.6 |
| balcony | diamond_princess | PC_D11_S_F | 1249 | 1300.0 | AHU_Pax_D11 | 0.6 |
| balcony | diamond_princess | PC_D11_S_M | 1264 | 1300.0 | AHU_Pax_D11 | 0.6 |
| balcony | diamond_princess | PC_D12_P_A | 1324 | 1300.0 | AHU_Pax_D12 | 0.6 |
| balcony | diamond_princess | PC_D12_P_F | 1294 | 1300.0 | AHU_Pax_D12 | 0.6 |
| balcony | diamond_princess | PC_D12_P_M | 1309 | 1300.0 | AHU_Pax_D12 | 0.6 |
| balcony | diamond_princess | PC_D12_S_A | 1369 | 1300.0 | AHU_Pax_D12 | 0.6 |
| balcony | diamond_princess | PC_D12_S_F | 1339 | 1300.0 | AHU_Pax_D12 | 0.6 |
| balcony | diamond_princess | PC_D12_S_M | 1354 | 1300.0 | AHU_Pax_D12 | 0.6 |
| balcony | diamond_princess | PC_D14_P_F | 1735 | 1300.0 | AHU_PC_D14 | 0.6 |
| balcony | diamond_princess | PC_D14_S_F | 1750 | 1300.0 | AHU_PC_D14 | 0.6 |
| balcony | diamond_princess | PC_D5_P_F | 1555 | 900.0 | AHU_PC_D5 | 0.6 |
| balcony | diamond_princess | PC_D5_S_F | 1600 | 900.0 | AHU_PC_D5 | 0.6 |
| balcony | diamond_princess | PC_D6_P_F | 1645 | 900.0 | AHU_PC_D6 | 0.6 |
| balcony | diamond_princess | PC_D6_S_F | 1690 | 900.0 | AHU_PC_D6 | 0.6 |
| balcony | diamond_princess | PC_D8_P_A | 964 | 1300.0 | AHU_Pax_D8 | 0.6 |
| balcony | diamond_princess | PC_D8_P_F | 934 | 1300.0 | AHU_Pax_D8 | 0.6 |
| balcony | diamond_princess | PC_D8_S_A | 1009 | 1300.0 | AHU_Pax_D8 | 0.6 |
| balcony | diamond_princess | PC_D8_S_F | 979 | 1300.0 | AHU_Pax_D8 | 0.6 |
| balcony | diamond_princess | PC_D9_P_A | 1054 | 1300.0 | AHU_Pax_D9 | 0.6 |
| balcony | diamond_princess | PC_D9_P_F | 1024 | 1300.0 | AHU_Pax_D9 | 0.6 |
| balcony | diamond_princess | PC_D9_S_A | 1099 | 1300.0 | AHU_Pax_D9 | 0.6 |
| balcony | diamond_princess | PC_D9_S_F | 1069 | 1300.0 | AHU_Pax_D9 | 0.6 |
| balcony | expedition_cruise_450 | PC_D5_P_A | 336 | 600.0 | AHU_Pax_D5 | 0.6 |
| balcony | expedition_cruise_450 | PC_D5_P_F | 321 | 600.0 | AHU_Pax_D5 | 0.6 |
| balcony | expedition_cruise_450 | PC_D5_S_A | 366 | 600.0 | AHU_Pax_D5 | 0.6 |
| balcony | expedition_cruise_450 | PC_D5_S_F | 351 | 600.0 | AHU_Pax_D5 | 0.6 |
| balcony | expedition_cruise_450 | PC_D6_P_A | 396 | 600.0 | AHU_Pax_D6 | 0.6 |
| balcony | expedition_cruise_450 | PC_D6_P_F | 381 | 600.0 | AHU_Pax_D6 | 0.6 |
| balcony | expedition_cruise_450 | PC_D6_S_A | 426 | 600.0 | AHU_Pax_D6 | 0.6 |
| balcony | expedition_cruise_450 | PC_D6_S_F | 411 | 600.0 | AHU_Pax_D6 | 0.6 |
| balcony | greg_mortimer | PC_D4_A | 65 | 420.0 | AHU_Cabins_D4 | 0.6 |
| balcony | greg_mortimer | PC_D4_F | 50 | 420.0 | AHU_Cabins_D4 | 0.6 |
| balcony | greg_mortimer | PC_D6_A | 95 | 360.0 | AHU_Cabins_D6 | 0.6 |
| balcony | greg_mortimer | PC_D6_F | 80 | 360.0 | AHU_Cabins_D6 | 0.6 |
| balcony | greg_mortimer | PC_D7_Suites | 110 | 180.0 | AHU_Cabins_D7 | 0.6 |
| balcony | mega_cruise_5000 | PC_D10_P_A | 1094 | 1200.0 | AHU_Pax_Deck_D10 | 0.6 |
| balcony | mega_cruise_5000 | PC_D10_P_F | 1064 | 1200.0 | AHU_Pax_Deck_D10 | 0.6 |
| balcony | mega_cruise_5000 | PC_D10_P_M | 1079 | 1200.0 | AHU_Pax_Deck_D10 | 0.6 |
| balcony | mega_cruise_5000 | PC_D10_S_A | 1139 | 1200.0 | AHU_Pax_Deck_D10 | 0.6 |
| balcony | mega_cruise_5000 | PC_D10_S_F | 1109 | 1200.0 | AHU_Pax_Deck_D10 | 0.6 |
| balcony | mega_cruise_5000 | PC_D10_S_M | 1124 | 1200.0 | AHU_Pax_Deck_D10 | 0.6 |
| balcony | mega_cruise_5000 | PC_D11_P_A | 1229 | 1200.0 | AHU_Pax_Deck_D11 | 0.6 |
| balcony | mega_cruise_5000 | PC_D11_P_F | 1199 | 1200.0 | AHU_Pax_Deck_D11 | 0.6 |
| balcony | mega_cruise_5000 | PC_D11_P_M | 1214 | 1200.0 | AHU_Pax_Deck_D11 | 0.6 |
| balcony | mega_cruise_5000 | PC_D11_S_A | 1274 | 1200.0 | AHU_Pax_Deck_D11 | 0.6 |
| balcony | mega_cruise_5000 | PC_D11_S_F | 1244 | 1200.0 | AHU_Pax_Deck_D11 | 0.6 |
| balcony | mega_cruise_5000 | PC_D11_S_M | 1259 | 1200.0 | AHU_Pax_Deck_D11 | 0.6 |
| balcony | mega_cruise_5000 | PC_D12_P_A | 1364 | 1200.0 | AHU_Pax_Deck_D12 | 0.6 |
| balcony | mega_cruise_5000 | PC_D12_P_F | 1334 | 1200.0 | AHU_Pax_Deck_D12 | 0.6 |
| balcony | mega_cruise_5000 | PC_D12_P_M | 1349 | 1200.0 | AHU_Pax_Deck_D12 | 0.6 |
| balcony | mega_cruise_5000 | PC_D12_S_A | 1409 | 1200.0 | AHU_Pax_Deck_D12 | 0.6 |
| balcony | mega_cruise_5000 | PC_D12_S_F | 1379 | 1200.0 | AHU_Pax_Deck_D12 | 0.6 |
| balcony | mega_cruise_5000 | PC_D12_S_M | 1394 | 1200.0 | AHU_Pax_Deck_D12 | 0.6 |
| balcony | mega_cruise_5000 | PC_D13_P_A | 1499 | 1200.0 | AHU_Pax_Deck_D13 | 0.6 |
| balcony | mega_cruise_5000 | PC_D13_P_F | 1469 | 1200.0 | AHU_Pax_Deck_D13 | 0.6 |
| balcony | mega_cruise_5000 | PC_D13_P_M | 1484 | 1200.0 | AHU_Pax_Deck_D13 | 0.6 |
| balcony | mega_cruise_5000 | PC_D13_S_A | 1544 | 1200.0 | AHU_Pax_Deck_D13 | 0.6 |
| balcony | mega_cruise_5000 | PC_D13_S_F | 1514 | 1200.0 | AHU_Pax_Deck_D13 | 0.6 |
| balcony | mega_cruise_5000 | PC_D13_S_M | 1529 | 1200.0 | AHU_Pax_Deck_D13 | 0.6 |
| balcony | mega_cruise_5000 | PC_D14_P_A | 1634 | 1200.0 | AHU_Pax_Deck_D14 | 0.6 |
| balcony | mega_cruise_5000 | PC_D14_P_F | 1604 | 1200.0 | AHU_Pax_Deck_D14 | 0.6 |
| balcony | mega_cruise_5000 | PC_D14_P_M | 1619 | 1200.0 | AHU_Pax_Deck_D14 | 0.6 |
| balcony | mega_cruise_5000 | PC_D14_S_A | 1679 | 1200.0 | AHU_Pax_Deck_D14 | 0.6 |
| balcony | mega_cruise_5000 | PC_D14_S_F | 1649 | 1200.0 | AHU_Pax_Deck_D14 | 0.6 |
| balcony | mega_cruise_5000 | PC_D14_S_M | 1664 | 1200.0 | AHU_Pax_Deck_D14 | 0.6 |
| balcony | mega_cruise_5000 | PC_D6_P_A | 554 | 1200.0 | AHU_Pax_Deck_D6 | 0.6 |
| balcony | mega_cruise_5000 | PC_D6_P_F | 524 | 1200.0 | AHU_Pax_Deck_D6 | 0.6 |
| balcony | mega_cruise_5000 | PC_D6_P_M | 539 | 1200.0 | AHU_Pax_Deck_D6 | 0.6 |
| balcony | mega_cruise_5000 | PC_D6_S_A | 599 | 1200.0 | AHU_Pax_Deck_D6 | 0.6 |
| balcony | mega_cruise_5000 | PC_D6_S_F | 569 | 1200.0 | AHU_Pax_Deck_D6 | 0.6 |
| balcony | mega_cruise_5000 | PC_D6_S_M | 584 | 1200.0 | AHU_Pax_Deck_D6 | 0.6 |
| balcony | mega_cruise_5000 | PC_D7_P_A | 689 | 1200.0 | AHU_Pax_Deck_D7 | 0.6 |
| balcony | mega_cruise_5000 | PC_D7_P_F | 659 | 1200.0 | AHU_Pax_Deck_D7 | 0.6 |
| balcony | mega_cruise_5000 | PC_D7_P_M | 674 | 1200.0 | AHU_Pax_Deck_D7 | 0.6 |
| balcony | mega_cruise_5000 | PC_D7_S_A | 734 | 1200.0 | AHU_Pax_Deck_D7 | 0.6 |
| balcony | mega_cruise_5000 | PC_D7_S_F | 704 | 1200.0 | AHU_Pax_Deck_D7 | 0.6 |
| balcony | mega_cruise_5000 | PC_D7_S_M | 719 | 1200.0 | AHU_Pax_Deck_D7 | 0.6 |
| balcony | mega_cruise_5000 | PC_D8_P_A | 824 | 1200.0 | AHU_Pax_Deck_D8 | 0.6 |
| balcony | mega_cruise_5000 | PC_D8_P_F | 794 | 1200.0 | AHU_Pax_Deck_D8 | 0.6 |
| balcony | mega_cruise_5000 | PC_D8_P_M | 809 | 1200.0 | AHU_Pax_Deck_D8 | 0.6 |
| balcony | mega_cruise_5000 | PC_D8_S_A | 869 | 1200.0 | AHU_Pax_Deck_D8 | 0.6 |
| balcony | mega_cruise_5000 | PC_D8_S_F | 839 | 1200.0 | AHU_Pax_Deck_D8 | 0.6 |
| balcony | mega_cruise_5000 | PC_D8_S_M | 854 | 1200.0 | AHU_Pax_Deck_D8 | 0.6 |
| balcony | mega_cruise_5000 | PC_D9_P_A | 959 | 1200.0 | AHU_Pax_Deck_D9 | 0.6 |
| balcony | mega_cruise_5000 | PC_D9_P_F | 929 | 1200.0 | AHU_Pax_Deck_D9 | 0.6 |
| balcony | mega_cruise_5000 | PC_D9_P_M | 944 | 1200.0 | AHU_Pax_Deck_D9 | 0.6 |
| balcony | mega_cruise_5000 | PC_D9_S_A | 1004 | 1200.0 | AHU_Pax_Deck_D9 | 0.6 |
| balcony | mega_cruise_5000 | PC_D9_S_F | 974 | 1200.0 | AHU_Pax_Deck_D9 | 0.6 |
| balcony | mega_cruise_5000 | PC_D9_S_M | 989 | 1200.0 | AHU_Pax_Deck_D9 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D10_P_A | 1005 | 900.0 | AHU_Pax_D10 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D10_P_F | 975 | 900.0 | AHU_Pax_D10 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D10_S_A | 1050 | 900.0 | AHU_Pax_D10 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D10_S_F | 1020 | 900.0 | AHU_Pax_D10 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D11_P_A | 1095 | 900.0 | AHU_Pax_D11 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D11_P_F | 1065 | 900.0 | AHU_Pax_D11 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D11_S_A | 1140 | 900.0 | AHU_Pax_D11 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D11_S_F | 1110 | 900.0 | AHU_Pax_D11 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D5_P_A | 555 | 900.0 | AHU_Pax_D5 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D5_P_F | 525 | 900.0 | AHU_Pax_D5 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D5_S_A | 600 | 900.0 | AHU_Pax_D5 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D5_S_F | 570 | 900.0 | AHU_Pax_D5 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D6_P_A | 645 | 900.0 | AHU_Pax_D6 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D6_P_F | 615 | 900.0 | AHU_Pax_D6 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D6_S_A | 690 | 900.0 | AHU_Pax_D6 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D6_S_F | 660 | 900.0 | AHU_Pax_D6 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D7_P_A | 735 | 900.0 | AHU_Pax_D7 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D7_P_F | 705 | 900.0 | AHU_Pax_D7 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D7_S_A | 780 | 900.0 | AHU_Pax_D7 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D7_S_F | 750 | 900.0 | AHU_Pax_D7 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D8_P_A | 825 | 900.0 | AHU_Pax_D8 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D8_P_F | 795 | 900.0 | AHU_Pax_D8 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D8_S_A | 870 | 900.0 | AHU_Pax_D8 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D8_S_F | 840 | 900.0 | AHU_Pax_D8 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D9_P_A | 915 | 900.0 | AHU_Pax_D9 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D9_P_F | 885 | 900.0 | AHU_Pax_D9 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D9_S_A | 960 | 900.0 | AHU_Pax_D9 | 0.6 |
| balcony | spirit_cruise_3000 | PC_D9_S_F | 930 | 900.0 | AHU_Pax_D9 | 0.6 |
| weather | aeolus_arc3 | Cable_Working_Deck | 101 | 2326.53 | AHU_Weather | 0.0 |
| weather | alexander_henry_cgs119 | Boat_Stowage_Open | 115 | 114.57 | AHU_Weather | 0.0 |
| weather | antietam_cvs36 | Flight_Deck | 62 | 25000.0 | VENT_Weather | 0.5 |
| weather | antietam_cvs36 | Forecastle_Deck | 208 | 7000.0 | VENT_Weather | 0.5 |
| weather | antietam_cvs36 | Gallery_Deck | 77 | 17500.0 | VENT_Hangar | 1.6 |
| weather | apl_24 | Fantail_Main | 14 | 128.12 | - | 0.0 |
| weather | apl_24 | Fantail_Upper | 267 | 195.13 | - | 0.0 |
| weather | assistance_ar17 | Boat_Deck_Fwd | 254 | 437.76 | HVAC_Accom | 3.0 |
| weather | assistance_ar17 | Boat_Gun_Deck_Aft | 171 | 984.97 | HVAC_Accom | 3.0 |
| weather | assistance_ar17 | Fwd_Working_Deck | 445 | 472.03 | HVAC_Accom | 3.0 |
| weather | assistance_ar17 | Stern_Working_Deck | 269 | 633.07 | HVAC_Accom | 3.0 |
| weather | astoria_ca34 | Boat_Deck | 156 | 1421.54 | VENT_Weather | 0.5 |
| weather | astoria_ca34 | Catapult_Deck | 261 | 885.4 | VENT_Weather | 0.5 |
| weather | astoria_ca34 | Fantail | 246 | 442.7 | VENT_Weather | 0.5 |
| weather | astoria_ca34 | Focsle_Deck | 231 | 743.79 | VENT_Weather | 0.5 |
| weather | astoria_ca34 | Upper_Deck_Aft | 120 | 408.49 | VENT_Weather | 0.5 |
| weather | battler_acv6 | Flight_Deck | 812 | 7923.41 | VENT_Weather | 0.5 |
| weather | battler_acv6 | Walkways_Focsle | 673 | 2102.53 | VENT_Weather | 0.5 |
| weather | bolster_ars38 | Focsle_Deck_Open | 44 | 145.21 | - | 0.0 |
| weather | bolster_ars38 | Focsle_Open_Aft | 106 | 531.22 | - | 0.0 |
| weather | bolster_ars38 | Salvage_Deck | 239 | 527.87 | - | 0.0 |
| weather | cannon_de701 | Fantail | 106 | 213.08 | - | 0.0 |
| weather | cannon_de701 | Focsle_Deck | 269 | 344.12 | - | 0.0 |
| weather | cannon_de701 | Gun_Deck_Open | 44 | 1051.33 | - | 0.0 |
| weather | cannon_de701 | Island_Open_Aft | 91 | 182.66 | - | 0.0 |
| weather | cannon_de701 | Signal_Deck | 29 | 85.06 | HVAC_Accom | 0.9 |
| weather | castle_class_corvette | Foc_Deck_Open | 113 | 307.84 | - | 0.0 |
| weather | castle_class_corvette | Quarterdeck | 128 | 575.42 | - | 0.0 |
| weather | castle_class_corvette | Upper_Deck_Aft | 212 | 395.93 | HVAC_Accom | 0.75 |
| weather | chicago_cg11 | Bow_Weather | 331 | 377.28 | VENT_Weather | 0.5 |
| weather | chicago_cg11 | Fantail_Weather | 181 | 288.2 | VENT_Weather | 0.5 |
| weather | chicago_cg11 | Forecastle_Deck | 316 | 576.4 | VENT_Weather | 0.5 |
| weather | chicago_cg11 | Helo_Deck | 196 | 2200.8 | VENT_Weather | 0.5 |
| weather | chicago_cg11 | Helo_Deck_02_Aft | 61 | 432.91 | VENT_Weather | 0.5 |
| weather | chicago_cg11 | Launcher_Deck_01 | 166 | 430.98 | VENT_Weather | 0.5 |
| weather | chicago_cg11 | Open_03 | 46 | 279.39 | VENT_Weather | 0.5 |
| weather | chicago_cg11 | Terrier_Deck_02 | 106 | 1057.55 | VENT_Weather | 0.5 |
| weather | classic_cruise_1900 | PoolDeck | 111 | 2100.0 | - | 0.0 |
| weather | cobalt_k124 | Foc_Deck_Open | 44 | 390.92 | - | 0.0 |
| weather | cobalt_k124 | Quarterdeck | 59 | 774.96 | - | 0.0 |
| weather | cobalt_k124 | Stern_Open | 74 | 768.64 | - | 0.0 |
| weather | cushing_dd376 | Fantail | 124 | 158.06 | - | 0.0 |
| weather | cushing_dd376 | Focsle_Open | 109 | 138.29 | - | 0.0 |
| weather | davison_dd618 | After_Deckhouse_Top | 61 | 272.3 | - | 0.0 |
| weather | davison_dd618 | Bow_Focsle | 322 | 36.44 | - | 0.0 |
| weather | davison_dd618 | Fantail_MS | 138 | 233.9 | - | 0.0 |
| weather | davison_dd618 | Focsle_Open | 123 | 397.61 | - | 0.0 |
| weather | davison_dd618 | Midship_Deckhouse | 76 | 266.96 | - | 0.0 |
| weather | davison_dd618 | Super_Open | 46 | 205.45 | - | 0.0 |
| weather | diamond_princess | OpenAirCinema | 733 | 800.0 | - | 0.0 |
| weather | eagle_pe60 | Fantail | 237 | 55.37 | - | 0.0 |
| weather | eagle_pe60 | Gun_Deck_Fwd | 332 | 114.19 | - | 0.0 |
| weather | eagle_pe60 | Open_Bridge | 30 | 41.27 | - | 0.0 |
| weather | enterprise_galaxy_tng | Holodeck1 | 81 | 260.0 | AHU_Public | 0.675 |
| weather | enterprise_galaxy_tng | Holodeck2 | 94 | 260.0 | AHU_Public | 0.675 |
| weather | erie_pg50 | Fantail_Aft | 225 | 146.73 | VENT_Weather | 6.0 |
| weather | erie_pg50 | Focsle_Main | 456 | 272.5 | VENT_Weather | 6.0 |
| weather | erie_pg50 | Focsle_Stores | 612 | 251.54 | HVAC_Accom | 3.0 |
| weather | erie_pg50 | Gun_Deck_Aft | 240 | 373.49 | VENT_Weather | 6.0 |
| weather | erie_pg50 | Sup_Deck_Open | 150 | 392.5 | VENT_Weather | 6.0 |
| weather | esteem_mso438 | Boat_Deck_Aft | 75 | 305.27 | VENT_Weather | 6.0 |
| weather | esteem_mso438 | Deck_House_Main | 166 | 37.76 | HVAC_Accom | 1.2 |
| weather | esteem_mso438 | Focsle_01 | 136 | 305.27 | VENT_Weather | 6.0 |
| weather | esteem_mso438 | Focsle_Store | 395 | 33.56 | - | 0.0 |
| weather | esteem_mso438 | Reel_Deck | 60 | 188.53 | VENT_Weather | 6.0 |
| weather | esteem_mso438 | Sweep_Deck | 151 | 327.65 | VENT_Weather | 6.0 |
| weather | expedition_cruise_300 | Pool_Deck | 24 | 1050.0 | - | 0.0 |
| weather | expedition_cruise_450 | PoolDeck | 79 | 1050.0 | - | 0.0 |
| weather | fletcher_dde_dd445 | Fantail | 14 | 419.62 | - | 0.0 |
| weather | fletcher_dde_dd445 | Focsle_Main | 92 | 233.12 | - | 0.0 |
| weather | fort_mandan_lsd21 | Top_House_Open | 14 | 1094.47 | VENT_Machinery_Holds | 4.5 |
| weather | fort_mandan_lsd21 | Well_Cover_Open | 241 | 2162.21 | VENT_Well_Deck | 2.0 |
| weather | fort_mandan_lsd21 | Well_Deck | 557 | 13000.0 | VENT_Well_Deck | 2.0 |
| weather | fort_william_j311 | Foc_Deck_Open | 74 | 250.49 | VENT_Machinery | 2.0 |
| weather | fort_william_j311 | Quarterdeck | 44 | 319.01 | VENT_Machinery | 2.0 |
| weather | fort_william_j311 | Signal_Deck | 14 | 201.29 | HVAC_Accom | 2.5 |
| weather | gordon_gunter_r338 | Aft_Working_Deck | 423 | 333.07 | - | 0.0 |
| weather | gordon_gunter_r338 | Boat_Deck | 101 | 663.25 | - | 0.0 |
| weather | gordon_gunter_r338 | Mission_Deck | 438 | 550.11 | - | 0.0 |
| weather | gordon_gunter_r338 | Shelter_Deck | 200 | 605.22 | - | 0.0 |
| weather | gosper_apa170 | Boat_Deck_Open | 92 | 756.34 | VENT_Machinery_Holds | 4.5 |
| weather | gosper_apa170 | Boat_Deck_Open_Fwd | 107 | 1368.62 | VENT_Machinery_Holds | 4.5 |
| weather | gosper_apa170 | Boat_Stowage_Deck | 250 | 380.33 | VENT_Machinery_Holds | 4.5 |
| weather | gosper_apa170 | Fantail | 219 | 311.19 | VENT_Machinery_Holds | 4.5 |
| weather | gosper_apa170 | Focsle_Deck_Open | 174 | 690.21 | VENT_Machinery_Holds | 4.5 |
| weather | gosper_apa170 | Focsle_Stores | 204 | 100.19 | VENT_Berthing_Messing | 1.2 |
| weather | gosper_apa170 | Focsle_Stores_2D | 732 | 490.3 | VENT_Berthing_Messing | 1.2 |
| weather | gosper_apa170 | Main_Deck_Open_Fwd | 450 | 646.55 | VENT_Machinery_Holds | 4.5 |
| weather | greg_mortimer | BarsDeck5 | 321 | 100.0 | AHU_Public_Main | 0.8 |
| weather | greg_mortimer | BarsDeck8 | 451 | 100.0 | AHU_Observation | 0.8 |
| weather | greg_mortimer | ObsDeck7 | 425 | 180.0 | AHU_Observation | 0.8 |
| weather | greg_mortimer | ObsDeck8 | 490 | 160.0 | AHU_Observation | 0.8 |
| weather | greg_mortimer | SunDeck | 399 | 300.0 | - | 0.0 |
| weather | greg_mortimer | TopDeck | 438 | 250.0 | - | 0.0 |
| weather | hunter_killer_dd692 | Boat_Deck_01 | 626 | 674.62 | - | 0.0 |
| weather | hunter_killer_dd692 | Fantail | 719 | 377.46 | - | 0.0 |
| weather | hunter_killer_dd692 | Focsle_Fwd | 950 | 449.81 | - | 0.0 |
| weather | hunter_killer_dd692 | Fwd_Mount_Deck | 935 | 327.13 | - | 0.0 |
| weather | hunter_killer_dd692 | Launcher_Deck_01 | 704 | 248.38 | - | 0.0 |
| weather | hunter_killer_dd692 | Torpedo_Deck | 734 | 283.1 | - | 0.0 |
| weather | idaho_bb42 | Fantail | 365 | 772.5 | HVAC_Main | 3.0 |
| weather | independence_cvl26 | Flight_Deck | 62 | 9954.8 | VENT_Weather | 0.5 |
| weather | independence_cvl26 | Focsle_Stores | 284 | 456.18 | VENT_Tanks | 1.8 |
| weather | independence_cvl26 | Forecastle_Deck | 140 | 1163.92 | VENT_Weather | 0.5 |
| weather | independence_cvl26 | Gallery_Deck | 110 | 2754.85 | VENT_Hangar | 1.6 |
| weather | independence_cvl26 | Poop_Deck | 125 | 708.74 | VENT_Weather | 0.5 |
| weather | jupiter_ac3 | Focsle_Deck_Open | 230 | 420.0 | VENT_Cargo | 2.0 |
| weather | jupiter_ac3 | Passage_Deckhouse | 200 | 77.21 | VENT_Accom | 0.9 |
| weather | jupiter_ac3 | Poop_Deck_Open | 215 | 6343.67 | VENT_Cargo | 2.0 |
| weather | keppler_dd765 | Fantail | 216 | 282.59 | - | 0.0 |
| weather | keppler_dd765 | Focsle_Fwd | 432 | 268.46 | - | 0.0 |
| weather | keppler_dd765 | Gun_Deck_Aft | 231 | 361.85 | - | 0.0 |
| weather | keppler_dd765 | Weather_Deck_01 | 123 | 574.89 | - | 0.0 |
| weather | legend_class_nsc | Boat_Deck | 219 | 80.0 | HVAC_Aviation | 3.2 |
| weather | legend_class_nsc | Flight_Deck | 167 | 200.0 | HVAC_Aviation | 3.2 |
| weather | lexington_cv2 | Flight_Deck | 14 | 14777.49 | - | 0.0 |
| weather | liberty_cargo_ec2 | Aft_Deck_Open | 297 | 156.23 | AHU_Weather | 0.0 |
| weather | liberty_cargo_ec2 | Boat_Deck_Open | 250 | 90.22 | AHU_Weather | 0.0 |
| weather | liberty_cargo_ec2 | Forecastle_Deck | 625 | 71.02 | AHU_Weather | 0.0 |
| weather | lsm_354 | Forecastle_Weather | 14 | 445.8 | - | 0.0 |
| weather | lsm_354 | Weather_Aft_Super | 92 | 384.66 | - | 0.0 |
| weather | lsm_354 | Weather_Fwd_Super | 139 | 624.86 | - | 0.0 |
| weather | luzon_arg2 | Boat_Deck_Aft | 97 | 788.7 | HVAC_Accom | 3.0 |
| weather | luzon_arg2 | Chain_Locker_Focsle | 479 | 71.53 | HVAC_Accom | 3.0 |
| weather | luzon_arg2 | Gun_Weather_Sup | 82 | 318.05 | HVAC_Accom | 3.0 |
| weather | luzon_arg2 | Stern_Weather | 226 | 510.9 | HVAC_Accom | 3.0 |
| weather | lyon_ap71 | Boat_Deck_Walkway | 127 | 473.71 | - | 0.0 |
| weather | lyon_ap71 | Bow_Shelter_Weather | 461 | 308.36 | - | 0.0 |
| weather | lyon_ap71 | Forecastle_Weather | 204 | 1894.84 | - | 0.0 |
| weather | lyon_ap71 | Hatch_3_Weather | 446 | 827.44 | - | 0.0 |
| weather | lyon_ap71 | Hatch_4_Weather | 234 | 886.55 | - | 0.0 |
| weather | lyon_ap71 | Quarter_Weather | 431 | 783.76 | - | 0.0 |
| weather | lyon_ap71 | Stern_Weather_Shelter | 219 | 755.49 | - | 0.0 |
| weather | mega_cruise_5000 | Main_Pool_Deck | 46 | 9000.0 | - | 0.0 |
| weather | mercury_aks20 | Fantail | 77 | 1411.67 | HVAC_Accom | 3.0 |
| weather | mercury_aks20 | Foredeck | 369 | 801.9 | HVAC_Accom | 3.0 |
| weather | messy_cruise_500 | Central_Park_Open_Atrium | 128 | 36000.0 | - | 0.0 |
| weather | messy_cruise_500 | Main_Pool_Deck | 37 | 9000.0 | - | 0.0 |
| weather | miami_cl89 | Bow_Weather | 411 | 431.03 | VENT_Weather | 0.5 |
| weather | miami_cl89 | Catapult_Deck | 195 | 410.5 | VENT_Weather | 0.5 |
| weather | middlesex_lst983 | Boat_Deck | 29 | 170.06 | - | 0.0 |
| weather | middlesex_lst983 | Fantail_Main | 122 | 60.22 | - | 0.0 |
| weather | middlesex_lst983 | Tank_Deck | 429 | 4200.0 | HVAC_TankDeck | 1.2 |
| weather | middlesex_lst983 | Tank_Deck_Port | 511 | 444.76 | HVAC_TankDeck | 1.2 |
| weather | middlesex_lst983 | Weather_Deck_Amids | 283 | 1179.95 | - | 0.0 |
| weather | midway_cv41 | Flight_Deck | 79 | 28293.69 | VENT_Weather | 0.5 |
| weather | missouri_bb63 | Boat_Waist_Open | 213 | 4485.1 | VENT_Weather | 0.5 |
| weather | missouri_bb63 | Fantail_Open | 198 | 2456.15 | VENT_Weather | 0.5 |
| weather | missouri_bb63 | Focsle_Void_2D | 728 | 313.24 | VENT_Weather | 0.5 |
| weather | missouri_bb63 | Forecastle_Open | 343 | 5446.21 | VENT_Weather | 0.5 |
| weather | missouri_bb63 | Signal_Deck | 51 | 399.28 | VENT_Weather | 0.5 |
| weather | montana_acr13 | MD_Aft_Open | 94 | 378.11 | VENT_Weather | 15.0 |
| weather | montana_acr13 | MD_Forecastle_Open | 470 | 1124.22 | VENT_Weather | 15.0 |
| weather | new_jersey_bb62 | Boat_Waist_Open | 213 | 4485.85 | VENT_Weather | 0.5 |
| weather | new_jersey_bb62 | Fantail_Open | 198 | 2456.44 | VENT_Weather | 0.5 |
| weather | new_jersey_bb62 | Focsle_Void_2D | 728 | 313.07 | VENT_Weather | 0.5 |
| weather | new_jersey_bb62 | Forecastle_Open | 343 | 5445.58 | VENT_Weather | 0.5 |
| weather | new_jersey_bb62 | Signal_Deck | 51 | 399.05 | VENT_Weather | 0.5 |
| weather | new_york_bb34 | Fantail_Weather | 16 | 900.0 | - | 0.0 |
| weather | new_york_bb34 | Focsle_Deck | 173 | 1500.0 | - | 0.0 |
| weather | new_york_bb34 | Super_Deck_Open | 188 | 1043.17 | - | 0.0 |
| weather | new_york_bb34 | Weather_Deck_Aft | 31 | 1600.0 | - | 0.0 |
| weather | nields_dd616 | After_Deckhouse_Top | 61 | 318.0 | - | 0.0 |
| weather | nields_dd616 | Bow_Focsle | 322 | 58.86 | - | 0.0 |
| weather | nields_dd616 | Fantail | 138 | 210.78 | - | 0.0 |
| weather | nields_dd616 | Focsle_Open | 123 | 403.42 | - | 0.0 |
| weather | nields_dd616 | Midship_Deckhouse | 76 | 212.95 | - | 0.0 |
| weather | nields_dd616 | Super_Open | 46 | 335.68 | - | 0.0 |
| weather | olympia_c6 | MD_Forecastle_Open | 437 | 380.68 | - | 0.0 |
| weather | olympia_c6 | MD_Stern_Fantail | 210 | 326.3 | - | 0.0 |
| weather | olympia_c6 | SD_Forecastle_Open | 195 | 201.26 | - | 0.0 |
| weather | olympia_c6 | SD_Stern_Open | 14 | 272.48 | - | 0.0 |
| weather | palmer_dms5 | Boat_Deck_Uptakes | 170 | 199.09 | - | 0.0 |
| weather | passumpsic_ao106 | Aft_Open_Deck | 254 | 140.53 | - | 0.0 |
| weather | passumpsic_ao106 | Focsle_Deck | 75 | 1162.15 | - | 0.0 |
| weather | passumpsic_ao106 | Island_Deck | 44 | 2029.15 | - | 0.0 |
| weather | passumpsic_ao106 | Signal_Deck | 29 | 121.79 | HVAC_Accom | 0.9 |
| weather | passumpsic_ao106 | Working_Deck | 239 | 2953.08 | - | 0.0 |
| weather | pce_874 | Fantail | 44 | 195.49 | - | 0.0 |
| weather | pce_874 | Focsle_Deck | 207 | 116.15 | - | 0.0 |
| weather | pope_ap110 | Boat_Deck_Open | 227 | 1088.42 | VENT_Stores_Holds | 0.8 |
| weather | pope_ap110 | Focsle_Deck | 451 | 501.46 | VENT_Stores_Holds | 0.8 |
| weather | pope_ap110 | Stern_Gun_Deck | 242 | 537.28 | VENT_Stores_Holds | 0.8 |
| weather | pope_ap110 | Sup_Deck_Mech | 78 | 386.77 | VENT_Stores_Holds | 0.8 |
| weather | pt_564 | Foredeck | 74 | 15.56 | VENT_Weather | 3.6 |
| weather | pt_564 | Torpedo_Deck | 29 | 58.49 | VENT_Weather | 3.6 |
| weather | puncher_cve53 | Flight_Deck | 61 | 8561.99 | VENT_Weather | 0.5 |
| weather | ranger_cv4 | Flight_Deck | 14 | 16520.85 | VENT_Weather | 0.5 |
| weather | ranger_cv4 | Poop_Deck | 186 | 1452.63 | VENT_Weather | 0.5 |
| weather | raven_am55 | Foc_Deck_Fwd | 151 | 312.85 | - | 0.0 |
| weather | raven_am55 | Foc_Deck_Open | 166 | 198.14 | - | 0.0 |
| weather | raven_am55 | Sweep_Deck | 181 | 111.4 | - | 0.0 |
| weather | river_class_frigate | Foc_Deck_Open | 74 | 526.42 | - | 0.0 |
| weather | river_class_frigate | Quarterdeck | 44 | 983.77 | - | 0.0 |
| weather | river_class_frigate | Signal_Deck | 14 | 521.1 | HVAC_Accom | 2.5 |
| weather | rolla_pc483 | Fantail | 30 | 106.13 | - | 0.0 |
| weather | rolla_pc483 | Focsle_Deck | 173 | 130.01 | - | 0.0 |
| weather | ruchamkin_apd89 | Boat_Deck_Open | 44 | 1051.33 | - | 0.0 |
| weather | ruchamkin_apd89 | Fantail | 106 | 213.08 | - | 0.0 |
| weather | ruchamkin_apd89 | Focsle_Deck | 270 | 303.64 | - | 0.0 |
| weather | ruchamkin_apd89 | Island_Open_Aft | 91 | 182.66 | - | 0.0 |
| weather | ruchamkin_apd89 | Signal_Deck | 29 | 85.06 | HVAC_Accom | 0.9 |
| weather | san_antonio_class_lpd | Flight_Deck | 206 | 600.0 | HVAC_Aviation | 3.2 |
| weather | san_antonio_class_lpd | Vehicle_Deck | 180 | 2360.0 | HVAC_Vehicle_Deck | 4.0 |
| weather | san_antonio_class_lpd | Well_Deck | 193 | 3800.0 | HVAC_Well_Deck | 3.0 |
| weather | saratoga_cv3 | Flight_Deck | 14 | 19047.89 | - | 0.0 |
| weather | saratoga_cv60 | Flight_Deck | 77 | 48100.0 | VENT_Weather | 0.5 |
| weather | savannah_ns | Boat_Deck_Aft | 343 | 870.74 | AHU_Weather | 0.0 |
| weather | savannah_ns | Boat_Deck_Fwd | 328 | 332.82 | AHU_Weather | 0.0 |
| weather | savannah_ns | Fantail_Aft | 358 | 440.67 | AHU_Weather | 0.0 |
| weather | savannah_ns | Fwd_Deck_Promenade | 182 | 1383.94 | AHU_Weather | 0.0 |
| weather | savannah_ns | Promenade_Aft_Open | 36 | 642.54 | AHU_Weather | 0.0 |
| weather | savannah_ns | Weather_Deck_Port_A | 484 | 467.38 | AHU_Weather | 0.0 |
| weather | savannah_ns | Weather_Deck_Stbd_A | 499 | 701.07 | AHU_Weather | 0.0 |
| weather | sigsbee_dd502 | Fantail | 92 | 158.06 | - | 0.0 |
| weather | sigsbee_dd502 | Focsle_Deck | 255 | 216.88 | - | 0.0 |
| weather | sigsbee_dd502 | Midship_Deckhouse | 46 | 267.66 | - | 0.0 |
| weather | sigsbee_dd502 | Mt2_Deck | 77 | 257.19 | - | 0.0 |
| weather | south_dakota_bb49 | Boat_Deck | 94 | 4433.89 | - | 0.0 |
| weather | south_dakota_bb49 | Fantail | 308 | 1193.77 | - | 0.0 |
| weather | spirit_cruise_3000 | SportsDeck | 344 | 1800.0 | - | 0.0 |
| weather | squier_ap130 | Stern_Deck_Up | 123 | 400.66 | VENT_Stores_Open | 2.0 |
| weather | texas_bb35 | Fantail_Weather | 155 | 654.66 | - | 0.0 |
| weather | texas_bb35 | Focsle_Deck | 340 | 1636.65 | - | 0.0 |
| weather | texas_bb35 | Super_Deck_Open | 46 | 531.6 | - | 0.0 |
| weather | texas_bb35 | Weather_Deck_Aft | 170 | 1534.36 | - | 0.0 |
| weather | thetis_bay_cve90 | Flight_Deck | 61 | 8841.45 | VENT_Weather | 0.5 |
| weather | wasp_cv7 | Flight_Deck | 77 | 16750.07 | VENT_Weather | 0.5 |
| weather | west_virginia_bb48 | Boat_Deck | 212 | 4607.21 | - | 0.0 |
| weather | west_virginia_bb48 | Fantail | 538 | 1441.66 | - | 0.0 |
| weather | west_virginia_bb48 | Signal_Bridge_Open | 123 | 970.67 | - | 0.0 |
| weather | winnipeg_j337 | Foc_Deck_Open | 74 | 341.48 | VENT_Machinery | 2.0 |
| weather | winnipeg_j337 | Quarterdeck | 44 | 588.66 | VENT_Machinery | 2.0 |
| weather | winnipeg_j337 | Signal_Deck | 14 | 248.13 | HVAC_Accom | 2.5 |
| weather | wisconsin_bb64 | Boat_Waist_Open | 213 | 4485.94 | VENT_Weather | 0.5 |
| weather | wisconsin_bb64 | Fantail_Open | 198 | 2456.48 | VENT_Weather | 0.5 |
| weather | wisconsin_bb64 | Focsle_Void_2D | 728 | 313.11 | VENT_Weather | 0.5 |
| weather | wisconsin_bb64 | Forecastle_Open | 343 | 5445.7 | VENT_Weather | 0.5 |
| weather | wisconsin_bb64 | Signal_Deck | 51 | 399.21 | VENT_Weather | 0.5 |
| weather | wright_cc2 | Flight_Deck_Aft | 45 | 4302.31 | VENT_Weather | 0.5 |
| weather | wright_cc2 | Flight_Deck_Fwd | 105 | 5736.42 | VENT_Weather | 0.5 |
| weather | wright_cc2 | Flight_Deck_Mid | 75 | 5377.89 | VENT_Weather | 0.5 |
| weather | yorktown_cv5 | Flight_Deck | 81 | 16132.41 | VENT_Weather | 0.5 |
