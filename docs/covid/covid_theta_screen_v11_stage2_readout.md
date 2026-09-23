# COVID Theta screen v11 — stage-2 readout: the conditional clause fails at every admissible Θ; the admissible set is empty and the deficit is localised to conditional outbreak size

> **Status:** Findings (2026-09-22), stage 2 complete — the arm's screen
> question is closed. Campaign `covid_theta_screen_v11_stage2`, declared in
> `picard_framework/runs/covid_theta_screen_v11_stage2_design.json` (frozen
> in the same change as the refine readout). **All 100 stage-2 cells have
> run** on AWS Batch at `main` = `8cda4c7`, image
> `picard-campaign:theta-v11-s2-8cda4c7`
> (`sha256:1eb7a01899f10cf417309c3460ad1207176fe064ac0f9b2ecc66cc64b086f947`),
> job definition `picard-covid-boarding-screen:16`, canary
> `e530602b-b0a6-41ba-af9f-d872172653bc` (20 cells at INDEX_OFFSET 40) +
> array `c237e916-8000-4d28-80cd-192ed2daaed0` (size 100). 100 of 100
> children SUCCEEDED, zero failures. Cells:
> `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_screen_v11_stage2/8cda4c7/cells/`.
> Merge: `python3 tools/fit_covid_theta.py screen --design
> picard_framework/runs/covid_theta_screen_v11_stage2_design.json --cells
> <cells> --out
> telemetry_buffer/observation_model/covid_theta_screen_v11_stage2.json`;
> flat table `docs/covid/covid_theta_screen_v11_stage2_surface.csv`. No
> Theta is claimed here; nothing below may be quoted as a fit.

Every figure below is measured at `8cda4c7` inside the campaign image on
the declared Diamond Princess replay — onset_day −1.0, departure_day 5.0,
dwell_weighted sanitary visits, one import, infection_age 3.3 carried,
the same 20 matched seeds at base 20200205 as v10 and QUAR-ATTR-V2,
768 epochs (32 days) with the declared intervention schedule — at the
Θ points the v11 clause enumerated from the refine stage-1 admissible set
{3.16e10, 4.22e10, 5.62e10} plus boundary flanks 2.37e10 and 7.5e10.

## 0. Canary

The Θ 3.16e10 row (all 20 seeds, array `e530602b`, 20/20 SUCCEEDED) was
read before the remaining 80 cells: the declared audit invariant held in
every cell — `index_onset_day == -1.0`, `index_shedding_at_day0` true —
and the row was non-degenerate (19/20 takeoff, recorded_onsets
2,085–3,561). The invariant additionally held in 100% of all 100 cells
(index_geometry_pass_fraction = 1.0 on every row).

## 1. Stage-2 surface — conditional clause scored on takeoff seeds

Clause (frozen, verbatim from v11): among seeds with `recorded_onsets ≥ 10`
(takeoff), the q05–q95 interval of `recorded_onsets` contains 197 AND the
takeoff seeds' median `before_share` is within 0.10 of 0.173; ≥5 takeoff
seeds or "insufficient takeoff mass". Candidate rows are the three
stage-1-admissible Θ; flank rows are reported as band edges, never
selected on.

| Θ | role | takeoff | ro q05–q95 (takeoff seeds) | contains 197 | before_share med | pass |
|---|------|--------:|----------------------------|:------------:|-----------------:|:----:|
| 2.37e10 | flank | 18/20 | 2,355 – 3,543 | no | 0.768 | False |
| 3.16e10 | candidate | 19/20 | 2,668 – 3,544 | no | 0.775 | False |
| 4.22e10 | candidate | 19/20 | 2,497 – 3,550 | no | 0.854 | False |
| 5.62e10 | candidate | 19/20 | 2,241 – 3,564 | no | 0.872 | False |
| 7.5e10 | flank | 19/20 | 2,088 – 3,562 | no | 0.919 | False |

## 2. Verdict: no admissible Θ exists on this arm

Every row fails the clause on mass, not on the interval: takeoff seeds
record a median ~3,469–3,520 onsets against the record's 197 — **~17.7×
over** — with the q05–q95 band (roughly 2,100–3,560) never approaching
it. `onset_mass_near_target` (takeoff seeds within [98.5, 394]) is
**0.00 on every row**: this is not a v7-style interval-span pass
structure; there is no seed anywhere near the record. `before_share`
runs 0.77–0.92 against 0.173 — onsets arrive essentially entirely before
the day-17 split at every Θ.

The unconditional read is the same shape: takeoff fraction 0.90–0.95 on
the declared geometry (vs 0.44–0.57 on generic voyages at the same Θ —
a symptomatic-at-boarding index takes off far more reliably than a drawn
incubation), and taken-off voyages run to median attack ~0.95 —
~3,500 infections on 3,711 hosts — a burn, not the observed 712-case
voyage. The θ ordering inside the takeoff class is monotone but weak:
recorded mass moves only ~1% across the band — **Θ still does not move
conditional outbreak size**, the v9/v10 finding reproduced at
eighth-decade resolution on the declared geometry.

## 3. The two surfaces disagree in the informative direction

The generic-voyage conditional read at the same Θ was median 129.5–247
recorded onsets in a 7-day voyage — at DP order, some seeds below the
record. The declared 32-day replay at the same Θ produces ~3,500. The
difference between those two numbers is the whole screen's answer: the
fleet's *typical* voyage at admissible Θ is calibrated (H3-shaped), but
the *conditioned, intervention-scheduled* voyage cannot be arrested —
the outbreak ignites between day −1 onset and the day-16 intervention
start and saturates before quarantine can bind. This is the
during-quarantine arrest gap of COVID-VENT-AUDIT-01, measured now at
eighth-decade Θ resolution inside the fleet-admissible band: **the
deficit is conditional outbreak size, exactly the localisation this
screen was designed to produce.**

Diagnostics (never thresholded): `campaign_positives` median falls
230 → 195 across the band against T3's 634 (the declared quarantine-era
testing channel undershoots the record in the same direction the onset
mass overshoots — the simulated burn completes before the campaign can
see it); asymptomatic share ~0.30 median against T4's 0.5047; index
geometry 1.0 on every row (declared invariant held).

## 4. Trigger review (`report_immediately_if`, all evaluated)

- Audit invariant failure → not met (1.0 pass fraction on all 100 cells).
- Every admissible row "insufficient takeoff mass" → not met (18–19
  takeoff seeds per row) — takeoff is not the deficit.
- Child failure > 5% → 0/100.
- Interval-spanning pass with zero onset-mass → not met (no row passed;
  mass near target is 0.00 everywhere).

## 5. What this closes, and the decision it leaves

Both stages of the v11 screen are now measured: the fleet-shape selector
admits {3.16e10, 4.22e10, 5.62e10} on generic forward-looking voyages,
and the declared-replay clause fails at all three (and at both flanks) —
the **admissible set is empty**, reported with nearest-cell reads per the
selection clause. There is no Θ to carry to the held-out Greg Mortimer
stage 3, which per the design does not run.

The measured answer to the screen's question is the one pre-declared in
v11's admissibility note: takeoff is achievable — a Θ that reproduces
the fleet's near-critical shape exists — but no Θ at which that fleet
shape holds can keep a taken-off declared voyage near the record's 197
onsets. The conditional outbreak size is the broken quantity, ~18× too
large. **Next decision for the user:** whether the COVID arm pivots to
that deficit directly — the quarantine-era arrest gap (intervention
strength/timing at the day-16 boundary, isolation effectiveness, or the
crew-work continuation channel) — rather than further Θ geometry, which
is now measured not to carry it.
