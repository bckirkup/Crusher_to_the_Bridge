# CONTAM-PHASE3-BASELINE-01
**Date:** 2026-11-19
**Commit:** 5c8f05cc
**Pathogens:** all
**Status:** measured
**Measured at:** 5c8f05cc

**Decision: use the two corrected hulls for a transport-methods comparison.
Do not use this check to certify as-built ventilation, choose a more accurate
airflow model, or infer an outbreak effect.** No pathogen, occupant or
stochastic outcome was simulated. No seeds or AWS jobs apply.

## Measured: numerical checks on the same revision

The [aggregate measurements](../audits/2026-11-19_phase3_transport_baseline/evidence/aggregate.json)
pin both platform directory trees, the full software revision and the ContamX
binary digest. The paired diagnostic compared four airflow fields: native
(declared flows), commissioned (fresh commissioned export), authored (committed
project) and design (fresh design export). The pressure diagnostic applies only
to the three ContamX fields.

| Deterministic check | Expedition cruise 450 | Destroyer baseline |
|---|---:|---:|
| Tracer cells (standard cases × two timings × four fields) | 32 | 24 |
| Maximum absolute mass closure error, per unit emitted | 6.66 × 10⁻¹⁶ | 5.55 × 10⁻¹⁶ |
| Pressure solves completed | 3 of 3 | 3 of 3 |
| Maximum absolute air-balance residual, all three fields (m³/h) | 0.00107 | 0.00000820 |
| Maximum path pressure difference, commissioned / design (Pa) | 89.19 / 9.72 | 10.79 / 1.05 |
| Commissioned make-up demand (m³/h) | 12,541.96 | 716.42 |

Mass closure is emitted minus retained, natural decay and transport loss.
The integrals use a 12-hour horizon, decay 0.10/h, filter efficiency 0.30
and the boundary-sink convention. No retained mass or loss term was negative.
Local plus remote material-time accounted for whole-hull material-time to
within 1.12 × 10⁻¹⁶ h. Air balance is a *different* check: make-up demand
minus net inward flow through the envelope and declared openings. Neither
check tests whether the assumed flow matches an actual vessel.

Authored and freshly commissioned exports returned identical tracer cell
outputs on these cases. This checks bundle consistency, not replication by
an independent solver: all four fields use the same matrix-exponential mass
propagator. The design/commissioned pressure difference on the cruise hull
remains an engineering assumption to check, not a diagnosed defect.

## Measured: effect of transferring the old baseline

For a unit pulse, whole-hull material-time is the integral of remaining
tracer mass divided by emitted mass, in hours. The following are unweighted
means across the same three destroyer reference cases, not passenger-weighted
exposures, room residence times or statistical replicates.

| Destroyer whole-hull material-time (h) | Before, `7cd051da` | Current, `5c8f05cc` |
|---|---:|---:|
| Native | 0.233 | 0.233 |
| Commissioned | 0.264 | 0.409 |

Between these revisions the destroyer airflow declaration, project and path
map changed together; neither the diagnostic nor the transport engine changed.
The [make-up repair](CONTAM-DESTROYER-MAKEUP-01.md) preserved exhaust demand,
but the commissioned tracer integral changed. That is a reason to version
the baseline, not a calibration target for native. The two aggregate means
do not determine which flow path caused the change.

## What this licenses

- **Numerical verification:** compare the corrected models, with revision and
  airflow field named. The Phase 1/2 panels remain evidence for their original
  inputs; their exact-integral addenda are not a re-run on this revision.
- **Physical validation:** still open. No independent pressure, ventilation
  or inert-tracer measurements from an actual vessel entered this check.
  Agreement and conservation cannot substitute for these observations.
- **Epidemiology:** not tested. The within-room exchange map and the inter-zone
  transport field are distinct. At the pinned platform defaults, the cruise
  hull declares positive ambient exchange; none of the destroyer declarations
  is positive. The latter is a possible no-change control for that map, not
  a second positive contrast. No stochastic effect is established by either.

**Next decision:** freeze a separate, aggregate respiratory attribution design
or stop at the methods comparison. If proceeding to design, declare the
paired comparison, null control, uncertainty criterion and stop rule before
looking at outcomes. Verify the intervention actually differs in the intended
arm. No campaign is authorized by this readout.
