# PLATFORM-FIDELITY-01b addendum — DP-only protocol correction

Status: pre-registered amendment, frozen before any 01b cell runs —
2026-11-08. Amends `docs/covid/covid_platform_fidelity_prereg_v1.md` for the
Diamond Princess pair only. Authorized scope (Edison review, relayed by the
owner): "Prepare the PLATFORM-FIDELITY-01b addendum with a functionally
justified union of essential-workplace IDs, frozen Θ and seeds, explicit
preflight witnesses, and a corrected execution count. Preserve the original
DP result as confounded. Reuse the proxy cells if behavioral equivalence is
established; otherwise rerun both DP arms. Leave GM untouched. Present the
addendum and preflight evidence for approval before submitting the corrective
runs."

**No 01b Batch job is submitted by this document.** Execution is blocked on
owner approval of this addendum.

## 1. The defect (measured in PF-01, not hypothesized)

The frozen PF-01 DP protocols file
(`data/config/protocols_covid_pf_dp.json`, SOP-017-MESSBOX) declares 11
`exempt_work_zones`, all `mega_cruise_5000` zone IDs. Of those, the
event-faithful `diamond_princess` hull carries exactly one (`Bridge`). The
engine intersects `exempt_classes` with `exempt_work_zones` by exact zone-ID
string (`orchestrator_epoch._order_exempt_ids`), and crew work zones are
random draws from each hull's free/dining zone pool
(`infection_dynamics_bridge._resolve_class_zones`; the scenario's
`_agent_classes` declares no `duty_zone`). The PF-01 DP contrast therefore
changed the intervention as well as the platform.

Measured on the PF-01 cell payloads (20 seeds/arm, `crew_window` witness):

| arm | working crew at quarantine activation (per seed range) | mean |
|---|---|---|
| proxy (`mega_cruise_5000`) | 295–368 of 1045 | 334.8 |
| dedicated (`diamond_princess`) | 10–21 of 1045 | 16.2 |

All proxy exemptions posted across the 11 declared zones; all dedicated
exemptions posted to `Bridge`. `confined_at_activation` was 3379 (proxy) vs
3693 (dedicated) — the dedicated arm quarantined ~318 more crew than the
proxy arm under the same nominal protocol. GM is unaffected: the GM
protocols file declares no `exempt_work_zones`, and all 160 GM cells show
~95/95 crew working at activation on both hulls.

Consequence: the PF-01 DP row mixes hull geometry with a large difference in
effective quarantine scope. It cannot answer the intended hull-fidelity
question. The original DP cells and readout row are **preserved and marked
confounded/superseded for hull-fidelity inference**; they remain evidence of
a zone-name-dependent intervention defect. They are not deleted and not
re-scored.

## 2. The repair: function-matched union of essential-workplace IDs

Essential workplaces are defined by **function**, then mapped to each hull's
native zone IDs. The hulls' real IDs are kept; nothing is renamed to
accommodate the protocol.

| function | proxy `mega_cruise_5000` IDs | dedicated `diamond_princess` IDs | intentional non-resolutions |
|---|---|---|---|
| galley (crew service) | `Main_Galley_Aft`, `SpecGalley`, `BuffetGal_U` | `MainGalley` | DP has one crew-only galley (`dining_service_type: galley`, "crew-only service"); the proxy's three galleys include passenger venues, kept because they were in the frozen PF-01 policy |
| engineering / waste | `Engine_Room_Aft`, `EngControl`, `WasteTreat` | `Engine_Room` | DP declares no engine-control or waste-treatment zone; engineering concentrates in `Engine_Room` (diesel-electric plant, Deck 0). No zone is invented |
| bridge | `Bridge` | `Bridge` | shared ID, already in the PF-01 list |
| stores | `Central_Stores` | `Stores` | — |
| laundry (crew industrial) | `Laundry_Main` | `Laundry` | DP `SelfLaundry` is a passenger self-service laundromat and is **excluded** — it is not a crew essential workplace, matching the proxy policy which exempts `Laundry_Main` only |
| crew-mess operations | `Crew_Mess_Main`, `CrewMess_Fwd` | `CrewMess`, `CrewMessOff` | `CrewMessOff` is the officers' mess (`dining_service_type: crew_mess`) — crew meal operations under the boxed-service protocol, so included |

Union list (17 IDs) in `data/config/protocols_covid_pf_dp_01b.json`:
the 11 PF-01 IDs plus `MainGalley`, `Engine_Room`, `Stores`, `Laundry`,
`CrewMess`, `CrewMessOff`. Everything else in the protocols file is
byte-identical to PF-01 (same protocol id `SOP-017-MESSBOX`, same modifiers
otherwise, same boxed `crew_meal_service`).

The list is **not** adjusted to reproduce the proxy's ~332 working crew.
Different layouts and postings legitimately produce different realized
counts; the requirement is the same exemption policy, not identical
staffing (Edison condition 1).

## 3. Preflight evidence (local, init-only probes — no Batch submission)

Probes build the exact PF-01 DP cell specs (`prepare_cell_run_spec` +
`base_overrides` + `protocols_path`) and call `build_fit_sim` without running
epochs, then count crew exempt under the order semantics for the 20 frozen
seeds (20200205–20200224). Init probes measure the exempt set at boarding;
the PF-01 witness is read at activation (epoch 384) and excludes crew
already isolated before activation, which is why probe counts can exceed
the witness by 0–1 on some seeds.

### 3.1 Which IDs resolve on each hull

- `mega_cruise_5000` (192 zones): all 11 PF-01 IDs resolve; **none** of the 6
  DP-native IDs (`MainGalley`, `Engine_Room`, `Stores`, `Laundry`,
  `CrewMess`, `CrewMessOff`) exist on this hull — verified against
  `data/platforms/mega_cruise_5000/spatial_layout.json`.
- `diamond_princess` (159 zones): `Bridge` (PF-01) plus the 6 DP-native IDs
  resolve; the other 10 PF-01 IDs do not exist on this hull — verified
  against `data/platforms/diamond_princess/spatial_layout.json`.
- `greg_mortimer` / `expedition_cruise_450`: not used by 01b (GM untouched);
  of the union, only `Bridge` exists there, and the GM protocols file
  declares no `exempt_work_zones` regardless.

### 3.2 Proxy arm: no new effective exemptions (Edison condition 2)

Controlled comparison under identical probe semantics, per seed:

- original 11-ID list vs union 17-ID list on `mega_cruise_5000`, seeds
  20200205–20200224: **identical exempt counts on every one of the 20 seeds**
  (no mismatches). The union is inert on the proxy by construction (the 6
  added IDs are absent from the hull) and confirmed empirically.
- Proxy exempt counts under the union (per seed): 295–368, mean 335.1 —
  matching the PF-01 witness range (295–368, mean 334.8). The 0–1 seed-level
  differences vs the activation-epoch witness are the pre-activation
  isolation effect described above, present identically for both lists.

**Baseline equivalence is established.** The 20 PF-01 proxy cells
(`campaign/covid_platform_fidelity_01/`, block `dp_t7e6_proxy`) are reused as
the 01b baseline; there is no scientific reason to repeat an unchanged
baseline for a newer timestamp.

### 3.3 Dedicated arm under the union (same policy, hull-native postings)

Exempt crew at boarding, per seed (20 seeds):

| seed | proxy exempt | dedicated exempt |
|---|---|---|
| 20200205 | 333 | 120 |
| 20200206 | 332 | 116 |
| 20200207 | 312 | 121 |
| 20200208 | 337 | 116 |
| 20200209 | 359 | 121 |
| 20200210 | 361 | 109 |
| 20200211 | 343 | 121 |
| 20200212 | 331 | 107 |
| 20200213 | 368 | 102 |
| 20200214 | 295 | 109 |
| 20200215 | 323 | 118 |
| 20200216 | 333 | 105 |
| 20200217 | 343 | 111 |
| 20200218 | 356 | 98 |
| 20200219 | 320 | 132 |
| 20200220 | 334 | 115 |
| 20200221 | 313 | 107 |
| 20200222 | 339 | 113 |
| 20200223 | 333 | 110 |
| 20200224 | 336 | 135 |

Dedicated range 98–135, mean 114.3 (vs 10–21, mean 16.2 under the defective
PF-01 list). By exempt function over the 20 seeds (dedicated): crew-mess
638, laundry 343, galley 332, engineering 331, bridge 323, stores 319; by
zone: `CrewMess` 321 + `CrewMessOff` 317, `Laundry` 343, `MainGalley` 332,
`Engine_Room` 331, `Bridge` 323, `Stores` 319 — every exemption posts to one
of the 7 hull-native essential zones, none to a non-existent ID.

The dedicated realized share (~11% of crew) differs from the proxy's (~32%)
because each hull's generic crew-posting draw distributes crew across that
hull's own free/dining pool; both hulls now apply the same policy (exempt =
crew posted to essential workplaces). This is hull fidelity, not a protocol
mismatch, and the list was not tuned toward any count.

### 3.4 End-to-end proxy-equivalence cell

One full local DP proxy cell (seed 20200205, Θ = 7.9e6, full declared
voyage, 01b protocols file) was run through the PF-01 cell worker and
diffed leaf-by-leaf against the PF-01 cell payload for the same seed
(`/tmp/pf_full/dp_t7e6_proxy/cell_20200205.json` vs the 01b run):

- 436 leaf fields compared; **19 differ, all metadata echoes**: the echoed
  `exempt_work_zones` declaration (17 vs 11 IDs), `design_id`,
  `platform_fidelity.protocols_path`, and the `design_sha256` /
  `protocols_sha256` / `run_spec_canonical_sha256` input hashes (the run-spec
  hash moves only because `protocols_path` is embedded in the spec).
- **Every epidemiological field is bit-identical**: `recorded_onsets`,
  takeoff, asymptomatic share, `quarantine_witness` (activation epoch 384,
  confined_at_activation 3379), `crew_window.at_activation`
  (working_crew_count 332, by-posted-zone histogram over the 11 proxy IDs),
  boxed `crew_meal_service` epochs, fired protocol ids
  [`SOP-017-MESSBOX`], and the `close_zones` audit flag.

The proxy arm's resolved behavior is demonstrably unchanged under the
union list, end to end, not only at init. Baseline reuse is justified.

## 4. Frozen design and corrected execution count

- Scenario `diamond_princess_2020`, voyage declared; Θ = 7.9e6 (the DP
  believability operating point), infection_age_days 6.8, imports 1,
  sanitary_visit_mode dwell_weighted — all frozen from PF-01.
- Seeds 20200205–20200224 (20), same seed list both arms (CRN pairing).
- Arm grammar unchanged: arm 0 `proxy_mega_cruise` baseline with empty
  overrides; arm 1 `dedicated_diamond_princess` with
  `platform_id: diamond_princess`.
- Design: `picard_framework/runs/covid_platform_fidelity_01b_dp_design.json`
  (enumerates 40 cells; `cells_note` records the reuse). Protocols:
  `data/config/protocols_covid_pf_dp_01b.json` (new file, new SHA-256; the
  PF-01 file is untouched so PF-01 cells remain reproducible).
- **Execution count: 20 new Batch executions** (the dedicated block only),
  plus the 20 reused PF-01 proxy cells = the committed DP design's 40
  executions total. If the reviewer rejects baseline equivalence, both arms
  rerun: 40 new executions. No replication increase is proposed; old and new
  executions are not counted together as 80.
- GM: untouched. No GM cells, no GM protocols change, no GM readout change
  beyond the statistical-wording corrections below.

## 5. Preflight witnesses for the 20 dedicated cells

Every 01b cell payload carries the PF-01 echo set plus these witnesses,
verified at readout before any interpretation:

1. `crew_window.at_activation.working_crew_count` and
   `working_crew_by_posted_zone`: working crew must be in the 98–135 band
   observed at boarding (allowing the 0–1 pre-activation isolation effect)
   and every posted zone must be one of the 7 hull-native essential IDs
   (`Bridge`, `MainGalley`, `Engine_Room`, `Stores`, `Laundry`, `CrewMess`,
   `CrewMessOff`). A witness outside this band is a FAILED COMPARISON,
   reported, never deleted.
2. `crew_window.crew_meal_service` / boxed service deliveries: boxed mode
   active (PF-01 showed `active_epochs` 360 on both DP arms); the boxed
   service diverts crew-mess placements hull-natively and is unaffected by
   the zone-ID list.
3. `platform_fidelity.fired_protocol_ids` == [`SOP-017-MESSBOX`] and
   `close_zones_fired_flag` false on every cell.
4. Input hashes per cell: `protocols_sha256` must equal the 01b file's hash;
   platform, scenario, pathogen, and agent-profile hashes must equal the
   PF-01 values (only the protocols file changed).
5. Technical-failure rate ≤ 10%; any `close_zones` firing is a FAILED
   COMPARISON per the frozen criteria.

## 6. Statistical corrections binding on the revised readout (Edison
condition 3)

The revised DP readout (01b) must:

- label all q05–q95 ranges as **seedwise spreads, not confidence
  intervals**;
- report **unconditional onset burden** (median and total `recorded_onsets`
  across all 20 seeds regardless of the takeoff gate) and **P(takeoff)**
  alongside the frozen takeoff-conditional endpoint — the PF-01 DP paired
  endpoint used only the 6 both-takeoff seeds and must not be quoted
  without its n;
- not conclude "small relative to seed noise" or platform equivalence from
  an interval crossing zero;
- preserve the PF-01 DP row as confounded/superseded, cross-referenced here.

The same wording care applies to the GM rows already published: "unaffected
by the DP protocol bug" does not mean "geometry shown not to matter."

## 7. What does not change

No biological parameter, no Θ, no seed, no scenario split, no hull geometry,
no GM cell, no canonical-platform selection. The only changes are the DP
protocols file's `exempt_work_zones` (function-matched union) and the DP
dedicated arm's rerun. Hull IDs are kept real; no hull is renamed.
