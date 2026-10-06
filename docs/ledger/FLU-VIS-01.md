# FLU-VIS-01
**Date:** 2026-10-06
**Commit:** ca775a0b
**Pathogens:** influenza_a
**Status:** measured
**Measured at:** ca775a0b

Two-axis observation-layer sweep on the FLU-OPEN-01 open voyage:
`report_scale` {0.25, 0.5, 2.0} multiply-then-clip on both
`reporting_probability_by_severity_{pre,post}_recognition` vectors ×
`eligibility` {declared `[0,0,0.85,1,1]`, strict-mild `[0,0,0,1,1]`}
injected via `pathogen_overrides.influenza_a.observation_model`. 6 arms
× 4 classes × seeds 8105–8204 = 2400 cells, plus OPEN-01 baseline reuse
(shipped corner not re-run — canary-verified bit-identical). Spec:
`campaigns/flu/visibility_01/DESIGN.md` (merged #928); readout of
record: `docs/flu/flu_visibility_01_readout.md`.

**Execution:** image `picard-campaign@sha256:1c0aa1d570f0fe905b936db9e08b3509369997d5a74999913a3decf95a2a17d3`
(tag `flu-vis01`, ENGINE_GIT_SHA `ca775a0b`), jobdef
`picard-flu-visibility-01:2–:25` (+`:1` canary registration), queue
`picard-analysis-queue` On-Demand. Baseline-identity canary `b346d49d`
SUCCEEDED, seed-8105 payload bit-identical to OPEN-01 — reuse held, the
four `r100_dec` contingency blocks never submitted. **2400/2400 arm
cells SUCCEEDED, 0 FAILED** (~5.7 h; mega serialized the tail on a
shared CE). Audits: arm echo = resolved severity model on 2401/2401
cells; 0 dated mild onsets on all 1200 strict-arm cells (witness).

## Measured verdict

**The reporting layer saturates — no declared corner reaches Ward's
~0.7 % presenting attack on the big hulls; the residual gap is
incidence, not visibility.**

- Presenting attack (`reported/complement`): exp 0.85–1.07 % —
  brackets Ward [0.4, 1.0] on every arm, overshoots at r200. spr
  0.21–0.22 %, cls 0.22–0.25 %, mega 0.13–0.16 % — flat across the
  whole 8× reporting span including the ceiling-saturated r200 corner.
  The big-hull reporting pipeline reports everything the severity mix
  lets it reach; closing the gap by visibility needs rep/inf ≈ 0.45 on
  the current infection pool (outside the declared space) or ~4–5× the
  incidence. Expedition sits at Ward because its voyage attack is ~2×
  the others' (1.68 % vs 0.72–0.88 %).
- Pooled reported/infected stays above F5's [0.03, 0.15] on every arm
  — even the coldest corner (r025×str) reads 0.188–0.492. The F5 frame
  is unreachable inside the swept grid; the floor on this voyage is
  ~0.19–0.25 pooled.
- Acquired-cohort reporting moves with scale where it binds (mega
  0.227→0.398 r025_str→r200_dec); exp saturates (~0.60–0.65 all arms).
- Feedback into transmission measured (paired seeds, all medians 0 —
  tail-driven): scale-down adds onboard acquisition on exp/spr
  (+0.15/+1.1–1.3 mean) as predicted; **r200 on exp adds infections
  (+1.56 mean) while quadrupling quarantine — sign reversal vs the
  declared hypothesis**. Attributed (addendum below): the
  serviced-quarantine crew bridge, not RNG re-realization. Visibility
  is transmission-relevant but not monotone.
- Recognition: final ≥ ALERT rates flat vs baseline on every class
  (exp 63–66 %, spr 95–99, cls 96–97, mega 97–100). First-ALERT
  timing is class-dominated — mega epoch 0 (import prevalence), spr 4–5,
  cls 9–11, exp 30–41; reporting scale nudges it only on exp (−10
  epochs r025→r200).
- Strict-mild corner: live (witness 0/1200) but second-order —
  presenting attack moves ≤0.01 pp; mild contributes little to the
  report pool at declared reporting vectors.
- Route mix invariant as predicted (caregiver ~36–56 % of acquired,
  droplet ~44–50 %, hvac background); exp r200's droplet rise rides the
  tail-infection cells.

## What this opened (not defects)

- The big-hull presenting-attack residual is now attributable to the
  incidence side of the cell — importation intensity / onboard
  acquisition / exposure window — not the observation layer. The
  comparator question for the ledger: is Ward's 0.7 % a fleet-level
  expectation or a realized outbreak voyage? Under shipped incidence the
  model's answer is "off-distribution on the big hulls, at Ward on
  expedition."
- Baseline-reuse-via-canary worked as designed: identical-seed corner
  verified bit-identical, 400 cells of baseline reused, contingency
  blocks stayed unsubmitted.
- The `r100_dec` arm row for exp in the readout tables is the n=1
  canary cell (baseline cells shadowed by the arm-suffixed dir); paired
  deltas still compute per-seed vs all 100 OPEN-01 baseline cells.

## Attribution addendum — the exp r200 sign-reversal

Measured at `ca775a0b` (paired local probe on driver seed 8188, +49;
cross-check on all 100 paired exp seeds; detail in the readout §4):

- Import cohorts identical across arms (`first_infection_epoch` 0 on
  the same six IDs) — stream intact through init; the divergence is
  state-mediated through reporting outcomes, not RNG corruption.
- Cabin-mate co-confinement refuted (2/59 onboard infections while
  confined). The channel is **service into quarantined cabins**:
  confined cohort ×5 (77 vs 15) → service deliveries ×2.6 (440 vs
  167) → crew caregiver infections 14 vs 9 (+6 crew droplet) →
  exempt crew seed a late passenger droplet wave (ep ~205–283, 38
  vs 2, nearly all never-confined).
- Pearson r = 0.81 between Δinfected and Δquarantined over the 100
  paired seeds, both directions (s8142 is the extreme of both signs).
- Verdict: real mechanism — quarantine's benefit is partly
  self-defeating via the crew-service channel on the 450-agent hull
  (cohort ≈ 17 % of complement); diluted on the big hulls. Not a
  defect; a measured property of organic confinement under a hot
  reporting vector.
