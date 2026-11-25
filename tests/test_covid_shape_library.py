"""Focused checks for the COVID-SHED-SHAPELIB-01 documentation data.

This is a literature input library, not engine-active configuration.  The
checks protect the separation and normalization conventions that later owner
approved implementation work will rely on.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARY_PATH = ROOT / "docs" / "covid" / "covid_shed_shape_library_01.json"


def load_library():
    return json.loads(LIBRARY_PATH.read_text())


def test_shape_library_is_documentation_data_not_engine_config():
    library = load_library()
    assert library["library_id"] == "COVID-SHED-SHAPELIB-01"
    assert library["status"] == "documentation_input_library_not_engine_active"
    assert "not fitted or selected against Diamond Princess outcomes" in library["non_goals"]
    assert "transmission-derived profiles are validation targets only" in library["non_goals"]


def test_evidence_classes_are_separate_and_complete():
    classes = load_library()["shape_classes"]
    assert set(classes) == {
        "direct_emitted_material",
        "viable_virus_culture_proxy",
        "rna_kinetic_sensitivity",
        "outcome_side_validation_targets",
    }
    assert "candidate source-term evidence" in classes["direct_emitted_material"]["class_role"]
    assert "not emitted material" in classes["viable_virus_culture_proxy"]["class_role"]
    assert "not viable emission" in classes["rna_kinetic_sensitivity"]["class_role"]
    assert "never candidate source terms" in classes["outcome_side_validation_targets"]["class_role"]


def test_zhou_daily_tables_have_independent_negative_onset_and_normalized_shapes():
    library = load_library()
    families = library["shape_classes"]["direct_emitted_material"]["families"]
    assert {family["family_id"] for family in families} == {
        "zhou2023_mask_rna_onset_aligned_zero_inflated",
        "zhou2023_air_rna_onset_aligned_zero_inflated",
    }
    for family in families:
        for key in [
            "axis_definition",
            "central_and_uncertainty_variants",
            "duration_tail",
            "normalization",
            "measured_inferred_hypothesis",
        ]:
            assert key in family
        rows = family["daily"]
        assert any(row["day"] < 0 for row in rows)
        assert any((row.get("equal_weight_normalized_shape") or 0.0) > 0.0 for row in rows if row["day"] < 0)
        assert abs(sum(row.get("equal_weight_normalized_shape") or 0.0 for row in rows) - 1.0) < 1e-6
        assert abs(sum(row.get("normalized_mean_linear_shape") or 0.0 for row in rows) - 1.0) < 1e-6
        for row in rows:
            if row["detection_probability"] is not None:
                assert 0.0 <= row["detection_probability"] <= 1.0


def test_hakki_family_validates_axis_and_keeps_culture_proxy_separate():
    family = load_library()["shape_classes"]["viable_virus_culture_proxy"]["families"][0]
    assert family["family_id"] == "hakki2022_pfu_unvaccinated_pre_alpha_alpha_onset_aligned"
    assert "paper median onset-to-PFU-peak interval of 3 d" in family["axis_validation"]
    assert "7/35 (20%) presymptomatic PFU-positive fraction" in family["axis_validation"]
    assert "strict negative rows give 5/35" in family["axis_validation"]
    assert "not emitted material" in load_library()["shape_classes"]["viable_virus_culture_proxy"]["class_role"]
    rows = family["daily"]
    assert any(row["day"] < 0 for row in rows)
    assert abs(sum(row.get("equal_weight_normalized_shape") or 0.0 for row in rows) - 1.0) < 1e-6
    assert abs(sum(row.get("normalized_mean_linear_shape") or 0.0 for row in rows) - 1.0) < 1e-6


def test_kissler_is_not_invented_as_onset_aligned_and_owner_decision_is_named():
    library = load_library()
    kissler = library["shape_classes"]["rna_kinetic_sensitivity"]["families"][1]
    assert kissler["family_id"] == "kissler2021_rna_first_detectability_parameters"
    assert "not defensible" in kissler["axis_transfer_to_onset"]
    assert "symptom-onset timing was not recorded" in kissler["axis_transfer_to_onset"]
    assert library["blocked_or_not_recovered"]
    decision = library["owner_decision_required_before_engine_implementation"]
    assert "Zhou direct emitted RNA" in decision
    assert "Hakki/Killingley culture-proxy PFU kinetics" in decision
    assert "declared hybrid proxy-transfer rule" in decision
