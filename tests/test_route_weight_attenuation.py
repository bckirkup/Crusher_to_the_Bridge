from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator

import pytest

from engines.transmission_core import TransmissionCore
from telemetry_buffer.observation_model import route_weight_attenuation as rwa

# Importing the harness installs its monkeypatch on the transmission core; undo
# it here so the rest of the suite runs against the shipped implementation.
TransmissionCore._apply_route_efficiencies = rwa._original

PATHOGEN = "norwalk_gi"
OTHER_PATHOGEN = "sars_cov2_resp"
FAKE_ATTENUATION = 0.5
REL = 1e-12


def _scaling_original(_self, _profile, agent_doses, agent_pathway_doses) -> None:
    for aid, pathways in agent_pathway_doses.items():
        for name in list(pathways):
            pathways[name] = float(pathways[name]) * FAKE_ATTENUATION
        agent_doses[aid] = sum(pathways.values())


@pytest.fixture(autouse=True)
def clear_module_accumulators() -> Iterator[None]:
    rwa.PRE.clear()
    rwa.POST.clear()
    rwa.EVENTS.clear()
    yield
    rwa.PRE.clear()
    rwa.POST.clear()
    rwa.EVENTS.clear()


@pytest.fixture
def target() -> dict[tuple[str, str], float]:
    return defaultdict(float)


def test_accumulate_sums_across_agents_and_calls(
    target: dict[tuple[str, str], float],
) -> None:
    doses = {
        "a1": {"fomite": 10.0, "droplet": 1.0},
        "a2": {"fomite": 5.0},
    }
    rwa.accumulate(PATHOGEN, doses, target)
    rwa.accumulate(PATHOGEN, doses, target)
    assert target[(PATHOGEN, "fomite")] == pytest.approx(30.0, rel=REL)
    assert target[(PATHOGEN, "droplet")] == pytest.approx(2.0, rel=REL)


def test_accumulate_keys_by_pathogen_so_the_two_arms_stay_independent(
    target: dict[tuple[str, str], float],
) -> None:
    rwa.accumulate(PATHOGEN, {"a1": {"fomite": 10.0}}, target)
    rwa.accumulate(OTHER_PATHOGEN, {"a1": {"fomite": 4.0}}, target)
    assert set(target) == {(PATHOGEN, "fomite"), (OTHER_PATHOGEN, "fomite")}
    assert target[(PATHOGEN, "fomite")] == pytest.approx(10.0, rel=REL)
    assert target[(OTHER_PATHOGEN, "fomite")] == pytest.approx(4.0, rel=REL)


def test_exposure_records_skips_zero_dose_agents() -> None:
    records = rwa.exposure_records(
        PATHOGEN,
        {"a1": 0.0, "a2": 35.0},
        {"a1": {"fomite": 0.0}, "a2": {"direct_contact": 30.0, "fomite": 70.0}},
        {"a1": {"fomite": 0.0}, "a2": {"direct_contact": 10.5, "fomite": 24.5}},
    )
    assert len(records) == 1
    assert records[0]["pathogen_id"] == PATHOGEN


def test_exposure_records_carry_both_dose_streams() -> None:
    records = rwa.exposure_records(
        PATHOGEN,
        {"a1": 0.0, "a2": 35.0},
        {"a1": {"fomite": 0.0}, "a2": {"direct_contact": 30.0, "fomite": 70.0}},
        {"a1": {"fomite": 0.0}, "a2": {"direct_contact": 10.5, "fomite": 24.5}},
    )
    record = records[0]
    assert record["post_total"] == pytest.approx(35.0, rel=REL)
    assert record["post"] == {"direct_contact": 10.5, "fomite": 24.5}
    assert record["pre"] == {"direct_contact": 30.0, "fomite": 70.0}


def test_exposure_records_pre_total_is_the_pre_pathway_sum_not_the_post_total() -> None:
    records = rwa.exposure_records(
        PATHOGEN,
        {"a2": 35.0},
        {"a2": {"direct_contact": 30.0, "fomite": 70.0}},
        {"a2": {"direct_contact": 10.5, "fomite": 24.5}},
    )
    assert records[0]["pre_total"] == pytest.approx(100.0, rel=REL)
    assert records[0]["pre_total"] != pytest.approx(35.0, rel=1e-3)


def test_exposure_record_keys_are_in_the_documented_order() -> None:
    records = rwa.exposure_records(
        PATHOGEN, {"a2": 35.0}, {"a2": {"fomite": 100.0}}, {"a2": {"fomite": 35.0}}
    )
    assert list(records[0]) == [
        "pathogen_id",
        "post_total",
        "post",
        "pre_total",
        "pre",
    ]


def test_instrumented_records_the_pre_weight_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rwa, "_original", _scaling_original)
    agent_doses = {"a1": 100.0}
    agent_pathway_doses = {"a1": {"fomite": 80.0, "droplet": 20.0}}
    rwa._instrumented(None, {"pathogen_id": PATHOGEN}, agent_doses, agent_pathway_doses)
    assert rwa.PRE[(PATHOGEN, "fomite")] == pytest.approx(80.0, rel=REL)
    assert rwa.PRE[(PATHOGEN, "droplet")] == pytest.approx(20.0, rel=REL)


def test_instrumented_records_the_post_weight_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rwa, "_original", _scaling_original)
    agent_pathway_doses = {"a1": {"fomite": 80.0, "droplet": 20.0}}
    rwa._instrumented(None, {"pathogen_id": PATHOGEN}, {"a1": 100.0}, agent_pathway_doses)
    for name in ("fomite", "droplet"):
        ratio = rwa.POST[(PATHOGEN, name)] / rwa.PRE[(PATHOGEN, name)]
        assert ratio == pytest.approx(FAKE_ATTENUATION, rel=REL)


def test_instrumented_appends_one_event_per_exposed_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rwa, "_original", _scaling_original)
    rwa._instrumented(
        None,
        {"pathogen_id": PATHOGEN},
        {"a1": 100.0, "a2": 0.0},
        {"a1": {"fomite": 100.0}, "a2": {"fomite": 0.0}},
    )
    assert len(rwa.EVENTS) == 1
    assert rwa.EVENTS[0]["pre_total"] == pytest.approx(100.0, rel=REL)
    assert rwa.EVENTS[0]["post_total"] == pytest.approx(50.0, rel=REL)


def test_build_run_spec_places_the_runner_fields() -> None:
    spec = rwa.build_run_spec(72, 450, "expedition_cruise_450", 500)
    assert spec["catalog"]["platform_id"] == "expedition_cruise_450"
    assert spec["run"]["random_seed"] == 500
    assert spec["run"]["num_epochs"] == 72
    assert spec["config_overrides"]["ship_graph"]["num_agents"] == 450


def test_build_run_spec_uses_the_two_pathogen_bundle() -> None:
    spec = rwa.build_run_spec(72, 450, "expedition_cruise_450", 500)
    assert spec["catalog"]["pathogen_bundle_id"] == "active_profiles"


@pytest.fixture
def report() -> list[str]:
    pre = {
        (PATHOGEN, "fomite"): 100.0,
        (PATHOGEN, "droplet"): 50.0,
        (OTHER_PATHOGEN, "droplet"): 200.0,
    }
    post = {
        (PATHOGEN, "fomite"): 30.0,
        (PATHOGEN, "droplet"): 5.0,
        (OTHER_PATHOGEN, "droplet"): 20.0,
    }
    return rwa.summary_lines(pre, post)


def test_summary_lines_has_one_section_per_pathogen(report: list[str]) -> None:
    headers = [line for line in report if line.startswith("\n--- ")]
    assert headers == [f"\n--- {PATHOGEN} ---", f"\n--- {OTHER_PATHOGEN} ---"]


def test_summary_lines_w_column_is_the_post_over_pre_ratio(report: list[str]) -> None:
    ratios = {}
    for line in report:
        fields = line.split()
        if fields and fields[0] in {"fomite", "droplet"}:
            ratios[(fields[0], float(fields[1]))] = float(fields[5])
    assert ratios[("fomite", 100.0)] == pytest.approx(0.300, abs=5e-4)
    assert ratios[("droplet", 50.0)] == pytest.approx(0.100, abs=5e-4)
    assert ratios[("droplet", 200.0)] == pytest.approx(0.100, abs=5e-4)


def test_summary_lines_realised_attenuation_is_the_total_ratio(
    report: list[str],
) -> None:
    realised = [line for line in report if line.startswith("realised attenuation")]
    assert realised[0].endswith(f"{35.0 / 150.0:.4f}")
    assert realised[1].endswith(f"{20.0 / 200.0:.4f}")
