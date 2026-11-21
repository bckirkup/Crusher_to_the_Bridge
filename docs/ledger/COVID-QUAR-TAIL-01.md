# COVID-QUAR-TAIL-01
**Date:** 2026-11-21
**Commit:** 6fa5e3bc
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 6fa5e3bc

Follow-on leg to COVID-CAPTURE-01: the capture deficit at right-sized
truth (θ=3.162e8) reduces to incidence timing — the model's tail
keeps producing infections ~10–15 days past the record's confinement
peak (model days 13–15). This entry decomposes the during/after-
quarantine tail on the same committed THETA-REFIT-01 `dp_theta_8p50`
payloads (16 takeoff cells, pure readout, no re-run). Echoes read:
`infections_before/during/after_quarantine`,
`during_quarantine_by_role/zone_class/route`,
`confined_passenger_infections_during_quarantine`,
`quarantine_witness`, `crew_window`, `crew_duty_exclusion`,
`funnel_hosts` (per-host infection_day × role).

## Result — the tail factorizes into late ignition × an under-damped confinement declaration

**Phase totals (16 takeoff cells, per-cell medians):** before 90 /
during 415 / after 187 infections. The same cells split into two
regimes: three record-timed ignitions (before 1,651–2,240, the cells
whose capture read 0.91–0.93) vs thirteen late-ignition cells
(before 7–283, during 264–835) — the model's exponential phase
ignites ~10 days late on most draws, so the susceptible pool is
undepleted when SOP-017 fires at day 16.

**Post-activation incidence is flat, not declining:** pooled
passenger+crew incidence runs ~250–350/day through days 16–30 —
effective R ≈ 1 in the confined structure where the record went
subcritical after ±2 days. The SOP itself fires on its terms:
passenger acquisition collapses ~10× at day 16 (pooled 1,103 → 117)
— the residual is the *declared* confined-service loop:

| during-window channel | pooled | share |
|---|---|---|
| cabin zone | 5,242 | 72% |
| droplet route | 4,076 | 56% |
| service_to_host (steward delivery into confined cabins) | 2,370 | 32% |
| caregiver | 834 | 11% |
| crew hosts | 4,008 | 55% of during-window infections* |

*the record's ~0.29 is crew share of *whole-voyage confirmed cases* —
a different basis (observation-funnel attribution); read this as
direction (crew carry the confined tail), not a magnitude gap.

`confined_passenger_infections_during_quarantine` ≈ all passenger
during-infections (3,274) — confined hosts are infected *in* cabins,
fed by service deliveries and cabin-mate droplet.

**Declaration witnesses (measured, boxed_s1s2):**
`quarantine_witness` — SOP-017-MESSBOX window [16,30], all four crew
classes exempt; `crew_duty_exclusion` — **enabled: false**
(symptomatic crew keep working and delivering; the record's medical
removed them, and VSP 2018 OM 4.4.1.1.1 makes removal unconditional);
`crew_window` — all 11 work zones exempt, ~286 crew posted to work
zones at activation. (This block carries no `service_deliveries`
echo; CW-02's read 128k–166k steward deliveries/cell at clause-leg θ.)

**After-window release (days 31–34):** 2,836 infections — the
declared window ends day 30; this is post-release mixing plus the
voyage-end tail that lands hosts at dpi ≤4 for the day-34 crew wave
(the capture-impossible pool of CAPTURE-01).

## Cross-reference: the dose-response is already measured

CREW-WINDOW-02 (at the clause-leg thetas 1e6/7.9e6) measured
during-window mass monotone in the realized exempt share: ~0.25–0.31
(FRAC_25 / ZONE_NARROW) lands the record-informed during band
[150,350]; boxed_s1s2's all-classes-exempt declaration realizes
~0.96–0.99 — roughly 3–4× over-declared on the confinement-dose
axis. The CW-02 band was a during-mass target at clause-leg
incidence; at right-sized truth the same lever is what the capture
leg needs.

## Seam design — declared

**The Θ blocker is a two-factor timing defect, and both factors are
now measured handles:**

1. **Confinement dose** (declared, immediate): re-run boxed_s1s2 at
   θ=3.162e8 with the CW-02 FRAC_25 / ZONE_NARROW arm ported to this
   operating point (exempt share ~0.25–0.31, symptomatic-crew
   exclusion armed). Dual prediction: during-window mass falls into
   band AND confirmed-per-infection capture rises toward ~0.85
   (fewer hosts stranded at dpi ≤4 inside the test window). One arm
   change tests the whole seam.
2. **Ignition timing** (harder, hypothesis): the ~10-day-late
   exponential phase at right-sized truth — the within-cabin / early
   seed-ring structure produces a slower front than the record's
   index-driven surge. This is the part that may be intrinsic to
   the dose that sizes the peak correctly; if factor 1 lands the
   during-band and capture, the residual late-ignition mass is the
   honest gap to report against H5 rather than fit away.

Non-goal (recorded, not taken): this does not decide whether the
exempt-share arm becomes the new boxed_s1s2 default — that is a
declaration change to the replay spec, an owner call on the same
footing as the H5 contract decision.

## Non-results

- The SOP-017 activation itself works: passenger acquisition
  collapses ~10× at day 16. Not a machinery defect.
- Crew carry 0.55 of during-window infections pooled — vs the
  record's ~0.29 crew share of whole-voyage confirmed (different
  basis: direction, not magnitude) — an *incidence-timing* artifact
  as much as a confinement one: crew carry the late tail because
  they are the channel still open.
- `hvac_airborne` contributes 15 during-window infections — the
  confined tail is contact/service, not ventilation.
