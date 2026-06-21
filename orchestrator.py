#!/usr/bin/env python3
"""
orchestrator.py -- The Master Intercom Loop  (Phase 4+)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Thin wrapper around :class:`ShipSimulation` from the Picard framework.
All domain logic lives in the shared helper modules
(``orchestrator_init``, ``orchestrator_epoch``, ``orchestrator_record``,
``orchestrator_chronic``, etc.) and is invoked by ShipSimulation.

Usage::

    python orchestrator.py              # uses num_epochs from config.yaml (default 24)
    python orchestrator.py --epochs 250 # override to 250 epochs
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def run() -> None:
    """Execute the full simulation: init, epoch loop, finalization."""
    sep = "\u2550" * 80
    print(sep)
    print("  CRUSHER TO THE BRIDGE  \u00b7  Phase 4+ \u2013 Multi-Pathogen & Microflora")
    print(sep)
    print()

    parser = argparse.ArgumentParser(
        description="Crusher to the Bridge \u2013 simulation orchestrator",
    )
    parser.add_argument(
        "--epochs", type=int, default=None,
        help="Number of simulation epochs (overrides config.yaml num_epochs)",
    )
    args = parser.parse_args()

    from picard_framework import PicardRunSpec, ShipSimulation

    kwargs: dict = {}
    if args.epochs is not None:
        kwargs["num_epochs"] = args.epochs

    spec = PicardRunSpec.from_legacy_yaml(repo_root=REPO_ROOT, **kwargs)
    sim = ShipSimulation(spec, display=True)
    sim.run()
    sim.finalize()


if __name__ == "__main__":
    try:
        run()
    except FileNotFoundError as exc:
        print(f"\n[ERROR] Missing file: {exc}", file=sys.stderr)
        print("  Hint: run 'python tools/sanity_checker.py --from-config' to validate paths.", file=sys.stderr)
        sys.exit(1)
    except (KeyError, ValueError) as exc:
        print(f"\n[ERROR] Configuration problem: {exc}", file=sys.stderr)
        print("  Hint: check crusher_labs/config.yaml and data/ JSON files.", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
