"""PRJ config fixes v2 — zone ≤15, per-AHU OA, deck temps, passive orifices."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from simulation_utils.paths import (  # noqa: E402
    resolve_repo_path,
    validate_path_component,
    validated_open,
)
from tools.contam_hobbyist import deck_temp_k  # noqa: E402
from tools.contamw34_prj import (  # noqa: E402
    _abbreviate_for_contam,
    _orifice_area_m2_for_flow_m3h,
    _unique_contam_name,
    export_contamw34,
)

_CONTAM_PLATFORMS = (
    "destroyer_baseline",
    "enterprise_constitution_tos",
    "enterprise_galaxy_tng",
    "mega_cruise_5000",
)
_REPO = str(REPO_ROOT)


def _read_json_under_repo(rel_path: str) -> dict | list:
    """Load JSON via Sonar-safe containment-checked open."""
    full = resolve_repo_path(_REPO, rel_path)
    with validated_open(full, "r", allowed_roots=(_REPO,), encoding="utf-8") as fh:
        return json.load(fh)


def _load_platform(platform: str) -> tuple[dict, dict, dict]:
    plat = validate_path_component(platform, label="platform id")
    base = f"data/platforms/{plat}"
    spatial = _read_json_under_repo(f"{base}/spatial_layout.json")
    airflow = _read_json_under_repo(f"{base}/air_flow_paths.json")
    overrides_rel = f"{base}/contam/hobbyist_overrides.json"
    overrides_path = Path(resolve_repo_path(_REPO, overrides_rel))
    overrides = (
        _read_json_under_repo(overrides_rel) if overrides_path.is_file() else {}
    )
    return spatial, airflow, overrides  # type: ignore[return-value]


def _parse_elem_symbols(prj_text: str) -> dict[int, str]:
    """Map Contam element nr → plr_orfc | fan_cvf."""
    symbols: dict[int, str] = {}
    in_el = False
    for line in prj_text.splitlines():
        if "! flow elements:" in line:
            in_el = True
            continue
        if not in_el:
            continue
        if line.strip() == "-999":
            break
        if "plr_orfc" in line:
            symbols[int(line.split()[0])] = "plr_orfc"
        elif "fan_cvf" in line:
            symbols[int(line.split()[0])] = "fan_cvf"
    return symbols


def _parse_path_elements(prj_text: str) -> dict[int, int]:
    """Map Contam path nr → element nr (field index 4)."""
    path_elem: dict[int, int] = {}
    in_paths = False
    for line in prj_text.splitlines():
        if "! flow paths:" in line:
            in_paths = True
            continue
        if not in_paths:
            continue
        if line.strip() == "-999":
            break
        if line.strip().startswith("!"):
            continue
        toks = line.split()
        if len(toks) >= 5 and toks[0].isdigit():
            path_elem[int(toks[0])] = int(toks[4])
    return path_elem


@pytest.mark.parametrize("platform", _CONTAM_PLATFORMS)
def test_contam_platform_zone_ids_fit_contam_name_limit(platform: str) -> None:
    spatial, _, _ = _load_platform(platform)
    long = [z["id"] for z in spatial["zones"] if len(z["id"]) > 15]
    assert long == [], f"{platform} zone IDs >15 chars: {long}"


def test_abbreviate_for_contam_prefers_word_shorts() -> None:
    assert len(_abbreviate_for_contam("Stellar_Cartography_Extra")) <= 15
    used: set[str] = set()
    a = _unique_contam_name("Main_Engineering_Bay_Alpha", used)
    assert len(a) <= 15
    assert "Eng" in a or a.startswith("Main")


def test_mega_engine_deck_temps_match_overrides() -> None:
    spatial, airflow, overrides = _load_platform("mega_cruise_5000")
    by_id = {z["id"]: z for z in spatial["zones"]}
    assert deck_temp_k(by_id["Engine_Room_Aft"]["deck"], overrides) == pytest.approx(
        298.15
    )
    assert deck_temp_k(by_id["EngControl"]["deck"], overrides) == pytest.approx(297.15)
    text, _ = export_contamw34(
        spatial, airflow, hobbyist=True, overrides=overrides,
    )
    assert "298.15 0 Engine_Room_Aft" in text
    assert "297.15 0 EngControl" in text


def test_per_ahu_oa_schedules_emitted_for_overrides() -> None:
    spatial, airflow, overrides = _load_platform("mega_cruise_5000")
    text, _ = export_contamw34(
        spatial, airflow, hobbyist=True, overrides=overrides,
    )
    assert "OAFr_15" in text or "OAFr15" in text
    assert "OAFr_40" in text or "OAFr40" in text
    assert "OAFracW" in text


def test_passive_cross_zone_uses_orifice_not_fan() -> None:
    spatial, airflow, overrides = _load_platform("destroyer_baseline")
    text, path_map = export_contamw34(
        spatial, airflow, hobbyist=True, overrides=overrides,
    )
    elem_symbol = _parse_elem_symbols(text)
    path_elem = _parse_path_elements(text)

    ladder_entries = [
        e for e in path_map
        if str(e.get("kind", "")).startswith("ladder_well_")
    ]
    assert ladder_entries
    for entry in ladder_entries:
        assert elem_symbol[path_elem[int(entry["path_nr"])]] == "plr_orfc"

    ducted = [e for e in path_map if e.get("kind") == "ventilation_shaft_aft"]
    assert ducted
    for entry in ducted:
        assert elem_symbol[path_elem[int(entry["path_nr"])]] == "fan_cvf"


def test_orifice_area_scales_with_design_flow() -> None:
    a20 = _orifice_area_m2_for_flow_m3h(20.0)
    a80 = _orifice_area_m2_for_flow_m3h(80.0)
    assert a80 == pytest.approx(4.0 * a20, rel=1e-9)
    a50 = _orifice_area_m2_for_flow_m3h(50.0, density=1.2)
    assert a50 == pytest.approx(0.01793, rel=0.02)
    assert math.isfinite(a50)
