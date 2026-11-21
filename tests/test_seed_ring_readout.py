"""Unit coverage for campaigns/covid/seed_ring_01/readout.py.

Synthetic cell payloads only — no engine runs. The grammar thresholds are
the frozen design's (founder >=10, ignition <=9, clause 197/0.173); the
payload shape mirrors the smoke cell under /tmp (seed_ring, observables,
acquisition_curve, quarantine_witness, delivery echoes).
"""
from __future__ import annotations

import json

import pytest

from campaigns.covid.seed_ring_01 import readout as ro


def _payload(
    arm: str = "PLACEMENT_BUFFET",
    seed: int = 20200205,
    theta: float = 316227766.01683795,
    founders: int = 12,
    clean: int = 10,
    d0: int = 3,
    routes: dict | None = None,
    onsets: int = 197,
    before: float = 34.0,
    ign_day: int | None = 8,
    placement: dict | None = None,
    dining_zone: str = "Windjammer",
    depart_epoch: int = 120,
    takeoff_floor: int = 10,
) -> dict:
    """A minimal-but-complete cell payload in the smoke-cell shape."""
    if placement is None and arm == "PLACEMENT_BUFFET":
        placement = {"dining_service_type": "buffet"}
    spec = {"count": 1, "role": "passenger", "infection_age_days": 6.8,
            "departure_day": 5.0, "onset_day": -1.0}
    if placement is not None:
        spec["placement"] = placement
    curve = {"total_by_day": {}}
    if ign_day is not None:
        # 49 below the mass until ign_day, then cross it that day.
        curve["total_by_day"] = {
            "0": 49, str(ign_day): 50 - 49 + 5,
        }
    return {
        "cell": {"key": f"{theta}|{arm}|{seed}", "theta": theta,
                 "arm_id": arm, "seed": seed},
        "index_onset_day": -1.0,
        "index_shedding_at_day0": True,
        "index_departed_epoch": depart_epoch,
        "funnel_hosts": [{"agent_id": 1}] * 3,
        "acquisition_curve": curve,
        "seed_ring": {
            "seeded_count": 1,
            "seed_spec": spec,
            "seeded_hosts": [{"agent_id": 1, "dining_zone": dining_zone}],
            "index_departure_epoch": depart_epoch,
            "aboard_window_acquisitions": founders,
            "aboard_window_clean_bound": clean,
            "aboard_window_by_route": routes or {"droplet": founders},
            "aboard_window_by_day": {"0": d0},
        },
        "observables": {
            "recorded_onsets": onsets,
            "onsets_before_split_day": before,
        },
        "quarantine_witness": {
            "window_days": [16, 30], "activated": True,
        },
        "propensity_draw": {"units_drawn": 2000},
        "delivery": {
            "presentation_draw_mode": "once_per_course",
            "hand_reservoir_mode": "hygiene_cycle",
            "caregiver": {"mode": "on"},
            "droplet_field_split": {
                "declared": {}, "mode": "partition",
                "far_field_share": 0.175, "settled_share": 0.0,
                "near_field_share": 0.825, "active": True,
            },
        },
    }


class TestScalars:
    def test_median_odd_even_empty(self):
        assert ro._median([]) is None
        assert ro._median([5.0]) == 5.0
        assert ro._median([1.0, 9.0]) == 5.0

    def test_quantile_endpoints(self):
        values = [0.0, 10.0, 20.0]
        assert ro._quantile(values, 0.0) == 0.0
        assert ro._quantile(values, 1.0) == 20.0
        assert ro._quantile(values, 0.5) == 10.0

    def test_fmt(self):
        assert ro._fmt(None) == "n/a"
        assert ro._fmt(1.0) == "1.000"

    def test_takeoff_threshold(self):
        assert ro._takeoff(_payload(onsets=10))
        assert not ro._takeoff(_payload(onsets=9))


class TestIgnitionDay:
    def test_crosses_mass(self):
        assert ro._ignition_day(_payload(ign_day=8)) == 8

    def test_never_ignites(self):
        assert ro._ignition_day(_payload(ign_day=None)) is None

    def test_empty_curve(self):
        p = _payload()
        p["acquisition_curve"] = {}
        assert ro._ignition_day(p) is None

    def test_before_share(self):
        p = _payload(onsets=200, before=34.0)
        assert ro._before_share(p) == pytest.approx(0.17)

    def test_before_share_none_on_zero(self):
        assert ro._before_share(_payload(onsets=0)) is None


class TestTrajectoryClause:
    def test_passes(self):
        cells = [
            _payload(seed=s, onsets=o)
            for s, o in zip(range(20200205, 20200210), [180, 190, 197, 200, 210])
        ]
        clause = ro._trajectory_clause(cells)
        assert clause["takeoff_n"] == 5
        assert clause["ok"]

    def test_fails_when_share_off(self):
        cells = [
            _payload(seed=s, before=200.0)
            for s in range(20200205, 20200210)
        ]
        clause = ro._trajectory_clause(cells)
        assert not clause["ok"]

    def test_insufficient_takeoff(self):
        cells = [_payload(seed=20200205, onsets=3)]
        assert ro._trajectory_clause(cells)["verdict"] == (
            "insufficient takeoff mass"
        )


class TestRowMetricsAndVerdict:
    def _row(self, n_ignite: int, n_dead: int, founders: int = 12):
        cells = [
            _payload(seed=20200205 + i, founders=founders, ign_day=8)
            for i in range(n_ignite)
        ] + [
            _payload(seed=20200300 + i, founders=founders, ign_day=None)
            for i in range(n_dead)
        ]
        return cells

    def test_censored_median_kills_timing_leg(self):
        """9 igniting + 11 dead takeoff cells: ignited-only median was 8,
        censored median is +inf, so the arm cannot LAND."""
        cells = self._row(9, 11)
        metrics = ro._row_metrics(cells)
        assert metrics["takeoff_n"] == 20
        assert metrics["ignited_n"] == 9
        assert metrics["ignition_day_median_takeoff"] == float("inf")
        verdict = ro._verdict("PLACEMENT_BUFFET", metrics)
        assert verdict.startswith("FOUNDERS-LIFTED-TIMING-SHORT")

    def test_landed(self):
        cells = self._row(20, 0)
        metrics = ro._row_metrics(cells)
        assert ro._verdict("PLACEMENT_BUFFET", metrics) == "SEED-RING-LANDED"

    def test_null_placement(self):
        cells = self._row(20, 0, founders=3)
        metrics = ro._row_metrics(cells)
        assert ro._verdict("PLACEMENT_BUFFET", metrics).startswith(
            "NULL-PLACEMENT"
        )

    def test_insufficient_mass(self):
        metrics = ro._row_metrics([_payload(onsets=3)])
        assert ro._verdict("PLACEMENT_BUFFET", metrics) == (
            "INSUFFICIENT-TAKEOFF-MASS"
        )

    def test_baseline_verdict(self):
        metrics = ro._row_metrics([])
        assert ro._verdict("D0_declared", metrics).startswith("BASELINE")

    def test_route_totals(self):
        cells = [
            _payload(seed=20200205, routes={"droplet": 2, "caregiver": 1}),
            _payload(seed=20200206, routes={"droplet": 1}),
        ]
        assert ro._row_metrics(cells)["route_totals"] == {
            "droplet": 3, "caregiver": 1,
        }


class TestAudit:
    def _audit(self, *payloads):
        return ro._audit(
            {p["cell"]["key"]: p for p in payloads}
        )

    def test_clean_payload(self):
        violations, flags = self._audit(_payload())
        assert violations == []
        assert flags == []

    def test_missing_placement_echo_on_probe_arm(self):
        p = _payload(placement=None)
        del p["seed_ring"]["seed_spec"]["placement"]
        violations, _ = self._audit(p)
        assert any("no placement echo" in v for v in violations)

    def test_wrong_placement_value(self):
        p = _payload(placement={"dining_service_type": "counter"})
        violations, _ = self._audit(p)
        assert any("!= declared" in v for v in violations)

    def test_non_buffet_zone_fails(self):
        violations, _ = self._audit(_payload(dining_zone="PC_D12_C_F"))
        assert any("buffet" in v for v in violations)

    def test_placement_leaks_to_baseline(self):
        p = _payload(arm="D0_declared",
                     placement={"dining_service_type": "buffet"})
        violations, _ = self._audit(p)
        assert any("leaked" in v for v in violations)

    def test_baseline_without_placement_clean(self):
        p = _payload(arm="D0_declared", placement=None,
                     dining_zone="SitDown_Room")
        violations, _ = self._audit(p)
        assert violations == []

    def test_index_geometry(self):
        violations, _ = self._audit(_payload())
        p = _payload()
        p["index_onset_day"] = 0.0
        violations, _ = self._audit(p)
        assert any("index_onset_day" in v for v in violations)
        p = _payload()
        p["index_shedding_at_day0"] = False
        violations, _ = self._audit(p)
        assert any("no emitter" in v for v in violations)

    def test_funnel_empty(self):
        p = _payload()
        p["funnel_hosts"] = []
        violations, _ = self._audit(p)
        assert any("funnel_hosts" in v for v in violations)

    def test_seeded_host_count_flag(self):
        p = _payload()
        p["seed_ring"]["seeded_hosts"] = []
        _, flags = self._audit(p)
        assert any("seeded_hosts" in f for f in flags)

    def test_departure_epoch_wrong_day(self):
        violations, _ = self._audit(_payload(depart_epoch=96))
        assert any("departure" in v for v in violations)

    def test_quarantine_witness(self):
        p = _payload()
        p["quarantine_witness"]["window_days"] = [16, 31]
        violations, _ = self._audit(p)
        assert any("quarantine_witness" in v for v in violations)
        p = _payload()
        p["quarantine_witness"]["activated"] = False
        violations, _ = self._audit(p)
        assert any("quarantine_witness" in v for v in violations)

    def test_propensity_zero(self):
        p = _payload()
        p["propensity_draw"]["units_drawn"] = 0
        violations, _ = self._audit(p)
        assert any("propensity" in v for v in violations)

    @pytest.mark.parametrize("field,bad", [
        ("presentation_draw_mode", "once_per_case"),
        ("hand_reservoir_mode", "snap"),
    ])
    def test_delivery_modes(self, field, bad):
        p = _payload()
        p["delivery"][field] = bad
        violations, _ = self._audit(p)
        assert any(field in v for v in violations)

    def test_caregiver_off(self):
        p = _payload()
        p["delivery"]["caregiver"]["mode"] = "off"
        violations, _ = self._audit(p)
        assert any("caregiver" in v for v in violations)

    def test_droplet_split_drift(self):
        p = _payload()
        p["delivery"]["droplet_field_split"]["far_field_share"] = 0.2
        violations, _ = self._audit(p)
        assert any("droplet_field_split" in v for v in violations)


class _FakeBody:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data


class _FakeS3:
    """Enough of boto3's client for _refit_witness."""

    def __init__(self, cells: dict):
        self._cells = cells  # key -> payload dict

    def get_object(self, Bucket, Key):  # noqa: N803 - boto3 arg names
        if Key not in self._cells:
            raise KeyError(Key)
        return {"Body": _FakeBody(json.dumps(self._cells[Key]).encode())}


class TestRefitWitness:
    def _rows(self, seeds=(20200205, 20200206)):
        rows = {}
        for seed in seeds:
            p = _payload(arm="D0_declared", placement=None, seed=seed,
                         dining_zone="SitDown_Room")
            rows.setdefault(
                (float(p["cell"]["theta"]), "D0_declared"), {}
            )[seed] = p
        return rows

    def _prefix_key(self, prefix, seed):
        rest = prefix[len("s3://"):]
        bucket, _, pfx = rest.partition("/")
        return f"{pfx.rstrip('/')}/{ro._REFIT_D0_BLOCK}/cell_{seed}.json"

    def test_clean_when_all_paired(self, monkeypatch):
        prefix = "s3://b/refit/"
        committed = {
            self._prefix_key(prefix, s): _payload(seed=s)
            for s in (20200205, 20200206)
        }
        monkeypatch.setattr(ro, "_s3_client", lambda: _FakeS3(committed))
        lines = ro._refit_witness(self._rows(), prefix)
        assert "DRIFT WITNESS CLEAN" in lines[0]
        assert "n=2" in lines[0]

    def test_unverified_on_missing_committed(self, monkeypatch):
        prefix = "s3://b/refit/"
        committed = {
            self._prefix_key(prefix, 20200205): _payload(seed=20200205),
        }
        monkeypatch.setattr(ro, "_s3_client", lambda: _FakeS3(committed))
        lines = ro._refit_witness(self._rows(), prefix)
        assert "DRIFT WITNESS UNVERIFIED" in lines[0]
        assert "CLEAN" not in lines[0]

    def test_drift_on_delta(self, monkeypatch):
        prefix = "s3://b/refit/"
        old = _payload(seed=20200205, onsets=190)
        committed = {
            self._prefix_key(prefix, 20200205): old,
            self._prefix_key(prefix, 20200206): _payload(seed=20200206),
        }
        monkeypatch.setattr(ro, "_s3_client", lambda: _FakeS3(committed))
        lines = ro._refit_witness(self._rows(), prefix)
        assert "DRIFT:" in lines[0]

    def test_zero_paired_unverified(self, monkeypatch):
        monkeypatch.setattr(ro, "_s3_client", lambda: _FakeS3({}))
        lines = ro._refit_witness(self._rows(), "s3://b/refit/")
        assert "UNVERIFIED" in lines[0]


class TestRender:
    def test_per_cell_table_and_sections(self):
        payloads = {
            p["cell"]["key"]: p
            for p in [_payload(seed=s, ign_day=8)
                      for s in range(20200205, 20200210)]
        }
        design = type("D", (), {"design_id": "covid_seed_ring_01"})()
        out = ro._render(design, payloads, "test-src", ["witness line"])
        assert "### PLACEMENT_BUFFET" in out
        assert "| 20200205 |" in out
        assert "Windjammer" in out
        assert "witness line" in out
        assert "SEED-RING-LANDED" in out

    def test_rows_grouping(self):
        p1 = _payload(seed=20200205)
        p2 = _payload(arm="D0_declared", placement=None, seed=20200205)
        rows = ro._rows({p["cell"]["key"]: p for p in (p1, p2)})
        assert len(rows) == 2
