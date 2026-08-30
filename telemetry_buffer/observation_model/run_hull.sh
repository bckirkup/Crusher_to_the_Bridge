#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HULL="$1"
SPEC_DIR="$SCRIPT_DIR/specs/$HULL"
OUTPUT_DIR="$SCRIPT_DIR/results/$HULL"
LOG_PATH="$SCRIPT_DIR/$HULL.log"
mkdir -p "$OUTPUT_DIR"
total=$(find "$SPEC_DIR" -maxdepth 1 -type f -name '*.json' | wc -l)
done_count=0
failed=0
printf 'start total=%s hull=%s commit=9d06492\n' "$total" "$HULL" >"$LOG_PATH"
while IFS= read -r spec; do
  run_id=$(basename "$spec" .json)
  if [[ -f "$OUTPUT_DIR/$run_id.pilot.json" ]] &&
     grep -q '"ok": true' "$OUTPUT_DIR/$run_id.pilot.json"; then
    done_count=$((done_count + 1))
    printf '[%s/%s] %s SKIP already complete\n' \
      "$done_count" "$total" "$run_id" >>"$LOG_PATH"
    continue
  fi
  printf '[%s/%s] %s START\n' "$((done_count + failed + 1))" "$total" "$run_id" >>"$LOG_PATH"
  started=$(date +%s)
  if python3 "$SCRIPT_DIR/postfix_worker.py" "$spec" "$OUTPUT_DIR" >>"$LOG_PATH" 2>&1; then
    elapsed=$(( $(date +%s) - started ))
    done_count=$((done_count + 1))
    printf '[%s/%s] %s OK %ss\n' \
      "$((done_count + failed))" "$total" "$run_id" "$elapsed" >>"$LOG_PATH"
  else
    elapsed=$(( $(date +%s) - started ))
    failed=$((failed + 1))
    printf '[%s/%s] %s FAIL %ss\n' \
      "$((done_count + failed))" "$total" "$run_id" "$elapsed" >>"$LOG_PATH"
  fi
done < <(find "$SPEC_DIR" -maxdepth 1 -type f -name '*.json' -print | sort)
printf 'finished total=%s succeeded=%s failed=%s\n' \
  "$total" "$done_count" "$failed" >>"$LOG_PATH"
exit "$failed"
