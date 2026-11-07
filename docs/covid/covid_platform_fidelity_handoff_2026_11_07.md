# Platform fidelity: state of play at 2026-11-07 handoff

> **Status:** Handoff record (2026-11-07), authored against `main` after #1171
> merged (`7c776a83`); amended after #1173 merged with the user's θ-structure
> decision (§8) and the external review's pre-lock changes. It retires the
> session that built the Diamond Princess hull and closed Edison's pre-freeze
> HVAC blocker. It states what exists, what is settled, and the single next
> action (§8). It reports no new numbers: every figure it refers to is quoted
> from the committed handoff or scenario file that measured or declared it.
> Nothing here is a fit, and nothing here has been run.

## 1. The question

How much does hull fidelity move the two frozen 2020 COVID event replays? The
repo holds two event scenarios in `data/scenarios/covid_hull_scenarios.json`,
each currently riding a generic proxy platform:

- `diamond_princess_2020` (split role **training**): population 3,711
  (2,666 passengers / 1,045 crew), 35 days from day zero 2020-01-20, SOP-017
  days 16–30, testing campaign from day 16, molecular ascertainment from day
  14, one explicit seed (passenger, infection age 6.8 d, departure day 5.0,
  onset day −1.0), agent bundle
  `data/scenarios/agent_profiles/diamond_princess_2020.json`. Today its
  `catalog.platform_id` is `mega_cruise_5000`.
- `greg_mortimer_2020` (split role **held_out**): population 223 (128 pax /
  95 crew), 28 days, on `expedition_cruise_450` today.

The comparison replays each event on its event-faithful hull —
`diamond_princess` (built this session, PR #1167) and `greg_mortimer` (pre-existing
platform, exterior HVAC corrected this session, PR #1171) — against the generic
proxy it currently rides, with everything else held fixed. It is a
**pre-registered sensitivity measurement**: it does not select Theta, does not
crown a canonical platform, and does not reopen the train/test split. Success
is a committed readout of the platform-effect size per event pair on paired
seeds; failure to move the record is a result, not a defect to fix by tuning.

## 2. Current hypothesis

Hull geometry — zone count, HVAC zoning, cabin-corridor topology, exterior
ventilation — is a first-order driver of the replay observables, so the
faithful hulls should move both events' replays relative to their proxies. If
the DP (training) and GM (held-out) arms move in the same direction, that is
evidence geometry is a systematic term; if they disagree, the disagreement is
itself the held-out result and is reported as-is, never repaired by parameter
change. Whether the effect is larger than seed noise at 20 seeds is unknown —
that is what the canary gate exists to measure.

## 3. Evidence for

- The split is frozen before implementation:
  `data/scenarios/covid_hull_scenarios.json` `split.fixed_before_implementation
  = true`, training `[diamond_princess_2020]`, held_out `[greg_mortimer_2020]`;
  `docs/proposals/covid_trajectory_fit_spec.md` — "If a held-out score is used
  to revise a parameter, it stops being held out."
- Both faithful hulls now exist and pass their contracts:
  - `diamond_princess` (PR #1167): recipe in
    `scripts/cruise_platform_recipes.py`, generated platform in
    `data/platforms/diamond_princess/` — 159 zones, 57 AHUs, nominal complement
    2,710 pax + 1,100 crew; contract tests in
    `tests/test_cruise_platform_cabin_corridor.py`; exterior set registered in
    `tests/test_exterior_zone_hvac_isolation.py`.
  - `greg_mortimer` (pre-existing; PR #1171 this session): five semi-open zones
    (`ZodiacPlatforms`, `ActivityPlat`, `ViewPlatforms`, `SunDeck`, `TopDeck`)
    removed from `AHU_Expedition` / `AHU_Public_Main` / `AHU_Observation`, Contam
    bundle regenerated, platform added to the exterior-isolation contract.
- The DP replay operating point this study would hold fixed: θ = 7.9e6, seeds
  20200205–20200224 (20 seeds), boxed `sect_mess_boxed` base — quoted from
  `docs/covid/covid_dp_replay_handoff_2026_10_09.md` (that handoff's own
  Measured-at SHAs govern the figures).
- The scenario machinery supports per-arm platform override without touching
  the frozen scenario records: `to_run_spec_dict()` emits
  `catalog.platform_id`, and `picard_framework/run_spec.py` resolves it per
  run; the population/`require_declared_total` complement rule is enforced only
  on the campaign-runner and leverage-screen paths, not the covid hull path, so
  event populations (3,711 / 223) can ride either hull.

## 4. Evidence against / unexplained

- **No platform-effect measurement exists.** The comparison has never been
  run; every claim about its size or sign is hypothesis until the canary
  readout exists.
- **Trigger-protocol zone-name asymmetry (unverified — freeze as an admissibility criterion).** SOP-007 /
  SOP-009 carry `modifiers.close_zones = [Main_Galley_Aft, Crew_Mess_Main]` —
  mega-only zone ids; `diamond_princess` and `greg_mortimer` use different
  dining names (`MainGalley`, `CrewMess`) — and the SOP-017 diagnostic
  counterfactual variants carry mega zone names in `exempt_work_zones`.
  `build_fit_run_spec` disables `diagnostic_cascade`
  (`picard_framework/covid_theta_fit.py` L395), which covers the cascade
  trigger path, but SOP-007/009 trigger on lab-instrument stoplights
  (`clinical_microbiology` / `clinical_qpcr` RED) AND
  `min_escalation_status` (SUSPECTED / LOCKDOWN), neither of which the
  cascade override disables; whether they can fire in the declared replay is
  UNVERIFIED. `apply_zone_closures` no-ops on unknown ids, so if they fire on
  the proxy arm and silently no-op on a dedicated arm, that is a
  differential-intervention confound. External design review (2026-11-07)
  flagged the same item. Frozen mitigation for the prereg (decide before any
  cell runs): echo fired protocol ids per cell and declare any cell where a
  `close_zones` protocol fired VOID, or strip SOP-007/009 via one shared
  `catalog.protocols_path` per event pair.
- **GM voyage length vs platform.** GM's 28-day, 223-agent event on the
  faithful hull is far smaller than the DP arm; seed-noise dominance is more
  likely there, which is why the seed budget is an open design parameter.

## 5. PRs landed this session, in dependency order

- **#1167 — Add Diamond Princess cruise platform (`diamond_princess`).**
  Recipe, generated 159-zone platform, Contam bundle, graphics/deck assets,
  `platform_class: "diamond"` schema, README registration, contract tests.
  Enabling work for the DP arm; no ledger entry (additive platform, no
  measurement).
- **#1171 — Fix Greg Mortimer exterior zones assigned to enclosed AHUs.**
  Five semi-open zones out of three AHU groups, Contam bundle regenerated,
  `greg_mortimer` added to `tests/test_exterior_zone_hvac_isolation.py`.
  Pre-freeze defect fix per external review; no ledger entry (platform not
  wired into any run; no recorded measurement invalidated — verified by
  repo-wide consumer grep).

## 6. Running jobs

None. No AWS Batch arrays, no schedules, no automations were created by this
session.

## 7. What is now void

Nothing. Both PRs touched platforms that no run spec, campaign, fit design, or
ledger measurement references: the `diamond_princess_2020` scenario still
points at `mega_cruise_5000` and `greg_mortimer_2020` at
`expedition_cruise_450` by design, and the `greg_mortimer` platform had no
runtime consumer before #1171. `docs/covid/covid_open_ledger.md` §1 is
unchanged and no entry there is withdrawn by this session.

## 8. The design, as settled (2026-11-07)

The user settled the θ structure after external review (Edison/Kosmos
`DESIGN_REVIEW.md`, whose own M1 recommendation to move everything to 2.37e11
was WITHDRAWN by its author as GM-informed parameter selection):

**Primary (frozen first) — shared Θ = 7.9e6, four arms:**

- DP event on `diamond_princess` vs `mega_cruise_5000`; GM event on
  `greg_mortimer` vs `expedition_cruise_450`.
- Event populations fixed (3,711 / 223), full voyage, one shared SHA, one
  emission-fraction state (5e-5, "declared not applied" per the provenance
  register tranche 27 §6), campaign-level `platform_id` overrides — the frozen
  scenario records and split are untouched.
- Resolved `platform_id` and relevant input hashes echoed in every cell (the
  payload does not echo `platform_id` today — small code change, part of the
  campaign registration).
- DP-side debugging first; GM arms revealed once, after DP machinery is
  proven. GM canary is TECHNICAL acceptance only; Θ is frozen before any GM
  epidemiological output is examined. If GM fizzles on both hulls at 7.9e6,
  that is reported as-is — no Θ change to make GM informative.

**Descriptive layers (pre-declared, none selectable, none fitted):**

1. GM pair at Θ = 2.37e11 (GM-RESCORE-02 anchor row) — historical continuity
   and a hedge against GM fizzle at 7.9e6.
2. GM θ-lattice {1e11, 2.37e11, 1e12} × both GM hulls — maps the
   geometry×θ interaction on the cheap hull. No DP lattice unless a
   pre-declared escalation rule (written in the prereg) fires; DP cells cost
   ~10–11 min each.

**Protocol discipline (adopted from external review, strengthened):** prevent
unwanted closures by construction — a frozen per-event-pair protocols file
carrying SOP-017 only; fired-protocol ids echoed per cell; any cell where a
`close_zones` protocol fired is a FAILED COMPARISON, not a deletable cell
(firing is outbreak-severity-dependent; deletion would bias the contrast).
Stop, diagnose, apply a predeclared correction/rerun policy; failed attempts
stay in the record.

**GM prior evidence acknowledged:** GM has been scored twice at the
fleet-shape θ lattice on the proxy hull (RESCORE-01/02). This is a paired
sensitivity comparison, not a fresh holdout; no parameter is revised from any
result of this campaign.

**Metrics (all frozen in the prereg as labeled design choices, not sourced
constants):** paired hull delta (per-seed dedicated − proxy recorded_onsets,
takeoff-conditional; median Δ with q05–q95); P(takeoff) per hull
(recorded_onsets ≥ 10 gate); takeoff-conditional asymptomatic share;
declared minimum detectable effect (proposal: 30%); seeds per row (proposal:
20 — 20 matched seeds × 2 platforms = 40 executions per event pair, per the
external review's cell-count clarification); CRN correlation measured on the
first canary batch (ρ < 0.3 → unpaired analysis); technical-failure policy
(>10% failed cells → stop, diagnose, resubmit).

**Remaining before freeze (proposed defaults, user confirms at prereg
review):** seed budget per row (20 vs GM-RESCORE's 50 convention) and
deliverable form (proposed: prereg doc under `docs/covid/` + campaign
registration `campaigns/covid/platform_fidelity_01/` in one PR). Then: local
smoke → Batch canary (≥20 seeds at one arm-row) → stop and report; the user
decides the full array.

**The single next action:** write the pre-registration doc (all of the above,
frozen) and, in the same change, the campaign registration with the
platform-override cell worker. Nothing runs before the user merges it.

## 9. Do not reopen

- The scenario split in `data/scenarios/covid_hull_scenarios.json` —
  `fixed_before_implementation: true`; not revisitable after seeing which hull
  fits (`docs/proposals/covid_trajectory_fit_spec.md`).
- GM held-out discipline: scored once, reported whatever it shows; any
  parameter revision from a held-out score voids it.
- No theta refit on the faithful hulls inside this study. A refit would be a
  separate pre-registered study: DP-only fitting, which forces a NEW held-out
  event — that is the user's decision, not this study's.
- No Θ adaptation to GM outcomes: if GM fizzles or saturates at 7.9e6, that is
  reported as-is; the descriptive layers never promote an arm to "the result"
  and no arm is selectable after outcomes are seen.
- Unexpected trigger-protocol firing is a FAILED COMPARISON, never a deletable
  cell — firing is outbreak-severity-dependent and deletion would bias the
  hull contrast; failed attempts stay in the record.
- No fitting any constant to the covid anchors (AGENTS.md); report ranges and
  tails (user preference).
- Campaign gate (`bounded-research-sessions` rule): geometry/seed gate
  validated, local smoke passed, canary ≥20 seeds at one cell read out — then
  stop and report; the user decides whether the full array runs. Simulation
  runs go to AWS Batch, never the local box.
- The bespoke `deploy/aws/*_entrypoint.py` / `submit_*.sh` /
  `batch_job_definition_*.json` layout stays frozen; new campaigns register
  under `campaigns/covid/<name>/` and submit through `scripts/campaign`.
