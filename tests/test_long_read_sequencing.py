"""Long-read Nanopore verification modality tests."""

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
    SPECIMEN_WASTEWATER_METAGENOMICS,
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


def test_verify_detects_pathogen_from_zone_mass() -> None:
    params_path = os.path.join(REPO_ROOT, "data/config/long_read_sequencing_params.json")
    mod = LongReadNanoporeSequencing.from_params_path(
        params_path, "flongle_rapid", rng=__import__("numpy").random.default_rng(0),
        repo_root=REPO_ROOT,
    )
    req = LongReadVerificationRequest(
        request_id="lr_test",
        specimen_source=SPECIMEN_WASTEWATER_METAGENOMICS,
        collection_key="Engine_Room",
        trigger_reasons=["mixed_infection_suspected"],
    )
    spaces = {
        "Engine_Room": {
            "pathogen_mass": 5000.0,
            "pathogen_mass_by_id": {"norovirus": 5000.0},
        },
    }
    out = mod.verify(req, epoch=1, spaces=spaces, agents=[], pathogen_profiles={})
    assert out["status"] == "complete"
    assert isinstance(out["pathogen_calls"], list)


def test_instrument_run_requests_complete() -> None:
    params_path = os.path.join(REPO_ROOT, "data/config/long_read_sequencing_params.json")
    mod = LongReadNanoporeSequencing.from_params_path(
        params_path, "flongle_rapid", repo_root=REPO_ROOT,
    )
    inst = LongReadVerificationSequencing(modality=mod)
    req = LongReadVerificationRequest(
        request_id="lr_0001",
        specimen_source="clinical_specimen",
        collection_key="3",
        trigger_reasons=["discordant_modalities"],
    )
    agents = [
        {
            "agent_id": 3,
            "shedding_rate": 5000.0,
            "pathogen_infections": {"norovirus": {"status": "INFECTED"}},
        },
    ]
    out = inst.run_requests(
        [req], epoch=0, spaces={}, agents=agents, pathogen_profiles={},
    )
    assert "lr_0001" in out
    assert out["lr_0001"]["status"] == "complete"
    assert "pathogen_calls" in out["lr_0001"]


def test_stoplights_include_long_read_when_results_present() -> None:
    lr = {
        "lr_0001": {
            "status": "complete",
            "pathogen_calls": [],
            "consensus_ready": False,
        },
    }
    lights = compute_stoplights({}, {}, {}, {}, {}, {}, long_read_results=lr)
    assert "long_read_verification_sequencing" in lights
    assert lights["long_read_verification_sequencing"]["lr_0001"] == "GREEN"


def test_stoplight_from_long_read_with_calls() -> None:
    assert stoplight_from_long_read_verification({"pathogen_calls": [{"taxon_id": "X"}]}) == "RED"


def test_stoplight_pending_is_green() -> None:
    assert stoplight_from_long_read_verification({"status": "pending"}) == "GREEN"
