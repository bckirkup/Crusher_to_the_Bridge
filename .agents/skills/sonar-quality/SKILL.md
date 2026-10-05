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
- Keep `C901` enabled with the measured repository ceiling of 56. New
  functions must stay at or below cognitive complexity 15 (Sonar new-code
  S3776). The local Ruff hook uses the repository ceiling; that ceiling only
  ever ratchets downward after a measured max below the current value is
  committed.
- Dedicated complexity-backlog splits are allowed when the user asks for
  them, as their own change. Do not sneak extractions into unrelated
  maintenance, Sentinel analysis, or campaign-science PRs.
- The last documented official Sonar `S3776` count was 87 (live scan
  28 Aug 2026). The campaign generator, `ShipSimulation.step`, and
  action dispatch are already closed on that scan. Remaining complexity
  backlog is listed below.
- Split composite assertions into independently diagnosable checks.
- Replace duplicated literals with named constants when the duplication is
  accidental; preserve repeated domain values when they are part of a
  documented model contract.
- Keep function and method names descriptive and consistent with the existing
  module vocabulary.
- Keep parameter counts bounded for new APIs; prefer a configuration object
  over adding unrelated positional parameters.
- The Stan-style `P_trigger`, `E_AR`, `P_accel`, `E_cost_onboard`, and
  `E_peak_epoch` property aliases in
  `picard_framework/analysis/boundary/posterior_lookup.py` were removed to
  clear Sonar `S1845` blockers. Use the snake_case `SurfacePoint` fields;
  serialized dictionary keys retain their schema-defined names.

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
fleet column / wastewater builders. Official open `S3776` is 87 after
those extractions scanned. Next named follow-ups (local ranking, not
official Sonar):

- `engines/infection_dynamics_bridge.py` `step` (deferred: higher-risk dynamics path)

Closed on the dedicated complexity-backlog pass (extract helpers only; behavior
locks via existing suites + `tests/test_complexity_backlog_seams.py`):

- `picard_framework/analysis/stan/posterior_summaries.py` `summarize_fit` / `summarize_outbreak_fit`
- `crusher_labs/diagnostic_cascade.py` `evaluate_epoch`
- `tools/sanity_checker.py` `_check_logical_contradictions`
- `picard_framework/analysis/figures.py` `write_standard_figures`

Keep that work under the owning package and out of Sentinel analysis
changes. The boundary aliases are removed and the `S1845` blockers are
cleared. Remaining `S100`/`S116` findings on `C_screen`/`C_case`-style
boundary cost fields are accepted as intentional: those names are fixed by
`schemas/preboarding_decision_scenario.schema.json` and the shipped
`picard_framework/analysis/boundary/data/*.json`; renaming them would require
a data migration for a naming nit.

## Coverage-exclusion convention for diag/readout tools

Diagnostic probe and readout tools are exempted from the 80% new-code
coverage gate via `sonar.coverage.exclusions` in `sonar-project.properties`.
Add a new tool's exclusion **in the same change that creates it** — a file
that lands without one fails the gate the first time the next PR touches it
(this has repeatedly been the only SonarCloud red on a campaign PR). Prefer
family globs over per-file rows where a convention already exists
(`tools/flu_*.py`, `tools/smalln_diag/**`, `tools/diag/**`,
`campaigns/**/*.py`, `scripts/campaign` are already globbed).

Two traps when editing `sonar-project.properties`:

- It is a properties file, not a sectioned config — an edit must rewrite the
  **whole** file. Writing back only the `sonar.coverage.exclusions=` line
  drops `sonar.projectKey`/`sonar.organization` and the scan dies with
  "mandatory properties for 'Unknown'".
- A typo'd exclusion filename silently covers nothing — the gate still fails
  on the real file. After adding one, confirm the path exists at the merge
  SHA.

## Recurring rule hits and their fixes

| Rule | Trigger | Fix |
|------|---------|-----|
| S5778 | Multiple throwing calls inside `pytest.raises` | one throwing invocation per `raises` block |
| S7519 | Dict built by assigning `None`/default per key | `dict.fromkeys` |
| S8786 | Regex compiled lazily inside a loop/function body | hoist to a module constant |
| S1244 | `assert x == <float>` in tests (sonar_guard flags test files too) | `pytest.approx` |
| S9073 | Composite `assert a and b` | split into separate asserts |

## Supply-Chain Rules

- Dependencies install only from `uv.lock`: `uv sync --locked --all-extras --no-install-project --no-build`.
  `--locked` refuses a stale lock, `--no-build` refuses source distributions
  (wheels only), and `--no-install-project` keeps the environment to the
  declared dependencies.
- Any remaining `pip install` (none in CI today) keeps `--only-binary=:all:`
  and version pins or hashes; `scripts/sonar_guard.py` enforces both forms.
- Regenerate the lock only with `uv lock` after editing `pyproject.toml`;
  never hand-edit `uv.lock`.

## Validation

Run the project validation commands from `AGENTS.md`, including both
mechanical-guard modes, blocking Ruff lint, the full pytest suite with XML
coverage, the sanity checker, and the orchestrator smoke. Run the Docker smoke
when Docker is available.
