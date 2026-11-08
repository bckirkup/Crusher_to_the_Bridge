# CONTAM-PHASE2-AMEND-01
**Date:** 2026-11-08
**Commit:** 94f21379
**Pathogens:** all
**Status:** closed
**Measured at:** db95a4f2b63c3dc115100c7421e1261fcf61bfd7

Amendment of the Phase 2 CONTAM four-cruise contrast manifest §7
(`docs/proposals/contam_phase2_scope_manifest.md`): the pilot's frozen
uniform full-panel extrapolation failed, Benjamin approved a stratified
per-hull cost estimate as the panel-scope expectation, and the full
1,200-trajectory panel is authorized on that basis. Docs-only; no `engines/`,
`tools/`, `campaign.json`, design-JSON, arm-spec or `readout.py` change, no
AWS submission. The entry stays `open` until the full-panel readout
(`CONTAM-PHASE2-FULL-01`, to be written by the panel session) compares the
measured totals with the expectation below.

## Defect class

Pre-declared conservative bound versus measured stratified reality. §7 priced
every one of the 1,200 trajectories at the pilot hull's rate, and the pilot
hull is `mega_cruise_5000` (192 zones, 275 operator nodes) — the largest hull
in either phase, chosen because it lies outside the flat per-trajectory
regime Phase 1 measured up to 108 zones. Only 300 trajectories run on that
hull; 900 run on hulls of 47, 79 and 115 zones. The uniform bound's failure is
an artefact of the pricing rule, not a cost finding.

**Nothing previously measured is void.** The 20 `mega_cruise_5000_e_baseline`
pilot cells in S3 remain valid panel cells and are not rerun; Phase 1
(`CONTAM-PHASE1-PILOT-01`, `CONTAM-PHASE1-FULL-01`) is untouched;
`CONTAM-PHASE2-PILOT-01` stands as measured with pilot gate `go = false` under
the frozen rule.

## Pilot result under the frozen rule (measured at `db95a4f2`)

20/20 SUCCEEDED, `BLOCKED_ENGINE_FALLBACK` 0, audit counts 0 / 0 / 0,
trajectory wall mean 6.342208448 s (p95 6.798478769 s), trajectory CPU
0.0352344914 CPU-h, artifacts 2,197,587 bytes (109,879.35 bytes per cell),
peak RSS 120.667969 MiB, array wall-clock 3.468983 min. Uniform
extrapolations: `1200 × 6.342208448 / 3600 = 2.1140694828` CPU-h vs the bound
1.697352 (12 × Phase 1 full-panel 0.141446); `1200 × 109,879.35 =
131,855,220` bytes vs 126,060,180 (12 × Phase 1 full-panel 10,505,015). Both
failed; every per-pilot threshold passed.

## Stratified estimate

Sources (read-only): the 340 Phase 1 cell artifacts under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_phase1_hvac_tracer_01/`
(measured at `801ea44c`) and the 20 Phase 2 pilot cells under
`.../campaign/contam_phase2_cruise_contrasts_01/mega_cruise_5000_e_baseline/`
(measured at `db95a4f2`); hull zone / HVAC-group counts from
`data/platforms/<hull>/` as frozen in the design `hull_panel`.

Phase 1 per-hull worst-lane block means of `timing.trajectory_seconds`:
`destroyer_baseline` 1.5298 s (9 zones), `fletcher_class_destroyer` 1.4284 s
(33), `expedition_cruise_450` 1.6816 s (47; E 1.6453, N 1.1920, P 1.6816),
`lexington_cv2` 1.6702 s (97), `missouri_bb63` 2.3466 s (103), `saratoga_cv3`
1.6754 s (108). Worst-lane on-disk bytes per cell: 7,178 / 17,027 / 23,479 /
43,567 / 46,297 / 48,209.

Method — CPU: straight-line (chord) interpolation in zone count between the
two measured cruise anchors, `expedition_cruise_450` 1.6816 s at 47 zones
(Phase 1) and `mega_cruise_5000` 6.3422 s at 192 zones (Phase 2 pilot), slope
0.03214238 s per zone. Every Phase 1 hull inside that interval lies well below
the chord (97–108 zones measured 1.67–2.35 s where the chord gives 3.29–3.64
s), so the chord is an upper envelope for the interior hulls, not a central
estimate. The node-count chord gives lower values (`classic` 2.5865 s,
`spirit` 3.7404 s) and is not used. Bytes: per cell `3,566.7 + 414.00 × zones`
(least-squares fit on the six Phase 1 worst-lane hull means, max residual
455 bytes) plus 30,031 bytes of Phase 2-only content (`ahs_flow_table`
18,175 + `arm_record` 11,749 + `arm` + `field_sha256`, identical on all 20
mega pilot cells, applied in full to every hull); the model predicts 113,086
bytes for mega against 109,879 measured (+2.9 %); the measured value is used
for mega.

| Hull | Zones | Nodes | Trajectories | Trajectory s (provenance) | CPU-h / trajectory | Hull CPU-h | Bytes / cell (provenance) | Hull bytes |
|---|---:|---:|---:|---|---:|---:|---|---:|
| `expedition_cruise_450` | 47 | 69 | 300 | 1.6816 (measured, Phase 1 worst lane) | 0.0004671 | 0.14013 | 53,056 (Phase 1 fit + Phase 2 extras) | 15,916,714 |
| `classic_cruise_1900` | 79 | 109 | 300 | 2.7101 (interpolated, zone chord) | 0.0007528 | 0.22584 | 66,304 (model) | 19,891,107 |
| `spirit_cruise_3000` | 115 | 160 | 300 | 3.8672 (interpolated, zone chord) | 0.0010742 | 0.32227 | 81,208 (model) | 24,362,299 |
| `mega_cruise_5000` | 192 | 275 | 300 | 6.3422 (measured, Phase 2 pilot) | 0.0017617 | 0.52852 | 109,879 (measured, Phase 2 pilot) | 32,963,805 |
| **Panel point estimate** | | | **1,200** | | | **1.216761** | | **93,133,925** |
| **Panel expectation (× 1.5 safety factor)** | | | **1,200** | | | **1.825142** | | **139,700,888** (≈ 133.2 MiB) |

Remaining 59 blocks (1,180 trajectories): 1.181527 CPU-h / 90,936,338 bytes
point estimate; 1.789907 CPU-h / 137,503,301 bytes after subtracting the
measured pilot block from the × 1.5 expectation. The uniform rule's
2.1140694828 CPU-h / 131,855,220 bytes are 1.74× / 1.42× the stratified
point estimate.

Assumptions (declared, not fitted): N and P lanes priced at each hull's worst
measured lane (Phase 1: N ≤ E on every hull except `saratoga_cv3`, N/E
1.017; P tracked E); arm ops change operator coefficients, not dimension, so
cost is arm-independent (pilot is `baseline`); expedition anchor epoch parity
verified — both designs `epochs = 12`, `epoch_hours = 1.0`, identical tracer
block (`unchanged_from_phase1: true`), identical `expedition_cruise_450`
source pool and seed mapping, Phase 2 fields byte-identical to the Phase 1
cache, Phase 2 worker reproduced Phase 1 expedition N seeds 1 and 14
bit-identically; safety factor 1.5× is a declared margin for Spot instance
heterogeneity (Phase 1 per-array wall-clock 2.93–3.50 min), pilot p95/mean
1.072, the unmeasured mega N/P lanes and the ~3 % bytes-model error.

Sanity context: roughly two CPU-hours on AWS Batch Spot and 130–140 MB in S3
are trivial costs; the estimate exists for honest accounting, not budget. The
pre-declared stop rule for this amendment (report instead of amend if the
expectation exceeded ~3 CPU-h or ~300 MB) was not triggered.

## Decision

Benjamin, 2026-11-08 (explicit): amend §7 with the stratified estimate,
ledgered here, then run the full 1,200-trajectory panel — the 59 remaining
blocks — in a separate session after this amendment merges. The panel-scope
expectation is **≤ 1.825142 CPU-h trajectory CPU and ≤ 139,700,888 artifact
bytes** for the full panel; it replaces the uniform 12× bound for panel scope
only. The full-panel readout must report the measured totals against both
this expectation and the historical uniform bound; exceeding the expectation
is a ledgered finding, not a reason to revise it. Pilot-gate thresholds,
`design/phase2_cruise_contrasts_design.json`, `campaign.json`, arm specs and
`readout.py` are unchanged.

## Closure

Closed by `CONTAM-PHASE2-FULL-01` (2026-11-08): the completed panel's measured
trajectory CPU and artifact bytes are recorded there against the point
estimate, the ×1.5 expectation above, and the historical uniform bound; the
expectation was not exceeded.
