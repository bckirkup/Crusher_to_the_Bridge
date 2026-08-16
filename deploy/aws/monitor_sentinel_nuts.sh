#!/usr/bin/env bash
set -euo pipefail

JOB_ID="${1:?usage: monitor_sentinel_nuts.sh <job-id> <bucket> [region]}"
BUCKET="${2:?usage: monitor_sentinel_nuts.sh <job-id> <bucket> [region]}"
REGION="${3:-us-east-1}"

while true; do
  SUMMARY="$(env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
    AWS_PROFILE=picard aws batch describe-jobs --jobs "$JOB_ID" --region "$REGION" \
    --query 'jobs[0].{status:status,reason:statusReason,summary:arrayProperties.statusSummary}' \
    --output json)"
  echo "$SUMMARY"
  STATUS="$(printf '%s' "$SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
  case "$STATUS" in
    SUCCEEDED|FAILED) break ;;
  esac
  sleep 60
done

env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
  AWS_PROFILE=picard aws s3 sync \
  "s3://${BUCKET}/campaign/sentinel_nuts_ladder_v1/cells/" \
  "tmp_nuts_batch_${JOB_ID}/" \
  --region "$REGION"
