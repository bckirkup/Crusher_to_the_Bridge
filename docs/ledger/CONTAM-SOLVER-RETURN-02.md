# CONTAM-SOLVER-RETURN-02
**Date:** 2026-11-21
**Commit:** b925a99cfce4514346d1659cc260de4a43522543
**Pathogens:** all
**Status:** measured
**Measured at:** 53b281253c0699c82cdf20abab0d97b84f97f723

Recovered the existing 4,575,643-byte whole-hull engineering package and
rebuilt all 140 respiratory seed endpoint rows and Batch timing rows.
The archive passed 51 checks and the respiratory reduction passed 21.
All six reduction-table hashes match the previous paired readout.
Source simulations retain commits `106a3583` / `8de77294` and seeds
20200205–20200224 on DP, 20200205–20200254 on GM.

Added a fixed-output `solver_return` option to the existing protected
`campaign-collect` workflow. It returns the engineering package and
seed-level voyage-wide endpoint CSV in one artifact, checks sizes and
SHA-256 digests, and uses HEAD-pinned reads. A live fetch with the Picard
role reproduced both hashes. Protected Actions execution remains subject
to the `aws-campaign` environment review.

Corrected residual ledger and handoff claims about closed solver
questions, preserved dose and historical takeoff probability. The
existing paired intervals, ranges and threshold discordance support
low observed provider sensitivity on these cases. Delivered-dose
equivalence remains unmeasured.

Full-job accounting recovered the original 140 AWS child records.
Classic and Spirit have engineering timings and older influenza
results, but a common paired-provider respiratory task and recoverable
full-job timings are absent. The all-cruise influenza campaign remains
unperformed. The current nine-cruise inventory distinguishes named
hulls from the original Mega/Expedition replay substitutions.

Readout and exact return contract are in
[`docs/contam_solver_return_02.md`](../contam_solver_return_02.md).
