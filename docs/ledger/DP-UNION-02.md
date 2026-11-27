# DP-UNION-02
**Date:** 2026-11-26
**Commit:** #1437
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** f585f710299040c374a02e94fe1afa563cb90f74

First post-`COVID-SHED-SHAPE-01` Diamond Princess union-arm measurement.
Design `docs/covid/covid_dp_union_02_design.md`, machine design
`picard_framework/runs/covid_dp_union_02_design.json`, campaign
`campaigns/covid/dp_union_02/`, execution ledger
`campaigns/covid/dp_union_02/LEDGER.md`, canonical canary readout
`docs/covid/dp_union_02_union_t1e8_canary_readout.json`.

## What ran

The owner-authorized stage was exactly one inspected single Batch child and
one 20-seed canary array for `union_t1e8_canary` at theta `1e8`, arm
`union_niid`, using the first 20 frozen ascertainment-conditioned seeds. No
cross-decade pilot, `_rest` block, other lattice cell, GM/H5 validation, or
further AWS submission ran.

Image digest
`sha256:40b95eb4b84c681ce0fb4020cbb0b11fc751c9b7a677d3109b40c80f7405b3e9`;
job-definition revisions 1–3 all read back on that digest. Single child
`3550df34-1f0c-4715-9e77-a67f515e480a` succeeded and was inspected before the
array. Array parent `9f129293-4457-4f1f-bcd9-7e5e068ddca1` succeeded with all
20 children `SUCCEEDED` in one attempt each; failure classification was 20
`ok`, zero Spot reclaim/OOM/timeout/other. The exact S3 prefix contains exactly
the 20 authorized artifacts.

## Canary measurement

All 20 artifacts are audit-clean. The row is formally provisional because the
frozen row is 24 seeds; the canonical readout therefore leaves `consistent`
null. Every measured seed is in both the founder and takeoff classes, no seed
is extinct, and the row is neither dead nor saturated.

| leg | frozen target/band | measured canary | result |
|---|---:|---:|---|
| ignition day | <= 9 | median 1 | pass |
| before-share | 0.173 +/- 0.10 | median 0.9833114203981133 | fail high |
| attack secondaries | 712–960 | median 3255.5 | fail high |
| during-quarantine | 150–350 | median 1.5 | fail low |
| conditioned capture | >= 0.80 | median 0.6047256797732786 | fail low |
| T3 positives through day 31 | 634 | median 188.5; 20/20 below | fail below |
| onboard positives through day 34 | 691 | median 188.5; 20/20 below | fail below |

Per-seed ranges are narrow and one-sided: attack 3218–3302,
during-quarantine 0–5, capture 0.429–0.732, before-share 0.974–0.988, and
P31/P34 156–229. Median specimens through day 31 are exactly the frozen 3063,
so the low T3 positive count is not a missing-test artifact. Median infections
are 3253 before quarantine, 1.5 during the quarantine window, and 0 after
quarantine.

Because all 20 measured seeds are already on the same failing side of the
median legs and below both testing targets, the four unrun `_rest` seeds
cannot reverse those median or side failures under the frozen readout
arithmetic. Theta `1e8` therefore cannot become a consistent 24-seed row even
though the canary remains formally provisional.

## Interpretation and stop state

Measured, not mechanism attribution: the ascertainment-conditioned seeds ignite
almost immediately, produce near-saturating pre-quarantine incidence, leave
almost no incidence during the quarantine window, and yield too few positive
tests and too little conditioned capture. The coherent early-burn-out shape is
an inference from those legs, not proof of which structural feature produced
it.

Execution stopped after the canary as required. Benjamin decides whether the
four `_rest` seeds are worth running for completeness despite the fixed
row-level failures, whether another already-declared lattice theta canary
should run, or whether the post-shape union arm requires design-level review
before further AWS execution.

The design-level review is now recorded in
`docs/ledger/DP-UNION-02-DESIGN-REVIEW-01.md`. Its recommendation supersedes
the open-ended decision list above: complete the already frozen 30-cell
cross-decade pilot and stop (25 cells remain unrun; the first five
theta-`1e8` artifacts are already that decade's pilot slice). The scored-row
dead/representativeness conflicts must be resolved before any post-pilot
scored row, but not before the pilot because the pilot scores no contract
leg.
