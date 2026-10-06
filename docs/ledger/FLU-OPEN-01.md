# FLU-OPEN-01
**Date:** 2026-10-05
**Commit:** 7f4702ef
**Pathogens:** influenza_a
**Status:** measured
**Measured at:** 7f4702ef

First free-running (open-voyage) census of the `influenza_a` arm: the
FLU-RHYTHM-01 conditioned spec minus declared SOP-017
(`conditioned_spec(confinement="organic")`), isolated `influenza_a`,
2-passenger explicit epoch-0 seed plus live boarding prevalence
(0.008 pax / 0.005 crew), k = 6e-4, 288 epochs, seeds 8105–8204, four
ship classes × 100 seeds each, single arm. Spec of record:
`campaigns/flu/open_voyage_01/DESIGN.md` (merged #921); readout of
record: `docs/flu/flu_open_voyage_01_readout.md`.

**Execution:** image `picard-campaign@sha256:bc72e55295de111b3b14a987daad3dd422983d5c922b2604befcd5707d952324`
(tag `flu-open-voy01`, ENGINE_GIT_SHA `7f4702ef`, built via root
`Dockerfile` + `deploy/aws/Dockerfile.campaign` overlay at the merge
SHA), jobdef `picard-flu-open-voyage-01:3–:6` (:1–:2 were the canary
registrations of the same rendered jobdef), queue `picard-analysis-queue`
On-Demand (the Spot queue `picard-campaign-queue` sat in a zero-capacity
drought ~35 min; moved per user decision). Canary `4c84471a` inspected
(passed); arrays `18074d2e`/`7224370a`/`bb8fdf0e`/`c86b415f`:
**400/400 SUCCEEDED, 0 FAILED.** Prefix `campaign/flu_open_voyage_01/`.

## Measured verdict

**Open-voyage depiction works on all four classes; the only surfaces
above their frozen frames are the ones the profile declares hot.** All
7 frozen frames read out in the readout; the load-bearing numbers:

- F5 `reported/infected` breaches [0.03, 0.15] on all four (exp 0.531,
  spr 0.255, cls 0.279, mega 0.203) — consistent with the
  `observation_model` note that the declared reporting vector is ~2× the
  Ward 0.08 comparator by design ("closing that is the sweep's job").
  Decomposed: onboard-acquired cohort reports at 0.29–0.68,
  epoch-0 imports at ~0.22. The frozen frame's implicit
  onboard-dominated denominator was wrong; this is declared-mechanism
  measurement, not a new defect.
- `ever_ill/infected` pooled 0.29–0.60 vs implied ≈0.74 — resolved as
  import composition: onboard-acquired ill = **0.750 ≈ declared**;
  imports follow the initiation `state_split` (44% never-symptomatic,
  30% of presenters presymptomatic → expected import ill ≈ 0.17,
  measured 0.13–0.16 net of seeds). Symptomatic-at-boarding imports
  carry resolved `presented`/`severity_peak` but no in-voyage `ill` —
  correct 12-day-window semantics.
- Per-band presentation flags on cls/spr/mega are the same composition
  (imports present per the initiation split ≈0.56–0.60, not the
  age-band table).
- **Caregiver is a first-order open-voyage route**: 49–55% of
  onboard-acquired infections are caregiver-dominant on every class
  (droplet 45–50%) — the s8113 crew-scale question measured at fleet
  scale. `hvac_airborne` is background (≤2% of acquired).
- Outbreak formation 0.67 (exp) → 0.97 (mega); organic confinement
  95–100%; trigger ≥ ALERT 67–99% (exp lowest — one-third of 450-agent
  voyages see zero onboard transmission).
- Voyage attack context: 1.68% (exp) to 0.72% (mega) of complement
  infected, dominated by imports — onboard acquisition is 17–37% of
  infections.

## What this census opened (not defects)

- The declared post-recognition reporting level on acquired infections
  vs the Ward anchor is the visibility sweep's surface — now measured
  per class at the declared vector.
- Expedition's 33% no-transmission rate is a small-ship property of the
  susceptible pool + k — cite it when comparing class-level realism.
- If a reporting-side frame is reused, it must pool onboard-acquired
  and import cohorts separately — epoch-0 imports' illness lifecycle
  mostly precedes the voyage and drags any pooled ratio.
