# Session prompt — Paper 1, WP1-revision: freeze contract corrections from Edison's review

**Status:** Planning — session brief, authored 2026-11-21; supersedes nothing, revises `paper1_freeze_design_contract_2026_11_20.md` (merged #1355). Deliverable is the corrected contract package; the freeze is still NOT declared — Edison reviews the revision.

Paper-1 work package WP1b, bounded session. Edison's pre-freeze review endorsed the program and required six contract corrections plus tighter verification before the freeze can be declared. This session applies them.

## Read first

- `docs/norovirus/edison_freeze_review_2026_11_21/REVIEW.md` — **the controlling document**; verbatim review. `FOR_DEVIN.md` alongside it is the implementation handoff summary.
- `docs/norovirus/paper1_freeze_design_contract_2026_11_20.md` — the contract being revised.
- `scripts/paper1_freeze_block_check.py` — the checker to tighten.
- `docs/norovirus/paper1_simulation_plan_assessment_2026_11_20.md` — background only.

## Settled inputs (do not re-derive)

- Edison endorses the scientific program and the proposed reference as the evaluation basis. No new biological mechanism is needed to address any finding. No broad audit, supply-chain model, or parameter fit is requested.
- The six required corrections are listed verbatim in REVIEW.md "Required contract corrections" 1–6. Apply all six; do not drop any as inconvenient.
- Affirmed decisions to record in the contract (REVIEW.md "Decisions I would affirm"): sanitary visits `none` + flush aerosol `0.0` stay as baseline; campaign escalation thresholds 2%/3%/5% stay, with the YAML-vs-runner distinction made explicit; `syndromic_comp65` stays the usual-recognition baseline including class-dependent compliance AND the upstream reported-case counters/role filters/confinement/recognition settings (the hard-coded either-channel aggregation does not freeze those); generic registry source + station-lot formulation stays the declared reference with actual source values and boarding choices resolved into the scenario record.
- Old quantitative results: replace any blanket "void" language with version- and mechanism-specific disposition. The dose-refit amendment predates the November experiments; specific earlier withdrawals remain specific. The bridge measures transfer to the new reference; it does not restore or erase historical outputs.
- Moratorium: protect the named reference and effective configuration; unrelated work continues on other revisions. New telemetry changing archive metadata is not new biology. An unplanned norovirus change creates a new reference + explicit disposition of already-run cells.

## The six corrections (apply each, mapped to contract sections)

1. **Role counts:** state intended passenger AND crew counts per reference scenario, not only totals; assert them on initialized agents and in each outcome payload. Explorer uses exact investigation counts (3,245/1,183) via the existing exact-class-count facility, with within-role class allocation declared. Template class fractions drift from nominal (Edison's table: Expedition 316/134 vs nominal 300/150, etc.) — record this. Keep archetype allocations as a labelled baseline where useful.
2. **Explorer exposure-cap eligibility:** record that the frozen block's cap request is not effective on `explorer_seas_06` (absent from the rhythm/event catalog). The contract names the resolution path: the bounded eligibility correction in flight (WP1c) plus per-hull effective-state assertions — resolved-state probes must run on ALL reference hulls, not only Expedition. If WP1c has not merged when you finish, mark this item pending its PR.
3. **Output contract:** the six-family promise becomes explicit — Sentinel line-list request required for clinical onsets; first-role threshold derived from role cumulative reports with passenger-first/crew-first/same-epoch/neither/missing states defined; declared compact-plus-environmental-panel or output-only compact harvest for assays (preserve swab location/time/amount-units/censoring; holding-tank wastewater distinct from the sequencing channel); onset/reporting coverage + role denominators required in extraction fixtures before the bridge executes.
4. **Bridge gate split:** technical completion (inputs used, outcomes extractable, attempts accounted, paired comparisons meaningful) is the gate. Scientific ordering is a measured result feeding a predeclared continuation decision — valid continuations: temporal reconstruction, population/geometry comparison, targeted uncertainty, precision expansion, justified defect correction. Zero-event strata are data, not auto-voids. Keep substantive scientific adequacy criteria as scientific criteria.
5. **Invariant baseline vs declared arms:** every arm retains the baseline block, declares changed paths, materializes complete effective nested objects (shallow merge can replace tier values), records the resolved effective config, and validates AFTER the runner applies every axis. Unplanned biological change restarts the reference/version decision. Complete the effective-reference annex: population, introduction, reporting/counters, strategy, source values.
6. **Checker tightening:** the 57 units cover 70 scalar leaves; label the seven configuration-only rows separately from resolved-state evidence. Any unexpected initialization exception FAILS the check; deliberately expected validation rejections are recorded separately with their reason (current code misclassifies FileNotFoundError as a live pin). Check full grouped dictionaries, not one projected field; label conditionally inactive controls (e.g. discrete ordering under continuous pathway) as conditional, not independently influential. Re-run the checker on the final named source and retain output.

## Also required (REVIEW.md "Recommended next handoff" step 2)

- A complete example run specification for each reference hull plus Explorer: role counts, pathogen/source/boarding choices, strategy, reported-case counters, requested outputs — materialized as the final generated cell would see it (post-runner-axes), checked, committed as the contract's annex.
- Bridge-size arithmetic stated honestly: the literal 4×3×420 table is 5,040 trajectories; the contract records the small-complete-bridge-first design principle and the zero-event bound convention (0/300 → one-sided 95% upper ≈0.994%) — WP2 owns the final design, the contract records the principle.

## Deliverable (exactly one)

One PR containing: the revised `paper1_freeze_design_contract_2026_11_20.md`, the tightened `scripts/paper1_freeze_block_check.py` with retained output, and the example-run-spec annex (in-contract section or companion file under `docs/norovirus/`). Update status lines; update `docs/README.md` index.

## Non-goals

- Do NOT declare the freeze — Edison reviews the revision first; the freeze record is a separate later document.
- No campaign code, no campaign runs, no mechanism changes (WP1c handles the eligibility fix separately), no seed census, no Morris work.
- Do not rename the contract file — Edison has it pinned at `73ad8724`; revise in place and note revision history inside.

## Report immediately if

- Any correction turns out to require mechanism work (contradicting Edison's "no new biological mechanism" — flag the contradiction rather than working around it).
- A pinned value in §2 must change to satisfy a correction (e.g. recognition defaults) — flag before editing the block; the block change itself restarts Edison's review.

## Validation gate before PR

- `python3 scripts/paper1_freeze_block_check.py` (or its tightened successor) passes on the revision branch.
- pre-commit, schema validation where JSON touched, docs status lines.

## Stop when

The revision PR is open AND you have posted the checklist mapping each of the six corrections + affirmed decisions to the exact contract section/commit that resolves it. Do not merge without the parent session's go-ahead unless CI is fully green and the mapping is complete.
