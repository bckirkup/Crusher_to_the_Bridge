# COVID Theta screen v11 — stage-1 readout: empty admissible set on the decade lattice; the H3 window is bracketed between 1e10 and 1e11

> **Status:** Findings (2026-09-22), stage 1 complete. Campaign
> `covid_theta_screen_v11`, declared in
> `picard_framework/runs/covid_theta_screen_v11_design.json` (as amended by
> #655 — see §0) and `docs/ledger/THETA-SCREEN-V11.md`. **All 1,600 stage-1
> cells have run** on AWS Batch at `main` = `7660392`, image
> `picard-campaign:theta-v11-7660392`
> (`sha256:22f5873389e99493c82ec3c2964612a54091677b434e6bc62ed7d542a45b1b7e`),
> job definition `picard-covid-boarding-screen:14`, array job
> `33482fcc-7954-4566-928d-7052d62b83ee` (size 1600) on
> `picard-campaign-queue`. 1,600 of 1,600 children SUCCEEDED, zero failures,
> ~28 min fleet wall-clock. Cells:
> `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_screen_v11/7660392/cells/`.
> Merge: `python3 tools/fit_covid_theta.py screen --design
> picard_framework/runs/covid_theta_screen_v11_design.json --cells <cells>
> --out telemetry_buffer/observation_model/covid_theta_screen_v11.json`;
> flat table `docs/covid/covid_theta_screen_v11_surface.csv`. No Theta is
> claimed here; nothing below may be quoted as a fit.

Every figure below is measured at `7660392` inside the campaign image, seeds
`20201001 + k`, k = 0..199 per Θ, `diamond_princess_2020` hull, one
introduction whose infection age is drawn from the profile incubation
distribution (lognormal, median 5.8 d, clamped [0.5, 21]), 168 epochs
(7 days, hourly), no intervention ever fires (SOP-017 and the swab campaign
start at day 16), and molecular ascertainment open from embarkation.

## 0. The design amendment that gates every number here

The canary's spec audit (declared verbatim in the design's
`execution.canary` block) found the recorded channel structurally dead: the
DP scenario carries `molecular_ascertainment.start_day: 14` — the day real
onboard testing began on the historical voyage — and onset records require
lab confirmation, so no generic 7-day voyage could ever record an onset.
First canary row: 200/200 SUCCEEDED, `recorded_onsets` 0 on every cell
including one with 2,352 infections. That is a DP-historical particular, not
a prior on generic forward-looking voyages (modern cruises swab from day 0;
the user confirmed the interpretation and the direction). #655 therefore
drops the key in `voyage_mode=generic` only; the declared replay keeps
day-14 ascertainment and canary (b) reproduced the QUAR-ATTR-V2/v10 record
exactly (infections_total 3458, attack_rate 0.9318) before and after. The
design file's `voyage_mode_note` and canary text were amended in the same
change. Canary (a) re-run on the fixed spec: 200/200 SUCCEEDED,
`recorded_onsets` 0→324 across the row (median 0, 33 takeoff seeds).

## 1. Stage-1 surface — recorded-channel fleet shape vs covid.H3

Selector (frozen): median recorded attack rate ∈ [0.0005, 0.008] AND
IQR overlapping [0.0003, 0.015] AND mean ≤ 0.06. H3 target (Willebrand
2022): median 0.002, IQR 0.0003–0.015, mean 0.037.

| Θ | P(takeoff) | takeoff seeds | recorded median | q25 | q75 | mean | P(rec ≥ 0.015) | fleet_shape_ok |
|---|-----------:|--------------:|----------------:|----:|----:|-----:|---------------:|:--------------:|
| 1e4  | 0.000 | 0/200   | 0 | 0 | 0 | 0.0001 | 0.000 | False |
| 1e5  | 0.005 | 1/200   | 0 | 0 | 0.0003 | 0.0002 | 0.005 | False |
| 1e6  | 0.030 | 6/200   | 0 | 0 | 0.0003 | 0.0006 | 0.015 | False |
| 1e7  | 0.090 | 18/200  | 0 | 0 | 0.0003 | 0.0020 | 0.060 | False |
| 1e8  | 0.165 | 33/200  | 0 | 0 | 0.0003 | 0.0050 | 0.105 | False |
| 1e9  | 0.225 | 45/200  | 0 | 0 | 0.0005 | 0.0104 | 0.155 | False |
| 1e10 | 0.355 | 71/200  | 0.0003 | 0 | 0.0125 | 0.0256 | 0.250 | False |
| 1e11 | 0.575 | 115/200 | 0.0158 | 0 | 0.0985 | 0.0746 | 0.505 | False |

## 2. Verdict: the stage-1 admissible set is empty — the H3 window is bracketed, not excluded

No lattice Θ passes the fleet-shape selector, so **the admissible set is
empty and stage 2 does not run** (per the design's `admissibility.selection`
clause). Per the same clause this readout reports the nearest cells and the
located band rather than claiming the screen found nothing:

- **Nearest cell below: Θ 1e10.** Fails on the median alone — 0.00027
  against the 0.0005 floor (a 1.85× miss) — while its IQR [0, 0.0125]
  overlaps the target window and its mean 0.026 ≤ 0.06 passes.
- **Nearest cell above: Θ 1e11.** Overshoots two clauses — median 0.0158
  above the 0.008 ceiling (2.0×), mean 0.075 above the 0.06 cap (1.24×);
  the IQR still overlaps.
- **Located band.** The fleet-shape window is entered and exited within the
  same decade: between 1e10 and 1e11 the recorded median climbs ~59×
  (0.00027 → 0.0158) while the mean climbs 2.9× and crosses its cap. An
  admissible Θ, if one exists, lives strictly inside (1e10, ~7e10). The band
  is interior to the lattice — it is not on a boundary — but the takeoff
  transition itself is unresolved at the top edge: P(takeoff) is still
  climbing at 1e11 (0.575), so the takeoff band spans at least
  [1e5, >1e11]. Both observations are reported as required by
  `report_immediately_if` ("admissible set touches the lattice boundary" is
  read here as the nearest-cell pair straddling the top edge with the
  transition unfinished).

## 3. Diagnostics that survive the verdict

- **Index geometry.** `index_geometry_pass_fraction` = 0.52 on every row —
  the share of drawn introduction ages that put the index host already
  symptomatic/shedding at boarding. The other ~48% board presymptomatic and
  onset mid-voyage. Θ-independent (a property of the draw, not of
  transmission); reported as a witness, below its ≥0.80 diagnostic bar — it
  feeds no gate.
- **Conditional-on-takeoff recorded mass is already at record scale.** Among
  takeoff seeds, median `recorded_onsets` rises 57.5 (1e6) → 106 (1e8) →
  142 (1e9) → **175 at 1e10** → 290 (1e11): generic takeoffs at ~1e10
  already produce DP-order recorded burden inside a 7-day voyage, before
  any replay cell runs. This is the measured hint that the conditional
  clause — had stage 2 run — would sit near 197 in the same band where the
  fleet-shape selector sits nearest its window.
- **`before_share` is trivially 1.0** on every generic row — the replay's
  day-17 split has no meaning on a 7-day voyage. Quoted, never gated.

## 4. The conditional read at the decade lattice is quoted from v10

Per `admissibility.selection`: with no stage-1 admissible Θ, the declared
replay does not run and the conditional number is the v10 surface's —
conditional-on-takeoff median onsets **1,582–3,391 from Θ 1e6 up, against
covid.T1's 197** (`a9b4f1f`). The design's pre-declared expectation
(conditional clause fails wherever the fleet clause passes) is supported by
the generic conditional medians in §3 sitting at 175–290, i.e. near or
above the record, at the very edge of the lattice where the fleet clause
comes closest.

## 5. Trigger review (`report_immediately_if`, all evaluated)

- Admissible set touches the 1e4/1e11 boundary → **the set is empty; the
  located band is interior but the nearest-passing side (1e11) sits on the
  top edge with takeoff still rising — reported as boundary-adjacent.**
- Zero takeoff at 1e11 → not met (0.575).
- Replay takeoff-class flip vs v10 → N/A (stage 2 did not run).
- Child failure rate > 5% → 0/1600.
- Stage-1 spec carries declared onset/departure → audited on the canary:
  absent, 168 epochs, no ascertainment key, contract unchanged.

## 6. Next decision — for the user

The design's own empty-set convention is satisfied: nearest cells reported,
band located, stage 2 correctly not run. One question remains open, and it
is the one the screen was built to answer: **does an admissible Θ exist
inside (1e10, 1e11), or does the window fail at every interior point too?**
A decade-lattice readout cannot distinguish "admissible set is a narrow
interior band" from "admissible set is empty everywhere" — the frozen
criterion is the same, and refining the grid is not loosening it.

Recommended next session (one deliverable): **stage-1 refinement** —
same worker, same image, same design with `thetas` replaced by a
half-decade lattice {1.8e10, 3.2e10, 5.6e10} (≈3 Θ × 200 seeds = 600
cells, ~35 core-hours), submitted under the same prefix machinery. Then:
- if any interior Θ passes the fleet selector → enumerate stage-2 replay
  cells at the admissible set plus the 1e10/1e11 flanks (per
  `stage_2.theta_points`) in the following session;
- if none passes → the empty set is measured at sub-decade resolution and
  the arm's deficit is localised as the design intended, with the located
  band the deliverable.

Also worth deciding: whether a future screen should declare a
non-decade-spaced `thetas` array up front, since the recorded channel's
~59×-per-decade slope near the band makes decade spacing coarse exactly
where the selector lives.
