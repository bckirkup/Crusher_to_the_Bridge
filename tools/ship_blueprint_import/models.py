"""Pydantic models for the ShipDigest intermediate representation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ZoneType = Literal["Free", "Dining", "Room", "Medical", "Engineering"]
TrafficLevel = Literal["low", "medium", "high"]


class DeckInfo(BaseModel):
    id: str
    page: int = Field(ge=1)
    role: str = ""


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
    description: str = ""


class AdjacencyHint(BaseModel):
    model_config = {"populate_by_name": True}

    from_: str = Field(alias="from")
    to: str
    type: str = "passageway"


class CrossZoneHint(BaseModel):
    model_config = {"populate_by_name": True}

    from_: str = Field(alias="from")
    to: str
    flow_rate_m3h: float = Field(default=50.0, ge=0)
    path: str = "ladder_well"
    is_hvac_ducted: bool = False
    description: str = ""


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
    cross_zone_hints: list[CrossZoneHint] = Field(default_factory=list)
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
