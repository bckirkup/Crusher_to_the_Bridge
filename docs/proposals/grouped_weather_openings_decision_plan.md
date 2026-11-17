# Grouped weather-zone openings: per-hull representation decisions

> **Status:** Proposed. **Nothing in this document describes current behaviour,
> authors platform data, or authorises a fleet rerun.** It is a doc-only decision
> record for the owner question left open by ambient-exposure stage 4: should
> HVAC-grouped weather zones with outdoor-air exchange receive
> `ambient_openings`?

## 1. Scope and evidence base

This proposal answers the grouped-zone open item recorded by stage 4: weather
zones that were skipped because they already exchange outdoor air through an
HVAC group. It does **not** re-open the settled stage-4 rule for ungrouped or
zero-outdoor-exchange zones, and it does not change platform data, exporter or
engine code, tests, frozen Phase1/Phase2 directories, S3 prefixes, `_v1` caches,
or committed readouts.

Committed record cited throughout:
[`docs/audits/2026-11-17_contam_pressure_localization/`](../audits/2026-11-17_contam_pressure_localization/),
pinned to repository revision `c93fa32fbe05440e797de8b551a2781b236d7e43`.
The three hulls that drive this proposal are byte-identical between that pin
and the `origin/main` used here; I re-verified with
`git diff --name-only c93fa32fbe05440e797de8b551a2781b236d7e43 origin/main -- data/platforms/midway_cv41 data/platforms/pope_ap110 data/platforms/aeolus_arc3`,
which returned no paths. PR #1284 merged after the pin and did not touch these
three hulls.

Settled schema context, not re-decided here:

- D1(a): top-level `ambient_openings` list, governed by
  `docs/ledger/CONTAM-AMBIENT-OPENING-SCHEMA-01.md`.
- D2(a): weather zones remain finite zones with an ambient opening and a
  declared exchange axis, per `docs/proposals/ambient_exposure_audit_and_fix_plan.md`.
- D4(a)/D5: declared per-type native exchange axis; `exchange_m3h` is the
  commissioned-lane ContamX-solved outward flow at the committed fleet-default
  wind point unless the owner rules otherwise.
- D7(b): authored `exposure` field in `spatial_layout.json`.
- D8: `paired_orifices` is the shipped two-way ambient-opening representation;
  `single_orifice` carries only net flow and `two_way_door` was rejected for
  current consumers.
- Fleet default weather is one declared relative wind per hull: 1 m/s from
  ahead, Grade C `ASSUMED-RELATIVE-WIND`, per
  `docs/ledger/CONTAM-DEFAULT-WEATHER-01.md`.

## 2. Fleet context

The committed census
(`docs/audits/2026-11-17_contam_pressure_localization/evidence/current_fleet_input_census.csv`)
reports 82 hulls with **154 `open_deck` records on 34 hulls** and **17
`makeup_louvre` records on 8 hulls**; those are the stage-3/4 ungrouped or
zero-exchange records. The grouped-zone open item is separate.

`grouped_weather_exclusions.csv` records the stage-4 roster-call skips row by
row. It is evidence of the scope rule, not a complete zone census, so the
fleet count below is a current-main re-run of the audit rule in
`docs/proposals/ambient_exposure_audit_and_fix_plan.md` Appendix A using
`tools/hull_audit.py` semantics: `_is_exterior()` for weather zones and
outdoor ACH `= ach * hvac_duty * oa_fraction` (or `ach` for the duty-0,
`oa_fraction >= 1` dedicated-exhaust branch).

On current main that re-run finds:

| inventory | count |
|---|---:|
| weather zones | 285 on 78 hulls |
| ungrouped weather zones | 152 |
| zero-outdoor-exchange weather zones | 179 |
| **grouped weather zones with outdoor exchange > 0** | **106 on 38 hulls** |
| hull × HVAC-group patterns among those 106 | 46 |

The 243-zone figure in `CONTAM-AMBIENT-EXPOSURE-01` is the pre-stage-4 lexical
inventory; D7(b) `exposure` authoring and stage-4 lexical-miss corrections have
since changed the weather inventory. The count that matters for this decision
is the 106-zone grouped OA>0 subset.

The 46 patterns are listed in §6. They cluster into the same shapes that stage
4 already touched as separate classes: carrier/flight-deck weather groups at
0.5–1.6 outdoor ACH, battleship/cruiser `VENT_Weather` groups at 0.5 outdoor
ACH, auxiliary accommodation/cargo groups at 2.0–4.5 outdoor ACH, amphibious
aviation/well-deck groups at 1.2–3.2 outdoor ACH, a small miscellaneous set, and
one fiction `AHU_Public` group at 0.675 outdoor ACH.

## 3. Midway CV41 — explicit flight-deck opening on a grouped weather deck

### 3.1 Current representation

`data/platforms/midway_cv41/air_flow_paths.json` has no `ambient_openings`
key. `Flight_Deck` is a room of:

```json
{
  "id": "VENT_Weather",
  "rooms": ["Flight_Deck", "Island_Upper"],
  "ach": 1.0,
  "oa_fraction": 1.0,
  "vent_mode": "nat_supply",
  "description": "Open-air flight deck + island platforms"
}
```

With the fleet default `hvac_duty = 0.5`, that is 0.5 outdoor ACH for both
rooms. `Flight_Deck` has volume 28,293.69 m³, floor area 10,882.19 m²,
ceiling 2.6 m, elevation 25.6 m, deck `flight_deck`, max occupancy 300, and no
`exposure` field. The audit-rule outdoor-exchange calculation therefore treats
it as a grouped weather zone with OA>0: exactly the skipped class.

### 3.2 Measured evidence

From `current_local_solve_summary.csv`, `group_cut_budgets.csv`, and
`localization_review.md`:

| Midway CV41 commissioned lane | envelope max \|ΔP\|, Pa | flowing interior max \|ΔP\|, Pa | makeup demand, m³/h | opening net inward, m³/h |
|---|---:|---:|---:|---:|
| baseline | 1,343,796.0 | 14.637153625488281 | 21,176.163088012137 | 0 |
| `all_explicit_weather_open` | 33.038177490234375 | 27.88310432434082 | 21,176.163088012137 | 21,100.28289879465 |

The scenario's `max_dp_pa` is 353.5849304199219 Pa because it includes a fan or
prescribed-flow path; the envelope and flowing-interior columns are the
boundary/interior diagnostics used by the review. Extraction/make-up demand is
unchanged. The envelope problem is therefore a missing pressure-responsive
boundary path, while the interior max rises modestly from 14.64 Pa to 27.88 Pa
and must be explained rather than ignored.

### 3.3 Representation decision requested

**Recommendation:** treat `Flight_Deck` as the class witness for "grouped
weather deck with group OA" and decide one of two owner rulings before any data
change:

1. **Opening replaces the weather-deck outdoor leg.** Author one
   `ambient_openings` record for `Flight_Deck` and re-declare `VENT_Weather`
   so it no longer counts the same physical flight-deck exchange as HVAC OA.
   This avoids double-counting but touches HVAC grouping semantics.
2. **Opening is additional and group OA remains.** Author the opening but
   accept that the native lane now has both a fixed group exchange and a
   pressure-responsive opening. This is only defensible if the two represent
   different physical paths; otherwise it double-counts outdoor supply.

The schema that applies is D1(a) `ambient_openings`, not `adjacency` to
`ambient` and not a new `cross_zone_links` mechanism. For `Flight_Deck` the
record shape would be:

- `zone`: `Flight_Deck`
- `type`: `open_deck`
- `area_m2`: Grade C deck-face area. Using the stage-4 auxiliary rule, the
  square-plan deck-face estimate is `2 * sqrt(V / 3) * 3 = 582.687 m²` for
  V = 28,293.69 m³. This is an authoring witness, not a measured area.
- `exchange_m3h`: D5 commissioned-lane solved outward flow at the committed
  1 m/s fleet-default wind. Do not copy the scenario's net inward flow
  (21,100.28 m³/h) into `exchange_m3h`; measure the new opening's outward leg
  after the representation decision.
- `wind_speed_m_s`: 1.0 unless the owner changes the fleet-default weather
  rule.
- `schedule`: `always_open` for a flight deck unless an operational closure
  state is authored.
- D7(b): declare `exposure: "weather"` on `Flight_Deck` if it is not already
  implied by the lexical audit. On current main it has no `exposure` field, so
  the owner should confirm whether to author it.

**Double-count risk.** The present `VENT_Weather` group already supplies
outdoor air to `Flight_Deck` and `Island_Upper`. An `ambient_openings` record
adds a second boundary exchange in the native lane and a second orifice pair
in the ContamX lane. If both remain, the model can represent the same open
deck twice: once as fixed HVAC outdoor exchange and once as a pressure-driven
deck opening. The owner must say which physical path each represents before
authoring.

**Witnesses for the Midway decision.** Before/after paired runs on
`midway_cv41` only, using the same tools as stage 4 and the audit:

- `tools/diag/contam_pressure_balance_diagnostic.py` for the hull row and the
  fleet table.
- `tools/diag/contam_paired_diagnostic.py` for native/commissioned paired
  closure.
- ContamX exported path maps for `midway_cv41`, checking that the opening adds
  `kind: "ambient_opening"` rows and does not remove the `VENT_Weather`
  supply/exhaust paths unless the owner chooses ruling 1.
- Acceptance should be stated before the run: envelope and flowing-interior
  max \|ΔP\|, makeup demand, opening inward/outward legs, balance residual, and
  the design-lane check used by stage 4. The audit scenario is a witness, not
  an acceptance target; do not tune `area_m2` or `exchange_m3h` to reproduce
  33.04 Pa.

## 4. Pope AP110 — adjudication plan for internal connectivity/closure

### 4.1 Current representation

`data/platforms/pope_ap110/air_flow_paths.json` has no `ambient_openings`
key. `Boat_Deck_Open`, `Stern_Gun_Deck`, and `Focsle_Deck` are three of 28
rooms in `VENT_Stores_Holds`:

```json
{
  "id": "VENT_Stores_Holds",
  "ach": 4.0,
  "oa_fraction": 0.4,
  "vent_mode": "mech_supply_exhaust",
  "description": "open decks, stores, holds and tank spaces (weather/nat vent)"
}
```

With the default duty, audit-rule outdoor ACH is `4.0 * 0.5 * 0.4 = 0.8` for
every room in that group. The three explicitly open decks are therefore
weather-exposed by description and elevation, but they share one HVAC group
with enclosed superstructure, stores, holds, and tankage. Only
`Sup_Deck_Mech` currently carries `exposure: "enclosed"` in
`spatial_layout.json`; the three open decks have no `exposure` field.

### 4.2 Measured evidence

From the committed audit:

| Pope AP110 commissioned lane | envelope max \|ΔP\|, Pa | flowing interior max \|ΔP\|, Pa | makeup demand, m³/h | opening net inward, m³/h |
|---|---:|---:|---:|---:|
| baseline | 1,355,146.75 | 58,552.33203125 | 28,574.92272392768 | 0 |
| `all_explicit_weather_open` | 806,283.75 | 804,135.8125 | 28,574.92272392768 | 8,085.661858107431 |

Adding openings to the three open decks reduces the envelope maximum but
**raises** the flowing-interior maximum by more than an order of magnitude.
`group_cut_budgets.csv` places the largest residual on `ladder_well_5`
(`VENT_Machinery -> VENT_Stores_Holds`, 476 expanded paths, declared reference
flow 50 m³/h): baseline net flow −5,576.08 m³/h along authored direction,
max path \|ΔP\| 58,552.33 Pa; all-open net flow −10,527.14 m³/h, gross flow
12,618.75 m³/h, max path \|ΔP\| 804,135.81 Pa. Exterior access alone is
therefore insufficient; the demand distribution and internal connectivity are
the defect class.

### 4.3 Adjudication plan

This is a plan, not a data change. The sequencing is deliberate: **topology and
closure first, ambient openings second**, with paired controls so the effect of
each is attributable.

**Step P0 — freeze the question.** Owner decides whether Pope's intended
operating state is historical service, museum static, or a bounded cruise
configuration. The audit treats historically operational service/closure modes
as the intended interpretation for museum-plan hulls; that assumption must be
confirmed for AP110 before closure states are authored.

**Step P1 — compartment evidence table.** For each of the 28 rooms in
`VENT_Stores_Holds`, record:

- deck, elevation, volume, floor area, description, `type`, occupancy, and
  current `exposure`;
- HVAC group membership and whether the room is a supply, return, or exhaust
  leaf in the exported AHS paths;
- adjacency edges and `cross_zone_links` touching the room;
- `systems_notes.json` mode and evidence grade (`sheet_read`, `era_rule`,
  `era_plausible`, or absent);
- import provenance in `import_provenance.json` / `deck_manifest.json` where
  available.

The three open decks should be classified explicitly as weather-exposed only if
the evidence supports it; `Boat_Deck_Open`, `Stern_Gun_Deck`, and
`Focsle_Deck` are the current candidates. Enclosed candidates include at least
`Sup_Deck_Mech`, `Nav_Bridge`, `Signal_Control_Block`, `Top_House`,
`Aft_Loading_House`, stores, holds, and tankage, but each needs its own row.

**Step P2 — drawing/HVAC evidence.** Use AP110 general-arrangement and
ventilation/HPAC material already in-tree or supplied by the owner to decide,
for each candidate edge, whether it is:

- open to weather or to an adjacent open deck;
- a passage/door/hatch that is open in service;
- a weathertight or damage-control closure that should be a small leakage
  opening, not a free passage;
- a ventilation trunk or fixed fan transfer, not a pressure-opening;
- absent/not represented.

Where drawings are absent, the declared evidence grade controls the
confidence: `sheet_read` can support an authored opening or closure; `era_rule`
and `era_plausible` can support only a Grade C assumption with a stated axis.
Do not convert a global adjacency `type` mapping into a Pope-specific repair.

**Step P3 — HVAC grouping adjudication.** Decide whether `VENT_Stores_Holds`
should remain one group. The measured failure is consistent with a single
aggregate group mixing open weather decks, occupied superstructure, stores,
holds, and tankage. Options for the owner:

1. keep one group but author internal openings/closures so the ContamX network
   matches the adjudicated topology;
2. split weather decks from enclosed stores/holds before authoring openings;
3. keep grouping but re-declare which rooms receive supply/return/exhaust.

Any split is a platform-data change for a later PR, not this document.

**Step P4 — opening-vs-topology sequencing.** Run paired controls on
`pope_ap110` only after P1–P3 are frozen:

- control A: topology/closure/HVAC-group changes with no new ambient openings;
- control B: the three `open_deck` ambient openings with no topology change
  (already witnessed by `all_explicit_weather_open`);
- control C: both, only if A and B are individually understood.

Do not author Pope ambient openings before the topology control, because the
all-open scenario shows that openings alone can move the maximum pressure to a
worse interior path. If the owner wants an earlier witness, the safe interim is
to record the negative result and keep Pope in the grouped-zone open item.

**Step P5 — witnesses.** For each control, report commissioned and design
lanes, envelope max \|ΔP\|, flowing-interior max \|ΔP\|, makeup demand,
opening inward/outward legs, per-link net/gross/max \|ΔP\| for
`ladder_well_1`–`ladder_well_5`, balance residual, and the path-map
`ambient_opening` rows. Acceptance criteria must be frozen before the run; the
stage-4 design-lane witness range (0.5–374 Pa) is a useful comparison, not a
universal cutoff.

## 5. Aeolus ARC3 — small group-link capacity class

### 5.1 Current representation

`data/platforms/aeolus_arc3/air_flow_paths.json` already has three
`ambient_openings` records from stage 4 (`Top_Of_House`, `Cable_Working_Deck`,
`Bow_Sheave_Area`), all `type: "open_deck"`, `wind_speed_m_s: 1.0`,
`schedule: "always_open"`, with Grade C deck-face areas 112.966, 167.088, and
44.208 m². The spatial zones carry `exposure: "weather"`. `AHU_Weather` has
`ach: 0.0`, `oa_fraction: 1.0`, `vent_mode: "mech_supply_exhaust"`; the decks
are therefore exposed through `ambient_openings`, not through group OA.

The sanitary make-up path is the open item. `AHU_Cable` (`Cable_Tanks`) is
`ach: 3.0`, `oa_fraction: 1.0`, `vent_mode: "mech_exhaust"`. Ladder-well links
are declared as:

```json
{
  "from": "AHU_Machinery",
  "to": "AHU_Cable",
  "flow_rate_m3h": 50.0,
  "path": "ladder_well_6",
  "is_hvac_ducted": false,
  "description": "Auto ladder-well coupling between adjacent AHU branches",
  "direction": "bidirectional",
  "mechanism": "pressure_opening",
  "filtered": false
}
```

`ladder_well_5` is the corresponding `AHU_Cable -> AHU_Weather` link. In the
ContamW exporter, a passive `pressure_opening` cross-zone link is sized by
`_orifice_elem_for_flow()`: the declared `flow_rate_m3h` is divided across
expanded room pairs and converted to a `plr_orfc` area for a 1 Pa design flow.
It is therefore a **reference flow used to set opening area**, not a solved
capacity cap.

### 5.2 Measured evidence

From `current_local_solve_summary.csv` and `group_cut_budgets.csv`:

| Aeolus ARC3 commissioned lane | max \|ΔP\|, Pa | envelope \|ΔP\|, Pa | interior flowing \|ΔP\|, Pa | makeup demand, m³/h | opening net inward, m³/h | envelope net inward, m³/h |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 952.9536743164062 | 952.9536743164062 | 434.7975158691406 | 1,066.0409476130371 | 792.2811838314883 | 273.76258714538517 |
| design baseline | 3.1224098205566406 | 3.1224098205566406 | 0.07130396366119385 | 0.0 | 11.591852804467635 | -11.591155234801672 |
| zero sanitary exhaust | 3.0995330810546875 | 3.0995330810546875 | 0.08298812806606293 | 0.0 | 12.501636745790165 | -12.491920190245118 |

The dominant commissioned residuals are:

- `ladder_well_5` (`AHU_Cable -> AHU_Weather`): 8 expanded paths, declared
  reference flow 50 m³/h, net −797.2674056649931 m³/h along authored direction,
  gross 797.2674056649931 m³/h, max path \|ΔP\| 434.7975158691406 Pa.
- `ladder_well_6` (`AHU_Machinery -> AHU_Cable`): 3 expanded paths, declared
  reference flow 50 m³/h, net −792.1080881092232 m³/h, gross
  792.1080881092232 m³/h, max path \|ΔP\| 342.8584289550781 Pa.

The solved flows are about 16 times the declared 50 m³/h reference on these two
links and carry hundreds of Pa. The zero-sanitary-exhaust control removes the
1,066 m³/h extraction demand and collapses max \|ΔP\| to about 3.1 Pa, so the
pressure problem is the sanitary make-up path, not the three open decks.

### 5.3 Decision requested

**Recommendation:** classify this as a **group-link capacity/orifice-area
defect**, not as a reason to add more ambient openings. The 50 m³/h declarations
are not credible large-passage capacities; they are un-sourced reference flows
that set small orifice areas. The defect is using those references for links
that must carry roughly 800 m³/h each in the commissioned solve.

Do **not** "fix" this by setting `flow_rate_m3h` to the solved 797/792 m³/h.
That would fit the diagnostic. Defensible replacements, in order of preference:

1. **Author passage evidence.** If AP/ARC drawings, compartment descriptions,
   or systems notes identify the ladder-well/hatch/trunk openings between
   `AHU_Weather`, `AHU_Cable`, and `AHU_Machinery`, replace the auto
   `pressure_opening` reference with an authored opening type/area and evidence
   grade. This is the only non-assumption path.
2. **Declare a bounded Grade C operating assumption.** If no drawing exists,
   declare an explicit assumption such as "ladder well open at both ends with
   area X m²" or "crew-passage hatch open" with a stated range, then run
   sensitivity controls. The assumption must be recorded as Grade C and must
   not be tuned to hit 3 Pa or 953 Pa.
3. **Keep reference flow but re-scope semantics.** If the owner wants to keep
   `flow_rate_m3h` as a nominal transfer, the schema/exporter contract must say
   that it is not a capacity and that passive `pressure_opening` area comes
   from an independent opening area. That is an engine/exporter change and is
   out of scope for this doc-only PR.

**Witnesses for the Aeolus decision.** On `aeolus_arc3` only:

- baseline commissioned/design and zero-sanitary-exhaust controls already in
  `current_local_solve_summary.csv`;
- a ladder-well capacity control that changes only `ladder_well_5` /
  `ladder_well_6` representation, with per-link net/gross/max \|ΔP\|;
- opening inward/outward legs and balance residual, because the three
  `ambient_openings` already supply about 792 m³/h inward while envelope leaks
  supply about 274 m³/h inward;
- native/field compare only if the change is claimed to improve transport
  agreement; pressure closure alone does not prove contaminant transport.

Acceptance must be frozen before the control: envelope max \|ΔP\|, interior
flowing max \|ΔP\|, makeup demand, per-link flows, and balance residual. The
zero-exhaust control is a diagnostic bound, not a recommended operating mode.

## 6. Fleet pattern table

Grouped weather zones with outdoor exchange > 0 on current main, by hull and
HVAC group. Outdoor ACH uses the audit-rule calculation above. Zone ids are
listed so the owner can see which hulls share each pattern without opening
every platform file.

| hull | HVAC group | outdoor ACH | zones | zone ids |
|---|---|---:|---:|---|
| `antietam_cvs36` | `VENT_Hangar` | 1.600 | 1 | `Gallery_Deck` |
| `antietam_cvs36` | `VENT_Weather` | 0.500 | 2 | `Flight_Deck`, `Forecastle_Deck` |
| `assistance_ar17` | `HVAC_Accom` | 3.000 | 4 | `Boat_Gun_Deck_Aft`, `Boat_Deck_Fwd`, `Stern_Working_Deck`, `Fwd_Working_Deck` |
| `astoria_ca34` | `VENT_Weather` | 0.500 | 5 | `Upper_Deck_Aft`, `Boat_Deck`, `Focsle_Deck`, `Fantail`, `Catapult_Deck` |
| `battler_acv6` | `VENT_Weather` | 0.500 | 2 | `Walkways_Focsle`, `Flight_Deck` |
| `castle_class_corvette` | `HVAC_Accom` | 0.750 | 1 | `Upper_Deck_Aft` |
| `chicago_cg11` | `VENT_Weather` | 0.500 | 8 | `Open_03`, `Helo_Deck_02_Aft`, `Terrier_Deck_02`, `Launcher_Deck_01`, `Fantail_Weather`, `Helo_Deck`, `Forecastle_Deck`, `Bow_Weather` |
| `enterprise_galaxy_tng` | `AHU_Public` | 0.675 | 2 | `Holodeck1`, `Holodeck2` |
| `erie_pg50` | `HVAC_Accom` | 3.000 | 1 | `Focsle_Stores` |
| `erie_pg50` | `VENT_Weather` | 6.000 | 4 | `Sup_Deck_Open`, `Fantail_Aft`, `Gun_Deck_Aft`, `Focsle_Main` |
| `esteem_mso438` | `HVAC_Accom` | 1.200 | 1 | `Deck_House_Main` |
| `esteem_mso438` | `VENT_Weather` | 6.000 | 4 | `Reel_Deck`, `Boat_Deck_Aft`, `Focsle_01`, `Sweep_Deck` |
| `fort_mandan_lsd21` | `VENT_Machinery_Holds` | 4.500 | 1 | `Top_House_Open` |
| `fort_mandan_lsd21` | `VENT_Well_Deck` | 2.000 | 2 | `Well_Cover_Open`, `Well_Deck` |
| `fort_william_j311` | `HVAC_Accom` | 2.500 | 1 | `Signal_Deck` |
| `fort_william_j311` | `VENT_Machinery` | 2.000 | 2 | `Quarterdeck`, `Foc_Deck_Open` |
| `gosper_apa170` | `VENT_Machinery_Holds` | 4.500 | 6 | `Boat_Deck_Open`, `Boat_Deck_Open_Fwd`, `Focsle_Deck_Open`, `Fantail`, `Boat_Stowage_Deck`, `Main_Deck_Open_Fwd` |
| `idaho_bb42` | `HVAC_Main` | 3.000 | 1 | `Fantail` |
| `independence_cvl26` | `VENT_Hangar` | 1.600 | 1 | `Gallery_Deck` |
| `independence_cvl26` | `VENT_Weather` | 0.500 | 3 | `Flight_Deck`, `Poop_Deck`, `Forecastle_Deck` |
| `jupiter_ac3` | `VENT_Cargo` | 2.000 | 2 | `Poop_Deck_Open`, `Focsle_Deck_Open` |
| `legend_class_nsc` | `HVAC_Aviation` | 3.200 | 2 | `Flight_Deck`, `Boat_Deck` |
| `luzon_arg2` | `HVAC_Accom` | 3.000 | 4 | `Gun_Weather_Sup`, `Boat_Deck_Aft`, `Stern_Weather`, `Chain_Locker_Focsle` |
| `mercury_aks20` | `HVAC_Accom` | 3.000 | 2 | `Fantail`, `Foredeck` |
| `miami_cl89` | `VENT_Weather` | 0.500 | 2 | `Catapult_Deck`, `Bow_Weather` |
| `middlesex_lst983` | `HVAC_TankDeck` | 1.200 | 2 | `Tank_Deck`, `Tank_Deck_Port` |
| `midway_cv41` | `VENT_Weather` | 0.500 | 1 | `Flight_Deck` |
| `missouri_bb63` | `VENT_Weather` | 0.500 | 5 | `Signal_Deck`, `Fantail_Open`, `Boat_Waist_Open`, `Forecastle_Open`, `Focsle_Void_2D` |
| `montana_acr13` | `VENT_Weather` | 15.000 | 2 | `MD_Aft_Open`, `MD_Forecastle_Open` |
| `new_jersey_bb62` | `VENT_Weather` | 0.500 | 5 | `Signal_Deck`, `Fantail_Open`, `Boat_Waist_Open`, `Forecastle_Open`, `Focsle_Void_2D` |
| `pope_ap110` | `VENT_Stores_Holds` | 0.800 | 3 | `Boat_Deck_Open`, `Stern_Gun_Deck`, `Focsle_Deck` |
| `pt_564` | `VENT_Weather` | 3.600 | 2 | `Torpedo_Deck`, `Foredeck` |
| `puncher_cve53` | `VENT_Weather` | 0.500 | 1 | `Flight_Deck` |
| `ranger_cv4` | `VENT_Weather` | 0.500 | 2 | `Flight_Deck`, `Poop_Deck` |
| `river_class_frigate` | `HVAC_Accom` | 2.500 | 1 | `Signal_Deck` |
| `san_antonio_class_lpd` | `HVAC_Aviation` | 3.200 | 1 | `Flight_Deck` |
| `san_antonio_class_lpd` | `HVAC_Well_Deck` | 3.000 | 1 | `Well_Deck` |
| `saratoga_cv60` | `VENT_Weather` | 0.500 | 1 | `Flight_Deck` |
| `squier_ap130` | `VENT_Stores_Open` | 2.000 | 1 | `Stern_Deck_Up` |
| `thetis_bay_cve90` | `VENT_Weather` | 0.500 | 1 | `Flight_Deck` |
| `wasp_cv7` | `VENT_Weather` | 0.500 | 1 | `Flight_Deck` |
| `winnipeg_j337` | `HVAC_Accom` | 2.500 | 1 | `Signal_Deck` |
| `winnipeg_j337` | `VENT_Machinery` | 2.000 | 2 | `Quarterdeck`, `Foc_Deck_Open` |
| `wisconsin_bb64` | `VENT_Weather` | 0.500 | 5 | `Signal_Deck`, `Fantail_Open`, `Boat_Waist_Open`, `Forecastle_Open`, `Focsle_Void_2D` |
| `wright_cc2` | `VENT_Weather` | 0.500 | 3 | `Flight_Deck_Aft`, `Flight_Deck_Mid`, `Flight_Deck_Fwd` |
| `yorktown_cv5` | `VENT_Weather` | 0.500 | 1 | `Flight_Deck` |

## 7. Staging recommendation

Do not roll out fleet-wide. Stage by representation class, with one witness
hull before any pattern generalizes.

| stage | scope | witness hull(s) | decision gate |
|---|---|---|---|
| G0 | Owner ruling on the fleet question | none | Rule whether grouped OA>0 weather zones may receive `ambient_openings`, and whether group OA must be re-declared to avoid double-counting. |
| G1 | Midway flight-deck opening representation | `midway_cv41` | Choose opening-replaces-OA vs opening-additional; author only after the double-count ruling; measure before/after. |
| G2 | Pope topology/closure adjudication | `pope_ap110` | Complete P0–P3 evidence table; run topology control before any opening control; do not author openings from the all-open scenario alone. |
| G3 | Aeolus ladder-well capacity class | `aeolus_arc3` | Decide whether the defect is missing passage evidence, an unsourced Grade C assumption, or a schema/semantics mismatch; do not fit `flow_rate_m3h` to solved flow. |
| G4 | Pattern generalization | one unmodified witness per pattern before class rollout | Carrier: `yorktown_cv5` or `wasp_cv7` after Midway; battleship: `missouri_bb63`; cruiser: `astoria_ca34`; auxiliary: `assistance_ar17` plus one `VENT_Machinery_Holds` hull such as `gosper_apa170`; amphibious: `san_antonio_class_lpd` and `fort_mandan_lsd21`; miscellaneous: `erie_pg50`/`montana_acr13`; fiction: hold `enterprise_galaxy_tng` unless the owner includes fiction weather openings under the calm-wind exception. |

Every stage needs the same witness bundle: pressure/balance diagnostic rows,
paired native/commissioned diagnostic, exported path-map checks for
`ambient_opening` or changed passive-opening rows, balance residual, and a
pre-frozen acceptance statement. Pressure witnesses alone do not authorize
transport claims; if a later PR claims contaminant-transport improvement, it
needs the paired compare evidence used by the stage ledgers.

## 8. Explicit owner decisions required

1. **Fleet rule:** may HVAC-grouped weather zones with OA>0 receive
   `ambient_openings`, and if so must the HVAC group's outdoor exchange be
   re-declared to avoid representing the same physical opening twice?
2. **Midway:** for `midway_cv41/Flight_Deck`, choose opening-replaces-OA or
   opening-additional; confirm whether to author `exposure: "weather"`; approve
   the Grade C 582.687 m² deck-face witness area or supply better evidence.
3. **Pope:** confirm the intended operating/closure state for AP110; approve
   the P1–P3 evidence-gathering plan; decide whether `VENT_Stores_Holds` stays
   one group; require topology control before opening control.
4. **Aeolus:** decide the defensible basis for `ladder_well_5`/`ladder_well_6`
   capacity: drawing/passsage evidence, a declared Grade C assumption with a
   stated range, or a schema/semantics change. Reject fitting the 50 m³/h
   reference to the solved ~792–797 m³/h.
5. **Staging:** approve G1–G3 as bounded hull-level changes before any fleet
   pattern rollout, and name the pattern witnesses if G4 is authorized later.

## 9. What this proposal does not do

- It does not author `ambient_openings`, `exposure`, HVAC groups,
  `cross_zone_links`, adjacency, leak areas, schedules, or exporter/engine
  semantics.
- It does not rerun the fleet or change frozen Phase1/Phase2 artifacts.
- It does not treat the audit scenarios as approved repairs; they are
  localization witnesses.
- It does not certify real-vessel ventilation adequacy. Huge pressure values
  are diagnostic signs of inadequate represented operating conditions, not
  credible vessel pressures or validated flow predictions.
