"""Phylodynamic observables for Paper 3 (Cruise Ships as Phylogenomic Observatories).

Truth from the lineage census, observation from the sentinel bundle, and every
observable reported per physical hour.
"""

from __future__ import annotations

from picard_framework.analysis.phylodynamics.artifact import (
    LINEAGE_CENSUS_SCHEMA_VERSION,
    CensusArtifact,
    CensusEpoch,
    LineageCensusError,
    StrainMeta,
    census_from_dict,
)
from picard_framework.analysis.phylodynamics.compare import (
    channel_information_summary,
    channel_summaries,
    information_rows,
    observed_composition,
    truth_composition,
)
from picard_framework.analysis.phylodynamics.detection import (
    CHANNEL_CLINICAL,
    CHANNEL_WASTEWATER,
    DETECTION_COLUMNS,
    DetectionRow,
    detection_rows,
    detection_speed_curve,
    detection_summary,
    genotype_emergence_hours,
)
from picard_framework.analysis.phylodynamics.diversity import (
    DIVERSITY_COLUMNS,
    DiversityRow,
    all_diversity_rows,
    bray_curtis_turnover,
    diversity_rows,
    diversity_summary,
    effective_lineages,
    shannon_bits,
)
from picard_framework.analysis.phylodynamics.information import (
    INFORMATION_COLUMNS,
    InformationRow,
    completeness,
    entropy_bits,
    information_gain_bits,
    js_distance,
)
from picard_framework.analysis.phylodynamics.report import (
    MissingCensusError,
    build_report,
    load_bundle,
    load_census,
    write_report,
)

__all__ = [
    "CHANNEL_CLINICAL",
    "CHANNEL_WASTEWATER",
    "DETECTION_COLUMNS",
    "DIVERSITY_COLUMNS",
    "INFORMATION_COLUMNS",
    "LINEAGE_CENSUS_SCHEMA_VERSION",
    "CensusArtifact",
    "CensusEpoch",
    "DetectionRow",
    "DiversityRow",
    "InformationRow",
    "LineageCensusError",
    "MissingCensusError",
    "StrainMeta",
    "all_diversity_rows",
    "bray_curtis_turnover",
    "build_report",
    "census_from_dict",
    "channel_information_summary",
    "channel_summaries",
    "completeness",
    "detection_rows",
    "detection_speed_curve",
    "detection_summary",
    "diversity_rows",
    "diversity_summary",
    "effective_lineages",
    "entropy_bits",
    "genotype_emergence_hours",
    "information_gain_bits",
    "information_rows",
    "js_distance",
    "load_bundle",
    "load_census",
    "observed_composition",
    "shannon_bits",
    "truth_composition",
    "write_report",
]
