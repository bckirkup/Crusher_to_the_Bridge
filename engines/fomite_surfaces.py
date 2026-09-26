"""engines.fomite_surfaces
~~~~~~~~~~~~~~~~~~~~~~~~~~

Per-item-class fomite surface bookkeeping (NORO-FOMITE-DISAGG-01).

This is a labelled default-off arm implementing option B of
``docs/proposals/fomite_surface_disaggregation_spec.md``: the pooled zone
surface pool is disaggregated into per-item-class sub-pools sharing the
unit's mass, each with its own area, touch share and cleaning coverage.
The default ``pooled`` representation takes none of this code; the shipped
run is bit-identical to the pre-change tree (identity per the spec's
section 3.4: deposits, uniform decay/disinfection, cleaning and pickup all
act on the pool, never re-associated per class).

The item tables (``ITEM_AREA_M2``, ``ZONE_ITEM_SETS``) were moved here
verbatim from ``tools/noro_diag/high_touch_area_envelope.py`` so the engine
arm and the envelope tool read one enumeration; the tool re-imports and
re-exports them. All areas and counts remain derived/declared Grade C
content of the NORO-HIGH-TOUCH-AREA-01 envelope, adopted nowhere as a
constant change.
"""

from __future__ import annotations

import json
import math
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

_REPO_ROOT = os.path.realpath(
    os.path.join(os.path.dirname(__file__), ".."),
)

FOMITE_REPRESENTATIONS = ("pooled", "per_surface")
DEFAULT_FOMITE_REPRESENTATION = "pooled"
TOUCH_SHARE_MODES = ("areal", "declared")
DEFAULT_TOUCH_SHARE_MODE = "areal"
FOMITE_AREA_BASES = ("shipped", "derived")
DEFAULT_FOMITE_AREA_BASIS = "shipped"
FOMITE_ITEM_READINGS = ("shared", "hardware", "broad")
DEFAULT_FOMITE_ITEM_READING = "shared"

# Numerical floor, not an epidemiological constant: a surface pool (or a
# per-unit class set) that decays below this is set to exactly 0.0 so
# ``<= 0`` gates close on a de-facto empty pool instead of on rounding
# luck (NORO-TOUCH-SHARE-02 §6). Far below one genome copy.
SURFACE_RESIDUE_FLOOR_GEC = 1e-12


def floor_surface_residue(mass: float) -> float:
    return 0.0 if mass < SURFACE_RESIDUE_FLOOR_GEC else mass


# Physical pickup threshold, above the numerical floor and distinct from it:
# genome equivalent copies are discrete, so a surface pool (pooled zone
# total, or per_surface unit total) holding less than one whole copy has no
# virion available for a hand to pick up. Below it the pickup gate closes
# and no pickup RNG is drawn against the pool. What is "measured": nothing
# environmental -- this is the quantisation of the mass unit the engine
# carries (GEC), declared as one copy. Setting: every zone and unit, all
# pathogens, both fomite representations, default path.
# Value: 1 GEC (exact, not an interval; the quantum is one copy).
# Grade C (declared assumption -- listed in norovirus_model_history.md §10).
# Origin: Tr (transcribed from this repository's own mass-unit definition,
# docs/ledger/NORO-GATE-FLOOR-01.md; no journal source defines a pickup
# threshold and none is claimed).
# Mass is *gated, not zeroed*: the sub-copy pool stays in the reservoir,
# keeps decaying, and the gate reopens if later deposition carries the
# total back to >= 1 GEC. Mass conservation is therefore unchanged by this
# constant; only the 1e-12 residue floor below it discards mass.
SURFACE_PICKUP_MIN_GEC = 1.0


def pickup_gate_open(surface_mass: float) -> bool:
    """True when a pool holds at least one whole genome copy to pick up."""
    return surface_mass >= SURFACE_PICKUP_MIN_GEC

# --- item areas in m2 -------------------------------------------------------
# (area_m2, src, note). ``measured``/``qmra`` items are read off the paper
# named in the note; ``declared`` items are this repository's geometry for an
# object no retrieved source dimensions.
ITEM_AREA_M2: dict[str, tuple[float, str, str]] = {
    "toilet_seat": (0.0700, "measured", "Park 2015 toilet seat surface 700 cm2"),
    "flush_actuator": (0.0010, "measured", "Gerba 2025 flush handle 10 cm2"),
    "door_lever": (0.0016, "qmra", "Weir 2016 aluminium fomite 15.8 cm2"),
    "small_panel": (0.0059, "qmra", "Weir 2016 plastic laminate 593 cm2"),
    "work_plane": (1.0450, "qmra", "Weir 2016 wood laminate 11.25 ft2"),
    "light_switch": (0.0020, "declared", "switch plate ~20 cm2"),
    "tap_set": (0.0100, "declared", "two handles + spout ~100 cm2"),
    "stall_latch": (0.0020, "declared", "latch + edge ~20 cm2"),
    "remote_or_phone": (0.0100, "declared", "handset/remote ~100 cm2"),
    "button_or_dispenser": (0.0050, "declared", "actuator + bezel ~50 cm2"),
    "grab_rail_m": (0.1000, "declared", "0.1 m2 of rail per linear metre"),
    "utensil": (0.0050, "declared", "serving tong / handle ~50 cm2"),
    "tableware_per_seat": (0.0200, "declared", "glass + cutlery + menu ~200 cm2"),
    "table_top_per_seat": (0.1200, "declared", "place setting footprint"),
    "chair_touched": (0.1500, "declared", "seat pan + back + arms"),
    "bed_and_linen_touched": (0.3000, "declared", "headboard, rail, top sheet edge"),
    "wardrobe_front": (0.1000, "declared", "door fronts and pulls"),
}

# --- item sets --------------------------------------------------------------
# ``fixed`` items are per zone unit; ``per_occupant`` items scale with the
# zone's declared max_occupancy (a 400-seat dining room has 400 place
# settings). ``hardware`` and ``broad`` differ only in which items count.
ZONE_ITEM_SETS: dict[str, dict[str, Any]] = {
    "cabin": {
        "unit": "one stateroom compartment (2 berths)",
        "occupants": 2,
        "count_anchor": "Heo 2023 38-item list; Park 2015 cabin swab sites",
        "hardware_fixed": {
            "door_lever": 3,
            "light_switch": 4,
            "tap_set": 1,
            "flush_actuator": 1,
            "toilet_seat": 1,
            "remote_or_phone": 2,
            "button_or_dispenser": 2,
            "grab_rail_m": 0.5,
        },
        "broad_extra_fixed": {
            "work_plane": 1,
            "bed_and_linen_touched": 2,
            "wardrobe_front": 1,
        },
        "shared_fixed": {
            "door_lever": 3,
            "light_switch": 4,
            "tap_set": 1,
            "flush_actuator": 1,
            "toilet_seat": 1,
            "remote_or_phone": 2,
            "button_or_dispenser": 2,
            "grab_rail_m": 0.5,
            "wardrobe_front": 1,
            "work_plane": 1,
        },
    },
    "sanitary": {
        "unit": "one water closet",
        "occupants": 1,
        "count_anchor": "Carling 2009 30.6 objects per shipboard public restroom",
        "hardware_fixed": {
            "flush_actuator": 1,
            "toilet_seat": 1,
            "stall_latch": 1,
            "door_lever": 1,
            "tap_set": 1,
            "button_or_dispenser": 2,
            "grab_rail_m": 0.5,
        },
        "broad_extra_fixed": {"work_plane": 0.3},
        "shared_fixed": {
            "flush_actuator": 1,
            "toilet_seat": 1,
            "stall_latch": 1,
            "door_lever": 1,
            "tap_set": 1,
            "button_or_dispenser": 2,
            "grab_rail_m": 0.5,
            "work_plane": 0.3,
        },
    },
    "dining": {
        "unit": "one dining zone",
        "count_anchor": "Jin 2022 restaurant touch classes; Lei 2017 per-seat scale",
        "hardware_fixed": {
            "door_lever": 4,
            "button_or_dispenser": 6,
            "utensil": 20,
            "tap_set": 2,
        },
        "hardware_per_occupant": {"tableware_per_seat": 1},
        "broad_extra_per_occupant": {"table_top_per_seat": 1, "chair_touched": 1},
        "shared_fixed": {
            "door_lever": 4,
            "button_or_dispenser": 6,
            "utensil": 20,
            "tap_set": 2,
        },
        "shared_per_occupant": {"table_top_per_seat": 1, "chair_touched": 1},
    },
    "crew_mess": {
        "unit": "one crew mess zone",
        "count_anchor": "as dining; crew service pattern",
        "hardware_fixed": {
            "door_lever": 3,
            "button_or_dispenser": 4,
            "utensil": 15,
            "tap_set": 2,
        },
        "hardware_per_occupant": {"tableware_per_seat": 1},
        "broad_extra_per_occupant": {"table_top_per_seat": 1, "chair_touched": 1},
        "shared_fixed": {
            "door_lever": 3,
            "button_or_dispenser": 4,
            "utensil": 15,
            "tap_set": 2,
        },
        "shared_per_occupant": {"table_top_per_seat": 1, "chair_touched": 1},
    },
    "public": {
        "unit": "one public zone",
        "count_anchor": "Lei 2017 3.3 touchable surfaces per seat; Ackerley 2025 lobby",
        "hardware_fixed": {
            "door_lever": 8,
            "button_or_dispenser": 10,
            "grab_rail_m": 20,
        },
        "hardware_per_occupant": {"small_panel": 0.5},
        "broad_extra_per_occupant": {"chair_touched": 1},
        "shared_fixed": {
            "door_lever": 8,
            "button_or_dispenser": 10,
            "grab_rail_m": 20,
        },
        "shared_per_occupant": {"chair_touched": 1, "small_panel": 0.5},
    },
    "galley": {
        "unit": "one galley zone",
        "count_anchor": "fixed equipment, not occupancy",
        "hardware_fixed": {
            "door_lever": 12,
            "utensil": 60,
            "tap_set": 6,
            "button_or_dispenser": 25,
        },
        "broad_extra_fixed": {"work_plane": 18},
        "shared_fixed": {
            "door_lever": 12,
            "utensil": 60,
            "tap_set": 6,
            "button_or_dispenser": 25,
            "work_plane": 18,
        },
    },
}


@dataclass(frozen=True)
class PerSurfaceConfig:
    """Resolved ``transmission.fomite_*`` block for the per-surface arm."""

    touch_share: str = DEFAULT_TOUCH_SHARE_MODE
    area_basis: str = DEFAULT_FOMITE_AREA_BASIS
    item_reading: str = DEFAULT_FOMITE_ITEM_READING
    declared_shares: dict[str, dict[str, float]] = field(default_factory=dict)
    cleaning_coverage_by_item_class: dict[str, float] = field(
        default_factory=dict,
    )


def _validated_enum(tx: Mapping[str, Any], key: str, allowed: tuple[str, ...], default: str) -> str:
    value = str(tx.get(key, default))
    if value not in allowed:
        raise ValueError(
            f"transmission.{key} must be one of {allowed}, got {value!r}",
        )
    return value


def _parse_declared_shares(raw: Any) -> dict[str, dict[str, float]]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError(
            "transmission.fomite_touch_share_table must be a mapping from "
            "zone class to item-class shares",
        )
    return {
        zone_class: _parse_declared_share_row(zone_class, shares)
        for zone_class, shares in raw.items()
    }


def _parse_declared_share_row(zone_class: Any, shares: Any) -> dict[str, float]:
    """Validate one zone class's item-class share mapping."""
    if zone_class not in ZONE_ITEM_SETS:
        raise ValueError(
            "transmission.fomite_touch_share_table: unknown zone class "
            f"{zone_class!r}; allowed {sorted(ZONE_ITEM_SETS)}",
        )
    if not isinstance(shares, Mapping):
        raise ValueError(
            "transmission.fomite_touch_share_table."
            f"{zone_class} must be a mapping from item class to share",
        )
    parsed: dict[str, float] = {}
    for item_class, value in shares.items():
        if item_class not in ITEM_AREA_M2:
            raise ValueError(
                "transmission.fomite_touch_share_table."
                f"{zone_class}: unknown item class {item_class!r}; "
                f"allowed {sorted(ITEM_AREA_M2)}",
            )
        share = float(value)
        if not math.isfinite(share) or share <= 0.0:
            raise ValueError(
                "transmission.fomite_touch_share_table."
                f"{zone_class}.{item_class} must be finite and > 0, "
                f"got {value!r}",
            )
        parsed[item_class] = share
    if abs(sum(parsed.values()) - 1.0) > 1e-9:
        raise ValueError(
            "transmission.fomite_touch_share_table."
            f"{zone_class} shares must sum to 1 (got "
            f"{sum(parsed.values())!r})",
        )
    return parsed


def _parse_item_class_coverage(cleaning: Any) -> dict[str, float]:
    if cleaning is None:
        return {}
    if not isinstance(cleaning, Mapping):
        raise ValueError("transmission.surface_cleaning must be a mapping")
    raw = cleaning.get("routine_coverage_by_item_class") or {}
    if not isinstance(raw, Mapping):
        raise ValueError(
            "transmission.surface_cleaning.routine_coverage_by_item_class "
            "must be a mapping from item class to coverage",
        )
    coverage: dict[str, float] = {}
    for item_class, value in raw.items():
        if item_class not in ITEM_AREA_M2:
            raise ValueError(
                "transmission.surface_cleaning."
                f"routine_coverage_by_item_class: unknown item class "
                f"{item_class!r}; allowed {sorted(ITEM_AREA_M2)}",
            )
        fraction = float(value)
        if not math.isfinite(fraction) or not 0.0 <= fraction <= 1.0:
            raise ValueError(
                "transmission.surface_cleaning."
                f"routine_coverage_by_item_class.{item_class} must be "
                f"finite in [0, 1], got {value!r}",
            )
        coverage[item_class] = fraction
    return coverage


def _safe_table_path(path: str | os.PathLike) -> str:
    """Canonicalise a declared-table path and refuse anything outside the repo."""
    resolved = os.path.realpath(path)
    if resolved != _REPO_ROOT and not resolved.startswith(
        _REPO_ROOT + os.sep,
    ):
        raise ValueError(
            f"declared share table {path!r} is outside the repository",
        )
    return resolved


def load_declared_share_table(
    path: str | os.PathLike,
    item_reading: str = DEFAULT_FOMITE_ITEM_READING,
) -> dict[str, dict[str, float]]:
    """Read a declared touch-share table file (NORO-TOUCH-SHARE-01).

    The file's ``item_reading`` must equal the reading the engine will
    enumerate units under, and it must carry a ``shares`` mapping in the
    ``transmission.fomite_touch_share_table`` shape. The returned table is
    raw: zone/item membership and share values are validated by
    ``_parse_declared_shares`` when the config resolves.
    """
    with open(_safe_table_path(path), encoding="utf-8") as handle:
        raw = json.load(handle)
    reading = raw.get("item_reading")
    if reading != item_reading:
        raise ValueError(
            f"declared share table {path}: item_reading {reading!r} does "
            f"not match the resolved fomite_item_reading {item_reading!r}",
        )
    shares = raw.get("shares")
    if not isinstance(shares, Mapping):
        raise ValueError(
            f"declared share table {path}: missing 'shares' mapping",
        )
    return dict(shares)


def _check_declared_completeness(
    table: dict[str, dict[str, float]],
    item_reading: str,
) -> None:
    """Refuse a declared table that drops classes a unit enumerates.

    Under ``declared`` a class absent from the table receives share 0.0 in
    ``_touch_shares`` and silently loses its deposit mass, so a zone class
    present in the table must name exactly the classes the reading
    enumerates. Zone classes absent from the table fall back to ``areal``
    whole and are not checked.
    """
    for zone_class, shares in table.items():
        declared = set(shares)
        enumerated = set(unit_item_counts(zone_class, item_reading, 1))
        if declared != enumerated:
            raise ValueError(
                "transmission.fomite_touch_share_table."
                f"{zone_class}: declared classes {sorted(declared)} must "
                f"equal the {item_reading} unit inventory "
                f"{sorted(enumerated)}",
            )


def parse_per_surface_config(tx: Mapping[str, Any]) -> PerSurfaceConfig | None:
    """Resolve the fomite representation selector (NORO-FOMITE-DISAGG-01).

    Absent or ``pooled`` returns ``None``: the engine then runs the shipped
    pooled path and touches none of the per-surface state. Any other value
    must name a representation in ``FOMITE_REPRESENTATIONS``.
    """
    rep = _validated_enum(
        tx, "fomite_representation",
        FOMITE_REPRESENTATIONS, DEFAULT_FOMITE_REPRESENTATION,
    )
    if rep == "pooled":
        return None
    item_reading = _validated_enum(
        tx, "fomite_item_reading",
        FOMITE_ITEM_READINGS, DEFAULT_FOMITE_ITEM_READING,
    )
    declared_shares = _parse_declared_shares(
        tx.get("fomite_touch_share_table") or {},
    )
    if declared_shares:
        _check_declared_completeness(declared_shares, item_reading)
    return PerSurfaceConfig(
        touch_share=_validated_enum(
            tx, "fomite_touch_share",
            TOUCH_SHARE_MODES, DEFAULT_TOUCH_SHARE_MODE,
        ),
        area_basis=_validated_enum(
            tx, "fomite_area_basis",
            FOMITE_AREA_BASES, DEFAULT_FOMITE_AREA_BASIS,
        ),
        item_reading=item_reading,
        declared_shares=declared_shares,
        cleaning_coverage_by_item_class=_parse_item_class_coverage(
            tx.get("surface_cleaning", {}) or {},
        ),
    )


def unit_item_counts(
    zone_class: str,
    reading: str,
    water_closets: int,
) -> dict[str, float]:
    """Fixed item counts of one zone unit under one reading.

    ``broad`` is hardware plus the touched planes of furniture, mirroring
    ``_envelope_for_class`` in the envelope tool. Per-occupant item groups
    are not included this session: the engine has no zone ``max_occupancy``
    at unit resolution (recorded as an open item in the ledger). For
    ``sanitary`` every count scales by the unit's water-closet count. Zero
    counts are dropped.
    """
    spec = ZONE_ITEM_SETS[zone_class]
    if reading == "broad":
        counts = dict(spec.get("hardware_fixed", {}))
        for item, n in spec.get("broad_extra_fixed", {}).items():
            counts[item] = counts.get(item, 0.0) + n
    else:
        counts = dict(spec.get(f"{reading}_fixed", {}))
    if zone_class == "sanitary":
        counts = {item: n * water_closets for item, n in counts.items()}
    return {item: float(n) for item, n in counts.items() if n > 0}


@dataclass(frozen=True)
class UnitInventory:
    """One unit's per-item-class enumeration under the resolved config."""

    zone_class: str
    counts: dict[str, float]
    area_each_m2: dict[str, float]
    touch_share: dict[str, float]
    total_area_m2: float
    coverage: dict[str, float]
    mean_coverage: float


class PerSurfaceFomiteState:
    """Per-(unit, pathogen, item-class) mass bookkeeping for the arm.

    The class sub-pools are a view over the unit's pooled mass: every
    engine write to the pooled compartment is mirrored here through the
    guarded hooks, so uniform operations (decay, disinfection, delivery
    scaling) stay uniform across classes as the spec's identity section
    requires.
    """

    def __init__(self, cfg: PerSurfaceConfig) -> None:
        self.cfg = cfg
        self.mass: dict[tuple[str, str, str], float] = {}
        self.cleanable: dict[tuple[str, str, str], float] = {}
        self._inventory: dict[str, UnitInventory] = {}

    def register_unit(
        self,
        unit_key: str,
        zone_class: str,
        pooled_area_m2: float,
        water_closets: int,
        zone_coverage: float,
    ) -> UnitInventory:
        """Return the unit's item inventory, building it once."""
        inv = self._inventory.get(unit_key)
        if inv is not None:
            return inv
        counts = unit_item_counts(zone_class, self.cfg.item_reading, water_closets)
        raw = sum(n * ITEM_AREA_M2[c][0] for c, n in counts.items())
        if self.cfg.area_basis == "shipped" and raw > 0.0:
            area_each = {
                c: ITEM_AREA_M2[c][0] * pooled_area_m2 / raw for c in counts
            }
            total_area = float(pooled_area_m2)
        else:
            area_each = {c: ITEM_AREA_M2[c][0] for c in counts}
            total_area = raw
        share = self._touch_shares(zone_class, counts, area_each, total_area)
        coverage = {
            c: self.cfg.cleaning_coverage_by_item_class.get(c, zone_coverage)
            for c in counts
        }
        inv = UnitInventory(
            zone_class=zone_class,
            counts=counts,
            area_each_m2=area_each,
            touch_share=share,
            total_area_m2=total_area,
            coverage=coverage,
            mean_coverage=sum(share[c] * coverage[c] for c in counts),
        )
        self._inventory[unit_key] = inv
        return inv

    def inventory(self, unit_key: str) -> UnitInventory | None:
        return self._inventory.get(unit_key)

    def _touch_shares(
        self,
        zone_class: str,
        counts: dict[str, float],
        area_each: dict[str, float],
        total_area: float,
    ) -> dict[str, float]:
        declared = (
            self.cfg.declared_shares.get(zone_class)
            if self.cfg.touch_share == "declared"
            else None
        )
        if declared is not None:
            return {c: declared.get(c, 0.0) for c in counts}
        if total_area <= 0.0:
            return dict.fromkeys(counts, 0.0)
        return {c: counts[c] * area_each[c] / total_area for c in counts}

    def deposit(
        self,
        unit_key: str,
        pathogen_id: str,
        mass: float,
        inv: UnitInventory,
    ) -> None:
        """Split one pooled deposit across classes by touch share."""
        for item_class, share in inv.touch_share.items():
            key = (unit_key, pathogen_id, item_class)
            self.mass[key] = self.mass.get(key, 0.0) + mass * share
            self.cleanable[key] = (
                self.cleanable.get(key, 0.0)
                + mass * share * inv.coverage[item_class]
            )

    def scale(self, unit_key: str, pathogen_id: str, factor: float) -> None:
        """Apply one uniform retention to every class of (unit, pathogen)."""
        for key in self._keys(unit_key, pathogen_id):
            self.mass[key] *= factor
            self.cleanable[key] = min(
                self.mass[key],
                self.cleanable.get(key, 0.0) * factor,
            )
        self._floor_unit(unit_key, pathogen_id)

    def pickup_requests(
        self,
        inv: UnitInventory,
        unit_key: str,
        pathogen_id: str,
        contacts: float,
        used_fraction: float,
        hand_area_m2: float,
        transfer_efficiency: float,
    ) -> dict[str, float]:
        """One target's requested mass per item class.

        The product order mirrors the pooled request: under ``areal``
        shares ``count*area/total`` cancels the per-class denominator and
        the class requests sum to the pooled request to fp tolerance.
        """
        requests: dict[str, float] = {}
        for item_class, count in inv.counts.items():
            mass_c = self.mass.get((unit_key, pathogen_id, item_class), 0.0)
            request = (
                contacts
                * (used_fraction * hand_area_m2 / (count * inv.area_each_m2[item_class]))
                * transfer_efficiency
                * mass_c
                * inv.touch_share[item_class]
            )
            requests[item_class] = min(mass_c, max(0.0, request))
        return requests

    def consume(
        self,
        unit_key: str,
        pathogen_id: str,
        delivered_by_class: dict[str, float],
    ) -> None:
        """Remove delivered mass class by class.

        The cleanable compartment sheds the same fraction the pooled
        ``_scale_surface_mass`` applies (``cleanable * remaining/old``),
        so delivery is a uniform removal across both compartments.
        """
        for item_class, delivered in delivered_by_class.items():
            key = (unit_key, pathogen_id, item_class)
            old_mass = self.mass.get(key, 0.0)
            new_mass = max(0.0, old_mass - delivered)
            self.mass[key] = new_mass
            self.cleanable[key] = min(
                new_mass,
                self.cleanable.get(key, 0.0)
                * (new_mass / old_mass if old_mass > 0.0 else 0.0),
            )
        self._floor_unit(unit_key, pathogen_id)

    def routine_clean(
        self,
        unit_key: str,
        pathogen_id: str,
        multiplier: float,
    ) -> float:
        """Apply one routine pass per class; return the total retention."""
        old_total = self.total(unit_key, pathogen_id)
        if old_total <= 0.0:
            return 1.0
        new_total = 0.0
        for key in self._keys(unit_key, pathogen_id):
            mass_c = self.mass.get(key, 0.0)
            if mass_c <= 0.0:
                continue
            old_cleanable = min(mass_c, self.cleanable.get(key, 0.0))
            retention = 1.0 - (old_cleanable / mass_c) * (1.0 - multiplier)
            self.mass[key] = mass_c * retention
            self.cleanable[key] = old_cleanable * multiplier
            new_total += self.mass[key]
        self._floor_unit(unit_key, pathogen_id)
        new_total = self.total(unit_key, pathogen_id)
        return new_total / old_total

    def disinfect(
        self,
        unit_key: str,
        pathogen_id: str,
        cleanable_factor: float,
        missed_factor: float,
    ) -> float:
        """One outbreak pass per class; return the total retention.

        The cleanable compartment takes ``cleanable_factor`` and the
        missed fraction takes ``missed_factor``, the same split the
        pooled ``_disinfect_zone`` applies to each compartment.
        """
        old_total = self.total(unit_key, pathogen_id)
        if old_total <= 0.0:
            return 1.0
        new_total = 0.0
        for key in self._keys(unit_key, pathogen_id):
            mass_c = self.mass.get(key, 0.0)
            if mass_c <= 0.0:
                continue
            old_cleanable = min(mass_c, self.cleanable.get(key, 0.0))
            old_missed = mass_c - old_cleanable
            self.mass[key] = (
                old_cleanable * cleanable_factor
                + old_missed * missed_factor
            )
            self.cleanable[key] = old_cleanable * cleanable_factor
            new_total += self.mass[key]
        self._floor_unit(unit_key, pathogen_id)
        new_total = self.total(unit_key, pathogen_id)
        return new_total / old_total

    def _floor_unit(self, unit_key: str, pathogen_id: str) -> None:
        # Floor on the unit total, never per class, so the areal arm stays
        # identical to pooled (which floors its zone total).
        if self.total(unit_key, pathogen_id) < SURFACE_RESIDUE_FLOOR_GEC:
            for key in self._keys(unit_key, pathogen_id):
                self.mass[key] = 0.0
                self.cleanable[key] = 0.0

    def _keys(
        self,
        unit_key: str,
        pathogen_id: str,
    ) -> list[tuple[str, str, str]]:
        return [
            key for key in self.mass
            if key[0] == unit_key and key[1] == pathogen_id
        ]

    def total(self, unit_key: str, pathogen_id: str) -> float:
        return sum(self.mass.get(key, 0.0) for key in self._keys(unit_key, pathogen_id))

    def cleanable_total(self, unit_key: str, pathogen_id: str) -> float:
        return sum(
            self.cleanable.get(key, 0.0)
            for key in self._keys(unit_key, pathogen_id)
        )

    def classes(self, unit_key: str, pathogen_id: str) -> list[str]:
        return [key[2] for key in self._keys(unit_key, pathogen_id)]

    def class_density_per_m2(
        self,
        unit_key: str,
        pathogen_id: str,
    ) -> dict[str, float]:
        """Per-class mass over its enumerated area (diagnostic)."""
        inv = self._inventory.get(unit_key)
        if inv is None:
            return {}
        density: dict[str, float] = {}
        for item_class, count in inv.counts.items():
            area = count * inv.area_each_m2[item_class]
            mass_c = self.mass.get((unit_key, pathogen_id, item_class), 0.0)
            density[item_class] = mass_c / area if area > 0.0 else 0.0
        return density
