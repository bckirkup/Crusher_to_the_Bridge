"""Fleet sentinel surveillance analysis (port introduction hazards).

Ancillary to the ship ABM: reads voyage configs and exported observations to
infer port-specific introduction hazards. The itinerary here is a read-only
view over ``engines.voyage_itinerary`` config — never a second itinerary model.
See ``docs/sentinel/sentinel_surveillance_spec.md``.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
