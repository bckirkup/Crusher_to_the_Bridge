# COVID-SEED-RING-02
**Date:** 2026-11-22
**Commit:** 3b355b64023343e2151d78b906ca1f86ebc1d0ba
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 3b355b64023343e2151d78b906ca1f86ebc1d0ba

(Image digest sha256:84dbb44299fd47c714dd98a557e5de416a9c9634907e08963111307796ae6611;
jobdef `picard-covid-seed-ring-02:1`; array
`9a81af55-29a3-48a4-91fb-e6766e149fc1`)

The voyage-stage contact-declaration probe commissioned after
COVID-EARLY-GROWTH-01's confounding measurement, run through the canary
gate: θ=3.162e8 (`dp_theta_8p50`) on the verbatim boxed_s1s2 replay, arm
`WINDOW_W1_A8` — day-1 embarkation with `contact_rate_multiplier` 8.0 —
× 20 seeds (20200205–20200224). Mechanism: `voyage_overrides` writes the
voyage itinerary layer; no engine change beyond the per-entry multiplier
pin. 20 cells on AWS Batch, audit invariants clean on every cell
(`effects_enabled: true`, α=8.0 echoed, departure epoch, quarantine
witness, droplet split vs shipped constants).

## Verdict: NULL-WINDOW at α=8 on the 1-day window (legs 1 and 2 fail)

Leg 1 — founder median **4.0** takeoff-conditional (3.0 over all 20
cells) vs the frozen ≥10; ignition median **13** on the 17/17 ignited
takeoff cells vs ≤9; takeoff 17/20. Leg 2 — the 6 record-timed cells
(ign ≤9) hold d15 cumulative-infection median **2,404** vs ≤960,
matching EARLY-GROWTH-01's frozen reading that the routine field
over-produces. Trajectory: recorded_onsets q05–q95 86–2628 vs record
197; before_share median 0.062 vs 0.173. Routes droplet 207 /
caregiver 38.

The surge mechanism fired but as a lottery, not a median: 6/20 seeds
produced record-class founder pools (60, 41, 56, 23, 21, 10) that
ignite days 3–9 — the draws whose index lands inside the day-0 surge
geometry. The remaining ~3/4 ignite days 12–27 on the routine field
alone. Same participation signature as SEED-RING-01's placement null:
the surge exists; the index rarely rides it. Windowed intensity is not
the binding constraint on the founder channel.

The seed-paired drift witness was **not executed** — the D0 block and
the remaining W-blocks (`w1_a2`, `w1_a4`, `w5_a8`) were not submitted;
the owner stopped the campaign at the canary gate (2026-11-22). The
null is read against clean in-cell audits, not a paired replay.

## What the null measures

A single dense embarkation day at α=8 cannot lift the *median* founder
pool to ≥10 — the 3/4 of draws that produce the DP timing need the
index inside the surge geometry, and declaring intensity does not move
participation. The α=2/α=4 dose-response and the multi-day W5
declaration were left unrun; a future session should treat the
participation-vs-intensity split, not window intensity, as the open
question. The θ contract consequence stands as before: envelope or
conditioned scoring is the remaining contract lever, and the routine
contact field remains under-examined (the Pung mapping is still open).

GM still gated; H5 still held out; θ unchanged at 3.162e8.
