# NORO-TOUCH-SHARE-02
**Date:** 2026-09-24
**Commit:** 56eaa0e
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 29bbd393140d32b85d93ece9c4b07039b6261bf0

A two-seed epoch-lockstep probe of the `per_surface + areal` (A) versus
`per_surface + declared` (D) fomite arms measured in `NORO-TOUCH-SHARE-01`,
answering one question: **at the first epoch where the two arms' RNG
streams differ, what caused the divergence?** §§0–3 are frozen before either
seed runs; §4 and §7 are filled only from the probe output (before and
after the in-session residue floor, §6); §5 and §8 state what is inferred
and what remains hypothesis. Every mass or dose-like quantity
quoted here is a paired, relative witness read from two arms of the same
seed — never a dose result (`../norovirus/norovirus_open_ledger.md` §1).
Nothing is adopted: `pooled` stays the default; the declared table and its
grades are untouched; no constant moves.

## 0. Settled inputs (quoted, not re-derived)

- **`NORO-TOUCH-SHARE-01`** (#666/#667, measured `3a54ad3`, seeds
  8000–8019, 288 epochs, `classic_cruise_1900`, `norwalk_gi`): A is
  bit-identical to #664 (`NORO-FOMITE-DISAGG-01`). The §4 rule fired
  `changes_coincidence` (median Jaccard 0.787), but deposit event streams
  stayed aligned on only 3/20 seeds (Jaccard ≈ 1.0 there); median
  `hand_to_mouth_calls` 4934.5 (A) → 11836.5 (D) with fewer deposits
  (26.5 → 24.5). Its §5.6 hypothesis — the D-arm divergence is real
  reallocation dynamics, not an RNG-stream disruption — is what is tested.
  Seed 8001 is one of the three aligned seeds; seed 8000 diverged.
- **`NORO-FOMITE-DISAGG-01`** §6.1 (measured `622f99f`): the archetype. A
  `<= 0` / empty / cap gate evaluated on a floating-point residue
  (|mass| ~ 1e-13 GEC) is taken differently by two algebraically equivalent
  arms, changing the *count* of downstream RNG draws and so the whole
  stream. Its fix — the exact-empty pattern (`if scale < 1.0:
  delivered_total = surface_mass`, per-class analogue in
  `_deliver_fomite_requests_by_class`) — is already on the default path.
  Its method — step two arms epoch by epoch under one process and compare
  RNG state after each epoch — is reused here.
- **Instrument seam:** `tools/noro_diag/per_host_dose_challenge.py`
  (`build_spec`, the read-only `instrumented()` wrappers). The declared
  table is the JSON shipped in #666.

## 1. Question and frozen classification rule

For each seed s ∈ {8001, 8000}, arms A and D are stepped in lockstep from
the same `ShipSimulation` seed for 288 epochs. After every epoch the root
`Generator` bit-state and the ordered per-epoch draw sequence (method,
argument shape, calling engine context) are compared.

**First divergence epoch** e* = the first epoch whose draw sequence (or,
if sequences are equal, whose bit-state) differs. Before e* both arms
must have identical cumulative event-stream counts (deposit calls,
per-class pickup requests, deliveries, `hand_to_mouth_calls`, challenge
resolutions); an inequality before e* is itself a finding (§1 class c).

The **first differing draw** d* is the first index in epoch e* at which
the two sequences differ (a differing method, a differing call context, or
one arm having a draw the other does not). Its cause is classified as
exactly one of:

- **(a) expected.** d* is issued from a fomite pickup / deposition /
  hand-to-mouth event whose *occurrence or argument* depends on a
  delivered, held or surface mass that legitimately differs between arms
  because D reallocates mass among item classes. Evidence required: the
  event, zone, item class, and the two masses — both with
  |mass| ≥ 1e-12 GEC, or one exactly 0.0 and the other ≥ 1e-12 GEC with
  the zero traceable to a class the declared table assigns share 0 or to a
  class whose mass was fully consumed (an exact zero, not a residue).
- **(b) archetype.** d* is issued (or omitted) because a `<= 0` / empty /
  cap gate — `surface_mass <= 0` (zone skip), `delivered <= 0.0`,
  `hand_load <= 0.0`, `_delivery_scale` cap, per-class empty — was taken
  differently on a quantity that in at least one arm is a floating-point
  residue: 0 < |value| < **1e-12 GEC** (frozen threshold; analogous
  quantities such as hand load use the same threshold in GEC). Evidence
  required: the gate and the two values.
- **(c) other.** Anything else; the mechanism is stated in §4.

**Verdict rule (frozen).** The archetype is ruled out for this pair iff
both seeds classify (a). Any (b) is an implementation defect and is
reported immediately; it is fixed in this session only if the fix is the
§6.1 exact-empty pattern, in which case it is labelled a default-path
change and the probe is re-run. Any (c) is reported immediately.

**Ordering witness (frozen).** Per seed, the probe records the epoch and
draw index of the first D-arm per-class pickup whose delivered mass
differs from A's by more than 1e-9 relative (both ≥ 1e-12 GEC). If d*
precedes that pickup, the share table changes something upstream of
pickup and this is reported immediately regardless of class.

## 2. Instrument (read-only)

`tools/noro_diag/touch_share_lockstep_probe.py`:

- Two `ShipSimulation`s per seed built from
  `per_host_dose_challenge.build_spec` (A: `per_surface`, `areal`,
  `shipped`; D: `per_surface`, `declared`, `shipped`, the #666 table).
- Each arm's root `rng` is replaced, before `initialize()`, by a tracing
  proxy that forwards every call unchanged to the real
  `numpy.random.Generator` and appends `(context, method, arg-shape)` to
  the arm's current-epoch trace. It consumes no randomness and changes no
  return value.
- Engine context is supplied by wrapping (not replacing) the same
  `TransmissionCore` methods `per_host_dose_challenge.instrumented()`
  already wraps, plus `_fomite_pickup_by_class`, `_deliver_one_pickup`,
  `_consume_surface_mass(_by_class)` and `_resolve_pathogen_challenge`;
  wrappers set the active context, count the event, record masses, and
  call the original with the original arguments.
- At the start of every epoch each arm's per-zone surface pool mass and,
  for the per-surface arm, per-(zone, class) mass are snapshotted
  (read-only from `TransmissionCore` state). Both arms are stepped one
  epoch, then compared; the comparison never feeds back into either arm.
- Cumulative `hand_to_mouth_calls` (all three call sites: pooled/per-class
  pickup, emesis patch, hand contact) are recorded per epoch for both arms
  for all 288 epochs, so the -01 "doubling with fewer deposits" observation
  can be placed before or after e*.
- Output is deterministic JSON; CLI-derived output paths go through the
  `_safe_path` pattern (Sonar S8707).
- `tests/test_touch_share_lockstep_probe.py` proves that the pooled default
  is bit-identical (root RNG state, surface pools, hand loads) with the
  instrument attached versus detached.

## 3. Non-goals

Larger seed blocks; AWS; changing the declared table or its grades; adding
event alignment to the -01 §4 rule (successor's job — see §8); adopting
`per_surface` or `declared`; whole-voyage dose interpretation; cleaning
policy; `derived` area basis.

## 4. Measured — pre-floor probe (`38ee2b4`)

Probe `tools/noro_diag/touch_share_lockstep_probe.py`, 288 epochs,
`classic_cruise_1900` (1910 agents), default bundle (norwalk_gi,
sars_cov2_resp, influenza_a), A vs D, one process per seed. Raw output:
`data/NORO-TOUCH-SHARE-02_prefix/NORO-TOUCH-SHARE-02_seed{8001,8000}.json`.
Masses are GEC, paired and relative; none is a dose.

### 4.1 First divergence

| | seed 8001 | seed 8000 |
|---|---|---|
| e* (first differing epoch) | 11 | 11 |
| d* (first differing draw, core stream) | 7195 | 1419 |
| event counts identical before e* | yes (all counters, all pathogens) | yes |
| A draw at d* | `uniform(445,535)` in `pickup_requests_by_class` sars_cov2_resp / KidsClub | `poisson(2)` (no fomite context) |
| D draw at d* | `uniform(445,535)` in `pickup_requests_by_class` sars_cov2_resp / **PoolDeck** | `uniform(445,535)` in `pickup_requests_by_class` **norwalk_gi / PoolDeck** |
| gate taken differently | `_pathway_fomite` `surface_mass <= 0`, sars_cov2_resp, PoolDeck | `_pathway_fomite` `surface_mass <= 0`, norwalk_gi, PoolDeck |
| A pool at start of e* | **0.0** (all three classes exactly 0.0) | **0.0** (all three classes exactly 0.0) |
| D pool at start of e* | **4.747e-8** (door_lever 3.02e-10, grab_rail_m 4.72e-8, button_or_dispenser 0.0) | **4.852e-42** (door_lever 3.09e-44, grab_rail_m 4.82e-42, button_or_dispenser 0.0) |
| deposits into that pool during e* | none in either arm | none in either arm |
| extra draws D makes at e* | PoolDeck pickup for 113 susceptibles, draws 7195–7873 | PoolDeck pickup for 148 susceptibles, draws 1419–2307 |
| **classification (frozen §1 rule)** | **(a) expected** — exact 0.0 vs ≥ 1e-12 | **(b) archetype** — exact 0.0 vs 0 < 4.85e-42 < 1e-12 |

Ordering witness (norwalk_gi, both masses ≥ 1e-12, rel. diff > 1e-9): did
**not** fire before d* on either seed. The same witness over all pathogens
fires at epoch 0 (influenza_a, Engine_Room, `button_or_dispenser`: A
7.08e-7 vs D 1.51e-5 on 8001; A 3.49e-8 vs D 7.84e-7 on 8000) — the
declared table changes per-class deliveries from the first pickup, as
designed, and every pathogen in the bundle receives the table.

### 4.2 `hand_to_mouth_calls` cumulative (A / D)

| epoch | 8001 norwalk | 8001 all pathogens | 8000 norwalk | 8000 all pathogens |
|---|---|---|---|---|
| 0 | 160 / 160 | 332 / 332 | 5 / 5 | 155 / 155 |
| 10 | 1049 / 1049 | 7709 / 7709 | 678 / 678 | 7176 / 7176 |
| 11 (e*) | 1210 / 1210 | 9489 / 9585 | 678 / **826** | 9356 / 9496 |
| 24 | 2692 / 2692 | 25268 / 26705 | 782 / 2959 | 33450 / 35295 |
| 48 | 5072 / 5056 | 43176 / 46667 | 818 / 5689 | 66628 / 72007 |
| 96 | 9324 / 9039 | 61967 / 64367 | 862 / 9785 | 105848 / 109026 |
| 144 | 10573 / 9916 | 66279 / 68591 | 894 / 11318 | 115677 / 117508 |
| 192 | 10744 / 10188 | 68088 / 71594 | 935 / 12152 | 118743 / 121261 |
| 287 | 10959 / 10500 | 78000 / 84010 | 1036 / **13771** | 126492 / 132068 |

Final norwalk_gi counters, seed 8000, A / D: `deliver_one_pickups` 918 /
13731; `deposit_calls` 305 / 542; `pickup_by_class_zones` 1021 / 1246.
Seed 8001: 10917 / 10363; 413 / 317; 993 / 997.

### 4.3 Report-immediately conditions

- (b) on seed 8000: **fired** (messaged on measurement).
- (c): not fired.
- A bit-identical to #664: not directly re-measured here; no numeric
  engine change between `3a54ad3` and `56eaa0e` (`engines/` diff is the
  `_safe_table_path` guard only), so the -01 identity measurement stands
  (inferred, not measured).
- d* before the first differing D-arm pickup: the norwalk-only witness
  never fires before d*, so for norovirus alone d* is literally first —
  but not because the table changes anything upstream of pickup: on 8001
  the divergence is another pathogen's gate; on 8000 the residue at e* is
  4.9e-42, so whatever norovirus pickups differed before e* did so on
  masses below 1e-12 and were excluded from the witness by construction
  (inferred). Not the condition's meaning; recorded, not escalated as
  such.

## 5. Inferred / hypothesis (pre-floor)

**Inferred (from §4, both seeds, same mechanism):** surface mass in both
representations decays geometrically (`_scale_surface_mass`,
`PerSurfaceFomiteState.scale/consume/routine_clean/disinfect`) and only
reaches exactly 0.0 when a delivery cap fires (§6.1 exact-empty). Under
`areal` shares every class's request/mass ratio is identical, so all
classes of a zone cap together and the zone empties exactly. Under
`declared` shares a low-share class's request stays below its mass, is
never capped, and decays forever as a residue that keeps
`surface_mass <= 0` open; D then dispatches a full per-class pickup — and
its hand-to-mouth draws — for every occupant of that zone every epoch. On
8001 the residue at e* was still macroscopic (4.7e-8, sars_cov2_resp), so
the frozen rule reads (a); on 8000 it had decayed to 4.9e-42
(norwalk_gi), so it reads (b). The two labels are one mechanism at two
ages.

**Inferred:** the -01 "hand_to_mouth doubling with fewer deposits" arises
at e* and grows from residue-open zones (8000: norwalk D/A = 13.3 by
epoch 287, starting at epoch 11 from a 4.9e-42 GEC pool). It is
draw-count inflation on de-facto empty surfaces, not reallocation
dynamics. -01 §5.6 is therefore **rejected**: the D-arm divergence in -01
is (at least on this seed) the DISAGG-01 §6.1 archetype.

**Inferred:** because the declared table is applied to all three bundle
pathogens, -01's norovirus Jaccard and `hand_to_mouth` deltas include
cross-pathogen RNG-stream perturbation (8001's first divergence is a
sars_cov2_resp gate).

**Hypothesis:** the same residue-open gates exist on the `pooled` default
path (the pooled pool also decays without a floor and only empties on a
cap), so the shipped stream has been drawing pickups on residue pools
wherever a zone was picked below its cap and never fully emptied. The
Greg Mortimer detector move in §6 is consistent with this but is one
cell, one seed.

## 6. Default-path change — surface residue floor (Benjamin, in-session)

Benjamin scoped the fix in ("We can do the floor fix here"). It is **not**
the §6.1 exact-empty pattern; it is labelled a default-path change.

- `engines/fomite_surfaces.py`: `SURFACE_RESIDUE_FLOOR_GEC = 1e-12` — a
  numerical floor (≪ one genome copy), not an epidemiological constant.
  `floor_surface_residue(mass)` returns exactly 0.0 below it.
  `PerSurfaceFomiteState._floor_unit` zeroes every class mass and
  cleanable of a (unit, pathogen) whose **total** falls below the floor
  (unit total, never per class, so the areal arm stays a re-expression of
  pooled); called after `scale`, `consume`, `routine_clean`, `disinfect`.
- `engines/transmission_core.py` `_scale_surface_mass`: `remaining` and the
  `_default` branch pass through `floor_surface_residue`. Every pooled
  decay, consumption, cleaning and disinfection path reaches the pool
  through this method or through `_roll_up_per_surface_zone` (which reads
  the already-floored per-surface total).
- Tests: `tests/test_fomite_per_surface.py` (+6: threshold function, unit
  floor on scale/consume, graded decay 1e-9 → 5e-12 continuous then snap
  to 0.0 at 5e-13, pooled `_scale_surface_mass` floors pool, cleanable
  and aggregate).
- Fast tier: 5850 passed, 7 skipped; **one change detector moved and is
  repinned with attribution**: `tests/test_covid_hull_change_detector.py`
  greg_mortimer_2020 `(1, 1, 217, 5, 0) → (1, 1, 217, 2, 0)` (CPython
  3.12 local; parent commit `38ee2b4` reproduces the old tuple in a scratch
  worktree; the 3.11 pin assumes the same move pending CI). Fewer
  campaign positives because sars_cov2_resp pickups on residue pools no
  longer occur. `diamond_princess_2020` (slow tier) already reads
  `(3400, 3031, 1938, 197, 47)` against its pin at `56eaa0e` before this
  change — pre-existing drift, not touched here.
- Hand loads (`hand_load_by_pathogen`) are **not** floored; the same
  residue pattern may exist there (§1 lists `hand_load <= 0.0` as a gate).
  Successor item.

## 7. Measured — post-floor probe (`29bbd39`, floor commit `40f22ce`)

Same probe, same seeds, epochs, platform, bundle and table; raw output
`data/NORO-TOUCH-SHARE-02_seed{8001,8000}.json`. The probe script is
unchanged between the two runs.

| | seed 8001 | seed 8000 |
|---|---|---|
| e* | 10 | 23 |
| d* (core stream) | 8543 | 2235 |
| event counts identical before e* | yes | yes |
| A draw at d* | `poisson(1)` (no fomite context; A had just finished Engine_Room sars_cov2_resp pickup, 119 susceptibles, pool 7.23e-6) | `uniform(445,535)` in `pickup_requests_by_class` sars_cov2_resp / PhotoShops (pool 0.0235) |
| D draw at d* | `uniform(445,535)` in `pickup_requests_by_class` sars_cov2_resp / **Specialty** | `uniform(445,535)` in `pickup_requests_by_class` sars_cov2_resp / **PoolDeck** |
| gate taken differently | `surface_mass <= 0`, sars_cov2_resp, Specialty | `surface_mass <= 0`, sars_cov2_resp, PoolDeck |
| A pool at start of e* | **0.0** (all four classes 0.0) | **0.0** (all three classes 0.0) |
| D pool at start of e* | **2.699e-9** (utensil only; other classes 0.0) | **6.560e-6** (grab_rail_m 6.52e-6, door_lever 4.17e-8, button_or_dispenser 0.0) |
| extra draws D makes at e* | Specialty pickup, 5 susceptibles, draws 8543–8573 | PoolDeck pickup, 14 susceptibles, draws 2235–2319 |
| norwalk ordering witness before d* | none | **epoch 14**, MainTheater, `button_or_dispenser`, A 87.6 vs D 1483.2 (before e* = 23) |
| **classification (frozen §1 rule)** | **(a) expected** — 0.0 vs 2.7e-9 ≥ 1e-12 | **(a) expected** — 0.0 vs 6.6e-6 ≥ 1e-12 |

No quantity at either d* is in (0, 1e-12): the (b) reading on 8000 is
gone and no new (b) appears. On 8000 a norovirus per-class delivery
differed in mass nine epochs before d* without moving the RNG stream —
confirming that mass differences alone do not change the draw sequence;
only gates do. The "d* before first differing D pickup" condition is not
met on 8000; on 8001 the norwalk witness never fires before d* for the
reason given in §4.3.

`hand_to_mouth_calls` cumulative (A / D), post-floor:

| epoch | 8001 norwalk | 8001 all | 8000 norwalk | 8000 all |
|---|---|---|---|---|
| 10 (8001 e*) | 1032 / 1032 | 8091 / 8104 | 33 / 33 | 6825 / 6825 |
| 23 (8000 e*) | 2181 / 1663 | 24970 / 25793 | 1007 / 1007 | 33219 / 33239 |
| 24 | 2185 / 1663 | 25474 / 26317 | 1011 / 1011 | 33710 / 33754 |
| 48 | 3596 / 1664 | 43802 / 43105 | 1034 / 3559 | 66840 / 70493 |
| 96 | 4234 / 1684 | 58039 / 54350 | 1062 / 9983 | 96831 / 112727 |
| 144 | 4253 / 1723 | 58815 / 54530 | 2234 / 10026 | 101689 / 119016 |
| 287 | 5370 / 1813 | 67520 / 61688 | 2387 / 10204 | 106327 / 123238 |

Final norwalk_gi counters A / D — 8001: `deposit_calls` 731 / 364,
`deliver_one_pickups` 5262 / 1647, `pickup_by_class_zones` 882 / 27;
8000: 335 / 308, 2235 / 9947, 380 / 717.

e* moved (8001: 11 → 10; 8000: 11 → 23) between the two runs: the floor
itself changes both arms' streams (labelled default-path change, §6), as
expected.

## 8. Verdict, inferred, hypothesis, next decision

**Verdict (frozen rule, measured `29bbd39`, seeds 8001 and 8000, 288
epochs):** both seeds classify (a). **The §6.1 archetype is ruled out
for this pair after the residue floor.** Pre-floor (`38ee2b4`) it was
**not** ruled out: seed 8000 was (b) on a 4.9e-42 GEC norovirus residue.

**Measured:** every first divergence, pre- and post-floor, on both seeds,
is the `_pathway_fomite` `surface_mass <= 0` zone gate, taken on a pool
that A emptied exactly (all classes capped together) and D did not (a
low-declared-share class kept mass). Post-floor three of four are
sars_cov2_resp gates; none is a norovirus event.

**Inferred:**
1. The D-arm divergence in -01 is not reallocation dynamics in the sense
   of §5.6 there; it is gate-count divergence — D keeps zones open that A
   closes. Pre-floor that included residue pools (archetype); post-floor
   it is pools that are macroscopic by the frozen 1e-12 rule but still
   far below one genome copy (2.7e-9, 6.6e-6 GEC).
2. The -01 `hand_to_mouth` "doubling with fewer deposits" arises after e*
   on both seeds and both runs and comes from D dispatching pickups (and
   their hand-to-mouth draws) to every occupant of a zone whose declared
   low-share class still holds sub-copy mass. It is a draw-count effect,
   not a mechanism that moves norovirus dose materially (paired, relative;
   no dose is quoted).
3. Because the table is applied to all bundle pathogens, any norovirus-only
   reading of A vs D is confounded by cross-pathogen stream shifts; three
   of the four measured first divergences are sars_cov2_resp gates.

**Hypothesis (not measured):**
- The 1e-12 GEC floor is a numerical floor. A pool of 1e-6 GEC cannot
  contain a virion; whether `surface_mass <= 0` should instead close at a
  physically meaningful threshold (order 1 GEC, or the LOD already used
  for surface swabs) is a modelling decision, not a defect fix, and would
  change both arms and the default path.
- Hand loads carry the same geometric decay without a floor and gate
  `hand_load <= 0.0`; the residue pattern likely exists there too.

**Next decision (for Benjamin):**
1. Whether the AWS 20-seed block with event alignment (the -01 successor)
   is justified now. This ledger's reading: **not yet**. Event alignment
   would measure a D arm whose extra events are sub-copy-mass pickups;
   the block would mostly count those. Decide first whether the zone gate
   closes at a physical threshold (hypothesis 1) and whether the declared
   table should be pathogen-scoped (inferred 3). If both are "no change",
   the block is justified as-is at the floor commit.
2. The residue floor is now on the default path (§6); the Greg Mortimer
   detector repin records its effect on one COVID cell.

Successor items (not done here): event alignment in the -01 §4 rule;
pathogen-scoping of the declared table; hand-load floor; physical
zone-gate threshold; `diamond_princess_2020` slow-tier detector drift
(pre-existing at `56eaa0e`).
