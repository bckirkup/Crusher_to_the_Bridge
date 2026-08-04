"""Pydantic models for the ShipDigest intermediate representation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ZoneType = Literal["Free", "Dining", "Room", "Medical", "Engineering"]
TrafficLevel = Literal["low", "medium", "high"]
OpeningStatus = Literal["draft", "confirmed", "engineer_review"]


class DeckInfo(BaseModel):
    id: str
    page: int = Field(ge=1)
    role: str = ""
    elevation_m: float | None = Field(
        default=None,
        description="Relative Contam level elevation (m); auto-stacked if omitted",
    )


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
