from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.special import hyp1f1

from telemetry_buffer.observation_model import route_weight_attribution as rwa

PATHOGEN = "norwalk_gi"
ALPHA, BETA = rwa.DOSE_RESPONSE[PATHOGEN]
REL = 1e-9

P_35 = 0.0777026853895808
P_300 = 0.22768488688573907
P_100 = 0.14442644881189637
P_1000 = 0.31905715697446213
S_POST = 0.3053875722753199
S_PRE = 0.4634836057863585
DIRECT_CONTACT_ESTABLISHMENT_SHARE_POST = 0.25443957922272137
DIRECT_CONTACT_MASS_SHARE_POST = 35.0 / 335.0

EVENTS = [
    {
        "pathogen_id": "norwalk_gi",
        "pre": {"direct_contact": 100.0, "fomite": 0.0},
        "post": {"direct_contact": 35.0, "fomite": 0.0},
        "pre_total": 100.0,
        "post_total": 35.0,
    },
    {
        "pathogen_id": "norwalk_gi",
        "pre": {"direct_contact": 0.0, "fomite": 1000.0},
        "post": {"direct_contact": 0.0, "fomite": 300.0},
        "pre_total": 1000.0,
        "post_total": 300.0,
    },
    {
        "pathogen_id": "sars_cov2_resp",
        "pre": {"direct_contact": 50.0, "fomite": 0.0},
        "post": {"direct_contact": 12.5, "fomite": 0.0},
        "pre_total": 50.0,
        "post_total": 12.5,
    },
]


@pytest.fixture
def events_file(tmp_path: Path) -> Path:
    path = tmp_path / "exposure_events_synthetic_s500.json"
    path.write_text(json.dumps(EVENTS), encoding="utf-8")
    return path


def _post_attribution(events_file: Path) -> tuple[list[str], rwa.Attribution]:
    _, events = rwa.load_events(events_file, PATHOGEN)
    pathways, _, post = rwa.dose_matrices(events)
    return pathways, rwa.attribute(post, ALPHA, BETA)


def test_establishment_probability_is_the_exact_kummer_form() -> None:
    for dose in (35.0, 100.0, 300.0, 1000.0):
        expected = 1.0 - hyp1f1(ALPHA, ALPHA + BETA, -dose)
        assert rwa.establishment_probability(dose, ALPHA, BETA) == pytest.approx(
            expected, rel=REL
        )


def test_establishment_probability_matches_the_published_doses() -> None:
    doses = np.array([35.0, 300.0, 100.0, 1000.0])
    values = rwa.establishment_probability(doses, ALPHA, BETA)
    assert values == pytest.approx([P_35, P_300, P_100, P_1000], rel=REL)


def test_pathogen_filter_keeps_only_the_requested_arm(events_file: Path) -> None:
    all_events, events = rwa.load_events(events_file, PATHOGEN)
    assert len(all_events) == 3
    assert len(events) == 2
    assert {e["pathogen_id"] for e in events} == {PATHOGEN}


def test_post_weight_total_excludes_the_other_pathogens_event(
    events_file: Path,
) -> None:
    _, attribution = _post_attribution(events_file)
    assert attribution.total_establishment == pytest.approx(S_POST, rel=REL)


def test_post_weight_total_would_be_larger_if_the_other_arm_leaked_in(
    events_file: Path,
) -> None:
    _, attribution = _post_attribution(events_file)
    leaked = S_POST + float(rwa.establishment_probability(12.5, ALPHA, BETA))
    assert attribution.total_establishment != pytest.approx(leaked, rel=REL)


def test_pre_weight_total_is_the_unweighted_stream(events_file: Path) -> None:
    _, events = rwa.load_events(events_file, PATHOGEN)
    _, pre, _ = rwa.dose_matrices(events)
    assert rwa.attribute(pre, ALPHA, BETA).total_establishment == pytest.approx(
        S_PRE, rel=REL
    )


def test_direct_contact_mass_share_is_its_dose_fraction(events_file: Path) -> None:
    pathways, attribution = _post_attribution(events_file)
    index = pathways.index("direct_contact")
    assert attribution.mass_share[index] == pytest.approx(
        DIRECT_CONTACT_MASS_SHARE_POST, rel=REL
    )


def test_direct_contact_establishment_share_is_credited_by_probability(
    events_file: Path,
) -> None:
    pathways, attribution = _post_attribution(events_file)
    index = pathways.index("direct_contact")
    assert attribution.establishment_share[index] == pytest.approx(
        DIRECT_CONTACT_ESTABLISHMENT_SHARE_POST, rel=REL
    )


def test_establishment_share_is_not_mass_share(events_file: Path) -> None:
    pathways, attribution = _post_attribution(events_file)
    index = pathways.index("direct_contact")
    assert attribution.establishment_share[index] != pytest.approx(
        attribution.mass_share[index], rel=1e-3
    )


def test_both_share_vectors_sum_to_one(events_file: Path) -> None:
    _, attribution = _post_attribution(events_file)
    assert sum(attribution.mass_share) == pytest.approx(1.0, rel=REL)
    assert sum(attribution.establishment_share) == pytest.approx(1.0, rel=REL)


def test_pathway_order_is_sorted(events_file: Path) -> None:
    _, events = rwa.load_events(events_file, PATHOGEN)
    pathways, _, _ = rwa.dose_matrices(events)
    assert pathways == ["direct_contact", "fomite"]


def test_a_pathogen_with_no_events_exits(events_file: Path) -> None:
    with pytest.raises(SystemExit):
        rwa.load_events(events_file, "influenza_a")


def test_an_unknown_pathogen_id_raises_key_error(
    events_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", ["route_weight_attribution.py", str(events_file), "not_a_pathogen"])
    with pytest.raises(KeyError):
        rwa.main(events_file)


def test_main_reports_the_two_streams(
    events_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["route_weight_attribution.py", str(events_file), PATHOGEN])
    assert rwa.main(events_file) == 0
    out = capsys.readouterr().out
    assert f"pre-weight (weights all 1.0): S = {S_PRE:.4f}" in out
    assert f"post-weight (shipped weights): S = {S_POST:.4f}" in out
    assert "dominant pathway among the top 1% of exposures" in out
