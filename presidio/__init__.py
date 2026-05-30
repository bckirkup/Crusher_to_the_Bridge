"""
Presidio — fleet-level meta-simulation over Picard ship cruises.

Configuration libraries live under ``presidio/data/`` (catalog, config,
economics, experiences). Use :mod:`presidio_runner` as the CLI entry point.
"""

from presidio.run_spec import PresidioRunSpec

__all__ = ["PresidioRunSpec"]
