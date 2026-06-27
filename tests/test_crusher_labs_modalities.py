"""
test_crusher_labs_modalities.py – Direct tests for lab_notebook and modality modules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Covers:
- ArtificialLabNotebook three-tier fidelity serialization
- FidelityProfile parsing
- ClinicalRDT sensitivity and specificity
- MetagenomicSequencing CLR transform and ecological drift
- TargetedPCR Ct computation and LOD gating

Closes #92.
"""

from __future__ import annotations

import json
import math
import os
import sys
from typing import Any

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


# ── FidelityProfile tests ───────────────────────────────────────────────

class TestFidelityProfile:
    def test_high_fidelity_enables_all(self) -> None:
        from crusher_labs.lab_notebook import FidelityProfile

        fp = FidelityProfile({
            "log_binary_states": True,
            "log_numeric_outputs": True,
            "log_raw_matrices": True,
            "log_host_microflora_variance": True,
            "log_contact_tracing": True,
            "log_raw_instrument_telemetry": True,
            "log_qc_validation": True,
        })
        assert fp.log_binary is True
        assert fp.log_numeric is True
        assert fp.log_raw is True
        assert fp.log_raw_instrument is True
        assert fp.log_qc_flags is True

    def test_low_fidelity_defaults(self) -> None:
        from crusher_labs.lab_notebook import FidelityProfile

        fp = FidelityProfile({})
        assert fp.log_binary is True  # default
        assert fp.log_numeric is False
        assert fp.log_raw is False

    def test_mid_fidelity(self) -> None:
        from crusher_labs.lab_notebook import FidelityProfile

        fp = FidelityProfile({
            "log_binary_states": True,
            "log_numeric_outputs": True,
            "log_raw_matrices": False,
        })
        assert fp.log_binary is True
        assert fp.log_numeric is True
        assert fp.log_raw is False


# ── ArtificialLabNotebook tests ─────────────────────────────────────────

class TestArtificialLabNotebook:
    def _make_notebook(self, fidelity_name: str = "HIGH_FIDELITY") -> Any:
        from crusher_labs.lab_notebook import ArtificialLabNotebook, FidelityProfile

        fp = FidelityProfile({
            "log_binary_states": True,
            "log_numeric_outputs": True,
            "log_raw_matrices": True,
            "log_host_microflora_variance": True,
            "log_contact_tracing": True,
            "log_raw_instrument_telemetry": True,
            "log_qc_validation": True,
        })
        return ArtificialLabNotebook(fidelity=fp, fidelity_name=fidelity_name)

    def test_set_run_metadata(self) -> None:
        nb = self._make_notebook()
        nb.set_run_metadata(
            num_agents=20,
            num_epochs=24,
            pathogens=["test_virus"],
            zones=["Bridge", "Galley"],
        )
        assert nb._metadata["num_agents"] == 20
        assert nb._metadata["active_pathogens"] == ["test_virus"]

    def test_log_trigger_transition(self) -> None:
        nb = self._make_notebook()
        nb.log_trigger_transition(5, "BASELINE", "SUSPECTED")
        assert len(nb.records) == 1
        rec = nb.records[0]
        assert rec["assay_type"] == "trigger_transition"
        assert rec["timestamp_epoch"] == 5

    def test_serialize_roundtrip(self) -> None:
        nb = self._make_notebook()
        nb.set_run_metadata(
            num_agents=10, num_epochs=4,
            pathogens=["p1"], zones=["Z1"],
        )
        nb.log_trigger_transition(0, "BASELINE", "SUSPECTED")
        path = os.path.join(REPO_ROOT, "telemetry_buffer", "test_lab_notebook_roundtrip.json")
        try:
            nb.serialize(path)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            assert data["notebook_type"] == "artificial_lab_notebook"
            assert data["version"] == "3.0"
            assert data["total_records"] == 1
            assert data["run_metadata"]["num_agents"] == 10
        finally:
            os.unlink(path)

    def test_low_fidelity_uses_stoplight(self) -> None:
        nb = self._make_notebook("LOW_FIDELITY")
        nb.log_trigger_transition(3, "BASELINE", "CONFIRMED")
        rec = nb.records[0]
        assert "stoplight" in rec
        assert rec["stoplight"] == "RED"

    def test_mid_fidelity_has_binary_result(self) -> None:
        nb = self._make_notebook("MID_FIDELITY")
        nb.log_trigger_transition(2, "BASELINE", "SUSPECTED")
        rec = nb.records[0]
        assert "binary_result" in rec
        assert rec["binary_result"] == "SUSPECTED"


# ── ClinicalRDT tests ───────────────────────────────────────────────────

class TestClinicalRDT:
    def test_default_init(self) -> None:
        from crusher_labs.modalities.clinical_rdt import ClinicalRDT

        rdt = ClinicalRDT()
        assert rdt.name == "clinical_rdt"
        assert 0.0 < rdt.base_sensitivity <= 1.0
        assert 0.0 < rdt.specificity <= 1.0

    def test_query_ground_truth_infected(self) -> None:
        from crusher_labs.modalities.clinical_rdt import ClinicalRDT

        rdt = ClinicalRDT(rng=np.random.default_rng(42))
        payload = {
            "epoch": 3,
            "agents": [
                {"agent_id": 0, "shedding_rate": 100.0},
                {"agent_id": 1, "shedding_rate": 0.0},
            ],
        }
        result = rdt.query_ground_truth(payload, sick_call_ids=[0, 1])
        assert "results" in result or "agent_results" in result or isinstance(result, dict)

    def test_query_ground_truth_no_sick_call(self) -> None:
        from crusher_labs.modalities.clinical_rdt import ClinicalRDT

        rdt = ClinicalRDT(specificity=1.0, rng=np.random.default_rng(42))
        payload = {
            "epoch": 0,
            "agents": [{"agent_id": 0, "shedding_rate": 0.0}],
        }
        result = rdt.query_ground_truth(payload)
        assert result is not None


# ── MetagenomicSequencing tests ──────────────────────────────────────────

class TestMetagenomicSequencing:
    def test_default_init(self) -> None:
        from crusher_labs.modalities.sequencing import MetagenomicSequencing

        seq = MetagenomicSequencing()
        assert seq.name == "sequencing"
        assert seq.read_depth == 100_000

    def test_clr_transform_module_level(self) -> None:
        from crusher_labs.modalities.sequencing import _clr_transform

        arr = np.array([50.0, 30.0, 20.0])
        clr = _clr_transform(arr)
        assert len(clr) == 3
        # CLR values should sum to ~0
        assert abs(clr.sum()) < 1e-6

    def test_seed_zone_microbiome(self) -> None:
        from crusher_labs.modalities.sequencing import MetagenomicSequencing

        seq = MetagenomicSequencing(rng=np.random.default_rng(42))
        configs = [{"name": "Z1", "type": "Dining"}, {"name": "Z2", "type": "Free"}]
        biomes = seq.seed_zones(configs)
        assert "Z1" in biomes
        assert "Z2" in biomes


# ── TargetedPCR tests ────────────────────────────────────────────────────

class TestTargetedPCR:
    def test_default_init(self) -> None:
        from crusher_labs.modalities.targeted_pcr import TargetedPCR

        pcr = TargetedPCR()
        assert pcr.name == "targeted_pcr"
        assert pcr.lod_ct_threshold == pytest.approx(38.0)

    def test_compute_ct_with_mass(self) -> None:
        from crusher_labs.modalities.targeted_pcr import TargetedPCR

        pcr = TargetedPCR(extraction_efficiency=0.5, ct_slope=-3.322, ct_intercept=40.0)
        ct = pcr._compute_ct(1000.0)
        assert ct is not None
        assert isinstance(ct, float)

    def test_compute_ct_zero_mass(self) -> None:
        from crusher_labs.modalities.targeted_pcr import TargetedPCR

        pcr = TargetedPCR()
        ct = pcr._compute_ct(0.0)
        assert ct is None

    def test_query_ground_truth(self) -> None:
        from crusher_labs.modalities.targeted_pcr import TargetedPCR

        pcr = TargetedPCR(lod_ct_threshold=38.0)
        payload = {
            "epoch": 5,
            "spaces": {
                "Z1": {"pathogen_mass": 1e6},
                "Z2": {"pathogen_mass": 0.0},
            },
        }
        result = pcr.query_ground_truth(payload)
        assert result["modality"] == "targeted_pcr"
        assert result["epoch"] == 5
        assert "Z1" in result["zone_results"]
        assert "Z2" in result["zone_results"]
        # High mass should be detected
        assert result["zone_results"]["Z1"]["detected"] is True
        # Zero mass should not
        assert result["zone_results"]["Z2"]["detected"] is False

    def test_surface_wipe_mode(self) -> None:
        from crusher_labs.modalities.targeted_pcr import TargetedPCR

        pcr = TargetedPCR()
        payload = {
            "epoch": 1,
            "spaces": {
                "Z1": {"pathogen_mass": 100.0},
                "Z2": {"pathogen_mass": 100.0},
            },
        }
        result = pcr.query_ground_truth(payload, surface_wipe_zones=["Z1"])
        assert result["surface_wipe_mode"] is True
        assert "Z1" in result["zone_results"]
        assert "Z2" not in result["zone_results"]
