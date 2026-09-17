"""Ship blackwater plumbing: a holding tank excreta actually reaches.

EPA 842-R-07-005, *Cruise Ship Discharge Assessment Report* (2008), §2 —
survey of 29 Alaska cruise ships. Grade B; the reported ranges are frozen
and swept, the nominal is the reported average — none of it is fitted to
any outcome. Derivation: ``docs/norovirus/environmental_observation_v1.md``
§3.
"""

from __future__ import annotations

import math

# EPA 842-R-07-005 (2008) §2 — blackwater generation, 8.4 US gal/person/day
# average over 29 Alaska cruise ships.
BLACKWATER_L_PER_PERSON_DAY = 31.8
# Reported range 1.1 .. 27 gal/person/day; the sweep axis.
BLACKWATER_L_PER_PERSON_DAY_RANGE = (4.16, 102.2)
# Average holding time in the tank.
BLACKWATER_RESIDENCE_HOURS = 62.0
# Reported range 0.5 .. 170 h.
BLACKWATER_RESIDENCE_HOURS_RANGE = (0.5, 170.0)

# Recorded, deliberately NOT added on top of the per-capita rate, which
# already contains it (0.3 gal x ~6 voids/day = 1.8 gal, inside 8.4):
# vacuum flush volume; one gravity system reported 1 gal.
FLUSH_VOLUME_L = 1.14
FLUSH_VOLUME_L_RANGE = (1.14, 3.79)

# Declared Grade D, not a free parameter: all cleaned-up vomitus enters
# the sewage stream (docs/norovirus/environmental_observation_v1.md §3).
EMESIS_DRAIN_CAPTURE_FRACTION = 1.0


class BlackwaterHoldingTank:
    """A well-mixed (CSTR) ship-level raw-influent pool.

    Volume accrues at ``complement * l_per_person_day`` and drains each
    epoch at ``epoch_hours / residence_hours``, so the steady-state
    inventory is ``rate x residence`` and the concentration does not
    depend on the flush count. Declared conservative assumption: no decay
    is applied over the holding time — norovirus is stable at ambient over
    62 h — so this is a statement, not a constant.
    """

    def __init__(
        self,
        l_per_person_day: float = BLACKWATER_L_PER_PERSON_DAY,
        residence_hours: float = BLACKWATER_RESIDENCE_HOURS,
        emesis_drain_capture_fraction: float = EMESIS_DRAIN_CAPTURE_FRACTION,
    ) -> None:
        if not math.isfinite(l_per_person_day) or l_per_person_day <= 0.0:
            raise ValueError(
                "transmission.blackwater_plumbing.l_per_person_day must be "
                f"positive and finite, got {l_per_person_day!r}",
            )
        if not math.isfinite(residence_hours) or residence_hours <= 0.0:
            raise ValueError(
                "transmission.blackwater_plumbing.residence_hours must be "
                f"positive and finite, got {residence_hours!r}",
            )
        if (
            not math.isfinite(emesis_drain_capture_fraction)
            or not 0.0 <= emesis_drain_capture_fraction <= 1.0
        ):
            raise ValueError(
                "transmission.blackwater_plumbing."
                "emesis_drain_capture_fraction must be finite in [0, 1], "
                f"got {emesis_drain_capture_fraction!r}",
            )
        self.l_per_person_day = float(l_per_person_day)
        self.residence_hours = float(residence_hours)
        self.emesis_drain_capture_fraction = float(emesis_drain_capture_fraction)
        self.volume_l = 0.0
        self.copies_by_pathogen: dict[str, float] = {}
        self.complement = 0
        self.telemetry: dict[str, float] = {
            "copies_in": 0.0,
            "copies_discharged": 0.0,
            "volume_in_l": 0.0,
            "volume_discharged_l": 0.0,
            "stool_events": 0,
            "emesis_events": 0,
        }

    def add_copies(self, pathogen_id: str, copies: float, source: str) -> None:
        """Credit a mass to the tank. ``source`` is ``"stool"`` or ``"emesis"``."""
        if not math.isfinite(copies) or copies <= 0.0:
            return
        self.copies_by_pathogen[pathogen_id] = (
            self.copies_by_pathogen.get(pathogen_id, 0.0) + copies
        )
        self.telemetry["copies_in"] += copies
        key = f"{source}_events"
        if key in self.telemetry:
            self.telemetry[key] += 1

    def advance_epoch(
        self,
        hours_per_epoch: float,
        day_fraction_per_epoch: float,
    ) -> None:
        """Inflow for the epoch, then discharge at the residence-time rate."""
        inflow_l = (
            self.complement * self.l_per_person_day * day_fraction_per_epoch
        )
        self.volume_l += inflow_l
        self.telemetry["volume_in_l"] += inflow_l
        drain_fraction = min(1.0, hours_per_epoch / self.residence_hours)
        discharged_l = self.volume_l * drain_fraction
        self.volume_l -= discharged_l
        self.telemetry["volume_discharged_l"] += discharged_l
        kept = 1.0 - drain_fraction
        copies_before = sum(self.copies_by_pathogen.values())
        for pathogen_id in list(self.copies_by_pathogen):
            self.copies_by_pathogen[pathogen_id] *= kept
        self.telemetry["copies_discharged"] += copies_before * drain_fraction

    def concentration_copies_per_l(
        self, pathogen_id: str | None = None,
    ) -> float:
        """Copies per litre in the tank; 0.0 when empty."""
        if self.volume_l <= 0.0:
            return 0.0
        if pathogen_id is None:
            copies = sum(self.copies_by_pathogen.values())
        else:
            copies = self.copies_by_pathogen.get(pathogen_id, 0.0)
        return copies / self.volume_l
