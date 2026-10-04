#!/usr/bin/env python3
"""Submit one NORO-OUTBREAK-04 cell window as an AWS Batch array.

The pinned campaign image (picard-campaign digest
sha256:017a0db816da98a8a9cbf2fe6ca864a4a9e1e061d876216ef9439fc2cbc76202,
merge ``1e158d47``) predates ``d71b301a`` "Fix _emit_emesis wrapper
drift under CAREGIVER-V1 signature": inside it,
``tools/diag/instrument_common.wrap_emit_emesis`` still declares the
pre-CAREGIVER-V1 signature and dies on the first emesis deposit. A new
image is out of scope, so this submitter applies the same fix as a
runtime overlay: each array child appends the repo's current
``wrap_emit_emesis`` definition to ``instrument_common.py`` (the later
def shadows the stale one at import) before running the normal
``import_map_entrypoint`` argv. Instrumentation-only — the engine call
is byte-identical, the patch restores what ``d71b301a`` blessed.

usage::

    deploy/aws/submit_outbreak_04.py --tier TIER --size N --index-offset M \
        [--s3-prefix URI] [--job-definition NAME:REV] [--queue Q] \
        [--job-name NAME] [--dry-run]
"""

from __future__ import annotations

import argparse
import ast
import textwrap
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

_DEFAULT_PREFIX = (
    "s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_outbreak_04/"
)
_DEFAULT_MANIFEST = (
    # The image serves specs via the byte-identical 01 manifest; the
    # committed noro_outbreak_04_manifest.json is the design-of-record.
    "picard_framework/runs/mega_cruise_campaign/noro_outbreak_01_manifest.json"
)
_ENTRYPOINT = "/app/deploy/aws/import_map_entrypoint.py"
_PATCH_TARGET = "/app/tools/diag/instrument_common.py"


def _wrapper_source() -> str:
    """The repo's current ``wrap_emit_emesis`` def, verbatim."""
    path = _REPO_ROOT / "tools" / "diag" / "instrument_common.py"
    src = path.read_text(encoding="utf-8")
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name == "wrap_emit_emesis":
            return textwrap.dedent(ast.get_source_segment(src, node) or "")
    raise SystemExit("wrap_emit_emesis not found in instrument_common.py")


def _payload(argv: list[str], patch_src: str) -> str:
    """The ``python3 -c`` program run as the child's CMD.

    Appends the fixed wrapper to instrument_common.py (shadowing the
    stale def, so the driver's fresh interpreter picks it up), then
    runs the unmodified entrypoint module as __main__.
    """
    return "\n".join(
        [
            "import runpy, sys",
            f"PATCH = {patch_src!r}",
            f"with open({_PATCH_TARGET!r}, 'a') as fh:",
            "    fh.write('\\n\\n' + PATCH)",
            f"sys.argv = {argv!r}",
            f"runpy.run_path({_ENTRYPOINT!r}, run_name='__main__')",
        ],
    )


def _argv(args: argparse.Namespace) -> list[str]:
    return [
        _ENTRYPOINT,
        "--s3-prefix",
        args.s3_prefix,
        "--manifest",
        args.manifest,
        "--pathogen-id",
        args.pathogen_id,
        "--tier",
        args.tier,
        # index=-1: array children resolve AWS_BATCH_JOB_ARRAY_INDEX.
        "--index",
        "-1",
        "--index-offset",
        str(args.index_offset),
    ]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--index-offset", type=int, default=0)
    parser.add_argument("--s3-prefix", default=_DEFAULT_PREFIX)
    parser.add_argument("--manifest", default=_DEFAULT_MANIFEST)
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--job-definition", default="picard-noro-outbreak-04:1")
    parser.add_argument("--queue", default="picard-campaign-queue")
    parser.add_argument("--job-name", default=None)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    job_name = args.job_name or (
        f"picard-ob04-{args.tier}-o{args.index_offset}"
        f"-{time.strftime('%Y%m%d-%H%M%S')}"
    )
    payload = _payload(_argv(args), _wrapper_source())
    request = {
        "jobName": job_name,
        "jobQueue": args.queue,
        "jobDefinition": args.job_definition,
        "containerOverrides": {"command": ["-c", payload]},
    }
    if args.size >= 2:
        request["arrayProperties"] = {"size": args.size}
    if args.dry_run:
        print(payload)
        return
    import boto3

    job = boto3.client("batch", region_name=args.region).submit_job(**request)
    print(f"{job_name} -> {job['jobId']} (size {args.size}, offset {args.index_offset})")


if __name__ == "__main__":
    main()
