"""
crusher_labs.modalities.long_read_sequencing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Oxford Nanopore long-read verification / pathogen-typing modality (framework).

Intended for follow-on use when short-read or rapid assays suggest mixed
infections, unexpected organisms, or discordant signals. Accepts upstream
instrument snapshots; detailed basecalling and classification parameters
are configured outside this stub.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
    """Framework modality — no fitted sequencing parameters in-repo."""

    name = "long_read_nanopore"

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def verify(self, request: LongReadVerificationRequest) -> dict[str, Any]:
        """Run verification/typing pass (stub until parameters are supplied)."""
        return {
            "modality": self.name,
            "instrument": "long_read_verification",
            "status": "framework_stub",
            "request_id": request.request_id,
            "specimen_source": request.specimen_source,
            "collection_key": request.collection_key,
            "purpose": (
                PURPOSE_PATHOGEN_TYPING
                if "mixed_infection_suspected" in request.trigger_reasons
                else PURPOSE_VERIFICATION
            ),
            "trigger_reasons": list(request.trigger_reasons),
            "upstream_instrument": request.upstream_instrument,
            "pathogen_calls": [],
            "consensus_ready": False,
            "mixed_infection_flag": "mixed_infection_suspected" in request.trigger_reasons,
            "unexpected_pathogen_flag": "unexpected_pathogen" in request.trigger_reasons,
            "discordant_modalities_flag": "discordant_modalities" in request.trigger_reasons,
            "notes": "Awaiting external long-read parameterization and classifier.",
        }
