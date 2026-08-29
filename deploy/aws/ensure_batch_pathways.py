#!/usr/bin/env python3
"""Create/refresh the EC2 scale-to-zero Batch compute environments and queues.

One implementation for both platforms: ``ensure_campaign_infra.sh`` and
``ensure_analysis_infra.ps1`` both shell out to this module so the Linux and
Windows paths cannot drift.

Every compute environment created here is native EC2 with ``minvCpus`` and
``desiredvCpus`` at 0, so the pathway holds no instances while its queue is
empty. Instance families come from ``instance_pathways.json``.

Usage:
    python3 ensure_batch_pathways.py --pathway abm_campaign \
        --queue picard-campaign-queue --subnets subnet-a,subnet-b \
        --security-groups sg-a [--capacity spot] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PATHWAYS_FILE = HERE / "instance_pathways.json"

# Batch names the environment after the pathway so the console shows which
# workload class an instance belongs to.
CE_SUFFIX = {"spot": "spot", "on_demand": "ondemand"}
AMI_TYPE = {"x86_64": "ECS_AL2023", "arm64": "ECS_AL2023_ARM64"}
ALLOCATION = {
    "spot": "SPOT_PRICE_CAPACITY_OPTIMIZED",
    "on_demand": "BEST_FIT_PROGRESSIVE",
}
CE_STATUS_TERMINAL = ("VALID", "INVALID")
CE_WAIT_SECONDS = 300


def load_pathway(pathway: str, arch: str) -> list[str]:
    """Return the instance types for one pathway/architecture pair."""
    data = json.loads(PATHWAYS_FILE.read_text(encoding="utf-8"))
    if pathway not in data:
        options = sorted(k for k in data if not k.startswith("_"))
        raise SystemExit(f"unknown pathway {pathway!r}; known: {options}")
    types = data[pathway].get(arch)
    if not types:
        raise SystemExit(f"pathway {pathway!r} has no {arch!r} instance types")
    return types


def compute_resources(args: argparse.Namespace, types: list[str]) -> dict[str, Any]:
    """Build the scale-to-zero EC2 computeResources block."""
    resources: dict[str, Any] = {
        "type": "SPOT" if args.capacity == "spot" else "EC2",
        "allocationStrategy": ALLOCATION[args.capacity],
        "minvCpus": 0,
        "desiredvCpus": 0,
        "maxvCpus": args.max_vcpus,
        "instanceTypes": types,
        "subnets": split_csv(args.subnets),
        "securityGroupIds": split_csv(args.security_groups),
        "instanceRole": args.instance_profile,
        "ec2Configuration": [{"imageType": AMI_TYPE[args.arch]}],
        "tags": {"Project": "picard", "Pathway": args.pathway},
    }
    if args.capacity == "spot":
        resources["bidPercentage"] = args.bid_percentage
    if args.launch_template:
        resources["launchTemplate"] = {
            "launchTemplateName": args.launch_template,
            "version": "$Latest",
        }
    return resources


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def describe_ce(batch: Any, name: str) -> dict[str, Any] | None:
    envs = batch.describe_compute_environments(computeEnvironments=[name])
    envs = envs["computeEnvironments"]
    return envs[0] if envs else None


def wait_for_ce(batch: Any, name: str) -> str:
    deadline = time.monotonic() + CE_WAIT_SECONDS
    status = "CREATING"
    while time.monotonic() < deadline:
        current = describe_ce(batch, name)
        status = current["status"] if current else "MISSING"
        if status in CE_STATUS_TERMINAL:
            return status
        time.sleep(5)
    return status


def ensure_compute_env(batch: Any, name: str, args: argparse.Namespace) -> None:
    """Create the compute environment, or align an existing one in place."""
    types = load_pathway(args.pathway, args.arch)
    resources = compute_resources(args, types)
    existing = describe_ce(batch, name)

    if existing is None:
        print(f"  CE {name}: creating ({args.capacity}, {len(types)} instance types)")
        batch.create_compute_environment(
            computeEnvironmentName=name,
            type="MANAGED",
            state="ENABLED",
            computeResources=resources,
        )
    elif existing["computeResources"].get("type") != resources["type"]:
        raise SystemExit(
            f"CE {name} exists as {existing['computeResources'].get('type')}, "
            f"want {resources['type']}. Batch cannot change a compute "
            "environment's capacity type: delete it (after draining its "
            "queue) or pass --ce-name for a new one."
        )
    else:
        print(f"  CE {name}: updating instance types and scale-to-zero floor")
        batch.update_compute_environment(
            computeEnvironment=name,
            state="ENABLED",
            computeResources={
                key: resources[key]
                for key in (
                    "minvCpus",
                    "desiredvCpus",
                    "maxvCpus",
                    "instanceTypes",
                    "subnets",
                    "securityGroupIds",
                    "instanceRole",
                )
            },
        )

    status = wait_for_ce(batch, name)
    print(f"  CE {name}: status={status}")
    if status != "VALID":
        raise SystemExit(f"CE {name} did not become VALID (status={status})")


def ensure_queue(batch: Any, queue: str, ce_name: str) -> None:
    """Point the queue at the EC2 compute environment, creating it if needed."""
    found = batch.describe_job_queues(jobQueues=[queue])["jobQueues"]
    order = [{"order": 1, "computeEnvironment": ce_name}]
    if not found:
        print(f"  queue {queue}: creating -> {ce_name}")
        batch.create_job_queue(
            jobQueueName=queue,
            state="ENABLED",
            priority=1,
            computeEnvironmentOrder=order,
        )
        return

    attached = [
        entry["computeEnvironment"].rsplit("/", 1)[-1]
        for entry in found[0]["computeEnvironmentOrder"]
    ]
    if attached == [ce_name]:
        print(f"  queue {queue}: already -> {ce_name}")
        return
    print(f"  queue {queue}: repointing {attached} -> {ce_name}")
    from botocore.exceptions import ClientError  # noqa: PLC0415 - optional at import time

    try:
        batch.update_job_queue(
            jobQueue=queue, state="ENABLED", computeEnvironmentOrder=order
        )
    except ClientError as exc:
        raise SystemExit(
            f"could not repoint {queue} ({exc}). A queue cannot mix Fargate "
            "and EC2 compute environments; drain and delete the queue, or "
            "pass a fresh --queue name and update the submit scripts."
        ) from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pathway", required=True)
    parser.add_argument("--queue", required=True)
    parser.add_argument("--ce-name", default=None)
    parser.add_argument("--subnets", default="")
    parser.add_argument("--security-groups", default="")
    parser.add_argument("--region", default=None)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--arch", default="x86_64", choices=sorted(AMI_TYPE))
    parser.add_argument("--capacity", default="spot", choices=sorted(ALLOCATION))
    parser.add_argument("--max-vcpus", type=int, default=256)
    parser.add_argument("--bid-percentage", type=int, default=100)
    parser.add_argument("--instance-profile", default="ecsInstanceRole")
    parser.add_argument(
        "--launch-template",
        default=None,
        help="EC2 launch template supplying a larger root volume (CmdStan draws).",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    ce_name = args.ce_name or f"picard-{args.pathway.replace('_', '-')}-{CE_SUFFIX[args.capacity]}"

    if args.dry_run:
        types = load_pathway(args.pathway, args.arch)
        print(json.dumps({"computeEnvironmentName": ce_name, "computeResources": compute_resources(args, types)}, indent=2))
        return 0

    if not args.subnets or not args.security_groups:
        raise SystemExit("--subnets and --security-groups are required")

    import boto3  # noqa: PLC0415 - keeps --dry-run usable without boto3 installed

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    batch = session.client("batch")
    print(f"Ensuring {args.pathway} pathway: CE={ce_name} queue={args.queue}")
    ensure_compute_env(batch, ce_name, args)
    ensure_queue(batch, args.queue, ce_name)
    print("  pathway ready (0 instances until a job is queued)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
