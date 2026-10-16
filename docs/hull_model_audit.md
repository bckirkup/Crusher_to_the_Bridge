# Hull model audit — fleet deviation report

> **Status:** Living audit. Index: [README.md](README.md).

## Purpose

`tools/hull_audit.py` is a static realism audit over every platform bundle in
`data/platforms/<pid>/` (`spatial_layout.json`, `air_flow_paths.json`,
`crew_manifest.json`, `systems_notes.json`). It exists because the fleet is now
its own reference population: imported hulls share conventions (zone signatures,
era rules, manifest wiring), so a platform that departs from its siblings is
visible without external fleet data.

## Scope — baseline vs declared deviations

The audit checks the **declared design baseline (normal steaming)** for
*unintentional* defects. Operational statuses that legitimately distort airflow
— lockdown, collective-protection citadel, HVAC casualty — are declared
deviations layered on top of the baseline and are **out of scope for the flag
set**. Whether a hull can express those states is recorded instead as
operability metrics per platform:

- `isolation_beds` — medical / isolation capacity (quarantine mode).
- `non_citadel_share` — share of interior volume ventilated by
  `nat_supply`/`open_air` modes, i.e. volume *outside* a hypothetical sealed
  citadel (higher = weaker collective-protection posture).
- `starved_groups` — dedicated exhaust/extraction groups with no makeup link:
  the wiring that produces real airflow deviations when a makeup branch is cut.
- `single_path_zones` — zones ventilated only by their own group with no
  adjacency to ventilated neighbours: sealed if the HVAC group is a casualty.

Severity vocabulary:

- **flag** — design-defect candidate on the baseline; needs engineer review.
- **note** — deviation worth knowing about, likely intentional (e.g. exterior
  decks carry no HVAC group by construction, OR cabins orphaned from the
  adjacency graph by declared design).

## Checks

1. **referential integrity** — HVAC-group room refs, cross-zone link endpoints,
   adjacency endpoints, `serves`, `graywater_uses`, manifest `berth_zone`/
   `duty_zone` all resolve.
2. **topology** — zone → HVAC-group coverage census (ungrouped zones classified
   exterior/void/occupied), adjacency-graph components, orphaned room classes.
3. **flow closure** — per the native engine's
   `build_zone_air_exchange_map` semantics: dedicated-exhaust groups
   (`hvac_duty<=0 && oa_fraction>=1`) lacking makeup links, zero-removal
   occupied zones, sealed zones (ungrouped + no passive exchange paths).
4. **mode consistency** — `systems_notes.zone_modes` intent vs the direction
   the zone's HVAC group actually realizes (supply-only vs exhaust-only vs
   mixed); anachronistic `mech_ac` on pre-air-conditioning era hulls.
5. **derived metrics** — m³/crew, dining seats/crew, sanitary occupancy per
   100 crew, berth assignment vs `max_occupancy × hot_bunk_ratio` (the
   hot-bunk occupancy lever is honoured before any oversubscription flag),
   manifest vs `nominal_complement` tie-out per role group, deck-envelope
   overclaim, ACH-by-class, `hvac_duty` scaling notes, systems_notes
   evidence share (`sheet_read` vs `era_rule` vs `era_plausible`).

Dynamic checks (in `tools/hull_dynamics_audit.py`, run — not read):

6. **occupancy smoke** — a no-pathogen voyage (`initial_infected: None`)
   with per-epoch zone occupancy observed from agent locations. Two arms
   per manifest hull: `default` (the shipped `ship_graph.agent_classes`
   taxonomy — cruise-hull prefs `PC_`/`CC_`/`Medical_Center`/`Engine`/
   `Galley`, which substring-miss most naval zone ids and scatter
   silently) vs `manifest` (`agent_classes` generated from
   `crew_manifest.json`, pinning `home_zone_preference`/`duty_zone` to
   exact zone ids). Outputs: zones never entered, peak occupancy vs
   `max_occupancy`, night-berthing concentration, and the share of
   agents whose assigned `home_zone` is a manifest-declared berth.
7. **drainage fingerprint** — unit mass injected into every real zone
   and stepped 48 epochs through `ContamTransportEngine` with
   `natural_decay_rate=0` and the divergence work's
   `filter_efficiency=0.50`. The retained-mass curve is the hull's
   drainage signature: ~1.0 = no exhaust path (the mass-trap defect
   class); the per-zone accumulation table names where mass pools.

Fleet-level passes: era-rule consistency (same era+zone-class, era-inferred
evidence only — `sheet_read` is trusted), within-era IQR outlier fences, and
adjacency-type coverage of the ContamX `passive_rates` table (types with no
explicit rate fall back to 10 m³/h — a coverage gap, not necessarily an error).

### What `max_occupancy` means in the engine

It is **rated capacity of installed fittings and a selection weight — never
a presence cap**. Three consumers:

- `weighted_zone_choice` and the dining-zone draw weight zones by
  `capacity` (default 100 when absent): an oversized `max_occupancy`
  *attracts* traffic rather than excluding it.
- Fomite per-occupant item counts scale off it (400 seats = 400 place
  settings).
- The boxed-meal overflow directive caps diners at
  `int(round(frac * max_occupancy))` only when that mode is armed.

Consequence: berth oversubscription flags in this audit mean "the manifest
assigns more crew than fittings rate" — manifests pin classes to
`berth_zone` regardless, and the over-cap zone *pulls extra weighted
traffic*. `hot_bunk_ratio` scales capacity before flagging; hot bunking is
a real practice and the honouring is deliberate. But over-cap findings are
not absorbable by occupancy caps — they are either under-read fittings or
correct overcrowding data that will show up in the check-6 overflow table.

## Usage

```bash
python3 tools/hull_audit.py                 # markdown report to stdout
python3 tools/hull_audit.py --platforms midway_cv41,raven_am55
python3 tools/hull_audit.py --json-out reports/hull_audit.json \
    --md-out reports/hull_audit.md
python3 tools/hull_audit.py --min-severity flag

# dynamic checks (ShipSimulation voyages — minutes to ~an hour fleet-wide)
python3 tools/hull_dynamics_audit.py --epochs 48 \
    --json-out reports/hull_dynamics.json --md-out reports/hull_dynamics.md
python3 tools/hull_dynamics_audit.py --platforms pce_874 --arms default
python3 tools/hull_dynamics_audit.py --skip-occupancy   # drainage only
```

CI-friendly: exit 0 always (it reports findings, it does not gate them).
Synthetic-platform fixtures drive `tests/test_hull_audit.py` and
`tests/test_hull_dynamics_audit.py`.

## Second fleet run — 2026-10-16, dynamic checks (25 platforms, seed 42, 48 epochs)

`tools/hull_dynamics_audit.py` over every bundle under `data/platforms/`.
Occupancy smoke ran 13 manifest hulls in `default` + `manifest` arms and
5 nominal-complement cruise hulls in `default` arm only; the 7
no-crew-source hulls ran the drainage fingerprint only.

Headline findings (measured, this run):

1. **Duty-zone pins cannot resolve on the imported hulls — every duty
   space holds zero occupants.** `_resolve_class_zones` resolves
   `duty_zone` only inside Free+Dining-typed zones, so a pin at
   Engineering/Medical/ops space silently degrades to a random
   free/dining draw. The pin-resolution pass flags it statically on every
   manifest hull (`engine_room→Engine_Rm`, `medical→Sick_Bay`,
   `radio_ops→PriFly_FlagPlot`, `ops_radio→Radar_Plot`…); the smoke
   confirms it dynamically — under the manifest arm, `Engine_Rm`,
   `Fire_Rm_*`, `Boiler_Rm`, `Sick_Bay`, `Radio_Rm`, `CIC`, `Radar_Plot`,
   `Work_Centers` hold **no agent in any epoch** on every imported hull.
   Consequence for dose modeling: machinery-space airborne/fomite dose is
   computed for rooms nobody is in, and crew work-hour co-location is
   realized as corridor leisure traffic instead of watch-standing.
   **Resolved** — `_resolve_duty_zone` now matches a duty pin against
   every zone (duty stations live wherever the hull puts them) and keeps
   the Free+Dining fallback for unmatched pins, so the RNG stream shape
   is unchanged. Verified on davison_dd618 (12 epochs, seed 42, manifest
   arm): `Engine_Rm_Fwd`, `Mid_Services`, `CIC_Block`, `Nav_Bridge_Sonar`
   now hold crew — CIC_Block peaks 38 agents vs cap 12, a real
   watch-standing density the gap used to hide. Where a pin substring now
   matches additional zones on authored hulls (e.g. cruise `Engine`),
   the realized work draw shifts — expected new-mechanism delta, not
   drift.
2. **Berth pins resolve but collapse to few blocks — measured
   overcrowding.** `manifest_berth_hit` is 1.0 under the manifest arm
   (berth pin → Room-type zone works), but `home_distinct` collapses to
   1–3 zones because manifests assign most crew to one block. Peak
   occupancy vs `max_occupancy` is measured crowding, not a sim cap:
   midway `Officers_Country_02` 4712 agents / cap 80, cvl26
   `Officers_Country` 1566/85, davison `WR_Block` 249/20, cannon
   `Aft_Berthing_1P` 170/40. These confirm the static oversubscription
   flags as real crowding (beyond what `hot_bunk_ratio` absorbs) and name
   the zones to re-read in the GA.
3. **Wardroom attractor (default arm):** officer wardrooms typed `Dining`
   absorb the fallback meal draw — midway `Wardroom_02` 1190/60 and
   `Wardroom_2D` 1570/80, cvl26 `Wardroom` 856/114, ruchamkin
   `Wardroom` 202/12. Under default classes the dining pref misses and
   weighted dining choice lands on whatever `Dining` rooms exist,
   officers' mess included. Same mechanism as (1): a preference that
   misses its domain degrades into a weighted draw, not an error.
4. **Drainage fingerprints: no traps fleet-wide.** Retained mass after
   48 epochs (unit inject, decay 0): 11–56%. All accumulating mass pools
   in `HD_*` sanitary-exhaust zones — the designed drain path, so the
   residual is in-transit mass at the exhaust endpoints, not sealed
   pockets. The cruise reference band (0.27–0.38) brackets most imports;
   above it: fletcher 0.561, destroyer_baseline 0.548, messy_cruise_500
   0.539, gordon_gunter 0.425 — slower-draining hulls worth a plumbing
   review; below it: midway 0.112, cannon 0.132, ruchamkin 0.140,
   independence 0.182.
5. **`HD_*` head zones never hold agents** — sanitary spaces are not
   schedule destinations in the engine at all (fleet-wide, both arms).
   Expected modeling, recorded so the never-occupied list isn't misread
   as orphaned compartments.
6. **Cruise-hull reference behavior** — the attractor artifact exists on
   the reference hulls too: mega `Engine_Room_Aft` 727/60, classic
   `Engine_Room` 199/20. The imported hulls' deviations are therefore
   mostly *coverage* (duty pins unreachable), not a new class of scatter.
7. **Default-arm scatter measured:** `home_on_manifest_berth_frac` under
   the shipped taxonomy is 0.19–0.77 across manifest hulls (midway 0.19,
   davison 0.26, castle 0.75) — i.e., 23–81% of crew get a non-berth
   home zone when the cruise-class prefs miss naval zone ids. The
   manifest arm is the meaningful wiring.

`crew_manifest.json` note: the sim does not consume it — it is the GA
import's proposed-class ledger. The `manifest` arm exists to measure what
wiring it into `ship_graph.agent_classes` would realize; today the hulls
sail on the shipped cruise-taxonomy classes (the `default` arm).

### Berthing deficit table (static, widest domain)

Manifest crew vs total capacity of the berth resolution domain — every
Room/Cabin_Corridor zone, including duty spaces the manifest could in
principle pin to, so it *overstates* real berthing. Even against that
ceiling, 10 of 13 manifest hulls are capacity-short: the deficit is not
a manifest pin problem, it is either a GA under-read (berthing
compartments missed, or `max_occupancy` under-plated) or genuine
wartime overcrowding that should be declared — `hot_bunk_ratio` is the
in-engine lever, declared on fiction hulls today.

| platform | manifest crew | berth-domain cap | worst assigned zone | verdict |
|---|---|---|---|---|
| midway_cv41 | 4712 | 2600 | Crew_Berthing_3D_Mid 2441/600 | short — deep (GA re-read) |
| independence_cvl26 | 1566 | 1368 | Crew_Berthing_3D 785/490 | short (GA re-read) |
| ruchamkin_apd89 | 357 | 266 | Troop_Berthing_Fwd 162/70 | short (GA re-read or troop overload) |
| sigsbee_dd502 | 322 | 267 | Crew_Berthing_Fwd 228/80 | short |
| davison_dd618 | 283 | 262 | Crew_Qtrs_1P 188/70 | short (marginal — crowding plausible) |
| passumpsic_ao106 | 280 | 181 | Crew_Qtrs_Fwd 165/60 | short (GA re-read) |
| nields_dd616 | 262 | 254 | Crew_Qtrs_1P 180/70 | short (marginal — crowding plausible) |
| cannon_de701 | 216 | 192 | Crew_Berthing_1P 109/80 | short |
| raven_am55 | 105 | 80 | Crew_Quarters 84/60 | short |
| pce_874 | 99 | 73 | Crew_Quarters 78/55 | short |
| bolster_ars38 | 90 | 79 | Crew_Quarters 70/55 | short (marginal) |
| castle_class_corvette | 99 | 103 | Seamen_Mess 62/45 | **pin-collapse** — `Mess_Mid` unassigned; manifest re-spread, no GA re-read |
| gordon_gunter_r338 | 35 | 43 | — | ok |

Two mechanisms to separate per hull: (a) WW2-era crowding is real —
wartime complements ran above design berthing (extra AA crews, troops) —
so a modest shortfall is a *declared crowding* decision, not an error;
(b) deep deficits like midway (4712 vs 2600 even counting every Room
zone, including shops and CIC) exceed any crowding interpretation and
point at berthing compartments the GA read missed. The decision per
hull: re-read the plates, or declare `hot_bunk_ratio`/crowded berthing
as the intended realism. Naming caveat for future audits: stateroom
zones named `*_SR` (gordon_gunter) dodge the berth-name hints; the
Room-type domain is the reliable denominator.

## First fleet run — 2026-10-16, 22 platforms

Headline deviation candidates (full per-platform detail below):

- **Berthing oversubscription is systemic** in the imported naval hulls.
  Worst cells: Midway `Crew_Berthing_3D_Mid` 2441 assigned vs capacity 600
  (total 4712 vs 2080), CVL-26 `Crew_Berthing_3D` 785 vs 490, APD-89
  `Troop_Berthing_Fwd` 162 vs 70. `hot_bunk_ratio` is honoured before
  flagging, so these exceed even a hot-bunk interpretation — plate-read
  `max_occupancy` appears to record physical bunks while manifests assign
  everyone a bed simultaneously. If occupancy is a sim cap rather than a bunk
  count, night-berthing crowding/dose is distorted on every naval hull.
- **APD-89 complement mismatch**: `nominal_complement.crew` 213 vs manifest
  crew rows summing 195 — an 18-man class-level gap (possibly the flag staff
  or an under-digitized rating block).
- **Era-rule contradictions**: `usn_ww2/mess` and `usn_ww2/magazine` modes are
  era-inferred yet disagree both across hulls *and within* individual hulls —
  the importer's mode assignment is inconsistent, not evidence-driven.
  `rn_ww2/mess` is Castle's own zones split across two modes.
- **Adjacency-graph islands** (no passive air path to the main component):
  Raven `Sick_Bay` — a *medical* zone, the one compartment that must be
  reachable during an epidemic — flagged; Galaxy `Armory` flagged plus three
  fiction-fragment notes (Airlock/Cargo/ShuttleBay, Bridge complex, Brig);
  Spirit 21-zone detached cabin-corridor component (`CC_D1_*`/`CC_D2_A`,
  likely intentional — cabins connect only through HVAC); PCE-874
  Galley/Mess_Hall block (7 zones) — the food complex with no passive air
  path to the accommodation block, worth a plate read.
- **Sanitary wiring**: Fletcher carries 13 Sanitary zones where naval siblings
  carry 1–3 (plausible for many small heads, worth a read); Gordon Gunter's
  sanitary capacity per 100 crew is ~14× the naval median (NOAA research
  ship, plausible).
- **`hvac_duty: 0.5` top-level on 17 of 22 platforms** halves every declared
  ACH — this is an import-era convention (the GA importer's default derate),
  not per-hull tuning. Worth deciding once whether 0.5 is the intended
  baseline or whether the ACH table already bakes the derate in.
- **passumpsic_ao106** is the within-era m³/crew outlier (79.1 vs IQR fence
  77.6) — an oiler is genuinely spacious, so this is a review item rather
  than a defect.
- **ContamX passive-rate coverage**: 19 of 23 adjacency types used across the
  fleet have no explicit entry in `passive_rates` (fall back to 10 m³/h).
  Explicit table only covers `passageway`, `service_hatch`, `ladder_well`,
  `sealed_door`.

Notably clean: every occupied *interior* zone is in an HVAC group on all 22
hulls (ungrouped census = exterior Free decks and declared voids only), and no
dedicated-exhaust group lacks its makeup link — the `AHU_HD_*` + `*_Makeup`
design that fixed the cruise-hull sink trap holds fleet-wide.

## Snapshot

<!-- regenerated by: python3 tools/hull_audit.py --md-out <this body> -->

Scope: declared design baseline (normal steaming). Operational deviations (lockdown, CPS, HVAC casualty) are intentionally out of scope for the defect flags; the operability fields record whether a hull can express them.

## Fleet panel

| platform | era | zones | crew | m3/crew | seats/crew | sanitary/100 | berth need/cap | flags |
|---|---|---|---|---|---|---|---|---|
| bolster_ars38 | usn_ww2 | 24 | 90 | 45.4 | 6.92 | 15.6 | 90/73 | 0 |
| cannon_de701 | usn_ww2 | 32 | 216 | 35.4 | 2.63 | 4.6 | 216/186 | 0 |
| castle_class_corvette | rn_ww2 | 19 | 99 | 48.7 | 1.14 | 17.2 | 99/83 | 0 |
| classic_cruise_1900 | uninferred | 79 | 1910 | 29.5 | 1.28 | 3.8 | 0/0 | 0 |
| destroyer_baseline | uninferred | 9 | 0 | - | - | - | 0/0 | 0 |
| enterprise_constitution_tos | uninferred | 63 | 0 | - | 0 | - | 0/0 | 0 |
| enterprise_galaxy_tng | uninferred | 127 | 0 | - | 0 | - | 0/0 | 1 |
| expedition_cruise_300 | uninferred | 36 | 0 | - | 0 | - | 0/0 | 0 |
| expedition_cruise_450 | uninferred | 47 | 450 | 43 | 0.82 | 8.4 | 0/0 | 0 |
| fletcher_class_destroyer | uninferred | 33 | 0 | - | 0 | - | 0/0 | 0 |
| gordon_gunter_r338 | noaa_research | 35 | 35 | 187.2 | 1.25 | 80 | 35/37 | 0 |
| independence_cvl26 | usn_ww2 | 46 | 1566 | 51.3 | 3.05 | 6.5 | 1566/1133 | 2 |
| legend_class_nsc | uninferred | 27 | 0 | - | 0 | - | 0/0 | 0 |
| mega_cruise_5000 | uninferred | 192 | 7000 | 57.7 | 0.97 | 5.1 | 0/0 | 0 |
| messy_cruise_500 | uninferred | 130 | 0 | - | 0 | - | 0/0 | 0 |
| midway_cv41 | usn_ww2 | 65 | 4712 | 42.2 | 5.07 | 3.8 | 4712/2080 | 4 |
| passumpsic_ao106 | usn_ww2 | 27 | 280 | 79.1 | 2.64 | 10 | 280/174 | 2 |
| pce_874 | usn_ww2 | 20 | 99 | 22.6 | 2.36 | 4 | 99/73 | 0 |
| raven_am55 | usn_ww2 | 21 | 105 | 33.8 | 2.5 | 3.8 | 105/80 | 1 |
| ruchamkin_apd89 | usn_ww2 | 32 | 375 | 20.9 | 3.12 | 2.9 | 357/190 | 4 |
| san_antonio_class_lpd | uninferred | 29 | 0 | - | 0 | - | 0/0 | 0 |
| spirit_cruise_3000 | uninferred | 115 | 3000 | 28.2 | 1.4 | 3.8 | 0/0 | 0 |

## Fleet findings
- **flag** [era_consistency] `rn_ww2/mess` — era-inferred modes disagree (within-platform only (a hull self-disagrees by zone)): mech_exhaust: ['castle_class_corvette']; nat_supply: ['castle_class_corvette']
- **flag** [era_consistency] `usn_ww2/magazine` — era-inferred modes disagree (cross-platform; ['midway_cv41'] also self-disagree): mech_exhaust: ['independence_cvl26', 'midway_cv41']; nat_supply: ['cannon_de701', 'midway_cv41', 'passumpsic_ao106', 'raven_am55', 'ruchamkin_apd89']
- **flag** [era_consistency] `usn_ww2/mess` — era-inferred modes disagree (cross-platform; ['cannon_de701', 'passumpsic_ao106', 'pce_874', 'raven_am55', 'ruchamkin_apd89'] also self-disagree): mech_exhaust: ['bolster_ars38', 'cannon_de701', 'independence_cvl26', 'midway_cv41', 'passumpsic_ao106', 'pce_874', 'raven_am55', 'ruchamkin_apd89']; nat_supply: ['cannon_de701', 'passumpsic_ao106', 'pce_874', 'raven_am55', 'ruchamkin_apd89']
- **flag** [fleet_outlier] `passumpsic_ao106` — m3_per_crew=79.1 outside usn_ww2 band [7.55,77.55]

## Adjacency type → passive rate coverage

| type | rate m3/h | platforms |
|---|---|---|
| connecting_tube | 10 **(default 10)** | 2 |
| corridor | 10 **(default 10)** | 8 |
| deck_walkway | 10 **(default 10)** | 6 |
| door | 10 **(default 10)** | 6 |
| doorway | 10 **(default 10)** | 6 |
| elevator | 10 **(default 10)** | 2 |
| elevator_bank | 10 **(default 10)** | 5 |
| hatch | 10 **(default 10)** | 2 |
| ladder | 10 **(default 10)** | 8 |
| ladder_well | 12 | 10 |
| multi_deck_void | 10 **(default 10)** | 5 |
| open_deck | 10 **(default 10)** | 5 |
| open_front | 10 **(default 10)** | 4 |
| passageway | 15 | 20 |
| pocket_door | 10 **(default 10)** | 2 |
| pressure_bulkhead | 10 **(default 10)** | 2 |
| sealed_door | 2 | 3 |
| service_corridor | 10 **(default 10)** | 6 |
| service_elevator | 10 **(default 10)** | 2 |
| service_hatch | 8 | 12 |
| service_stairwell | 10 **(default 10)** | 6 |
| stairwell | 10 **(default 10)** | 6 |
| turbolift | 10 **(default 10)** | 2 |

## bolster_ars38

- era=usn_ww2 crew=90 zones=24 vol=4087 isolation=1
- removal ACH by class: berthing=3.0 machinery=5.0 medical=3.0 mess=3.0 open_other=3.2 ops_office=3.0 sanitary=19.1 tank_hold=0.0 weather_open=0.0
- zone-mode evidence: era_plausible=1, era_rule=21, sheet_read=2
- ungrouped: occupied=[] void=['Fuel_Tanks', 'Fwd_Peak']
- berth over-assignment: CPO_Quarters 13>10, Crew_Quarters 70>55
- **note** [metrics] `bolster_ars38` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared
- **note** [modes] `Galley` — declared mech_exhaust sits in HVAC_Accom realized as supply — intent vs field mismatch
- **note** [modes] `Wardroom` — declared mech_exhaust sits in HVAC_Accom realized as supply — intent vs field mismatch
- **note** [topology] `Focsle_Deck_Open` — weather_open zone declares no passage (walk-island gap or closed compartment)
- **note** [topology] `Fuel_Tanks` — unvented zone (tank/hold/void class) — sealed by design?
- **note** [topology] `Fwd_Peak` — unvented zone (tank/hold/void class) — sealed by design?

## cannon_de701

- era=usn_ww2 crew=216 zones=32 vol=7640 isolation=2
- removal ACH by class: berthing=3.0 machinery=5.0 magazine=5.0 medical=3.0 mess=3.0 open_other=4.2 ops_office=3.0 sanitary=19.1 tank_hold=5.0 weather_open=0.6
- zone-mode evidence: era_plausible=3, era_rule=26, sheet_read=3
- adjacency components: [29, 2]
- berth over-assignment: Officers_Qtrs 15>10, CPO_Quarters 24>16, Aft_Berthing_1P 52>40, Crew_Berthing_1P 109>80
- **note** [metrics] `cannon_de701` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared
- **note** [modes] `Galley` — declared mech_exhaust sits in HVAC_Berthing realized as supply — intent vs field mismatch
- **note** [modes] `Wardroom` — declared mech_exhaust sits in HVAC_Accom realized as supply — intent vs field mismatch
- **note** [topology] `Chain_Locker+Fwd_Hold` — adjacency fragment of 2 zones disconnected from main graph

## castle_class_corvette

- era=rn_ww2 crew=99 zones=19 vol=4823 isolation=1
- removal ACH by class: berthing=1.67 machinery=5.0 magazine=5.0 medical=2.5 mess=2.5 open_other=2.5 sanitary=19.1 weather_open=1.25
- zone-mode evidence: era_plausible=2, era_rule=13, sheet_read=4
- berth over-assignment: Seamen_Mess 62>45
- **note** [metrics] `castle_class_corvette` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared
- **note** [modes] `Fwd_Magazines` — declared mech_exhaust sits in VENT_Machinery realized as supply — intent vs field mismatch
- **note** [modes] `Galley` — declared mech_exhaust sits in HVAC_Accom realized as supply — intent vs field mismatch

## classic_cruise_1900

- era=uninferred crew=1910 zones=79 vol=56403 isolation=0
- removal ACH by class: machinery=7.5 mess=4.58 open_other=4.45 room_other=3.14 sanitary=19.2 weather_open=0.0
- **note** [metrics] `classic_cruise_1900` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared

## destroyer_baseline

- era=uninferred crew=0 zones=9 vol=692 isolation=0
- removal ACH by class: berthing=5.0 machinery=5.0 mess=4.0 open_other=3.5 sanitary=19.2
- **note** [metrics] `destroyer_baseline` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared

## enterprise_constitution_tos

- era=uninferred crew=0 zones=63 vol=12020 isolation=8
- removal ACH by class: machinery=8.0 medical=6.0 mess=5.17 open_other=5.47 room_other=3.95 sanitary=19.2
- adjacency components: [40, 4]
- **note** [metrics] `enterprise_constitution_tos` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared
- **note** [topology] `Science1+Science2+Transprt1+Transprt2` — adjacency fragment of 4 zones disconnected from main graph

## enterprise_galaxy_tng

- era=uninferred crew=0 zones=127 vol=36612 isolation=24
- removal ACH by class: machinery=7.6 medical=6.0 mess=6.17 open_other=5.22 room_other=3.7 sanitary=19.2 weather_open=4.5
- adjacency components: [68, 9, 4, 2, 2, 2, 2]
- **flag** [topology] `Armory` — room_other zone declares no passage (walk-island gap or closed compartment)
- **note** [flow_closure] `Armory` — 1 zones ventilated only by their group — HVAC casualty leaves them sealed
- **note** [metrics] `enterprise_galaxy_tng` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared
- **note** [topology] `Airlock+CargoAux+CargoMain+ShuttleBay` — adjacency fragment of 4 zones disconnected from main graph
- **note** [topology] `Bridge+BriefRoom+Comms+OC_D8_A` — adjacency fragment of 9 zones disconnected from main graph
- **note** [topology] `Brig+Security` — adjacency fragment of 2 zones disconnected from main graph
- **note** [topology] `Gym+Holodeck1` — adjacency fragment of 2 zones disconnected from main graph
- **note** [topology] `Science1+Science2` — adjacency fragment of 2 zones disconnected from main graph
- **note** [topology] `Transprt1+Transprt2` — adjacency fragment of 2 zones disconnected from main graph

## expedition_cruise_300

- era=uninferred crew=0 zones=36 vol=20544 isolation=0
- removal ACH by class: berthing=7.43 machinery=12.0 mess=9.5 open_other=8.0 room_other=15.0 sanitary=19.2 weather_open=0.0
- no findings at this severity

## expedition_cruise_450

- era=uninferred crew=450 zones=47 vol=19359 isolation=0
- removal ACH by class: machinery=7.5 mess=4.62 open_other=4.64 room_other=3.18 sanitary=19.2 weather_open=0.0
- **note** [metrics] `expedition_cruise_450` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared

## fletcher_class_destroyer

- era=uninferred crew=0 zones=33 vol=2296 isolation=0
- removal ACH by class: berthing=4.4 machinery=21.5 magazine=8.0 medical=5.0 mess=6.5 open_other=6.67 sanitary=19.2
- no findings at this severity

## gordon_gunter_r338

- era=noaa_research crew=35 zones=35 vol=6552 isolation=1
- removal ACH by class: machinery=5.0 mess=4.0 open_other=3.45 ops_office=3.0 room_other=3.0 sanitary=19.1 weather_open=0.0
- zone-mode evidence: era_plausible=1, era_rule=32, sheet_read=2
- **note** [metrics] `gordon_gunter_r338` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared
- **note** [modes] `Galley` — declared mech_exhaust sits in HVAC_Mess_Galley realized as supply — intent vs field mismatch
- **note** [modes] `Genl_Mess` — declared mech_exhaust sits in HVAC_Mess_Galley realized as supply — intent vs field mismatch

## independence_cvl26

- era=usn_ww2 crew=1566 zones=46 vol=80401 isolation=4
- removal ACH by class: berthing=3.0 machinery=4.62 magazine=3.0 medical=4.0 mess=3.0 open_other=2.2 ops_office=3.0 room_other=3.0 sanitary=19.1 tank_hold=2.0 weather_open=1.1
- zone-mode evidence: era_plausible=3, era_rule=38, sheet_read=5
- adjacency components: [40, 2]
- berth over-assignment: Crew_Berthing_3D 785>490, Crew_Berthing_Main 274>90
- **flag** [metrics] `Crew_Berthing_3D` — 785 assigned to berth capacity 490 — exceeds any hot-bunk interpretation
- **flag** [metrics] `Crew_Berthing_Main` — 274 assigned to berth capacity 90 — exceeds any hot-bunk interpretation
- **note** [metrics] `independence_cvl26` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared
- **note** [modes] `Bomb_Assembly` — declared mech_exhaust sits in HVAC_Berthing realized as supply — intent vs field mismatch
- **note** [modes] `CPO_Mess` — declared mech_exhaust sits in HVAC_Berthing realized as supply — intent vs field mismatch
- **note** [modes] `Crew_Mess` — declared mech_exhaust sits in HVAC_Berthing realized as supply — intent vs field mismatch
- **note** [modes] `Galley` — declared mech_exhaust sits in HVAC_Berthing realized as supply — intent vs field mismatch
- **note** [modes] `Ordnance_Stores` — declared mech_exhaust sits in HVAC_Berthing realized as supply — intent vs field mismatch
- **note** [modes] `Wardroom` — declared mech_exhaust sits in HVAC_Accom realized as supply — intent vs field mismatch
- **note** [topology] `Hold_Tanks+Stern_Hold` — adjacency fragment of 2 zones disconnected from main graph
- **note** [topology] `Stern_Stores_2P` — open_other zone declares no passage (walk-island gap or closed compartment)

## legend_class_nsc

- era=uninferred crew=0 zones=27 vol=2859 isolation=0
- removal ACH by class: berthing=8.0 machinery=20.0 medical=12.0 mess=10.33 open_other=8.0 sanitary=19.2 weather_open=8.0
- no findings at this severity

## mega_cruise_5000

- era=uninferred crew=7000 zones=192 vol=403555 isolation=0
- removal ACH by class: machinery=10.0 medical=6.0 mess=5.27 open_other=3.97 room_other=2.97 sanitary=19.2 weather_open=0.0
- **note** [metrics] `mega_cruise_5000` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared

## messy_cruise_500

- era=uninferred crew=0 zones=130 vol=461595 isolation=0
- removal ACH by class: berthing=6.26 machinery=20.0 medical=12.0 mess=10.54 open_other=7.71 room_other=12.0 sanitary=19.2 weather_open=0.0
- no findings at this severity

## midway_cv41

- era=usn_ww2 crew=4712 zones=65 vol=198768 isolation=4
- removal ACH by class: berthing=3.0 machinery=5.0 magazine=2.0 medical=4.0 mess=3.0 open_other=1.62 ops_office=3.0 room_other=3.0 sanitary=19.1 tank_hold=2.0 weather_open=1.75
- zone-mode evidence: era_plausible=2, era_rule=56, sheet_read=7
- berth over-assignment: Officers_Country_02 430>80, CPO_3D 229>100, Crew_Berthing_3D_Mid 2441>600, Crew_Berthing_2D 392>350, Crew_Berthing_3D_Aft 420>350, Crew_Berthing_3D_Fwd 800>600
- **flag** [metrics] `CPO_3D` — 229 assigned to berth capacity 100 — exceeds any hot-bunk interpretation
- **flag** [metrics] `Crew_Berthing_3D_Mid` — 2441 assigned to berth capacity 600 — exceeds any hot-bunk interpretation
- **flag** [metrics] `Officers_Country_02` — 430 assigned to berth capacity 80 — exceeds any hot-bunk interpretation
- **flag** [metrics] `midway_cv41` — manifest assigns 4712 to berth zones capped at 2080 (>1.5x)
- **note** [metrics] `midway_cv41` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared
- **note** [modes] `Crew_Mess_2D` — declared mech_exhaust sits in HVAC_Berthing realized as supply — intent vs field mismatch
- **note** [modes] `Fwd_Messing_2D` — declared mech_exhaust sits in HVAC_Berthing realized as supply — intent vs field mismatch
- **note** [modes] `Hangar_Fwd` — declared mech_exhaust sits in VENT_Hangar realized as supply — intent vs field mismatch
- **note** [modes] `Magazine_1P_Fwd` — declared mech_exhaust sits in VENT_Tanks realized as supply — intent vs field mismatch
- **note** [modes] `Wardroom_02` — declared mech_exhaust sits in HVAC_Accom realized as supply — intent vs field mismatch
- **note** [modes] `Wardroom_2D` — declared mech_exhaust sits in HVAC_Berthing realized as supply — intent vs field mismatch

## passumpsic_ao106

- era=usn_ww2 crew=280 zones=27 vol=22141 isolation=2
- removal ACH by class: berthing=3.0 machinery=5.0 magazine=5.0 medical=3.0 mess=3.0 open_other=4.0 ops_office=3.0 sanitary=19.1 tank_hold=4.0 weather_open=0.6
- zone-mode evidence: era_plausible=2, era_rule=22, sheet_read=3
- adjacency components: [18, 7]
- berth over-assignment: CPO_Quarters 19>14, Crew_Qtrs_Fwd 165>60
- **flag** [metrics] `Crew_Qtrs_Fwd` — 165 assigned to berth capacity 60 — exceeds any hot-bunk interpretation
- **flag** [metrics] `passumpsic_ao106` — manifest assigns 280 to berth zones capped at 174 (>1.5x)
- **note** [metrics] `passumpsic_ao106` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared
- **note** [modes] `Galley` — declared mech_exhaust sits in HVAC_Berthing realized as supply — intent vs field mismatch
- **note** [modes] `Wardroom` — declared mech_exhaust sits in HVAC_Accom realized as supply — intent vs field mismatch
- **note** [topology] `Aft_Open_Deck+CPO_Quarters+Galley+Mess_Hall` — adjacency fragment of 7 zones disconnected from main graph
- **note** [topology] `Fwd_Peak_Tanks` — tank_hold zone declares no passage (walk-island gap or closed compartment)

## pce_874

- era=usn_ww2 crew=99 zones=20 vol=2241 isolation=1
- removal ACH by class: berthing=3.0 machinery=5.0 medical=3.0 mess=3.0 open_other=3.5 sanitary=19.1 tank_hold=5.0 weather_open=0.0
- zone-mode evidence: era_plausible=1, era_rule=16, sheet_read=3
- berth over-assignment: CPO_Quarters 13>10, Crew_Quarters 78>55
- **note** [metrics] `pce_874` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared
- **note** [modes] `Galley` — declared mech_exhaust sits in HVAC_Accom realized as supply — intent vs field mismatch
- **note** [modes] `Wardroom` — declared mech_exhaust sits in HVAC_Accom realized as supply — intent vs field mismatch

## raven_am55

- era=usn_ww2 crew=105 zones=21 vol=3547 isolation=1
- removal ACH by class: berthing=3.0 machinery=5.0 magazine=5.0 medical=3.0 mess=3.0 open_other=1.5 sanitary=19.1 weather_open=0.0
- zone-mode evidence: era_plausible=1, era_rule=17, sheet_read=3
- berth over-assignment: CPO_Quarters 13>12, Crew_Quarters 84>60
- **flag** [topology] `Sick_Bay` — medical zone declares no passage (walk-island gap or closed compartment)
- **note** [flow_closure] `Sick_Bay` — 1 zones ventilated only by their group — HVAC casualty leaves them sealed
- **note** [metrics] `raven_am55` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared
- **note** [modes] `Galley` — declared mech_exhaust sits in HVAC_Accom realized as supply — intent vs field mismatch
- **note** [modes] `Wardroom` — declared mech_exhaust sits in HVAC_Accom realized as supply — intent vs field mismatch
- **note** [topology] `Bosn_Gear` — open_other zone declares no passage (walk-island gap or closed compartment)
- **note** [topology] `Foc_Deck_Fwd` — weather_open zone declares no passage (walk-island gap or closed compartment)
- **note** [topology] `Fwd_Stores` — open_other zone declares no passage (walk-island gap or closed compartment)

## ruchamkin_apd89

- era=usn_ww2 crew=375 zones=32 vol=7822 isolation=2
- removal ACH by class: berthing=3.0 machinery=5.0 magazine=5.0 medical=3.0 mess=3.0 open_other=4.0 ops_office=3.0 sanitary=19.1 tank_hold=5.0 weather_open=0.6
- zone-mode evidence: era_plausible=2, era_rule=27, sheet_read=3
- adjacency components: [29, 2]
- berth over-assignment: Officers_Qtrs 15>10, Crew_Berthing_Mid 42>40, Crew_Berthing_1P 48>40, Crew_Berthing_Aft 90>30, Troop_Berthing_Fwd 162>70
- **flag** [metrics] `Crew_Berthing_Aft` — 90 assigned to berth capacity 30 — exceeds any hot-bunk interpretation
- **flag** [metrics] `Troop_Berthing_Fwd` — 162 assigned to berth capacity 70 — exceeds any hot-bunk interpretation
- **flag** [metrics] `ruchamkin_apd89` — nominal_complement.crews 213 != manifest crew sum 195
- **flag** [metrics] `ruchamkin_apd89` — manifest assigns 357 to berth zones capped at 190 (>1.5x)
- **note** [metrics] `ruchamkin_apd89` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared
- **note** [modes] `Galley` — declared mech_exhaust sits in HVAC_Berthing realized as supply — intent vs field mismatch
- **note** [modes] `Troop_Mess_Below` — declared mech_exhaust sits in HVAC_Berthing realized as supply — intent vs field mismatch
- **note** [modes] `Wardroom` — declared mech_exhaust sits in HVAC_Accom realized as supply — intent vs field mismatch
- **note** [topology] `Chain_Locker+Fwd_Hold` — adjacency fragment of 2 zones disconnected from main graph

## san_antonio_class_lpd

- era=uninferred crew=0 zones=29 vol=16075 isolation=0
- removal ACH by class: berthing=7.5 machinery=20.0 medical=12.0 mess=9.5 open_other=8.83 sanitary=19.2 weather_open=8.0
- no findings at this severity

## spirit_cruise_3000

- era=uninferred crew=3000 zones=115 vol=84704 isolation=0
- removal ACH by class: machinery=7.5 mess=4.65 open_other=3.91 room_other=3.1 sanitary=19.2 weather_open=0.0
- adjacency components: [66, 21]
- **note** [metrics] `spirit_cruise_3000` — top-level hvac_duty=0.5 halves/scales every group ACH vs declared
- **note** [topology] `CC_D1_A+CC_D1_F+CC_D1_M+CC_D2_A` — adjacency fragment of 21 zones disconnected from main graph
