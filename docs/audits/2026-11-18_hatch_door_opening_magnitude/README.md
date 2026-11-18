> **Status:** Evidence note for the ambient-exposure stage-5 hatch/door opening gate. This note authors no openings, platform data, constants, schedules, or behaviour change.

# Hatch and door opening magnitude evidence (ambient-exposure stage 5)

## Scope and pins

- Repository: `bckirkup/Crusher_to_the_Bridge`; branch base `origin/main` `b33bb52a2a8674553c0cf2c2114a846866d314ad`.
- Governing plan: `docs/proposals/ambient_exposure_audit_and_fix_plan.md` stage 5 and `docs/audits/2026-11-18_stage5_hatch_readiness/README.md` §3. The candidate edge set is 9 edges on 6 naval hulls: `hangar_door` on `astoria_ca34` and `miami_cl89`; `hatch` on `lsm_354`, `middlesex_lst983`, `lyon_ap71`, and `montana_acr13`.
- Retrieval rule followed: `consensus-literature-retrieval` plus `searching-literature-evidence`; every Consensus `search` call below passed `include_full_text_chunks: true` and named the quantity and unit in the query. Government, agency, classification-society, standards-body, and industry documents are treated as a separate access class from peer-reviewed journals.
- The question is clear-opening **area** or **free-area fraction**, not merely door existence. No source reviewed gives a defensible free-area fraction for shipboard weather hatches, weather doors, or hangar doors.

## Retrieval log

Consensus searches run on 2026-11-18, all with `include_full_text_chunks: true` and `page_size` 20 unless noted:

1. `shipboard weather hatch clear opening area m2 dimensions marine hatch`
2. `"weather hatch" ship clear opening area m2`
3. `marine weather-tight door clear opening width mm dimensions ship door`
4. `aircraft carrier hangar door clear opening dimensions m2 area`
5. `vessel weather hatch opening dimensions deck hatch clear opening mm ship`
6. `ship hatchway clear opening area m2 deck hatchway dimensions marine`
7. `ship weather tight door hatch open closed at sea navigation operating condition`
8. `aircraft carrier hangar door open closed at sea operations hangar`

Separate web/standards searches were used for marine door/hatch standards, classification-society rules, IMO/IACS operating rules, manufacturer hangar-door dimensions, and building-code analogues because those classes are not literature-indexed material.

## Candidate magnitudes found

| Source | Quantity reported | Value and unit | Setting / relevance | Grade for stage-5 use | Access class | Read location |
|---|---|---:|---|---|---|---|
| ISO 3796:2023, *Clear openings for external single-leaf doors*; ISO 6042:2015, *Weathertight single-leaf steel doors* | Standardized clear opening height × width for external single-leaf shipboard doors | Nominal clear-opening sizes span 1200×600 mm to 1800×900 mm; rectangular clear-opening area range **0.72–1.62 m²**; representative standard size 1500 mm × 750 mm = **1.125 m²** | International standards for external single-leaf doors on board ships where coamings are required; directly commensurable with `weather_door`, not with hatchways or multi-panel hangar doors | **C basis value**: nominal standardized geometry, not a measured opening area or duty cycle | Standards-body previews | ISO 3796 preview scope/summary; ISO 6042:2015 Table 2 nominal sizes |
| UK MCA guidance, MGN 628 Part 3 *Watertight and Weathertight Integrity* | Main access hatch clear opening | Normally **600 mm × 600 mm = 0.36 m²**; restricted-space minimum **500 mm × 500 mm = 0.25 m²** | Government/agency marine construction guidance for small-vessel access hatchways; fishing-vessel context inferred from MCA/Fishing Vessel Certifying Authority wording; not a naval-ship weather-hatch rule | **C — analogue only**: small-vessel access hatch, not a generic naval `weather_hatch` area | Government/agency PDF | §3.1.8–§3.1.15 |
| Lloyd's Register Rules, Pt 3 Ch 11 §6 | Small hatchway/access-opening threshold | Opening **≤ 2.5 m²** for the small-hatchway regime; number/size kept to minimum; rope hatches closed before leaving port and at sea | Classification-society structural rule for hatchways on exposed decks; gives a threshold, not a clear-opening dimension | **C — not admissible as an area** | Classification-society rules webpage | §6.1.1–§6.1.6, §6.4 |
| Daule & Diwate 2020, *Design Optimization of Foldable Hangar Door for Naval Ships*, DOI `10.26706/ijaefea.2.7.20200608` | Foldable hangar-door minimum clear opening | **6000 mm × 6196 mm = 37.176 m²** | One naval-ship foldable hangar-door design specification; customer-specified service conditions, not a fleet generic | **C — ship-specific design value** | Peer-reviewed journal; Consensus full text | General Specifications bullet list |
| GRSE hangar-door technical specification, 2025 procurement PDF | Hangar-door clear opening width × height | **5400 mm × 7600 mm = 41.04 m²** and **4300 mm × 4800 mm = 20.64 m²** examples | Government/industry procurement specification for vessel hangar doors; ship-specific | **C — ship-specific design value** | Government/industry PDF | Technical Specification of Hangar Doors, scope table |
| L3Harris/Calzoni hangar-door datasheet; Mafo hangar-door page | Hangar-door maximum dimensions | Up to **15 m × 6.5 m** and up to **15 m × 6 m** respectively; area not stated | Manufacturer capability ranges for customized naval hangar doors; demonstrates large ship-to-ship variance | **C — not admissible as generic** | Industry datasheets/pages | Main features / product description |
| Flizikowski et al. 2017, *Bulkhead Door – Critical Evacuation States*, DOI `10.1515/pomr-2017-0008` | Power-operated sliding watertight bulkhead-door clear passage width | Register requirement: normally limited to maximum clear passage width **1.2 m** | Interior watertight bulkhead-door requirement, not a weather hatch/door or hangar door; width only, not area | **C — not commensurable** | Peer-reviewed journal; Consensus full text | Register's requirements excerpt |
| ABCB NCC 2025 Part 2, *Dwelling entrance* | Building-code entrance clear opening width | At least one dwelling entrance door clear opening width **820 mm** | Building-code egress/accessibility analogue; gives width only, not marine weathertight area or free-area fraction | **C — not commensurable** | Government building-code page | Clause 2.1 / Figure 2.1 |

## Operating-state evidence: closed versus open at sea

The retrieved rules show that **door-like shipboard openings are normally closed at sea**, but they do **not** give an open-duty fraction for the stage-5 classes:

- IMO MSC.1/Circ.1564 for passenger-ship watertight doors: all watertight doors are to be kept closed during navigation except temporary passage of passengers/crew or work in the immediate vicinity; Category B/C doors may be opened only for those limited purposes and must be immediately closed afterwards; Category D doors remain closed. Access class: IMO guidance PDF; read location: §§1.2, 5, 6, 8.
- IACS UI SC156 for watertight doors in cargo and passenger ships: operation modes are "normally closed," "permanently closed," or "used"; "used" doors are kept closed at sea but may be opened during navigation only for passage/work and shall be immediately closed after use. Access class: IACS/class-society PDF; read location: §3.1 Frequency of Use whilst at sea.
- Lloyd's Register small-hatchway rules: rope hatches may have reduced coamings only if well secured and closed before the ship leaves port, with a notice that they are to be closed whilst at sea; hatchway number and size are to be kept to the minimum consistent with satisfactory operation. Access class: classification-society rules; read location: Pt 3 Ch 11 §6.1.2–§6.1.6.
- UK MCA guidance: flush deck hatches require a permanent "HATCH TO BE KEPT CLOSED AT SEA" notice; access, loading, and discharge hatches likely to be opened at sea should be positioned on the centreline where practicable. Access class: government/agency PDF; read location: §3.1.11 and §3.1.15.
- Hangar doors: the design purpose is to protect helicopters/aircraft from sea atmospheric conditions, and manufacturer literature emphasizes weathertight/light-tight closure. Open-duty evidence found was anecdotal or exercise-specific, not an operational dataset: web/Q&A accounts describe carrier hangar doors being opened for ventilation/flight operations and closed in heavy weather, and a DVIDS image shows hangar-bay doors closing during a general-quarters exercise. Access class: industry/web; read location: article/image captions. This is context only, not a defensible duty cycle.

Consequence: even where a clear-opening magnitude exists, no source supplies a measured open fraction, open hours per day, or weather-dependent duty cycle for shipboard weather hatches, weather doors, or hangar doors. Any nonzero `exchange_m3h` still requires a separate, sourced duty/exchange basis; this note does not author one.

## Finding and per-type verdict

| Stage-5 type | Defensible magnitude? | Basis and grade | Where read | Fallback for authoring leg |
|---|---|---|---|---|
| `weather_door` | **YES, with caveats** | Grade C basis value **1.125 m²** (1500 mm × 750 mm clear opening), within ISO 3796/ISO 6042 standardized range **0.72–1.62 m²** for external single-leaf shipboard doors | ISO 3796 preview; ISO 6042:2015 Table 2 | Use only for a single-leaf external weathertight door with coaming. If the actual door is multi-leaf, sliding, hangar, cargo-access, or ship-specific, use the drawing/spec clear opening instead; otherwise do not author a generic area. |
| `weather_hatch` / candidate `hatch` edges | **NO generic naval magnitude** | Only small-vessel access-hatch analogue found: MCA normal **0.36 m²**, minimum **0.25 m²**; LR small-hatchway threshold **≤2.5 m²** but no dimensions. Candidate hatchways include tank wells, tank decks, cargo holds, and forecastle/engine-room accesses, so one small access-hatch size is not defensible across them | MCA MGN 628 Part 3 §3.1.8–§3.1.15; LR Pt 3 Ch 11 §6.1 | Keep the zone-to-zone hatch/door path as the transmission mechanism and do not add a fleet-wide `ambient_openings` record. Author an opening only with per-edge clear-opening geometry from GA/drawing/owner, or a declared per-edge Grade C value with explicit provenance; otherwise leave ambient exchange unchanged. |
| `hangar_door` | **NO generic magnitude** | Retrieved values are ship-specific custom clear openings: **37.176 m²** foldable naval hangar door, **20.64–41.04 m²** procurement examples, manufacturer maxima **15×6–15×6.5 m**. No standard free-area fraction or typical area exists | Daule & Diwate 2020 General Specifications; GRSE 2025 spec; L3Harris/Mafo datasheets | Do not author a generic hangar-door area. Use the ship-specific hangar-door clear opening from drawings/specification if available; if absent, do not add `ambient_openings` for the hangar edge. Operating state should not be assumed `always_open`; treat as closed unless a ship-specific schedule/evidence is supplied. |

## Recommendation

- For a future `weather_door` record that is genuinely an ISO-type external single-leaf weathertight door, the recommended Grade C basis value is **`area_m2 = 1.125`**, provenance: ISO 3796:2023 clear-opening definition plus ISO 6042:2015 Table 2 nominal size 1500 mm × 750 mm. This is a nominal standardized clear opening, not a measured airflow area; `exchange_m3h`, azimuth, wind speed, and schedule remain separate authoring decisions.
- For the current candidate `hatch` edges (`lsm_354`, `middlesex_lst983`, `lyon_ap71`, `montana_acr13`) and `hangar_door` edges (`astoria_ca34`, `miami_cl89`), **rule out a fleet-generic stage-5 magnitude**. The authoring leg should fall back to ship-specific geometry/specification or no ambient opening, following the balcony-leg precedent of refusing an unfounded constant.
- What would reopen a hatch or hangar magnitude: a ship-specific drawing/specification clear opening for the exact edge, a classification-society or navy standard for that opening class, or direct measurement of open area and duty at sea. A building-code entrance width or a manufacturer maximum dimension is not sufficient.

## Validation

- Docs-only change: one new `docs/audits/2026-11-18_hatch_door_opening_magnitude/README.md`.
- No `data/`, engine, exporter, schema, test, ledger, or campaign file is changed.
- No ledger entry is created, so `tests/test_ledger_entries.py` is not implicated.
- Pre-commit is run on the changed file before PR.
