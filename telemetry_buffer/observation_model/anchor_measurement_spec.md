# Anchor measurement spec

The four literature anchors are ratios between quantities we already simulate.
Three of them are currently unmeasurable, or measurable only wrongly, because
the numerator and denominator are drawn from different populations. This spec
fixes the definitions before anything is scored against them.

## The defect

`compute_derived_metrics` emits

```
attack_rate = (infected_final + recovered_final) / num_agents      # whole ship
ever_ill_attack_rate_passenger  = ever-ill passengers / passengers # passengers
reported_case_attack_rate_passenger                                # passengers
```

so `ever_ill / attack_rate` — the ill/infected anchor — divides a passenger
rate by a whole-ship rate. Crew are roughly 30–40% of complement on these
hulls and have their own contact structure, so the mismatch is not a rounding
term. Every ill/inf figure quoted from v4 and from the two pilots carries it.

Separately, the *counter* metric named `attack_rate` in
`orchestrator_epoch._counter_metric_value` returns

```
n_symptomatic_now / pop
```

which is instantaneous symptomatic prevalence, not any attack rate. It cannot
accumulate, and it is not the quantity the escalation thresholds are documented
against.

## Required quantities

Accumulate `ever_infected_ids` per epoch exactly as `ever_ill_ids` and
`ever_reported_ids` are accumulated (`orchestrator_init.update_ever_ill_ids` is
the pattern): an agent joins the set the first epoch it is infected or
recovered, and never leaves. Emit, per epoch, alongside the existing fields:

| field | definition |
|---|---|
| `cumulative_ever_infected` | `len(ever_infected_ids)` |
| `cumulative_ever_infected_passenger` | ever-infected ∩ passengers |
| `cumulative_ever_infected_crew` | ever-infected ∩ crew |
| `infection_attack_rate_passenger` | ever-infected passengers / passengers |
| `infection_attack_rate_crew` | ever-infected crew / crew |
| `ever_ill_rate_crew` | ever-ill crew / crew |
| `reported_case_rate_crew` | ever-reported crew / crew |

The last three already exist inside `_compute_group_rates`, which returns
`{"overall", "passenger", "crew", "max_group"}`; only the passenger member is
emitted today. Nothing new needs computing for them.

Promote the same four rates to `derived` from the final epoch:
`infection_attack_rate_passenger`, `infection_attack_rate_crew`,
`ever_ill_attack_rate_crew`, `reported_case_attack_rate_crew`.

`attack_rate` in `derived` keeps its current whole-ship definition so historical
campaign artifacts stay comparable; it is simply no longer used as the ill/inf
denominator.

## Counter naming

Add `symptomatic_prevalence` as the canonical name for the existing
`attack_rate` counter behaviour, and keep `attack_rate` accepted as a
deprecated alias resolving to the identical function, so no shipped config or
threshold changes value. Document both in the counter docstring. Escalation
thresholds are untouched by this change — they read `max_group` from
`compute_group_attack_rates`, which is cumulative ever-ill and already correct.

## Anchors, once the above exists

All conditional on take-off (peak prevalence ≥ 10 infected), per hull × dose ×
response cell, cell medians over ≥ 10 seeds.

| # | anchor | quantity | target |
|---|---|---|---|
| A1 | Wikswo whole-ship cohort | `ever_ill_attack_rate_passenger` | ≈ 0.154 |
| A2 | asymptomatic ratio | `ever_ill_attack_rate_passenger / infection_attack_rate_passenger` | 0.68–0.81 (0.59–0.81 if GII.4-weighted) |
| A3 | infirmary capture | `reported_case_attack_rate_passenger / ever_ill_attack_rate_passenger` | 0.60 ± 0.05 |
| A4 | VSP posted attack rate | `reported_case_attack_rate_passenger` | inside the hull class IQR **derived per hull class × era** from `telemetry_buffer/observation_model/vsp_outbreak_series.csv` by `telemetry_buffer/observation_model/vsp_class_era_scoring.py`; see `telemetry_buffer/observation_model/incidence_and_attack_rate_scoring_spec.md` |
| A5 | passenger vs crew | `reported_case_attack_rate_passenger / reported_case_attack_rate_crew` | ≈ 3.5 (7% vs 2%) |
| A8 | unconditional AGE incidence (**Implemented**) | reported cases per 100,000 travel days over all simulated voyages | MMWR Surveill Summ 2021;70(6) by ship-size band, interval endpoint and pooled-rate ratios — `telemetry_buffer/observation_model/midrs_incidence_targets.py`; source record `telemetry_buffer/observation_model/midrs_observed_targets.md` |
| A9 | posting probability (**Implemented**) | simulated eligible voyages passing VSP's posting rule / eligible simulated voyages | MMWR investigated versus project posted fleet interval; per-hull numerator unpublished — `telemetry_buffer/observation_model/midrs_incidence_targets.py`; source record `telemetry_buffer/observation_model/midrs_observed_targets.md` |
| A10a | incidence gradient over voyage length (**Proposed**) | reported cases per travel day across 3-5, 6-7, 8-10, 11-14, 15-21 day voyages | passenger per-day rate rises 13.3 → 40.0 per 100,000 travel days (MMWR Table 2); gradient sign and rough magnitude only — §A10 of `telemetry_buffer/observation_model/incidence_and_attack_rate_scoring_spec.md` |
| A10b | crew gradient over voyage length (**Proposed**) | the same quantity for crew | crew rates flat (17.5, 22.1, 19.0, 17.4, 20.9); scored as passenger gradient positive with crew gradient flat, never as a ratio — §A10 of `telemetry_buffer/observation_model/incidence_and_attack_rate_scoring_spec.md` |
| A10c | outbreak probability over voyage length (**Proposed**) | simulated voyages passing the posting rule / all simulated voyages, per length band | derived from MMWR Tables 1 and 3: ≈0.5 → ≈29 posted outbreaks per 1,000 voyages, 3-5 d to 15-21 d — §A10 of `telemetry_buffer/observation_model/incidence_and_attack_rate_scoring_spec.md` |

A4's target values were previously four hard-coded quantile triples with no
derivation script and no source note, and they do not reproduce from this
repository's own series under any band edges tried. They are withdrawn. The
replacement ships with the code that derives it, and a hull class with fewer
than ten postings in the scored era carries no A4 anchor at all —
`mega_cruise_5000` has four pre-2020 and three post-2020 postings.
A4 remains conditional on VSP posting the voyage, as A7 is: VSP publishes
nothing about voyages it never posted. A8 and A9 now put implemented
unconditional channels alongside it. A10 remains Proposed.
A10 adds the only trajectory evidence norovirus offers: duration gradients
recovered across voyages, since no within-voyage norovirus time series
exists. Voyage length and ship size are confounded in the published
marginals, so A10 scores gradient sign and rough magnitude only.

Ratios are computed per seed and then summarised, and separately as a ratio of
cell medians; both are reported, because they differ materially whenever the
denominator is small (the postfix pilot has cells where the two disagree by 2×).
Seeds with a zero denominator are excluded from the per-seed ratio and counted.

A2 is a *prediction*, not a fitted quantity: `P(ill | infected)` is the Teunis
η/γ function of the inoculum each host actually received, so A2 is a statement
about dose magnitude and its variance, and A1/A2/A3 cannot all be satisfied by
scaling mean dose alone.

## A6, deliberately not scored the same way

The superspreader anchor — top decile of transmitters causing 57% of secondary
cases, symptomatic about half as often, detected ~1.8× later — has no direct
observable here: transmission runs through shared reservoirs, so an infection
has no identifiable infector and the secondary-case distribution does not
exist in our state. It will be scored on a declared proxy, per host:

```
transmission_pressure(host) = Σ_epochs  emitted_mass(host, epoch)
                                        × susceptible_co_occupants(host, epoch)
```

and reported as the top-decile share of total pressure, plus that decile's
symptomatic fraction and its `first_sick_call_epoch − symptom_onset_epoch`
against the rest. This is a proxy for, not a measurement of, the secondary-case
share, and must be labelled as such wherever it is quoted. It needs a per-host
emission ledger that does not exist yet, so it is a separate change from the
denominator fixes above.

## A7, the COVID discontinuity: a difference, and an out-of-sample one

A1-A5 are levels, and a level can be matched by compensating errors. A7 is a
difference across the 2020 break in the same observation system, so anything
wrong in both arms cancels — which is why it earns a place here after an effort
spent finding errors that cancel in levels.

Measured on `vsp_outbreak_series.csv` (428 posted outbreaks extracted from
CDC-hosted pages; 262 in the `pre` arm ending 2004-2019, 66 in the `post` arm
ending 2022 onward), by `vsp_discontinuity_analysis.py`, reported in
`vsp_covid_discontinuity_findings.md`, justified in
`vsp_covid_discontinuity_design.md`. All values conditional on VSP posting a
voyage; VSP publishes no voyage denominator, so nothing here is per voyage.

| # | quantity | measured | target for the model |
|---|---|---|---|
| A7a | post/pre ratio of median passenger reported attack rate | 0.912 (0.788-1.182), p=0.26 | compatible with 1; **not** a level drop |
| A7b | post/pre ratio of median crew reported attack rate | 1.365 (1.004-1.677), p=0.007 | rose; 1.211 (0.846-1.561) on 1000+ pax ships |
| A7c | A7a / A7b, the passenger-specific component | 0.668 (0.532-0.907), p<0.001 | **0.53-0.91**, and 0.581-1.053 under the composition control |
| A7d | share of postings above 15% of passengers ill | 18/262 → 2/66; on 1000+ pax ships 11/226 → 0/48 | direction only, Fisher p=0.22; never a fitted target |
| A7e | postings per year, norovirus fraction | descriptive | never scored, no denominator |

**A7c is the scored anchor; A7a, A7b and A7d are reported context.** Three
things about it must travel with the number wherever it is quoted:

1. It is scored as an *out-of-sample prediction*. The common dose is fitted on
   the pre-2020 arm alone; the post-2020 arm runs at that same dose with an
   independently sourced post-2020 configuration. Fitting anything to A7c
   destroys its value as evidence — it is the only anchor here that can
   discriminate a mechanism, and it can only do that once.
2. Simulated voyages must pass VSP's own posting rule (100+ passengers, 3-21
   days, 3% of passengers or crew reporting) before entering the statistic, or
   the two sides are not truncated alike. The posting floor attenuates A7a and
   can push A7b above 1 with no change in crew behaviour at all, which is the
   documented reason A7a alone is not the anchor.
3. Crew are not a clean control. They are selected by the same posting rule from
   a smaller denominator, and about half of the crew rise is fleet composition —
   small expedition vessels, several below VSP's own 100-passenger criterion,
   are posted post-2020 and carry a few hundred crew, where two cases move the
   rate by a point. The composition-controlled arm (1000+ passengers) is
   reported alongside for that reason and its interval touches 1.

The ledger's earlier reading of this break — a 15-20% fall in passenger attack
rates with crew unchanged — does not survive the per-outbreak data. Passenger
medians barely move; crew rise. What actually disappears is the upper tail: on
ships carrying 1000+ passengers the worst post-2020 posting reaches 13.5% of
passengers ill against a pre-2020 maximum of 25.2%, with 11 of 226 pre-2020
postings above 15% and none of 48 after. A model that matches A7c by lowering
every voyage uniformly, and one that matches it by removing the tail, are
different models; A7d exists to keep that distinction visible even though its
counts are too sparse to score.
