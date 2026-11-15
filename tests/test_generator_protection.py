"""Committed-platform generator overwrite guards and shared link contract."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from cruise_platform_recipes import RECIPES  # noqa: E402
from derive_sanitary_provisioning import (  # noqa: E402
    sanitary_airflow_augment,
    sanitary_makeup_link,
)

SANITARY_LINK_KEYS = {
    "from",
    "to",
    "flow_rate_m3h",
    "is_hvac_ducted",
    "path",
    "direction",
    "mechanism",
    "filtered",
    "description",
}


def _recipe(platform_id: str):
    return replace(RECIPES["expedition_cruise_450"], platform_id=platform_id)


def _oneway_sanitary_makeup_links(links: list[dict]) -> list[dict]:
    return [
        link
        for link in links
        if link.get("path") == "Sanitary_Makeup"
        and link.get("direction") == "oneway"
    ]


def test_cruise_writer_refuses_existing_platform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import generate_cruise_platform_layout as cruise

    monkeypatch.setattr(cruise, "REPO", str(tmp_path))
    out_dir = tmp_path / "data" / "platforms" / "guarded_hull"
    out_dir.mkdir(parents=True)
    sentinel = out_dir / "air_flow_paths.json"
    sentinel.write_text('{"sentinel": true}\n', encoding="utf-8")

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        cruise.write_platform(_recipe("guarded_hull"))

    assert sentinel.read_text(encoding="utf-8") == '{"sentinel": true}\n'
    assert not (out_dir / "spatial_layout.json").exists()


def test_cruise_writer_creates_new_platform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import generate_cruise_platform_layout as cruise

    monkeypatch.setattr(cruise, "REPO", str(tmp_path))
    cruise.write_platform(_recipe("fresh_guard_hull"))

    out_dir = tmp_path / "data" / "platforms" / "fresh_guard_hull"
    spatial = json.loads((out_dir / "spatial_layout.json").read_text(encoding="utf-8"))
    airflow = json.loads((out_dir / "air_flow_paths.json").read_text(encoding="utf-8"))
    assert spatial["platform"] == "fresh_guard_hull"
    assert airflow["platform"] == "fresh_guard_hull"
    assert _oneway_sanitary_makeup_links(airflow["cross_zone_links"])


def test_cruise_writer_allows_empty_platform_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import generate_cruise_platform_layout as cruise

    monkeypatch.setattr(cruise, "REPO", str(tmp_path))
    out_dir = tmp_path / "data" / "platforms" / "empty_bootstrap_hull"
    out_dir.mkdir(parents=True)

    cruise.write_platform(_recipe("empty_bootstrap_hull"))

    assert (out_dir / "spatial_layout.json").is_file()
    assert (out_dir / "air_flow_paths.json").is_file()


def test_cruise_writer_overwrite_flag_replaces_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import generate_cruise_platform_layout as cruise

    monkeypatch.setattr(cruise, "REPO", str(tmp_path))
    out_dir = tmp_path / "data" / "platforms" / "overwrite_hull"
    out_dir.mkdir(parents=True)
    (out_dir / "spatial_layout.json").write_text("{}\n", encoding="utf-8")

    cruise.write_platform(_recipe("overwrite_hull"), overwrite=True)

    spatial = json.loads((out_dir / "spatial_layout.json").read_text(encoding="utf-8"))
    assert spatial["platform"] == "overwrite_hull"


def test_enterprise_cli_refuses_existing_platform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import generate_cruise_platform_layout as cruise
    import generate_enterprise_platform_layout as enterprise

    monkeypatch.setattr(cruise, "REPO", str(tmp_path))
    pid = "enterprise_constitution_tos"
    out_dir = tmp_path / "data" / "platforms" / pid
    out_dir.mkdir(parents=True)
    sentinel = out_dir / "spatial_layout.json"
    sentinel.write_text('{"sentinel": true}\n', encoding="utf-8")

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        enterprise.main(["--platform", pid])
    assert sentinel.read_text(encoding="utf-8") == '{"sentinel": true}\n'

    enterprise.main(["--platform", pid, "--overwrite"])
    spatial = json.loads(sentinel.read_text(encoding="utf-8"))
    assert spatial["platform"] == pid


def test_mega_writer_refuses_existing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import generate_mega_cruise_cabin_layout as mega

    out_dir = tmp_path / "mega_cruise_5000"
    out_dir.mkdir()
    sentinel = out_dir / "spatial_layout.json"
    sentinel.write_text('{"sentinel": true}\n', encoding="utf-8")
    monkeypatch.setattr(mega, "OUT_DIR", str(out_dir))

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        mega.main([])

    assert sentinel.read_text(encoding="utf-8") == '{"sentinel": true}\n'
    assert not (out_dir / "air_flow_paths.json").exists()


def test_mega_writer_creates_new_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import generate_mega_cruise_cabin_layout as mega

    out_dir = tmp_path / "mega_cruise_5000"
    monkeypatch.setattr(mega, "OUT_DIR", str(out_dir))

    assert mega.main([]) == 0

    spatial = json.loads((out_dir / "spatial_layout.json").read_text(encoding="utf-8"))
    airflow = json.loads((out_dir / "air_flow_paths.json").read_text(encoding="utf-8"))
    assert spatial["platform"] == "mega_cruise_5000"
    assert airflow["platform"] == "mega_cruise_5000"
    assert _oneway_sanitary_makeup_links(airflow["cross_zone_links"])


def test_legacy_enterprise_builder_refuses_existing_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import build_enterprise_platforms as legacy

    monkeypatch.setattr(legacy, "DATA", str(tmp_path))
    sentinel = tmp_path / "pathogens" / "enterprise_tos_profiles.json"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text('{"sentinel": true}\n', encoding="utf-8")

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        legacy.main([])

    assert sentinel.read_text(encoding="utf-8") == '{"sentinel": true}\n'
    assert not (
        tmp_path / "platforms" / "enterprise_constitution_tos"
        / "spatial_layout.json"
    ).exists()


def test_legacy_enterprise_builder_writes_empty_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import build_enterprise_platforms as legacy

    monkeypatch.setattr(legacy, "DATA", str(tmp_path))

    assert legacy.main([]) == 0

    for path in legacy._output_paths():
        assert Path(path).is_file()


def test_sanitary_makeup_link_contract_is_shared() -> None:
    from tools.ship_blueprint_import.synthesize import (
        SANITARY_EXHAUST_M3H_PER_WC,
        _head_makeup_links,
    )

    zones = [
        {
            "id": "Mess_Main",
            "type": "Dining",
            "traffic": "high",
            "volume_m3": 120.0,
            "deck": "1_Main",
            "max_occupancy": 50,
            "display": {"x": 0.0, "y": 0.0},
        }
    ]
    recipe_airflow = {
        "hvac_zones": [{"id": "AHU_Main", "rooms": ["Mess_Main"], "ach": 6.0}],
        "cross_zone_links": [],
    }
    recipe_out = sanitary_airflow_augment(zones, recipe_airflow)
    recipe_links = [
        link
        for link in recipe_out["cross_zone_links"]
        if link.get("path") == "Sanitary_Makeup"
    ]
    assert recipe_links

    ga_links = _head_makeup_links(
        ["Head_Main"],
        [
            {
                "id": "Head_Main",
                "type": "Sanitary",
                "deck": "1_Main",
                "serves": ["Mess_Main"],
                "floor_area_m2": 5.4,
            }
        ],
        [{"id": "AHU_Main", "rooms": ["Mess_Main"]}],
    )
    assert len(ga_links) == 1

    direct = sanitary_makeup_link(
        source="AHU_Main",
        target_ahu_id="AHU_HD_Head_Main",
        head_zone_id="Head_Main",
        flow_rate_m3h=2 * SANITARY_EXHAUST_M3H_PER_WC,
    )

    for link in [*recipe_links, ga_links[0], direct]:
        assert set(link) == SANITARY_LINK_KEYS
        assert link["path"] == "Sanitary_Makeup"
        assert link["direction"] == "oneway"
        assert link["mechanism"] == "pressure_opening"
        assert link["filtered"] is False
        assert link["is_hvac_ducted"] is False
    assert ga_links[0] == direct
