> **Status:** Proposed — Phase-3 decision brief for the CONTAM-vs-native ship epidemiology study. It authorizes nothing, runs nothing, and is decision material rather than documentation of current behaviour; every number below is quoted from the cited ledger/audit entry at the SHA recorded there.

# Phase-3 epidemiology gate decision brief

**Update at `5c8f05cc`:** the [destroyer make-up repair](../ledger/CONTAM-DESTROYER-MAKEUP-01.md)
has landed. The [two-hull transport baseline](../ledger/CONTAM-PHASE3-BASELINE-01.md)
checks the corrected configurations. The evidence inventory in §2 remains
historical; neither it nor the new baseline authorizes an epidemiology run.

## 1. What Phase 3 is

Phase 3 is the coupled epidemiology decision gate. It is not a transport PR and not a campaign submission. Its two coupled outputs are:

1. **Paper structure:** choose between a coupled epidemiology paper and a transport-methods paper.
2. **Epidemiology-arm authorization:** decide which of the candidate arms below may proceed to design/canary, and under what attribution and data-return conditions.

The gate may authorize a bounded design or canary stage. It does not itself choose epidemiological constants, submit AWS Batch arrays, or contact Edison Scientific.

## 2. Evidence inventory

The representation work below is landed on `origin/main` `7cd051da`. Witness headlines are copied from the cited entries; this brief does not re-measure them.

| Landed representation work | Witness headline | Evidence |
|---|---|---|
| `ambient_openings` schema and native/export machinery; outward solved opening flow is a contaminant boundary sink independent of `envelope_leak_mode` | Stage-1 D8 paired-orifice witness at ΔT = +5 K: outward 21,392.23 m³/h on `Flow0`, `Flow1` = 0; stage-2 scratch `Pool_Deck` opening removes 872,299.40 units vs the no-opening arm in one epoch with closure error ~1e-16 | [schema](../ledger/CONTAM-AMBIENT-OPENING-SCHEMA-01.md), [boundary sink](../ledger/CONTAM-AMBIENT-OPENING-BOUNDARY-01.md) |
| Cruise/fiction `makeup_louvre` openings for prescribed exhaust sinks | 15 cruise + 2 fiction records; cruise design max \|ΔP\| 1.76e5–7.16e5 Pa → 11.3–1,213 Pa with residuals recorded, fiction 1.669e5/1.254e5 Pa → 13.71/3.246e4 Pa; exhaust-sink magnitudes unchanged | [cruise](../ledger/CONTAM-AMBIENT-MAKEUP-CRUISE-01.md), [fiction](../ledger/CONTAM-AMBIENT-MAKEUP-FICTION-01.md) |
| Localized make-up fixes on Greg Mortimer, Olympia and Pope | Greg commissioned max path \|ΔP\| 44,878.2 → 15.43 Pa; Olympia adds one louvre (`path_map` 821 → 823, new legs 697.1 m³/h inward); Pope seven louvres take commissioned envelope max \|ΔP\| 1,633,363.125 → 12.054 Pa and interior flowing max \|ΔP\| 67,544.531 → 0.888 Pa with make-up demand preserved | [Greg](../ledger/CONTAM-GREG-SERVICE-MAKEUP-01.md), [Olympia](../ledger/CONTAM-OLYMPIA-MAKEUP-01.md), [Pope](../ledger/CONTAM-POPE-MAKEUP-01.md), [Pope boundary audit](../audits/2026-11-18_pope_ap110_envelope_makeup_boundary/README.md) |
| Stage-4 open-deck weather zones: `exposure: weather` + `open_deck` records with D5 `exchange_m3h` | 182 stage-4 `open_deck` records across the fleet; cruise class is 23 records / 6 hulls at 27,472–421,508 m³/h, Olympia holdout is 10 records at 24,135–51,953 m³/h, and no cruise hull's design max \|ΔP\| worsens (classic 693 → 127 Pa, spirit 1,213 → 757 Pa) | [exposure audit](../ledger/CONTAM-AMBIENT-EXPOSURE-01.md), [cruise](../ledger/CONTAM-AMBIENT-WEATHER-CRUISE-01.md), [Olympia](../ledger/CONTAM-AMBIENT-WEATHER-OLYMPIA-01.md), [auxiliary](../ledger/CONTAM-AMBIENT-WEATHER-AUXILIARY-01.md), [battleship](../ledger/CONTAM-AMBIENT-WEATHER-BATTLESHIP-01.md), [destroyer](../ledger/CONTAM-AMBIENT-WEATHER-DESTROYER-01.md), [carrier](../ledger/CONTAM-AMBIENT-WEATHER-CARRIER-01.md), [cruiser](../ledger/CONTAM-AMBIENT-WEATHER-CRUISER-01.md), [amphibious](../ledger/CONTAM-AMBIENT-WEATHER-AMPHIBIOUS-01.md), [misc](../ledger/CONTAM-AMBIENT-WEATHER-MISC-01.md), [fiction](../ledger/CONTAM-AMBIENT-WEATHER-FICTION-01.md) |
| Grouped-weather G1: Midway `Flight_Deck` opening replaces the `VENT_Weather` OA leg | Native outflow k 0.5025 → 13.4755 1/h; commissioned envelope max \|ΔP\| 1,343,796 → 32.678 Pa while the remaining all-path max 353.585 Pa is an AHS system path | [Midway](../ledger/CONTAM-GROUPED-WEATHER-MIDWAY-01.md) |
| Grouped-weather G2/G3: Pope topology control and Aeolus ladder-well authoring | Pope control A is negative as a pressure fix: commissioned envelope max \|ΔP\| 1.355 MPa → 1.633 MPa and interior flowing max \|ΔP\| 58.55 → 67.54 kPa; Aeolus commissioned envelope/interior max \|ΔP\| 952.954/434.798 → 3.382/2.613 Pa with ladder-well links ≤ 0.392 Pa and make-up demand preserved | [Pope evidence](../audits/2026-11-17_pope_ap110_grouped_weather_evidence/README.md), [Pope topology](../ledger/CONTAM-POPE-TOPOLOGY-01.md), [Pope make-up](../ledger/CONTAM-POPE-MAKEUP-01.md), [Aeolus](../ledger/CONTAM-AEOLUS-LADDER-WELL-AUTHOR-01.md) |
| Grouped-weather G4 class rollout: opening replaces grouped HVAC OA leg, no double-count | G4 adds 100 `open_deck` records across six classes (fiction no-op); with G1 the grouped-weather total is 101; battleship example is 16 openings / 4 hulls with commissioned envelope max \|ΔP\| 61–357 kPa → 2.2–59 Pa | [battleship](../ledger/CONTAM-GROUPED-WEATHER-BATTLESHIP-01.md), [auxiliary](../ledger/CONTAM-GROUPED-WEATHER-AUXILIARY-01.md), [misc](../ledger/CONTAM-GROUPED-WEATHER-MISC-01.md), [carrier](../ledger/CONTAM-GROUPED-WEATHER-CARRIER-01.md), [cruiser](../ledger/CONTAM-GROUPED-WEATHER-CRUISER-01.md), [amphibious](../ledger/CONTAM-GROUPED-WEATHER-AMPHIBIOUS-01.md), [fiction](../ledger/CONTAM-GROUPED-WEATHER-FICTION-01.md) |
| Balcony rule-out | No defensible cruise balcony-door airflow magnitude at sea was found; the closest CFD ACH range is not commensurable because it lacks balcony opening area and door-open duty, so no balcony `ambient_openings` were authored | [balcony audit](../audits/2026-11-17_balcony_opening_magnitude/README.md) |
| Stage-5 bounded hatch/door leg | Six `weather_hatch` records (0.36 m², `HatchOccasionalW`, 1 m/s) on four hulls; hatch outward exchange 24.038–28.877 m³/h; the four hulls' envelope/interior max \|ΔP\| do not move materially while ambient-opening leg counts move 8→10, 18→22, 22→26 and 4→6; `hangar_door` ruled out | [hatch ledger](../ledger/CONTAM-AMBIENT-HATCH-01.md), [hatch magnitude audit](../audits/2026-11-18_hatch_door_opening_magnitude/README.md), [stage-5 readiness](../audits/2026-11-18_stage5_hatch_readiness/README.md) |
| Duct contract option B | `skip_duct_spines` on the nine spined hulls; commissioned bundles have zero duct elements/junctions/segments with byte-identical path maps; six cruise D5 values re-derived within ±2%; 27 pressure rows / 0 unsolved and `destroyer_baseline` commissioned envelope residual 81,561.180 Pa is pre-existing | [duct exclude](../ledger/CONTAM-DUCT-EXCLUDE-01.md), [duct inventory](../audits/2026-11-17_duct_spine_fleet_inventory/fleet_inventory.csv) |
| Pressure-localization fixes | Spirit commissioned all-path max \|ΔP\| 550.205 → 24.167 Pa and interior flowing max \|ΔP\| 539.453 → 22.147 Pa (`path_map` 1,311 → 1,599); Greg/Olympia make-up rows above; Olympia self-path fix moves `path_map` 805 → 801 | [Olympia self-path](../ledger/CONTAM-OLYMPIA-SELFPATH-01.md), [Greg](../ledger/CONTAM-GREG-SERVICE-MAKEUP-01.md), [Spirit](../ledger/CONTAM-SPIRIT-CABIN-RELIEF-01.md), [pressure localization audit](../audits/2026-11-17_contam_pressure_localization/README.md) |
| ROOM-AIR-01 ambient exchange wiring | Additive `sum(exchange_m3h)/volume_m3` on positive openings; census 74 platforms / 283 changed open-deck zones; residence-factor ratio 10.5071–585.7584 (median 112.7241); norovirus continuous airborne is null by construction; COVID n=2 Greg readout is one null and one +10-onsets move that stays unattributed | [ROOM-AIR-01](../ledger/ROOM-AIR-01-AMBIENT-EXCHANGE-01.md), [ROOM-AIR audit](../audits/2026-11-18_room_air_01_ambient_exchange/README.md) |
| Fleet make-up census | Static census over 77 committed bundles: every hull has exhaust-only AHS branches; make-up carriage is already authored as 26 `makeup_louvre` records on 10 hulls, but among campaign hulls only `destroyer_baseline` remains Pope-class with commissioned envelope max \|ΔP\| 81,561 Pa; the other campaign hulls are 4.61–290.365 Pa envelope max or already have authored make-up/plenum carriage | [make-up census](../audits/2026-11-19_makeup_path_fleet_census/README.md), [pressure review](../ledger/CONTAM-FIELD-PRESSURE-REVIEW-01.md) |
| Paired-diagnostic tooling | `--hull` now accepts all committed bundles through `bundled_hulls()`: 82 platform dirs / 77 bundles, the nine curated `PLATFORM_SOURCES` hulls keep default sources and the other 68 bundled hulls require `--source`; `midway_cv41 --source Flight_Deck` writes 12 cells | [paired hull allowlist](../ledger/CONTAM-PAIRED-HULL-ALLOWLIST-01.md) |

## 3. The arms

### (a) Norovirus limited-airflow-impact arm

Post-#1315, `norwalk_gi` has no continuous airborne emission by construction: the profile is `emesis_conditioned`, the default `profile_conditioned` droplet mode returns zero continuous emission for that arm, and near-field admission refuses it. The only remaining room-air consumer is the per-emesis bolus.

Implication for the gate: this arm **cannot** show a continuous airborne dose reduction from ambient openings or ROOM-AIR-01 wiring. It can only test whether limited airflow changes non-continuous channels (emesis bolus, fomite/food/contact) or serve as a pre-registered null/negative control. It must not be presented as evidence that ventilation reduces norovirus airborne transmission.

### (b) Respiratory epidemiology arm (COVID/flu)

This is the arm the landed transport work can actually move. ROOM-AIR-01 wiring changes the room-air residence factor on 283 opened open-deck zones, with residence-factor ratios of 10.5–585.8× (median 112.7×) versus the sealed baseline. The existing COVID readout is not yet an attribution: at n=2 paired Greg seeds, one seed is null and the other moves `recorded_onsets` 57 → 67 (+17.5%), outside the 13% onsets band, so the entry explicitly does not claim a stochastic reduction.

Gate implication: COVID/flu may be authorized only after a paired-seed attribution design is frozen and canaried at campaign-relevant scale. The arm should name the profiles, show the ROOM-AIR map is material for those profiles, and pre-declare what counts as attributed versus RNG-stream disruption.

### (c) Environmental detection arm

This arm is the least constrained by the transport evidence above. It should consume existing detection/observation channels and the Phase-4 Edison data-return format rather than introduce new epidemiological constants. If the paper structure is transport-methods, this arm is optional; if the paper is coupled epidemiology, it needs a defined detection observable, provenance, and a paired-seed design before authorization.

### (d) Ship X adapter

Ship X is funded-later and should not be part of Phase-3 authorization. When funded, it needs its own platform/hull review, paired-diagnostic coverage, and a decision on whether it is a transport-methods validation hull or an epidemiology arm hull.

## 4. Open decisions for the gate

- **Paper structure:** coupled epidemiology vs transport-methods. The evidence inventory supports transport claims now; epidemiology attribution is still pending.
- **Campaign scale/cost:** scale should be set by the attribution requirement, not by the 82-platform fleet. No full array should run before a frozen design, local smoke, and a canary readout.
- **Attribution requirements before arms run:** paired seeds, a criterion declared before the run, enough replicates to separate rare-event stream noise in hull counts, proof that the pathway was exercised, and measured/inferred/hypothesis kept separate.
- **Edison data-return format (Phase 4):** the return manifest/schema for arm outputs must be fixed before arms are authorized if Edison is to consume them; the [bounded return note](../contam_edison_return_01.md) records that schema confirmation was deferred to Phase 4.
- **`destroyer_baseline` disposition (closed):** the commissioned pressure discrepancy was repaired. Use the current transport baseline, not the pre-repair census, for comparisons.
- **Ship X go/no-go:** recommend no-go for Phase 3; revisit after paper structure and respiratory attribution are settled.

## 5. Coordinator recommendation

Recommend the gate choose the **transport-methods paper structure** as the Phase-3 spine and authorize epidemiology only as a bounded validation layer:

1. **First:** freeze a separate ROOM-AIR-01 respiratory attribution design before a canary — paired `ambient_off` / `ambient_on` comparisons, ≥20 seeds per cell as an initial diagnostic minimum (not a power guarantee), and an attribution criterion declared before the run. Verify a positive map contrast rather than assuming every naval hull has one; the destroyer at platform defaults is a no-change control. Do not authorize full COVID/flu arms until a canary is read out.
2. **Norovirus:** hold as a pre-registered null/control arm only if the paper needs a non-airborne limited-airflow contrast; otherwise exclude it from the airborne claim because continuous airborne norovirus is null by construction.
3. **`destroyer_baseline`:** retain as a corrected transport reference. At platform defaults the ROOM-AIR-01 ambient exchange change is zero; it is not a second positive contrast for that intervention.
4. **Environmental detection:** defer until the Phase-4 Edison return format is fixed; do not let it block the transport-methods paper.
5. **Ship X:** no-go; funded-later only.

If the owner instead chooses the coupled epidemiology paper, respiratory attribution remains a prerequisite. Transport verification alone does not establish an outbreak effect.
