# CONTAM-vs-native HVAC Phase 1 thin scope manifest

> **Status:** Proposed — awaiting Benjamin sign-off; no simulation, campaign,
> AWS submission, code change, Ship X adapter, S lane, or epidemiology coupling
> is authorized by this document.
> **Filing:** `docs/proposals/` per the `docs/README.md` filing rule; the panel
> artifact does not exist yet. Verified against `origin/main` `c5f4ea97`.

## 1. Purpose and authority

This manifest freezes the thinned Phase 1 scope for the Edison Scientific
publication on CONTAM-vs-native HVAC airflow-representation impact on ship
epidemiology simulations. Phase 1 is a **tracer-only mechanism panel**: it tests
whether field generation (native heuristic HVAC vs ContamX-solved commissioned
export, with committed PRJ as a bounded authoring contrast) changes tracer
transport enough to matter mechanically, before any coupled epidemiology is
considered.

Settled inputs, not re-derived here: Phase 0 is complete on `main`
(`tests/test_contam_analytic_fixtures.py` F1–F6, PR #1166; arm-integrity fixes
PR #1169; AHS declared-OA fix PR #1170). The Edison protocol/handoff
attachments are alignment proposals only; where they conflict with the settled
scope below, the settled scope governs. In particular, the nominal
120-trajectory Cartesian panel and the T00–T10 implementation spec are **not**
adopted.

## 2. Scope and lane definitions

Phase 1 compares airflow-field generation for an identical tracer source,
propagated by the same Crusher mass operator. It has no stochastic agents, no
pathogen coupling, no epidemiological constants, and no VSP/Park/attack-rate
anchor.

| Lane | Field generation | Propagation / permitted claim |
|---|---|---|
| **N — native** | Prescribed star-HVAC + passive/cross-zone heuristic flows from `spatial_layout.json` + `air_flow_paths.json` | `engines/py_contam_bridge.py` matrix-exponential mass propagator. Not a pressure-network ground truth. |
| **E — commissioned export** | Fresh `export_prj_with_path_map(..., filter_efficiency=0.5, ahs_terminal_mode="commissioned")`, `_annotate_ahs_declared_oa`, ContamX solve, `engines/contamx_ahs_bridge.py` AHS synthesis | `ContamXTransportEngine` inherits the same `py_contam_bridge` propagator. Tests operational mapping and field generation only. |
| **P — committed project** | Checked-in `contam/platform.prj` + `contam/path_map.json` as authored, baseline only, only where present | Same bridge after PRJ parsing/path-map normalization. Difference includes authoring, geometry, schedule, mapping, and field. Cannot represent JSON-only mutations; Phase 1 has none. |
| **S — stock ContamX contaminant integration** | **Excluded from Phase 1** | Later time-boxed attempt for the independent-solver claim. |

**Lane honesty:** N, E, and P share the `engines/py_contam_bridge.py`
`expm` mass propagator (`ContamXTransportEngine` subclasses
`ContamTransportEngine`). Agreement among N/E/P is **not** independent
contaminant-solver validation; it isolates field generation only. Any
independent-solver claim is deferred to the later S-lane attempt.

Machinery reused: `tools/contam_fleet_compare.py` field builders/arm runner
(`_contamx_field`, `_native_engine`, `_contamx_engine`, `_cell_summary`,
`_divergence`), `engines/contamx_transport.py`, `engines/contamx_runner.py`,
`engines/contamx_ahs_bridge.py`, and the existing `campaigns/<pathogen>/<name>/`
+ `scripts/campaign` + reducer/collector infrastructure. No new
Parquet/Kosmos/data-product stack.

## 3. Six-hull early mechanism panel

| Hull | Zones | Volume (m³) | HVAC groups | Rooms served | Cross-zone links | Adjacency links | `contam/path_map.json` entries | Committed PRJ | Phase 1 lanes | Provenance status / note |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| `destroyer_baseline` | 9 | 692.26 | 6 | 9 | 6 | 6 | 69 | yes | N/E/P | Baseline mechanism hull; committed fiction Contam bundle. |
| `expedition_cruise_450` | 47 | 19358.98 | 22 | 46 | 17 | 48 | 343 | yes | N/E/P | Supersedes legacy `expedition_cruise_300`; one HVAC-unserved zone (`PoolDeck`) remains a remote candidate. |
| `fletcher_class_destroyer` | 33 | 2295.67 | 20 | 33 | 22 | 24 | — | **no** | **N/E only** | WWII Fletcher-class DD-445 class hull, forced-draft ventilation, no HVAC filtration, hot-bunking. No committed `contam/` bundle: E uses fresh commissioned export; P is unavailable. |
| `lexington_cv2` | 97 | 47482.60 | 6 | 8 | 5 | 154 | 300 | yes | N/E/P | CV-2 1941; many zones are outside `hvac_zones[].rooms` and reach air through adjacency/airflow paths. |
| `saratoga_cv3` | 108 | 54494.07 | 6 | 8 | 5 | 163 | 320 | yes | N/E/P | CV-3 wartime fit, sister hull to CV-2. |
| `missouri_bb63` | 103 | 151331.55 | 11 | 103 | 10 | 122 | 2248 | yes | N/E/P | Iowa-class BB-63; largest panel hull by volume/path-map and the cost-pilot hull. |

**Provenance exception to decide at sign-off:** the settled verification
criterion named `contam/path_map.json` for every hull. `fletcher_class_destroyer`
has `spatial_layout.json` and `air_flow_paths.json` but no `contam/` directory.
The E lane does **not** require the committed bundle — it is generated fresh by
the commissioned export — but P is impossible for Fletcher and there is no
committed Contam provenance artifact for that hull. If Benjamin requires
committed Contam provenance for all six hulls before sign-off, Fletcher needs a
bundle first; otherwise Phase 1 proceeds with Fletcher as N/E only.

Inclusion/exclusion justification:

- `expedition_cruise_300` — excluded: legacy archived platform, superseded by
  `expedition_cruise_450` for cabin-corridor resolution; no Contam bundle.
- `fletcher_dde_dd445` — excluded from Phase 1: DDE conversion study drawing
  with thin import above the first platform; an alternate-fidelity variant, not
  the Fletcher-class mechanism hull.
- `saratoga_cv60` — excluded from Phase 1: Forrestal-class post-SLEP 1993
  configuration, a different class/era from the CV-2/CV-3 wartime carrier pair.
- `classic_cruise_1900`, `spirit_cruise_3000`, `mega_cruise_5000` — excluded:
  cruise archetypes reserved for the Phase 2 cruise contrasts despite having
  Contam bundles.

## 4. Exact run matrix

Primary confirmatory matrix is N/E only:

- Hulls: 6
- Lanes: 2 (`N`, `E`)
- Seeds: 20 paired seeds per hull×lane (`seed = 1..20`; the same seed selects
  the same source realization in every lane)
- Epochs per trajectory: 12
- Epoch hours: 1.0 (12 physical hours; the hourly flow basis of the transport
  paths)
- Trajectories: `6 × 2 × 20 = 240`
- Hourly transport steps: `240 × 12 = 2880`
- ContamX field solves: 6 E-lane solves (one per hull, reused across seeds);
  native needs no external solve.

Bounded P authoring contrast, included only because existing machinery already
emits `contamx_committed` at baseline:

- Hulls: 5 (all panel hulls except `fletcher_class_destroyer`)
- Lane: P, baseline only
- Seeds/epochs/epoch-hours: same 20 × 12 × 1.0
- Additional trajectories: `5 × 20 = 100`; total with P = 340 trajectories /
  4080 hourly steps; additional field solves = 5 committed-PRJ solves.

If Benjamin wants strict N/E only at sign-off, drop P; the N/E matrix is
unchanged at 240 trajectories.

## 5. Tracer injection protocol

- Tracer mass: `1,000,000` tracer units per seed, normalized by emitted mass
  (`1e6`); concentrations are tracer mass / zone volume. No pathogen titre, no
  epidemiological constant.
- Decay/removal for the primary matrix: `natural_decay_rate = 0.0`
  (conservative chemical/particulate surrogate). The optional `0.1/h` model
  removal sensitivity is **not** in the Phase 1 primary matrix.
- Filtration: shipped baseline `filter_efficiency = 0.5` on ducted paths for
  both N and E; no filter arms.
- OA/recirculation: platform-declared `air_flow_paths.json` values and per-AHS
  declared OA after PR #1170; no `set_oa`, ACH, duty, isolation, or hatch arms.
- Source pool per hull: up to 10 zones selected only from platform metadata —
  up to 4 `large_venue`, up to 3 `sanitary_branch`, up to 3 `remote_weak`.
  Selection is deterministic (volume/type/id/HVAC-service/duty/adjacency
  degree; tie-break by zone id) and is materialized in the campaign design file
  before any cell runs. No selector may use VSP, Park, attack-rate, or any
  scored anchor.
- Seed → source mapping: for seed `s`, let `k = s - 1`; timing pattern is
  `k mod 2` (`0 = t0_pulse`, `1 = t0_t1_split`); zone is
  `pool[(k // 2) mod len(pool)]`. For a 10-zone pool, seeds 1–20 enumerate
  every zone with both timing patterns exactly once. For smaller pools the
  mapping cycles deterministically; effective unique realizations are
  `min(20, 2 × len(pool))`, and repeated seeds are deterministic repeats for
  canary/reproducibility, not new information.
- Timing patterns: `t0_pulse` injects `1e6` at `t = 0`; `t0_t1_split` injects
  `500,000` at `t = 0` and `500,000` at `t = 1 h` (added after the first hourly
  transport step). Both are inside the 12 h horizon; there is no continuous
  source.

## 6. Machinery and campaign gates

Execution, after sign-off only, must reuse the fleet-compare field builders and
the existing campaign grammar. A thin campaign worker may be added under the
campaign namespace at design freeze; this PR adds no campaign files and changes
no `engines/` or `tools/` code. If `scripts/campaign` does not admit a
non-pathogen tracer namespace, the closest grammar-admissible namespace is
chosen at design freeze without touching engines/tools.

Before any AWS submission, campaign-preflight Rule A applies: admissibility,
selectors, thresholds, and report-only diagnostics are frozen in the design
file before the first cell runs. Required gates: geometry/seed gate validated;
local smoke proves the config override reaches the engine and the output
contract is unchanged; `--dry-run` count matches the design; pinned job-definition
revision and image digest; manifest present in S3; one canary child inspected;
then the array with an ETA. AWS Batch only (`AWS_PROFILE=picard`), never the
local box for campaigns. After the canary readout, STOP and report before the
full panel.

## 7. Cost pilot protocol and pre-declared go/no-go thresholds

Cost pilot = the `missouri_bb63` × lane E cell: largest panel hull by zones,
volume, and path-map entries, and the only lane with external solver cost. It
uses the same 20 paired seeds, 12 epochs, and 1 h epoch length, and doubles as
the ≥20-seed canary cell. It runs on AWS Batch at 1 vCPU / 2048 MiB per child
after the campaign gates above.

The pilot measures: ContamX commissioned-export field-solve wall-clock
(export + subprocess + SIM read), per-trajectory wall-clock for N/E transport,
peak RSS memory, per-cell and total artifact bytes, path inventories, alias /
dropped-endpoint / unknown-zone counts, and injection connectivity.

Pre-declared thresholds — **GO** to the remaining panel only if all hold:

- pilot cell SUCCEEDED with no `BLOCKED_ENGINE_FALLBACK`;
- E field solve wall-clock ≤ 30 s;
- per-trajectory wall-clock p95 ≤ 60 s;
- pilot cell array wall-clock ≤ 30 min at the stated resources;
- pilot total CPU-time ≤ 1.0 CPU-hour;
- peak RSS ≤ 1792 MiB (headroom under the 2048 MiB request);
- pilot artifacts ≤ 25 MiB total;
- no dropped endpoints, unknown real-zone IDs, or alias collisions; any
  isolated injection zone is a declared `remote_weak` candidate and is
  reported, not silently dropped.

**NO-GO / STOP** if any threshold fails or the E field is unavailable for
`missouri_bb63`; message Benjamin with the measured number before any further
submit. A conservative extrapolation is `full panel ≤ 12 × pilot cell` because
Missouri is the largest hull and E is the only solver-cost lane; P adds at most
five committed-PRJ solves bounded by the same envelope. The fleet ledger
(`CONTAM-FLEET-01`) already bounds field solves at median 90 ms / max 588 ms and
propagation at parity, so infeasibility is not expected; the pilot replaces that
fleet median with a measured worst-case hull number before committing the array.

## 8. Acceptance gates and metrics

Transport-correctness base: `tests/test_contam_analytic_fixtures.py` F1–F6
closed-form controls for `engines/py_contam_bridge.py` must be green on the
producer SHA. Phase 1 does not rerun them as simulations; it cites them as the
correctness base for the shared propagator.

Phase 1 panel is **complete** when, and only when:

1. Coverage: every planned N/E cell landed or was classified; P cells landed
   for the five hulls with committed PRJ or P was explicitly dropped at
   sign-off; `fletcher_class_destroyer` P is unavailable by design, not a
   failure; no `BLOCKED_ENGINE_FALLBACK` is counted as an E/P result.
2. Pairing: for every seed, N and E are present for the same source
   realization; P, where present, uses the same seed mapping.
3. Metrics per hull×lane are computed: retained-fraction curve over the 12 h
   horizon; per-zone concentration statistics (time-integrated concentration,
   final and peak concentration, time-to-peak, arrival above the numerical
   floor); exposure proxies (source-normalized volume-weighted concentration
   burden `B_V`, source-to-receptor contrasts, path-type flow differences). No
   occupant dose is computed because no breathing rate is declared.
4. N-vs-E comparison is reported as paired seed differences with a 95%
   interval across the 20 paired seeds. Seed variance here measures the
   declared source-realization ensemble and any numerical nondeterminism; it
   is not agent/pathogen stochasticity.
5. Report-only diagnostics are never selected on: timing, path inventory,
   field-solve seconds, alias/dropped-endpoint counts, injection connectivity.

Phase 1 does **not** decide the publication claims. Coupled epidemiology —
norovirus null and respiratory epidemiology/environmental detection — is the
Phase 3 decision gate, not Phase 1.

## 9. Edison data-return plan (bounded)

Phase 1 returns a bounded S3 dump under the existing campaign prefix
(`s3://crusherbucket-994254241749-us-east-1-an/campaign/<design>/`,
`AWS_PROFILE=picard`) using the existing `campaigns/` + `scripts/campaign` +
reducer/collector pattern (`.github/workflows/campaign_collect.yml`; see the
edison-aws-bridge pattern already proven in this repo). Contents: per-cell
summary sidecars, slim per-cell metrics (retention curve, concentration
statistics, exposure proxies, divergence, timing, path-inventory/alias audit),
and a machine-readable run manifest (producer SHA, job-definition revision,
image digest, lane definitions, source-pool materialization, seed mapping,
thresholds). Full per-epoch per-zone frames are optional and only if the pilot
artifact threshold passes. Format/schema is confirmed by Edison in Phase 4; no
Parquet/Kosmos/data-product stack is built for Phase 1, and no raw S3
credentials are handed to Edison.

## 10. Explicit non-goals

- No Ship X adapter (funded, but later).
- No S lane / stock ContamX contaminant integration.
- No epidemiology coupling: no agents, pathogens, dose-response, attack rate,
  VSP/Park anchors, or environmental-detection claims.
- No Phase 2 cruise contrasts and no expansion to the excluded variants/hulls.
- No simulation, campaign, or AWS submission before Benjamin signs this
  manifest; after sign-off, the cost pilot/canary still stops for readout
  before the full panel.
- No code changes to `engines/` or `tools/` in this PR; no new Parquet/Kosmos/
  data-product stack.
- No fitting of any physical constant to a scored anchor.

## 11. Sign-off decision points

1. Confirm the six-hull panel and the Fletcher provenance exception (N/E only,
   or require a committed Contam bundle first).
2. Confirm P as a bounded baseline-only authoring contrast for five hulls, or
   drop it for strict N/E.
3. Confirm the 20 paired seeds as a source-realization ensemble (not agent
   stochasticity) and the frozen go/no-go thresholds in §7.
4. Confirm the bounded Edison return format is acceptable to defer exact schema
   confirmation to Phase 4.
