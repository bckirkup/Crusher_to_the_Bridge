#!/usr/bin/env bash
# Wait for one Batch job of this campaign, fetch its raw artifact, and read the
# gate verdict out of it. Exit 0 only when the job SUCCEEDED, the artifact has
# no blocker.json and smoke_gates.json says passed: Batch exit 0 alone proves
# nothing, because the runner exits 0 after writing a blocker.
#   collect_job.sh <job-id> <block> <artifact-name> <work-dir>
set -euo pipefail
job="$1"; block="$2"; artifact="$3"; work="$4"
bucket="${CAMPAIGN_BUCKET:-crusherbucket-994254241749-us-east-1-an}"
profile="${AWS_PROFILE_NAME:-picard}"; region="${AWS_REGION:-us-east-1}"
# A reused work directory must not carry an earlier job's blocker or gates.
rm -rf "$work/raw"
mkdir -p "$work/raw"
while :; do
  status=$(aws --profile "$profile" batch describe-jobs --region "$region" --jobs "$job" \
    --query 'jobs[0].status' --output text)
  case "$status" in SUCCEEDED|FAILED) break ;; esac
  sleep 30
done
aws --profile "$profile" batch describe-jobs --region "$region" --jobs "$job" > "$work/describe.json"
echo "job $job $status"
[ "$status" = SUCCEEDED ] || exit 5
uri="s3://$bucket/campaign/contam_fleet_workup_fleet_01/$block/$artifact"
aws --profile "$profile" s3 cp --only-show-errors "$uri" "$work/$artifact"
tar -xzf "$work/$artifact" -C "$work/raw" --strip-components=0
sha256sum "$work/$artifact"
gates=$(find "$work/raw" -name smoke_gates.json | head -1)
if [ -n "$(find "$work/raw" -name blocker.json)" ]; then
  echo "BLOCKER"; cat "$(find "$work/raw" -name blocker.json | head -1)"; exit 6
fi
python3 - "$gates" <<'PY'
import json, sys
g = json.load(open(sys.argv[1]))
failed = g["failed"] if isinstance(g["failed"], int) else len(g["failed"])
checks = g["checks"] if isinstance(g["checks"], int) else len(g["checks"])
print(f"gates passed={g['passed']} checks={checks} failed={failed}")
sys.exit(0 if g["passed"] and not failed else 7)
PY
