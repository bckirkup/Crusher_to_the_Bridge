# COVID replay fit: state of play at 2026-11-20 handoff

> **Status:** Handoff record (2026-11-20), authored against `main` = `a01130fb`
> after #1352 merged. It states where the Diamond Princess / Greg Mortimer
> record-fit work stands after TRANSPORT-FIT-01, REPAIR-ISOLATION-01 and
> THETA-REFIT-01. It reports no new numbers: every figure is quoted from the
> ledger entry or readout that measured it, with that entry's `Measured at`
> SHA. Nothing here is a fit.

## 1. The question

With the airflow repairs (B1–B3: near-field two-box, pathogen pool transport,
room-air removal, duty-0 terminal) shipped, do the COVID outbreak replays match
the record — on the Diamond Princess replay (`boxed_s1s2`) and, held-out, on
the Greg Mortimer (`hygiene_cycle`) — under both the native solver and ContamX;
and at what fitted Θ? Success is record-scale confirmations on DP (712
lab-confirmed) and GM (128/217 positives, asym share 0.8125) with composition
channels inside the record's windows; a miss that survives across θ, solvers
and hulls is a model defect to locate, not a fitting failure.

## 2. Current hypothesis

The paired provider readout supports low observed provider sensitivity on
these cases. DP has three differing pairs, including +39 recorded onsets
and +50 confirmations in one seed. All 70 pairs agree at the declared
takeoff threshold. Equivalence and delivered-dose preservation remain
unmeasured (`campaigns/covid/transport_fit_01/READOUT_PAIRED.md`).
Under that budget the composite Θ refits to 3.162e11 (the
~12× emission rescale plus the ambient/deck sinks absorbed the old 7.9e6 point)
and magnitude is restored on both hulls. **The remaining defect is not moved
by dose**: the asymptomatic-share miss is invariant across θ, both engines, and
both hulls — consistent with the symptom/observation channel — and DP's
recorded_onsets channel overshoots an order of magnitude at the fitted point.

## 3. Evidence for

- **Low observed provider sensitivity on these cases** —
  `COVID-TRANSPORT-FIT-01` (140 cells measured at `106a3583` and
  `8de77294`). DP onset mean Δ +1.70 with paired-t 95% interval
  [−2.54, +5.94], observed range −9 to +39. GM positive mean Δ −0.48
  [−1.83, +0.87], range −15 to +10. Takeoff classes match in 70 pairs.
  No equivalence margin was declared. Delivered dose was unmeasured.
- **near-field carries the confirmations** — `COVID-REPAIR-ISOLATION-01`
  (measured at `ecdb2c9f`, 120 cells): `nearfield_off` collapses pooled lab_confirmed
  1,236 → 76 (takeoff 9/20 → 1/20); `pool_off` doubles pooled volume to 2,449
  via a few huge cells — the pool caps the outbreak tail; room-air ~neutral;
  duty-0 a strict no-op; `all_off` ≈ `nearfield_off`.
- **the missing pre-repair volume is outside B1–B3** — diagnosis in
  `COVID-REPAIR-ISOLATION-01` §Diagnosis: the ~1,400 pre-repair ensemble was
  measured at `90b2fdae`, 147 commits before the isolation SHA; in-window
  changes include the covid #30 emission rescale (~12× up) and the ambient
  openings / envelope-leak / exhaust sink series on mega_cruise_5000.
- **Θ refits to 3.162e11** — `COVID-THETA-REFIT-01` (measured at `c053e15f`,
  840 cells): bootstrap selection frequency 0.736, interior minimum, not
  boundary-pinned; DP takeoff 0.95, campaign_positives med 443 vs scored
  target 634; **GM held-out** takeoff 0.96, positives med 108.5 [26.45–133.2]
  vs 128; H1 share 0.500 vs 0.5899.
- **operating point landed** — `thetas: [3.162e11]` is the canonical replay
  spec (`covid_crew_reach_01_design.json`, `covid_platform_fidelity_02_dp_design.json`),
  provenance-register Θ row updated (PR #1352, merged at `a01130fb`).

## 4. Evidence against / unexplained

- **Asym share invariant-miss** — GM 0.272 med vs 0.8125 record (miss 49/50),
  invariant across the full θ grid (0.24–0.44) and both engines
  (`COVID-THETA-REFIT-01`); DP asym day-31 ~0.146 vs ~0.505 measured at the
  superseded 7.9e6 point (`COVID-TRANSPORT-FIT-01` — the refit readout does
  not score that endpoint on DP). Demonstrated on two hulls, five decades of
  θ, two solvers — consistent with a symptom/observation-channel defect.
- **DP recorded_onsets overshoot** — med ~2.9k vs 197 at θ=3.162e11
  (ledger `COVID-THETA-REFIT-01`): the onset-recording channel produces far
  more dated onsets than the record while confirmations land near target.
- **DP takeoff is bimodal, not stable** — 9/20 seeds reach ≥10 onsets at 7.9e6
  (TF-01); conditional on takeoff the fit is still off (med lab_confirmed 72,
  over-dated ~0.8 vs 0.277, crew-loaded ~0.75 vs 0.29). Per Benjamin, real
  life was N=1 — frequency is not the complaint; composition is.

## 5. PRs landed this session

Dependency order, all merged:

- **#1334** — TRANSPORT-FIT-01 campaign machinery (`transport_engine` arm key,
  ContamX S3-pinned binary, design specs) → `COVID-TRANSPORT-FIT-01`.
- **#1337** — TRANSPORT-FIT-01 full readout + ledgers.
- **#1339** — REPAIR-ISOLATION-01 campaign machinery (four repair toggles,
  fail-closed cell checks) → `COVID-REPAIR-ISOLATION-01`.
- **#1341** — all_off canary readout (pre-repair ensemble not restored).
- **#1342** — REPAIR-ISOLATION-01 full readout + diagnosis of the
  pre-repair↔now gap (147-commit window, #30 + sinks).
- **#1343** — THETA-REFIT-01 campaign machinery (12-point θ grid × DP/GM,
  enforced fit/held-out split) → `COVID-THETA-REFIT-01`.
- **#1345** — dp_theta_6p90 canary (shipped baseline reproduced exactly,
  pooled lab_confirmed 1,236).
- **#1348** — THETA-REFIT-01 full readout: θ=3.162e11 selected, GM held-out
  scored, ledgers.
- **#1352** — refit Θ committed as the canonical replay operating point
  (design `thetas` + provenance register + ledgers).

## 6. Running jobs

None. All five campaign job families finished SUCCEEDED; every artifact is
under `s3://crusherbucket-994254241749-us-east-1-an/campaign/{covid_transport_fit_01,covid_repair_isolation_01,covid_theta_refit_01}/`
and the merged readouts are committed in the campaign LEDGERs and
`docs/ledger/` entries above.

## 7. What is now void

- **The 7.9e6 operating point is superseded.** Every DP/GM replay figure
  measured at Θ=7.9e6 (or the older 1e6) is historical on the Θ channel: the
  canonical spec is now `thetas: [3.162e11]`. Campaign specs that ran at the
  old point (TF-01, RI-01, GM rescore, CREW-REACH-01, PF-02) keep their own
  θ as the record of what ran; `open_ledger` §1 records the withdrawal.
- **Provider comparisons retain their input revision.** TF-01 establishes
  agreement on the takeoff flag for its seeds and configurations.
  Outcome differences and earlier transport measurements retain their
  measured scope.
- **The pre-repair (~1,400 pooled) ensemble at `90b2fdae` is not a target
  state** — it predates the emission rescale and the sink series; `all_off`
  at the current SHA measures 156, a different mass budget, not a regression
  inside the toggle grammar.

## 8. The single open decision

**Where is the asym-share / onset-recording defect?** It is now the only
standing composition miss on both hulls, and it is unmoved by every dose
change measured (θ over five decades, both engines) — that does not prove
the cause, but it makes a magnitude fix the wrong lever. The discriminating
evidence is a
channel-level trace: symptom-onset vs specimen-day vs recorded-onset paths on
paired seeds at the fitted θ, to separate (a) too many infections declared
symptomatic from (b) the observation layer dating/recording events the record
never saw. The recorded_onsets ~2.9k vs 197 overshoot on DP is the largest
single channel residual and the cheapest first probe — it may be the same
defect seen through a different window. Options ranked: (i) instrument the
onset→specimen→record funnel on DP `boxed_s1s2` at θ=3.162e11 before touching
any constant; (ii) accept the miss as a bounded known-defect and move to the
next hull/arm.

## 9. Do not reopen

- **Solver choice** — native ≈ ContamX is measured, paired-seed, two hulls;
  do not re-litigate engine selection for COVID replays.
- **`all_off` reconstruction of the pre-repair ensemble** — measured dead;
  the gap is in the 147-commit window, not the toggle grammar.
- **Θ fitted only on covid.T1 + covid.T3** — it is the arm's one fitted
  composite, never fitted on held-out hulls; GM remains held-out. Do not fit
  Θ (or any physical constant) to an anchor the model is scored against
  (model-parameter-provenance skill).
- **Completed campaign specs keep their θ** — `campaign.json` args are the
  record of what ran; editing them to the new θ would silently mislabel a
  re-run over the recorded S3 paths (rejected Devin Review finding on #1352,
  fail-closed `_match_cell` abort is intended).
