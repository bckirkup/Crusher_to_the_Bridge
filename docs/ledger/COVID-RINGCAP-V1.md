# COVID-RINGCAP-V1
**Date:** 2026-09-28
**Commit:** 6085e726
**Pathogens:** sars_cov2_resp
**Status:** closed
**Measured at:** def39066

Declared before any cell ran. Mechanism candidate 1 of the THETA-SCREEN-V13
residual hunt: the fixed rings (cabin-mate ring, same-table dining party)
spend the shedder's per-epoch exposure-cap budget FIRST, so the pooled
droplet/HVAC cohort draws only the remainder. THETA-SCREEN-V13 measured
the conditional clause cap-invariant — the band shifted to
{1.78e11..5.62e11} while takeoff-seed recorded-onsets floors stayed
1,770-2,024 (~9-10x the record's 197) — consistent with ROUTE-ATTR-V1's
~98% ring-side dose weight: the v12/v13 cap gates only the pooled routes
(`_droplet_unit_doses`, `_apply_hvac_downstream_doses`) while the ring
routes (`_cabin_mate_droplet_addback`, `_near_field_unit`, dealt tables)
dose outside it.

## Mechanism

New flag `transmission.exposure_cap.include_fixed_rings` (default false =
v13 baseline, byte-identical — ring accounting adds no RNG draws). When
true, at each shedder's first budget draw of an epoch the count of its
dose-forming fixed-ring contacts is subtracted from the Poisson draw:

- cabin mates aboard and open to infection with a positive co-presence
  share this epoch;
- same-table partners — the dealt meal-table entry when a deal ran this
  epoch, or the fixed dining party (mdr/specialty seating) while the
  shedder stands on a Meal token.

Adjacent-table deals stay inside the pooled reach by declaration: that
ring is venue structure, not a pre-committed contact. Rings still dose;
what changes is how much incidental pooled reach remains. Inert while the
cap is inactive (naval/uncatalogued platforms unchanged).

## Declared

- `picard_framework/runs/covid_ring_cap_v1_design.json` — declared-replay
  clause assay: {1e9 anchor + 1.78e11, 2.37e11, 3.16e11, 4.22e11,
  5.62e11} x arms {cap_on, rings_first} x 20 seeds (base 20200205) = 240
  cells, verbatim v13 stage-2 shape (768 epochs, onset_day −1.0,
  departure_day 5.0, dwell_weighted).
- `picard_framework/runs/covid_ring_cap_v1_fleet_design.json` — coarse
  generic-voyage fleet-shape response: the five admissible Thetas x same
  arms x 50 seeds (base 20201001) = 500 cells. Response check only; no
  selector verdict, no Theta admitted from it.

## Frozen criteria

`conditional_trajectory_clause` and `index_geometry` audit invariant
carried verbatim from covid_theta_screen_v13_stage2. Verdict grammar
(frozen in the design): clause outcome class per (theta, arm), magnitude
class of any residual gap vs the v13 ~9-10x read, before_share direction.
A clause PASS under rings_first triggers a re-screen design on that arm —
it is not an admission.

## Report-immediately-if (carried)

Audit-invariant failure in any cell; every rings_first row reporting
insufficient takeoff mass; clause PASS confined to a boundary endpoint;
failure sign/magnitude-class change vs the v13 read; ring-spend readout
zero on an arm row (flag did not reach the engine); child failures >5%.

## Result

Canary measured 2026-09-28 at `472cdf13` (readout:
`docs/covid/covid_mech_v1_canary_readout.md`) — those readings are STALE:
they predate the PRESENT-SHARE-01 presentation repair
(`presentation_draw_mode = once_per_course`, PR #825).

Re-measured 2026-10-02 at `def39066` on the v15-paired design (PR #850;
image `picard-campaign@sha256:516b0b57…`, jobdef
`picard-covid-boarding-screen:46`, 40/40 anchor cells): under
once_per_course the premise **collapses** — rings_first fails the anchor
clause on both legs (takeoff n 11, q05–q95 405–2460 does not contain
197, before_share 0.343 vs 0.173±0.10) while cap_on anchors cleanly
(n 10, 153–2438 ∋ 197, 0.090). The stale rings_first PASS does not
survive the repaired draw, so the band rows never ran.
Readout: `docs/covid/covid_mech_v2_canary_readout.md`; band context
`docs/covid/covid_mech_v2_band_readout.md`.

Execution: image `covid-mech-v1-472cdf13` (engine `472cdf13`, PR #767;
digest `sha256:10902239ff…`), jobdef `picard-covid-boarding-screen:31`,
Batch `5a815be5-3804-4eaf-9c53-4356d6c36db3`, 40/40 children SUCCEEDED on
the Θ1e9 anchor row (INDEX_OFFSET 0, both arms, seeds 20200205-224).

Flag landed: 9/20 paired seeds differ cap_on vs rings_first (e.g.
20200210: 14 -> 880 recorded onsets; identical pairs are extinct cells).
Audit invariant clean (index_geometry frac 1.0 both arms); rows
non-degenerate; 0% failures.

Anchor-row clause read: cap_on FAIL (before_share med 0.373, q05-q95
[11.75, 3087.25]) — the v13 anchor arm exactly — **rings_first PASS**
(q05-q95 [133.25, 3146.0] contains 197, before_share med 0.128, 6 takeoff
seeds). The PASS is at the boundary endpoint only; whether it survives
the admissible rows is what the full array answers.
