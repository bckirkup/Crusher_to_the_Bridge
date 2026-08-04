"""Naval general-plan → Crusher ship-class importer.

Standalone tooling (not part of the simulation / dashboard runtime).
Pipeline: ingest PDF/images → vision LLM digest → SVG overlay edit
(GIMP/Krita/Inkscape) → deterministic synthesize → validate.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
