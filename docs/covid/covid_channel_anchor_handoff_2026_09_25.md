# COVID observation channel + serology anchor: state of play at 2026-09-25 handoff

> **Status:** Handoff record (2026-09-25), authored against `main` at
> `efc30bf` after #688 merged. It states where the conditional-gap hunt
> stands after four measured assays, what the serology anchor and the
> period-faithful channel are proposed to be, and the single open decision
> the next session must make. It reports no new numbers: every figure is
> quoted from the ledger entry or readout that measured it, with that
> entry's `Measured at` SHA. Nothing here is a fit.

## 1. The question

The declared Diamond Princess replay records ~3,470–3,520 onsets on takeoff
seeds against the record's 197 — the ~18× conditional gap. Four assays have
now mapped where that gap does *not* live. The user's next-stage direction:
anchor "real infections" to the later serology rather than to the record's
own channel, make the model's observational channel period-faithful, then
run a campaign that maps the attack overshoot in detail under that channel.

Success would be: a `covid.H5` serology anchor scored against
`infections_total`, a period channel expressible as an arm override with no
constant tuned to 197, and a measured θ × channel surface that says whether
any declared θ puts both truth (vs serology) and record (vs 197) inside
their bands simultaneously.

## 2. Current hypothesis

The channel's over-inclusion lives almost entirely in **onset dating**,
not in case ascertainment: the model confirms ~76% of all infected
(ROUTE-ATTR-V1 funnel) while the record confirmed 712 of a serology-informed
~800–1,000 true infections (~70–85%) — the confirm *rate* is already
period-rough. The broken rung is dating: the model dates 93–100% of
confirmed cases at the true onset while the record dated 197/712 = 27.7%.
Fixing dating alone leaves recorded mass ~575–740 (~3× over) — the residual
is truth-level over-infection: ~2,700–3,500 infected vs a serology-informed
~840, i.e. an attack overshoot of roughly 4× at θ ×1.0 that shrinks with θ
but (LAMBDA-CROSS-V1) never lands on target on surviving seeds.

## 3. Evidence for

- **`PARTNER-RATE-V1` (#673, #675), measured at `37dc215`.** Partner-rate
  ×0.25 left the conditional distribution flat (median 3,474, band excludes
  197). Ring reach cleared. Array stood down by user decision.
- **`PLUME-DOSE-V1` (#676, #678), measured at `2bcdeb7`, job-def rev 20.**
  200/200 cells: plume-dose sweep ×0.05–×1.00 flat (elasticity 0.004), all
  four per-activity ring knockouts flat, pool witness ≈ partition. The
  sampled proximity ring is cleared as the mass carrier.
- **`ROUTE-ATTR-V1` (#680, #682).** Whole-voyage attribution + funnel, 3
  seeds, local. Droplet dose to infected hosts is ~98% ring-side
  (near-field plume 60–69% + cabin-mate addback 30–40%, a fixed ring no arm
  grammar reaches); the channel confirms ~76% of infected and dates
  93–100% at true onset vs the record's 27.7%; 85–89% of dated mass is
  mild — the stratum a real investigation loses to recall.
- **`LAMBDA-CROSS-V1` (#683, #688), measured at `8649d31`, job-def rev 22.**
  140/140 cells. Θ is the first knob that moves the gap (conditional median
  3,486 → 624 over θ ×1.0 → ×0.001, elasticity 0.216) and rescues timing
  (before_share crosses the record's 0.173 near θ ×0.01), but the response
  is a shallow bend plus bimodal extinction — verdict
  `lambda_bound_but_short`; no row's median is on target.
- **λ instrument (local 3.12, structural).** Per-challenge λ on the takeoff
  seed is tiny (median 2.8e-6) but Σλ ≈ 19,400 vs 3,711 hosts (~5×
  oversubscribed); slow seeds run Σλ/host ≈ 1.4–3×. Incidence tracks
  aggregate challenge volume, not per-challenge certainty.

## 4. Evidence against / unexplained

- The serology anchor itself is an extrapolation: Hung et al. (Lancet
  Infect Dis 2020) found 9/215 PCR-negative repatriated HK passengers were
  infected (~4%, CI 2–8) → ~120 missed of ~3,000 PCR-negatives → ~840
  total. Self-selected subgroup, like `covid.H4`; the band carries the
  uncertainty, the point does not.
- `ROUTE-ATTR-V1` anomaly, unresolved: seed 20200205 resolved every
  infected agent to severity ≥ mild — zero asymptomatics against the
  profile's 0.31 base probability. Logged in its ledger entry.
- Conditional-clause satisfaction at θ ×0.03/×0.01/×0.001 is tail-driven —
  bands contain 197 through widening, not mass on target (near-share ≤0.25).
- Whether the proposed onset-recording gate lands ~0.28 or overshoots
  downward is unmeasured — that is what the next canary is for.

## 5. PRs landed this session

In dependency order:

- **#673 / #675** — `PARTNER-RATE-V1` design + measured canary closeout
  (`docs/ledger/PARTNER-RATE-V1.md`).
- **#676 / #678** — `PLUME-DOSE-V1` design + measured 200-cell readout
  (`docs/ledger/PLUME-DOSE-V1.md`).
- **#680 / #682** — `tools/covid_route_attribution.py` + instrument fix and
  measured readout (`docs/ledger/ROUTE-ATTR-V1.md`).
- **#683 / #688** — `LAMBDA-CROSS-V1` design + λ instrumentation + measured
  140-cell readout (`docs/ledger/LAMBDA-CROSS-V1.md`).

## 6. Running jobs

None. Terminal arrays: partner-rate canary (rev 19, 20 cells,
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_partner_rate_assay_v1/37dc215/`),
plume-dose (rev 20, 200 cells, `.../covid_plume_dose_assay_v1/2bcdeb7/`),
lambda-cross canary + array (rev 22, 140 cells,
`.../covid_lambda_cross_v1/8649d31/`). Worker images are layered via
`deploy/aws/Dockerfile.covid_hull` over the campaign base (`ENTRYPOINT
["python3"]`); job-defs are cloned by `family:REV` ARN, never by
`jobDefinitions[-1]` ordering — both lessons are committed in
`.agents/skills/aws-batch-campaign/SKILL.md`.

## 7. What is now void

- The in-session claim "per-epoch hazard saturates (p_epoch ≈ 1)" is
  superseded by the λ instrument: per-challenge λ is tiny and the burn is
  aggregate-volume-driven. Never committed to a ledger; recorded here so
  it is not re-asserted.
- No previously committed figure is withdrawn by this session; the open
  ledger's §1 stands as written.

## 8. The single open decision

Approve — or correct — the proposed `SERO-CHANNEL-V1` design before any
cell runs. Its three pieces:

- **Anchor `covid.H5` (held_out):** serology-informed true infections
  ≈ 840, admissible band [712, 960] (Hung et al. CI-driven), channel
  `infections_total` — the engine's own ever-infected count, so the anchor
  is scorable *without* a serology instrument: serology approximates
  ever-infected, which the model emits directly. Grade B, subgroup
  extrapolation declared. `split.held_out_anchors` updated in the same
  change; the anchor is never in `fitted_against`.
- **Period channel (additive, default-off):** new optional
  `observation_model.onset_recording` on `sars_cov2_resp` —
  `{symptomatic_at_confirmation_required: bool, report_probability:
  float}`. The gate requires the stored presentation onset ≤ the
  confirming specimen's epoch (the record's own
  `symptomatic_at_specimen` field — 51% of DP positives were asymptomatic
  at specimen and contributed no onset date); the recall draw (~0.55–0.6
  declared, record-derivable: 197/712 ÷ ~0.49) covers interview/reporting
  loss. Enforced in `SyndromicSurveillance._onset_observation`, drawn on a
  dedicated onset RNG stream so molecular draws are unperturbed.
  Arm-expressible via the existing `pathogen_overrides` deep-merge — no new
  arm grammar key. Defaults off ⇒ declared channel is bit-identical.
- **Grid:** θ ∈ {1.0, 0.3, 0.1, 0.03, 0.01, 0.005, 0.003, 0.002, 0.001}
  (two added inside the bend, where the infected median crosses the
  serology band) × channel {declared, period} × 20 seeds = 360 cells.
  The declared-channel arm is the labelled baseline: it re-verifies the
  additive change is a no-op on the new image. Frozen scoring: per-cell
  `infections_total` vs the [712, 960] serology band (conditional on
  takeoff — the anchor is a burn-seed draw), `recorded_onsets` vs 197 under
  each channel, before_share, takeoff share. Canary = period channel at
  θ ×0.001 (nearest the anchor), 20 seeds, then stop.

Evidence that settles it: the canary read — whether the gate lands dating
near 0.28 of confirmed (if it undershoots, the alternative is the recall
draw alone without the symptomatic-at-specimen gate — declare which before
the array, not after).

## 9. Do not reopen

- No constant tuned to hit 197 or the serology band — `report_probability`
  is record-derivable and declared; the anchor band is literature-derived.
- `syndrome_case_eligibility_by_severity`,
  `lab_sampling_probability_by_severity` and the reporting vectors are
  declared Grade C and are not swept as channel proxies.
- The sampled-ring arm grammar (partner rate, per-partner dose, per-activity
  knockouts) is measured closed for the conditional gap — do not re-run
  reach/dose sweeps on this replay.
- `covid.H5` is held-out forever: a θ chosen against it would re-run the
  tuning the split exists to forbid.
- RNG pairing caveat stands for every channel/dose draw added — reads are
  distribution-level.
