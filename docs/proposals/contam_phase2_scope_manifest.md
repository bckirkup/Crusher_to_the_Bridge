# CONTAM-vs-native HVAC Phase 2 thin scope manifest (four-cruise contrasts)

> **Status:** Proposed — awaiting Benjamin's sign-off. No campaign files,
> AWS submission, pilot submit, Ship X adapter, S lane, epidemiology coupling,
> or `engines/`/`tools/` change is authorized by this document. The design
> freeze (campaign files under `campaigns/contam/phase2_cruise_contrasts_01/`)
> is a later session, after sign-off.
> **Filing:** `docs/proposals/` per the `docs/README.md` filing rule; the
> campaign artifact does not exist yet. Verified against `origin/main`
> `6f368f67` (post PR #1181).

## 1. Purpose and authority

This manifest freezes the thinned Phase 2 scope for the Edison Scientific
CONTAM-vs-native HVAC study: the **four-cruise transport contrasts**. Phase 2
is **transport-only**, like Phase 1: an identical tracer source is propagated
by the same Crusher mass operator under two airflow-field generations (N, E)
and a bounded committed-project baseline (P), now with named operational
arms on the four cruise archetypes. Epidemiology remains the headline of the
publication, but it is the Phase 3 decision gate, not Phase 2 work.

Settled inputs, not re-derived here:

- Phase 1 is complete and durable: manifest
  `docs/proposals/contam_phase1_scope_manifest.md` (signed off), frozen
  campaign `campaigns/contam/phase1_hvac_tracer_01/` (340/340 trajectories,
  `readout/phase1_readout.json`, `READOUT.md`), ledgers
  `docs/ledger/CONTAM-PHASE1-PILOT-01.md` and
  `docs/ledger/CONTAM-PHASE1-FULL-01.md`.
- Benjamin's standing decisions: thinned ambition, **not** Edison's full
  T00–T10 implementation spec; versioned arms, labelled baselines, ledger
  entries, no silent behaviour changes ("I don't like defects"); Ship X
  adapter funded but later; Phase 2 = the four-cruise contrasts DC01–DC05 and
  DC07 on N/E lanes with P as a bounded baseline.
- Edison's `computational_study_protocol.md` and `engineering_handoff.md`
  (7 November 2026, baseline pin `f5d32477`) are **proposals**. Where they
  conflict with the settled scope, the settled scope governs and the
  deviation is noted in §2.4. The governing contrast registry they cite,
  `decisive_contrasts.csv`, was **not** supplied with the attachments; §2
  quotes the contrast definitions from the protocol/handoff prose and §11
  asks for the CSV to be checked before freeze.
- Machinery: `tools/contam_fleet_compare.py` field ops (`set_oa` scope-aware
  default `supply_groups` with labelled `all_groups` baseline; `set_filter`;
  `scale_ach`; `_FIELD_OPS` forces a fresh ContamX export + solve — PR #1169),
  `engines/contamx_ahs_bridge.py` declared-OA fallback (PR #1170),
  `engines/py_contam_bridge.py` propagator, `tests/test_contam_analytic_fixtures.py`
  F1–F6, the Phase 1 campaign pattern (`design/build.py` → `campaign.json` →
  `cell.py`/`entry.py`/`readout.py`, `scripts/campaign` submit, AWS Batch
  only, `AWS_PROFILE=picard`), and the Option A local field pre-stage
  (ContamX is in no Docker image).

## 2. Contrast selection

### 2.1 Lanes (unchanged from Phase 1 §2)

| Lane | Field generation | Propagation / permitted claim |
|---|---|---|
| **N — native** | Prescribed star-HVAC + passive/cross-zone heuristic flows from the (arm-mutated) `air_flow_paths.json` | `engines/py_contam_bridge.py` matrix-exponential mass propagator. Not a pressure-network ground truth. |
| **E — commissioned export** | Fresh `export_prj_with_path_map(..., ahs_terminal_mode="commissioned")` of the same arm-mutated JSON, `_annotate_ahs_declared_oa`, ContamX solve, `engines/contamx_ahs_bridge.py` AHS synthesis | `ContamXTransportEngine` inherits the same propagator. Tests operational mapping and field generation only. |
| **P — committed project** | Checked-in `contam/platform.prj` + `contam/path_map.json`, **baseline arm only** | Same bridge after PRJ parsing / alias normalization. Cannot represent a JSON-only mutation (protocol §4: "A P-lane result cannot represent a JSON-only control mutation applied to an unchanged PRJ"). |
| **S — stock ContamX** | **Excluded** | Independent-solver claim stays deferred. |

**Lane honesty** (protocol §4, Phase 1 §2): N/E/P share the `expm` mass
propagator; agreement is not independent contaminant-solver validation.
Every arm applies the same filter efficiency through the shared propagator
on `is_hvac_ducted` paths, so an arm's lane difference isolates field
generation, not integration.

### 2.2 Arms (versioned, named; `baseline` is the anchor)

All arms are `tools/contam_fleet_compare.py` op lists applied to a copy of
the platform `air_flow_paths.json` and/or the engine parameters, exactly as
the fleet arms in `data/config/contam_compare/fleet_arms.json` are. The AHS
tracer gain is `r = (1 − f)(1 − η)` with `f` the supply-group OA fraction and
`η` the filter efficiency (protocol §5.1). Every active supply group on the
four hulls declares `oa_fraction = 0.2`, so at the shipped `η = 0.5`
`r_base = 0.4` (verified §3).

| Arm id | Ops (fleet-compare grammar) | `f` / `η` on the 59 supply groups | AHS gain `r` | Serves | Expressible today |
|---|---|---|---|---:|---|
| `baseline` (**B**) | none | 0.2 / 0.5 | 0.40 | anchor for every contrast; the only P-lane arm | yes (Phase 1 arm) |
| `oa_050` (**O**) | `set_oa value=0.5` (default scope `supply_groups`) | 0.5 / 0.5 | 0.25 | DC01 | yes |
| `filter_090` (**F**) | `set_filter value=0.9` | 0.2 / 0.9 | 0.08 | DC01 | yes (fleet arm `filter_merv13`) |
| `oa_050_filter_090` (**OF**) | `set_oa 0.5` + `set_filter 0.9` | 0.5 / 0.9 | 0.05 | DC01 | yes |
| `eq_gain_025_filter` (**G**) | `set_filter value=0.6875` | 0.2 / 0.6875 | 0.25 | DC02 (equal gain to **O**) | yes |
| `ach_150_supply` (**A**) | `scale_ach factor=1.5` **restricted to supply groups** | 0.2 / 0.5, turnover ×1.5 | 0.40 | DC04 high-turnover arm | **no — see §2.4 and §11.1** |
| `oa_080` (**R**) | `set_oa value=0.8` (default scope `supply_groups`) | 0.8 / 0.5 | 0.10 | DC04 matched-removal partner | yes |

`set_oa` with the default `supply_groups` scope rewrites `oa_fraction` only
on groups with `hvac_duty > 0` and preserves the declared `oa_fraction`
(1.0) of every duty-0 exhaust branch (`_set_oa_supply_groups`), which is the
protocol's "apply it only to approved non-sanitary groups" and "keep the 121
duty-zero/OA-one groups unchanged". The legacy `all_groups` scope is the
labelled baseline and is **not** used by any Phase 2 arm. Native physical
supply (`ach × V × duty`) is unchanged by `set_oa`/`set_filter`, so O/F/OF/G
are gain-only fixed-field arms in N; in E the mutated JSON is re-exported
and re-solved, and the realized OA/recirculation is read back from the
solved field (DC05).

### 2.3 Contrast definitions as executable arms

Each definition quotes the protocol (`computational_study_protocol.md` §5.1
unless stated) or handoff (`engineering_handoff.md` §6), then states the
Phase 2 operationalization. Readout metrics are defined in §8.

**DC01 — monotonicity / ordered-gain control.** Protocol: "**DC01–DC02**
monotonicity/equal-gain controls"; "At declared cruise baseline f=.2 and
eta=.5, intended B/O/F/OF AHS gains are **.40/.25/.08/.05**. Thus **OF ≤ F ≤
O ≤ B** is a conditional prediction for concentrations and nonnegative
exposure burdens—not a measured hull finding, a peak-time ordering, or an
equal-resource comparison." Handoff §6: "DC01/DC02 use coefficient
ordering/equality before response computation." Arms: B, O, F, OF on N and E.
Readout: per seed, per lane, per hull, the ordering `B_V(OF) ≤ B_V(F) ≤
B_V(O) ≤ B_V(B)` and the per-zone ordering of `E_i(12 h)`; violations are
counted and listed (a violation in N is a propagator/operator finding; a
violation in E only is a field-generation finding). This is a control, not a
result: "Without costs or feasibility constraints, dominance of stronger
fixed-field removal is not an operational optimum."

**DC02 — equal-gain equivalence control.** Protocol: "Equal gain vectors
give identical operators only if OA/filter affect no other terms." Arms: O
(`f=0.5, η=0.5`) vs G (`f=0.2, η=0.6875`), both `r = 0.25` on every supply
group. They differ exactly where OA and filter act on other terms: `η` also
applies to the `is_hvac_ducted` cross-zone trunk links (1 / 11 / 17 / 21 of
the 17 / 31 / 48 / 88 cross-zone links on expedition / classic / spirit /
mega, carrying 400 / 15,000 / 22,000 / 40,500 m³/h), while `f` changes the
OA/recirculation split of the exported AHS in E. Readout: paired per-seed
`B_V(O) − B_V(G)` and `max_i |E_i(O) − E_i(G)|` per lane; an exact zero in N
means the operator is gain-only on that hull, a nonzero value measures the
"other terms".

**DC03 — exact mean-loss / different-mixing control (closed form, no
trajectories).** Protocol: "**DC03** exact mean-loss/different-mixing
control"; "The selected F3 illustration already predicts equal mean
concentration **1.13198508548** at 1 h for \((a,r)=(1.8,.4)\) and
\((1.2,.1)\), but source-room values **2.23397767363** versus
**3.13994649823** and remote-room values **.580988791411** versus
**.128004379109**. These are known scalar controls, not discoveries." Handoff
§6: "DC03 uses independent conservative mixing plus common loss; the
existing F3 different-mixing values are controls, not novel results."
Operationalization: DC03 is executed as a closed-form fixture in
`tests/test_contam_analytic_fixtures.py` next to the existing F3 class
(three 100 m³ rooms, `C0 = (10, 0, 0)`; the two cases are `ach=1.8, oa=0.2,
η=0.5` and `ach=1.2, oa=0.8, η=0.5`, the exact three-room analogue of the
DC04 pair). It consumes zero Batch trajectories; recomputed here: mean rate
`a(1−r) = 1.08/h` in both cases, mean `(10/3)e^{−1.08} = 1.131985`, source
`1.131985 + (20/3)e^{−a}` = 2.233978 / 3.139946, remote
`1.131985 − (10/3)e^{−a}` = 0.580989 / 0.128004 — matching the protocol
values. The fixture is a `tests/` addition at design freeze (no `engines/`
or `tools/` change); it is listed as a decision in §11.6.

**DC04 — feasible group-matched removal (hull level).** Protocol: "set high
turnover \(a_{hi,g}=\alpha a_{base,g}\) at baseline gain, and match
baseline-turnover gain by \(r_{low,g}=1-\alpha(1-r_{base,g}),\ \alpha=1.5\).
Require \(0\le r_{low,g}\le1\); with alpha=1.5, baseline gain must be at
least 1/3. … The declaration-only screen identifies **59 active supply
groups** across the four cruise hulls (9, 13, 17, and 20), all with baseline
f=.2 and design eta=.5. Their rbase=.4 gives rlow=.1, achievable
algebraically at **OA=.8 with eta=.5**. Preserve the other **121
duty-zero/OA-one groups** unchanged. This is groupwise nominal matching,
**not proven operating feasibility or a common whole-vessel k**." Arms: A
(`ach_150_supply`, turnover ×1.5 on the 59 supply groups, `r = 0.4`) vs R
(`oa_080`, baseline turnover, `r = 0.1`), each also contrasted with B; per
supply group `k_hi = 1.5a·0.6 = 0.9a` and `k_low = a·0.9 = 0.9a`. Readout:
paired per-seed `B_V(A) − B_V(R)`, the per-zone `E_i(A) − E_i(R)` distribution
with sign-flip zones listed (a local increase under changed mixing "must not
be averaged away in a hull-wide benefit"), and the arm reductions
`R_A = 1 − B_V(A)/B_V(B)` and `R_R` with their pairwise gap. The match label
is nominal and groupwise; if any group's `r_low` would leave `[0, 1]` the
arm fails closed ("Never clip negative gain and retain a 'matched' label").
The R arm is expressible today; the A arm is **not** (§2.4).

**DC05 — paired N/E field adequacy.** Protocol: "**DC04–DC05** feasible
group-matched removal and paired N/E field adequacy"; "A pair matched in N is
not automatically matched in E." Handoff §6: "DC05/DC07 then ask which hull
field/source pathways change an approved decision." Arms: none additional —
every arm runs in both lanes with the same seeds. Readout: paired per-seed
`N − E` differences for every hull × arm (Phase 1's contrast, now per arm),
the **arm-effect parity** (does `ΔB_V(arm − B)` agree in sign and magnitude
between N and E; same for the per-zone `ΔE_i` tail), and the realized
per-AHS supply / return / OA / recirculation flows read from the solved E
field entries against the declared values, so the DC04 "matched in N"
pairing is checked in E rather than assumed. Path-type flow differences are
reported separately from exposure differences (protocol §5.2).

**DC07 — selected source / receptor responses.** Protocol: "**DC07**
selected source/receptor responses"; "For source map \(U\) and nonnegative
receptor map \(W\), compute selected responses \(H(t)=WD_V^{-1}e^{A_Mt}U\),
\(K(T)=WD_V^{-1}\int_0^T e^{A_Mt}dt\,U\)"; "Kosmos needs per-zone/per-source
tails and source-to-remote contrasts, not just a whole-fleet mean or an
isolated percentile." Arms: none additional. Each trajectory is one column
of `K(12 h)`: the source realization (seed → source zone × timing, §5) is
`U`, and the per-zone time-integrated concentration `E_i(12 h)` that the
Phase 1 `cell.py` already emits in `zone_stats` is the receptor response
for every `W = e_i`. Readout: per hull × lane × arm × source class, the
distribution over receptor zones of `E_i(12 h)` normalized by emitted mass,
split local (receptor in the source's HVAC group or an adjacency neighbour)
vs remote, with p50/p95/max, time-to-peak, first arrival above the numerical
floor, and the never-reached receptor count. No all-source response tensor
is built ("Do not replace 120 redundant trajectories with an unnecessary
all-source response tensor"); the 20 realizations per hull are the selected
sources.

### 2.4 Deviations from the Edison proposal (settled scope governs)

- **DC04 high-turnover arm is not expressible with the existing field ops.**
  `scale_ach` (`_op_scale_ach`) multiplies `ach` on **every** `hvac_zones[]`
  group with no scope; duty-0 groups are exhaust-only terminals whose flow is
  `ach × V_room` in both lanes (`engines/py_contam_bridge.py`
  `_append_exhaust_paths` under the default `duty0_terminal_mode="extract"`;
  `tools/contamw34_prj.py` `exhaust_only` → `flows[room] = (0.0, ach * vol)`),
  so `scale_ach 1.5` would also scale the 121 sanitary exhausts and break
  "Preserve the other 121 duty-zero/OA-one groups unchanged". `set_duty`
  without `select` retypes duty-0 exhausts into supply groups, so it is not a
  substitute. Options for §11.1: (a) a `scope` argument on `scale_ach`
  mirroring PR #1169's `set_oa` scope (`supply_groups` default,
  `all_groups` the labelled legacy baseline that the fleet arm `ach_surge`
  keeps), a small `tools/` PR before design freeze — **recommended**; (b) a
  campaign-local versioned op in the Phase 2 `cell.py`; (c) drop the A arm,
  leaving DC04 as `oa_080` vs `baseline`, which is unmatched and collapses
  into the DC01 monotone family.
- **`decisive_contrasts.csv` not supplied.** Definitions above are from
  prose; the CSV must be reconciled before freeze (§11.7). Edison's
  priority order ("front-load DC03–DC05 … with DC07") is honoured by making
  the DC01/DC02 control arms separable (§4 "core" matrix).
- **No "passenger circulation" source class.** Edison lists "eligible large
  public/venue, passenger circulation, remote/weakly connected or sanitary
  region"; Phase 2 reuses the Phase 1 selector unchanged (`large_venue` /
  `sanitary_branch` / `remote_weak`, §5). `Cabin_Corridor` is inside
  `LARGE_VENUE_TYPES` and is outranked on every cruise hull by occupancy /
  volume, so no corridor is a Phase 2 source (§5 pools). Adding a class is a
  tracer amendment, not adopted (§11.4).
- **No `λ = 0.1/h` sensitivity, no `η = 0.9` global sweep beyond the F/OF
  arms, no OA × η grid, no sustained/moving sources, no event-aligned
  control onset, no itinerary dose** (`D_p` requires a breathing rate; none
  is declared).
- **No T00–T10 machinery**: no 80-platform inventory table, source-register
  adapter, Parquet reducer, Kosmos query path, fresh-process randomized
  timing blocks, or A00–A27 metric contract. Timing/RSS stay report-only
  diagnostics as in Phase 1.

### 2.5 Excluded contrasts (one line each, from the protocol's own gating)

The protocol names DC06, DC08–DC12 only in summary ("**DC06/DC08** add
pressure-response or representation alternatives only when informative.
**DC09–DC11** establish switching/cache, independent integration, and
response-computation performance; **DC12** preserves vessel and fleet
scope."); the DC09/DC10/DC11 assignment below follows that listed order and
is an inference pending the CSV.

- **DC06 (boundary / pressure response)** — excluded: "DC06 requires
  supported boundary accounting" and "the current adapter skips
  envelope-leak/unknown-endpoint paths; account for their tracer/ambient
  contribution or retain a boundary-specific blocker" — that is an
  `engines/contamx_transport.py` change, out of scope.
- **DC08 (representation alternatives)** — excluded: "only when
  informative", i.e. conditional on a DC05 finding that does not exist yet.
- **DC09 (switching / cache controls)** — excluded: Phase 2 arms are fixed
  fields with no scheduled change, so there is no W1 "changing field/control"
  workload; the T04 cache-contract work is `engines/`.
- **DC10 (independent integration)** — excluded: it is the S lane, deferred
  by the settled scope.
- **DC11 (response-computation performance)** — excluded: multi-right-hand-side
  / exponential-action profiling is engineering benchmarking, not a
  transport contrast; Phase 2 reports timing as a diagnostic only.
- **DC12 (vessel and fleet scope, all 80 platforms)** — excluded: Phase 2 is
  the four cruise hulls; "Never extrapolate the purposive panel into measured
  fleet coverage" applies to its readout.

## 3. Four-cruise hull panel (recomputed from `data/platforms/<hull>/`)

| Hull | Zones | Volume (m³) | HVAC groups (supply / duty-0) | Rooms served | HVAC-unserved zones | Cross-zone links (ducted) | Adjacency links | `contam/path_map.json` entries | Committed PRJ | `hobbyist_overrides.json` | Phase 1 state |
|---|---:|---:|---|---:|---|---:|---:|---:|---|---|---|
| `expedition_cruise_450` | 47 | 19,358.98 | 22 (9 / 13) | 46 | 1 (`PoolDeck`) | 17 (1) | 48 | 343 | yes | yes | Phase 1 panel hull; N/E/P baseline measured (`CONTAM-PHASE1-FULL-01`) |
| `classic_cruise_1900` | 79 | 56,403.33 | 30 (13 / 17) | 78 | 1 (`PoolDeck`) | 31 (11) | 75 | 835 | yes | yes | reserved for Phase 2 (Phase 1 §3) |
| `spirit_cruise_3000` | 115 | 84,704.15 | 45 (17 / 28) | 112 | 3 (`AftPool`, `MainPool`, `SportsDeck`) | 48 (17) | 103 | 1,302 | yes | yes | reserved for Phase 2 |
| `mega_cruise_5000` | 192 | 403,554.55 | 83 (20 / 63) | 187 | 5 (`Aqua_Theater`, `CentralPark`, `Main_Pool_Deck`, `Sports_Court`, `Waterpark`) | 88 (21) | 202 | 2,623 | yes | yes | reserved for Phase 2; largest hull of either phase by zones, volume, and path map (Phase 1's `missouri_bb63`: 103 zones, 151,331.55 m³, 2,248 entries) |
| **Total** | **433** | **564,021.01** | **180 (59 / 121)** | 423 | 10 | 184 (50) | 428 | **5,103** | 4 / 4 | 4 / 4 | — |

Declaration facts the contrasts depend on (every group checked):

- All 59 supply groups: `hvac_duty = 0.5`, `oa_fraction = 0.2`, no per-group
  `filter_efficiency` (the engine-level `η = 0.5` applies); `ach` ∈ {5, 6, 8,
  10, 12, 15, 20}/h. Hence `r_base = 0.4 ≥ 1/3` on every group and the DC04
  `r_low = 0.1` is feasible algebraically on all 59.
- All 121 duty-0 groups: `hvac_duty = 0.0`, `oa_fraction = 1.0`, `ach =
  19.2`/h; they are the `AHU_HD_*` sanitary exhaust branches and their count
  equals the `Sanitary` zone count on each hull (13 / 17 / 28 / 63).
- Zone counts, volumes, and the 9/13/17/20 and 121 group counts match Edison's
  Table 2 and §5.1 declaration screen exactly.
- The Phase 1 `expedition_cruise_450` E/P fields were produced at repo SHA
  `a3dab46f`; `git diff a3dab46f..origin/main` over the four hulls'
  `data/platforms/` directories, `tools/contam_prj_bridge.py`,
  `tools/contamw34_prj.py`, `tools/contam_fleet_compare.py`,
  `engines/contamx_ahs_bridge.py`, `engines/contamx_transport.py`, and
  `engines/py_contam_bridge.py` is empty, so those two fields are
  reproducible inputs for Phase 2 (§4 reuse rule).

Inclusion/exclusion: these are Edison's "all four required cruise
archetypes"; the Phase 1 non-cruise hulls (`destroyer_baseline`,
`fletcher_class_destroyer`, `lexington_cv2`, `saratoga_cv3`, `missouri_bb63`)
are not rerun; `expedition_cruise_300` and `messy_cruise_500` are excluded
(legacy / no committed bundle); the Ship X 22-zone template is not a
platform and stays blocked pending the funded adapter.

## 4. Exact run matrix

Common to every cell: 20 paired seeds (`seed = 1..20`), 12 epochs × 1.0 h,
one trajectory per hull × lane × arm × seed, each written as
`cell_{seed}.json` by a 20-child Batch array per block (the Phase 1 shape).

**Full matrix (DC01–DC02 controls included):**

| Component | Hulls × lanes × arms × seeds | Trajectories | Hourly steps | Blocks (arrays of 20) |
|---|---|---:|---:|---:|
| N/E primary | 4 × 2 × 7 × 20 | 1,120 | 13,440 | 56 |
| P baseline (arm `baseline` only) | 4 × 1 × 1 × 20 | 80 | 960 | 4 |
| **Total** | | **1,200** | **14,400** | **60** |

**Core matrix (if Benjamin drops the DC01/DC02 control arms, §11.2):** arms
B, A, R only → N/E `4 × 2 × 3 × 20 = 480`, P 80, **560 trajectories**, 6,720
steps, 28 blocks. DC03 (closed form) adds zero trajectories either way.

**Seed pairing rules:** seed `s` selects the same source realization (§5)
in every lane **and every arm** of a hull, so lane contrasts (N − E, P − N)
and arm contrasts (arm − B, A − R, O − G) are all paired per seed with
`n = 20`. Every cruise pool has exactly 10 zones, so seeds 1–20 enumerate
each source zone with both timing patterns exactly once; there are no
repeated realizations. Seeds are a deterministic source-realization
ensemble, not agent stochasticity; 95% half-widths over the 20 paired
differences describe that ensemble.

**Field solves (ContamX, local Option A pre-stage) and Phase 1 cache reuse:**

| Field set | Count (full) | Count (core) | Fresh solve required? |
|---|---:|---:|---|
| E, arm `baseline`, 4 hulls | 4 | 4 | 3 fresh; `expedition_cruise_450:E` exists in the Phase 1 cache (inputs unchanged, §3) |
| P, arm `baseline`, 4 hulls | 4 | 4 | 3 fresh; `expedition_cruise_450:P` exists in the Phase 1 cache |
| E, op arms (O, F, OF, G, A, R) × 4 hulls | 24 | 8 | **all fresh** — every op is in `_FIELD_OPS`, which forces export + solve (PR #1169); none can reuse a baseline field |
| **Total** | **32** | **16** | 30 fresh + 2 reusable (full); 14 + 2 (core) |

Reuse rule: the Phase 2 pre-stage re-solves all 32 fields into one
`field_cache.json` (Phase 1's 11 solves took 0.80 s in total, max 0.24 s)
and, as a report-only reproducibility control, byte-compares the two
`expedition_cruise_450` baseline fields with the Phase 1 cache (SHA256
`b91665323192f95591f538aeb9badfefc1c6e7393aa7c4cafaef0748a496f5b5`). N
needs no external solve; the native engine rebuilds its operator from the
mutated JSON per arm. Field-cache keys are `hull:lane:arm` and the cache
records the realized per-group `ach` / `hvac_duty` / `oa_fraction` and the
filter efficiency used at export, so a stale-field reuse is impossible by
construction (handoff §4: cache keys must include every actual dependency).

## 5. Source pool and tracer protocol

Phase 2 **reuses the Phase 1 tracer protocol unchanged**: `1,000,000`
tracer units per seed normalized by emitted mass, `natural_decay_rate = 0.0`
(conservative surrogate; the optional `0.1/h` sensitivity is not adopted),
shipped baseline `filter_efficiency = 0.5` (arms F/OF/G override it as the
named op), 12 × 1.0 h epochs, timing patterns `t0_pulse` (`1e6` at `t = 0`)
and `t0_t1_split` (`500,000` at `t = 0` and `500,000` after the first hourly
step). Justification: the Phase 2 question is whether named operational arms
and field generation change where the tracer goes; changing the tracer at
the same time would confound that with Phase 1 and break the
`expedition_cruise_450` bridge (its Phase 2 `baseline` cells must reproduce
the Phase 1 N/E/P cells seed-for-seed — a bit-identity check listed in §8).

Source pools reuse the Phase 1 `design/build.py` selector verbatim
(metadata-only: zone type, volume, `max_occupancy`, HVAC service and duty,
adjacency degree; tie-break by zone id; up to 4 `large_venue`, 3
`sanitary_branch`, 3 `remote_weak`; no VSP/Park/attack-rate input).
Materialized output for the four hulls, recomputed from the committed
platform JSONs (to be frozen in the Phase 2 design file before any cell
runs):

| Hull | `large_venue` (4) | `sanitary_branch` (3) | `remote_weak` (3) |
|---|---|---|---|
| `expedition_cruise_450` | `MainDining`, `TheaterLng`, `CasualDining`, `ExpedLounge` | `HD_5P_F`, `HD_5P_M`, `HD_7S_F` | `PoolDeck` (unserved), `Library`, `MedBay` |
| `classic_cruise_1900` | `MainTheater`, `MainDining_L`, `MainDining_U`, `LidoBuffet` | `HD_4M_M`, `HD_5L_F`, `HD_9L_F` | `PoolDeck` (unserved), `IsolRoom`, `Bridge` |
| `spirit_cruise_3000` | `MainTheater`, `MainDining_L`, `MainDining_U`, `Promenade` | `HD_4M_F_1`, `HD_4M_F_2`, `HD_5L_M` | `SportsDeck`, `AftPool`, `MainPool` (all unserved) |
| `mega_cruise_5000` | `Royal_Promenade`, `Main_Theater`, `CentralPark` (unserved, 36,000 m³), `Windjammer` | `HD_3D_F`, `HD_3D_M`, `HD_5P_F_1` | `Sports_Court`, `Waterpark`, `Aqua_Theater` (all unserved) |

The `expedition_cruise_450` pool is identical to its Phase 1 pool. HVAC-unserved
sources reach air only through adjacency / cross-zone paths; they are
reported as declared `remote_weak` (or, for `CentralPark`, a large venue with
no HVAC service), never silently dropped. `t0_t1_split` on a `sanitary_branch`
source with a duty-0 exhaust is a legitimate near-total-removal case.

**Deterministic seed → source mapping (Phase 1 rule, unchanged):** `k = s −
1`; timing `k mod 2` (`0 = t0_pulse`, `1 = t0_t1_split`); zone
`pool[(k // 2) mod 10]` in the pool order `large_venue`, `sanitary_branch`,
`remote_weak`. Seeds 1–8 are large venues, 9–14 sanitary branches, 15–20
remote/weak zones.

## 6. Machinery and campaign gates

- **Namespace:** `campaigns/contam/phase2_cruise_contrasts_01/` with the
  Phase 1 file pattern — `design/build.py` (writes
  `design/phase2_cruise_contrasts_design.json`, `source_pools.json`,
  `campaign.json`), `cell.py` (`--mode field-cache | trajectory`, new
  `--arm`), `entry.py`, `readout.py`, `LEDGER.md`. Blocks are named
  `<hull>_<lane>_<arm>`; `campaign.json` pins `queue`
  `picard-campaign-queue`, `resources` 1 vCPU / 2048 MiB, an `image_tag`
  with digest, and `readout`. Submission only through `scripts/campaign`
  (`AWS_PROFILE=picard`), AWS Batch only, never the local box for
  trajectories.
- **Arm application:** `cell.py` applies the arm's op list through
  `tools.contam_fleet_compare._apply_arm_ops` so the mutation is the same
  object the fleet comparison uses, and records the `edits` log plus the
  realized per-group settings in every cell artifact. No `engines/` or
  `tools/` change is made at design freeze other than the §11.1 decision.
- **Option A field pre-stage:** `cell.py --mode field-cache` runs locally
  with the official NIST ContamX `3.4.0.3 64 bit` binary (SHA256
  `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`, tarball
  SHA256 `3612798dff9a4f1ea4f0279c4c7b526b244b88875dea425fafd868f3570df4fa`;
  NIST Contam is U.S. public domain, 17 U.S.C. §105) to write the 32-field
  `field_cache.json`, uploaded to
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase2_cruise_contrasts_01/field_cache/field_cache.json`;
  every E/P trajectory child consumes `--field-cache-uri`. The pilot ledger
  records the exact repo SHA and binary hash used for field generation
  (Phase 1 `LEDGER.md` requirement). No ContamX binary enters the campaign
  image; a native fallback on an E/P cell is `BLOCKED_ENGINE_FALLBACK`, never
  a result.
- **Campaign-preflight gates (Rule A, before any AWS submission):**
  admissibility, selectors, thresholds and report-only diagnostics frozen in
  the design file before the first cell runs; geometry/seed gate validated
  (`build.py --check` reports trajectory and array-child counts equal to §4);
  local smoke proves each arm's op reaches the engine (the `edits` log and
  realized settings differ from baseline exactly as declared) and the cell
  output contract is unchanged; `scripts/campaign describe` and
  `submit --dry-run --account 994254241749` counts match the design (60 or
  28 blocks, `arrayProperties.size = 20` each); pinned job-definition
  revision and image digest (never a bare tag; `scripts/campaign submit`
  registers a new revision per block — record each); design manifest
  mirrored byte-identically to S3 `manifest.json` and the field cache
  uploaded with its SHA256 recorded; **canary = the cost-pilot cell (≥ 20
  seeds at one cell, §7) inspected and read out; then STOP and report** to
  Benjamin before the remaining array. Before any submit, check the merged
  `LEDGER.md` and recent PRs for a sibling session's run.

## 7. Cost pilot protocol and pre-declared go/no-go thresholds

**Empirical basis (Phase 1, `CONTAM-PHASE1-FULL-01` / `-PILOT-01`):**
340 trajectories, trajectory wall p95 2.454948 s (max 2.878910 s), peak RSS
100.894531 MiB, trajectory CPU 0.141446 CPU-h (mean 1.498 s per
trajectory), artifacts 10,505,015 bytes (30,897 bytes per cell), 11 field
solves totalling 0.797858 s (max 0.240678 s), per-array wall-clock
2.2–3.5 min at 1 vCPU / 2048 MiB. Per-trajectory time was flat from 9-zone
`destroyer_baseline` to 103-zone `missouri_bb63`, so cost scales with cell
count, not field size, in that range; `mega_cruise_5000` (192 zones, 2,623
entries) is outside it and is why the pilot is on that hull.

**Pilot cell:** block `mega_cruise_5000_e_baseline` — largest hull, solver
lane, 20 paired seeds, 12 × 1 h, 1 vCPU / 2048 MiB. It is the ≥ 20-seed
canary. Field-solve timing for all 32 fields is measured in the local
pre-stage before the pilot submit. Measured: per-field solve wall-clock
(export + subprocess + SIM read), per-trajectory wall-clock, peak RSS,
per-cell bytes, path inventory, alias / dropped-endpoint / unknown-zone
counts, injection connectivity, realized vs declared per-group flows.

**Pre-declared thresholds — GO to the remaining blocks only if all hold:**

| Gate | Limit | Phase 1 reference |
|---|---|---|
| Pilot array SUCCEEDED, `BLOCKED_ENGINE_FALLBACK` count | 20/20, 0 | 20/20, 0 |
| Any single field solve wall-clock (all 32, local) | ≤ 30 s | max 0.240678 s |
| Per-trajectory wall-clock p95 (pilot) | ≤ 60 s | 2.597248 s (pilot) |
| Pilot array wall-clock | ≤ 30 min | 2.199567 min |
| Pilot total CPU-time | ≤ 1.0 CPU-h | 0.0131034 CPU-h |
| Peak RSS | ≤ 1792 MiB | 100.894531 MiB |
| Pilot artifacts (20 cells) | ≤ 25 MiB | 892,670 bytes |
| Dropped endpoints / unknown real zones / alias collisions | 0 / 0 / 0 | 0 / 0 / 0 |
| **Extrapolation bound — predicted full-panel trajectory CPU** `= N_traj × pilot mean per-trajectory CPU` | ≤ 12 × Phase 1 full panel = **1.697352 CPU-h** (i.e. pilot mean ≤ 5.09 s per trajectory for 1,200) | Phase 1 rate predicts 0.4992 CPU-h (1,200) / 0.2330 CPU-h (560) |
| **Extrapolation bound — predicted full-panel artifact bytes** `= N_traj × pilot mean bytes per cell` | ≤ 12 × Phase 1 full panel = **126,060,180 bytes** (≈ 120 MiB) | Phase 1 rate predicts ≈ 37 MB, before the 192-zone `zone_stats` growth |

The Phase 1 "≤ 12 × pilot cell" phrasing is **not** carried over: the Phase 2
pilot is 1/60 of the panel by cell count, so a 12× pilot bound would be
meaningless. The 12× is instead anchored on the measured Phase 1 full panel,
which is the empirical basis Benjamin asked for.

**NO-GO / STOP** if any threshold fails or any E/P field is unavailable for a
cruise hull; message Benjamin with the measured number before any further
submit. Thresholds are frozen in the design file; they are never adjusted
after a measurement.

## 8. Acceptance gates and metrics

Transport-correctness base: `tests/test_contam_analytic_fixtures.py` F1–F6
green on the producer SHA, plus the DC03 fixture if adopted (§11.6).

Phase 2 is **complete** when, and only when:

1. **Coverage:** every planned hull × lane × arm × seed cell landed or is
   classified; P present for all four hulls (or dropped at sign-off); no
   `BLOCKED_ENGINE_FALLBACK` counted as an E/P result; `field_source` is
   `field_cache` for every E/P cell and `native_layout` for every N cell.
2. **Pairing:** for every seed, every arm is present in both N and E for the
   same source realization; P `baseline` uses the same mapping.
3. **Bridge to Phase 1:** `expedition_cruise_450` `baseline` N/E/P cells
   reproduce the Phase 1 `cell_{seed}.json` metrics seed-for-seed (bit-identity
   on `retained_fraction_curve`, `volume_weighted_concentration_burden_h`,
   `zone_stats`); a mismatch is a defect to attribute before any contrast is
   read.
4. **Arm realization:** every arm cell's recorded realized per-group
   settings equal the declared op (59 groups changed, 121 unchanged for
   O/OF/A/R; 0 groups changed for F/G); the DC04 `r_low ∈ [0, 1]` check holds
   on every supply group.
5. **Metrics `readout.py` must emit** (per hull × lane × arm, medians and
   paired contrasts over the 20 seeds, `n` recorded): the Phase 1 set —
   `retained_final`, `b_v_h` (`B_V`), `auc_sum`, `peak_concentration`,
   `source_zone_final_mass`, path-flow inventory by path type — plus
   **DC01** ordering pass counts and violation lists (B_V and per-zone
   `E_i`); **DC02** paired `O − G` on `B_V` and `max_i |ΔE_i|`; **DC04**
   paired `A − R`, `A − B`, `R − B` on `B_V`, reductions `R_a = 1 −
   B_a/B_B` with pairwise gaps, per-zone `ΔE_i` distribution and sign-flip
   zone lists; **DC05** paired `N − E` per arm, arm-effect parity between
   lanes, realized-vs-declared per-AHS flow table; **DC07** source-class ×
   receptor response tables (`E_i(12 h)`/emitted mass; local vs remote;
   p50/p95/max; time-to-peak; first arrival; never-reached count). Near-zero
   baselines are reported as absolute differences, not percentages.
6. **Report-only diagnostics, never selected on:** timing, RSS, path
   inventory, field-solve seconds, audit counts, injection connectivity, the
   Phase 1 cache byte-comparison, and Edison's proposed 5-percentage-point
   "practical tie band" (reported against the `R_a` gaps for information;
   it is not a pass/fail or a selection rule in Phase 2).
7. **No epidemiology:** no occupant dose, breathing rate, attack rate, or
   anchor enters the readout.

Phase 2 does not decide publication claims. Which contrasts "change an
approved decision" is a Kosmos/Benjamin interpretation step on the returned
distributions, not a `readout.py` verdict.

## 9. Edison data-return plan (bounded)

Same pattern as Phase 1 §9: a bounded S3 dump under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase2_cruise_contrasts_01/`
(`AWS_PROFILE=picard`) via the existing `campaigns/` + `scripts/campaign` +
collector pattern. Contents: per-cell `cell_{seed}.json` (Phase 1 schema
family plus an `arm` block with ops, `edits` and realized per-group
settings), `field_cache.json` (32 fields with realized flows and declared-OA
annotations), the byte-identical design `manifest.json` (producer SHA,
job-definition revisions, image digest, lane/arm definitions, source pools,
seed mapping, thresholds), and the committed `readout/phase2_readout.json` +
`READOUT.md`. Per-zone `zone_stats` in every cell already give the
per-zone/per-source tails Edison asks for. Format/schema confirmation is
Phase 4; no Parquet/Kosmos/data-product stack, no raw S3 credentials to
Edison.

## 10. Explicit non-goals

- No epidemiology coupling: no agents, pathogens, dose-response, breathing
  rate, attack rate, VSP/Park anchors, or environmental-detection claims.
- No Ship X adapter (funded, later); no S lane / stock ContamX contaminant
  integration (DC10).
- No DC06, DC08, DC09, DC11, DC12; no 80-platform fleet scope; no non-cruise
  hull reruns.
- No Parquet/Kosmos/data-product stack; no T00–T10 machinery.
- No simulation, campaign file, or AWS submission before Benjamin signs this
  manifest; after sign-off the pilot/canary still STOPs for readout before
  the remaining blocks.
- No `engines/` or `tools/` code change in this PR; the only candidate
  tools change is the §11.1 `scale_ach` scope, decided by Benjamin.
- No fitting of any physical constant to a scored anchor; no threshold
  adjusted after measurement.

## 11. Sign-off decision points

1. **DC04 high-turnover arm:** (a) add `scope` to `scale_ach` in
   `tools/contam_fleet_compare.py` mirroring PR #1169 (`supply_groups`
   default, `all_groups` labelled baseline), as a separate small PR before
   design freeze — recommended; (b) campaign-local versioned op; (c) drop the
   A arm and accept DC04 as unmatched.
2. **Matrix size:** full 7-arm matrix (1,200 trajectories, 60 blocks) with
   the DC01/DC02 controls, or core B/A/R matrix (560 trajectories, 28
   blocks).
3. **P lane:** keep the bounded `baseline`-only P for all four hulls (80
   trajectories, 4 committed-PRJ solves) or drop it for strict N/E.
4. **Tracer and selector:** confirm Phase 1 tracer protocol and source-pool
   selector reused unchanged (no passenger-circulation class, no `λ = 0.1/h`
   sensitivity).
5. **Pilot and thresholds:** confirm `mega_cruise_5000_e_baseline` as pilot /
   canary and the §7 thresholds, including the 12 × Phase-1-full-panel
   extrapolation bound.
6. **DC03:** confirm it is satisfied by a closed-form `tests/` fixture
   (zero trajectories) added at design freeze.
7. **Registry check:** obtain `decisive_contrasts.csv` from Edison and
   reconcile the DC01–DC05/DC07 definitions and the DC09–DC11 assignment in
   §2.5 before freeze; any difference is a manifest amendment, not a silent
   change.
8. **Edison return:** confirm the bounded S3 dump with schema deferred to
   Phase 4.
