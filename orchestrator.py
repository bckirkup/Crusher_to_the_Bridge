#!/usr/bin/env python3
"""
orchestrator.py – Legacy CLI entry for single-ship Crusher-to-the-Bridge runs.

Delegates to Picard_Framework :class:`ShipSimulation` while preserving the
original command-line interface and display output.

Usage::

    python orchestrator.py              # uses num_epochs from config.yaml (default 24)
    python orchestrator.py --epochs 250 # override to 250 epochs
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from picard_framework import PicardRunSpec, ShipSimulation
from orchestrator_types import REPO_ROOT


def run() -> None:
    """Execute the full simulation: init, epoch loop, finalization."""
    sep = "═" * 80
    print(sep)
    print("  CRUSHER TO THE BRIDGE  ·  Phase 4+ – Multi-Pathogen & Microflora")
    print(sep)
    print()

    parser = argparse.ArgumentParser(
        description="Crusher to the Bridge – simulation orchestrator",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help="Number of simulation epochs (overrides config.yaml num_epochs)",
    )
    args = parser.parse_args()

    run_spec = PicardRunSpec.from_legacy_yaml(
        REPO_ROOT,
        num_epochs=args.epochs,
    )
    sim = ShipSimulation(run_spec, display=True, repo_root=REPO_ROOT)
    sim.run()
    sim.finalize(display=True)


if __name__ == "__main__":
    run()
    sys.exit(0)
