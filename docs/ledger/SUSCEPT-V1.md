# SUSCEPT-V1
**Date:** 2026-09-30
**Commit:** 2e12ccf1
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 2e12ccf1

The SUSCEPT-V1 conditioned array: the surviving lever class after four
measured retirements (COOP-V1 dose law, Θ, ASCERTAIN-V1 channel,
SEED-GEOM-V1 index geometry) all left truth at ~96% of aboard while the
held-out serology band covid.H5 sits at 19–26% — a declared sweep over
susceptibility / effective-population structure, all expressible under
the shipped arm grammar with zero engine changes:

- **Immune depth** — `ship_graph.immune_fraction` ∈ {0.10, 0.25, 0.50,
  0.75} (IMM10/IMM25/IMM50/IMM75): the engineered-health-paradox arm —
  a pre-screened, aged, affluent passenger manifest plausibly carrying
  substantial non-detecting immunity.
- **Immune placement / role split** — `ship_graph.crew_immune_ratio`
  corners: IMM25_C0 (all immunity on passengers), IMM25_C90 (25%
  passengers, 90% crew), IMM0_C90 (the crew-hub-isolation corner:
  passengers 0%, crew 90%).
- **Frailty dispersion** — `dose_response_frailty` α ∈ {0.05, 1.0, 2.0}
  at β 58.0 fixed (the COVID-VULN-01 envelope knots around shipped
  0.18), each at the Θ-preserved `susceptibility_scale =
  Θ(α+β)/α` per the covid_vuln_cells convention: E[susceptibility]
  never moves, only the draw's shape does (α 0.05: heavy near-immune
  tail; α 2.0: near-homogeneous limit).
- **Mixing-saturation corners** — `transmission.exposure_cap`: CAP_OFF
  (per-epoch contact budget removed) and CAP_FR (fixed rings spend the
  budget first), plus the declared interaction cells IMM50_CAPOFF and
  FRAIL_A05_CAPOFF.

Lattice: 16 arms (14 susceptibility + D0_declared paired baseline +
REF_M0P56 channel-matched reference, the ASCERTAIN-V1 M0P56 overrides
verbatim) × θ {1e11, 2.37e11, 1e12} × seeds 20200205–14 = 480 cells.
Design `picard_framework/runs/covid_suscept_v1_design.json` (PR #790,
admissibility frozen before any cell ran). Anchors: covid.T1 = 197
recorded onsets / before_share 0.173 (±0.10 declared window) and the
held-out serology band covid.H5 = infections_total ∈ [712, 960]. No
constants fitted. Immune arms are seed-matched but not draw-paired vs
D0 (immunity dealing consumes RNG draws; declared in the design).

## Execution (measured)

Two AWS Batch array jobs on `picard-campaign-queue` (Spot, no drought),
job-def `picard-covid-boarding-screen:36` digest-pinned to
`picard-campaign@sha256:966eb54be09102ac7af74859fb56c7861bc03e003801d1614af51688aecbc410`
(base image `covid-suscept-v1-2e12ccf` built at merged SHA `2e12ccf1`
plus the `deploy/aws/Dockerfile.covid_hull` `ENTRYPOINT ["python3"]`
layer — rev 35, built straight from the root Dockerfile, fast-failed
its first canary on argv handoff and was superseded before any cell
ran): canary `afb8cbae-2b45-49db-8875-769780b04161` (cells 0–159, all
16 arms at the anchor θ) then remainder
`0ac6c351-c12f-499c-8791-a2a73f4e7783` (cells 160–479). **480/480
cells SUCCEEDED (two children needed Spot retries — one CAP_FR@1e12,
one IMM50_CAPOFF@1e12 — and landed on later attempts).** Payloads under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_suscept_v1/cells/`.

Susceptibility-structure audit on every cell
(tools/covid_suscept_v1_readout.py): **0/480 failures** —
`ship_graph_immune` echoes declared/resolved fractions and the realized
pool hits `int(complement × share)` exactly per role (e.g. IMM25_C90:
passenger 666/2666, crew 940/1045), `dose_response` echoes the
declared α/β and the Θ-preserved `susceptibility_scale = Θ(α+β)/α` at
each lattice point, `exposure_cap_active` resolves correctly on both
cap corners, `susceptibility_draw` and `acquisition_curve` are present
on every armed payload, and REF_M0P56 carries the M0P56
`onset_recording` + eligibility echoes verbatim.

Drift check (frozen in the design): REF_M0P56 reproduces its measured
ASCERTAIN-V1 read — anchor-θ takeoff recorded_onsets median **234**
∈ [207, 270]; D0_declared reproduces the ~3,500-class truth baseline
(3,558 at anchor). No engine drift.

## Both-legs readout (takeoff-seed medians, recorded_onsets ≥ 10)

Truth leg = infections_total median ∈ [712, 960]; timing leg =
before_share median ∈ [0.073, 0.273]; count leg = recorded_onsets
median vs 197.

| θ | arm | takeoff | inf med | share med | rec med | legs |
|---|-----|---------|---------|-----------|---------|------|
| 1e11 | D0_declared | 8/10 | 3,547 | 0.821 | — | — |
| 1e11 | IMM75 | 5/10 | **869** | 0.899 | — | TRUTH |
| 2.37e11 | D0_declared | 7/10 | 3,558 | 0.606 | 3,008 | — |
| 2.37e11 | REF_M0P56 | 7/10 | 3,558 | 0.635 | 234 | — |
| 2.37e11 | IMM75 | 5/10 | **877** [865–893] | 0.942 | 740 | TRUTH |
| 2.37e11 | CAP_FR | 9/10 | 3,461 | 0.205 | 2,417 | TIMING |
| 2.37e11 | FRAIL_A05 | 8/10 | 2,232 | 0.631 | 1,883 | — |
| 1e12 | D0_declared | 9/10 | 3,599 | 0.764 | — | — |
| 1e12 | IMM75 | 6/10 | **884** | 0.961 | — | TRUTH |

(Full per-arm medians in `campaign_results/covid_suscept_v1/readout_full.json`.)

**No declared susceptibility arm moves both legs.** Measured leg
behaviour:

- **Immune depth is the only lever that reaches the truth band, and
  only at the 0.75 corner**: takeoff infections ~869–884 at all three
  θ — a θ-invariant ~24% of aboard (sterilizing pre-immunity caps the
  burn mechanically, dose-independently). Elasticity is strongly
  sub-linear below it: medians ~3,200 (IMM10), ~2,650 (IMM25),
  ~1,750 (IMM50). But IMM75's before_share stays 0.90–0.96 — the
  thinned burn still completes pre-split — and takeoff mass is thin
  (5–6 of 10 seeds; the rest fizzle outright), and its
  recorded_onsets median at anchor (740) still overshoots 197
  ~4-fold. **Truth-in-band without the timing leg, and with a
  fizzle-majority risk at the band edge.**
- **Placement matters at fixed mass**: at 25% immune, putting 90% of
  crew in the pool (IMM25_C90) cuts truth to ~2,000 vs ~2,900 for
  passenger-only placement (IMM25_C0) — the crew stratum carries
  measurable mixing. But IMM0_C90 (crew-hub isolation, zero passenger
  immunity) still medians ~2,660–2,690 — crew immunity alone cannot
  reach the band; passenger susceptibles burn anyway.
- **Frailty dispersion moves truth modestly and only at the extreme
  knot**: FRAIL_A05 (α 0.05, heavy near-immune tail) medians
  ~2,100–2,370 (~1.6–3.6× below baseline depending on θ) — real but
  ~2.5× above the band ceiling. FRAIL_A1/A2 sit at the ~3,710 ceiling
  (no takeoff headroom at all on several seeds — homogeneous draw
  burns everyone). The near-immune tail thins; it does not reach.
- **Cap corners move nothing on truth**: CAP_OFF ≈ baseline at all θ
  (the cap was not the binding constraint — reach saturates before
  the budget binds); CAP_FR leaves truth ~3,460–3,600. CAP_FR's lone
  TIMING-IN-BAND median (0.205 at anchor θ only; 0.767 at 1e11, 0.96
  at 1e12) is **takeoff-set composition**: it rescues seeds the
  baseline fizzles (s20200207, s20200210), whose rescued burns carry
  near-zero shares; seed-paired share deltas on shared takeoff seeds
  are mixed (s20200213 +0.13, s20200214 −0.085). Same artifact class
  as SEED-GEOM-V1's FR_IN.
- **Fizzle pressure grows with immune depth**: takeoff mass 10→9→7→6→5
  across IMM10→IMM75 at anchor — declared expected, since immune hosts
  cannot seed and thinning shortens the early burn below the
  recorded-onset threshold.

## Suppression discriminator (shape leg)

For every row: `infections_during_quarantine` medians 0–700 (row max
CAP_FR@anchor = 696, ~20% of its truth — slow-burn extension, not a
kink), `confined_passenger_infections_during_quarantine` q95 ≤ 6 on
IMM75, and the day-16 kink ratio (days 17–19 vs 13–15 mean daily
acquisitions) sits at 0.0–0.28 on every arm — at or below the
baseline's own 0.15–0.27 decline. **No row is DURING-DOMINANT, no row
shows a post-activation kink.** IMM75's pooled during-quarantine
stratum is tiny (45 acquisitions over 5 takeoff seeds; crew 37 /
passenger 8; crew_mess 23 > cabin 15; all droplet) — no cabin or
confined-passenger concentration.

**The in-band landing reads smooth-thinned, not suppression-kinked**:
IMM75 attenuates the whole curve uniformly and dies mid-voyage rather
than deferring mass into the enforced window — the structure-shaped
signature, per the frozen criterion.

## Verdict

**susceptibility_structure_incapable (for the joint record)** —
effective-population structure reaches the serology band only through
brute-force sterilizing depth (75% of aboard immune at embarkation),
where it lands θ-invariantly at ~870–885 infections — but that same
mechanism cannot move the timing leg (before_share stays ~0.9+
because the residual burn still completes pre-split), fails the count
leg on its own record (~740 onsets vs 197), and fizzles half its
seeds. Placement, frailty dispersion, and cap saturation all move
truth in the right direction but none reach the band, and nothing
moves before_share robustly below ~0.5. Per the design's frozen
declared-expectation clause: with no declared susceptibility arm
moving both legs, **the surviving suspect class is mid-voyage
suppression dynamics** — a suppression channel acting earlier or
otherwise than the declared SOP-017 day-16 confinement — and the
day-16 kink read is already wired to detect a deferral-shaped landing
if one exists.

## What this cannot settle

- Non-sterilizing / transient immunity, cross-strain partial
  protection, or pre-existing T-cell attenuation of severity (the
  engine's immune state is absolute legacy protection) — a partial-
  protection susceptibility structure is a different axis, not
  measured here.
- Whether IMM75's θ-invariant landing is a genuine attractor or a
  complement-arithmetic boundary (75% immune ⇒ ~928 susceptible
  passengers + 105 crew before role split — the band may simply bound
  the susceptible pool itself).
- Onset-recording sensitivity to the thinned onboard course (M0P56
  count-matches the degenerate baseline; whether a leaner channel can
  pair a ~880-infection truth with a 197-onset record is a channel
  question this array does not re-open).
- Any suppression channel outside SOP-017 — including pre-Feb-3
  voluntary isolation, medical-bay hold, or cabin-spend behaviour —
  which the record does not declare and this design does not arm.

## Next decision

The immune-depth axis is now bounded both ways: sub-band requires
fizzle-majority depths, in-band requires a manifest that is ~75%
sterile at boarding and still cannot reproduce the onset split. The
open lever class is suppression dynamics with an earlier/other
signature — e.g. an embarkation-to-quarantine-interval behavioural
channel — or a combined-structure hypothesis (frailty tail × moderate
immune depth × partial protection). Next assay decision: declare the
mid-voyage suppression grammar (pre-SOP-017 channels) or retire the
structure class and take the channel question back to the
observation model.

## Reproduce

```
aws s3 sync s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_suscept_v1/cells/ \
  campaign_results/covid_suscept_v1/cells/
python3 tools/covid_suscept_v1_readout.py \
  --cells campaign_results/covid_suscept_v1/cells \
  --design picard_framework/runs/covid_suscept_v1_design.json \
  --out campaign_results/covid_suscept_v1/readout_full.json --allow-partial
```
