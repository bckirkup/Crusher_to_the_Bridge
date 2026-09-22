# THETA-SCREEN-V11
**Date:** 2026-09-22
**Commit:** 32d1842
**Pathogens:** sars_cov2_resp
**Status:** declared

Declared only; no cell has run.

## Declared (before any cell runs)

`covid_theta_screen_v11`
(`picard_framework/runs/covid_theta_screen_v11_design.json`) resolves the
admissibility-criterion decision left open by THETA-SCREEN-V9/V10 — the choice
posed verbatim in `docs/covid/covid_theta_handoff_2026_09_21.md` §8:
**T1 trajectory with import geometry as the swept axis, versus takeoff
probability against covid.H3 with onsets scored conditional on takeoff.**
This design declares the second.

**Why.** V9 (`0fb186b`) and its re-measurement V10 (`a9b4f1f`) established that
Θ moves the probability that one declared import takes off (0 at ≤ 1e3 →
0.90 at 1e10), not the size of a taken-off voyage (conditional median onsets
1,582–3,391 from 1e6 up, against covid.T1's 197), and that covid.T1 as
declared is satisfiable by an interval spanning 197 between extinct and
burning seeds (`onset_mass_near_target` 0.00 at the sole pass). A selector Θ
cannot move is vacuous. V11 therefore inverts the v10 stage ordering: the
fleet-shape block v10 reserved as a post-hoc held-out refuser becomes the
stage-1 **selector**, scored as the across-voyage attack-rate distribution
against covid.H3 on generic 7-day voyages, and the declared Diamond Princess
replay is scored **only on seeds that took off** — the record's voyage is a
taken-off voyage, and scoring extinct seeds against it is the category error
that made T1 vacuous.

**The two-clause criterion** (frozen in the design file, verbatim there):

- **Fleet-shape selector (stage 1).** Eight decade Θ (1e4–1e11) × 200 generic
  voyages each = **1,600 cells**, seed base 20201001. Generic voyage = the
  declared seed's `onset_day`/`departure_day` dropped, infection age drawn
  from the profile's incubation distribution, 168 epochs, no intervention
  (every declared mechanism starts after day 7). Criterion verbatim from the
  v10 `stage_2_fleet_shape` block: median recorded attack rate within
  [0.0005, 0.008], IQR overlapping [0.0003, 0.015], mean ≤ 0.06.
- **Conditional trajectory clause (stage 2).** Declared replay cells at each
  stage-1-admissible Θ (v10 cell shape, 20 matched seeds at base 20200205),
  scored only among takeoff seeds (`recorded_onsets ≥ 10`): the takeoff
  seeds' q05–q95 interval of `recorded_onsets` contains 197 AND their median
  `before_share` is within 0.10 of 0.173. Scored only when a cell has ≥ 5
  takeoff seeds; below that it reports "insufficient takeoff mass", not fail.
- **Joint admissibility; the admissible set may be empty.** On an empty set
  the readout reports the nearest cells on each clause and the located
  takeoff band and states that no admissible Θ exists on this arm; no
  criterion is loosened after the fact. Pre-declared expectation: the H3 band
  sits near the takeoff transition and the conditional clause fails there
  (conditional medians ~10× over target at `a9b4f1f`), so the expected result
  is an empty set localising the deficit to conditional outbreak size — the
  during-quarantine arrest gap of COVID-VENT-AUDIT-01 — not to takeoff.

**Declared role change.** covid.H3 leaves the held-out set for this screen:
it is the stage-1 selection anchor, because the only training-side selector
(unconditional covid.T1) is measured vacuous on this arm and the Willebrand
2022 fleet distribution is the only anchor that exists for voyage-level
takeoff. covid.H1/H2 (`greg_mortimer_2020`, stage 3, gated) remain held out
and are the check this screen never selected on; T2/T3/T4, VSP-crossing and
burn-tail remain diagnostics, never selected on.

**Rejected alternative recorded in the design file** (T1 + import geometry):
unconditional T1 is measured vacuous; imports > 1 is measured negative
(COVID-FIT-01, `a686114`, 1,180 cells: matching early onsets overshoots the
voyage total 3–6× on every Θ row) and unlicensed by the record (Sekizuka
2020, single introduction); independently timed imports are not expressible
in the screen machinery.

**Worker support not yet present.** `apply_boarding_axis` mutates only seed
count, infection age and sanitary-visit mode; the generic-voyage mode
(drop onset/departure, drawn age, 168 epochs) and the stage-2 enumeration
need a `voyage_mode` branch before any cell runs. This declaration commits
the criterion only; the next session implements the worker path, runs the
two-part canary (stage-1 Θ 1e8 × 200 generic voyages + the (1e9, 20200205)
replay reproduction cell at 3458 / 0.9318), stops and reports.

## Validation gate (local, this PR)

- `DESIGN=covid_theta_screen_v11 deploy/aws/submit_covid_boarding_screen.sh
  --dry-run` prints array size **1600**.
- `load_design` accepts the file (imports contains 1, infection_age_days
  contains 0.0; unknown keys — `voyage_mode`, gated stage blocks, the
  rejected-alternatives record — are ignored as in v10).

## Result

Not run. Stage 1 is 1,600 generic-voyage cells behind a worker change and a
canary; the canary is declared in the design file's `execution.canary` block.
