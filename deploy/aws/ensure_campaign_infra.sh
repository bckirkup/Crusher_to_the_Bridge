#!/usr/bin/env bash
# ============================================================================
#  ensure_campaign_infra.sh — recreate missing Batch queue / log group and
#  register the current picard-campaign job definition (1 vCPU / 2 GB,
#  --timeout 3600, OOM exit-without-retry).
#
#  Prerequisites:
#    AWS_PROFILE=picard   # assumes picard-deploy-role with ExternalId
#    ACCOUNT_ID, REGION, BUCKET env vars set (or pass as args)
#
#  Usage:
#    export AWS_PROFILE=picard REGION=us-east-1 ACCOUNT_ID=994254241749 BUCKET=<bucket>
#    ./ensure_campaign_infra.sh
#    ./ensure_campaign_infra.sh --register-only
#    ./ensure_campaign_infra.sh --smoke-submit 2   # array size 2 after ensure
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGION="${REGION:-us-east-1}"
ACCOUNT_ID="${ACCOUNT_ID:-}"
BUCKET="${BUCKET:-}"
CE_NAME="${CE_NAME:-picard-campaign-spot}"
QUEUE_NAME="${QUEUE_NAME:-picard-campaign-queue}"
LOG_GROUP="${LOG_GROUP:-/aws/batch/picard-campaign}"
JOB_DEF_NAME="${JOB_DEF_NAME:-picard-campaign}"
REGISTER_ONLY=0
SMOKE_SIZE=0

AWS_PROFILE_ARG=()
if [[ -n "${AWS_PROFILE:-}" ]]; then
  AWS_PROFILE_ARG=(--profile "$AWS_PROFILE")
fi

usage() {
  sed -n '2,16p' "$0" | tr -d '#'
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --register-only) REGISTER_ONLY=1; shift ;;
    --smoke-submit) SMOKE_SIZE="${2:?}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown arg: $1" >&2; usage ;;
  esac
done

if [[ -z "$ACCOUNT_ID" ]]; then
  ACCOUNT_ID="$(aws "${AWS_PROFILE_ARG[@]}" sts get-caller-identity --query Account --output text)"
fi
if [[ -z "$BUCKET" ]]; then
  echo "ERROR: set BUCKET=… (S3 results bucket name)" >&2
  exit 1
fi

echo "Ensuring campaign infra:"
echo "  profile    : ${AWS_PROFILE:-<default>}"
echo "  account    : $ACCOUNT_ID"
echo "  region     : $REGION"
echo "  bucket     : $BUCKET"
echo "  CE         : $CE_NAME"
echo "  queue      : $QUEUE_NAME"

if [[ "$REGISTER_ONLY" -eq 0 ]]; then
  # Compute environment must already exist (created once in README §5).
  ce_status="$(aws "${AWS_PROFILE_ARG[@]}" batch describe-compute-environments \
    --compute-environments "$CE_NAME" --region "$REGION" \
    --query 'computeEnvironments[0].status' --output text 2>/dev/null || true)"
  if [[ "$ce_status" != "VALID" ]]; then
    echo "ERROR: compute environment $CE_NAME status=$ce_status (want VALID)." >&2
    echo "Create it first (README §5)." >&2
    exit 1
  fi
  echo "  CE status  : $ce_status"

  # Log group (execution role cannot create it).
  if aws "${AWS_PROFILE_ARG[@]}" logs describe-log-groups \
      --log-group-name-prefix "$LOG_GROUP" --region "$REGION" \
      --query "logGroups[?logGroupName=='$LOG_GROUP'].logGroupName" \
      --output text | grep -qx "$LOG_GROUP"; then
    echo "  log group  : exists"
  else
    aws "${AWS_PROFILE_ARG[@]}" logs create-log-group \
      --log-group-name "$LOG_GROUP" --region "$REGION"
    echo "  log group  : created $LOG_GROUP"
  fi

  # Job queue (inventory has seen CE present with queue missing).
  q_status="$(aws "${AWS_PROFILE_ARG[@]}" batch describe-job-queues \
    --job-queues "$QUEUE_NAME" --region "$REGION" \
    --query 'jobQueues[0].status' --output text 2>/dev/null || true)"
  if [[ "$q_status" == "VALID" || "$q_status" == "CREATING" ]]; then
    echo "  queue      : $q_status"
  else
    aws "${AWS_PROFILE_ARG[@]}" batch create-job-queue \
      --job-queue-name "$QUEUE_NAME" \
      --state ENABLED --priority 1 \
      --compute-environment-order "order=1,computeEnvironment=$CE_NAME" \
      --region "$REGION"
    echo "  queue      : create requested"
  fi

  # Wait briefly for queue VALID.
  for _ in $(seq 1 30); do
    q_status="$(aws "${AWS_PROFILE_ARG[@]}" batch describe-job-queues \
      --job-queues "$QUEUE_NAME" --region "$REGION" \
      --query 'jobQueues[0].status' --output text)"
    [[ "$q_status" == "VALID" ]] && break
    sleep 2
  done
  echo "  queue      : $q_status"
  if [[ "$q_status" != "VALID" ]]; then
    echo "ERROR: queue did not become VALID" >&2
    exit 1
  fi
fi

# Register job definition from repo JSON (1 vCPU / 2048 MB, timeout 3600).
tmp="$(mktemp)"
sed -e "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" \
    -e "s/<REGION>/$REGION/g" \
    -e "s#<BUCKET>#$BUCKET#g" \
    "$ROOT/batch_job_definition.json" > "$tmp"

reg_out="$(aws "${AWS_PROFILE_ARG[@]}" batch register-job-definition \
  --cli-input-json "file://$tmp" --region "$REGION")"
rm -f "$tmp"
revision="$(echo "$reg_out" | python3 -c 'import json,sys; print(json.load(sys.stdin)["revision"])')"
echo "  job def    : $JOB_DEF_NAME:$revision registered"

if [[ "$SMOKE_SIZE" -gt 0 ]]; then
  if [[ "$SMOKE_SIZE" -lt 2 ]]; then
    echo "ERROR: Batch array size must be >= 2 (got $SMOKE_SIZE)" >&2
    exit 1
  fi
  s3_prefix="s3://$BUCKET/campaign/"
  echo "Submitting smoke array size=$SMOKE_SIZE …"
  AWS_PROFILE="${AWS_PROFILE:-}" "$ROOT/submit_array_job.sh" \
    "$SMOKE_SIZE" "$s3_prefix" "$QUEUE_NAME" "$JOB_DEF_NAME"
  echo "After smoke, classify failures:"
  echo "  AWS_PROFILE=${AWS_PROFILE:-picard} python3 $ROOT/classify_batch_failures.py --recent 1 --region $REGION"
fi

echo "Done."
