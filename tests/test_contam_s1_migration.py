"""S1 cross-zone link schema migration invariants.

The migration makes ``direction`` / ``mechanism`` / ``filtered`` explicit on
every ``cross_zone_links`` entry while keeping ``is_hvac_ducted`` as a
deprecated alias. These tests pin the operator-identical property: resolving
the migrated fields must give the same triple the legacy alias gave, and the
native decay-free transport operator must not move, except for links later
authored under the forced-exhaust fix plan.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from engines.py_contam_bridge import (
    ContamAirflowPath,
    ContamTransportEngine,
    cross_zone_link_semantics,
)
from engines.sim_clock import SimClock

REPO_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_ROOT = REPO_ROOT / "data" / "platforms"
FILTER_EFFICIENCY = 0.37

# Post-S1 galley authoring (CONTAM-FORCED-EXHAUST-GALLEY-01) intentionally moves
# these links away from the alias expansion; every other link remains pinned.
POST_S1_GALLEY_LINKS = {
    ("classic_cruise_1900", "Dining_Galley_Exhaust"),
    ("diamond_princess", "Dining_Galley_Exhaust"),
    ("expedition_cruise_450", "Dining_Galley_Exhaust"),
    ("greg_mortimer", "Dining_Galley_Exhaust"),
    ("spirit_cruise_3000", "Dining_Galley_Exhaust"),
    ("enterprise_constitution_tos", "Galley_Service_Exhaust"),
    ("enterprise_galaxy_tng", "Galley_Service_Exhaust"),
    ("san_antonio_class_lpd", "galley_exhaust_to_mess"),
}
POST_S1_GALLEY_OPERATOR_PLATFORMS = {
    platform for platform, _ in POST_S1_GALLEY_LINKS
}


def _platform_files() -> list[Path]:
    return sorted(PLATFORM_ROOT.glob("*/air_flow_paths.json"))


@pytest.fixture(scope="module")
def platforms() -> dict[str, dict[str, Any]]:
    bundles: dict[str, dict[str, Any]] = {}
    for path in _platform_files():
        name = path.parent.name
        bundles[name] = {
            "airflow": json.loads(path.read_text(encoding="utf-8")),
            "spatial": json.loads(
                (path.parent / "spatial_layout.json").read_text(encoding="utf-8"),
            ),
        }
    return bundles


def _expansion_direction(link: dict[str, Any]) -> str:
    return "oneway" if bool(link.get("is_hvac_ducted", False)) else "bidirectional"


def _legacy_link(link: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct the pre-S1 link used for the migration comparison.

    ``mechanism`` and ``filtered`` did not exist before S1. ``direction`` is
    dropped only when it equals the alias expansion: a differing direction is
    a pre-existing declaration (the D1 sanitary pins) that the migration must
    preserve.
    """
    legacy = {
        key: value
        for key, value in link.items()
        if key not in {"mechanism", "filtered"}
    }
    if legacy.get("direction") == _expansion_direction(link):
        legacy.pop("direction", None)
    return legacy


def _legacy_airflow(airflow: dict[str, Any]) -> dict[str, Any]:
    out = dict(airflow)
    out["cross_zone_links"] = [
        _legacy_link(link)
        for link in airflow.get("cross_zone_links", [])
    ]
    return out


class TestCrossZoneLinkSemantics:
    def test_alias_expansion_table(self) -> None:
        assert cross_zone_link_semantics({"is_hvac_ducted": True}) == {
            "direction": "oneway",
            "mechanism": "prescribed_flow",
            "filtered": True,
        }
        assert cross_zone_link_semantics({"is_hvac_ducted": False}) == {
            "direction": "bidirectional",
            "mechanism": "pressure_opening",
            "filtered": False,
        }
        assert cross_zone_link_semantics({}) == {
            "direction": "bidirectional",
            "mechanism": "pressure_opening",
            "filtered": False,
        }

    def test_explicit_fields_win_over_alias(self) -> None:
        sanitary = cross_zone_link_semantics({
            "is_hvac_ducted": False,
            "direction": "oneway",
        })
        assert sanitary == {
            "direction": "oneway",
            "mechanism": "pressure_opening",
            "filtered": False,
        }

        override = cross_zone_link_semantics({
            "is_hvac_ducted": True,
            "filtered": False,
        })
        assert override == {
            "direction": "oneway",
            "mechanism": "prescribed_flow",
            "filtered": False,
        }

    def test_path_filtered_defaults_to_ducted_alias(self) -> None:
        ducted = ContamAirflowPath("p", "A", "B", 1.0, is_hvac_ducted=True)
        assert ducted.filtered is True
        explicit = ContamAirflowPath(
            "p", "A", "B", 1.0, is_hvac_ducted=True, filtered=False,
        )
        assert explicit.filtered is False


class TestS1MigrationInvariants:
    def test_migrated_links_declare_resolved_triple(
        self, platforms: dict[str, dict[str, Any]],
    ) -> None:
        for name, bundle in platforms.items():
            for index, link in enumerate(
                bundle["airflow"].get("cross_zone_links", []),
            ):
                assert isinstance(link.get("is_hvac_ducted"), bool), (
                    f"{name}[{index}] lost the is_hvac_ducted alias"
                )
                assert link.get("direction") in {"oneway", "bidirectional"}, (
                    f"{name}[{index}] direction={link.get('direction')!r}"
                )
                assert link.get("mechanism") in {
                    "prescribed_flow", "pressure_opening",
                }, f"{name}[{index}] mechanism={link.get('mechanism')!r}"
                assert isinstance(link.get("filtered"), bool), (
                    f"{name}[{index}] filtered={link.get('filtered')!r}"
                )

    def test_resolved_semantics_match_pre_migration_alias(
        self, platforms: dict[str, dict[str, Any]],
    ) -> None:
        skipped = 0
        for name, bundle in platforms.items():
            for index, link in enumerate(
                bundle["airflow"].get("cross_zone_links", []),
            ):
                if (name, link.get("path")) in POST_S1_GALLEY_LINKS:
                    skipped += 1
                    continue
                migrated = cross_zone_link_semantics(link)
                legacy = cross_zone_link_semantics(_legacy_link(link))
                assert migrated == legacy, (
                    f"{name}[{index}] {link.get('path')!r}: "
                    f"migrated={migrated} legacy={legacy}"
                )
        assert skipped == len(POST_S1_GALLEY_LINKS)

    def test_decay_free_operator_is_migration_invariant(
        self, platforms: dict[str, dict[str, Any]],
    ) -> None:
        clock = SimClock(epoch_duration_hours=1.0, mode="hours")
        for name, bundle in platforms.items():
            if name in POST_S1_GALLEY_OPERATOR_PLATFORMS:
                continue
            spatial = bundle["spatial"]
            post = bundle["airflow"]
            pre = _legacy_airflow(post)
            pre_engine = ContamTransportEngine(
                spatial,
                pre,
                filter_efficiency=FILTER_EFFICIENCY,
                natural_decay_rate=0.0,
                clock=clock,
            )
            post_engine = ContamTransportEngine(
                spatial,
                post,
                filter_efficiency=FILTER_EFFICIENCY,
                natural_decay_rate=0.0,
                clock=clock,
            )
            pre_operator = pre_engine._build_decay_free_operator()
            post_operator = post_engine._build_decay_free_operator()
            assert pre_operator.shape == post_operator.shape, name
            if not np.array_equal(pre_operator, post_operator):
                diff = float(np.max(np.abs(pre_operator - post_operator)))
                pytest.fail(f"{name}: transport operator moved by {diff}")


class TestFilteredFieldTransport:
    @staticmethod
    def _engine(link: dict[str, Any]) -> ContamTransportEngine:
        layout = {
            "zones": [
                {"id": "A", "volume_m3": 100.0},
                {"id": "B", "volume_m3": 100.0},
            ],
        }
        airflow = {
            "hvac_zones": [],
            "cross_zone_links": [link],
            "adjacency": [],
        }
        return ContamTransportEngine(
            layout,
            airflow,
            filter_efficiency=0.5,
            natural_decay_rate=0.0,
        )

    def test_filtered_field_overrides_ducted_alias(self) -> None:
        base = {
            "from": "A",
            "to": "B",
            "flow_rate_m3h": 60.0,
            "is_hvac_ducted": False,
            "direction": "bidirectional",
        }
        unfiltered = self._engine({**base, "filtered": False})
        filtered = self._engine({**base, "filtered": True})

        unfiltered_op = unfiltered._build_decay_free_operator()
        filtered_op = filtered._build_decay_free_operator()
        row = filtered._real_zone_ids.index("B")
        column = filtered._real_zone_ids.index("A")

        assert unfiltered_op[row, column] > 0.0
        assert filtered_op[row, column] == pytest.approx(
            0.5 * unfiltered_op[row, column],
        )
