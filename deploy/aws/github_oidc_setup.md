# GitHub → AWS OIDC setup (dispatch + collector)

One-time setup giving GitHub Actions short-lived AWS credentials with **no
stored keys anywhere**. GitHub mints an OIDC token per workflow run; AWS
trades it for a scoped role. Two roles:

- `github-crusher-dispatch` — Batch submit/describe on `picard-*`
  queues/jobdefs + S3 read/write on `campaign/*` (receipts, manifests).
- `github-crusher-collector` — read-only S3 on `campaign/*` +
  Batch describe/list. Cannot delete, restore, or write anything.

Both require the GitHub environment `aws-campaign`, so every run must pass
that environment's protection rules (e.g. required reviewer approval)
before any AWS credential is issued.

## Step 1 — create the AWS resources (one command)

In the AWS console (account `994254241749`), open **CloudShell** and run:

```bash
aws cloudformation deploy --stack-name github-oidc-campaign --template-file <(curl -sL https://raw.githubusercontent.com/bckirkup/Crusher_to_the_Bridge/main/deploy/aws/github_oidc_stack.yaml) --capabilities CAPABILITY_NAMED_IAM --parameter-overrides NotificationEmail=YOUR_EMAIL
```

(replace `YOUR_EMAIL`, or drop `--parameter-overrides ...` to skip the
monthly Batch+S3 budget alert — currently capped at $500 with 80%/100%
email notifications).

The command finishes with two outputs:

- `DispatchRoleArn` → `arn:aws:iam::994254241749:role/github-crusher-dispatch`
- `CollectorRoleArn` → `arn:aws:iam::994254241749:role/github-crusher-collector`

To change anything later, rerun the same command — CloudFormation updates
in place.

## Step 2 — create the GitHub environment

Repo → **Settings → Environments → New environment**, name it exactly
`aws-campaign`. Under *Deployment protection* add yourself as a required
reviewer — every dispatch/collect run then waits for your approve click.

Under *Environment variables*, add:

| Name | Value |
|---|---|
| `AWS_DISPATCH_ROLE_ARN` | `arn:aws:iam::994254241749:role/github-crusher-dispatch` |
| `AWS_COLLECTOR_ROLE_ARN` | `arn:aws:iam::994254241749:role/github-crusher-collector` |

(ARNs are identifiers, not secrets — variables, not Secrets.)

## Step 3 — run the handshake (no spend)

**Actions → campaign-dispatch → Run workflow** on `main`. It will pause on
the environment approval; approve it. Expected:

- `aws sts get-caller-identity` shows `assumed-role/github-crusher-dispatch`
- the three picard queues described
- `scripts/campaign submit --dry-run` renders a jobdef without registering
- the delete probe is **denied** (proves the role is correctly under-scoped)

**Actions → campaign-collect → Run workflow** similarly: lists campaign
prefixes (bounded), publishes a compact index as a comment on a tracking
issue, and its write probe must be denied.

If a step fails with `AccessDenied`, the error names the action — the fix
is a policy edit in `github_oidc_stack.yaml` and a re-deploy, not a
credential change.

## What this does NOT do

- No Edison callback: Edison consumes the *published index* via the repo's
  GitHub connection and compact uploads via `edison-client`. Durable
  Edison re-entry is the report's S4 gate and untested.
- No real submits yet: `campaign_dispatch` dry-runs only. Wiring an actual
  `submit` behind the same environment is a follow-up.
- No cleanup rights: deletion/restoration stays on Benjamin's
  `PowerUserAccess` profile — deliberately.
