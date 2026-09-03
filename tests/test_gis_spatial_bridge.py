"""Graded sensitivity + bounds tests for tools.gis_spatial_bridge helpers.

Covers in-memory GeoDataFrame paths for polygon→zones, polygon adjacency,
and line→edge tracing without reading shapefiles from disk.
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Point, Polygon

from tools.gis_spatial_bridge import (
    _compute_polygon_adjacency,
    _lines_to_edges,
    _polygons_to_zones,
    convert,
    emit_deck_graphics,
)


def _square(xmin: float, ymin: float, size: float = 10.0) -> Polygon:
    return Polygon(
        [
            (xmin, ymin),
            (xmin + size, ymin),
            (xmin + size, ymin + size),
            (xmin, ymin + size),
        ]
    )


def _poly_gdf(rows: list[dict]) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(rows, geometry="geometry")


class TestPolygonsToZones:
    """Attribute columns grade zone fields; invalid geoms are skipped."""

    def test_volume_and_defaults_grade(self) -> None:
        volumes = (50.0, 150.0, 400.0)
        zones_by_vol: list[list[dict]] = []
        for vol in volumes:
            gdf = _poly_gdf(
                [
                    {
                        "ROOM_NAME": "Alpha Room",
                        "ROOM_TYPE": "Cabin",
                        "VOLUME_M3": vol,
                        "BASE_ACH": 8.0,
                        "DECK": "Upper",
                        "TRAFFIC": "HIGH",
                        "geometry": _square(0, 0),
                    },
                    {
                        "ROOM_NAME": "skip_point",
                        "geometry": Point(1, 1),  # non-polygon → skipped
                    },
                    {
                        "ROOM_NAME": "skip_empty",
                        "geometry": Polygon(),  # empty → skipped
                    },
                ]
            )
            zones_by_vol.append(
                _polygons_to_zones(gdf, None, None, None, None, None, None)
            )

        volumes_out = [z[0]["volume_m3"] for z in zones_by_vol]
        assert volumes_out == sorted(volumes_out)
        assert volumes_out[-1] - volumes_out[0] > 100.0
        for zones in zones_by_vol:
            assert len(zones) == 1
            z = zones[0]
            assert z["id"] == "Alpha_Room"
            assert z["type"] == "Cabin"
            assert z["traffic"] == "high"
            assert z["deck"] == "upper"
            assert z["base_ach"] == pytest.approx(8.0)
            assert z["volume_m3"] > 0
            assert "display" in z
            assert z["display"]["x"] == pytest.approx(5.0)
            assert z["display"]["y"] == pytest.approx(5.0)

    def test_missing_columns_use_defaults(self) -> None:
        gdf = _poly_gdf([{"geometry": _square(10, 20)}])
        zones = _polygons_to_zones(gdf, None, None, None, None, None, None)
        assert len(zones) == 1
        z = zones[0]
        assert z["id"].startswith("Zone_")
        assert z["type"] == "Free"
        assert z["traffic"] == "medium"
        assert z["volume_m3"] == pytest.approx(100.0)
        assert z["deck"] == "main"
        assert "base_ach" not in z

    def test_multipolygon_accepted(self) -> None:
        multi = MultiPolygon([_square(0, 0, 5), _square(20, 0, 5)])
        gdf = _poly_gdf([{"NAME": "Combo", "geometry": multi}])
        zones = _polygons_to_zones(gdf, None, None, None, None, None, None)
        assert len(zones) == 1
        assert zones[0]["id"] == "Combo"
        assert isinstance(zones[0]["display"]["x"], float)


class TestPolygonAdjacency:
    """Touching polygons produce passageway edges; disjoint do not."""

    def test_touching_vs_disjoint_grades_edge_count(self) -> None:
        touching = _poly_gdf(
            [
                {"geometry": _square(0, 0)},
                {"geometry": _square(10, 0)},  # shares edge at x=10
                {"geometry": _square(100, 100)},  # isolated
            ]
        )
        zone_ids = ["A", "B", "C"]
        adj = _compute_polygon_adjacency(touching, zone_ids)
        assert len(adj) == 1
        assert adj[0] == {"from": "A", "to": "B", "type": "passageway"}

        gaps = _poly_gdf(
            [
                {"geometry": _square(0, 0)},
                {"geometry": _square(50, 0)},
                {"geometry": _square(100, 0)},
            ]
        )
        adj_gap = _compute_polygon_adjacency(gaps, zone_ids)
        assert adj_gap == []

    def test_skips_empty_and_dedupes(self) -> None:
        gdf = _poly_gdf(
            [
                {"geometry": _square(0, 0)},
                {"geometry": Polygon()},
                {"geometry": _square(10, 0)},
            ]
        )
        # zone_ids aligned to rows; empty geom row still occupies an index
        adj = _compute_polygon_adjacency(gdf, ["Z0", "Z1", "Z2"])
        assert len(adj) == 1
        assert adj[0]["from"] == "Z0"
        assert adj[0]["to"] == "Z2"


class TestLinesToEdges:
    """Flow rate and ducted flag grade HVAC edges; malformed flow keeps default."""

    def _rooms(self) -> gpd.GeoDataFrame:
        return _poly_gdf(
            [
                {"geometry": _square(0, 0)},
                {"geometry": _square(20, 0)},
            ]
        )

    def test_flow_rate_grades_and_ducted_types(self) -> None:
        poly = self._rooms()
        zone_ids = ["Room_A", "Room_B"]
        flows = (10.0, 50.0, 200.0)
        rates: list[float] = []
        for flow in flows:
            lines = _poly_gdf(
                [
                    {
                        "FLOW_RATE": flow,
                        "IS_DUCTED": "yes",
                        "geometry": LineString([(5, 5), (25, 5)]),
                    }
                ]
            )
            links, adj = _lines_to_edges(lines, poly, zone_ids)
            assert len(links) == 1
            assert len(adj) == 1
            rates.append(links[0]["flow_rate_m3h"])
            assert links[0]["is_hvac_ducted"] is True
            assert adj[0]["type"] == "hvac_duct"
            assert links[0]["from"] == "Room_A"
            assert links[0]["to"] == "Room_B"
            assert links[0]["path"] == "Room_A_to_Room_B"

        assert rates == sorted(rates)
        assert rates[-1] - rates[0] > 50.0

    def test_malformed_flow_keeps_default_and_passageway(self) -> None:
        poly = self._rooms()
        lines = _poly_gdf(
            [
                {
                    "FLOW_RATE": "not-a-number",
                    "IS_DUCTED": 0,
                    "geometry": LineString([(5, 5), (25, 5)]),
                },
                {"geometry": Point(0, 0)},  # skipped
                {"geometry": LineString()},  # empty skipped
            ]
        )
        links, adj = _lines_to_edges(lines, poly, ["Room_A", "Room_B"])
        assert len(links) == 1
        assert links[0]["flow_rate_m3h"] == pytest.approx(50.0)
        assert links[0]["is_hvac_ducted"] is False
        assert adj[0]["type"] == "passageway"

    def test_multiline_connects_rooms(self) -> None:
        poly = self._rooms()
        multi = MultiLineString(
            [LineString([(5, 5), (25, 5)]), LineString([(100, 100), (110, 110)])]
        )
        lines = _poly_gdf([{"geometry": multi}])
        links, adj = _lines_to_edges(lines, poly, ["Room_A", "Room_B"])
        assert len(links) >= 1
        assert all(link["flow_rate_m3h"] > 0 for link in links)
        assert all(a["type"] in ("passageway", "hvac_duct") for a in adj)


class TestConvertAndDeckGraphics:
    """End-to-end convert / emit_deck_graphics write valid JSON under a sandboxed root."""

    def test_convert_polygon_only_writes_layout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import tools.gis_spatial_bridge as gis

        monkeypatch.setattr(gis, "REPO_ROOT", str(tmp_path))
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "ROOM_NAME": "Bridge",
                        "ROOM_TYPE": "Work",
                        "VOLUME_M3": 80,
                        "DECK": "main",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
                        ],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"ROOM_NAME": "Mess", "VOLUME_M3": 120},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[10, 0], [20, 0], [20, 10], [10, 10], [10, 0]]
                        ],
                    },
                },
            ],
        }
        inp = tmp_path / "deck.geojson"
        inp.write_text(json.dumps(geojson), encoding="utf-8")
        out_dir = tmp_path / "platform_out"
        spatial_path, airflow_path = convert(
            str(inp),
            str(out_dir),
            platform_name="test_platform",
        )
        spatial = json.loads(Path(spatial_path).read_text(encoding="utf-8"))
        airflow = json.loads(Path(airflow_path).read_text(encoding="utf-8"))
        assert spatial["platform"] == "test_platform"
        assert len(spatial["zones"]) == 2
        assert all(z["volume_m3"] > 0 for z in spatial["zones"])
        assert len(airflow["adjacency"]) >= 1
        assert len(airflow["hvac_zones"]) >= 1

    def test_convert_with_line_layer_builds_cross_zone_links(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import tools.gis_spatial_bridge as gis

        monkeypatch.setattr(gis, "REPO_ROOT", str(tmp_path))
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"ROOM_NAME": "A", "VOLUME_M3": 40},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
                        ],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"ROOM_NAME": "B", "VOLUME_M3": 40},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[20, 0], [30, 0], [30, 10], [20, 10], [20, 0]]
                        ],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"FLOW_RATE": 75, "IS_DUCTED": True},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[5, 5], [25, 5]],
                    },
                },
            ],
        }
        inp = tmp_path / "with_ducts.geojson"
        inp.write_text(json.dumps(geojson), encoding="utf-8")
        spatial_path, airflow_path = convert(str(inp), str(tmp_path / "out"))
        airflow = json.loads(Path(airflow_path).read_text(encoding="utf-8"))
        assert len(airflow["cross_zone_links"]) >= 1
        assert airflow["cross_zone_links"][0]["flow_rate_m3h"] == pytest.approx(75.0)
        assert Path(spatial_path).is_file()

    def test_emit_deck_graphics_includes_hull(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import tools.gis_spatial_bridge as gis

        monkeypatch.setattr(gis, "REPO_ROOT", str(tmp_path))
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"ROOM_NAME": "A", "DECK": "main", "TYPE": "Free"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]
                        ],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[1, 1], [4, 4]],
                    },
                },
            ],
        }
        inp = tmp_path / "gfx_in.geojson"
        inp.write_text(json.dumps(geojson), encoding="utf-8")
        out = tmp_path / "deck_graphics.geojson"
        path = emit_deck_graphics(str(inp), str(out), platform_id="gfx_ship")
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        kinds = {f["properties"]["kind"] for f in data["features"]}
        assert "hull_outline" in kinds
        assert "compartment" in kinds
        assert "hvac_path" in kinds
        assert data["type"] == "FeatureCollection"
