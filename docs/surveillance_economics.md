# Surveillance economics and benefit split

This package is a deterministic post-processing layer for Paper 3 PR 11. It
does not add transmission dynamics to the ship simulation and does not
reimplement the merged 11b shore model.

## Scenarios and provenance

`presidio/data/economics/surveillance_scenarios.json` records the five §4
scenarios: Baseline, Minimal, Moderate, Full, and Fleet network. The annual
costs are rough-order-of-magnitude values from the specification, not
measurements. The voyage-frequency grid and every allocation quantity are
unanchored modelling assumptions. Allocation quantities remain in their
native medium units (cash dollars, labour hours, or consumable units) so that
conversion-rate sensitivity remains visible. Shore capability lines are
attributed to port or public-health payers, and onboard lines to the ship
operator, without tuning the allocation to favour either community.

“Variants detected” is intentionally absent from configuration: it is a
surveillance-model output, not an input.

## Cost and benefit accounting

`CostAllocation` entries become the existing `CostLedger` contribution records.
They are attribution lines alongside ledger expenditure, not new spend. Cash
is recorded at face value; labour and consumables are converted explicitly
when a report is requested. The per-payer report exposes cash, each in-kind
medium, total equivalent, and cost share.

`BenefitSplit` combines signed shore benefit from the 11b
`CounterfactualResult.benefit` values across port calls with afloat cases
averted supplied by the campaign or ABM. It reports the shore:afloat ratio and
each community’s share. No dollar value is assigned to a case averted.

Willingness to pay is therefore a share comparison: a community pays its own
way when its benefit share is at least its cost share. Labour conversion rates
are swept without changing the benefit side. The reported crossing is the
first pair of grid rates where the port cost share overtakes its benefit share;
the package does not interpolate a threshold or claim monotonicity unless the
observed grid is monotone.

The shore side remains a linear renewal approximation. In particular, the
central 11b norovirus scenario is deliberately supercritical, so its
`unbounded_growth` (and, on sufficiently long horizons, `depletion_regime`)
flags are expected. Results are interpretable only while cumulative cases
remain small relative to the port population. This layer also does not model
shore-side evolution or claim a monetised value for cases.
