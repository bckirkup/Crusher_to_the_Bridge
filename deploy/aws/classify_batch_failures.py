#!/usr/bin/env python3
"""
classify_batch_failures.py — classify AWS Batch array-child attempts.

Separates Spot reclaim from OOM (exit 137 / OutOfMemoryError), attempt
timeouts, and other failures so operators can tell whether Fargate Spot
reclaims or the 1 vCPU / 2 GB sizing is biting.

Examples::

    AWS_PROFILE=picard python3 deploy/aws/classify_batch_failures.py \\
        --job-id <parentArrayJobId> --region us-east-1

    AWS_PROFILE=picard python3 deploy/aws/classify_batch_failures.py \\
        --queue picard-campaign-queue --region us-east-1 \\
        --out-json failure_report.json

    AWS_PROFILE=picard python3 deploy/aws/classify_batch_failures.py \\
        --job-id <parentArrayJobId> --region us-east-1 \\
        --s3-uri s3://bucket/campaign/_ops/failure_report_<id>.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from simulation_utils.paths import confine_to_base, validated_open  # noqa: E402

SPOT_RE = re.compile(r"Host EC2|Spot|TASK FAILED TO START.*spot", re.IGNORECASE)
OOM_REASON_RE = re.compile(r"OutOfMemoryError", re.IGNORECASE)
TIMEOUT_RE = re.compile(r"timeout|TimeoutExpired|Attempt duration", re.IGNORECASE)


def _cwd_root() -> str:
    return os.path.realpath(os.getcwd())


def safe_path(path: Path | str) -> str:
    try:
        return confine_to_base(_cwd_root(), str(path))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def classify_attempt(
    *,
    status_reason: str | None,
    exit_code: int | None,
    container_reason: str | None,
) -> str:
    """Return one of: spot_reclaim, oom, timeout, other, ok."""
    status = status_reason or ""
    reason = container_reason or ""
    combined = f"{status} {reason}"

    if exit_code == 0 and not status and not reason:
        return "ok"
    if exit_code == 0 and not OOM_REASON_RE.search(combined) and not SPOT_RE.search(combined):
        # Successful attempt that Batch still lists (rare on children).
        if not status or status.upper() in {"NONE", "SUCCESS", "SUCCEEDED"}:
            return "ok"

    # Fargate Spot reclaim often SIGKILLs with exit 137 and
    # statusReason "Your Spot Task was interrupted." — check Spot BEFORE OOM.
    if SPOT_RE.search(combined):
        return "spot_reclaim"
    if OOM_REASON_RE.search(combined) or exit_code == 137:
        return "oom"
    if TIMEOUT_RE.search(combined):
        return "timeout"
    if exit_code == 0:
        return "ok"
    return "other"


def _boto3_session(profile: str | None, region: str):
    try:
        import boto3  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("boto3 is required (pip install boto3).") from exc
    if profile:
        return boto3.Session(profile_name=profile, region_name=region)
    return boto3.Session(region_name=region)


def _list_child_job_ids(batch, parent_job_id: str) -> list[str]:
    """List all array child job IDs for a parent array job."""
    child_ids: list[str] = []
    for status in (
        "SUBMITTED",
        "PENDING",
        "RUNNABLE",
        "STARTING",
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
    ):
        token = None
        while True:
            kwargs: dict[str, Any] = {
                "arrayJobId": parent_job_id,
                "jobStatus": status,
            }
            if token:
                kwargs["nextToken"] = token
            resp = batch.list_jobs(**kwargs)
            for summary in resp.get("jobSummaryList", []):
                jid = summary.get("jobId")
                if jid:
                    child_ids.append(jid)
            token = resp.get("nextToken")
            if not token:
                break
    # Deduplicate while preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for jid in child_ids:
        if jid not in seen:
            seen.add(jid)
            ordered.append(jid)
    return ordered


def _recent_parent_job_ids(batch, queue: str, limit: int = 5) -> list[str]:
    ids: list[str] = []
    for status in ("RUNNING", "SUCCEEDED", "FAILED", "SUBMITTED", "PENDING", "RUNNABLE"):
        resp = batch.list_jobs(jobQueue=queue, jobStatus=status, maxResults=min(100, limit * 5))
        for summary in resp.get("jobSummaryList", []):
            # Array parents have arrayProperties.size; children have arrayProperties.index.
            props = summary.get("arrayProperties") or {}
            if "size" in props and "index" not in props:
                ids.append(summary["jobId"])
            if len(ids) >= limit:
                return ids
    return ids


def _chunks(items: list[str], size: int = 100):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def describe_and_classify(batch, job_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chunk in _chunks(job_ids, 100):
        if not chunk:
            continue
        resp = batch.describe_jobs(jobs=chunk)
        for job in resp.get("jobs", []):
            attempts = job.get("attempts") or []
            if not attempts:
                # Job never started an attempt — still classify statusReason.
                klass = classify_attempt(
                    status_reason=job.get("statusReason"),
                    exit_code=None,
                    container_reason=None,
                )
                rows.append(
                    {
                        "job_id": job.get("jobId"),
                        "job_name": job.get("jobName"),
                        "status": job.get("status"),
                        "attempt_index": None,
                        "class": klass,
                        "status_reason": job.get("statusReason"),
                        "exit_code": None,
                        "container_reason": None,
                        "log_stream": (job.get("container") or {}).get("logStreamName"),
                        "job_definition": job.get("jobDefinition"),
                    }
                )
                continue
            for idx, attempt in enumerate(attempts):
                container = attempt.get("container") or {}
                klass = classify_attempt(
                    status_reason=attempt.get("statusReason") or job.get("statusReason"),
                    exit_code=container.get("exitCode"),
                    container_reason=container.get("reason"),
                )
                rows.append(
                    {
                        "job_id": job.get("jobId"),
                        "job_name": job.get("jobName"),
                        "status": job.get("status"),
                        "attempt_index": idx,
                        "class": klass,
                        "status_reason": attempt.get("statusReason") or job.get("statusReason"),
                        "exit_code": container.get("exitCode"),
                        "container_reason": container.get("reason"),
                        "log_stream": container.get("logStreamName"),
                        "job_definition": job.get("jobDefinition"),
                        "started_at": attempt.get("startedAt"),
                        "stopped_at": attempt.get("stoppedAt"),
                    }
                )
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(r["class"] for r in rows)
    total = sum(counts.values()) or 1
    by_job: dict[str, set[str]] = {}
    for r in rows:
        by_job.setdefault(r["job_id"], set()).add(r["class"])
    jobs_with_oom = sum(1 for classes in by_job.values() if "oom" in classes)
    jobs_with_spot = sum(1 for classes in by_job.values() if "spot_reclaim" in classes)
    samples = {
        klass: [r for r in rows if r["class"] == klass][:5]
        for klass in ("spot_reclaim", "oom", "timeout", "other")
    }
    return {
        "attempt_counts": dict(counts),
        "attempt_rates": {k: round(v / total, 4) for k, v in counts.items()},
        "jobs_total": len(by_job),
        "jobs_with_oom": jobs_with_oom,
        "jobs_with_spot_reclaim": jobs_with_spot,
        "samples": samples,
    }


def parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise SystemExit(f"--s3-uri must look like s3://bucket/key, got {uri!r}")
    return parsed.netloc, parsed.path.lstrip("/")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify AWS Batch campaign array-child attempts "
        "(Spot reclaim vs OOM vs timeout vs other).",
    )
    parser.add_argument("--job-id", action="append", default=[], help="Parent array job ID (repeatable)")
    parser.add_argument("--queue", default="picard-campaign-queue", help="Job queue for --recent")
    parser.add_argument(
        "--recent",
        type=int,
        default=0,
        help="If >0 and no --job-id, classify this many recent parent array jobs on --queue",
    )
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"))
    parser.add_argument(
        "--profile",
        default=os.environ.get("AWS_PROFILE"),
        help="AWS named profile (default: AWS_PROFILE env, e.g. picard)",
    )
    parser.add_argument("--out-json", default=None, help="Write full report JSON locally")
    parser.add_argument("--out-csv", default=None, help="Write per-attempt CSV locally")
    parser.add_argument(
        "--s3-uri",
        default=None,
        help="Optional s3://bucket/key to upload the JSON report",
    )
    args = parser.parse_args(argv)

    session = _boto3_session(args.profile, args.region)
    batch = session.client("batch")

    parent_ids = list(args.job_id)
    if not parent_ids:
        if args.recent <= 0:
            args.recent = 1
        parent_ids = _recent_parent_job_ids(batch, args.queue, limit=args.recent)
        if not parent_ids:
            print(f"No parent array jobs found on queue {args.queue!r}.", file=sys.stderr)
            return 1

    all_rows: list[dict[str, Any]] = []
    parents: list[dict[str, Any]] = []
    for parent_id in parent_ids:
        parent_resp = batch.describe_jobs(jobs=[parent_id])
        parent_jobs = parent_resp.get("jobs") or []
        parent_meta = parent_jobs[0] if parent_jobs else {"jobId": parent_id}
        child_ids = _list_child_job_ids(batch, parent_id)
        rows = describe_and_classify(batch, child_ids)
        summary = summarize(rows)
        parents.append(
            {
                "job_id": parent_id,
                "status": parent_meta.get("status"),
                "status_reason": parent_meta.get("statusReason"),
                "array_summary": (parent_meta.get("arrayProperties") or {}).get("statusSummary"),
                "job_definition": parent_meta.get("jobDefinition"),
                "child_count": len(child_ids),
                "summary": summary,
            }
        )
        for row in rows:
            row["parent_job_id"] = parent_id
        all_rows.extend(rows)

    report = {
        "region": args.region,
        "queue": args.queue,
        "parents": parents,
        "overall": summarize(all_rows),
        "attempts": all_rows,
    }

    print(json.dumps({"parents": parents, "overall": report["overall"]}, indent=2))

    if args.out_json:
        path = safe_path(args.out_json)
        with validated_open(path, "w", allowed_roots=[_cwd_root()], encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
            fh.write("\n")
        print(f"Wrote {path}", file=sys.stderr)

    if args.out_csv:
        path = safe_path(args.out_csv)
        fieldnames = [
            "parent_job_id",
            "job_id",
            "job_name",
            "status",
            "attempt_index",
            "class",
            "status_reason",
            "exit_code",
            "container_reason",
            "log_stream",
            "job_definition",
            "started_at",
            "stopped_at",
        ]
        with validated_open(path, "w", allowed_roots=[_cwd_root()], encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in all_rows:
                writer.writerow(row)
        print(f"Wrote {path}", file=sys.stderr)

    if args.s3_uri:
        bucket, key = parse_s3_uri(args.s3_uri)
        s3 = session.client("s3")
        body = json.dumps(report, indent=2).encode("utf-8")
        s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")
        print(f"Uploaded s3://{bucket}/{key}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
