# Sonar and Ruff Quality Guidance

## Before Editing

Read this guide before changing Crusher source or workflows. Keep mechanical
quality fixes separate from Sentinel analysis and campaign implementation work.

## Active Quality Rules

- Keep the CI lint scope blocking for Ruff `E`, `F`, `W`, and `I`.
- Keep `C901` enabled with the measured repository ceiling of 117. New
  functions should remain at or below the existing development threshold of
  15; do not refactor existing high-complexity functions in a maintenance
  change. Crusher's local Ruff hook uses the repository ceiling because the
  backlog contains 128 `S3776` findings and the measured `C901` maximum is
  117. Sonar's new-code gate enforces 15 cognitive complexity on new
  functions, and the repository ceiling only ever ratchets downward.
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
