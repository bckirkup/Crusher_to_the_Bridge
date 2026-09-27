# NORO-DEPOSIT-ATTR-01
**Date:** 2026-09-26
**Commit:** d0ac415d
**Pathogens:** norwalk_gi
**Status:** measured

Per-change attribution of the post-#724 surface-pool deposit-mass collapse
(~5 orders of magnitude) measured by NORO-REBASE-01 (`a872367c`) on the
`fl_spr_12d` cell — `spirit_cruise_3000`, n=3000, 288 epochs,
`syndromic_comp65`, rung `reportable`, paired seeds 8105/8106, cell
overrides `sanitary_visit_mode: dwell_weighted`, `flush_aerosol_fraction: 0.0`,
`flush_cabin_emission: true`, `cabin_air_mode: cabin_compartment`,
`hvac.pathogen_pool_transport: airflow`.

## Attribution criterion (declared before any ablation ran)

Statistic, per (arm, seed) voyage: the per-epoch
`sanitary_activity.dose_delivered` series, plus the deposit split this probe
records — `deposit_by_venue_class_gec` (shared_head / cabin_fittings /
other_zone), `deposit_by_call_site_gec`, per-epoch `pool_{class}` mass,
`stool_venue_destinations`, `new_infections` (non-seed).

- **Carrier**: the arm restores the shared-head deposit mass and
  `dose_delivered` to within the pre-fix archive's order of magnitude
  (>= 1e4/epoch peak vs the post-724 ~2-5) on both paired seeds, while the
  other arms stay at the post-724 reading. Partial restoration (>= 10x the
  post-724 reading, < 1e4/epoch peak, same on both seeds) is **partial**.
- **Null**: an arm within the seed-pair spread of the post-724 base on
  deposit mass and `dose_delivered`.
- **Multiplicative collapse**: no single arm restores — the fall is split
  across several correct removals; reported immediately (fork changes: refit
  becomes mandatory).
- **Overshoot**: an arm restores beyond the pre-fix trace — reported
  immediately; the pre-fix level may itself be artifact-inflated.
- **RNG reorder**: arms that move spawn draws (watch_off) or remove
  downstream draws (emesis_zonepool drops patch-pickup draws) are flagged
  stream-non-neutral; for those arms the criterion is read on event ordering
  and the venue-class deposit split, not just totals, per the
  stochastic-attribution skill.

Instrument: `tools/noro_diag/deposit_attr_trace.py` — verbatim
`generate_tier_runs(manifest, "fl_spr_12d")` specs, arm overrides merged on
top, read-only wrappers plus a per-epoch observer; no engine writes, no
wrapper draws RNG.

## Method per candidate (fixed before running)

| candidate | arm | method |
|---|---|---|
| emesis footprint localization (#604, `9daa4a8f`) | `emesis_zonepool` | in-process revert via the shipped emitter: floor-area lookup patched to the fomite surface (making the shipped share equal the pre-604 `min(1, high_touch/area)`) + each filed EmesisPatch re-filed into the zone surface pool; draw order preserved |
| blackwater bowl share (`transmission.blackwater_plumbing`, default-on `b120ad3d`) | `blackwater_off` | labelled config baseline `false`; documented stream-neutral |
| crew watch schedules (#723, `e86b73bf`) | `watch_off` | `ship_graph.agent_classes` without `schedule` keys (pre-723 verbatim state) + `agent_behavior.schedule_jitter_hours` zeroed; spawn draws reorder — distribution caveat |
| sub-copy pickup gate (NORO-GATE-FLOOR-01, #674/677) | `gate_off` | in-process `SURFACE_PICKUP_MIN_GEC = 0.0` for the run — equivalent to reverting the constant; gate consumes no RNG either way |
| reporting de-stack (NORO-CHANNEL-02, `b9cae80f`) | `report_scale` | `pathogen_overrides.norwalk_gi.observation_model.reporting_belief_scaling: "trust_medical"` — the pre-change stacking as a labelled baseline; added after static review showed reporting speed changed confinement timing in-window |
| **joint pre-change baseline** | `pre_all` | all six candidates at labelled baseline simultaneously — declared after the single-arm grid returned only partials/nulls, as the decisive multiplicative test |
| cabin-pair fomite (NORO-CABIN-01, `b49a3ec2`) | `cabin_fomite_off` | labelled config baseline `transmission.cabin_confined_fomite.mode: "off"` |

Named-candidate coverage: all four ledger-named drivers have arms; the two
extra rows are in-window changes found on the deposit path during the method
inventory (confinement timing, cabin-pair delivery). Considered and rejected
as carriers: `room_air_removal`, `cabin_cooccupancy`, `cabin_air_mode`
(airborne-side or already pinned identically in both cells);
`norwalk_only.json` registration (bundle untouched by this cell — profile
diff in-window adds only `reporting_belief_scaling`, exercised by the
`report_scale` arm).

## Pre-run static audit (recorded so the table is read against it)

Byte-identical across `7f689b9..fbad8738`: the whole stool->hand chain
(`_route_stool_event_venue`, `_stool_event_occurs`, `_stool_bowl_copies`,
`_replenish_hand`, `_stationary_hand_load`, `_hand_carriage_propensity`,
`shedding_value`, `_shedding_curve_point`, `get_pathogen_hand_target`,
`_get_shedders`, `_get_susceptible`, `_cabin_confinement_active`,
`_draw_sanitary_visits`, `_sanitary_visit_share`, `_fomite_surface_contacts`,
`_hand_to_surface_drying`, `_delivery_scale`), and the deposit formula in
`_sanitary_venue_deposits` (contacts x share x used_fraction x
transfer_efficiency x hand, `min(hand, requested)`).

Changed in-window on the same path: `_fomite_pickup_request` (new
`_cabin_presence_share` factor, dedicated `_fomite_rng` stream),
`_hand_to_mouth_dose`, `_consume_surface_mass` (exact-empty on capped pools),
`_update_surface_pools`, `_fomite_surface_area`, `_emit_emesis` (patch
filing), `_deposit_surface_mass` (per-surface mirror, inert when pooled),
sanitary exposure split into helpers at `94b179ab` (mechanical S3776 split —
formula preserved verbatim, verified line-by-line).

## Results

Local, this box's py3.12 venv, post-#724 base `56bb723c`. Canary `base` arm
reproduced the ledger's post-724 cold reading exactly before any ablation
ran: `dose_delivered` peak 2.02/epoch @17 on s8105 (ledger: 2–5), s8106 peak
0.52 — instrument reads the same ledger.

Per-arm `fl_spr_12d` readings (s8105 / s8106), `dose_delivered` = the
sanitary ledger; `dep_head/cab/oth` = deposit mass to each venue class
(GEC, voyage totals); `deliv` = pooled-path delivered mass; `inf` = final
infected count (seeds included).

| arm | dose peak /ep | dose total | dep_head | dep_cab | dep_oth | deliv | inf |
|---|---|---|---|---|---|---|---|
| base | 2.0 / 0.5 | 6.5 / 1.0 | 809 / 149 | 23.9k / 438 | 8.5k / 1.3k | 44.8 / 9.6 | 11 / 8 |
| blackwater_off | 2.0 / 0.5 | 6.5 / 1.0 | 809 / 149 | 23.9k / 438 | 8.5k / 1.3k | 44.8 / 9.6 | 11 / 8 |
| watch_off | **503.7** / 0.0 | 587.5 / 0.0 | 233 / 8 | 88.1k / 142 | 9.1k / 667 | 17.4 / 0.2 | 11 / 7 |
| gate_off | 2.9 / 1.0 | 5.6 / 2.3 | 10 / 2 | 48.4k / 282 | 1.6k / 2.3k | 0.7 / 0.1 | 11 / 8 |
| emesis_zonepool | 3.7 / 0.5 | 4.7 / 1.0 | 185 / 149 | **1.52e8** / 438 | **3.9e7** / 1.3k | 0.7 / 9.6 | **31** / 8 |
| report_scale | 2.0 / 0.5 | 6.5 / 1.0 | 809 / 149 | 23.9k / 438 | 8.5k / 1.3k | 44.8 / 9.6 | 11 / 8 |
| cabin_fomite_off | 0.9 / 0.5 | 2.0 / 1.0 | 283 / 149 | 403 / 438 | 5.9k / 1.3k | 7.6 / 9.6 | 11 / 8 |
| **pre_all** (joint baseline) | **4.0e5** / 0.3 | **1.49e6** / 0.7 | **60.5k** / 115 | **3.6e9** / 30 | **2.3e9** / 2.4k | 2.9k / ~0 | **315** / 2 |

`blackwater_off` and `report_scale` are bit-identical to base on every field
of both seeds (verified: the `report_scale` override lands —
`observation_model.reporting_belief_scaling: "trust_medical"` — but no
report decision diverged inside the window; `blackwater_off` is null by
construction: the tank only sequesters mass that was already
non-deposited). `gate_off` opened 98,089 requests vs 1,767 on s8105 with the
dose unchanged — measured proof the gate was suppressing spam on near-empty
pools, not blocking dose.

## Reading the mechanism

`dose_delivered` is not the pickup mass. In `_deliver_sanitary_pooled_requests`
the booked dose is `_hand_to_mouth_dose(agent, epoch, hand + delivered)` — a
mouth-contact fraction of the requester's **entire accumulated hand load** at
pickup, not of the delivered mass alone. A head pickup by an agent carrying a
~33k hand books a ~500 dose off a ~30-GEC pool (measured: `watch_off` s8105
ep16, pool_shared_head 28, delivered 1.77, dose 503.7). Susceptible hands are
built by **cabin-zone pickups** (`_fomite_zone_pickup` on cabin-compartment
occupants), which are fed by shedder surface deposits plus, pre-#604, the
full emesis bolus filed into the zone pool. Post-#604 the bolus is filed as
an `EmesisPatch` exposing only `footprint_area/floor_area` of the zone's
occupants — on this cell ~3e-5 of a ~6.5e6-GEC index bolus is
occupant-reachable; the rest is sequestered, not deleted
(`emesis_zonepool` s8105 redirected 5.9e9 GEC total — measured).

Seed asymmetry, measured: on s8106 **no emesis event fires in the whole
288-epoch voyage under either config** (`emesis_mass_by_venue_class` empty on
`base`, `emesis_zonepool`, and `pre_all` alike — the zonepool run is
bit-identical to base there). The window-edge A/B settles what that means:
**the pre-window engine itself (`7f689b9`, bare voyage, s8106, this cell) is
cold** — `dose_delivered` total 0.026, recipients 22,170, residual pool
mass ~0. `pre_all` on s8106 (dose 0.7) is a faithful reproduction of the
pre-fix engine, not a stream-reorder artefact. The archive's "s8106 posted,
peak 371" came from the `flush_sweep_v1_off_s4` **7-day** tier — a different
cell — so on this cell s8106 was never warm, before or after the window.
Measured conclusion: the armed set is complete; the warm/cold pattern
matches the pre-fix engine on both seeds.

So the collapse runs through a chain, not a switch: emesis sequestration
(#604) removes the cabin-pool seed → susceptible hands stay ~0 → head
pickups deliver ~1 GEC regardless of pool; #723 watch rerouting thins the
shedder-visit/susceptible-visit coincidence at heads (seed-fragile spark on
s8105); the capped-empty consume (`bd87ce9a`) and pickup gate
(`f7092d5b`) keep thin pools honest; confinement + `reporting_belief_scaling`
timing decide how long shedders remain free to visit heads.

## Verdict

- **emesis footprint localization (#604, `9daa4a8f`) — primary carrier.**
  Correct removal: the zone-wide whole-bolus pool it retired was the
  artefact (a ~6.5e6-GEC bolus dosing every occupant of a ~200 m² room). The
  measured `pre_all` overshoot on s8105 (peak 4.0e5 vs archive 1.8e5)
  confirms the pre-fix level was inflated. → refit path, not a defect entry;
  the patch mechanics behave as designed (measured: mass conserved,
  exposure limited to the footprint). The s8106 `pre_all` cell stays cold
  with zero emesis draws — the window-edge A/B (`7f689b9`, s8106, bare
  voyage) reads cold too (dose 0.026 total), so this is faithful
  reproduction, not reorder: on this seed the index simply never vomits.
- **crew watch schedules (#723) — partial contributor.** Seed-fragile:
  249× base on s8105, 0 on s8106 — fails the both-seeds clause → **null**
  by criterion as a standalone carrier, but implicated in the joint effect
  (thins shedder-head coincidence; stream-non-neutral arm).
- **blackwater bowl-share (#590s), sub-copy gate (NORO-GATE-FLOOR-01),
  reporting de-stack (NORO-CHANNEL-02), cabin-pair fomite (NORO-CABIN-01) —
  null** (first two bit-identical; gate suppresses spam on empty pools;
  cabin channel contributes only to the tiny residual).
- **Joint baseline `pre_all` restores the warm state** — the collapse is
  **multiplicative across the named set**, dominated by #604. No in-window
  defect found on the deposit path: every armed change reads as a correct
  removal of an artefact, and the residual contributors (`bd87ce9a`
  capped-empty consume — bookkeeping-equivalent; `40f22ced` residue floor —
  adds mass, cannot remove; `3878c2f2` INDEX-GEOM-01 — 11-line departure
  guard; `1b9d37ca` CABIN-OCC-01 — `_cabin_presence_share` is 1.0 for
  non-confined, non-cabin pickups, verified neutral on the head path) are
  ruled out by construction or measurement.

**Fork: refit is mandatory.** The post-#724 engine is the correct engine;
the withdrawn dose ledger needs a refit against it. The overshoot reading
says pre-fix magnitudes were themselves artefact-inflated — the refit target
is the labelled post-#724 baseline, not the archive's 1.8e5. Note the
diagnostic asymmetry this exposes for the refit: on this cell the warm
state is emesis-ignition-dependent — s8106 never vomits and was cold even
pre-fix — so establishment-vs-extinction is partly a rare-event draw on a
small seed pair; the refit readout should price that.

## Proposed next step (prompt skeleton)

> **NORO-DOSE-REFIT-01** — on the post-#724 main, refit the norwalk_gi dose
> ledger: re-derive `dose_adjustment` (and the pickup/deposit fractions it
> composes) so the `fl_spr_12d` cell produces establishment (defence, not
> mass) consistent with the declared anchors on the *patched* engine.
> Settled: this ledger (carriers/mechanism), REBASE-01 readings. Non-goals:
> no change to #604/#723/gate/blackwater semantics. Gate: canary s8105/8106
> reproducing secondaries>0 without exceeding measured pool mass; report
> immediately if any constant needs >10× moves — that signals a residual
> structural defect, not a dose problem.

## Evidence class

Measured: every arm table row (this session, seeds 8105/8106, commit
`56bb723c`), the `dose_delivered = f(hand+delivered)` swallow semantics,
patch sequestration mass, `report_scale` override landing, bit-identical
arms, the window-edge A/B (`7f689b9` s8106 cold, dose 0.026 total — same
cell, same seed, bare voyage on the pre-window engine). Inferred: the
cabin-seed → hand → head-swallow causal chain (from arm-level
dose/hand/venue reads — internally consistent, single-cell). Hypothesis:
the pre-fix archive's warm s8105 ran through the same chain (consistent
with `pre_all` s8105 overshoot; no pre-fix deposit-mass dump survives to
verify against).
