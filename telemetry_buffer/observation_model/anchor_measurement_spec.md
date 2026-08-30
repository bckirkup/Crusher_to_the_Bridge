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
| A4 | VSP distribution | `reported_case_attack_rate_passenger` | inside the hull class IQR |
| A5 | passenger vs crew | `reported_case_attack_rate_passenger / reported_case_attack_rate_crew` | ≈ 3.5 (7% vs 2%) |

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
