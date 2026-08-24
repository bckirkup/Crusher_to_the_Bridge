# Surveillance economics: who pays, who benefits, and would a port pay in

`picard_framework/analysis/economics/` prices a surveillance capability and
splits its benefit between the two communities that receive it. It is a
post-processing layer: it consumes what the ABM and the shore renewal model
already produce and computes nothing epidemiological of its own.

## Why a payer, and not just a total

`crusher_labs/cost_ledger.py` already prices surveillance in three units —
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
  in the same shape the shore module reports its `R_shore` surface.

The within-community split of shore benefit between a port authority and a
public-health agency is an institutional assumption, not a simulation result. It
is an explicit weight input, defaulting to even, and is documented as such.

## Decision rule

A payer is willing to contribute while its share of the benefit covers its share
of the cost, so its break-even contribution is the monetary equivalent of the
benefit it receives. A payer contributing nothing reports *no* benefit-to-cost
ratio rather than an infinite one: an infinity reads as a result and is not.
