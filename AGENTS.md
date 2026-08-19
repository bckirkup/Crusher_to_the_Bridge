# Crusher-to-the-Bridge — Agent Instructions

## Setup

```bash
python3 -m pip install --only-binary=:all: --require-hashes -r requirements.lock.txt
pre-commit install
```

## Before Editing

Read `.agents/skills/sonar-quality/SKILL.md` before changing code or workflows.

Crusher's local Ruff pre-commit hook uses the repository `C901` ceiling of 117.
Sonar's new-code gate holds new functions to cognitive complexity 15. Dedicated
complexity-backlog splits are allowed as their own change; do not mix them into
Sentinel analysis. The last documented official `S3776` count was 98 — update
it only from a live Sonar scan. The ceiling only ever ratchets downward.

## Validation

```bash
pre-commit run --all-files
python3 scripts/sonar_guard.py <source-files>
python3 scripts/sonar_guard.py --workflows .github/workflows
ruff check --select E,F,W,I,C901 --ignore E501,E741 --target-version py311 \
  engines/ crusher_labs/ picard_framework/ decision_engine/ \
  orchestrator*.py presidio_runner.py deploy/aws/
python3 -m pytest tests/ -v --tb=short --cov --cov-report=xml
python3 tools/sanity_checker.py --from-config
python3 orchestrator.py
python3 presidio_runner.py \
  --fleet-config presidio/data/config/smoke_fleet.json \
  --cruises 1
```

Docker campaign smoke is optional when Docker is unavailable:

```bash
docker build -t picard-campaign .
docker run --rm picard-campaign --smoke
```

## Scope Rules

- Do not modify tests to make them pass.
- Preserve the hash-pinned installation and both CI workflows.
- Keep substantive Sentinel work under `picard_framework/analysis/stan/` and
  `picard_framework/runs/` separate from mechanical maintenance.
