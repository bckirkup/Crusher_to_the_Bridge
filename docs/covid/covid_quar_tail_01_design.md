# QUAR-TAIL-SEAM-01 design

**Status:** frozen, pre-results.

Executes the discriminating probe declared in
[COVID-QUAR-TAIL-01](../ledger/COVID-QUAR-TAIL-01.md): port the
CREW-WINDOW-02 reduced-exempt arm grammar to the right-sized-truth
operating point (boxed_s1s2, θ=3.162e8) and test the dual prediction —
during-window mass into the record-informed band [150,350] AND
confirmed-per-infection capture ≥ 0.80 (toward the record's ~0.85).

## Arms

| arm | overrides | lever |
|---|---|---|
| D0_declared | — | shipped default; pairing base + drift witness vs committed `dp_theta_8p50` cells |
| ZONE_NARROW | `SOP-017-NARROW` | exempt-share lever alone (11 essential zones, ~0.32 expected) |
| ZN_DUTY | `SOP-017-NARROW` + `crew_duty_exclusion` | record-warding composition (canary) |
| F25_DUTY | `SOP-017-QUARTER` + `crew_duty_exclusion` | fractional alternative (261/1045 drawn) |

All non-D0 arms are non-scoring discriminating probes. ZONE_NARROW alone
isolates the exempt-share lever from the symptomatic-removal lever so a
HALF-LANDED-MASS result is attributable.

## Frozen admissibility

Verbatim from the design JSON's `admissibility` block (frozen before any
cell exists): SEAM-LANDED = takeoff-conditional during median ∈ [150,350]
AND capture median ≥ 0.80 AND before-mass seed-paired unmoved; the
sub-combinations report as HALF-LANDED-MASS / UNDER-DAMPED / OVER-DAMPED /
UNMOVED with reach-echo audits first.

Non-goals: no arm becomes the boxed_s1s2 default on this evidence alone —
that is an owner declaration call; the ignition-lateness factor from
COVID-QUAR-TAIL-01 is out of scope here (arms fire inside/after the
window only).
