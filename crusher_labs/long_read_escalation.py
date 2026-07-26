"""
crusher_labs.long_read_escalation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Heuristic escalation hooks that queue Oxford Nanopore long-read verification
when routine modalities raise mixed-infection, discordant, or ambiguous signals.

Trigger toggles live in ``config.yaml`` under ``long_read_sequencing``.
Assay physics and detection live in ``long_read_sequencing_params.json`` and
``crusher_labs.modalities.long_read_sequencing``. Escalation reads **delivered**
upstream instrument results (after instrument TAT), not same-epoch raw samples.
"""

from __future__ import annotations

from typing import Any

from crusher_labs.modalities.long_read_sequencing import (
    SPECIMEN_CLINICAL,
    SPECIMEN_CLINICAL_CULTURE,
    SPECIMEN_SURVEILLANCE_SWAB,
    SPECIMEN_WASTEWATER_METAGENOMICS,
    LongReadVerificationRequest,
)

_VALID_SOURCES = frozenset({
    SPECIMEN_WASTEWATER_METAGENOMICS,
    SPECIMEN_CLINICAL,
    SPECIMEN_CLINICAL_CULTURE,
    SPECIMEN_SURVEILLANCE_SWAB,
})


def long_read_config(cfg: dict[str, Any]) -> dict[str, Any]:
    return cfg.get("long_read_sequencing", {})


def is_long_read_enabled(cfg: dict[str, Any]) -> bool:
    lr = long_read_config(cfg)
    return bool(lr.get("enabled", False))


def allowed_specimen_sources(cfg: dict[str, Any]) -> set[str]:
    lr = long_read_config(cfg)
    raw = lr.get("specimen_sources", list(_VALID_SOURCES))
    if not isinstance(raw, list):
        return set(_VALID_SOURCES)
    return {s for s in raw if s in _VALID_SOURCES} or set(_VALID_SOURCES)


def _triggers(cfg: dict[str, Any]) -> dict[str, bool]:
    t = long_read_config(cfg).get("escalation_triggers", {})
    return {
        "mixed_infection_suspected": bool(t.get("mixed_infection_suspected", True)),
        "unexpected_pathogen": bool(t.get("unexpected_pathogen", True)),
        "discordant_modalities": bool(t.get("discordant_modalities", True)),
        "special_circumstance": bool(t.get("special_circumstance", False)),
    }


def _ww_pathogen_ids(ww_data: dict[str, Any]) -> list[str]:
    reads = ww_data.get("read_counts", {}) or {}
    return [
        k for k in reads
        if k.startswith("Pathogen_") and reads.get(k, 0) > 0
    ]


def _collect_mixed_infection_requests(
    add: Any,
    ww_results: dict[str, dict[str, Any]],
) -> None:
    for zone, data in ww_results.items():
        if len(_ww_pathogen_ids(data)) > 1:
            add(
                SPECIMEN_WASTEWATER_METAGENOMICS,
                zone,
                ["mixed_infection_suspected"],
                "wastewater_sequencing",
                data,
            )


def _collect_unexpected_ww_requests(
    add: Any,
    ww_results: dict[str, dict[str, Any]],
) -> None:
    for zone, data in ww_results.items():
        if data.get("anomaly_detected") and data.get("total_pathogen_reads", 0) == 0:
            add(
                SPECIMEN_WASTEWATER_METAGENOMICS,
                zone,
                ["unexpected_pathogen"],
                "wastewater_sequencing",
                data,
            )


def _collect_discordant_clinical_requests(
    add: Any,
    clin_rdt_results: dict[int, dict[str, Any]],
    clin_qpcr_results: dict[int, dict[str, Any]],
) -> None:
    for aid in set(clin_rdt_results) | set(clin_qpcr_results):
        rdt = clin_rdt_results.get(aid, {})
        qpcr = clin_qpcr_results.get(aid, {})
        if bool(rdt.get("positive", False)) != bool(qpcr.get("detected", False)):
            add(
                SPECIMEN_CLINICAL,
                str(aid),
                ["discordant_modalities"],
                "clinical_rdt/clinical_qpcr",
                {"rdt": rdt, "qpcr": qpcr},
            )


def _collect_microbio_discordance_requests(
    add: Any,
    clin_microbio_results: dict[int, dict[str, Any]],
) -> None:
    for aid, data in clin_microbio_results.items():
        if data.get("secondary_infection_detected") or data.get("flora_shift_detected"):
            add(
                SPECIMEN_CLINICAL_CULTURE,
                str(aid),
                ["discordant_modalities"],
                "clinical_microbiology",
                data,
            )


def _collect_swab_unexpected_requests(
    add: Any,
    swab_results: dict[str, dict[str, Any]],
) -> None:
    for zone, data in swab_results.items():
        if data.get("detected") and data.get("ct_value") is None:
            add(
                SPECIMEN_SURVEILLANCE_SWAB,
                zone,
                ["unexpected_pathogen"],
                "targeted_surface_swab",
                data,
            )


def collect_long_read_escalation_requests(
    cfg: dict[str, Any],
    *,
    ww_results: dict[str, dict[str, Any]],
    swab_results: dict[str, dict[str, Any]],
    clin_rdt_results: dict[int, dict[str, Any]],
    clin_qpcr_results: dict[int, dict[str, Any]],
    clin_microbio_results: dict[int, dict[str, Any]],
) -> list[LongReadVerificationRequest]:
    """Build verification queue from upstream instrument outputs."""
    if not is_long_read_enabled(cfg):
        return []

    triggers = _triggers(cfg)
    sources = allowed_specimen_sources(cfg)
    requests: list[LongReadVerificationRequest] = []
    seq = 0

    def _add(
        specimen_source: str,
        collection_key: str,
        reasons: list[str],
        upstream_instrument: str,
        snapshot: dict[str, Any],
    ) -> None:
        nonlocal seq
        if specimen_source not in sources or not reasons:
            return
        seq += 1
        requests.append(
            LongReadVerificationRequest(
                request_id=f"lr_{seq:04d}",
                specimen_source=specimen_source,
                collection_key=collection_key,
                trigger_reasons=reasons,
                upstream_instrument=upstream_instrument,
                upstream_snapshot=snapshot,
            ),
        )

    if triggers["mixed_infection_suspected"] and SPECIMEN_WASTEWATER_METAGENOMICS in sources:
        _collect_mixed_infection_requests(_add, ww_results)

    if triggers["unexpected_pathogen"] and SPECIMEN_WASTEWATER_METAGENOMICS in sources:
        _collect_unexpected_ww_requests(_add, ww_results)

    if triggers["discordant_modalities"]:
        if SPECIMEN_CLINICAL in sources:
            _collect_discordant_clinical_requests(
                _add, clin_rdt_results, clin_qpcr_results,
            )
        if SPECIMEN_CLINICAL_CULTURE in sources:
            _collect_microbio_discordance_requests(_add, clin_microbio_results)

    if triggers["unexpected_pathogen"] and SPECIMEN_SURVEILLANCE_SWAB in sources:
        _collect_swab_unexpected_requests(_add, swab_results)

    if triggers["special_circumstance"]:
        flag = long_read_config(cfg).get("special_circumstance_flag", False)
        if flag and SPECIMEN_CLINICAL in sources:
            _add(
                SPECIMEN_CLINICAL,
                "fleet",
                ["special_circumstance"],
                "operator",
                {"flag": True},
            )

    return requests
