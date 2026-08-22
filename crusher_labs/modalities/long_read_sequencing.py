"""
crusher_labs.modalities.long_read_sequencing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Oxford Nanopore long-read verification / pathogen-typing modality.

Loads assay parameters from ``data/config/long_read_sequencing_params.json``,
samples compositional read counts from ground-truth pathogen mass, applies
configured error injection, and returns pathogen classification calls.

When the caller supplies the genotype mixture a clinical specimen actually
contains, the same run also produces amplicon genotype calls through
:class:`crusher_labs.modalities.clinical_strain_typing.ClinicalStrainTyping`
(variant surveillance, Paper 3): pathogen-level calls say *what*, genotype
calls say *which lineage*, and the latter can be wrong rather than merely
absent.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from crusher_labs.modalities.clinical_strain_typing import ClinicalStrainTyping
from crusher_labs.modalities.sequencing import MULTI_KINGDOM_TAXA
from simulation_utils.numeric import default_simulation_rng
from simulation_utils.paths import resolve_repo_path, validated_open

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Specimen channels this modality can consume
SPECIMEN_WASTEWATER_METAGENOMICS = "wastewater_metagenomics"
SPECIMEN_CLINICAL = "clinical_specimen"
SPECIMEN_CLINICAL_CULTURE = "clinical_culture"
SPECIMEN_SURVEILLANCE_SWAB = "surveillance_swab"

ALL_SPECIMEN_SOURCES: tuple[str, ...] = (
    SPECIMEN_WASTEWATER_METAGENOMICS,
    SPECIMEN_CLINICAL,
    SPECIMEN_CLINICAL_CULTURE,
    SPECIMEN_SURVEILLANCE_SWAB,
)

PURPOSE_VERIFICATION = "verification"
PURPOSE_PATHOGEN_TYPING = "pathogen_typing"

_HOST_SCALE_WW = 1000.0
_HOST_SCALE_CLINICAL = 100.0
_HOST_SCALE_SWAB = 500.0


@dataclass(frozen=True)
class LongReadVerificationRequest:
    """Escalation request routed to Nanopore long-read workflow."""

    request_id: str
    specimen_source: str
    collection_key: str
    trigger_reasons: list[str] = field(default_factory=list)
    upstream_instrument: str = ""
    upstream_snapshot: dict[str, Any] = field(default_factory=dict)


class LongReadNanoporeSequencing:
    """Oxford Nanopore long-read verification with config-driven detection."""

    name = "long_read_nanopore"

    def __init__(
        self,
        params: dict[str, Any],
        profile_name: str,
        *,
        enabled: bool = True,
        rng: np.random.Generator | None = None,
        strain_typing: ClinicalStrainTyping | None = None,
    ) -> None:
        self.enabled = enabled
        self.strain_typing = strain_typing
        self.params = params
        self.profile_name = profile_name
        self.rng = rng if rng is not None else default_simulation_rng()

        profiles = params.get("deployment_profiles", {})
        if profile_name not in profiles:
            raise ValueError(f"Unknown long-read profile: {profile_name}")
        self.profile = profiles[profile_name]
        self.sim_params = params.get("simulation_parameters", {})
        self.detection_model = self.sim_params.get("detection_model", {})
        self.specimen_processing = params.get("specimen_processing", {})

    @classmethod
    def from_params_path(
        cls,
        path: str,
        profile_name: str | None = None,
        *,
        enabled: bool = True,
        rng: np.random.Generator | None = None,
        repo_root: str | None = None,
        strain_typing: ClinicalStrainTyping | None = None,
    ) -> LongReadNanoporeSequencing:
        root = repo_root or REPO_ROOT
        path = resolve_repo_path(root, path)
        with validated_open(path, "r", allowed_roots=(root,), encoding="utf-8") as fh:
            params = json.load(fh)
        sim = params.get("simulation_parameters", {})
        profile = profile_name or sim.get("default_profile", "flongle_rapid")
        return cls(
            params, profile, enabled=enabled, rng=rng, strain_typing=strain_typing,
        )

    @property
    def turnaround(self) -> dict[str, Any]:
        return dict(self.profile.get("turnaround", {}))

    def profile_turnaround_delay_epochs(self, hours_per_epoch: float = 24.0) -> int:
        from crusher_labs.instrument_turnaround import TurnaroundSpec

        return TurnaroundSpec.from_profile_turnaround(
            self.turnaround,
            hours_per_epoch=hours_per_epoch,
        ).delay_epochs

    def _background_taxa(self) -> tuple[list[str], np.ndarray]:
        taxa: list[str] = []
        abund: list[float] = []
        for _kingdom, taxa_dict in MULTI_KINGDOM_TAXA.items():
            for taxon, base in taxa_dict.items():
                taxa.append(taxon)
                abund.append(base)
        arr = np.array(abund, dtype=np.float64)
        arr /= arr.sum()
        return taxa, arr

    def _zone_pathogen_masses(
        self,
        zone: dict[str, Any],
        extraction: float,
    ) -> dict[str, float]:
        pathogen_masses: dict[str, float] = {}
        by_id = zone.get("pathogen_mass_by_id", {}) or {}
        for pid, mass in by_id.items():
            if mass > 0:
                pathogen_masses[str(pid)] = float(mass) * extraction
        if not pathogen_masses:
            pm = float(zone.get("pathogen_mass", 0.0))
            if pm > 0:
                pathogen_masses["target"] = pm * extraction
        return pathogen_masses

    def _clinical_pathogen_masses(
        self,
        request: LongReadVerificationRequest,
        agents: list[dict[str, Any]],
        pathogen_profiles: dict[str, dict[str, Any]],
        proc: dict[str, Any],
        specimen: str,
    ) -> dict[str, float]:
        pathogen_masses: dict[str, float] = {}
        try:
            aid = int(request.collection_key)
        except ValueError:
            aid = None
        agent_data: dict[str, Any] = {}
        if aid is not None:
            for ag in agents:
                if ag.get("agent_id") == aid:
                    agent_data = ag
                    break
        shedding = float(agent_data.get("shedding_rate", 0.0))
        infections = agent_data.get("pathogen_infections", {}) or {}
        eff = float(proc.get("extraction_efficiency", 0.4))
        if specimen == SPECIMEN_CLINICAL_CULTURE:
            eff *= float(proc.get("extraction_efficiency", 0.7))
        for pid, inf in infections.items():
            status = inf.get("status", "") if isinstance(inf, dict) else ""
            if status == "INFECTED" or pid in pathogen_profiles:
                pathogen_masses[str(pid)] = max(
                    pathogen_masses.get(str(pid), 0.0),
                    shedding * eff,
                )
        if shedding > 0 and not pathogen_masses:
            pathogen_masses["target"] = shedding * eff
        return pathogen_masses

    def _pathogen_fractions(
        self,
        request: LongReadVerificationRequest,
        *,
        spaces: dict[str, dict[str, Any]],
        agents: list[dict[str, Any]],
        pathogen_profiles: dict[str, dict[str, Any]],
    ) -> tuple[list[str], np.ndarray]:
        """Build taxon list and composition vector on the simplex."""
        bg_taxa, bg_comp = self._background_taxa()
        specimen = request.specimen_source
        proc = self.specimen_processing.get(specimen, {})
        extraction = float(proc.get("extraction_efficiency", 0.4))

        pathogen_masses: dict[str, float] = {}
        host_scale = _HOST_SCALE_WW

        if specimen == SPECIMEN_WASTEWATER_METAGENOMICS:
            pathogen_masses = self._zone_pathogen_masses(
                spaces.get(request.collection_key, {}), extraction,
            )

        elif specimen == SPECIMEN_SURVEILLANCE_SWAB:
            host_scale = _HOST_SCALE_SWAB
            pathogen_masses = self._zone_pathogen_masses(
                spaces.get(request.collection_key, {}), extraction,
            )

        elif specimen in (SPECIMEN_CLINICAL, SPECIMEN_CLINICAL_CULTURE):
            host_scale = _HOST_SCALE_CLINICAL
            pathogen_masses = self._clinical_pathogen_masses(
                request, agents, pathogen_profiles, proc, specimen,
            )

        total_pathogen = sum(pathogen_masses.values())
        pathogen_frac = total_pathogen / (total_pathogen + host_scale)
        env_frac = 1.0 - pathogen_frac

        taxa = list(bg_taxa)
        composition = bg_comp * env_frac

        for pid, pmass in pathogen_masses.items():
            taxon_name = f"Pathogen_{pid}"
            pf = pmass / (total_pathogen + host_scale) if total_pathogen > 0 else 0.0
            if pf <= 0:
                continue
            taxa.append(taxon_name)
            composition = np.append(composition, pf)

        composition = np.clip(composition, 1e-12, None)
        composition /= composition.sum()
        return taxa, composition

    def _misallocation_rate(self, err_cfg: dict[str, Any]) -> float:
        sub = float(err_cfg.get("substitution_rate", 0.02))
        ins = float(err_cfg.get("insertion_rate", 0.015))
        dele = float(err_cfg.get("deletion_rate", 0.015))
        homo = float(err_cfg.get("homopolymer_collapse_prob", 0.08))
        return min(0.5, sub + ins + dele + homo)

    def _apply_read_misallocations(
        self,
        read_dict: dict[str, int],
        taxa: list[str],
        misrate: float,
    ) -> None:
        n_taxa = len(taxa)
        for i, taxon in enumerate(taxa):
            count = read_dict.get(taxon, 0)
            if count <= 0:
                continue
            for _ in range(count):
                if self.rng.random() < misrate and n_taxa > 1:
                    j = int(self.rng.integers(0, n_taxa))
                    if j != i:
                        read_dict[taxon] = read_dict.get(taxon, 0) - 1
                        other = taxa[j]
                        read_dict[other] = read_dict.get(other, 0) + 1

    def _inject_errors(
        self,
        taxa: list[str],
        reads: np.ndarray,
    ) -> dict[str, int]:
        err_cfg = self.detection_model.get("error_injection", {})
        if not err_cfg.get("enabled", True):
            return {t: int(c) for t, c in zip(taxa, reads) if c > 0}

        misrate = self._misallocation_rate(err_cfg)
        read_dict = {t: int(c) for t, c in zip(taxa, reads)}
        total = int(reads.sum())
        if total <= 0 or misrate <= 0:
            return read_dict

        self._apply_read_misallocations(read_dict, taxa, misrate)
        return {t: c for t, c in read_dict.items() if c > 0}

    def _classify_calls(
        self,
        read_dict: dict[str, int],
        total_reads: int,
    ) -> list[dict[str, Any]]:
        det = self.profile.get("detection", {})
        min_frac = float(det.get("min_fraction_for_detection", 1e-4))
        min_reads_call = int(
            self.detection_model.get("classification", {}).get("min_reads_for_call", 5),
        )
        species_sens = float(
            self.detection_model.get("classification", {}).get(
                "species_sensitivity",
                det.get("species_classification_accuracy", 0.96),
            ),
        )

        calls: list[dict[str, Any]] = []
        for taxon, count in read_dict.items():
            if not taxon.startswith("Pathogen_"):
                continue
            frac = count / max(total_reads, 1)
            if frac < min_frac or count < min_reads_call:
                continue
            if self.rng.random() > species_sens:
                continue
            pid = taxon.replace("Pathogen_", "", 1)
            prof = {}  # optional name lookup omitted; taxon_id sufficient
            calls.append({
                "taxon_id": pid,
                "taxon_name": prof.get("name", pid) if prof else pid,
                "rank": "species",
                "classified_reads": count,
                "fraction_total": round(frac, 8),
                "confidence": round(min(0.99, species_sens * (1.0 + frac * 10)), 4),
                "amr_genes_detected": [],
            })

        calls.sort(key=lambda c: c["classified_reads"], reverse=True)
        max_org = int(
            self.sim_params.get("verification_outputs", {})
            .get("mixed_infection_report", {})
            .get("max_organisms_reportable", 5),
        )
        return calls[:max_org]

    def _genotype_calls(
        self,
        request: LongReadVerificationRequest,
        *,
        agents: list[dict[str, Any]],
        pathogen_profiles: dict[str, dict[str, Any]],
        genotype_mixtures: dict[str, dict[str, float]] | None,
        epoch: int,
        typing_read_depth: int | None,
    ) -> list[dict[str, Any]]:
        """Amplicon typing results for a clinical specimen, one per pathogen.

        Empty unless a typing assay is configured and the caller passed the
        specimen's genotype truth; the amplicon Ct gate is fed by the same
        clinical specimen mass the metagenomic pass uses, so a specimen too
        dilute to sequence is too dilute to type.
        """
        if self.strain_typing is None or not genotype_mixtures:
            return []
        if request.specimen_source not in (SPECIMEN_CLINICAL, SPECIMEN_CLINICAL_CULTURE):
            return []
        proc = self.specimen_processing.get(request.specimen_source, {})
        masses = self._clinical_pathogen_masses(
            request, agents, pathogen_profiles, proc, request.specimen_source,
        )
        try:
            agent_id = int(request.collection_key)
        except ValueError:
            agent_id = -1
        calls: list[dict[str, Any]] = []
        for pid, mixture in genotype_mixtures.items():
            calls.append(self.strain_typing.type_specimen(
                agent_id,
                str(pid),
                masses.get(str(pid), masses.get("target", 0.0)),
                mixture,
                epoch=epoch,
                read_depth=typing_read_depth,
            ))
        return calls

    def verify(
        self,
        request: LongReadVerificationRequest,
        *,
        epoch: int = 0,
        spaces: dict[str, dict[str, Any]] | None = None,
        agents: list[dict[str, Any]] | None = None,
        pathogen_profiles: dict[str, dict[str, Any]] | None = None,
        genotype_mixtures: dict[str, dict[str, float]] | None = None,
        typing_read_depth: int | None = None,
    ) -> dict[str, Any]:
        """Run verification/typing pass from ground-truth specimen composition.

        ``genotype_mixtures`` maps pathogen id to the genotype composition the
        specimen actually carries (see
        :func:`crusher_labs.modalities.clinical_strain_typing.specimen_genotype_mixture`).
        Supplying it adds ``genotype_calls`` to the result; omitting it leaves
        the pathogen-level behaviour exactly as before.
        """
        spaces = spaces or {}
        agents = agents or []
        pathogen_profiles = pathogen_profiles or {}

        purpose = (
            PURPOSE_PATHOGEN_TYPING
            if "mixed_infection_suspected" in request.trigger_reasons
            else PURPOSE_VERIFICATION
        )

        if not self.enabled:
            return {
                "modality": self.name,
                "instrument": "long_read_verification",
                "status": "disabled",
                "request_id": request.request_id,
                "specimen_source": request.specimen_source,
                "collection_key": request.collection_key,
                "purpose": purpose,
                "pathogen_calls": [],
                "consensus_ready": False,
            }

        throughput = self.profile.get("throughput", {})
        read_depth = int(
            throughput.get("total_reads")
            or self.detection_model.get("read_depth", 500_000),
        )

        taxa, composition = self._pathogen_fractions(
            request,
            spaces=spaces,
            agents=agents,
            pathogen_profiles=pathogen_profiles,
        )
        reads = self.rng.multinomial(read_depth, composition)
        read_dict = self._inject_errors(taxa, reads)
        total_reads = sum(read_dict.values())
        pathogen_calls = self._classify_calls(read_dict, total_reads)

        genotype_calls = self._genotype_calls(
            request,
            agents=agents,
            pathogen_profiles=pathogen_profiles,
            genotype_mixtures=genotype_mixtures,
            epoch=epoch,
            typing_read_depth=typing_read_depth,
        )

        det = self.profile.get("detection", {})
        reads_strain = int(det.get("reads_for_strain_typing", 10_000))
        top_reads = pathogen_calls[0]["classified_reads"] if pathogen_calls else 0
        consensus_ready = top_reads >= reads_strain

        return {
            "modality": self.name,
            "instrument": "long_read_verification",
            "status": "complete",
            "profile": self.profile_name,
            "epoch": epoch,
            "request_id": request.request_id,
            "specimen_source": request.specimen_source,
            "collection_key": request.collection_key,
            "purpose": purpose,
            "trigger_reasons": list(request.trigger_reasons),
            "upstream_instrument": request.upstream_instrument,
            "read_depth": read_depth,
            "total_classified_reads": total_reads,
            "read_counts": read_dict,
            "pathogen_calls": pathogen_calls,
            "genotype_calls": genotype_calls,
            "consensus_ready": consensus_ready,
            "mixed_infection_flag": (
                "mixed_infection_suspected" in request.trigger_reasons
                or len(pathogen_calls) > 1
            ),
            "unexpected_pathogen_flag": "unexpected_pathogen" in request.trigger_reasons,
            "discordant_modalities_flag": "discordant_modalities" in request.trigger_reasons,
            "notes": "",
        }
