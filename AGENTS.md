# Crusher-to-the-Bridge — Agent Instructions

## Setup

```bash
python3 -m pip install --only-binary=:all: --require-hashes -r requirements.lock.txt
pre-commit install
```

## Before Editing

Read `.agents/skills/sonar-quality/SKILL.md` before changing code or workflows.

Before changing any epidemiological constant — transmission rates, transfer
fractions, contact kernels, decay rates, titres, areas, deposition fractions —
read `.agents/skills/model-parameter-provenance/SKILL.md`. Constants carry a
source and an evidence grade at their definition, and none of them may be
chosen to make VSP, Park, or the passenger/crew ratio come out right.

`docs/norovirus_open_ledger.md` records what is currently withdrawn. **Every
dose figure in the repository is void pending a refit** — check the ledger
before quoting one.

Crusher's local Ruff pre-commit hook uses the repository `C901` ceiling of 117.
Sonar's new-code gate holds new functions to cognitive complexity 15. Dedicated
complexity-backlog splits are allowed as their own change; do not mix them into
Sentinel analysis. The last documented official `S3776` count was 87, taken from
a live Sonar scan on 2026-08-28 — update it only from a live Sonar scan. The
ceiling only ever ratchets downward.

## Validation

```bash
pre-commit run --all-files
python3 scripts/sonar_guard.py <source-files>
python3 scripts/sonar_guard.py --workflows .github/workflows
ruff check --select E,F,W,I,C901 --ignore E501,E741 --target-version py311 \
  engines/ crusher_labs/ picard_framework/ decision_engine/ \
  orchestrator*.py presidio_runner.py deploy/aws/
python3 -m pytest tests/ -m 'not slow' -v --tb=short --cov --cov-report=xml
python3 tools/sanity_checker.py --from-config
python3 orchestrator.py
python3 presidio_runner.py \
  --fleet-config presidio/data/config/smoke_fleet.json \
  --cruises 1
```

`-m 'not slow'` is the fast tier that `.github/workflows/ci.yml` runs on every
push (about 4.5 min locally). The `slow` marker covers the posterior-recovery
fits — all of `tests/test_sentinel_fleet_validation.py` plus a few reference-walker
and campaign cases — measured at 35 of the suite's 41 min;
`.github/workflows/nightly.yml` runs the whole suite on cron and on demand. Run
`python3 -m pytest tests/ -v --tb=short` locally before changing anything under
`picard_framework/analysis/stan/`.

Docker campaign smoke is optional when Docker is unavailable:

```bash
docker build -t picard-campaign .
docker run --rm picard-campaign --smoke
```

## Scope Rules

- Do not modify tests to make them pass. When a model change legitimately moves
  a numeric expectation, attribute the move to a specific part of your diff
  before updating it; an unattributed baseline move is a possible defect.
- Do not fit a physical constant to an anchor the model is scored against.
- Update `docs/norovirus_open_ledger.md` in the same change as anything that
  invalidates a measurement recorded there.
- Preserve the hash-pinned installation and both CI workflows.
- Keep substantive Sentinel work under `picard_framework/analysis/stan/` and
  `picard_framework/runs/` separate from mechanical maintenance.
