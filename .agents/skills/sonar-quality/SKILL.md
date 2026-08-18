---
name: sonar-quality
description: Apply Crusher Ruff/Sonar quality rules (C901 ceiling, S3776 new-code 15, extraction patterns). Use before changing code or workflows, and when splitting high-complexity backlog functions.
---

# Sonar and Ruff Quality Guidance

## Before Editing

Read this guide before changing Crusher source or workflows. Keep mechanical
quality fixes separate from Sentinel analysis and campaign implementation work.

## Active Quality Rules

- Keep the CI lint scope blocking for Ruff `E`, `F`, `W`, and `I`.
- Keep `C901` enabled with the measured repository ceiling of 117. New
  functions must stay at or below cognitive complexity 15 (Sonar new-code
  S3776). The local Ruff hook uses the repository ceiling; that ceiling only
  ever ratchets downward after a measured max below the current value is
  committed.
- Dedicated complexity-backlog splits are allowed when the user asks for
  them, as their own change. Do not sneak extractions into unrelated
  maintenance, Sentinel analysis, or campaign-science PRs.
- The last documented official Sonar `S3776` count was 128. Update that
  number only from a live Sonar scan — a local AST estimator is not a
  substitute.
- Split composite assertions into independently diagnosable checks.
- Replace duplicated literals with named constants when the duplication is
  accidental; preserve repeated domain values when they are part of a
  documented model contract.
- Keep function and method names descriptive and consistent with the existing
  module vocabulary.
- Keep parameter counts bounded for new APIs; prefer a configuration object
  over adding unrelated positional parameters.
- The Stan-style `P_trigger` and `E_AR` property aliases in
  `picard_framework/analysis/boundary/posterior_lookup.py` are compatibility
  aliases. Do not rename them.

## Extracting high-complexity functions

New functions created by a split still count as new code: they must stay
≤15 cognitive complexity. Nested `for` loops in a new iterator still count;
collapse cartesian products with `itertools.product`. Dispatch tables beat
long `elif` chains.

Do not make a dispatcher a generator if the caller checks `is not None`.
A generator object is always truthy, so `sr*` / `vd*` families would never
run. `dispatch_standard_or_calibration` is a plain function that returns an
iterator or `None`.

Scratch dataclasses (`_EpochWork`, `SimpleNamespace` campaign ctx) are the
intended way to share phase state without growing parameter lists.

Do not rewrite control flow when extracting. For Picard, `ShipSimulation.step`
is an orchestrator over `_begin_epoch` plus `_step_*` methods sharing
`_EpochWork`; golden Picard is the behavior lock. For the campaign,
`tests/test_mega_cruise_campaign.py` dry-run cartesian counts are the
behavior lock; `tests/test_tier_iterators.py` and
`tests/test_campaign_boundaries.py` lock the extracted module boundary.

Unknown action kinds, and kinds in `_NEEDS_CTX` when `ctx is None`, remain
no-ops in `action_applier.py`. Stan indexed names in fleet columns stay
1-based.

New seams get graded sensitivity and bounds tests (skill `ci-test-design`),
not goldens:

| Seam | Tests |
|------|-------|
| Campaign iterators | `tests/test_tier_iterators.py`, `tests/test_campaign_boundaries.py` |
| Epoch helpers | `tests/test_ship_epoch_helpers.py` |
| Action dispatch | `tests/test_action_applier.py` |
| Stan fleet columns | `tests/test_sentinel_fleet_columns.py` |

## Remaining complexity hotspots

A dedicated backlog pass already split campaign generators
(`tier_iterators.py`), `ShipSimulation.step`, action dispatch, and Stan
fleet column / wastewater builders. Local cognitive-complexity estimates
still flag these as the next named follow-ups (not an official Sonar list):

- `picard_framework/analysis/stan/posterior_summaries.py` `summarize_fit`
- `crusher_labs/diagnostic_cascade.py` `evaluate_epoch`
- `engines/infection_dynamics_bridge.py` `step`
- `picard_framework/analysis/figures.py` `write_standard_figures`
- `summarize_outbreak_fit`
- `dashboard/charts.py` `render_standing_orders`

Keep that work under the owning package and out of Sentinel analysis
changes.

## Supply-Chain Rules

- Keep `--require-hashes -r requirements.lock.txt` on pip installs.
- Keep `--only-binary=:all:` on published-package installs.
- If uv is introduced in a future workflow, use its frozen/locked mode and
  `--no-build` safeguards; this repository does not use uv for dependency
  installation today.

## Validation

Run the project validation commands from `AGENTS.md`, including both
mechanical-guard modes, blocking Ruff lint, the full pytest suite with XML
coverage, the sanity checker, and the orchestrator smoke. Run the Docker smoke
when Docker is available.
