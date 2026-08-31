# Surveillance economics: who pays, who benefits, and would a port pay in

> **Status:** Implemented, numbers not quotable

`picard_framework/analysis/economics/` prices a surveillance capability and
splits its benefit between the two communities that receive it. It is a
post-processing layer: it consumes what the ABM and the shore renewal model
already produce and computes nothing epidemiological of its own.

## Why a payer, and not just a total

`../../crusher_labs/cost_ledger.py` already prices surveillance in three units —
dollars, person-hours, and consumed items — but records only *what* was spent,
never *who* paid. The paper's question is whether a port would rationally
contribute, and that question is unanswerable from a single total, because the
party bearing the cost and the community receiving the benefit need not be the
same. So a contribution carries:

| field | meaning |
| --- | --- |
| `payer` | `ship_operator`, `port_authority`, or `public_health_agency` |
| `medium` | `cash`, `labour_hours`, or `consumables` |
| `quantity` | in that medium's own unit (USD, person-hours, item counts) |
| `item` | names the consumable, so per-item unit costs apply |

`ContributionRates` converts the non-cash media to monetary equivalents:
cash is the identity, labour converts through `usd_per_labour_hour`, and
consumables through a per-item cost with a declared fallback. The rate is an
input rather than a constant precisely because it moves the answer — see the
sensitivity requirement below.

`contributions_from_financial_audit()` bridges a run's `FINANCIAL_AUDIT` block
into that shape, with an explicit medium-to-payer attribution map so the *same*
simulated capability can be re-costed under different funding arrangements
without re-running the simulation. Only surveillance lines are read:
intervention spend is a consequence of an outbreak, not a price of watching for
one, and pooling the two would make the capability look more expensive the worse
it performed.

## Two benefit streams, kept separate

**Afloat benefit is a paired difference** — the same voyage with and without
the capability being priced (`AfloatBenefit`). Negative differences are not
clamped: an arm that came out worse reports that it did.

**Shore benefit is adopted, not invented** (`ShoreBenefit.from_counterfactual`).
CTB simulates the ship; ports enter only as a hazard prior, so shore cases
averted cannot come out of the ABM. They come from
`picard_framework/analysis/shore/`, whose counterfactual differences a
ship-timed against a port-timed detection. Detection lead arrives in epochs and
is converted to physical hours through `epoch_hours`; a missing detection stays
`None` rather than becoming zero.

The package exposes two benefit-split shapes:

- **`benefit.BenefitSplit`** — monetised under an explicit `BenefitValuation`.
- **`surveillance.BenefitSplit`** — signed case counts only, built from 11b
  `CounterfactualResult.benefit` values plus campaign-supplied afloat cases
  averted. No dollar value is assigned to a case averted in this path.

## §4 scenarios and provenance

`../../presidio/data/economics/surveillance_scenarios.json` records the five §4
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

Presidio fleet configs keep `catalog.economics_id` pointed at the existing
`fleet_economics.json` reward configuration. The surveillance catalog is
separate: `catalog.surveillance_economics_id` identifies the scenario file and
`catalog.surveillance_scenario_id` selects the scenario. Both conversion rates
(`labour_conversion_rate` and `consumables_conversion_rate`) are required by
the scenario analysis API; callers should supply them from the central values
or sweep grids in `../../data/config/resource_costs.json`.

`CostAllocation` entries become `CostLedger` contribution records. They are
attribution lines alongside ledger expenditure, not new spend. Cash is recorded
at face value; labour and consumables are converted explicitly when a report is
requested.

## What is reportable, and what is not, before the re-fit

The absolute dollar levels in `valuations.py` are **unanchored placeholders**
whose provenance strings say so. They exist to be swept. Nothing in a paper
should quote a dollar level computed from them, and the `c1_*` dose-adjustment
re-fit under the hourly clock has to land before any absolute campaign figure is
quoted at all.

What *is* reportable now:

- the **shore:afloat ratio in cases averted**, which carries no valuation;
- the **shore:afloat monetary ratio**, which under `UNIT_VALUATION` equals the
  case ratio and therefore separates a valuation effect from a modelling one;
- each payer's **cost share against its benefit share**, and the sign of its net
  position;
- **break-even contribution**, in cash and in the labour hours that could be
  given instead — the form a port actually negotiates in;
- the **labour-rate sensitivity surface** (`labour_rate_sensitivity`), reported
  in the same shape the shore module reports its `R_shore` surface;
- the **scenario WTP sweep** (`sweep_willingness_to_pay`) over conversion-rate
  grids without changing the benefit side.

The within-community split of shore benefit between a port authority and a
public-health agency is an institutional assumption, not a simulation result. It
is an explicit weight input, defaulting to even, and is documented as such.

## Decision rule

A payer is willing to contribute while its share of the benefit covers its share
of the cost, so its break-even contribution is the monetary equivalent of the
benefit it receives. A payer contributing nothing reports *no* benefit-to-cost
ratio rather than an infinite one: an infinity reads as a result and is not.

For the scenario path, willingness to pay is a share comparison on signed case
benefit: a community pays its own way when its benefit share is at least its cost
share. The reported crossing is the first pair of grid rates where the port cost
share overtakes its benefit share; the package does not interpolate a threshold
or claim monotonicity unless the observed grid is monotone. Benefit shares are
unavailable (`None`) when total signed benefit is zero or negative, and the WTP
comparison rejects that regime instead of reporting a misleading share.

The shore side remains a linear renewal approximation. In particular, the
central 11b norovirus scenario is deliberately supercritical, so its
`unbounded_growth` (and, on sufficiently long horizons, `depletion_regime`)
flags are expected. Results are interpretable only while cumulative cases
remain small relative to the port population. This layer also does not model
shore-side evolution or claim a monetised value for cases.
