#!/usr/bin/env python3
"""TRANSPORT-FIT-01 cell worker: run one (theta, arm_id, seed) replay cell.

One worker for both scenario designs (DP and GM are the same cell shape):
the block's ``args`` carry the design, theta and arm_id. The design's
``base_overrides`` block — the DP boxed_s1s2 configuration; absent on the
GM design — is applied to every cell's run spec after
``prepare_cell_run_spec`` composes the arm's own overrides, the
CREW-REACH-01 composition pattern verbatim.

The arm's ``transport_engine`` override writes
``config_overrides.hvac.transport_engine``; for a ``contamx`` cell the
worker ensures a runnable NIST ContamX binary exists before the spec is
built: a local ``third_party/contamx/`` drop wins, else the sha256-pinned
copy under ``campaign/covid_transport_fit_01/vendor/contamx3`` in the
campaign bucket is fetched
and ``CONTAMX_BINARY`` pointed at it. A contamx cell that still cannot
build ContamXTransportEngine fails closed — ``transport_engine: auto``
is unreachable by arm grammar.

``--num-epochs`` caps the voyage for local smoke validation only; Batch
runs always take the design's full declared voyage.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import math
import os
import stat
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    QuarantineAttributionLedger,
    apply_arm_overrides,
    cell_payload,
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import (  # noqa: E402
    load_covid_profile,
    run_fit_spec,
)

# The NIST ContamX 3.4.0.3 64-bit Linux binary, U.S. public domain, pinned
# by sha256 (the same digest CONTAM-PHASE2's field pre-stage verified).
_CONTAMX_SHA256 = (
    "d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b"
)
_CONTAMX_S3_BUCKET = "crusherbucket-994254241749-us-east-1-an"
_CONTAMX_S3_KEY = "campaign/covid_transport_fit_01/vendor/contamx3"


def _ensure_contamx_binary(raw: dict) -> str | None:
    """Point CONTAMX_BINARY at a runnable solver, or return None.

    Resolution mirrors ``engines.contamx_runner.find_contamx``: a local
    drop/config/env entry wins untouched; only when nothing resolves is
    the pinned S3 copy fetched. Returns the resolved path so the cell
    payload can echo it; a contamx cell treats ``None`` as fatal.
    """
    from engines.contamx_runner import find_contamx

    local = find_contamx({})
    if local is not None:
        return local
    dest = Path(tempfile.mkdtemp(prefix="crusher_contamx_bin_")) / "contamx3"
    import boto3

    client = boto3.client("s3")
    client.download_file(_CONTAMX_S3_BUCKET, _CONTAMX_S3_KEY, str(dest))
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    if digest != _CONTAMX_SHA256:
        raise SystemExit(
            f"contamx binary sha256 mismatch: got {digest}, "
            f"expected {_CONTAMX_SHA256}",
        )
    dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    os.environ["CONTAMX_BINARY"] = str(dest)
    return str(dest)


def base_overrides(design_path: str, repo_root: Path = _REPO_ROOT) -> dict:
    """The design's declared shared base (empty on designs without one)."""
    raw = json.loads(
        (repo_root / design_path).read_text(encoding="utf-8"),
    )
    return dict(raw.get("base_overrides") or {})


def _match_cell(
    design: object, theta: float, arm_id: str, seed: int,
) -> object:
    """The single design cell at (theta, arm_id, seed), or die."""
    matches = [
        cell for cell in enumerate_cells(design)
        if cell.arm_id == arm_id and cell.seed == seed
        and math.isclose(cell.theta, theta, rel_tol=1e-12)
    ]
    if len(matches) != 1:
        raise SystemExit(
            f"{len(matches)} cells match theta={theta} arm={arm_id} "
            f"seed={seed}; expected exactly 1",
        )
    return matches[0]


def _declared_engine(design: object, arm_id: str) -> str:
    """The arm's declared airflow solver: 'native' or 'contamx'."""
    overrides = design.arm_overrides(arm_id) if design.arms else {}
    return str(
        (overrides.get("transport_engine"))
        or "native",
    )


def run_transport_cell(
    design: object,
    cell: object,
    *,
    design_path: str,
    num_epochs: int | None = None,
) -> dict:
    """Run one cell: base_overrides composed under the arm's overrides."""
    engine = _declared_engine(design, cell.arm_id)
    binary_path = _ensure_contamx_binary({}) if engine == "contamx" else None
    if engine == "contamx" and binary_path is None:
        raise SystemExit(
            "contamx arm requested but no ContamX binary could be "
            "resolved or fetched; refusing to fall back to native",
        )
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=num_epochs, repo_root=str(_REPO_ROOT),
    )
    base = base_overrides(design_path)
    if base:
        apply_arm_overrides(
            raw, base,
            profile=load_covid_profile(str(_REPO_ROOT)),
            theta=cell.theta,
        )
    ledger = QuarantineAttributionLedger()
    sim = run_fit_spec(
        raw, repo_root=str(_REPO_ROOT), epoch_observer=ledger.observe,
    )
    # build_transport_engine returns native transport with only a printed
    # warning when an explicit "contamx" build fails — a completed voyage
    # under the wrong solver would score as a contamx result, so the cell
    # fails after the run rather than emit a mislabeled payload.
    resolved = (
        type(sim.contam_engine).__name__
        if getattr(sim, "contam_engine", None) is not None else None
    )
    expected = {
        "contamx": "ContamXTransportEngine",
        "native": "ContamTransportEngine",
    }[engine]
    if resolved != expected:
        raise SystemExit(
            f"arm {cell.arm_id!r} declared {engine!r} but the resolved "
            f"transport engine is {resolved!r}; refusing to emit a "
            f"fallback result",
        )
    payload = cell_payload(design, cell, sim, ledger, raw)
    payload["transport_engine_binary"] = binary_path
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", required=True,
                        help="repo-relative boarding-screen design JSON")
    parser.add_argument("--theta", required=True, type=float)
    parser.add_argument("--arm", required=True, help="design arm_id")
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--out", required=True,
                        help="directory the cell artifact is written to")
    parser.add_argument("--num-epochs", type=int, default=None,
                        help="smoke cap on voyage epochs (local only)")
    args = parser.parse_args(argv)

    design = load_design(str(_REPO_ROOT / args.design))
    cell = _match_cell(design, args.theta, args.arm, args.seed)
    runner = functools.partial(run_transport_cell, design_path=args.design)
    if args.num_epochs is not None:
        runner = functools.partial(
            runner, num_epochs=args.num_epochs,
        )
    payload = {
        "design_id": design.design_id,
        "sanitary_visit_mode": design.sanitary_visit_mode,
        "cell": cell.as_dict(),
        **runner(design, cell),
    }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / f"cell_{args.seed}.json"
    artifact.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8",
    )
    print(f"WROTE {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
