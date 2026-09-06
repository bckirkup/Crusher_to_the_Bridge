# Draft remediation tranche map for Devin/Cursor

Baseline: `07561adf2b93ff6b358859fb382b253c08828156`. This is a planning extraction from r11, not an implementation request or evidence of a fix.

## A — Prevent silent scientific misconfiguration

### ARCH-01 — Run-spec schema is not enforced at runtime: version 999, zero/negative epochs, string 'false' coerced to True, unknown retention category silently falls back to 'full'.
- **Consequence:** Invalid configurations accepted silently; bool('false')=True can invert scientific behavior.
- **Remediation:** Validate with Pydantic or JSON Schema at loader boundary; reject unknown versions and wrong types.
- **Acceptance test:** RunSpec with version 999, epochs=-1, or write_ground_truth='false' each raise ValueError.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r4/run_spec_contract_probe.json` $.probes[*] (named cases: schema_version_999, negative_epochs, string_false, invalid_retention)

### DIM-01 — Food ingestion fraction is per-epoch (0.05/agent/epoch), giving resolution-dependent pool depletion: 1h grid consumes 14.16x the 24h-grid amount in 24 physical hours.
- **Consequence:** Silently changes scientific results when epoch width changes; all cross-resolution comparisons are invalidated for food-borne route.
- **Remediation:** Rename to food_ingestion_fraction_per_day; derive per-epoch via clock.decay_per_epoch; add cross-grid invariance test.
- **Acceptance test:** Pool remaining after 24h at 1h, 6h, 24h grids agrees within 1e-6.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r2/synthetic_scale_test_results.json` food_pool_remaining_after_24h

### DIM-02 — SimClock accepts NaN and +∞ as epoch_duration_hours because __post_init__ checks only <= 0.
- **Consequence:** NaN/∞ propagate through probability, decay, and accumulation helpers, yielding nonsensical simulation state without error.
- **Remediation:** Add math.isfinite guard in __post_init__; test NaN, +inf, -inf constructors.
- **Acceptance test:** SimClock(NaN,...) and SimClock(inf,...) both raise ValueError.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r2/nonfinite_clock_reproduction.txt` nonfinite_clock_reproduction.txt: lines 1-4

### DIM-03 — Negative physical delays/durations silently clamp to zero epochs via max(0,...) in epochs_for_hours/days.
- **Consequence:** Sign error or unit-entry error becomes instantaneous operation instead of raising.
- **Remediation:** Reject negative canonical physical inputs with ValueError at config boundary.
- **Acceptance test:** config_epochs_for_hours(-2) raises ValueError.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r2/boundary_and_calendar_scale_tests.txt` negative delay tests

### STAN-04 — sentinel_fleet.stan data contract incomplete: allows T[v]>Tmax, wastewater epochs beyond T[v], all-zero simplex raw vectors (division by zero), ww_reads>ww_total.
- **Consequence:** Python builders may prevent some cases, but Stan program accepts invalid data directly.
- **Remediation:** Add dependent bounds and transformed-data reject() checks for cross-field invariants.
- **Acceptance test:** Stan data block with T[v]>Tmax, zero simplex, or reads>total triggers reject() statement.
- **Evidence:** `/workspace/Crusher_to_the_Bridge/picard_framework/analysis/stan/sentinel_fleet.stan` lines 153-220

## B — Make runs immutable and content-addressed

### CAMP-01 — Run archive does not contain pinned SHA, source manifest, dependency lock, resolved environment, runtime platform, input hashes, effective config, start/end timestamps, commands, output hashes, or campaign identifier. Only seed is captured.
- **Consequence:** Runs cannot be independently reconstructed or attributed to a specific source/environment.
- **Remediation:** Implement mandatory signed/hashed campaign and per-run manifests with all listed fields.
- **Acceptance test:** Every run archive contains run_manifest.json with all 13 provenance fields populated.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r6/provenance_capture_audit.json` 12/13 checks failed

### CAMP-02 — Overwrite prevention failed: re-running without --resume against existing output exits 0, rewrites ZIP, appends duplicate completed_runs line.
- **Consequence:** Irrecoverable lineage loss; prior run evidence destroyed without warning.
- **Remediation:** Refuse nonempty destination unless explicit --force-new-attempt; immutable run directories.
- **Acceptance test:** Re-run without --resume or --force exits non-zero; original ZIP unchanged.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r6/overwrite_prevention_test.json` $.exit; $.refused_overwrite; $.changed_files; $.completed_runs_lines

### CAMP-03 — Stale-cache detection failed: changed HVAC filter efficiency from 0.50 to 0.85 while preserving run ID; --resume skipped the cached run without warning.
- **Consequence:** Configuration change invisible to resume gate; scientifically wrong results reused.
- **Remediation:** Compute run_fingerprint from SHA256(effective config + source hash + input hashes + seed); resume only on exact fingerprint match.
- **Acceptance test:** Changed filter efficiency with same run_id: --resume exits non-zero with fingerprint mismatch message.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r6/stale_cache_test.json` $.manifest_change; $.exit; $.artifact_changes; $.cached_run_spec_filter_efficiency

### CAMP-04 — Campaign identifier is discarded: changing top-level manifest 'campaign' field produced byte-identical internal outputs; campaign ID appears nowhere in run archives.
- **Consequence:** Renamed/iterated campaigns collide in namespace; cannot distinguish runs from different campaigns.
- **Remediation:** Include immutable campaign UID and human slug in run IDs, paths, manifests, and shard keys.
- **Acceptance test:** Run archive run_spec.json contains campaign_uid field matching parent manifest.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r6/repeatability_comparison.json` changed_campaign section

### PROV-03 — Effective merged configuration is not captured in run output; only selected overrides appear in run_spec.json.
- **Consequence:** Cannot reconstruct what defaults/overrides produced a given result; drift in config.yaml is invisible.
- **Remediation:** Serialize fully resolved effective config after all merge steps; hash and embed in run archive.
- **Acceptance test:** run archive contains effective_config.json whose SHA-256 is recorded in run_manifest.json.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r6/provenance_capture_audit.json` checks.complete_effective_configuration: false

### CAMP-07 — No exploratory/confirmatory/revision/review-response separation as campaign metadata; no run_intent, paper_id, analysis_plan_id, or review_response_id field.
- **Consequence:** Post-hoc exploratory results can silently enter confirmatory claims; no immutable campaign lifecycle.
- **Remediation:** Add controlled run_intent enum and stage gates; distinct immutable roots and permissions per intent.
- **Acceptance test:** Campaign manifest requires run_intent field from {exploratory,confirmatory,revision,review_response}.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r6/ASSESSMENT.numbered.txt` lines 123-124

## C — Repair installed execution and analysis contracts

### PKG-01 — Wheel build omits simulation_utils, orchestrator.py, presidio_runner.py; both declared console scripts fail with ModuleNotFoundError after non-editable install.
- **Consequence:** Published/installed distribution is non-functional; users cannot pip-install and run the declared entry points.
- **Remediation:** Include simulation_utils in packages; package CLI modules or move them under a package; add wheel-install CI smoke test.
- **Acceptance test:** pip install dist/*.whl in empty venv; crusher-orchestrator --help exits 0; import simulation_utils succeeds.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r0/wheel_contents.txt` wheel_contents.txt:all; command_installed_cli_orchestrator_help.log

### ARCH-02 — Analysis fit artifact directories have no manifest/schema/version gate; duplicate rows silently plotted; malformed hazard_mean fails late in Matplotlib.
- **Consequence:** Scientific figures can include duplicate/corrupt data without detection.
- **Remediation:** Define per-CSV table contract; validate primary keys, types, nullability before figures.
- **Acceptance test:** Duplicate-row CSV raises ValueError at artifact load; missing hazard_mean raises at artifact load, not at plot time.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r4/artifact_contract_probe.json` $.probes[*] (named cases: missing_hazard_mean, malformed_hazard_mean, duplicate_row)

## D — Repair inference semantics

### DIM-07 — Trajectory Stan data builder pools runs with different physical epoch widths without carrying or normalizing time.
- **Consequence:** Mixed-grid inference treats epoch indices as comparable when their physical meaning differs.
- **Remediation:** Require single epoch_duration_hours across all rows; fail if absent or inconsistent.
- **Acceptance test:** Builder raises ValueError when fed 1h and 6h runs together.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r2/stan_mixed_grid_reproduction.txt` stan_mixed_grid_reproduction.txt: lines 1-3

### STAN-03 — synthetic_recovery_latent cannot separately identify dose_adj and the free intercept: the likelihood is invariant along their ridge. Fresh r9 posterior dependence was corr=0.9312 under pinned priors and 0.9796 after widening intercept prior SD 1→3; only intercept - beta_d_fixed*dose_adj remained tightly identified.
- **Consequence:** Passing smoke diagnostics does not permit a separate dose-recovery claim; the marginal dose posterior location is prior-anchored along the ridge.
- **Remediation:** Fix intercept, supply external anchor, or use data where dose varies within a joint model.
- **Acceptance test:** SBC with simulated data shows dose_adj 95% intervals have correct coverage (not prior-width).
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r9/latent_prior_sensitivity.json` $[0] plus runs/synthetic_recovery_latent/result.json $.latent_dependence

## E — Establish fresh evidence and paper gates

### LEG-01 — 0/63 sampled legacy run archives contain source-commit or environment metadata; token compatibility (profile/platform names) present but not sufficient for SHA attribution.
- **Consequence:** Legacy outputs cannot be attributed to pinned SHA; must not be used for calibration, validation, or publication claims.
- **Remediation:** Quarantine legacy outputs; retain for historical factor recovery only; run fresh campaigns with provenance.
- **Acceptance test:** No legacy archive is cited as evidence in any publication figure or table.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r7_recovery/legacy_evidence_recovery_report.line_numbered.md` lines 62-73

### LEG-02 — Committed CmdStan outputs (sentinel_fleet 4 fits) are legacy evidence: one-chain, 200 draws, NaN rejections, no between-chain convergence. These are in the pinned tree but do not constitute valid inference.
- **Consequence:** Treating committed fit outputs as validated posteriors would be scientifically unsound.
- **Remediation:** Re-run with predeclared diagnostic protocol (≥4 chains, Rhat, ESS, divergence thresholds).
- **Acceptance test:** No committed fit output is cited as posterior evidence; all quotable fits have ≥4-chain diagnostics.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r5_recovery/stan_audit_recovery_report.line_numbered.md` lines 58-77

### PUB-01 — No assessed paper is presently publication-ready. R8's c1_* dose-refit dependency is supported for its source-defined Paper 1/2/3 chain, but not demonstrated as a biological prerequisite for every prospective modular paper. Independently, absent immutable campaign lineage blocks all modules.
- **Consequence:** Source-defined Papers 1-3 have domain blockers; all modular papers are operationally blocked by shared lineage/provenance controls.
- **Remediation:** Complete c1_* dose refit first; then unblock Paper 3 tiers, Paper 2 economics, Paper 1 diagnostics.
- **Acceptance test:** At least one paper passes all 11 gates (G1-G11) including G8 Bayesian diagnostics.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r8/publication_readiness_audit_r8.md` §4 gate matrix

### PUB-04 — Immutable campaign attempts, exact run fingerprints, figure/table lineage, and parent-child campaign records are all absent. Cannot support separate exploratory/confirmatory/revision/review-response campaigns.
- **Consequence:** Publication readiness is BLOCKED for every prospective paper.
- **Remediation:** Implement the campaign manifest spec from r6 §8 including run_intent, parent_campaign_uid, fingerprints, and immutable attempt directories.
- **Acceptance test:** Campaign smoke test: create exploratory → freeze → create confirmatory citing parent; confirmatory root is append-only; exploratory results cannot be imported unless predeclared.
- **Evidence:** `/workspace/scratch/fresh_repo_assessment/r6/ASSESSMENT.numbered.txt` lines 123-124, 136-148

## Sequencing rule

Tranche A should land before campaign infrastructure because fingerprints cannot rescue semantically invalid configurations. Tranche B should land before any new scientific campaign. Tranches C and D can proceed in parallel after A if they preserve boundary contracts. Tranche E begins only after the earlier acceptance tests pass and requires fresh campaigns; legacy output cannot clear it.

Each tranche should be implemented as small reviewable changes with regression tests, then independently audited against a new pinned SHA. Do not combine model-semantic repairs with recalibration in one change set.
