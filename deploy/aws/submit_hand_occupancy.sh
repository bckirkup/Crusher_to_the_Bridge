#!/usr/bin/env bash
# Submit one NORO-HAND-STATIONARY-01 cell block as an AWS Batch array.
#
# BLOCK=fl_spr_12d            -> the 22 ignited spirit seeds through
#                              growth_chain_census (verbatim tier spec).
# BLOCK=classic_cruise_1900   -> the 20 EMESIS-SIZE-01 seeds through
#                              fomite_mass_balance (shipped bundle).
#
# One submission per block: child i runs seeds[i] and uploads its dump
# under S3_PREFIX/<block>/. Canary runs are single (non-array) jobs whose
# container override passes --index <flat cell index>; the array-index
# env var is reserved on Batch.
set -euo pipefail

USAGE="usage: submit_hand_occupancy.sh <bucket> [region] [queue] [job-definition]"
BUCKET="${1:?$USAGE}"
AWS_REGION="${2:-us-east-1}"
JOB_QUEUE="${3:-picard-campaign-queue}"
JOB_DEFINITION="${4:-picard-hand-occupancy}"

BLOCK="${BLOCK:-fl_spr_12d}"
SEEDS="${SEEDS:-8105,8107,8110,8112,8113,8114,8115,8117,8121,8123,8124,8129,8132,8135,8137,8148,8149,8156,8158,8159,8162,8163}"
MANIFEST="${MANIFEST:-picard_framework/runs/mega_cruise_campaign/noro_dose_refit_01_manifest.json}"
PATHOGEN_ID="${PATHOGEN_ID:-norwalk_gi}"
EPOCHS="${EPOCHS:-288}"
S3_PREFIX="${S3_PREFIX:-s3://${BUCKET}/campaign/noro_hand_stationary_01/}"
JOB_NAME="${JOB_NAME:-picard-hand-occupancy-${BLOCK}-$(date +%Y%m%d-%H%M%S)}"
AWS_PROFILE="${AWS_PROFILE:-picard}"
export AWS_PROFILE

ARRAY_SIZE="$(awk -F',' '{print NF}' <<<"$SEEDS")"

echo "Submitting hand occupancy array:"
echo "  name      : $JOB_NAME"
echo "  block     : $BLOCK"
echo "  seeds     : $SEEDS (array size $ARRAY_SIZE)"
echo "  manifest  : $MANIFEST"
echo "  epochs    : $EPOCHS"
echo "  pathogen  : $PATHOGEN_ID"
echo "  prefix    : $S3_PREFIX"
echo "  queue     : $JOB_QUEUE"
echo "  jobdef    : $JOB_DEFINITION"

# submit-job's --parameters shorthand splits comma lists (the seeds) and
# rejects empty values, so the cell goes in as a literal argv via
# --container-overrides; the Ref:: parameters the jobdef declares are
# still mandatory and are supplied alongside.
read -r -d '' SUBMIT_JSON <<JSON || true
{
  "jobName": "$JOB_NAME",
  "jobQueue": "$JOB_QUEUE",
  "jobDefinition": "$JOB_DEFINITION",
  "arrayProperties": {"size": $ARRAY_SIZE},
  "containerOverrides": {
    "command": [
      "deploy/aws/hand_occupancy_entrypoint.py",
      "--s3-prefix", "$S3_PREFIX",
      "--block", "$BLOCK",
      "--seeds", "$SEEDS",
      "--manifest", "$MANIFEST",
      "--pathogen-id", "$PATHOGEN_ID",
      "--epochs", "$EPOCHS"
    ]
  },
  "parameters": {
    "s3_prefix": "$S3_PREFIX",
    "block": "$BLOCK",
    "seeds": "array"
  }
}
JSON

aws batch submit-job \
  --region "$AWS_REGION" \
  --cli-input-json "$SUBMIT_JSON"
