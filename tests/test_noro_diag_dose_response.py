"""The shared noro_diag dose-response lookup follows its bundle argument."""

from __future__ import annotations

import json

import pytest

from simulation_utils import asset_defaults
from simulation_utils.paths import REPO_ROOT, resolve_repo_path
from tools.noro_diag.dose_response import load_dose_response


def _shipped(bundle: str, pathogen_id: str) -> dict[str, float]:
    path = resolve_repo_path(REPO_ROOT, asset_defaults.pathogen_bundle_rel(bundle))
    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)
    for entry in document["pathogens"]:
        if entry.get("pathogen_id") == pathogen_id:
            return entry["dose_response"]
    raise AssertionError(f"{pathogen_id} absent from bundle {bundle}")


def test_default_bundle_matches_the_shipped_profile():
    alpha, beta = load_dose_response("norwalk_gi")
    shipped = _shipped(asset_defaults.DEFAULT_PATHOGEN_BUNDLE_ID, "norwalk_gi")
    assert (alpha, beta) == (shipped["alpha"], shipped["beta"])
    assert alpha > 0.0
    assert beta > 0.0


@pytest.mark.parametrize(
    ("bundle", "pathogen_id"),
    [
        ("active_profiles", "norwalk_gi"),
        ("active_profiles", "sars_cov2_resp"),
        ("edison_10pathogen_profiles", "norovirus_gii4"),
        ("enterprise_tng_profiles", "tng_shipboard_influenza"),
    ],
)
def test_each_bundle_reports_its_own_pair(bundle: str, pathogen_id: str):
    shipped = _shipped(bundle, pathogen_id)
    assert load_dose_response(pathogen_id, bundle) == (
        shipped["alpha"], shipped["beta"],
    )


def test_unknown_pathogen_is_named_in_the_error():
    with pytest.raises(SystemExit) as excinfo:
        load_dose_response("not_a_pathogen")
    assert "not_a_pathogen" in str(excinfo.value)


def test_unknown_bundle_is_rejected():
    with pytest.raises((FileNotFoundError, ValueError)):
        load_dose_response("norwalk_gi", "not_a_bundle")
