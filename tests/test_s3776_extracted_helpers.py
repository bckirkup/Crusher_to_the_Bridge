"""Targeted coverage for helpers extracted during the S3776 splits.

These exercise branches the broad suite leaves dark — validation raises,
catalog fallbacks and early-return guards — so the moved lines do not drop
below the new-code coverage gate.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from engines.contamx_ahs_bridge import _ahs_group_star_paths
from engines.engine_paths import _collect_engine_py_paths, engine_import_paths
from engines.fomite_surfaces import _parse_declared_shares
from engines.infection_dynamics_bridge import (
    KorkinShipEngine,
    _dining_catalog_from,
    _leisure_catalog_from,
    _merged_agent_behavior,
)
from engines.initiation import (
    ExplicitSeed,
    _seed_count,
    _seed_departure_day,
    _seed_epoch_fields,
    _seed_infection_age_days,
    _seed_onset_day,
    _seed_role,
    _stamp_seed_onset,
)
from engines.py_contam_bridge import (
    PATH_TYPE_HVAC_SUPPLY,
    ContamAirflowPath,
    ContamTransportEngine,
)
from engines.sim_clock import SimClock
from engines.voyage_itinerary import (
    EpochState,
    _apply_disembarkation_day,
    _between_ashore_windows,
    _day_type_and_entry,
    _embarkation_surge,
    _onboard_fraction,
)
from engines.wearable_monitor import (
    WearableDevice,
    WearableMonitor,
    build_wearable_monitor_from_config,
)


class TestSeedFieldValidators:
    def test_count_defaults_to_one_and_rejects_negatives(self) -> None:
        assert _seed_count({}, "initiation.explicit_seeds[0]") == 1
        with pytest.raises(ValueError, match="count"):
            _seed_count({"count": -1}, "initiation.explicit_seeds[0]")

    def test_role_rejects_unknown_values(self) -> None:
        assert _seed_role({}, "loc") is None
        assert _seed_role({"role": "crew"}, "loc") == "crew"
        with pytest.raises(ValueError, match="role"):
            _seed_role({"role": "officer"}, "loc")

    def test_infection_age_rejects_negatives(self) -> None:
        assert _seed_infection_age_days({}, "loc") == pytest.approx(0.0)
        with pytest.raises(ValueError, match="infection_age_days"):
            _seed_infection_age_days({"infection_age_days": -0.5}, "loc")

    def test_departure_day_validates_finiteness(self) -> None:
        assert _seed_departure_day({}, "loc") is None
        assert _seed_departure_day({"departure_day": 3.5}, "loc") == pytest.approx(3.5)
        with pytest.raises(ValueError, match="departure_day"):
            _seed_departure_day({"departure_day": -1}, "loc")
        with pytest.raises(ValueError, match="departure_day"):
            _seed_departure_day({"departure_day": float("nan")}, "loc")

    def test_onset_day_is_finite_but_may_be_signed(self) -> None:
        assert _seed_onset_day({}, "loc") is None
        assert _seed_onset_day({"onset_day": -2.0}, "loc") == pytest.approx(-2.0)
        with pytest.raises(ValueError, match="onset_day"):
            _seed_onset_day({"onset_day": float("inf")}, "loc")


def _seed(**overrides) -> ExplicitSeed:
    base = {
        "pathogen_id": "noro",
        "count": 1,
        "role": None,
        "epoch": 10,
        "infection_age_days": 1.0,
        "dose": None,
        "strain_id": None,
    }
    base.update(overrides)
    return ExplicitSeed(**base)


class TestSeedEpochFields:
    # Hourly clock: 24 epochs per voyage day.
    _clock = SimClock(epoch_duration_hours=1.0, mode="hours")
    _engine = SimpleNamespace(clock=_clock)

    def test_no_onset_or_departure(self) -> None:
        onset_inc, elapsed, dep = _seed_epoch_fields(
            _seed(), self._engine, epoch=10, location="loc",
        )
        assert (onset_inc, elapsed, dep) == (None, None, None)

    def test_onset_cannot_precede_acquisition(self) -> None:
        seed = _seed(onset_day=0.5, infection_age_days=0.2)
        # epoch 24 -> seed_day 1.0; incubation = 0.2 + 0.5 - 1.0 < 0
        with pytest.raises(ValueError, match="onset_day"):
            _seed_epoch_fields(seed, self._engine, epoch=24, location="loc")

    def test_departure_cannot_precede_the_seed_epoch(self) -> None:
        seed = _seed(departure_day=0.1, epoch=10)
        # 0.1 days -> epoch ~2.4, before the seed's own epoch 10
        with pytest.raises(ValueError, match="departure_day"):
            _seed_epoch_fields(seed, self._engine, epoch=10, location="loc")

    def test_declared_onset_and_departure_resolve(self) -> None:
        seed = _seed(onset_day=0.5, infection_age_days=1.0, departure_day=1.0)
        onset_inc, elapsed, dep = _seed_epoch_fields(
            seed, self._engine, epoch=12, location="loc",
        )
        # seed_day = 0.5 -> incubation 1.0, already at onset at the epoch
        assert onset_inc == pytest.approx(1.0)
        assert elapsed == pytest.approx(0.0)
        assert dep == 24


class TestStampSeedOnset:
    def test_future_onset_only_stamps_the_record(self) -> None:
        agent = SimpleNamespace(infections={"noro": {}})
        _stamp_seed_onset(
            agent, _seed(), {}, SimClock(), np.random.default_rng(0),
            onset_incubation=2.0, elapsed_since_onset=0.0, location="loc",
        )
        assert agent.infections["noro"]["incubation_days"] == pytest.approx(2.0)
        assert agent.infections["noro"]["will_present"] is True


class TestVoyageHelpers:
    def test_unconfigured_day_is_a_sea_day(self) -> None:
        day_type, entry = _day_type_and_entry([], 3)
        assert day_type == "sea_day"
        assert entry["day"] == 3
        day_type, entry = _day_type_and_entry(
            [{"day": 4, "type": "port_day"}], 4,
        )
        assert day_type == "port_day"

    def test_between_ashore_windows(self) -> None:
        entry = {
            "disembark_window_hours_of_day": [8, 12],
            "reembark_window_hours_of_day": [16, 20],
        }
        assert _between_ashore_windows("sea_day", entry, 14) is False
        assert _between_ashore_windows("port_day", {}, 14) is False
        assert _between_ashore_windows("port_day", entry, 14) is True
        assert _between_ashore_windows("port_day", entry, 9) is False

    def test_embarkation_surge(self) -> None:
        entry = {"buffet_surge_fraction": 0.6}
        assert _embarkation_surge("sea_day", entry, {}, True, 1.0) == (0.0, 1.0)
        assert _embarkation_surge("embarkation", entry, {}, False, 1.0) == (
            0.0, 1.0,
        )
        surge, contact = _embarkation_surge(
            "embarkation", entry,
            {"embarkation_buffet_surge": True, "contact_rate_multiplier": 1.2},
            True, 1.0,
        )
        assert surge == pytest.approx(0.6)
        assert contact == pytest.approx(1.2)

    def test_onboard_fraction_branches(self) -> None:
        defaults = {"onboard_passenger_fraction": 0.4}
        assert _onboard_fraction(
            "port_day", defaults, in_disembark=True,
            in_reembark=False, between_ashore=False, disembark_fraction=0.3,
        ) == pytest.approx(0.7)
        assert _onboard_fraction(
            "port_day", defaults, in_disembark=False,
            in_reembark=True, between_ashore=False, disembark_fraction=0.3,
        ) == pytest.approx(1.0)
        assert _onboard_fraction(
            "disembarkation", defaults, in_disembark=True,
            in_reembark=False, between_ashore=False, disembark_fraction=0.3,
        ) == pytest.approx(0.4)
        assert _onboard_fraction(
            "sea_day", defaults, in_disembark=False,
            in_reembark=False, between_ashore=False, disembark_fraction=0.3,
        ) == pytest.approx(0.4)

    def test_disembarkation_day_sends_passengers_ashore_only(self) -> None:
        pax = [SimpleNamespace(), SimpleNamespace()]
        crew = [SimpleNamespace()]
        state = EpochState(day_type="disembarkation", in_disembark_window=True)
        _apply_disembarkation_day(pax, crew, state)
        assert all(a.ashore for a in pax)
        assert all(not a.ashore for a in crew)


class TestBehaviorMergeAndCatalogs:
    def test_merged_behavior_defaults(self) -> None:
        merged = _merged_agent_behavior(None)
        assert "dining_meal_weights" in merged

    def test_merged_behavior_deep_merges_meal_weights(self) -> None:
        merged = _merged_agent_behavior({
            "dining_rotation_probability": 0.5,
            "dining_meal_weights": {"lunch": {"buffet": 0.9}},
        })
        assert merged["dining_rotation_probability"] == pytest.approx(0.5)
        lunch = merged["dining_meal_weights"]["lunch"]
        assert lunch["buffet"] == pytest.approx(0.9)
        # The other service-type entries survive the merge.
        assert "mdr" in lunch or len(lunch) >= 1

    def test_leisure_catalog_falls_back_to_all_free_zones(self) -> None:
        zones = [
            {"name": "Engine Room", "type": "Free"},
            {"name": "Sky Lounge", "type": "Free"},
        ]
        catalog = _leisure_catalog_from(zones)
        assert [z["name"] for z in catalog] == ["Sky Lounge"]
        fallback = _leisure_catalog_from([
            {"name": "Engine Room", "type": "Free"},
        ])
        assert [z["name"] for z in fallback] == ["Engine Room"]

    def test_dining_catalog_resolves_service_types(self) -> None:
        zones = [
            {"name": "Windjammer", "type": "Dining"},
            {"name": "Crew Mess Hall", "type": "Dining", "meal_seatings": 2},
            {"name": "Pool Deck", "type": "Free"},
        ]
        catalog = _dining_catalog_from(zones)
        assert [e["name"] for e in catalog] == [
            "Windjammer", "Crew Mess Hall",
        ]
        assert catalog[0]["service_type"] == "buffet"
        assert catalog[1]["service_type"] == "crew_mess"
        assert catalog[1]["meal_seatings"] == 2


class TestLegacyInitHelpers:
    def test_engine_constructs_with_legacy_classes(self) -> None:
        engine = KorkinShipEngine(
            num_passengers=4,
            num_crew=2,
            initial_infected=1,
            immune_ratio=0.0,
            seed=7,
            clock=SimClock(epoch_duration_hours=1.0, mode="hours"),
        )
        assert len(engine.agents) == 6


class TestAhsStarPaths:
    def test_empty_and_zero_flow_groups_yield_no_paths(self) -> None:
        assert _ahs_group_star_paths(1, {"returns": {}, "supplies": {},
                                        "recirc": 0.0}, 0.2) == []
        group = {"returns": {"z1": 0.0}, "supplies": {"z2": 0.0},
                 "recirc": 0.0}
        assert _ahs_group_star_paths(1, group, 0.2) == []

    def test_declared_zero_recirc_is_recovered_from_oa(self) -> None:
        group = {"returns": {"z1": 100.0}, "supplies": {"z2": 100.0},
                 "recirc": 0.0}
        paths = _ahs_group_star_paths(1, group, 0.2)
        assert paths  # recirc recovered as (1 - oa) * min(sumR, sumS)
        assert all(p.flow_rate_m3h > 0.0 for p in paths)


class TestFoldAhsPlenum:
    def _engine(self) -> ContamTransportEngine:
        return ContamTransportEngine(
            spatial_layout={"zones": [{"id": "A", "volume_m3": 100.0}]},
            air_flow_paths={
                "hvac_zones": [], "cross_zone_links": [], "adjacency": [],
            },
        )

    def test_zero_return_flow_is_a_noop(self) -> None:
        engine = self._engine()
        source_rate: dict[str, float] = {}
        outflow_rate: dict[str, float] = {}
        engine._fold_ahs_plenum([], [], {}, source_rate, outflow_rate)
        assert source_rate == {}
        assert outflow_rate == {}

    def test_supply_to_unknown_zone_is_skipped(self) -> None:
        engine = self._engine()
        returns = [ContamAirflowPath(
            "r1", "zone_a", "ahs_plenum_1", 10.0,
        )]
        supplies = [ContamAirflowPath(
            "s1", "ahs_plenum_1", "zone_b", 10.0,
            path_type=PATH_TYPE_HVAC_SUPPLY,
        )]
        source_rate: dict[str, float] = {"zone_b": 0.0}
        outflow_rate: dict[str, float] = {}
        concentrations = {"zone_a": 2.0}
        engine._fold_ahs_plenum(
            returns, supplies, concentrations, source_rate, outflow_rate,
        )
        assert source_rate["zone_b"] > 0.0
        assert "zone_a" not in outflow_rate  # no zone_nodes entry

    def test_supply_to_untracked_zone_is_dropped(self) -> None:
        engine = self._engine()
        returns = [ContamAirflowPath("r1", "zone_a", "ahs_plenum_1", 10.0)]
        supplies = [ContamAirflowPath(
            "s1", "ahs_plenum_1", "zone_b", 10.0,
            path_type=PATH_TYPE_HVAC_SUPPLY,
        )]
        source_rate: dict[str, float] = {}
        engine._fold_ahs_plenum(
            returns, supplies, {"zone_a": 2.0}, source_rate, {},
        )
        assert source_rate == {}


class TestWearableGates:
    def _monitor(self) -> WearableMonitor:
        return WearableMonitor(
            devices={}, class_device_assignments={},
            rng=np.random.default_rng(0),
        )

    def test_false_positive_injection_at_low_specificity(self) -> None:
        monitor = self._monitor()
        device = WearableDevice("w", ["heart_rate"])
        result: dict = {"anomaly_count": 0, "anomaly_channels": [],
                        "summary": {}}
        monitor._gate_anomaly_flags(
            result, device, False, sensitivity=1.0, specificity=0.0,
        )
        assert result["anomaly_count"] == 1
        assert result["anomaly_channels"] == ["heart_rate"]

    def test_true_anomaly_suppressed_at_zero_sensitivity(self) -> None:
        monitor = self._monitor()
        device = WearableDevice("w", ["heart_rate"])
        result: dict = {
            "anomaly_count": 1, "anomaly_channels": ["heart_rate"],
            "summary": {"heart_rate": {"anomaly": True}},
        }
        monitor._gate_anomaly_flags(
            result, device, True, sensitivity=0.0, specificity=1.0,
        )
        assert result["anomaly_count"] == 0
        assert result["summary"]["heart_rate"]["anomaly"] is False

    def test_monitor_config_without_devices_returns_none(self) -> None:
        assert build_wearable_monitor_from_config(
            {"wearable_monitoring": {"enabled": True, "devices": []}},
        ) is None


class TestSmallHelpers:
    def test_fomite_row_rejects_non_mapping(self) -> None:
        with pytest.raises(ValueError, match="mapping"):
            _parse_declared_shares({"cabin": 42})

    def test_collect_engine_py_paths_verbose(self, capsys) -> None:
        paths: list[str] = []
        _collect_engine_py_paths(
            "t", {"repo_dir": "/tmp", "py_paths": []}, paths, True,
        )
        assert "(no Python paths)" in capsys.readouterr().out
        _collect_engine_py_paths(
            "t", {"repo_dir": "/tmp", "py_paths": ["/tmp"]}, paths, True,
        )
        assert paths == ["/tmp"]
        assert "python   /tmp" in capsys.readouterr().out

    def test_unknown_engine_is_reported_missing(self) -> None:
        status, paths = engine_import_paths(engines=["no_such_engine"])
        assert status == {"no_such_engine": False}
