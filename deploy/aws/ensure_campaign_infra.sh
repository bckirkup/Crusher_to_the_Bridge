#!/usr/bin/env bash
# ============================================================================
#  ensure_campaign_infra.sh — ensure the EC2 Spot scale-to-zero campaign
#  pathway (compute environment / queue / log group) and register the current
#  picard-campaign job definition (1 vCPU / 2 GB, --timeout 3600,
#  OOM exit-without-retry).
#
#  Prerequisites:
#    AWS_PROFILE=picard   # assumes picard-deploy-role with ExternalId
#    ACCOUNT_ID, REGION, BUCKET env vars set (or pass as args)
#    SUBNET_IDS, SECURITY_GROUP_IDS  # only needed to create/refresh the CE
#
#  Usage:
#    export AWS_PROFILE=picard REGION=us-east-1 ACCOUNT_ID=<ACCOUNT_ID> BUCKET=<bucket>
#    ./ensure_campaign_infra.sh
#    ./ensure_campaign_infra.sh --register-only
#    ./ensure_campaign_infra.sh --smoke-submit 2   # array size 2 after ensure
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGION="${REGION:-us-east-1}"
ACCOUNT_ID="${ACCOUNT_ID:-}"
BUCKET="${BUCKET:-}"
CE_NAME="${CE_NAME:-picard-abm-campaign-spot}"
PATHWAY="${PATHWAY:-abm_campaign}"
SUBNET_IDS="${SUBNET_IDS:-}"
SECURITY_GROUP_IDS="${SECURITY_GROUP_IDS:-}"
MAX_VCPUS="${MAX_VCPUS:-256}"
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

  # EC2 Spot compute environment (minvCpus 0) + queue. Shared implementation
  # with ensure_analysis_infra.ps1 so the two platforms cannot drift.
  if [[ -z "$SUBNET_IDS" || -z "$SECURITY_GROUP_IDS" ]]; then
    echo "ERROR: set SUBNET_IDS and SECURITY_GROUP_IDS to ensure $CE_NAME" >&2
    echo "       (or pass --register-only to skip compute-environment work)" >&2
    exit 1
  fi
  python3 "$ROOT/ensure_batch_pathways.py" \
    --pathway "$PATHWAY" \
    --ce-name "$CE_NAME" \
    --queue "$QUEUE_NAME" \
    --capacity spot \
    --max-vcpus "$MAX_VCPUS" \
    --subnets "$SUBNET_IDS" \
    --security-groups "$SECURITY_GROUP_IDS" \
    --region "$REGION" \
    ${AWS_PROFILE:+--profile "$AWS_PROFILE"}

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
trap 'rm -f "$tmp"' EXIT
sed -e "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" \
    -e "s/<REGION>/$REGION/g" \
    -e "s#<BUCKET>#$BUCKET#g" \
    "$ROOT/batch_job_definition.json" > "$tmp"

reg_out="$(aws "${AWS_PROFILE_ARG[@]}" batch register-job-definition \
  --cli-input-json "file://$tmp" --region "$REGION")"
rm -f "$tmp"
trap - EXIT
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
