"""
crusher_labs.lab_notebook
~~~~~~~~~~~~~~~~~~~~~~~~~

Artificial Lab Notebook serializer with three-tier fidelity output.

**Fidelity Tiers:**

HIGH_FIDELITY (Raw Synthetic Instrument):
  Raw machine telemetry — cycle-by-cycle amplification curves, raw
  background fluorescence, raw pre-normalization read counts,
  Dirichlet parameters, culture plate images, control line intensities.

MID_FIDELITY (Certified Clinical):
  CAP-style certified lab reports — Patient/Zone ID, Assay Target,
  clean binary outcomes (DETECTED/NOT DETECTED), formal Ct values,
  explicit QC validation flags, extraction efficiencies.

LOW_FIDELITY (Command/Strategic):
  Stoplight indicators — GREEN (Clear), AMBER (Elevated Anomaly),
  RED (Critical Hazard / Isolate Immediately).  No numeric detail.

Each record follows the biosurveillance-ingestible schema:
  sample_id, timestamp_epoch, collection_point_type, collection_zone,
  assay_type, raw_metric_output, inferred_anomaly_score
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from crusher_labs.stoplight import (
    stoplight_from_anomaly,
    stoplight_from_ct,
    stoplight_from_disruption,
    stoplight_from_rdt,
)
from simulation_utils.paths import prepare_output_directory, resolve_repo_path, validated_open
from telemetry_buffer.agent_axes import clinical_axes_for_notebook

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FIDELITY_HIGH = "HIGH_FIDELITY"
FIDELITY_MID = "MID_FIDELITY"
FIDELITY_LOW = "LOW_FIDELITY"

BINARY_DETECTED = "DETECTED"
BINARY_NOT_DETECTED = "NOT DETECTED"


# ── Fidelity model ───────────────────────────────────────────────────────


class FidelityProfile:
    """Parsed fidelity configuration."""

    def __init__(self, profile_dict: dict[str, Any]) -> None:
        self.log_binary = profile_dict.get("log_binary_states", True)
        self.log_numeric = profile_dict.get("log_numeric_outputs", False)
        self.log_raw = profile_dict.get("log_raw_matrices", False)
        self.log_microflora_variance = profile_dict.get("log_host_microflora_variance", False)
        self.log_contact_tracing = profile_dict.get("log_contact_tracing", False)
        self.log_raw_instrument = profile_dict.get("log_raw_instrument_telemetry", False)
        self.log_qc_flags = profile_dict.get("log_qc_validation", False)


def load_logging_profile(
    cfg_path: str | None = None,
) -> tuple[str, FidelityProfile, dict[str, Any]]:
    """Load the logging profile configuration."""
    if cfg_path is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg_path = resolve_repo_path(repo_root, "data/config/logging_profile.json")
    else:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg_path = resolve_repo_path(repo_root, cfg_path)

    if not os.path.isfile(cfg_path):
        return FIDELITY_HIGH, FidelityProfile({
            "log_binary_states": True,
            "log_numeric_outputs": True,
            "log_raw_matrices": True,
            "log_host_microflora_variance": True,
            "log_contact_tracing": True,
            "log_raw_instrument_telemetry": True,
            "log_qc_validation": True,
        }), {}

    with validated_open(cfg_path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        config = json.load(fh)

    fidelity_name = config.get("logging_fidelity", FIDELITY_HIGH)
    levels = config.get("fidelity_levels", {})
    profile_dict = levels.get(fidelity_name, {})

    return fidelity_name, FidelityProfile(profile_dict), config


def _sample_id(epoch: int, zone: str, assay: str) -> str:
    raw = f"E{epoch:03d}_{zone}_{assay}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:8]
    return f"CLN-{epoch:03d}-{zone[:6].upper()}-{assay[:4].upper()}-{h}"


# Stoplight functions imported from crusher_labs.stoplight
_stoplight_from_ct = stoplight_from_ct
_stoplight_from_anomaly = stoplight_from_anomaly
_stoplight_from_rdt = stoplight_from_rdt
_stoplight_from_disruption = stoplight_from_disruption


def _microbio_binary_result(secondary: bool, flora_shift: bool) -> str:
    if secondary:
        return "SECONDARY_INFECTION"
    if flora_shift:
        return "FLORA_SHIFT"
    return "NORMAL"


# ── Record builders ──────────────────────────────────────────────────────

def _air_sniffer_record(
    epoch: int,
    zone: str,
    data: dict[str, Any],
    fidelity_name: str,
    _fidelity: FidelityProfile,
) -> dict[str, Any]:
    detected = data.get("detected", False)
    ct = data.get("ct_value")

    if ct is not None and detected:
        anomaly = round(min(1.0, (38.0 - ct) / 20.0), 4)
    else:
        anomaly = 0.0

    record: dict[str, Any] = {
        "sample_id": _sample_id(epoch, zone, "AIR_SNIFFER"),
        "timestamp_epoch": epoch,
        "collection_point_type": "continuous_air_sampler",
        "collection_zone": zone,
        "assay_type": "aerosol_pcr",
        "fidelity_tier": fidelity_name,
    }

    if fidelity_name == FIDELITY_LOW:
        record["stoplight"] = _stoplight_from_ct(ct, detected)
        record["inferred_anomaly_score"] = anomaly
        return record

    # MID_FIDELITY: CAP-certified clinical report
    record["binary_result"] = BINARY_DETECTED if detected else BINARY_NOT_DETECTED
    record["inferred_anomaly_score"] = anomaly
    record["ct_value"] = ct
    record["captured_mass"] = data.get("captured_mass")
    record["concentration_per_m3"] = data.get("concentration_per_m3")
    record["sampled_volume_m3"] = data.get("sampled_volume_m3")

    # QC validation flag
    qc = data.get("qc_control")
    if qc:
        record["qc_status"] = qc["qc_status"]
        record["qc_measured_mass"] = qc["measured_mass"]
    else:
        record["qc_status"] = "QC_NOT_RUN"

    record["cross_contamination_carryover"] = data.get("cross_contamination_carryover", 0)

    if fidelity_name == FIDELITY_HIGH:
        record["raw_amplification_curve"] = data.get("raw_amplification_curve", [])
        record["background_fluorescence"] = data.get("background_fluorescence")

    return record


def _surface_swab_record(
    epoch: int,
    zone: str,
    data: dict[str, Any],
    fidelity_name: str,
    _fidelity: FidelityProfile,
) -> dict[str, Any]:
    detected = data.get("detected", False)
    ct = data.get("ct_value")

    if ct is not None and detected:
        anomaly = round(min(1.0, (38.0 - ct) / 20.0), 4)
    else:
        anomaly = 0.0

    record: dict[str, Any] = {
        "sample_id": _sample_id(epoch, zone, "SURFACE_SWAB"),
        "timestamp_epoch": epoch,
        "collection_point_type": "targeted_surface_swab",
        "collection_zone": zone,
        "assay_type": "surface_pcr",
        "fidelity_tier": fidelity_name,
    }

    if fidelity_name == FIDELITY_LOW:
        record["stoplight"] = _stoplight_from_ct(ct, detected)
        record["inferred_anomaly_score"] = anomaly
        return record

    record["binary_result"] = BINARY_DETECTED if detected else BINARY_NOT_DETECTED
    record["inferred_anomaly_score"] = anomaly
    record["ct_value"] = ct
    record["recovered_mass"] = data.get("recovered_mass")
    record["collection_efficiency"] = data.get("actual_collection_efficiency")
    record["technique_quality"] = data.get("technique_quality")
    record["compliance_scalar"] = data.get("compliance_scalar")

    qc = data.get("qc_control")
    if qc:
        record["qc_status"] = qc["qc_status"]
        record["qc_measured_mass"] = qc["measured_mass"]
    else:
        record["qc_status"] = "QC_NOT_RUN"

    record["cross_contamination_carryover"] = data.get("cross_contamination_carryover", 0)

    if fidelity_name == FIDELITY_HIGH:
        record["raw_amplification_curve"] = data.get("raw_amplification_curve", [])
        record["background_fluorescence"] = data.get("background_fluorescence")

    return record


def _wastewater_record(
    epoch: int,
    zone: str,
    data: dict[str, Any],
    fidelity_name: str,
    _fidelity: FidelityProfile,
) -> dict[str, Any]:
    anomaly_detected = data.get("anomaly_detected", False)
    pathogen_reads = data.get("total_pathogen_reads", 0)
    read_depth = data.get("read_depth", 50000)
    pathogen_frac = pathogen_reads / max(read_depth, 1)
    kingdom_shift = sum(abs(d) for d in data.get("kingdom_clr_deltas", {}).values())
    anomaly = round(min(1.0, pathogen_frac * 10 + kingdom_shift * 2), 4)

    record: dict[str, Any] = {
        "sample_id": _sample_id(epoch, zone, "WASTEWATER_SEQ"),
        "timestamp_epoch": epoch,
        "collection_point_type": "wastewater_sequencing_grid",
        "collection_zone": zone,
        "assay_type": "metagenomic_sequencing",
        "fidelity_tier": fidelity_name,
    }

    if fidelity_name == FIDELITY_LOW:
        record["stoplight"] = _stoplight_from_anomaly(anomaly)
        record["inferred_anomaly_score"] = anomaly
        return record

    record["binary_result"] = "ANOMALY" if anomaly_detected else "NORMAL"
    record["inferred_anomaly_score"] = anomaly
    record["pathogen_reads"] = pathogen_reads
    record["read_depth"] = read_depth
    record["pathogen_fraction"] = round(pathogen_frac, 6)
    record["disruption_types"] = data.get("disruption_types", [])
    record["kingdom_reads"] = data.get("kingdom_reads", {})
    record["kingdom_clr_deltas"] = data.get("kingdom_clr_deltas", {})

    qc = data.get("qc_control")
    if qc:
        record["qc_status"] = qc["qc_status"]
        record["qc_measured_mass"] = qc["measured_mass"]
    else:
        record["qc_status"] = "QC_NOT_RUN"

    record["cross_contamination_carryover"] = data.get("cross_contamination_carryover", 0)

    if fidelity_name == FIDELITY_HIGH:
        record["raw_read_counts_prenorm"] = data.get("raw_read_counts_prenorm", {})
        record["dirichlet_concentration"] = data.get("dirichlet_concentration")
        record["read_counts"] = data.get("read_counts", {})

    return record


def _long_read_verification_record(
    epoch: int,
    request_id: str,
    data: dict[str, Any],
    fidelity_name: str,
    _fidelity: FidelityProfile,
) -> dict[str, Any]:
    from crusher_labs.stoplight import stoplight_from_long_read_verification

    status = data.get("status", "")
    anomaly = 0.0
    if status == "pending":
        anomaly = 0.2
    elif data.get("mixed_infection_flag") or data.get("unexpected_pathogen_flag"):
        anomaly = max(anomaly, 0.7)

    record: dict[str, Any] = {
        "sample_id": _sample_id(epoch, request_id, "LONG_READ"),
        "timestamp_epoch": epoch,
        "collection_point_type": data.get("specimen_source", "long_read_verification"),
        "collection_zone": data.get("collection_key", "unknown"),
        "assay_type": "oxford_nanopore_long_read",
        "fidelity_tier": fidelity_name,
        "purpose": data.get("purpose", "verification"),
        "trigger_reasons": data.get("trigger_reasons", []),
    }

    if fidelity_name == FIDELITY_LOW:
        record["stoplight"] = stoplight_from_long_read_verification(data)
        record["inferred_anomaly_score"] = anomaly
        return record

    if status == "pending":
        record["binary_result"] = "PENDING"
    else:
        record["binary_result"] = "PENDING" if not data.get("consensus_ready") else "TYPED"
    record["inferred_anomaly_score"] = anomaly
    record["pathogen_calls"] = data.get("pathogen_calls", [])
    record["upstream_instrument"] = data.get("upstream_instrument", "")
    return record


def _clinical_rdt_record(
    epoch: int,
    data: dict[str, Any],
    fidelity_name: str,
    _fidelity: FidelityProfile,
) -> dict[str, Any]:
    agent_id = data.get("agent_id", -1)
    positive = data.get("positive", False)
    anomaly = 0.8 if positive else 0.0

    record: dict[str, Any] = {
        "sample_id": _sample_id(epoch, f"AGENT{agent_id}", "CLIN_RDT"),
        "timestamp_epoch": epoch,
        "collection_point_type": "clinical_rdt",
        "collection_zone": data.get("location", "MedBay"),
        "assay_type": "lateral_flow_antigen",
        "fidelity_tier": fidelity_name,
    }

    if fidelity_name == FIDELITY_LOW:
        record["stoplight"] = _stoplight_from_rdt(positive)
        record["inferred_anomaly_score"] = anomaly
        return record

    record["patient_id"] = agent_id
    record["binary_result"] = BINARY_DETECTED if positive else BINARY_NOT_DETECTED
    record["inferred_anomaly_score"] = anomaly
    record.update(clinical_axes_for_notebook(data))

    qc = data.get("qc_control")
    if qc:
        record["qc_status"] = qc["qc_status"]
    else:
        record["qc_status"] = "QC_NOT_RUN"

    record["cross_contamination_carryover"] = data.get("cross_contamination_carryover", 0)

    if fidelity_name == FIDELITY_HIGH:
        record["control_line_intensity"] = data.get("control_line_intensity")
        record["test_line_intensity"] = data.get("test_line_intensity")
        record["effective_sensitivity"] = data.get("effective_sensitivity")
        record["shedding_rate"] = data.get("shedding_rate")

    return record


def _clinical_qpcr_record(
    epoch: int,
    data: dict[str, Any],
    fidelity_name: str,
    _fidelity: FidelityProfile,
) -> dict[str, Any]:
    agent_id = data.get("agent_id", -1)
    detected = data.get("detected", False)
    ct = data.get("ct_value")

    if ct is not None and detected:
        anomaly = round(min(1.0, (40.0 - ct) / 20.0), 4)
    else:
        anomaly = 0.0

    record: dict[str, Any] = {
        "sample_id": _sample_id(epoch, f"AGENT{agent_id}", "CLIN_QPCR"),
        "timestamp_epoch": epoch,
        "collection_point_type": "clinical_qpcr",
        "collection_zone": data.get("location", "MedBay"),
        "assay_type": "patient_qpcr",
        "fidelity_tier": fidelity_name,
    }

    if fidelity_name == FIDELITY_LOW:
        record["stoplight"] = _stoplight_from_ct(ct, detected)
        record["inferred_anomaly_score"] = anomaly
        return record

    record["patient_id"] = agent_id
    record["binary_result"] = BINARY_DETECTED if detected else BINARY_NOT_DETECTED
    record["inferred_anomaly_score"] = anomaly
    record["ct_value"] = ct
    record["viral_load_copies_ml"] = data.get("viral_load_copies_ml")
    record.update(clinical_axes_for_notebook(data))

    qc = data.get("qc_control")
    if qc:
        record["qc_status"] = qc["qc_status"]
    else:
        record["qc_status"] = "QC_NOT_RUN"

    record["cross_contamination_carryover"] = data.get("cross_contamination_carryover", 0)

    if fidelity_name == FIDELITY_HIGH:
        record["raw_amplification_curve"] = data.get("raw_amplification_curve", [])
        record["background_fluorescence"] = data.get("background_fluorescence")
        record["specimen_mass"] = data.get("specimen_mass")

    return record


def _clinical_microbio_record(
    epoch: int,
    data: dict[str, Any],
    fidelity_name: str,
    _fidelity: FidelityProfile,
) -> dict[str, Any]:
    agent_id = data.get("agent_id", -1)
    flora_shift = data.get("flora_shift_detected", False)
    secondary = data.get("secondary_infection_detected", False)
    disruption = data.get("microflora_disruption_level", 0.0)
    anomaly = round(min(1.0, disruption), 4)

    record: dict[str, Any] = {
        "sample_id": _sample_id(epoch, f"AGENT{agent_id}", "CLIN_MICRO"),
        "timestamp_epoch": epoch,
        "collection_point_type": "clinical_microbiology",
        "collection_zone": data.get("location", "MedBay"),
        "assay_type": "culture_and_staining",
        "fidelity_tier": fidelity_name,
    }

    if fidelity_name == FIDELITY_LOW:
        record["stoplight"] = _stoplight_from_disruption(disruption)
        record["inferred_anomaly_score"] = anomaly
        return record

    record["patient_id"] = agent_id
    record["binary_result"] = _microbio_binary_result(secondary, flora_shift)
    record["inferred_anomaly_score"] = anomaly
    record["disruption_site"] = data.get("disruption_site")
    record["gram_stain_result"] = data.get("gram_stain_result")
    record["flora_shift_detected"] = flora_shift
    record["secondary_infection_detected"] = secondary
    record.update(clinical_axes_for_notebook(data))

    qc = data.get("qc_control")
    if qc:
        record["qc_status"] = qc["qc_status"]
    else:
        record["qc_status"] = "QC_NOT_RUN"

    record["cross_contamination_carryover"] = data.get("cross_contamination_carryover", 0)

    if fidelity_name == FIDELITY_HIGH:
        record["culture_results"] = data.get("culture_results", {})
        record["microflora_disruption_level"] = disruption

    return record


def _long_read_record(
    epoch: int,
    data: dict[str, Any],
    fidelity_name: str,
    _fidelity: FidelityProfile,
) -> dict[str, Any]:
    """Notebook entry for one delivered long-read verification.

    Keyed on the request rather than an agent, because the specimen may be
    environmental. The genotype recorded is the assay's consensus call, so a
    notebook read back later shows what the lab reported, not the truth.
    """
    calls = data.get("pathogen_calls") or []
    genotypes = data.get("genotype_calls") or []
    detected = bool(calls)
    record: dict[str, Any] = {
        "sample_id": _sample_id(epoch, f"REQ{data.get('request_id', '')}", "LONG_READ"),
        "timestamp_epoch": epoch,
        "collection_point_type": "long_read_verification",
        "collection_zone": data.get("collection_key", ""),
        "assay_type": data.get("purpose", "long_read_verification"),
        "fidelity_tier": fidelity_name,
    }
    if fidelity_name == FIDELITY_LOW:
        record["stoplight"] = "RED" if detected else "GREEN"
        record["inferred_anomaly_score"] = 1.0 if detected else 0.0
        return record

    record["binary_result"] = BINARY_DETECTED if detected else BINARY_NOT_DETECTED
    record["inferred_anomaly_score"] = 1.0 if detected else 0.0
    record["specimen_source"] = data.get("specimen_source", "")
    record["consensus_ready"] = bool(data.get("consensus_ready", False))
    record["mixed_infection_detected"] = bool(data.get("mixed_infection_flag", False))
    record["genotype_calls"] = [
        {
            "pathogen_id": call.get("pathogen_id"),
            "status": call.get("status"),
            "consensus_genotype": call.get("consensus_genotype"),
        }
        for call in genotypes
    ]
    qc = data.get("qc_control")
    record["qc_status"] = qc["qc_status"] if qc else "QC_NOT_RUN"

    if fidelity_name == FIDELITY_HIGH:
        record["read_depth"] = data.get("read_depth")
        record["total_classified_reads"] = data.get("total_classified_reads")
        record["pathogen_calls"] = calls
        record["trigger_reasons"] = data.get("trigger_reasons", [])

    return record


# ── Main notebook class ──────────────────────────────────────────────────

class ArtificialLabNotebook:
    """Accumulates diagnostic records across all instrument classes
    and serializes to JSON with tier-appropriate detail."""

    def __init__(
        self,
        fidelity: FidelityProfile | None = None,
        fidelity_name: str = FIDELITY_HIGH,
    ) -> None:
        if fidelity is None:
            _, fidelity, _ = load_logging_profile()
        self.fidelity = fidelity
        self.fidelity_name = fidelity_name
        self.records: list[dict[str, Any]] = []
        self._metadata: dict[str, Any] = {}

    def set_run_metadata(
        self,
        num_agents: int,
        num_epochs: int,
        pathogens: list[str],
        zones: list[str],
        trigger_timeline: list[dict[str, Any]] | None = None,
    ) -> None:
        self._metadata = {
            "num_agents": num_agents,
            "num_epochs": num_epochs,
            "active_pathogens": pathogens,
            "zones": zones,
            "trigger_timeline": trigger_timeline or [],
            "logging_fidelity": self.fidelity_name,
        }

    # ── Environmental instruments ────────────────────────────────────

    def log_air_sniffer(
        self,
        epoch: int,
        results: dict[str, dict[str, Any]],
    ) -> None:
        for zone_name, data in results.items():
            self.records.append(
                _air_sniffer_record(epoch, zone_name, data, self.fidelity_name, self.fidelity)
            )

    def log_surface_swab(
        self,
        epoch: int,
        results: dict[str, dict[str, Any]],
    ) -> None:
        for zone_name, data in results.items():
            self.records.append(
                _surface_swab_record(epoch, zone_name, data, self.fidelity_name, self.fidelity)
            )

    def log_wastewater_seq(
        self,
        epoch: int,
        results: dict[str, dict[str, Any]],
    ) -> None:
        for zone_name, data in results.items():
            self.records.append(
                _wastewater_record(epoch, zone_name, data, self.fidelity_name, self.fidelity)
            )

    # ── Individual patient clinical diagnostics ──────────────────────

    def log_clinical_rdt(
        self,
        epoch: int,
        results: dict[int, dict[str, Any]],
    ) -> None:
        for _aid, data in results.items():
            self.records.append(
                _clinical_rdt_record(epoch, data, self.fidelity_name, self.fidelity)
            )

    def log_clinical_qpcr(
        self,
        epoch: int,
        results: dict[int, dict[str, Any]],
    ) -> None:
        for _aid, data in results.items():
            self.records.append(
                _clinical_qpcr_record(epoch, data, self.fidelity_name, self.fidelity)
            )

    def log_clinical_microbiology(
        self,
        epoch: int,
        results: dict[int, dict[str, Any]],
    ) -> None:
        for _aid, data in results.items():
            self.records.append(
                _clinical_microbio_record(epoch, data, self.fidelity_name, self.fidelity)
            )

    def log_long_read_verification(
        self,
        epoch: int,
        results: dict[str, dict[str, Any]],
    ) -> None:
        for _req_id, data in results.items():
            self.records.append(
                _long_read_record(epoch, data, self.fidelity_name, self.fidelity)
            )

    # ── System events ────────────────────────────────────────────────

    def log_trigger_transition(
        self,
        epoch: int,
        prev_status: str,
        new_status: str,
    ) -> None:
        record: dict[str, Any] = {
            "sample_id": _sample_id(epoch, "SYSTEM", "ESCALATION"),
            "timestamp_epoch": epoch,
            "collection_point_type": "system_escalation",
            "collection_zone": "ALL",
            "assay_type": "trigger_transition",
            "fidelity_tier": self.fidelity_name,
        }

        if self.fidelity_name == FIDELITY_LOW:
            record["stoplight"] = "RED" if new_status == "CONFIRMED" else "AMBER"
            record["inferred_anomaly_score"] = 1.0 if new_status == "CONFIRMED" else 0.5
        else:
            record["binary_result"] = new_status
            record["raw_metric_output"] = f"{prev_status} -> {new_status}"
            record["inferred_anomaly_score"] = 1.0 if new_status == "CONFIRMED" else 0.5

        self.records.append(record)

    def log_agent_summary(
        self,
        epoch: int,
        agents: list[dict[str, Any]],
    ) -> None:
        if not self.fidelity.log_microflora_variance:
            return
        for ag in agents:
            disruption = ag.get("microflora_disruption", 0.0)
            if disruption <= 0:
                continue
            aid = ag.get("agent_id", -1)
            record: dict[str, Any] = {
                "sample_id": _sample_id(epoch, f"AGENT{aid}", "MICROFLORA"),
                "timestamp_epoch": epoch,
                "collection_point_type": "host_biomarker",
                "collection_zone": ag.get("location", "unknown"),
                "assay_type": "microflora_disruption_status",
                "fidelity_tier": self.fidelity_name,
            }

            if self.fidelity_name == FIDELITY_LOW:
                record["stoplight"] = _stoplight_from_disruption(disruption)
                record["inferred_anomaly_score"] = round(min(1.0, disruption), 4)
            else:
                record["binary_result"] = "DISRUPTED"
                record["raw_metric_output"] = round(disruption, 4)
                record["inferred_anomaly_score"] = round(min(1.0, disruption), 4)
                record["patient_id"] = aid
                record["pathogen_infections"] = ag.get("pathogen_infections", {})
                record["susceptibility_multiplier"] = ag.get("susceptibility_multiplier", {})

            self.records.append(record)

    def serialize(
        self,
        output_path: str,
        financial_audit: dict[str, Any] | None = None,
        protocol_summary: dict[str, Any] | None = None,
    ) -> str:
        notebook: dict[str, Any] = {
            "notebook_type": "artificial_lab_notebook",
            "version": "3.0",
            "run_metadata": self._metadata,
            "total_records": len(self.records),
            "fidelity_tier_definitions": {
                "HIGH_FIDELITY": "Raw Synthetic Instrument — cycle-by-cycle curves, raw fluorescence, pre-norm reads",
                "MID_FIDELITY": "Certified Clinical — CAP-style reports, DETECTED/NOT DETECTED, QC flags",
                "LOW_FIDELITY": "Command/Strategic — GREEN/AMBER/RED stoplight indicators",
            },
            "records": self.records,
        }

        if financial_audit is not None:
            notebook["FINANCIAL_AUDIT"] = financial_audit

        if protocol_summary is not None:
            notebook["PROTOCOL_SUMMARY"] = protocol_summary

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_path = resolve_repo_path(repo_root, output_path)
        prepare_output_directory(
            os.path.dirname(output_path),
            allowed_roots=(repo_root,),
        )
        with validated_open(output_path, "w", allowed_roots=(repo_root,), encoding="utf-8") as fh:
            json.dump(notebook, fh, indent=2, default=str)

        return os.path.abspath(output_path)


def build_notebook_from_config(
    logging_profile_path: str | None = None,
) -> ArtificialLabNotebook:
    fidelity_name, fidelity, _ = load_logging_profile(logging_profile_path)
    return ArtificialLabNotebook(
        fidelity=fidelity,
        fidelity_name=fidelity_name,
    )
