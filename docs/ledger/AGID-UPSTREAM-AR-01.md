# AGID-UPSTREAM-AR-01
**Date:** 2026-09-19
**Commit:** e53a73c
**Pathogens:** sars_cov_2_respiratory, norovirus_gii4
**Status:** measured
**Measured at:** e53a73c

## Question

Two claims were load-bearing for how this repository reads its own COVID
result: that the upstream Korkin-lab model fit the Diamond Princess attack
rate, and that the VSP-shadow monograph fit an attack rate too. If a
predecessor of this engine reproduced DP's 19.2% (712/3,711), then our
extinction-or-burn surface — 80–95% attack conditional on takeoff at every
Θ ≥ 1e6, `THETA-SCREEN-V9` — is a regression in this port rather than a
mis-chosen target.

## What the upstream paper reports

Read from the published record, Srinivasan et al., *Real-time spatiotemporal
tracking of infectious outbreaks in confined environments with a host–pathogen
agent-based system*, PNAS, doi 10.1073/pnas.2422574123, open-access full text
Europe PMC `PMC12849694`:

- The AGID SARS-CoV-2 run reaches an 18.6% attack rate and is scored against
  the DP daily case series at RMSE 23.73, MAE 16.62, KS D 0.22, beating SIR
  (D 0.62) and SEIR (D 0.69).
- That run is on Ship X's GIS, with DP scaled from 3,711 to 2,702 agents and
  the same factor applied to the initial and daily infection counts; 10
  simulations per parameter combination.
- Figure 4B labels the 18.6–19% run as the one "based on the documented 2020
  outbreak", and reports a *separate* Isolation-protocol run at 4%.
- The Delta arm reaches 54.2%, and mask/symptom-presentation arms 5.7–6.7%.

So the answer to the first claim is yes: upstream does report a DP attack-rate
fit, on a scaled hull, against the daily series.

## Why that fit does not transfer

DP's 19.2% is a *post-intervention* outcome: the 5 February cabin quarantine
was in force for the second half of the outbreak, which is why this repository
declares SOP-017 on days 16–30 of `diamond_princess_2020` with
`confinement_enforced: true`. Upstream's 18.6% is a run with no arrest layer,
and the same parameterisation with its Isolation protocol applied yields 4%.
The historically correct configuration therefore *undershoots* DP by roughly
five-fold on upstream's own numbers, and the reported match is a no-response
run scored against a with-response observation. It is a coincidence of
magnitude, not a reproduction of mechanism, and it cannot be inherited as
evidence that the arrest layer is calibrated.

## Why the two engines cannot fail the same way

Measured by reading the upstream source at `bckirkup/infection-dynamics`
`8d159f4` (`NorwalkVirus/Source/CruiseShipModel/`, excluding vendored
GeoMason):

- Exposure is a geometric proximity query at `foot/2` = 0.1524 m, every
  `infectInterval` = 20 minutes, and the number of targets an infectious agent
  may infect in that step is drawn from `avgR = {1,2,1,2,1,1,1,2,1,1,1,2}` —
  so at most two per shedder per 20 minutes (`Person.java:318-357`).
- The infection decision is **not** stochastic and does not accumulate dose.
  `becomesInfected` computes the beta-Poisson
  `P = 1 − (1 + dose/β)^(−α)` with α = 0.111, β = 32.81 and returns
  `infProb > 0.5`; the Bernoulli draw is present only as commented-out code
  (`Person.java:157-180`). The dose passed in is the *source's* own shedding
  value, not anything the target received.
- With those coefficients the 0.5 threshold sits at dose 1.69e4, i.e.
  log10 shedding − `doseAdjustment` > 4.23. The symptomatic curve
  (`Person.java:40-44`, `doseAdjustment` = 4) is 7.75 on day 0 (P = 0.435,
  below threshold) and 9–11 on days 1–9 (P = 0.59–0.75, above). Recovery zeroes
  shedding at day 3 (`Person.java:280-290`).
- There is no active environmental route at all: viral-particle creation in
  `Agent.java:455-461` and the particle's own infection block in
  `ViralParticle.java:28-45` are both commented out. No room air, no cabin air,
  no HVAC transport, no surface reservoir.
- 20% of the population starts immune (`immuneRatio = 0.2`,
  `Person.java:44-46`), and the ship model runs 15 days
  (`Ship.java:51-52`).

The consequence — inference, not a measured number — is that in that engine the
attack rate is a *contact-opportunity count*, not a dose response. Above the
threshold the dose term is a constant `true`; pathogen quantity cannot move the
outcome, and only the incubation/shedding window, the immune fraction and how
often two agents come within 15 cm can. An outbreak stops at 19% there because
sub-16-cm encounters are scarce, not because transmission is arrested.

This port is the opposite construction. Per-epoch dose from direct contact,
short-range droplet/near-field air, HVAC-transported airborne pool and fomite
is summed per agent (`engines/transmission_core.py::_accumulate`,
`_merge_pathogen_doses`) and resolved in a single exponential hazard draw,
`-math.expm1(-susceptibility * effective_dose)`
(`transmission_core.py:2991-2999`, `3839-3891`); Θ enters as
`susceptibility_scale` (`picard_framework/covid_theta_fit.py:194-228`), and the
COVID fit sets `immune_fraction = 0.0` over a 32-day voyage. Because the
dominant terms are shared-air concentrations, the dose delivered to occupants
of one air volume is near-uniform, so the population crosses the hazard
together: extinction below, saturation above, with no intermediate band. That
is the mechanism the v9 surface exhibits, and it is a property of the dose
construction rather than of Θ.

## Consequences for this repository

1. "The predecessor fit the attack rate" is true as a citation and void as an
   inheritance. Do not use it as evidence that this port's arrest layer, or its
   dose scale, was ever calibrated against DP.
2. The VSP-shadow monograph's attack-rate fit (`docs/reports/05_vsp.tex`) is a
   post-response norovirus/VSP band at `dose_adjustment` 10.6, not a COVID DP
   fit; it is unaffected by this entry and equally non-transferable.
3. The open question is not which target to fit. It is whether an enforced
   cabin quarantine in *this* engine can arrest a respiratory outbreak at all
   while shared-air routes remain active. That is measurable, and it is what
   `covid_quarantine_attribution_v1` exists to measure.
4. The decisive arm for this entry is the one that switches the shared-air
   terms off together, leaving contact and fomite — the configuration closest
   to the upstream engine. If an intermediate attack rate appears only there,
   the bimodality is a property of the air model, not of Θ or of the response
   layer.
