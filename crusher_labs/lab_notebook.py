"""
crusher_labs.lab_notebook
~~~~~~~~~~~~~~~~~~~~~~~~~

Artificial Lab Notebook serializer.

Produces a standardized, machine-readable diagnostic report structured
as a flat array of sample records suitable for ingestion by external
corporate, fleet, or CDC-level biosurveillance portals.

Each record follows a public-health-report schema:
  - sample_id:              UUID-style identifier
  - timestamp_epoch:        Simulation epoch (integer)
  - collection_point_type:  Instrument/modality type
  - collection_zone:        Spatial zone name
  - assay_type:             Specific assay performed
  - raw_metric_output:      Primary quantitative result
  - inferred_anomaly_score: Computed anomaly probability [0..1]
  - additional fields depending on fidelity level

The fidelity level controls how much detail each record contains.
"""

from __future__ import annotations

import json
import os
import hashlib
from typing import Any


# ── Fidelity filters ─────────────────────────────────────────────────────

class FidelityProfile:
    """Parsed fidelity configuration from logging_profile.json."""

    def __init__(self, profile_dict: dict[str, Any]) -> None:
        self.log_binary = profile_dict.get("log_binary_states", True)
        self.log_numeric = profile_dict.get("log_numeric_outputs", False)
        self.log_raw = profile_dict.get("log_raw_matrices", False)
        self.log_microflora_variance = profile_dict.get("log_host_microflora_variance", False)
        self.log_contact_tracing = profile_dict.get("log_contact_tracing", False)


def load_logging_profile(
    cfg_path: str | None = None,
) -> tuple[str, FidelityProfile, dict[str, Any]]:
    """Load the logging profile configuration.

    Returns (fidelity_name, FidelityProfile, full_config).
    """
    if cfg_path is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg_path = os.path.join(repo_root, "data", "config", "logging_profile.json")

    if not os.path.isfile(cfg_path):
        # Default to HIGH_FIDELITY
        return "HIGH_FIDELITY", FidelityProfile({
            "log_binary_states": True,
            "log_numeric_outputs": True,
            "log_raw_matrices": True,
            "log_host_microflora_variance": True,
            "log_contact_tracing": True,
        }), {}

    with open(cfg_path, "r", encoding="utf-8") as fh:
        config = json.load(fh)

    fidelity_name = config.get("logging_fidelity", "HIGH_FIDELITY")
    levels = config.get("fidelity_levels", {})
    profile_dict = levels.get(fidelity_name, {})

    return fidelity_name, FidelityProfile(profile_dict), config


def _sample_id(epoch: int, zone: str, assay: str) -> str:
    """Generate a deterministic sample identifier."""
    raw = f"E{epoch:03d}_{zone}_{assay}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:8]
    return f"CLN-{epoch:03d}-{zone[:6].upper()}-{assay[:4].upper()}-{h}"


# ── Record builders ──────────────────────────────────────────────────────

def _air_sniffer_record(
    epoch: int,
    zone: str,
    data: dict[str, Any],
    fidelity: FidelityProfile,
) -> dict[str, Any]:
    """Build a lab notebook record from air sniffer output."""
    detected = data.get("detected", False)
    ct = data.get("ct_value")

    # Anomaly score: based on Ct distance from LOD
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
        "binary_result": "POSITIVE" if detected else "NEGATIVE",
        "inferred_anomaly_score": anomaly,
    }

    if fidelity.log_numeric:
        record["raw_metric_output"] = ct
        record["captured_mass"] = data.get("captured_mass")
        record["concentration_per_m3"] = data.get("concentration_per_m3")
        record["sampled_volume_m3"] = data.get("sampled_volume_m3")

    return record


def _surface_swab_record(
    epoch: int,
    zone: str,
    data: dict[str, Any],
    fidelity: FidelityProfile,
) -> dict[str, Any]:
    """Build a lab notebook record from surface swab output."""
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
        "binary_result": "POSITIVE" if detected else "NEGATIVE",
        "inferred_anomaly_score": anomaly,
    }

    if fidelity.log_numeric:
        record["raw_metric_output"] = ct
        record["recovered_mass"] = data.get("recovered_mass")
        record["collection_efficiency"] = data.get("actual_collection_efficiency")
        record["technique_quality"] = data.get("technique_quality")
        record["compliance_scalar"] = data.get("compliance_scalar")

    return record


def _wastewater_record(
    epoch: int,
    zone: str,
    data: dict[str, Any],
    fidelity: FidelityProfile,
) -> dict[str, Any]:
    """Build a lab notebook record from wastewater sequencing output."""
    anomaly_detected = data.get("anomaly_detected", False)
    pathogen_reads = data.get("total_pathogen_reads", 0)
    read_depth = data.get("read_depth", 50000)

    # Anomaly score: combined pathogen fraction + kingdom shift
    pathogen_frac = pathogen_reads / max(read_depth, 1)
    kingdom_shift = sum(
        abs(d) for d in data.get("kingdom_clr_deltas", {}).values()
    )
    anomaly = round(min(1.0, pathogen_frac * 10 + kingdom_shift * 2), 4)

    record: dict[str, Any] = {
        "sample_id": _sample_id(epoch, zone, "WASTEWATER_SEQ"),
        "timestamp_epoch": epoch,
        "collection_point_type": "wastewater_sequencing_grid",
        "collection_zone": zone,
        "assay_type": "metagenomic_sequencing",
        "binary_result": "ANOMALY" if anomaly_detected else "NORMAL",
        "inferred_anomaly_score": anomaly,
    }

    if fidelity.log_numeric:
        record["raw_metric_output"] = pathogen_reads
        record["read_depth"] = read_depth
        record["pathogen_fraction"] = round(pathogen_frac, 6)
        record["disruption_types"] = data.get("disruption_types", [])

    if fidelity.log_raw:
        record["read_counts"] = data.get("read_counts", {})
        record["kingdom_reads"] = data.get("kingdom_reads", {})
        record["kingdom_clr_deltas"] = data.get("kingdom_clr_deltas", {})
        record["dirichlet_concentration"] = data.get("dirichlet_concentration")

    return record


# ── Main notebook class ──────────────────────────────────────────────────

class ArtificialLabNotebook:
    """Accumulates diagnostic records and serializes to JSON.

    The notebook is an ordered list of flat, standardized records
    suitable for ingestion by external biosurveillance systems.
    """

    def __init__(
        self,
        fidelity: FidelityProfile | None = None,
        fidelity_name: str = "HIGH_FIDELITY",
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
        """Capture run-level metadata for the notebook header."""
        self._metadata = {
            "num_agents": num_agents,
            "num_epochs": num_epochs,
            "active_pathogens": pathogens,
            "zones": zones,
            "trigger_timeline": trigger_timeline or [],
            "logging_fidelity": self.fidelity_name,
        }

    def log_air_sniffer(
        self,
        epoch: int,
        results: dict[str, dict[str, Any]],
    ) -> None:
        """Log air sniffer results for all zones at an epoch."""
        for zone_name, data in results.items():
            self.records.append(
                _air_sniffer_record(epoch, zone_name, data, self.fidelity)
            )

    def log_surface_swab(
        self,
        epoch: int,
        results: dict[str, dict[str, Any]],
    ) -> None:
        """Log surface swab results for all zones at an epoch."""
        for zone_name, data in results.items():
            self.records.append(
                _surface_swab_record(epoch, zone_name, data, self.fidelity)
            )

    def log_wastewater_seq(
        self,
        epoch: int,
        results: dict[str, dict[str, Any]],
    ) -> None:
        """Log wastewater sequencing results for all zones at an epoch."""
        for zone_name, data in results.items():
            self.records.append(
                _wastewater_record(epoch, zone_name, data, self.fidelity)
            )

    def log_trigger_transition(
        self,
        epoch: int,
        prev_status: str,
        new_status: str,
    ) -> None:
        """Log escalation trigger transitions."""
        self.records.append({
            "sample_id": _sample_id(epoch, "SYSTEM", "ESCALATION"),
            "timestamp_epoch": epoch,
            "collection_point_type": "system_escalation",
            "collection_zone": "ALL",
            "assay_type": "trigger_transition",
            "binary_result": new_status,
            "raw_metric_output": f"{prev_status} -> {new_status}",
            "inferred_anomaly_score": 1.0 if new_status == "CONFIRMED" else 0.5,
        })

    def log_agent_summary(
        self,
        epoch: int,
        agents: list[dict[str, Any]],
    ) -> None:
        """Log per-agent microflora variance if HIGH_FIDELITY."""
        if not self.fidelity.log_microflora_variance:
            return
        for ag in agents:
            disruption = ag.get("microflora_disruption", 0.0)
            if disruption <= 0:
                continue
            self.records.append({
                "sample_id": _sample_id(epoch, f"AGENT{ag['agent_id']}", "MICROFLORA"),
                "timestamp_epoch": epoch,
                "collection_point_type": "host_biomarker",
                "collection_zone": ag.get("location", "unknown"),
                "assay_type": "microflora_disruption_status",
                "binary_result": "DISRUPTED",
                "raw_metric_output": round(disruption, 4),
                "inferred_anomaly_score": round(min(1.0, disruption), 4),
                "agent_id": ag.get("agent_id"),
                "pathogen_infections": ag.get("pathogen_infections", {}),
                "susceptibility_multiplier": ag.get("susceptibility_multiplier", {}),
            })

    def serialize(self, output_path: str) -> str:
        """Write the notebook to JSON and return the absolute path."""
        notebook = {
            "notebook_type": "artificial_lab_notebook",
            "version": "1.0",
            "run_metadata": self._metadata,
            "total_records": len(self.records),
            "records": self.records,
        }

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(notebook, fh, indent=2, default=str)

        return os.path.abspath(output_path)


def build_notebook_from_config(
    logging_profile_path: str | None = None,
) -> ArtificialLabNotebook:
    """Factory: build a notebook instance from the logging profile config."""
    fidelity_name, fidelity, config = load_logging_profile(logging_profile_path)
    return ArtificialLabNotebook(
        fidelity=fidelity,
        fidelity_name=fidelity_name,
    )
