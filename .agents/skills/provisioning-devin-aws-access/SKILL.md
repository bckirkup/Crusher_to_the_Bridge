---
name: provisioning-devin-aws-access
description: Set up or repair role-based AWS access for Devin in any repository, using a zero-permission bootstrap IAM user that can only assume one scoped, ExternalId-gated role, plus the Devin secrets, the ~/.aws profile, and the failure modes that cost time. Use whenever a repo needs AWS access for the first time, an AWS call fails with AccessDenied or a signing error, or credentials need rotating.
---

# Role-based AWS access for Devin

The same pattern is already installed for Crusher to the Bridge (`picard-*`),
GutIBM (`gutibm-*`) and TheKingsAndI (`kingsandi-*`). Do not re-derive it per
repo: pick the prefix, run one script as admin, store four secrets, write one
profile. Everything else in this file is the failure modes.

## The identity model (four identities, never conflate them)

| Identity | Credentials | Can do | Used for |
|---|---|---|---|
| **admin** (console login / CloudShell) | admin | everything | the one-time setup below, IAM re-application, `ec2:Describe*` discovery |
| **`<prefix>-devin`** (IAM user) | long-lived keys, given to Devin | **only** `sts:AssumeRole` on the role below | source profile |
| **`<prefix>-devin-role`** | short-lived (`MaxSessionDuration`), requires `ExternalId` | the scoped work: Batch, ECR, S3, logs on `<prefix>-*` | every AWS command Devin runs |
| **`<prefix>-batch-job-role`** / **`-batch-execution-role`** | ambient, inside the container | job role writes results to S3; execution role pulls the image and writes logs | AWS Batch runtime; no keys in the image |

Devin's long-lived key is therefore worthless on its own: it can do nothing but
assume a role, and only when it also supplies the ExternalId secret.

## Setup, once per repo

The user runs step 1 (admin). Devin does steps 2 to 4.

**1. Admin, in CloudShell (already has admin identity, no local AWS CLI needed):**

```bash
export EXTERNAL_ID=$(openssl rand -hex 32)
PREFIX=<prefix> REGION=us-east-1 EXTERNAL_ID=$EXTERNAL_ID ./provision-devin-aws-role.sh
aws iam create-access-key --user-name <prefix>-devin
```

`provision-devin-aws-role.sh` sits next to this file. It is idempotent, and
`RENDER_ONLY=1` prints the policies without calling AWS — use that to show the
user exactly what they are about to grant before they run it. Capability
switches (`WITH_BATCH`, `WITH_ECR`, `WITH_S3`, `WITH_LOGS`) drop the parts a
repo does not need; everything granted is scoped to `<prefix>-*` resources.

**2. Four Devin secrets** (`<PREFIX>` upper-cased, hyphens to underscores):
`<PREFIX>_AWS_ROLE_ARN`, `<PREFIX>_AWS_EXTERNAL_ID`,
`<PREFIX>_AWS_ACCESS_KEY_ID`, `<PREFIX>_AWS_SECRET_ACCESS_KEY`. Offer them as
permanent org secrets — this access is needed every session, so a
session-scoped secret just recreates the problem next time. The region is not
a secret; keep it in `AWS_DEFAULT_REGION`.

**3. The profile, in the session** (the CLI then assumes the role and refreshes
the temporary credentials itself, so Devin never handles them):

```bash
# substitute the repo's own secret names for the GUTIBM_* ones
mkdir -p ~/.aws
cat > ~/.aws/credentials <<EOF
[gutibm-devin]
aws_access_key_id = ${GUTIBM_AWS_ACCESS_KEY_ID}
aws_secret_access_key = ${GUTIBM_AWS_SECRET_ACCESS_KEY}
EOF
cat > ~/.aws/config <<EOF
[profile gutibm]
role_arn = ${GUTIBM_AWS_ROLE_ARN}
source_profile = gutibm-devin
external_id = ${GUTIBM_AWS_EXTERNAL_ID}
region = ${AWS_DEFAULT_REGION}
EOF
chmod 600 ~/.aws/credentials
```

**4. Verify — it must print the assumed-role ARN, not the user ARN:**

```bash
aws --profile <prefix> sts get-caller-identity
```

Then `export AWS_PROFILE=<prefix>` for the session, and put the step-3 profile
write into the repo blueprint's `initialize` so future sessions start with it.

## Failure modes that actually cost time

- **`MalformedPolicyDocument` / "Syntax errors in policy".** IAM policy and
  trust documents accept only the top-level keys `Version`, `Id`, `Statement`.
  A `Comment` key, or any annotation, fails. Document policies outside the JSON.
  A Batch job definition is not an IAM document and is exempt.
- **`IncompleteSignature ... Invalid key=value pair (missing equal-sign) in
  Authorization header`.** `~/.aws/credentials` does not support inline `#`
  comments: a trailing comment is parsed into the secret. Strip all inline
  comments.
- **`get-caller-identity` returns the *user* ARN.** The profile was not used.
  `--profile <prefix>` or `AWS_PROFILE`, on every call.
- **`AccessDenied` on `sts:AssumeRole`.** Usually the ExternalId: the trust
  policy requires it and the CLI only sends it if `external_id` is in the
  profile. Re-check the value, then that the trust policy names the right user.
- **`AccessDenied` on a resource that looks in scope.** The grants are name
  scoped to `<prefix>-*`. A bucket, queue or job definition named off-pattern is
  denied by design; rename it rather than widening the policy.
- **`ec2:Describe*` (subnet / security group discovery) and any IAM change are
  not in the role.** Do those in CloudShell as admin. Do not widen the role to
  make one discovery call convenient.
- **`AccessKeysPerUser` quota is 2.** Rotation is delete-then-create:
  `aws iam list-access-keys` / `delete-access-key` / `create-access-key`.
- **Batch: the execution role can create log *streams* but not the log group.**
  If `/aws/batch/<prefix>-*` does not exist, every array child dies at startup
  with `ResourceInitializationError ... ResourceNotFoundException`. Create it
  once as admin: `aws logs create-log-group --log-group-name /aws/batch/<name>`.
- **Batch: a compute environment is `CREATING` when `create-compute-environment`
  returns.** `create-job-queue` fails with "Compute Environment ... is not
  valid" until it reaches `VALID`. Poll `describe-compute-environments`.
- **Windows PowerShell.** These snippets are bash. In PowerShell use
  `$env:NAME`, drop `|| true`, replace `sed` rendering with single-line
  `.Replace()` chains (literal, unlike `-replace` which is regex), write the
  result to a file and pass `file://<path>`. Keep `--query` on one line;
  multi-line JSON and JMESPath garble when pasted.

## Repo-side conventions worth copying

- Keep the trust and permission JSON, and a `NN_setup_devin_role.sh` wrapper,
  under `deploy/aws/` in the repo so the grant is reviewable in git. Existing
  examples: `GutModelBacteriocins/deploy/aws/06_setup_devin_role.sh` plus
  `deploy/aws/policies/devin-*.json`, and `Crusher-to-the-Bridge/deploy/aws/`
  (`bootstrap_user_policy.json`, `deploy_role_*.json`, `batch_*_role_*.json`).
- Containers get their identity from the Batch job role via the ambient
  credential chain. Never bake keys into an image or pass them as job env vars.
- New capability the role lacks: add one narrowly scoped statement to
  `role-permissions.json`, re-apply as admin, and record why. Never attach an
  AWS managed policy to the bootstrap user.
