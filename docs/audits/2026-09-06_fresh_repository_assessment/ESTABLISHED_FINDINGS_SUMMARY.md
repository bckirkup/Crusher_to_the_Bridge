# Established findings summary — r11

- **Source:** declared SHA `07561adf2b93ff6b358859fb382b253c08828156`; current 1,375-record manifest exactly matches r9 pre-execution baseline.
- **Inventory:** exactly nine Stan models.
- **Fresh compilation:** 9/9 compiled.
- **Bounded execution:** 9/9 completed four-chain synthetic runs.
- **Declared smoke diagnostics:** 8/9 PASS; `sentinel_fleet` FAIL because prior-only `ww_slope` tail ESS was 303.738 versus 400 in a clinical-only `NW=NC=0` fixture. It had 0 divergences, 0 treedepth saturations, max R-hat 1.00706, and min E-BFMI 0.903396.
- **Repeat evidence:** `boundary_outbreak` repeated bitwise on the same host under identical inputs/seeds/controls; no other model was repeated and no cross-host portability was tested.
- **Malformed inputs:** six direct family-representative mutations returned nonzero; this is not a complete nine-model invalid-input matrix. Fleet cross-field and beta-endpoint contract limitations remain.
- **Identifiability:** `synthetic_recovery_latent` cannot separately identify `dose_adj` and its free intercept; no separate dose-recovery claim is valid.
- **Scientific validation:** 0/9 demonstrated. Smoke compilation/sampling/diagnostics and finite generated quantities are not posterior-predictive validation, simulation-based recovery, real-data calibration, or fitness for scientific inference.
- **Paper readiness:** 8/8 modules remain BLOCKED because claim-grade validation and immutable campaign/analysis lineage remain incomplete.
- **Overall verdict:** **BLOCKED for inference-backed publication campaigns**; unchanged from r10.

Machine-readable source: `established_findings_summary.json`.
