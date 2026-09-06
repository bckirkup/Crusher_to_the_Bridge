# Corrected integrated assessment — r11

**Pinned source:** `/workspace/Crusher_to_the_Bridge`  
**Declared canonical SHA:** `07561adf2b93ff6b358859fb382b253c08828156`  
**Assessment time:** 2026-09-06 UTC  
**Scope:** correction and synthesis of r9 and r10 only; no Stan rerun, broad source scan, or scientific campaign.  
**Authority:** this report supersedes only the stale Stan-runtime and Stan-dependent readiness statements in r10. All other r10 findings are carried forward without re-audit.

## 1. Corrected verdict

**Publication status remains BLOCKED for inference-backed modular campaigns.** R9 materially improves the execution classification: all **9/9** Stan models freshly compiled and all **9/9** completed bounded four-chain synthetic runs; **8/9** passed the declared smoke thresholds. It does **not** establish scientific inference validity. The fixtures were tiny synthetic smoke inputs, not real observations or parameter-recovery truth sets; active fleet wastewater was disabled; posterior-predictive scientific validation and simulation-based or real-data recovery remain absent; the latent dose/intercept model is structurally non-identifiable; and r10's immutable campaign-lineage criteria remain unmet.

The precise corrected status is therefore:

> **Source-checkout executable; all nine Stan models have bounded four-chain synthetic execution evidence; installed distribution defective; scientific inference and publication-campaign readiness BLOCKED.**

Confidence is **high** for execution and smoke classifications because r9 preserves per-model source/executable/data hashes, commands, chain seeds, raw outputs, summaries, and diagnostics. Confidence is **high** that these results do not satisfy scientific-validation criteria because r9 explicitly labels its fixtures and checks as bounded smoke evidence.

## 2. Evidence boundary

I used only r9 and r10 artifacts plus one narrowly necessary source-identity check. I did not rerun Stan, tests, campaigns, or broad semantic scans. R9 is the definitive fresh Stan execution layer; r10 remains the integrated source, architecture, lineage, and publication-readiness adjudication. Where they conflict on runtime availability, later r9 execution supersedes r10's r5-derived status.

The snapshot has no `.git`, so `git rev-parse` is unavailable. I compared the current source tree against r9's complete pre-execution manifest (path, type, mode, size, file SHA-256, or symlink target): **1,375 vs 1,375 records, 0 missing, 0 unexpected, 0 mismatched**. Evidence: `baseline_final_verification.json` and `r9/baseline_manifest_pre.json`.

## 3. Stan protocol and aggregate result

R9 forced fresh compilation under CmdStan 2.39.0. Each bounded run used four chains, distinct fixed seeds 91001–91004, 500 warmup plus 500 retained draws/chain, `adapt_delta=0.9`, maximum treedepth 12, and a 900 s/model bound. Declared smoke acceptance required maximum R-hat ≤1.01, minimum bulk and tail effective sample size (ESS) ≥400, zero divergences, zero transitions at maximum treedepth, and minimum energy Bayesian fraction of missing information (E-BFMI) ≥0.3.

| Model | max R-hat | min bulk ESS | min tail ESS | Div. | Depth saturation | min E-BFMI | Smoke |
|---|---:|---:|---:|---:|---:|---:|---|
| `boundary_ar` | 1.00414 | 950.379 | 879.176 | 0 | 0 | 0.872 | **PASS** |
| `boundary_outbreak` | 1.00747 | 1093.330 | 1075.170 | 0 | 0 | 1.024 | **PASS** |
| `norovirus_outbreak` | 1.00494 | 791.314 | 691.574 | 0 | 0 | 0.897 | **PASS** |
| `norovirus_trajectory` | 1.00599 | 1031.850 | 591.721 | 0 | 0 | 0.939 | **PASS** |
| `sentinel_attribution` | 1.00193 | 845.618 | 575.078 | 0 | 0 | 0.859 | **PASS** |
| `sentinel_fleet` | 1.00706 | 797.098 | 303.738 | 0 | 0 | 0.903 | **FAIL** |
| `synthetic_recovery_ar` | 1.00457 | 1759.470 | 1171.230 | 0 | 0 | 1.000 | **PASS** |
| `synthetic_recovery_latent` | 1.00982 | 638.207 | 456.550 | 0 | 0 | 0.788 | **PASS** |
| `synthetic_recovery_outbreak` | 1.00274 | 1785.400 | 1149.850 | 0 | 0 | 0.979 | **PASS** |

`sentinel_fleet` alone missed a declared threshold: tail ESS **303.738 versus 400** for `ww_slope`. In this one-voyage clinical-only fixture, `NW=NC=0`; therefore `ww_slope` was prior-only and the active wastewater/concentration likelihood was not tested. The run nevertheless had zero divergences, no treedepth saturation, maximum R-hat 1.00706, and minimum E-BFMI 0.903396. This is a bounded smoke-gate failure, not evidence that a realistic fleet fit is unstable, and not evidence that fleet wastewater inference is valid.

Evidence: `r9/runtime_summary.json`, `r9/runs/*/result.json`, and `r9/REPORT.md` lines 69–91.

## 4. Required layer-by-layer disposition for every model

| Model | Fresh compile | Bounded 4-chain run | Smoke | Malformed input | Same-host repeat | Identifiability | Posterior-predictive validation | Real-data / recovery | Scientific fitness |
|---|---|---|---|---|---|---|---|---|---|
| `boundary_ar` | compiled | completed | PASS | Direct nonzero | Not tested | Not assessed | not demonstrated | not demonstrated | Not demonstrated |
| `boundary_outbreak` | compiled | completed | PASS | Family representative only | PASS same-host only | Not assessed | not demonstrated | not demonstrated | Not demonstrated |
| `norovirus_outbreak` | compiled | completed | PASS | Family representative only | Not tested | Not assessed | not demonstrated | not demonstrated | Not demonstrated |
| `norovirus_trajectory` | compiled | completed | PASS | Direct nonzero | Not tested | Not assessed | not demonstrated | not demonstrated | Not demonstrated |
| `sentinel_attribution` | compiled | completed | PASS | Direct nonzero | Not tested | Not assessed | not demonstrated | not demonstrated | Not demonstrated |
| `sentinel_fleet` | compiled | completed | FAIL | Direct nonzero | Not tested | Not assessed | not demonstrated | not demonstrated | Not demonstrated |
| `synthetic_recovery_ar` | compiled | completed | PASS | Direct nonzero | Not tested | Not assessed | not demonstrated | not demonstrated | Not demonstrated |
| `synthetic_recovery_latent` | compiled | completed | PASS | Direct nonzero | Not tested | FAIL: dose/intercept separate | not demonstrated | not demonstrated | Not fit for separate dose; otherwise not demonstrated |
| `synthetic_recovery_outbreak` | compiled | completed | PASS | Family representative only | Not tested | Not assessed | not demonstrated | not demonstrated | Not demonstrated |

The compact table must be read with the following exact model-specific qualifications:

### `boundary_ar`
- Fixture: 16 synthetic beta-regression rows; no scientific observations or recovery truth.
- Malformed input: direct wrong-length `ar` test returned 1 and left no success artifact.
- Generated quantities: finite/shape and same-fixture mean consistency only; not posterior-predictive validation.
- Scientific inference: not established; beta endpoints remain an explicit contract limitation (STAN-07).

### `boundary_outbreak`
- Fixture: 20 synthetic Bernoulli rows; no recovery truth.
- Malformed input: not directly tested; only the boundary-family `boundary_ar` representative was fault-injected.
- Repeat: the only deterministic repeat in r9. Four draw-payload hashes and diagnostic dictionaries matched bitwise on the same host with identical inputs/seeds/controls. This does not establish cross-host portability.
- Scientific inference: not established.

### `norovirus_outbreak`
- Fixture: 20 synthetic rows; no recovery truth.
- Malformed input: not directly tested; `norovirus_trajectory` represented the family.
- Generated quantities: finite/shape and minimal same-fixture consistency only.
- Scientific inference: not established; unconstrained divisor `vsp_ref` remains (STAN-06).

### `norovirus_trajectory`
- Fixture: four runs × four epochs, 100 agents/run.
- Malformed input: direct `N_agents[1]=0` test returned 1 and left no success artifact.
- Prediction: RNG outputs were finite, but use observed lagged infections and are one-step conditional, not recursive epidemic posterior-predictive validation (STAN-08).
- Scientific inference: not established; mixed-grid assembly and divisor limitations remain (DIM-07, STAN-06).

### `sentinel_attribution`
- Fixture: one synthetic four-epoch voyage; clinical attribution only.
- Malformed input: direct ascertainment 1.5 test returned 1 and left no success artifact.
- Generated quantities: finite attribution and clinical log-likelihood checks only.
- Scientific inference: not established.

### `sentinel_fleet`
- Fixture: one synthetic three-epoch voyage, `NW=NC=0`; active wastewater and concentration paths were disabled.
- Malformed input: direct `T[1]=Tmax+1` test returned 1 only after runtime indexing; this confirms the missing parse-time cross-field guard, and its partial failure CSV was quarantined.
- Smoke: FAIL only because prior-only `ww_slope` tail ESS was 303.738 <400; other quoted diagnostics were acceptable.
- Identifiability, active-channel posterior prediction, recovery, and real-data calibration were not assessed.
- Scientific inference: blocked for active fleet wastewater and otherwise not established; STAN-04/05 remain.

### `synthetic_recovery_ar`
- Fixture: 16 synthetic rows; despite the name, this was not a parameter-recovery truth set.
- Malformed input: direct endpoint `ar[1]=0` was accepted by declaration but rejected by the beta likelihood; exit 1 and partial CSV quarantined. This confirms STAN-07's contract mismatch.
- Scientific inference: not established.

### `synthetic_recovery_latent`
- Fixture: 40 synthetic rows; no generated-quantities block.
- Malformed input: direct `outbreak[1]=2` test returned 1 with no success artifact.
- Smoke: PASS, but this does not repair non-identifiability. `corr(dose_adj, intercept)=0.9312` under pinned priors and 0.9796 after widening intercept prior SD 1→3. The identifiable likelihood combination is `intercept - beta_d_fixed*dose_adj`.
- Scientific inference: **not fit for separate dose-recovery claims**. Other inference remains unvalidated.

### `synthetic_recovery_outbreak`
- Fixture: 20 synthetic Bernoulli rows; not a parameter-recovery truth set.
- Malformed input: not directly tested; `synthetic_recovery_ar` represented the pooled family.
- Generated quantities: finite/shape and minimal same-fixture consistency only.
- Scientific inference: not established.

Exact field-level dispositions and evidence paths are in `stan_model_register.json/csv`.

## 5. Identifiability versus diagnostics

The strong `dose_adj`/free-intercept posterior dependence in `synthetic_recovery_latent` prevents separate dose-recovery claims. The exact likelihood invariance is the combination `intercept - beta_d_fixed*dose_adj`; priors select a position along the ridge. R9's good R-hat/ESS and smoke PASS show that a sampler can traverse the posterior under the selected priors; they do not show that data separately identify dose. STAN-03 remains **HIGH** severity and Priority 0.

Evidence: `r9/runs/synthetic_recovery_latent/result.json` and `r9/latent_prior_sensitivity.json`.

## 6. Malformed-input synthesis

R9 directly fault-injected one model for each of six assembler families. All six commands returned 1, no success-named completed-draw artifact remained, and two partial error CSVs were quarantined. This is positive fail-closed evidence for those exact mutations only. It is not a complete invalid-input matrix for all nine models. Two tests preserve unresolved contract defects: fleet `T>Tmax` fails late rather than at ingestion; beta endpoint 0 is legal in the data declaration but invalid for the likelihood.

Evidence: `r9/invalid_input_results.json` and `r9/invalid_tests/`.

## 7. Finding-register reconciliation

The corrected register retains 64 findings. STAN-01 now cites fresh r9 compilation. STAN-02 is rewritten from absent/limited runtime evidence to bounded four-chain execution for 9/9 with 8 PASS and one fixture-qualified FAIL; its severity changes **HIGH → MEDIUM** because runtime absence is resolved. STAN-03 remains **HIGH** and gains direct posterior-sensitivity evidence. Other r10 findings were carried forward without re-audit.

Corrected severity counts are: **18 HIGH, 1 MEDIUM-HIGH, 28 MEDIUM, 5 LOW, 3 PASS, 1 PASS (with qualifications), and 8 INFO**. The change in counts is solely STAN-02's reclassification.

## 8. Paper-readiness reconciliation

All eight paper modules remain **BLOCKED** at exploratory, confirmatory, revision, and review-response lifecycle stages. R9 changes the Stan execution premise for M01, M04, and M07, but not their readiness labels:

- **M01 model validation/calibration:** bounded execution exists, but calibration, posterior-predictive scientific validation, identifiable recovery, and immutable lineage do not.
- **M04 wastewater surveillance:** fleet four-chain smoke exists, but its active wastewater paths were disabled and its prior-only `ww_slope` missed tail ESS; active-channel recovery/validation and lineage do not exist.
- **M07 fleet-to-port inference:** both Sentinel models ran four chains, but neither has claim-grade validation and wrapper completion is not a diagnostic gate.

The common lineage blockers (CAMP-01/02/03/04/07 and PUB-04) are unchanged. Therefore no supplied evidence satisfies the existing requirement for immutable campaign attempts, exact fingerprints, parent-child intent records, or figure/table lineage.

## 9. Remediation and priority effects

1. **Resolved:** “obtain any multi-chain runtime evidence for eight models.” No longer a remediation item.
2. **Retained, Medium:** make fit status diagnostic-aware; repeat `sentinel_fleet` with representative active wastewater/concentration data and predeclared thresholds.
3. **Retained, High/Priority 0:** redesign or externally anchor `synthetic_recovery_latent` before separate dose claims.
4. **Retained:** complete prior/posterior predictive checks, simulation-based calibration or recovery for identifiable quantities, real-data validation where the claim requires it, and representative active-channel tests.
5. **Retained:** satisfy r10's immutable campaign and analysis-lineage acceptance criteria before publication campaigns.

## 10. Cross-file consistency checks

I mechanically checked the r11 products:

- Stan model IDs: 9 unique in JSON and CSV.
- Compile/completion: 9/9 and 9/9.
- Smoke: 8 PASS, 1 FAIL; sole failure `sentinel_fleet`.
- Scientific inference validation: 0/9 demonstrated.
- Paper readiness: 8/8 BLOCKED.
- Finding register: 64 unique IDs; corrected severity counts agree with this report.
- Evidence paths: every r9 path cited by the Stan register exists; all model source and executable hashes are present.
- Source tree: 1,375 records; zero manifest differences against r9 pre-execution baseline.

Machine results are preserved in `cross_file_consistency.json` and `baseline_final_verification.json`.

## 11. Final adjudication

The hypothesis is supported. Incorporating r9 changes Stan execution from limited/absent evidence to successful bounded four-chain synthetic execution for all nine models, with one declared smoke failure. It does not change the overall verdict. Scientific inference validation, real-data calibration or simulation-based recovery, posterior-predictive validation, latent-model identifiability, active fleet wastewater validation, and immutable campaign lineage remain incomplete.

**Final status: BLOCKED for inference-backed publication campaigns.**

## Discretionary analytical decisions

- I let the later fresh r9 execution supersede r10's recovered r5 runtime classifications, while preserving r10's non-runtime findings.
- I lowered STAN-02 from HIGH to MEDIUM because its central “runtime absent” premise is resolved; I retained scientific-validation absence as a readiness block rather than mislabeling smoke success as validation.
- I used “not assessed/not demonstrated” rather than “failed” where r9 did not run identifiability, posterior-predictive, recovery, or real-data validation tests.
- I treated family-level malformed-input tests as direct evidence only for the model actually invoked and qualified the other family members.
- I treated the same-host repeat as deterministic repeat evidence only, not cross-host reproducibility.
