# Forced-exhaust audit and fix plan (cross-zone link direction, mechanism, filtration)

> **Status:** Proposed — **nothing in §5 exists**. No engine, schema, exporter
> or hull-data change is made or authorized by this document. What does exist
> is the read-only audit: `tools/diag/forced_exhaust_audit.py` and its three
> committed outputs beside this file (`forced_exhaust_audit_links.csv`,
> `forced_exhaust_audit_summary.json`,
> `forced_exhaust_exact_integral_check.json`). Measured at `origin/main`
> `94daa3bf`. It responds to three testing corrections from Edison on the
> frozen CONTAM transport study. **Amended after merge:** Edison's figures
> reproduce at the conditions his bundle declares; the earlier "does not
> reproduce" verdicts compared different conditions (§3, reconciliation note).

**Evidence vocabulary used throughout.** *Measured* = computed this session
from the tree at `94daa3bf` by the committed script. *Inferred* = follows from
measured facts plus stated reasoning. *Hypothesis* = not tested. Standards
claims carry **source · access class · origin · grade**; grades follow
`.agents/skills/model-parameter-provenance/SKILL.md` (A direct in this
setting, B analogous setting or design requirement rather than as-built
measurement, C inferred or declared), origins follow
`docs/parameter_provenance_register.md` §1 (`Tr` transcribed from a
non-journal document, `Sec` secondary, `?nr` not retrieved).

**No constant is proposed, chosen or adjusted here to make any model output
match any other.** §1 fixes the convention from standards before §3–§4 look at
what the lanes compute, and where a lane disagrees with the convention that is
reported as a result.

## 1. Standards and engineering basis

### 1.1 What was retrieved, and how

| # | Source | Access class | Origin | What it says (verbatim where quoted) | Grade for our use |
|---|---|---|---|---|---|
| S1 | CDC, *Vessel Sanitation Program 2025 Construction Standards*, §33.1.4, §33.2.1–33.2.5, §7.3.2 (document pp. 28, 90–91) | **Agency document, open** — in no literature index; direct fetch returned 403, retrieved through the browser network stack | `Tr` | §33.2.1: these "must exhaust air through independent systems that are completely separated from systems using recirculated air": engine rooms; medical or isolation spaces; RWFs; "Galleys and other FOOD PREPARATION AREAS"; "Cabin and public toilet rooms"; waste processing areas. §33.2.2: "Maintain negative air pressure, in relation to the surrounding areas, in the areas listed in section 33.2.1." §33.1.4: "Provide a sufficient make-up air supply in all FOOD PREPARATION AREAS, WAREWASHING, cleaning, and toilet rooms." §33.2.5: a written balancing report must "demonstrate negative air pressure". | **B** for cruise hulls (a construction requirement for vessels in VSP jurisdiction, not an as-built measurement of any hull here); **C** by analogy for naval and museum hulls |
| S2 | ISO 9943:2009, *Shipbuilding — Ventilation and air-treatment of galleys and pantries with cooking appliances*, §4.1, §5.2, Annex A.2.1, A.2.3 | **Industry standard, paywalled** — read only in the publisher-hosted free preview pages (iTeh sample); the rest of the standard was not opened | `Tr` (preview pages only) | §4.1: "A separate supply air system shall be provided for the galley; this supply air system shall take in outdoor air only. A separate exhaust air system shall be provided for the galley, discharging the total airflow to the atmosphere." §5.2: "The quantity of the exhaust airflow shall be greater than that of the supply airflow." A.2.3: "There should be lower air pressure in the galley than in adjoining accommodation spaces." A.2.1: cooking appliances "should be equipped with a hood-type exhaust air terminal device ... with grease drip-trays and grease filters". | **B** (merchant-ship design standard, applied "when ... specified by the shipowner") |
| S3 | ISO 7547:2022, *Air-conditioning and ventilation of accommodation spaces ... Design conditions and basis of calculations* | **Industry standard, paywalled** | `?nr` | The table of contents shows §6.4 "Exhaust airflow", §6.4.2 "Exhaust system", §6.5 "Air balance". **The clause text was not read.** | none — no claim is drawn from it |
| S4 | ILO Maritime Labour Convention 2006, Standard A3.1 ¶7(c) | Treaty text, open; read on two mirrors (mlc2006.com, lovdata.no), not on ILO NORMLEX | `Sec` | "all sanitary spaces shall have ventilation to the open air, independently of any other part of the accommodation" | **B** (crew accommodation on merchant ships; a requirement, not a measurement) |
| S5 | ANSI/ASHRAE 62.1, §5.16.3.4 (2010 numbering) | **Industry standard, paywalled**; the clause was read as quoted in ASHRAE's own open interpretation IC 62.1-2010-1 | `Sec` | "Class 4 air shall not be recirculated or transferred to any space nor recirculated within the space of origin." Which exhaust streams are Class 2/3/4 (Table 5.16.1 / 6.5) was **not** read in the standard this session. | **C** (land-building standard; class assignment unread) |
| S6 | ANSI/ASHRAE 62.1 Table 6-5, 70 cfm per water closet | Already cited in-tree at `scripts/derive_sanitary_provisioning.py:44`; not re-opened here | as recorded in-tree | The head exhaust rate behind every `AHU_HD_*` branch | unchanged by this document |
| S7 | Mihai & Rusu 2021, *Inventions* 6(3):55, DOI 10.3390/inventions6030055, §1 | Journal, open access; Consensus full-text excerpt | `Sec` (review statement citing class rules) | "there are rooms such as the galley, toilets, mess rooms, and laundry where recirculation is not allowed." | **B**, corroborating only |
| S8 | NIST CONTAM user manual (NISTIR 6921), "Airflow Element Types" | Agency document, open; read on a third-party text mirror, not the NIST PDF | `Sec` | Power-law elements "permit flow in the direction of the pressure drop" — the sign of the flow through an orifice element is an output of the pressure solution, not an input. | **A** for what the element does; confirmed by the solved fields in §3.2 |
| — | ASHRAE 170 (health-care ventilation); ASHRAE 154 (commercial cooking); ASHRAE Handbook *HVAC Applications*, "Ships" chapter; SOLAS II-2; DNV / LR / ABS rules; NAVSEA general specifications | Industry / classification / statutory, **paywalled**; NAVSEA material is distribution-restricted | `?nr` | **Not opened. No claim is drawn from any of them.** This is a blocked read, not a null result: it says nothing about whether they contain a contrary or a more specific requirement. | none |

Access classes are kept separate on purpose: S1 and S8 are agency documents
(remedy: browser fetch or the agency archive), S2/S3/S5 and the unopened row
are paywalled industry standards (remedy: purchase or a library copy), and the
naval material is restricted (no remedy available to this project). The
unopened row is the honest boundary of §1.

### 1.2 What the basis supports

1. **Mechanism — galley and toilet exhaust is fan-driven extract to
   atmosphere, on a system separate from recirculating air.** S1 §33.2.1, S2
   §4.1, S4. In network terms this is a *prescribed-flow* path from the room
   to ambient, not a zone-to-zone link and not a pressure-sized opening.
   Grade B.
2. **Direction — the served room is held below its neighbours, so air
   crosses the boundary inward only, by design.** S1 §33.2.2, S2 A.2.3. The
   transfer (make-up) air that enters a head or a galley from an adjoining
   space is therefore one-way *into* the exhausted room. Grade B. This is a
   design convention: door openings, wind and unbalanced systems can reverse
   it on a real ship, and no source retrieved here measures how often.
3. **Magnitude of the transfer flow is a balance, not an independent
   declaration.** S2 §5.2 requires exhaust > supply; the inward transfer is
   the difference. A head with no supply (the `AHU_HD_*` branches) draws its
   whole extract as make-up, which is how
   `scripts/derive_sanitary_provisioning.py:403-413` sizes `Sanitary_Makeup`.
   For a galley, S2 §4.1 gives it its own outdoor-air supply, so the dining →
   galley transfer is only the exhaust-minus-supply remainder. **No retrieved
   source gives that remainder as a number**, and none of the
   `Dining_Galley_Exhaust` magnitudes in the hull data (5,000–18,000 m³/h)
   carries a citation. They stay Grade C declared values (§5.5).
4. **Filtration — these streams are not recirculated, so no recirculation
   filter acts on them.** S1 §33.2.1, S5, S7. Transfer air through a door
   undercut or grille is unfiltered. A hood grease filter (S2 A.2.1) exists,
   but **no source retrieved here gives its efficiency for respiratory or
   enteric aerosol**, so this document assigns it none.
5. **What the basis does not support.** It does not say which of the two
   lanes' flow fields resembles a real vessel, and it does not cover naval
   hulls except by analogy. Edison's own caveat ("These calculations do not
   determine which flow matches a real vessel") stands.

**Assumption labels where no source exists** (to be carried on the data when
§5 is implemented): `ASSUMED-GALLEY-TRANSFER-MAGNITUDE` (Grade C, declared),
`ASSUMED-NAVAL-BY-ANALOGY` (Grade C, S1/S2 applied to warships),
`ASSUMED-NO-AEROSOL-CREDIT-GREASE-FILTER` (Grade C, declared zero).

## 2. Fleet-wide audit

### 2.1 Method and reconciliation

`python3 tools/diag/forced_exhaust_audit.py audit` reads every
`data/platforms/*/air_flow_paths.json` and writes one CSV row per
`cross_zone_links` entry. Per link it records the declared fields, the endpoint
kinds and room-pair expansion, a **keyword reading of `path` + `description`**
(the stated intent — an authoring statement, never a physical measurement; the
rule that matched is in the `intent_rule` column and the rule table is echoed
in the summary JSON), what native does (it calls the engine's own
`cross_zone_link_bidirectional`), what the exporter emits, and the
disagreement flags.

| Reconciliation (measured) | Count |
|---|---:|
| `data/platforms/` entries | 85 |
| — not platforms (`CLASS_PHOTO_ATTRIBUTION.md`, `class_photo_catalog.json`, `deck_provenance.json`) | 3 |
| Platforms with `air_flow_paths.json` = platforms audited = independent recount | **82** |
| Links audited = independent recount = sum over platforms = unique `(platform, link_index)` keys = sum over intent classes | **1,011** |
| Platforms with zero links | 0 |
| Links with unresolved endpoints / zero flow / unstated intent | 0 / 0 / 0 |

The independent recount (`_direct_recount`) shares no classification code with
the audit; the script exits non-zero if any of the five link totals differ.

### 2.2 Fleet totals

| Declared field | Count of 1,011 |
|---|---:|
| `direction` present | **0** |
| `is_hvac_ducted: true` | 110 (on 14 platforms) |
| `is_hvac_ducted: false` | 901 |
| `path == "Sanitary_Makeup"` | 585 (on all 82 platforms) |

| Stated-intent class | Links | Stated direction | Stated mechanism | Native emits reverse paths | Exporter element |
|---|---:|---|---|---|---|
| `sanitary_makeup` | 585 | one-way | prescribed flow | **yes, all 585** | `plr_orfc` |
| `passive_opening` (ladder wells, doors, trunks, passages) | 302 | bidirectional | pressure opening | yes (as stated) | `plr_orfc` |
| `ducted_transfer` | 56 | one-way | prescribed flow | no | `fan_cvf` |
| `forced_exhaust` — ducted | 45 | one-way | prescribed flow | no | `fan_cvf` |
| `forced_exhaust` — **not** ducted | 7 | one-way | prescribed flow | **yes, all 7** | `plr_orfc` |
| `forced_supply` | 9 | one-way | prescribed flow | no | `fan_cvf` |
| `pressure_directed` (door leakage held inward by a stated pressure difference) | 7 | one-way | pressure opening | **yes, all 7** | `plr_orfc` |
| **Total** | **1,011** | | | | 110 `fan_cvf` + 901 `plr_orfc` |

| Disagreement flag | Links | Meaning |
|---|---:|---|
| `native_reverse_on_stated_oneway` | **599** (585 + 7 + 7) | The description states one-way; native emits both senses. These links expand to **6,131** reverse room-pair paths fleet-wide |
| `exporter_orifice_on_stated_prescribed_flow` | **592** (585 + 7) | The description states a fan-driven flow; the exporter emits an orifice whose flow and sign are solved, not prescribed |
| `filtration_coupled_to_ducted_flag` | 110 | Filtration follows `is_hvac_ducted` in both lanes and cannot be declared separately; 45 of these are exhaust streams |

### 2.3 Galley-related links

All galley-, mess- and scullery-related links that are not `Sanitary_Makeup`
(22 fleet-wide; 9 are ordinary ladder wells or passages and are omitted here —
they are in the CSV with `galley_related=True`):

| Platform | Path | From → to | m³/h | Ducted | Stated intent | Flags / note |
|---|---|---|---:|---|---|---|
| `classic_cruise_1900` | `Dining_Galley_Exhaust` | `MainDining_L` → `MainGalley` | 12,000 | no | forced exhaust | reverse + orifice; no description |
| `diamond_princess` | `Dining_Galley_Exhaust` | `International` → `MainGalley` | 18,000 | no | forced exhaust | reverse + orifice; no description |
| `expedition_cruise_450` | `Dining_Galley_Exhaust` | `MainDining` → `MainGalley` | 8,000 | no | forced exhaust | reverse + orifice; no description |
| `greg_mortimer` | `Dining_Galley_Exhaust` | `DiningRoom` → `MainGalley` | 5,000 | no | forced exhaust | reverse + orifice; no description |
| `spirit_cruise_3000` | `Dining_Galley_Exhaust` | `MainDining_L` → `MainGalley` | 15,000 | no | forced exhaust | reverse + orifice; no description |
| `enterprise_constitution_tos` | `Galley_Service_Exhaust` | `Galley` → `Mess_Hall` | 5,000 | no | forced exhaust | reverse + orifice; **declared sense is galley → mess, against §1.2(2)** |
| `enterprise_galaxy_tng` | `Galley_Service_Exhaust` | `Galley` → `Mess_Hall` | 8,000 | no | forced exhaust | as above |
| `mega_cruise_5000`, `messy_cruise_500` | `Dining_to_Galley_Transfer` | `AHU_Network_Aft_Dining_Rec` → `AHU_Dedicated_Service_Exhaust` | 15,000 | yes | forced exhaust | filter coupled; one-way fan in both lanes (solved 60 × 250 m³/h on `mega_cruise_5000`) |
| `expedition_cruise_300` | `Galley_Exhaust_Return` | `AHU_3_Service` → `AHU_2_Main` | 600 | yes | forced exhaust | filter coupled; description states a partial *return* of service-area air to the main AHU — against S1 §33.2.1 |
| `expedition_cruise_300` | `Galley_Service_Door` | `Main_Dining_Room` → `Galley` | 300 | no | passive opening | bidirectional as stated |
| `san_antonio_class_lpd` | `galley_exhaust_to_mess` | `HVAC_Galley` → `HVAC_Crew_Habitable` | 400 | yes | forced exhaust | filter coupled; "Galley exhaust partially recirculated to mess decks" — naval, §1 applies by analogy only |
| `san_antonio_class_lpd` | `galley_to_troop_mess` | `HVAC_Galley` → `HVAC_Troop_Berthing` | 350 | yes | forced supply | filter coupled |
| `legend_class_nsc` | `galley_supply` | `HVAC_Enlisted_Fwd` → `HVAC_Galley` | 200 | yes | forced supply | filter coupled |

The name `Dining_Galley_Exhaust` is itself a source of confusion: by §1.2 the
link is the dining → galley **make-up transfer** induced by the galley's
exhaust, and its declared sense (dining → galley) agrees with the convention.

### 2.4 The remaining one-way-stated passive links

`pressure_directed`, 7 links on four platforms: `mega_cruise_5000` (3),
`messy_cruise_500` (2), `expedition_cruise_300` (1) and
`fletcher_class_destroyer` (1) — `Crew_to_Engine_Stairwell`,
`Medical_Door_Leakage` / `MedBay_Door_Leakage` and `access_trunk_boilers`. Each description states a maintained pressure
difference and a net direction. Per-platform rows are in the CSV; the per-hull
counts are under `platforms.<id>.by_intent_class` in the summary JSON.

## 3. Verification of Edison's three claims

Reproduction: `python3 tools/diag/forced_exhaust_audit.py exact-check --hull
<each of the ten study hulls> --source Mess_Hall`. It reads no campaign output.
It rebuilds the linear operator `A` from the tree under the frozen Phase 1
tracer conditions (η = 0.5, λ = 0, 12 × 1 h, read from
`campaigns/contam/phase1_hvac_tracer_01/design/phase1_hvac_tracer_design.json`)
and reports, for a unit pulse at t = 0 in one source zone, the **exact**
whole-hull material-time ∫₀¹² 1ᵀe^{At}m₀ dt and the **endpoint sum** Σₖ
1ᵀe^{Ak}m₀ (k = 1…12), which is what the campaign cells accumulate. The
ContamX lane is the campaign's own E-lane construction
(`tools/contam_fleet_compare.py:384-414`, commissioned terminals at line 409)
solved locally with ContamX 3.4; it is a **fresh solve, not the frozen S3
field cache**, which this session did not read (no AWS).

### 3.1 Claim 1 — sanitary make-up links and the native bidirectional default

| Element of the claim | Verdict | Evidence |
|---|---|---|
| Native defaults a passive link with no `direction` to bidirectional | **Reproduces** | `engines/py_contam_bridge.py:73-74` (`DEFAULT_PASSIVE_LINK_MODE = "bidirectional"`), `:98-113` (resolver: absent `direction` → `not is_hvac_ducted`), `:563-589` (reverse room pairs appended) |
| `Sanitary_Makeup` links lack `direction` | **Reproduces, and is fleet-wide** | 0 of 585 (0 of all 1,011 links), §2.2 |
| 7 reverse sanitary paths on the destroyer, 53 on the expedition hull | **Reproduces** | measured 7 and 53 (`native_reverse_paths` summed over `Sanitary_Makeup` rows; the expedition hull's 54th is the galley link) |
| Pinning `direction="oneway"` on `Sanitary_Makeup` only gives 0.052 h on both hulls | **Reproduces** | measured 0.0521 h on both = 1 / 19.2 ACH exactly, i.e. the head empties only through its own exhaust |
| Baseline 0.200 h (destroyer) and 0.260 h (expedition) | **Reproduces at Edison's conditions** | measured 0.199898 h (`HD_MAIN_M`) and 0.259980 h (`HD_5P_M`) at η = 0.3, λ = 0.1 h⁻¹ — identical to his `results.csv` to six figures. At the frozen Phase 1 conditions the same two hulls give 0.184 h (mean of 3 heads; 0.172 / 0.172 / 0.208) and 0.232 h (mean of 13; 0.124–0.316) |
| Adjusted native matches commissioned ContamX within 0.24 % / 0.11 % | **Reproduces for the heads he tested** | at his conditions native one-way is 0.051813 h on both hulls; the E lane built by `tools/contam_fleet_compare.py:384-414` gives 0.051813 h for `HD_MAIN_M` and `HD_5P_M`, his field gives 0.051687 / 0.051757 h. He attributes his residual to solved/declared terminal-flow ratios of 1.0025 / 1.0011; why the campaign's field construction shows no such residual was **not traced** |
| "Remote sanitary burden goes to exactly zero in both adjusted native and ContamX" | **Reproduces for the heads he tested; does not generalise to every head** | Native: exact for all heads on all ten hulls. E lane: a head that loses mass only to its own exhaust has material-time exactly 1/(ACH + λ). That holds for `HD_MAIN_M` and `HD_5P_M`, and for every head on `destroyer_baseline`, `fletcher_class_destroyer`, `lexington_cv2`, `saratoga_cv3`. It does not hold for 5 of 13 heads on `expedition_cruise_450` (0.062–0.139 h at his conditions, max 0.129 h at Phase 1 conditions), nor on `missouri_bb63` (max 0.064 h), `greg_mortimer` (0.119), `mega_cruise_5000` (0.247), `classic_cruise_1900` (0.326) or `spirit_cruise_3000` (0.566) at Phase 1 conditions. These heads are outside his sample. *Inferred:* either some head's solved extract is below its declared rate or its `Sanitary_Makeup` orifice carries air out of the head; not separated here |

**Two qualifications to the framing, both from the tree:**

1. **`direction` already exists.** `schemas/air_flow_paths.schema.json:108-116`
   declares `direction: oneway | bidirectional` on `CrossZoneLink`, added by
   `CONTAM-BIDIR-01` (#1141). Native honours it; no hull uses it. Claim 1's fix
   needs **no schema change**.
2. **The bidirectional default was a deliberate, measured fix, not an
   oversight.** `docs/ledger/CONTAM-BIDIR-01.md` records fleet
   native-unreachable zones falling from ~600 to 52 when passive links became
   two-way. The defect is narrower and is a regression that change introduced:
   the sanitary links were authored on 2026-09-15 (`5b365345`) as "exactly one
   directional ... edge ... never a reverse edge ... so a head cannot be an air
   source for the space it serves" (`scripts/derive_sanitary_provisioning.py:356-363`),
   which was true while native was one-way. `CONTAM-BIDIR-01` (2026-11-01,
   `899e4ca0`) flipped the default for every undeclared passive link and pinned
   `direction` only on a test fixture, silently reversing that guarantee on 585
   links. Each link's own description still says "never back to the served
   space".

**Not only a CONTAM-study effect.** `build_hvac_downstream_map`
(`engines/transmission_core.py:15087-15123`) uses the same resolver, so the
reverse sanitary edges are in every default simulation since #1141, for every
pathogen with an airborne pool.

### 3.2 Claim 2 — `Dining_Galley_Exhaust` and the overloaded `is_hvac_ducted`

| Element of the claim | Verdict | Evidence |
|---|---|---|
| Declared 8,000 m³/h, `is_hvac_ducted=false`, no direction | **Reproduces** | `data/platforms/expedition_cruise_450/air_flow_paths.json`, CSV row `expedition_cruise_450` / `Dining_Galley_Exhaust` |
| Native treats it as 8,000 m³/h bidirectional | **Reproduces** | resolver as §3.1; one room pair each way at the declared rate |
| The exporter sizes it as a pressure opening giving 8,000 m³/h at a reference condition | **Reproduces** | `tools/contamw34_prj.py:797-827` (`ducted` → `fan_cvf`, else `_orifice_elem_for_flow`), `:561-580`, and `:136-147` (area for the design flow at `dp_pa = 1.0`, `cd = 0.6`) |
| In the solved field it carries 413 m³/h against the link name | **Reproduces within 1 %** | measured **−416.9 m³/h** (negative = against the declared from → to sense). The difference from 413 is consistent with a fresh solve versus the frozen cache but was not traced |
| — extends beyond the expedition hull | **New** | same link, same sign: `classic_cruise_1900` −1,756 of 12,000; `spirit_cruise_3000` −765 of 15,000; `greg_mortimer` −700 of 5,000 (after #1171) |
| The exporter does not read `direction` | **New, and it limits claim 1's fix** | `tools/contamw34_prj.py` contains no read of `direction`; measured: the E-lane operator is identical with and without the pin on all ten hulls (`as_authored` = `sanitary_makeup_oneway` in the check JSON) |
| `is_hvac_ducted` is overloaded | **Reproduces** | one boolean selects direction (`py_contam_bridge.py:113`), mechanism (`contamw34_prj.py:810-816`) and filtration (`py_contam_bridge.py:662-663`, `:742-743`; `engines/contamx_transport.py:147-164`) |
| Resolution: separate `direction`, `mechanism`, `filtered` | **Agreed, with the §3.1 qualification** | only `mechanism` and `filtered` are new |

By §1.2(2) the solved sign (galley → dining) is the one that contradicts the
design convention, and the declared sense is the conventional one. That is a
statement about convention, not about any real vessel, and it is not a reason
to choose a magnitude (§1.2(3)).

### 3.3 Claim 3 — hourly endpoint sampling versus the exact integral

| Element of the claim | Verdict | Evidence |
|---|---|---|
| The historical statistic is an hourly endpoint sum | **Reproduces** | `campaigns/contam/phase1_hvac_tracer_01/cell.py:264-278` (each epoch is observed only *after* `transport_step`), `:252` (`auc += concentration * epoch_hours`), `:300-303` (`b_v`); the same code at `campaigns/contam/phase2_cruise_contrasts_01/cell.py:405` and `:470`; read out as `b_v_h` at `phase1_.../readout.py:97` and `phase2_.../readout.py:115` |
| It underestimates fast-clearing pulses badly | **Reproduces, and the committed readout shows it** | a right-endpoint sum never sees the first hour. For a head at 19.2 ACH the first endpoint is e^{−19.2} = 4.587 × 10⁻⁹, and `phase1_readout.json` records exactly that as the E-lane `b_v_h` minimum (`4.58699e-09`) on `destroyer_baseline`, `fletcher_class_destroyer` and `expedition_cruise_450`, against a true 0.052 h |
| Destroyer mess-hall pulse: exact 0.372 h, sampled 0.070 h (81 % under) | **Reproduces at Edison's conditions** | measured native `Mess_Hall` at η = 0.3, λ = 0.1 h⁻¹: exact **0.372358 h**, endpoint sum **0.070272 h** — identical to his figures. At the frozen Phase 1 conditions: exact 0.313 h, endpoint sum 0.040 h (87 % under); E lane 0.286 h / 0.024 h (92 % under) |
| Native/ContamX ratio 1.84× sampled → 1.14× exact | **Reproduces within the E-lane difference** | at his conditions: 1.81× → 1.14× against the campaign-built E lane (`Mess_Hall` E exact 0.3278 h vs his 0.3252 h; endpoint 0.0389 vs 0.0381). At Phase 1 conditions 1.67× → 1.10×; with the §5.2 sanitary pin applied to native, 0.77× → 0.92× |
| Exact integrals are available from frozen operators without a rerun | **Reproduces** | the operator is a deterministic function of the tree (N) or of `field_cache.json` entries + flows (E, P): `cell.py:93-120`. The check above is that computation |

**Reconciliation with Edison's reproduction bundle (added after merge of
#1209).** The first version of this section marked the baseline, mess-hall and
ratio figures "does not reproduce". That was an error of comparison in this
document, not in Edison's numbers. His diagnostic declares filter efficiency
0.3 and natural decay 0.1 h⁻¹ and reports one named source per case
(`HD_MAIN_M`, `HD_5P_M`, `Mess_Hall`, `MainDining`), pinned at `e46742af`; this
document had evaluated the frozen Phase 1 / Phase 2 tracer conditions (0.5 and
0, both campaign designs) and averaged over every head. His inputs are the
same bytes as `94daa3bf`: the SHA-256 of both hulls' `air_flow_paths.json` and
`spatial_layout.json`, of `engines/py_contam_bridge.py` and of
`tools/contamw34_prj.py` in his manifest equal the tree's. Re-run at his
conditions (`forced_exhaust_exact_integral_check_eta030_decay010.json`,
command in the appendix), every native figure matches his `results.csv` to six
significant figures, including expedition `MainDining` (0.402164 native,
0.398208 pinned). The E lane differs by under 1 % (`Mess_Hall` 0.3278 vs
0.3252 h, `MainDining` 0.5229 vs 0.5218 h), untraced. Both condition sets are
legitimate; they answer different questions, and **only the 0.5 / 0 set
describes the frozen campaigns**. §4 and §5 do not depend on either.

## 4. Impact assessment

### 4.1 Per study hull (measured; material-times in hours, mean with range)

| Hull | Links | Sanitary links | Reverse paths on one-way-stated links | Native sanitary-source exact, as authored | Native, sanitary pinned one-way | ContamX E lane (unchanged by the pin) | Galley link, ContamX solved |
|---|---:|---:|---:|---|---:|---|---|
| `destroyer_baseline` | 6 | 3 | 7 | 0.184 (0.172–0.208) | 0.0521 | 0.0521 | — |
| `fletcher_class_destroyer` | 22 | 13 | 46 | 0.131 (0.068–0.197) | 0.0521 | 0.0521 | — |
| `lexington_cv2` | 5 | 5 | 15 | 0.199 (0.196–0.201) | 0.0524 | 0.0524 | — |
| `saratoga_cv3` | 5 | 5 | 15 | 0.197 (0.196–0.199) | 0.0524 | 0.0524 | — |
| `missouri_bb63` | 10 | 5 | 108 | 0.265 (0.255–0.278) | 0.0524 | 0.057 (0.052–0.064) | — |
| `expedition_cruise_450` | 17 | 13 | 54 | 0.232 (0.124–0.316) | 0.0521 | 0.072 (0.052–0.129) | −417 of 8,000 |
| `classic_cruise_1900` | 31 | 17 | 64 | 0.214 (0.146–0.299) | 0.0521 | 0.190 (0.052–0.326) | −1,756 of 12,000 |
| `spirit_cruise_3000` | 48 | 28 | 154 | 0.211 (0.147–0.270) | 0.0521 | 0.177 (0.052–0.566) | −765 of 15,000 |
| `mega_cruise_5000` | 88 | 63 | 446 | 0.187 (0.128–0.273) | 0.0521 | 0.112 (0.052–0.247) | +15,000 (ducted fan) |
| `greg_mortimer` | 19 | 11 | 62 | 0.187 (0.146–0.238) | 0.0521 | 0.067 (0.052–0.119) | −700 of 5,000 |

0.0524 rather than 0.0521 on the three museum hulls is their rounded `ach`.
`missouri_bb63`'s 108 is five `Sanitary_Makeup` links whose source groups hold
many rooms; the reverse-path count is room pairs, not links.

**Every other hull with a committed `contam/` bundle.** 77 platforms have one
(all but `expedition_cruise_300`, `fletcher_class_destroyer`,
`legend_class_nsc`, `messy_cruise_500`, `san_antonio_class_lpd`). All 77 carry
`Sanitary_Makeup` links and so all 77 change under D1; no hull outside the
table above and §2.3 has an unducted forced-exhaust link, so for the rest D1 is
the whole change. Per-platform counts: `platforms.<id>` in
`forced_exhaust_audit_summary.json`. The exact check was run on the ten study
hulls only.

### 4.2 The frozen Phase 1 / Phase 2 results

| Question | Answer | Basis |
|---|---|---|
| Are the as-run results still valid? | **Yes, as measurements of the tree at their `baseline_sha`.** No cell is wrong about what the code did. What changes is what they may be cited for | the N lane ran the default resolver; the engine and both hull files are unchanged since (`git log` on `engines/py_contam_bridge.py` and the platform files) |
| Which frozen numbers are affected in meaning? | (i) Every **N-lane** cell: the native field carries reverse sanitary paths on all ten hulls. (ii) Every **`sanitary_branch`** source cell in any lane: `b_v_h` there is dominated by the endpoint-sampling artefact (§3.3). (iii) **N-vs-E contrasts**: part of the reported divergence is the reverse sanitary paths plus the sampling rule, not field generation | §3.1, §3.3 |
| Would the E-lane field caches change under D1 (the direction pin)? | **No.** The exporter does not read `direction`; measured identical on ten hulls. **No new cache schema version for D1** | §3.2 |
| Would they change under the exporter fixes (X1, X2)? | **Yes** — the PRJ changes, so the solved field changes. That requires `contam_phase{1,2}_..._field_cache_v2` and a new `design_id`; the frozen `_v1` caches (SHA-256 in `docs/ledger/CONTAM-EDISON-RETURN-01.md`) stay as they are | §5.4 |
| P lane (committed `platform.prj`)? | Unchanged unless a PRJ is regenerated. The committed path maps already contain the `Sanitary_Makeup` orifices, so P shares the E lane's behaviour | `data/platforms/*/contam/path_map.json` |
| Do the readouts need addenda? | **Yes, two, both doc-only.** (a) an exact-integral addendum; (b) a caveat on N-lane and `sanitary_branch` rows pointing at the D1 ledger entry. Neither edits a committed readout file | repo rule: never overwrite a payload a ledger cites |
| Is a rerun needed for the exact integral? | **No.** N from the tree at `baseline_sha`; E and P from the frozen `field_cache.json` objects. The cells' `retained_fraction_curve` cannot supply it — it holds endpoints only | §3.3 |
| Does anything in the epidemiology change? | **Under D1, yes**: `build_hvac_downstream_map` loses the reverse sanitary edges in every default run. That is an all-pathogen move and needs the open-ledger entries in the same change | §3.1 |

### 4.3 Exact-integral readout option (no rerun, no AWS compute)

A doc-plus-JSON addendum per campaign: for each (hull, lane, source zone,
timing pattern) recompute `b_v_h` exactly from the operator, and report it
beside the committed endpoint value and their ratio. Inputs: the two frozen
field caches (read-only S3 GET, a credentialed leg this session did not take)
and the tree at each `baseline_sha`. It is a few seconds of linear algebra per
hull. `t0_t1_split` is the same integral with the second half-pulse injected at
t = 1 h. The committed `phase1_readout.json` / `phase2_readout.json` are not
touched; the addendum is a new file.

## 5. Versioned fix proposal

Defect fixes restore a guarantee the tree already states. Authoring
improvements add information the tree never had. They ship separately.

### 5.1 Two paths (Edison's resolution is a proposal; both are priced)

| | Minimal path | Spec-faithful path (Edison's resolution) |
|---|---|---|
| Sanitary reverse flow (native) | D1: pin `direction` on 585 links via the generator | same |
| Schema | none — `direction` exists | add `mechanism`, `filtered`; make `direction` required |
| Exporter | X1: honour `direction` for one-way passive links | X1 + X2: honour `mechanism` and `filtered` |
| Galley links | declare `direction` only | declare all three; magnitude stays Grade C |
| Hull files touched | 82 | 82, every link |
| Consumers that exist today | native, downstream map | the same two plus the exporter; **no reader of `mechanism` or `filtered` exists yet** |
| Frozen caches | unaffected until X1 | new cache schema version |

Recommendation: ship D1 alone first — it is a one-field data fix with a
measured effect and no schema change — then decide S1/X2 with the D1 numbers in
hand. S1 is worth doing: the overload is real (§3.2). It is not a prerequisite
for D1.

### 5.2 D1 — DEFECT: sanitary make-up links lost their one-way guarantee

*Ledger plan:* new entry `docs/ledger/CONTAM-SANITARY-DIR-01.md`, **Pathogens:**
all, **Status:** `open` until measured. It records the chronology in §3.1, the
599-link / 6,131-path extent, the before/after material-times from the check
JSON, and names `CONTAM-BIDIR-01` as the change that introduced it (that entry
is annotated, not rewritten). Open-ledger notes go to
`docs/norovirus/norovirus_open_ledger.md`, `docs/covid/covid_open_ledger.md`
and `docs/flu/flu_open_ledger.md` in the same change.

*Fix:* `scripts/derive_sanitary_provisioning.py:403-413` emits
`"direction": "oneway"`; the 585 existing links get the same key by targeted
text edit (the hull JSONs are hand-formatted — no `json.dump` rewrite). Value
source: the generator's own stated intent (`:356-363`), S1 §33.2.1–33.2.2, S4.
No flow rate changes.

*Guard (the part that prevents recurrence):* `tools/sanity_checker.py` rejects
any link whose `to` is an exhaust-only terminal (duty 0, `oa_fraction` 1.0)
unless `direction == "oneway"`, and any link whose `from` is one.

*What is deliberately not changed:* `DEFAULT_PASSIVE_LINK_MODE`. The default
for an undeclared passive opening stays bidirectional; `CONTAM-BIDIR-01`'s
measurement stands. Changing the engine default instead would re-create the
unreachable-zone defect it fixed.

*Default and baseline:* the fix ships on (it is data, there is no flag). The
labelled baseline is the tree before the change, by SHA, pinned on every
artefact that measured it — both campaign readouts, `CONTAM-PHASE1-*`,
`CONTAM-PHASE2-*`, `docs/contam_fleet_compare.md` and
`docs/contam_museum_hull_audit.md`.

### 5.3 S1 — schema (authoring improvement, versioned)

Add to `CrossZoneLink`, both optional at first:

- `mechanism`: `prescribed_flow` | `pressure_opening`.
- `filtered`: boolean — whether the recirculation filter efficiency applies.

`direction` is kept as is. `is_hvac_ducted` becomes a deprecated alias with a
fixed, behaviour-preserving expansion:

| `is_hvac_ducted` | `direction` | `mechanism` | `filtered` |
|---|---|---|---|
| `true` | `oneway` | `prescribed_flow` | `true` |
| `false` | `bidirectional` | `pressure_opening` | `false` |

Migration writes the explicit triple on every link from this table (plus D1's
pin), so the migration PR is **operator-identical** by construction and
testable as such. Only after that do authoring PRs change individual links.
Then `direction` becomes required and the alias is deleted, not kept.

### 5.4 Native and exporter

- **N1 (native, with S1):** read `filtered` instead of `is_hvac_ducted` at
  `py_contam_bridge.py:662-663` and `:742-743`; read `direction` only, never
  infer it from `is_hvac_ducted`, once the field is required.
- **X1 (exporter, defect-adjacent):** `tools/contamw34_prj.py:797-827` ignores
  `direction`. A link declared one-way must not export as an element that can
  reverse. Which CONTAM element expresses a one-way passive opening has **not
  been verified** against the NIST documentation this session — that check is
  the first task of X1, not an assumption of this plan. Until X1 lands, D1
  makes native *stricter* than ContamX on the six hulls listed in §3.1, and
  that asymmetry must be stated wherever the two are compared.
- **X2 (exporter, with S1):** `mechanism: prescribed_flow` exports as
  `fan_cvf` regardless of `filtered`; `filtered` selects the filter element,
  not the flow element.
- **X1 and X2 change solved fields** → new field-cache schema version and new
  campaign `design_id`s (§4.2). They do not touch the frozen prefixes.
- Add a per-link solved-versus-declared sign check to
  `tools/contam_commissioned_check.py` so a reversed prescribed link is
  reported at field-solve time rather than found later.

### 5.5 Per-platform data plan

| Class | Links | Change | Value source | Kind |
|---|---:|---|---|---|
| `Sanitary_Makeup` | 585 on 82 platforms | `direction: oneway` (D1) | generator intent; S1, S4 | **defect** |
| `Dining_Galley_Exhaust` (5 cruise hulls) | 5 | `direction: oneway` (dining → galley, as declared); under S1 `mechanism: prescribed_flow`, `filtered: false`; add a description; consider renaming to say "transfer" | direction: S1 §33.2.2, S2 A.2.3. **Magnitude: none — stays `ASSUMED-GALLEY-TRANSFER-MAGNITUDE`, Grade C. It is not to be re-chosen from either lane's output** | authoring |
| `Galley_Service_Exhaust` (2 fiction hulls) | 2 | review the declared sense (galley → mess) against §1.2(2); decision recorded, not assumed | S2 A.2.3 by analogy, Grade C | authoring |
| `Galley_Exhaust_Return` (`expedition_cruise_300`), `galley_exhaust_to_mess` (`san_antonio_class_lpd`) | 2 | review whether recirculated galley exhaust is intended; no value proposed | S1 §33.2.1 (cruise), analogy only (naval) | authoring |
| `pressure_directed` door/stairwell leakage | 7 | `direction: oneway` if the stated pressure regime is kept | each link's own description; S1 §33.2.1–33.2.2 for the medical ones | authoring |
| Ducted relief/medical exhaust | 45 | under S1, decide `filtered` per stream; exhaust to another zone through the recirculation filter is the current behaviour | none retrieved — declared | authoring |
| Passive openings | 302 | explicit `direction: bidirectional` at S1 migration | as authored | mechanical |

### 5.6 Tests (structural invariants, no goldens)

- A unit pulse in any exhaust-only terminal room never raises mass in any
  other zone (native; and the exporter lane once X1 lands).
- That room's exact material-time equals 1 / `ach` to solver tolerance — an
  identity, not a pinned number.
- Sanity-checker rule of §5.2, with a failing fixture.
- S1 migration: operator equality before/after on every platform.
- Exporter: element type as a function of (`direction`, `mechanism`,
  `filtered`) on a three-link fixture.
- Graded response: scaling a one-way link's flow changes downstream mass and
  leaves upstream mass unchanged.
- `tools/diag/forced_exhaust_audit.py audit` reconciles and reports zero
  `native_reverse_on_stated_oneway` on `Sanitary_Makeup` after D1.

### 5.7 Rollout order

1. **This PR** — audit, artefacts, plan. Nothing else.
2. **Exact-integral addenda** for Phase 1 and Phase 2 (§4.3). Independent of
   every fix; needs one read-only S3 leg.
3. **D1** — generator + 585 pins + sanity-checker rule + ledger
   `CONTAM-SANITARY-DIR-01` + open-ledger notes + readout caveats.
4. **X1** — after the CONTAM element check; new cache schema version.
5. **S1 + N1 + X2** — operator-identical migration first, then authoring PRs
   per §5.5, one hull class at a time.
6. Any re-measurement of the transport study is a **new campaign** with a new
   `design_id`, decided after step 3's numbers are read. Not proposed here.

### 5.8 What stays frozen

Both campaign directories, both S3 prefixes and their `_v1` field caches, both
committed readouts, `docs/contam_edison_return_01.{md,json}`, and the ledgers
`CONTAM-PHASE1-*`, `CONTAM-PHASE2-*`, `CONTAM-ACH-SCOPE-01`,
`CONTAM-EDISON-RETURN-01`. `CONTAM-BIDIR-01` keeps its measurement and gains a
forward reference. No epidemiological constant is touched by any step.

## Appendix — reproduction

```bash
python3 tools/diag/forced_exhaust_audit.py audit
python3 tools/diag/forced_exhaust_audit.py exact-check \
  --hull destroyer_baseline --hull fletcher_class_destroyer \
  --hull lexington_cv2 --hull saratoga_cv3 --hull missouri_bb63 \
  --hull expedition_cruise_450 --hull classic_cruise_1900 \
  --hull spirit_cruise_3000 --hull mega_cruise_5000 --hull greg_mortimer \
  --source Mess_Hall
```

To evaluate Edison's declared conditions instead of the frozen campaign
conditions (writes a separate, labelled file):

```bash
python3 tools/diag/forced_exhaust_audit.py exact-check \
  --hull destroyer_baseline --hull expedition_cruise_450 \
  --source Mess_Hall --source HD_MAIN_M --source MainDining --source HD_5P_M \
  --filter-efficiency 0.3 --decay-per-hour 0.1 --label eta030_decay010
```

The first is pure file reading. The second needs ContamX for the E lane
(`third_party/contamx/contamx3` or `CONTAMX_BINARY`); `--no-contamx` gives the
native lane alone. The check applies the D1 pin **in memory only**.
