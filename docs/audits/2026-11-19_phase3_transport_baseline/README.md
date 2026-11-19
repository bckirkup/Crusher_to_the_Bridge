# Phase 3 transport baseline: handoff

**Status:** Handoff; no new measurements. The [canonical readout](../../ledger/CONTAM-PHASE3-BASELINE-01.md)
reports the deterministic diagnostics at `5c8f05cc`. The [aggregate evidence](evidence/aggregate.json)
includes the platform tree IDs and solver fingerprint.

**Question.** Do the corrected cruise and naval models balance air and tracer
well enough to compare their numerical behaviour? That is a narrower question
than whether either predicts real ship ventilation or infection.

**Current hypothesis.** The transport comparison can stand on its own.
The changed naval result reflects sensitivity to how make-up air is
represented; it is not evidence of a change in real exposure.

**Evidence for.** See the closure, air-balance and matched-revision
comparison in the canonical readout. For verification, use the existing
`contam_paired_diagnostic` and `contam_pressure_balance_diagnostic` at the
pinned commits. The JSON records the two hulls, fields, timings and
parameters; use the standard cases for each hull. Compare absolute residual
maxima over all cells, and take the arithmetic mean of whole-hull
material-time over only the single-pulse cases within each hull/field.
The historical comparator uses only the three fields and timing listed for
that revision, with the same executable. No seed or population weighting.

**Evidence against / unexplained.** No external engineering measurements;
design and commissioned fields differ. Neither agreement nor disagreement
identifies the more accurate field. Nothing in this run tests human dose.

**PRs landed / running jobs.** None as of handoff authoring. No AWS
submission, image change, model change or parameter fit.

**What is void.** No historical measurement is withdrawn on its own inputs.
Do not transfer the pre-repair destroyer tracer result to the corrected hull.
No pathogen ledger measurement is superseded.

**Single open decision.** Stop at the transport-methods paper or freeze a
separate respiratory validation design. Recommend design only; hold execution
until a distinct positive contrast, no-change control, paired uncertainty
analysis and smoke check are established.

**Do not reopen.** The make-up repair is complete. Do not tune flow or disease
parameters to reconcile models or match an outbreak anchor.
