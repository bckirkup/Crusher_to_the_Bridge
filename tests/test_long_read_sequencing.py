"""Long-read Nanopore verification modality framework tests."""

from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs import load_config, build_modalities
from crusher_labs.long_read_escalation import (
    collect_long_read_escalation_requests,
    is_long_read_enabled,
)
from crusher_labs.modalities.long_read_sequencing import (
    ALL_SPECIMEN_SOURCES,
    LongReadNanoporeSequencing,
    LongReadVerificationRequest,
)
from crusher_labs.observation_core import LongReadVerificationSequencing
from crusher_labs.protocol_engine import compute_stoplights
from crusher_labs.stoplight import stoplight_from_long_read_verification


def test_long_read_disabled_by_default() -> None:
    cfg = load_config()
    assert is_long_read_enabled(cfg) is False
    mods = build_modalities(cfg)
    assert "long_read_nanopore" not in mods


def test_escalation_mixed_infection_wastewater() -> None:
    cfg = {
        "long_read_sequencing": {
            "enabled": True,
            "specimen_sources": list(ALL_SPECIMEN_SOURCES),
            "escalation_triggers": {"mixed_infection_suspected": True},
        },
    }
    ww = {
        "Engine_Room": {
            "read_counts": {"Pathogen_a": 10, "Pathogen_b": 5},
            "anomaly_detected": False,
            "total_pathogen_reads": 15,
        },
    }
    reqs = collect_long_read_escalation_requests(
        cfg, ww_results=ww, swab_results={}, clin_rdt_results={},
        clin_qpcr_results={}, clin_microbio_results={},
    )
    assert len(reqs) == 1
    assert reqs[0].specimen_source == "wastewater_metagenomics"


def test_instrument_run_requests_stub() -> None:
    mod = LongReadNanoporeSequencing(enabled=True)
    inst = LongReadVerificationSequencing(modality=mod)
    req = LongReadVerificationRequest(
        request_id="lr_0001",
        specimen_source="clinical_specimen",
        collection_key="3",
        trigger_reasons=["discordant_modalities"],
    )
    out = inst.run_requests([req])
    assert "lr_0001" in out
    assert out["lr_0001"]["status"] == "framework_stub"
    assert out["lr_0001"]["pathogen_calls"] == []


def test_stoplights_include_long_read_when_results_present() -> None:
    lr = {
        "lr_0001": {
            "status": "framework_stub",
            "pathogen_calls": [],
            "consensus_ready": False,
        },
    }
    lights = compute_stoplights({}, {}, {}, {}, {}, {}, long_read_results=lr)
    assert "long_read_verification_sequencing" in lights
    assert lights["long_read_verification_sequencing"]["lr_0001"] == "AMBER"


def test_stoplight_from_long_read_with_calls() -> None:
    assert stoplight_from_long_read_verification({"pathogen_calls": ["X"]}) == "RED"
