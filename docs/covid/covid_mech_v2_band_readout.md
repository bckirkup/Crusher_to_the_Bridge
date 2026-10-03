# COVID-MECH-V2 band readout — RINGCAP-V1 dead, SUSCPOOL-V1 dead under `once_per_course`

**Status: measured.** The surviving-arms re-measurement of the
mechanism assays on the v15-paired designs is complete: the replay
clause verdict and the fleet-shape response, scored verbatim at
`def39066` (PR #850 designs; image digest `sha256:516b0b57…`, jobdef
`picard-covid-boarding-screen:46`, On-Demand queue, 700/700 children
SUCCEEDED, 0 audit failures).

Submitted scope per the user decision after the anchor canary
(`docs/covid/covid_mech_v2_canary_readout.md`): the collapsed
`rings_first` rows were skipped entirely; SUSCPOOL replay rows
{declared, f050} × {1.78e11…5.62e11} × 20 seeds (200 cells) plus the
anchor row from the canary; SUSCPOOL fleet rows {declared, f050} × 5 θ
× 50 seeds (500 cells). f025/f075 band rows are unrun —
`row_never_landed` entries in the report are that declared scope, not
failures.

## SUSCPOOL replay — the clause verbatim at every band row

| arm | θ | takeoff n | q05–q95 recorded onsets | before_share med | clause |
|-----|------|-----------|-------------------------|------------------|--------|
| declared | 1e9 | 10 | 153–2438 | 0.090 | PASS (anchor) |
| f050 | 1e9 | 6 | 169–1193 | 0.150 | PASS (anchor) |
| declared | 1.78e11 | 19 | 1735–2619 | 0.873 | FAIL |
| f050 | 1.78e11 | 9 | 910–1290 | 0.687 | FAIL |
| declared | 2.37e11 | 20 | 1739–2618 | 0.904 | FAIL |
| f050 | 2.37e11 | 9 | 411–1293 | 0.737 | FAIL |
| declared | 3.16e11 | 20 | 1610–2641 | 0.951 | FAIL |
| f050 | 3.16e11 | 8 | 878–1326 | 0.900 | FAIL |
| declared | 4.22e11 | 19 | 1471–2630 | 0.944 | FAIL |
| f050 | 4.22e11 | 9 | 858–1310 | 0.897 | FAIL |
| declared | 5.62e11 | 19 | 1487–2639 | 0.957 | FAIL |
| f050 | 5.62e11 | 9 | 806–1329 | 0.863 | FAIL |

**f050's anchor PASS is a boundary-endpoint phenomenon — it does not
survive the admissible band.** At every admissible θ the takeoff-seed
q05 floor sits at 411+ (2–6× the record's 197) and the before_share
median runs 0.69–0.90 against the 0.173±0.10 window — the
once_per_course draw moves the *timing* leg the wrong way as hard as
the count leg.

Drift audit clean: `declared` reproduces the v15 stage-2 parent
seed-for-seed exactly at all six θs (every paired delta 0.0, 0
takeoff-class flips, n=20 each). f050's effect is a real, monotone
mechanism move: paired vs v15 it cuts takeoff-seed recorded onsets by
a median −1340 to −2525 per θ row and flips 10–12 of 20 takeoff
classes — but the ~2× susceptible-pool cut is nowhere near the ~10×
gap the admissible band carries.

## SUSCPOOL fleet — the H3 (Willebrand) window response

The fleet-shape check is report-only by declaration — no row is
admitted or rejected. Per-(θ, arm) rows at 50 seeds paired to the
first-50 v15 stage-1 block (the declared baseline reproduces it
seed-for-seed — all paired deltas 0.0, notches_up 0):

| θ | declared median AR (IQR) | f050 median AR (IQR) | f050 in H3 window |
|------|--------------------------|----------------------|-------------------|
| 1.78e11 | 0.0058 ([0.0001, 0.0265]) | 0.00027 ([0.0000, 0.0104]) | no — sagged *below* floor |
| 2.37e11 | 0.0113 ([0.0001, 0.0314]) | 0.00094 ([0.0000, 0.0103]) | **yes** |
| 3.16e11 | 0.0128 ([0.0003, 0.0445]) | 0.0032 ([0.0000, 0.0121]) | **yes** |
| 4.22e11 | 0.0224 ([0.0003, 0.0443]) | 0.0043 ([0.0000, 0.0154]) | **yes** |
| 5.62e11 | 0.0201 ([0.0007, 0.0622]) | 0.0061 ([0.0000, 0.0188]) | **yes** |

**f050's fleet response sags the H3 window — and that is the
interesting half of the three-body answer.** At the same-50-seed
comparator the band interior runs hot on fleet shape: declared is in
the window only at 1.78e11 and above the 0.008 median ceiling at the
other four θs. The half-pool drops the median attack 4–5 lattice
positions at the high θs, landing inside the H3 window at all of
θ ≥ 2.37e11 (and through the floor at 1.78e11 — over-sag at the band
edge). Per-seed deltas are monotone non-positive (no sign flip: the
declared `upward_lattice_notch` trigger never fires), fizzle
probability P(recorded ≤ 0.01) rises 0.36–0.56 → 0.58–0.74, takeoff
fraction falls 0.62–0.72 → 0.38–0.60.

Jointly: the mechanism produces cross-ship-shaped outbreaks where the
unmodified band cannot — **but only at θs where the replay leg is
already dead by ~5×**. A follow-on re-screen would have to find a
fraction × θ point that is simultaneously in the H3 window and within
reach of the 197 conditional band; at f050 the two are separated by
~4 lattice notches of attack rate. The design's own grammar reserves a
re-screen for a clause PASS, which never came — but this table is the
map a future pool-fraction or multiplicative-mechanism design needs.

## Verdicts

- **COVID-RINGCAP-V1 — dead under the current engine.** Premise
  collapsed at the anchor (`docs/covid/covid_mech_v2_canary_readout.md`);
  ring-first budgeting cannot rescue the presentation-repaired draw.
  Status → closed.
- **COVID-SUSCPOOL-V1 — dead under the current engine.** The f050
  premise survived the anchor re-measure but fails the clause at every
  admissible θ; f025/f075 remain unmeasured on the band (same sign of
  failure as their stale canary reads; run only if a future design
  wants them). Status → closed. The fleet-shape response is measured
  and recorded above for any successor design.

## Provenance

Engine `def39066` (PR #850); image
`picard-campaign@sha256:516b0b57b7f7aebea3b301c891d5dfdb10599e9cca271db69fa1610d983484fd`;
jobdef `picard-covid-boarding-screen:46`; queue `picard-analysis-queue`.
20 array jobs (10 replay × 20 cells, 10 fleet × 50 cells); cells under
`campaign/covid_mech_v2/def39066/cells/` and
`campaign/covid_mech_v2_fleet/def39066/cells/` with manifest + designs.
Readouts: `tools/covid_mech_v2_readout.py` (replay) and
`tools/covid_mech_v2_fleet_readout.py` (fleet, new this PR).
700/700 children SUCCEEDED — 0% failure rate. Note: band cells landed
under the nested `cells/cells/` sub-prefix (submit `S3_PREFIX` carried
the `cells/` segment the worker appends); data intact, convention
documented.
