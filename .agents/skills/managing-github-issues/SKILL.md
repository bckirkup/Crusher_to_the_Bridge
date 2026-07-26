---
name: managing-github-issues
description: Triage, batch, and resolve GitHub issues for Crusher-to-the-Bridge. Covers listing, categorizing by size/type, batching small issues into single PRs, closing resolved issues, and creating new issues. Use when working through the issue backlog or managing issue lifecycle.
---

# Managing GitHub Issues

## Prerequisites

- `gh` CLI authenticated (available in Devin environment)
- Repository: `bckirkup/Crusher_to_the_Bridge`
- Working directory: repo root

## Devin Secrets Needed

None — `gh` CLI is pre-authenticated.

## Step 1: List and Triage Open Issues

### List all open issues
```bash
gh issue list --state open --limit 50
```

### List with labels and JSON output for filtering
```bash
gh issue list --state open --json number,title,labels,createdAt \
  -q '.[] | "#\(.number) [\(.labels | map(.name) | join(","))] \(.title)"'
```

### View a specific issue
```bash
gh issue view <NUMBER>
```

### Filter by label
```bash
gh issue list --label bug --state open
gh issue list --label enhancement --state open
gh issue list --label wontfix --state open
```

## Step 2: Categorize Issues

Sort issues into these categories:

| Category | Criteria | Action |
|----------|----------|--------|
| **CI/Test coverage** | Missing tests, coverage gaps, CI pipeline improvements | Batch into single PR |
| **Doc fixes** | Stale docs, incorrect architecture descriptions | Batch into single PR |
| **Small code fixes** | Bug fixes < 50 lines, config changes, schema cleanup | Batch 3-7 per PR |
| **Medium features** | New modality, new platform, reward model expansion | 1-2 per PR |
| **Large features** | New engine, API layer, major refactor | Separate session per issue |
| **Wontfix** | Labeled `wontfix` | Skip |

### Sizing heuristic

- **Small**: Doc-only, config-only, or < 50 lines of code changes
- **Medium**: 50-300 lines, touches 2-5 files, may need new tests
- **Large**: 300+ lines, new modules, architectural changes, needs design discussion

## Step 3: Batch Small Issues

Create a feature branch for the batch:
```bash
git checkout main && git pull
git checkout -b devin/$(date +%s)-<batch-description>
```

### Commit message format for batching
```
<summary of batch>

Closes #<N1> — <one-line description>
Closes #<N2> — <one-line description>
...
```

GitHub auto-closes issues when the PR is merged if each issue has its own
`Closes #N` line in the PR body. **Do not** use comma-separated lists
(`Closes #1, #2, #3`) — GitHub only closes the first one.

### PR body format
Follow the repo's PR template:
```markdown
### What did you change?
| Issue | Change |
|-------|--------|
| #N1 | description |
| #N2 | description |

### Why?
Batch resolution of <category> issues.

### Did you run the CI tests?
- [x] Yes — <count> passed in <time>, 0 failures
```

## Step 4: Close Resolved Issues

### Close with comment (when PR auto-close didn't work)
```bash
gh issue close <NUMBER> -c "Resolved in PR #<PR_NUMBER>"
```

### Batch close
```bash
for i in 82 83 87 89; do
  gh issue close $i -c "Resolved in PR #112"
done
```

### Verify closures
```bash
gh issue list --state closed --limit 20
```

## Step 5: Create New Issues

### Create a bug report
```bash
gh issue create --title "[Bug] <title>" --label bug --body "## Summary
<description>

## Steps to Reproduce
1. ...

## Expected Behavior
...

## Actual Behavior
...

## Source
Code review ($(date +%Y-%m-%d))."
```

### Create an enhancement request
```bash
gh issue create --title "[Enhancement] <title>" --label enhancement --body "## Summary
<description>

## Suggested Resolution
...

## Source
Code review ($(date +%Y-%m-%d))."
```

### Create a fidelity issue
```bash
gh issue create --title "[Fidelity] <title>" --label bug --body "## Summary
<description>

## Source Reference
MATHEMATICAL_FIDELITY_AUDIT.md section X.Y

## Suggested Resolution
...

## Source
Code review ($(date +%Y-%m-%d))."
```

## Step 6: Verify After Merge

After a PR is merged, check that all referenced issues were closed:
```bash
# List issues that should have been closed
for i in <issue_numbers>; do
  echo "#$i: $(gh issue view $i --json state -q .state)"
done
```

If any remain open, close them manually (Step 4).

## Available Labels

| Label | Use for |
|-------|---------|
| `bug` | Incorrect behavior, doc inaccuracies, fidelity mismatches |
| `enhancement` | New features, capability additions |
| `question` | Needs design discussion before implementation |
| `wontfix` | Will not be addressed (skip these) |
| `documentation` | Documentation-only changes |
| `good first issue` | Simple, well-scoped tasks |

## Issue Lifecycle

```
OPEN → (triage) → categorized → (branch + implement) → PR created
  → CI green → PR merged → issue auto-closed
  → (if not auto-closed) → manual close with PR reference
```

## Repo-Specific Conventions

- **Issue title prefixes**: `[High]`, `[Medium]`, `[Low]` for priority; `[Fidelity]`, `[Enhancement]`, `[Bug]` for type
- **Wontfix issues**: Skip during triage. Do not spend time on them.
- **Closing format**: Always reference the PR number: `Resolved in PR #N`
- **Batch size**: 3-7 small issues per PR is the sweet spot. More than 10 becomes hard to review.
- **Branch naming**: `devin/<timestamp>-<description>` (e.g., `devin/1782056631-small-issues-batch`)
- **Tests required**: Run `python3 -m pytest tests/ -v --tb=short` before every PR. All ~858 tests must pass.
- **Ruff lint**: Run ruff after code changes. ~65 pre-existing findings are expected and non-blocking.

## Cross-References

- Testing: `.agents/skills/run-full-test-suite/SKILL.md`
- Data contracts: `.agents/skills/testing-data-contracts/SKILL.md`
- Schema validation: `.agents/skills/schema-validation/SKILL.md`
- CI workflows: `.github/workflows/ci.yml`, `.github/workflows/picard-presidio.yml`
