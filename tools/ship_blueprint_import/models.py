"""Pydantic models for the ShipDigest intermediate representation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ZoneType = Literal["Free", "Dining", "Room", "Medical", "Engineering", "Sanitary"]
TrafficLevel = Literal["low", "medium", "high"]
OpeningStatus = Literal["draft", "confirmed", "engineer_review"]
RoleGroup = Literal["crew", "passenger"]


class DeckInfo(BaseModel):
    id: str
    page: int = Field(ge=1)
    role: str = ""
    elevation_m: float | None = Field(
        default=None,
        description="Relative Contam level elevation (m); auto-stacked if omitted",
    )
    plan_bbox_norm: list[float] | None = Field(
        default=None,
        description=(
            "Normalized [x0, y0, x1, y1] page-image box of the drawn deck plan "
            "view. Sheets carry title blocks and margins; when omitted the whole "
            "page is treated as the plan (legacy behaviour)."
        ),
    )
    hull_x_span_m: list[float] | None = Field(
        default=None,
        description=(
            "[x_start, x_end] metres of hull length covered by plan_bbox_norm "
            "(bow datum at length_m, stern at 0 — same axis as zone display.x). "
            "Defaults to [0, length_m]."
        ),
    )
    hull_y_span_m: list[float] | None = Field(
        default=None,
        description=(
            "[y_start, y_end] metres of beam covered by plan_bbox_norm. "
            "Defaults to [0, beam_m]."
        ),
    )

    @field_validator("plan_bbox_norm", "hull_x_span_m", "hull_y_span_m")
    @classmethod
    def _span_lengths(cls, value: list[float] | None) -> list[float] | None:
        if value is None:
            return value
        if len(value) not in (2, 4):
            raise ValueError("span/bbox lists must have 2 or 4 entries")
        return [float(v) for v in value]


class ZoneDigest(BaseModel):
    id: str
    type: ZoneType
    deck: str
    page: int = Field(ge=1)
    polygon_norm: list[list[float]] = Field(
        default_factory=list,
        description="Normalized [0,1]x[0,1] polygon vertices (page image space)",
    )
    max_occupancy: int | None = Field(default=None, ge=1)
    volume_m3_est: float | None = Field(default=None, gt=0)
    floor_area_m2_est: float | None = Field(default=None, gt=0)
    elevation_m: float | None = None
    traffic: TrafficLevel = "medium"
    serves: list[str] = Field(
        default_factory=list,
        description=(
            "Zone ids this block serves (e.g. a Sanitary head block's served "
            "deck cluster), matching spatial_layout.schema.json `serves`"
        ),
    )
    notes: str = ""

    @field_validator("id")
    @classmethod
    def _id_no_spaces(cls, value: str) -> str:
        cleaned = value.strip().replace(" ", "_")
        if not cleaned:
            raise ValueError("zone id must be non-empty")
        return cleaned

    @field_validator("polygon_norm")
    @classmethod
    def _polygon_points(cls, value: list[list[float]]) -> list[list[float]]:
        if not value:
            return value
        if len(value) < 3:
            raise ValueError("polygon_norm needs at least 3 vertices")
        out: list[list[float]] = []
        for pt in value:
            if len(pt) != 2:
                raise ValueError("each polygon vertex must be [x, y]")
            x, y = float(pt[0]), float(pt[1])
            out.append([max(0.0, min(1.0, x)), max(0.0, min(1.0, y))])
        return out


class HvacHint(BaseModel):
    id: str
    rooms: list[str]
    ach: float = Field(default=6.0, ge=0)
    oa_fraction: float | None = Field(default=None, ge=0, le=1)
    filter_preset: str | None = None
    description: str = ""


class AdjacencyHint(BaseModel):
    model_config = {"populate_by_name": True}

    from_: str = Field(alias="from")
    to: str
    type: str = "passageway"


class OpeningHint(BaseModel):
    """Contam orifice between two spatial zones (engineer-editable draft)."""

    model_config = {"populate_by_name": True}

    from_: str = Field(alias="from")
    to: str
    type: str = "passageway"
    area_m2: float | None = Field(default=None, gt=0)
    schedule: str | None = Field(
        default=None,
        description="Hobbyist schedule key hint (DoorTrafficW / HatchOccasionalW / …)",
    )
    status: OpeningStatus = "draft"
    notes: str = ""


class CrossZoneHint(BaseModel):
    model_config = {"populate_by_name": True}

    from_: str = Field(alias="from")
    to: str
    flow_rate_m3h: float = Field(default=50.0, ge=0)
    path: str = "ladder_well"
    is_hvac_ducted: bool = False
    description: str = ""


class CrewClassBlock(BaseModel):
    """One row of a proposed crew manifest (agent-class level)."""

    class_id: str
    role_group: RoleGroup = "crew"
    count: int = Field(ge=1)
    berth_zone: str | None = Field(
        default=None, description="Zone id where the class sleeps"
    )
    duty_zone: str | None = Field(
        default=None, description="Zone id where the class works"
    )
    notes: str = ""


class ComplementProposal(BaseModel):
    """Proposed nominal complement + class manifest for the platform."""

    passengers: int = Field(default=0, ge=0)
    crew: int = Field(default=0, ge=0)
    source: str = ""
    manifest: list[CrewClassBlock] = Field(default_factory=list)


VentKind = Literal[
    "cowl", "mushroom", "gooseneck", "skylight", "air_port",
    "vent_trunk", "air_shaft", "fan_room", "uptake", "funnel",
]
VentFacing = Literal[
    "fore", "aft", "port", "starboard", "up", "down", "unknown"
]
VentDirection = Literal["supply", "exhaust", "unknown"]
ShipEra = Literal[
    "usn_ww2", "usn_coldwar", "usn_modern", "rn_ww2",
    "noaa_research", "merchant_ww2", "generic",
]


class VentMarker(BaseModel):
    """A ventilation termination read off a GA sheet.

    `evidence` separates sheet reads (the marker is drawn/labeled at this
    position) from era-typical placements the digest records as priors.
    """

    id: str
    page: int = Field(ge=1)
    position_norm: list[float] = Field(
        description="Normalized [x, y] sheet position of the marker"
    )
    deck: str | None = Field(
        default=None,
        description="Deck id the marker feeds/extracts (its termination)",
    )
    kind: VentKind = "cowl"
    facing: VentFacing = "unknown"
    direction: VentDirection = "unknown"
    serves_zone: str | None = Field(
        default=None,
        description="Zone id the marker clearly terminates in, when legible",
    )
    evidence: Literal["sheet_read", "era_plausible"] = "sheet_read"
    notes: str = ""

    @field_validator("position_norm")
    @classmethod
    def _pos_pair(cls, value: list[float]) -> list[float]:
        if len(value) != 2:
            raise ValueError("position_norm must be [x, y]")
        return [max(0.0, min(1.0, float(v))) for v in value]


class TankMarker(BaseModel):
    """A named tank/compartment label read off the sheet (plumbing anchor)."""

    label: str = Field(description="Label as drawn, e.g. 'F.W. TANK A-101-F'")
    page: int = Field(ge=1)
    position_norm: list[float]
    deck: str | None = None
    notes: str = ""

    @field_validator("position_norm")
    @classmethod
    def _tank_pos(cls, value: list[float]) -> list[float]:
        if len(value) != 2:
            raise ValueError("position_norm must be [x, y]")
        return [max(0.0, min(1.0, float(v))) for v in value]


class SystemsDigest(BaseModel):
    """Ventilation/plumbing evidence read from the sheet + era typing."""

    era: ShipEra = "generic"
    vent_markers: list[VentMarker] = Field(default_factory=list)
    tanks: list[TankMarker] = Field(default_factory=list)


class ContamHints(BaseModel):
    """Starter ContamW authoring hints for Path A side-chain (Target B)."""

    filter_preset: str = "MERV13"
    wind_profile: str = "ship_hull"
    oa_fraction: float = Field(default=0.2, ge=0, le=1)
    hvac_duty: float = Field(default=0.5, ge=0)
    envelope_leak_m2: float = Field(default=0.0001, gt=0)
    duct_hvac_ids: list[str] = Field(
        default_factory=list,
        description=(
            "AHU ids that get fiction Darcy duct spines "
            "(placeholder until engineer replaces)"
        ),
    )
    deck_temp_offset_K: dict[str, float] = Field(default_factory=dict)
    orifice_type_map: dict[str, str] = Field(default_factory=dict)
    handoff_notes: list[str] = Field(default_factory=list)
    skip_duct_spines: bool = Field(
        default=True,
        description=(
            "Naval GA default: omit fiction ducts; "
            "engineer authors real ducts in ContamW"
        ),
    )


class ShipDigest(BaseModel):
    """Coarse naval zone model extracted from general-arrangement drawings."""

    platform_id: str
    class_name: str = ""
    description: str = ""
    length_m: float = Field(default=100.0, gt=0)
    beam_m: float = Field(default=12.0, gt=0)
    crew_estimate: int = Field(default=100, ge=1)
    ceiling_height_m: float = Field(default=2.8, gt=0)
    decks: list[DeckInfo] = Field(default_factory=list)
    zones: list[ZoneDigest] = Field(min_length=1)
    hvac_hints: list[HvacHint] = Field(default_factory=list)
    adjacency_hints: list[AdjacencyHint] = Field(default_factory=list)
    opening_hints: list[OpeningHint] = Field(default_factory=list)
    cross_zone_hints: list[CrossZoneHint] = Field(default_factory=list)
    contam_hints: ContamHints = Field(default_factory=ContamHints)
    graywater_zones: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    isolation_unit_capacity: int = Field(default=0, ge=0)
    complement: ComplementProposal | None = Field(
        default=None,
        description=(
            "Proposed nominal complement + crew manifest; synthesize emits "
            "nominal_complement into spatial_layout.json and a "
            "crew_manifest.json proposal"
        ),
    )
    systems: SystemsDigest | None = Field(
        default=None,
        description=(
            "Ventilation/plumbing evidence read from the sheet (vent markers, "
            "tank labels) plus the ship's era type; synthesize maps it through "
            "era rules into HVAC group enrichment and a systems notes ledger"
        ),
    )

    @field_validator("platform_id")
    @classmethod
    def _snake_platform(cls, value: str) -> str:
        cleaned = value.strip().lower().replace("-", "_").replace(" ", "_")
        if not cleaned.replace("_", "").isalnum():
            raise ValueError("platform_id must be snake_case alphanumeric")
        return cleaned

    def zone_by_id(self) -> dict[str, ZoneDigest]:
        return {z.id: z for z in self.zones}

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=False)
