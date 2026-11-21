# QUAR-TAIL-SEAM-01 design

**Status:** frozen, pre-results.

Executes the discriminating probe declared in
[COVID-QUAR-TAIL-01](../ledger/COVID-QUAR-TAIL-01.md): reduced-exempt /
symptomatic-removal compositions on the verbatim boxed_s1s2 replay at the
right-sized-truth operating point (θ=3.162e8), testing the dual
prediction — during-window mass into the record-informed band [150,350]
AND confirmed-per-infection capture ≥ 0.80 (toward the record's ~0.85).

Every cell runs the design's `base_overrides` — the boxed_s1s2 resolved
configuration (SOP-017-MESSBOX: 11-zone essential exempt list + boxed
crew meals; section-bound steward service; retest tiers + day-34 crew
wave) — with only the arm's declared delta composed on top (arm keys
win). `funnel_echo` is armed so the CAPTURE-01 decomposition resolves on
completed cells. The committed 8p50 cells already carry the zone-narrowed
exempt list and read realized_exempt_share 0.27–0.31 at activation
(illness pre-confinement); a plain SOP-017-NARROW arm would have been
redundant on the share axis AND would have stripped boxed meals, so the
share lever is expressed as the exact-quarter fraction instead.

## Arms

| arm | overrides | lever |
|---|---|---|
| D0_declared | — | boxed_s1s2 verbatim; pairing base + drift witness vs committed `dp_theta_8p50` cells |
| MB_DUTY | `crew_duty_exclusion.enabled` | VSP 4.4.1.1.1 symptomatic-crew removal on the committed exempt structure (canary) |
| FRAQMB | `SOP-017-QUARTERMB` | exact-quarter fraction (261/1045 drawn) vs the zone lottery, boxed meals kept |
| FRAQMB_DUTY | `SOP-017-QUARTERMB` + `crew_duty_exclusion` | both levers |

All non-D0 arms are non-scoring discriminating probes.
`crew_duty_exclusion` is a standing policy (it binds symptomatic crew
before day 16 too), so before-window movement on DUTY arms is an expected
reported effect, not a violation.

## Frozen admissibility

Verbatim from the design JSON's `admissibility` block (frozen before any
cell exists, thresholds under `audit_thresholds`): SEAM-LANDED =
takeoff-conditional during median ∈ [150,350] AND capture median ≥ 0.80
AND before-mass seed-paired unmoved (DUTY arms exempt from the last);
rows under 5 takeoff cells report INSUFFICIENT-TAKEOFF-MASS; the
sub-combinations report as HALF-LANDED-MASS / UNDER-DAMPED / OVER-DAMPED /
UNMOVED with reach-echo audits first.

Non-goals: no arm becomes the boxed_s1s2 default on this evidence alone —
that is an owner declaration call; the ignition-lateness factor from
COVID-QUAR-TAIL-01 is out of scope here (arms fire inside/after the
window only, modulo the standing-duty caveat above).
