# Sonar backlog sweep — handoff (2026-09-26)

**Status: handoff record.** This is a maintenance-sweep handoff, not a science
ledger: it reports no model numbers. Every issue count below is quoted from a
live SonarCloud scan (`bckirkup_Crusher_to_the_Bridge`, sonarcloud.io) at the
stated commit.

## The task

User directive: clean up the SonarQube backlog on `main` — the one security
issue plus the maintainability mass — end-to-end across four workstreams:
(1) flagged items, (2) mechanical sweep, (3) S107 parameter-count refactors,
(4) the S3776 cognitive-complexity backlog in batched PRs.

Success = open-issue count driven to ~0 with the quality gate green on every
PR; mechanical fixes kept in dedicated PRs per AGENTS.md.

## State of play (live scan, 2026-09-26, main @ bc0230e6+)

- Start: 246 open issues.
- Now: **97 open** — all `python:S3776` (the S107s closed when #706
  merged; an earlier scan raced the post-merge re-analysis).
- 3 PRs merged for workstreams 1–3 (#701, #703, #704), plus #706 (S107) and
  #708 (sanity_checker S3776 batch).
- ~40 issues closed without code (S116 ×9 boundary field names accepted;
  S5655, S7504 marked false-positive — genuine Sonar inference artifacts).

## PRs landed this session, in dependency order

| PR | Content |
|----|---------|
| #701 | Flagged items: `--out` path clamp (S8707), single-exit wrappers (S3516 ×2); S5655 marked FP |
| #703 | Test sweep: S5778 ×82 `pytest.raises` single-invocation + misc (~94 issues) |
| #704 | Source sweep: S7519/S1192/S3358/S7504/S7517/S1940/S1172 (~20 issues) |
| #706 | S107 ×9: config objects (`ScreenRunParams`, `ZoneContext`, `EpochRecordRequest`, `SyndromicParams`, …) |
| #708 | S3776 batch 1: `tools/sanity_checker.py` 14 hotspots (child session 72fd71ef…) |

## Open PR

| PR | Content | Status |
|----|---------|--------|
| #710 | S3776 batch 2: tools diagnostics (`covid_route_attribution`, `contam_flow_compare`, `contam_engine_compare`, `contam_outcome_compare`, `contam_prj_bridge`, `hand_occupancy_readout`) + new coverage tests | CI green; 2 S2583s on it marked FP (dispatch-mutation invisible to analyzer); awaiting merge |

## Running child sessions (own the batches; do not re-do)

| Session | Batch | Issues |
|---------|-------|--------|
| https://app.devin.ai/sessions/8826a02918404b788ff696745cc477e0 | `engines/transmission_core.py` | 10 |
| https://app.devin.ai/sessions/87e040ec1fa841328d217d8b6c36c8c8 | `orchestrator_epoch/init/chronic/display` | 11 |

## Queued batches (spawn-blocked: free SWE-2 cap is 5 sessions)

When a slot frees, spawn with `devin_mode="swe-2-high"`, repo
`bckirkup/Crusher_to_the_Bridge`, branch `devin/$(date +%s)-sonar-s3776-<area>`
off `origin/main`. Per-child prompt = settled inputs / deliverable / non-goals /
validation gate / report-if / stop-when; rules: pure extraction, zero behavior
change, preserve RNG draw order, every new function ≤15 CC, shallow-first,
skip-and-report.

- **picard_framework ×19** — `analysis/vsp_degradation_postprocess` (54, 103,
  140, 241, 468), `analysis/synthetic_recovery_postprocess` (60, 616, 947),
  `analysis/metrics` (125, 236), `analysis/parse_run_id` (79, 186),
  `analysis/{campaign:212, export_outbreak_surface:240, pairwise:85,
  report:57, stan/_data:155}`, `runs/mega_cruise_campaign/{boarding_axis:569,
  campaign_execution:722,1507, count_manifest_cartesian:56}`,
  `simulation/ship_simulation:312`.
- **engines-rest ×18** — `infection_dynamics_bridge` (952, 1744, 2133, 2278),
  `initiation` (939, 1645, 1732), `wearable_monitor` (581, 701, 925),
  `voyage_itinerary` (251, 466), singles in `contamx_ahs_bridge:34`,
  `contamx_transport:108`, `engine_paths:96`, `fomite_surfaces:264`,
  `natural_history:451`, `py_contam_bridge:517`. Exclude
  `transmission_core.py` (owned).
- **tools+labs ×~22** — `noro_diag/per_host_dose_challenge` (362, 460, 551,
  831, 1357), `noro_diag/observation_channel_funnel` (220, 311),
  `ship_blueprint_import/{author_contam:76,166,215, validate:23,87,
  svg_io:59,199, synthesize:123,234}`, `gis_spatial_bridge` (100, 193, 252,
  429), `contamw34_prj:1976`, `crusher_labs/{clinical_correlation:170,
  clinical_instrument_params:155, long_read_escalation:147,
  modalities/syndromic:320,1133, observation_core:1598}`,
  `telemetry_buffer/observation_model/bounded_screen:865`. Exclude the six
  files owned by open PR #710 (`covid_route_attribution`,
  `contam_flow_compare`, `contam_engine_compare`, `contam_outcome_compare`,
  `contam_prj_bridge`, `hand_occupancy_readout`) until it merges — the
  remaining S3776s in those files ride along in it.

## Findings worth keeping (Sonar mechanics)

- **New-code coverage gate counts moved lines.** Extraction dragged previously
  uncovered branches (e.g. ContamX-binary paths) into the ≥80% gate. Fix:
  targeted unit tests for extracted helpers (dict-driven/monkeypatched is fine
  for binary-dependent code). Done on #710.
- **S2583 "always empty/false" FPs from extracted dispatchers.** Sonar can't
  see mutation through a callable table inside a helper. Mark
  `change_sonar_issue_status {key, status:"falsepositive"}` — don't restructure
  working code to satisfy the analyzer.
- **S5778 hoist:** with `pytest.raises`, any constructed argument (e.g. a
  dataclass) must be built ABOVE the `with` block; two callables inside
  re-triggers the rule.
- **S3776 count moved 87→97 despite 14 closed** — net +24 net new-code
  findings since 2026-08-28 (moved lines + extraction helpers re-scanned). The
  ceiling only ratchets on `main`; trust live scans, not stale counts.

## The single open decision

Nothing conceptual — pure scheduling: spawn the three queued batches when
SWE-2 slots free, then a final live scan and (if any S3776 remains) a
cleanup batch. 
## Do not reopen

- Do not tune any epidemiological constant, do not loosen the C901=56 ceiling
  or the ≤15 new-code bar, do not rename the accepted `C_screen`/`C_case`
  boundary fields, do not modify tests to make them pass.
- Do not "fix" the S2583 FPs by restructuring the working dispatcher; the
  Sonar statuses are recorded.
