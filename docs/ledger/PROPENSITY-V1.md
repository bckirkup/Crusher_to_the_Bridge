# PROPENSITY-V1
**Date:** 2026-10-02
**Commit:** 63f4f3a9
**Pathogens:** all
**Status:** measured
**Measured at:** e0d43979

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

## Measurement (DP-replay clause canary, `e0d43979`)

`covid_propensity_v1` (40 cells: `{D0_declared party mode, PROP_OFF} ×
Θ1e9 × 20 seeds` at the v15 stage-2 replay contract; readout
`docs/covid/covid_propensity_v1_readout.md`). **The clause fails on both
arms at the anchor**: D0 takeoff 19/20, recorded q05–q95 [1,518, 2,445]
∌ 197 and takeoff before_share median 0.452 ∉ 0.173±0.10; PROP_OFF
takeoff 20/20, [1,190, 2,443], share 0.397 — likewise dead. The
mechanism exercised cleanly (≈2,089 party units per voyage, multiplier
q05–q95 ≈ 0.24–2.4; the off arm drew zero units on every cell — the
bit-identity witness) but its seed-paired footprint is seed noise:
PROP_OFF − D0 deltas med +12 recorded onsets [−923, +657], −0.047
before_share [−0.49, +0.17]. Pairing against the recorded v15 anchor row
(`6efec855`) also shows the anchor itself drifted ~+1,600 median
recorded onsets / 10→20 takeoff seeds under engine merges since then —
independent of propensity — so the v15 anchor clause pass is historical
at its own SHA. The fourth early-COVID failure mode joins the dead
candidates; whether the admissible-band array still runs is the user's
open decision.
