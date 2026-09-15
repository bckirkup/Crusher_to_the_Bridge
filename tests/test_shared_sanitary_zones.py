"""Tests for shared sanitary zones: layout wiring invariants and the
``transmission.sanitary_visit_mode`` mechanism.

Sensitivity-first per ci-test-design: visit counts must scale with the
served complement and with SANITARY_VOIDS_PER_DAY, head fomite dose must
scale with dwell share and inversely with the head's declared surface
area, and ``none`` must be exactly the absent-key baseline on paired
seeds. Platform goldens are limited to structural invariants that must
hold on every hull.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from derive_sanitary_provisioning import (  # noqa: E402
    SANITARY_ACH,
)
from engines.infection_dynamics_bridge import KorkinAgent  # noqa: E402
from engines.sim_clock import HOURS, SimClock  # noqa: E402
from engines.transmission_core import (  # noqa: E402
    SANITARY_CEILING_HEIGHT_M,
    SANITARY_DWELL_SECONDS,
    SANITARY_EXHAUST_M3H_PER_WC,
    SANITARY_FLOOR_AREA_M2_PER_WC,
    SANITARY_VOIDS_PER_DAY,
    TransmissionCore,
)

PLATFORMS_DIR = REPO_ROOT / "data" / "platforms"
PLATFORM_IDS = sorted(
    p.name
    for p in PLATFORMS_DIR.iterdir()
    if (p / "spatial_layout.json").exists()
)


def _load_platform(platform_id: str) -> tuple[dict, dict]:
    base = PLATFORMS_DIR / platform_id
    return (
        json.loads((base / "spatial_layout.json").read_text(encoding="utf-8")),
        json.loads((base / "air_flow_paths.json").read_text(encoding="utf-8")),
    )


def _make_core(
    *,
    mode: str | None = "dwell_weighted",
    serves: dict[str, dict[str, str]] | None = None,
    floor_areas: dict[str, float] | None = None,
    seed: int = 11,
) -> TransmissionCore:
    cfg = (
        {"transmission": {"sanitary_visit_mode": mode}}
        if mode is not None
        else {}
    )
    return TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={
            "TheaterLng": 4000.0, "PC_D5_P_F": 800.0,
            "HD_5T_M": 62.1, "HD_5T_F": 62.1, "HD_5T_M2": 124.2,
        },
        zone_types={
            "TheaterLng": "Free", "PC_D5_P_F": "Cabin_Corridor",
            "HD_5T_M": "Sanitary", "HD_5T_F": "Sanitary",
            "HD_5T_M2": "Sanitary",
        },
        zone_floor_areas=floor_areas or {
            "HD_5T_M": 27.0, "HD_5T_F": 27.0, "HD_5T_M2": 54.0,
        },
        sanitary_zone_map=(
            {"TheaterLng": {"male": "HD_5T_M", "female": "HD_5T_F"}}
            if serves is None else serves
        ),
        clock=SimClock(mode=HOURS),
        cfg=cfg,
    )


def _agent(aid: int, location: str, gender: str = "male") -> KorkinAgent:
    a = KorkinAgent(
        aid, "passenger", False, "PC_D5_P_F", "MainDining", "TheaterLng",
        "Casino", ["Free"] * 24, gender=gender,
    )
    a.current_location = location
    a.current_activity = "Sleep" if location == "PC_D5_P_F" else "Free"
    a.cabin_mate_ids = frozenset()
    return a


# ── Layout wiring invariants (every platform) ─────────────────────────


@pytest.mark.parametrize("platform_id", PLATFORM_IDS)
def test_sanitary_wiring_invariants(platform_id: str) -> None:
    spatial, airflow = _load_platform(platform_id)
    zones = spatial["zones"]
    zone_ids = {z["id"] for z in zones}
    heads = [z for z in zones if z["type"] == "Sanitary"]
    head_ids = {z["id"] for z in heads}
    if not heads:
        pytest.fail(f"{platform_id} has no Sanitary zones")

    # Every head carries the derived geometry and exhaust ACH = ratio.
    expected_ach = (
        SANITARY_EXHAUST_M3H_PER_WC
        / (SANITARY_FLOOR_AREA_M2_PER_WC * SANITARY_CEILING_HEIGHT_M)
    )
    for z in heads:
        assert z["base_ach"] == pytest.approx(expected_ach, abs=0.1)
        assert z["ceiling_height_m"] == pytest.approx(
            SANITARY_CEILING_HEIGHT_M,
        )
        assert z["volume_m3"] == pytest.approx(
            z["floor_area_m2"] * SANITARY_CEILING_HEIGHT_M, rel=1e-3,
        )
        assert all(s in zone_ids for s in z.get("serves", []))
    # Layout ACH equals the generator's single derived value.
    assert SANITARY_ACH == pytest.approx(expected_ach, abs=0.1)

    # Each head sits in exactly one exhaust-only HVAC group of one room.
    coverage: dict[str, int] = {}
    head_ahus = set()
    for group in airflow["hvac_zones"]:
        for room in group["rooms"]:
            coverage[room] = coverage.get(room, 0) + 1
        if group["id"].startswith("AHU_HD_"):
            head_ahus.add(group["id"])
            assert len(group["rooms"]) == 1
            assert group["rooms"][0] in head_ids
            assert group["ach"] == pytest.approx(expected_ach, abs=0.1)
            assert group["oa_fraction"] == pytest.approx(1.0)
            assert group.get("hvac_duty", 0.0) == pytest.approx(0.0)
    for zid in head_ids:
        assert coverage.get(zid) == 1, (platform_id, zid)
    assert len(head_ahus) == len(head_ids)

    # The one-way air rule: exactly one directional makeup link INTO each
    # head's group and NOTHING out — no reverse cross link, no adjacency.
    into = set()
    for link in airflow.get("cross_zone_links", []):
        if "AHU_HD_" in link["from"]:
            pytest.fail(f"head AHU is a link source: {platform_id} {link}")
        if link["to"].startswith("AHU_HD_"):
            into.add(link["to"])
            assert link["path"] == "Sanitary_Makeup"
            assert link["is_hvac_ducted"] is False
    assert into == head_ahus
    for edge in airflow.get("adjacency", []):
        assert edge["from"] not in head_ids
        assert edge["to"] not in head_ids

    # Heads are not a graywater collection point.
    assert not head_ids & set(spatial.get("graywater_zones", []))


def test_sanitary_provisioning_counts() -> None:
    """Change-detector: the signed-off per-hull head counts."""
    expected = {
        "classic_cruise_1900": 17,      # 16 cluster heads + 1 bridge head
        "spirit_cruise_3000": 28,
        "expedition_cruise_450": 13,
        "expedition_cruise_300": 11,
        "mega_cruise_5000": 63,
        "messy_cruise_500": 63,
        "enterprise_constitution_tos": 19,
        "enterprise_galaxy_tng": 37,
        "destroyer_baseline": 3,
        "fletcher_class_destroyer": 13,
        "legend_class_nsc": 9,
        "san_antonio_class_lpd": 7,
    }
    for platform_id, count in expected.items():
        spatial, _ = _load_platform(platform_id)
        heads = [
            z for z in spatial["zones"] if z["type"] == "Sanitary"
        ]
        assert len(heads) == count, platform_id


# ── Visit mechanism ───────────────────────────────────────────────────


def test_none_mode_bit_identical_on_paired_seeds() -> None:
    """``none`` and the absent key are the same engine on the same seed."""
    def draws(mode: str | None) -> list[float]:
        core = _make_core(mode=mode, seed=99)
        return [float(core.rng.random()) for _ in range(10)]

    assert draws(None) == draws("none")
    absent = _make_core(mode=None, seed=99)
    explicit = _make_core(mode="none", seed=99)
    assert absent._sanitary_visits_rng is None
    assert explicit._sanitary_visits_rng is None
    assert absent.sanitary_visit_mode == "none"


def test_dwell_weighted_has_own_stream() -> None:
    """Spawning the visit stream does not perturb the shared stream."""
    armed = _make_core(mode="dwell_weighted", seed=99)
    inert = _make_core(mode="none", seed=99)
    assert armed._sanitary_visits_rng is not None
    assert inert._sanitary_visits_rng is None
    for _ in range(10):
        assert float(armed.rng.random()) == float(inert.rng.random())


def test_visit_counts_scale_with_complement_and_rate() -> None:
    """Mean visits/epoch ≈ VOIDS_PER_DAY x day_fraction at occupancy."""
    core = _make_core(seed=5)
    n_agents = 400
    occupants = [_agent(i, "TheaterLng") for i in range(n_agents)]
    occ = {"TheaterLng": occupants}
    total = 0
    epochs = 24
    for e in range(epochs):
        visits = core._draw_sanitary_visits(e, occ)
        total += sum(len(v) for v in visits.values())
    expected = (
        n_agents * epochs
        * SANITARY_VOIDS_PER_DAY * core.clock.day_fraction_per_epoch
    )
    # Poisson mean: graded sensitivity, not a golden.
    assert total == pytest.approx(expected, rel=0.08)

    # Halving the complement halves the visit count on the same seed.
    core_half = _make_core(seed=5)
    half = 0
    for e in range(epochs):
        visits = core_half._draw_sanitary_visits(
            e, {"TheaterLng": occupants[: n_agents // 2]},
        )
        half += sum(len(v) for v in visits.values())
    assert half == pytest.approx(total / 2, rel=0.15)


def test_home_visits_are_own_fittings_telemetry_only() -> None:
    core = _make_core(seed=3)
    home = _agent(1, "PC_D5_P_F")
    visits = {}
    for e in range(72):
        drawn = core._draw_sanitary_visits(e, {"PC_D5_P_F": [home]})
        visits.update(drawn)
    # Sleeping-at-home visits resolve to the cabin compartment, which is
    # covered by whole-epoch occupancy and must not re-enter exposure.
    assert 1 not in visits
    assert core.sanitary_telemetry["visits"] > 0


def test_head_fomite_area_is_fixture_hardware_not_footprint() -> None:
    """Touchable surface scales with water closets, not floor area."""
    core = _make_core(seed=7)
    # 27 m2 = 10 WC -> 5.0 m2; 54 m2 = 20 WC -> 10.0 m2; a single-fixture
    # head (2.7 m2) -> 0.5 m2, below a stateroom's 1.5 m2.
    core.zone_floor_areas["HD_1W_M"] = SANITARY_FLOOR_AREA_M2_PER_WC
    core.zone_types["HD_1W_M"] = "Sanitary"
    assert core._fomite_surface_area("HD_5T_M") == pytest.approx(5.0)
    assert core._fomite_surface_area("HD_5T_M2") == pytest.approx(10.0)
    assert core._fomite_surface_area("HD_1W_M") == pytest.approx(0.5)
    # No declared floor area -> the single-fixture whole-zone fallback.
    core.zone_floor_areas.pop("HD_5T_M")
    assert core._fomite_surface_area("HD_5T_M") == pytest.approx(0.5)
    # The deck-plan footprint never enters the transfer area: doubling
    # floor area per fixture does not double the touchable surface.
    core.zone_floor_areas["HD_1W_M"] = 2 * SANITARY_FLOOR_AREA_M2_PER_WC
    assert core._fomite_surface_area("HD_1W_M") == pytest.approx(1.0)


def test_head_fomite_dose_scales_inversely_with_surface_area() -> None:
    """Same contaminated mass in a bigger head -> lower delivered dose."""
    def delivered(area: float) -> float:
        core = _make_core(
            seed=7,
            floor_areas={"HD_5T_M": area, "HD_5T_F": 27.0, "HD_5T_M2": 54.0},
        )
        core.surface_pools["HD_5T_M"] = 1000.0
        visitor = _agent(1, "TheaterLng")
        # Force one visit: draw until the agent has at least one.
        for e in range(4):
            drawn = core._draw_sanitary_visits(e, {"TheaterLng": [visitor]})
            if drawn.get(1):
                break
        drawn = {1: ["HD_5T_M"]}
        core._sanitary_visits = drawn
        request = core._fomite_pickup_request(
            visitor, "HD_5T_M", core.surface_pools["HD_5T_M"], 0,
        )
        share = SANITARY_DWELL_SECONDS / 3600.0
        return request * share

    # Pool request itself already carries the 1/area dependence; the
    # dwell share is a pure multiplier, so the ratio is exact, not
    # statistical: it follows the pickup formula's surface-area term.
    small = delivered(27.0)
    large = delivered(54.0)
    assert large == pytest.approx(small / 2, rel=1e-6)


def test_exposure_share_is_dwell_over_epoch() -> None:
    """A 155 s visit to an hourly epoch is ~4.3% exposure."""
    share = SANITARY_DWELL_SECONDS / 3600.0
    assert share == pytest.approx(0.043, rel=0.01)


def test_sanitary_constants_are_the_derived_ratio() -> None:
    """Head ACH is derived, not a second hardcoded copy."""
    assert (
        SANITARY_EXHAUST_M3H_PER_WC
        / (SANITARY_FLOOR_AREA_M2_PER_WC * SANITARY_CEILING_HEIGHT_M)
    ) == pytest.approx(19.15, abs=0.01)


def test_unserved_zone_visits_are_unresolved() -> None:
    core = _make_core(serves={})  # no head serves TheaterLng
    visitor = _agent(1, "TheaterLng")
    for e in range(72):
        core._draw_sanitary_visits(e, {"TheaterLng": [visitor]})
    assert core._sanitary_visits.get(1) is None
    assert core.sanitary_telemetry["unresolved"] > 0
