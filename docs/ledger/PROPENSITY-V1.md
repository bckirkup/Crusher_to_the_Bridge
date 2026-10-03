# PROPENSITY-V1
**Date:** 2026-10-02
**Commit:** 63f4f3a9
**Pathogens:** all
**Status:** declared

## Question

Every declared candidate for the DP residual has been measured dead
(RING-CAP-V1, SUSCPOOL-V1 the last pair), and the miss pattern — ~96% burn
against a 197/712 record — matches the canonical early-COVID model failure:
homogeneous participation. The rhythm layer deals each agent a fresh i.i.d.
Bernoulli on `participation_fraction` per event per day, so every passenger
is the same sociable person in expectation. Is persistent contact-propensity
heterogeneity — the Britton/Ball–Trapman term that makes early epidemic
models overshoot — the missing variance?

## Declaration

`docs/propensity_v1_spec.md` — a persistent per-unit participation
multiplier dealt once on a dedicated stream and consumed at the
`_deal_occurrence` Bernoulli as `min(1, p × propensity)`, restricted to the
discretionary event classes (open_venue, show_performance,
scheduled_activity, meal_seating, port_call). `mode: party` draws one
multiplier per travelling party (families share an activity level);
`mode: agent` is the per-agent arm; `mode: off` is the labelled baseline and
is bit-identical (the propensity stream is never consumed). The unit draw is
mean-pinned lognormal (cv 0.8 declared, gamma arm reserved) times a
per-agent `age_band_mean` tilt applied at read, so venue dose constants and
event denominators are untouched.

## Mechanism

Heterogeneous participation stalls an epidemic because it burns the
high-propensity tail first and leaves low-propensity susceptibles. The
i.i.d. deal removes exactly that term: over a 17-day pre-quarantine window
every agent converges to the same venue exposure. This is orthogonal to the
retired candidates — SUSCPOOL gated susceptibility binary, FRAILTY-V1
conditioned the per-challenge hazard, suppression compressed the calendar;
none touched who shows up.

## Scope

Declared and implemented on the same branch (rhythm layer + delivery echo +
witnesses); no campaign, no refit. The clause canary at the Θ1e9 anchor and
the admissible-band array are the measurement stage and are not run here.
