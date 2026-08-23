"""Genotype truth reaches the line list as a *reported* call (Paper 3).

The chain under test is: a host's resident lineages -> the specimen mixture a
clinical request draws -> the long-read typing pass -> the sentinel line list's
``genotype`` field, plus the per-epoch lineage census. The properties that
matter for the paper are that an untracked run stays pathogen-level, and that
what lands in the line list is the assay's call (which may be wrong) rather
than the simulator's truth.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from crusher_labs.modalities.clinical_strain_typing import (
    STATUS_ABOVE_CT_THRESHOLD,
    STATUS_TYPED,
    ClinicalStrainTyping,
    SequencingAssay,
    typed_genotypes,
)
from crusher_labs.modalities.long_read_sequencing import (
    SPECIMEN_CLINICAL,
    SPECIMEN_WASTEWATER_METAGENOMICS,
    LongReadVerificationRequest,
)
from crusher_labs.observation_core import LongReadVerificationSequencing
from engines.infection_dynamics_bridge import KorkinAgent
from engines.strain_state import StrainRegistry, StrainState
from orchestrator_epoch import clinical_genotype_mixtures
from picard_framework.analysis.sentinel.line_list import SentinelLedger

PATHOGEN = "norwalk_gi"
OTHER_PATHOGEN = "aeromonas_gi"
GENOTYPES = ("GII.4", "GII.17", "GII.2")

PROFILE = {
    "pathogen_id": PATHOGEN,
    "recovery_day": 5,
    "shedding_curve_log10": [6.0, 7.0, 7.0, 6.0, 5.0],
    "asymptomatic_shedding_log10": [5.0, 5.0, 5.0, 4.0, 4.0],
    "dose_adjustment": 1.0,
    "strain_evolution": {"genotypes": list(GENOTYPES)},
    "sequencing_assay": {
        "amplicon_target": "Capsid (VP1)",
        "read_accuracy": 0.92,
        "ct_threshold": 30.0,
        "cost_usd": 150.0,
    },
}
UNTRACKED_PROFILE = {
    "pathogen_id": OTHER_PATHOGEN,
    "recovery_day": 5,
    "shedding_curve_log10": [6.0, 7.0, 7.0, 6.0, 5.0],
    "asymptomatic_shedding_log10": [5.0, 5.0, 5.0, 4.0, 4.0],
    "dose_adjustment": 1.0,
}

AMPLE_MASS = 1e6


def _agent(aid: int = 1) -> KorkinAgent:
    return KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone="MainDining_L",
        dining_zone="MainDining_L",
        work_zone="MainDining_L",
        free_zone="MainDining_L",
        schedule=["Free"] * 24,
    )


def _infected(
    registry: StrainRegistry,
    genotypes: list[str],
    *,
    aid: int = 1,
    pathogen_id: str = PATHOGEN,
) -> KorkinAgent:
    agent = _agent(aid)
    strains = []
    for idx, genotype in enumerate(genotypes):
        strain = StrainState(
            strain_id=f"{pathogen_id}:{aid}:{idx}",
            pathogen_id=pathogen_id,
            genotype=genotype,
        )
        registry.register(strain)
        strains.append(strain)
    agent.infect_with_pathogen(
        pathogen_id, dose=100.0, epoch=0, strain_id=strains[0].strain_id,
    )
    for strain in strains[1:]:
        agent.superinfect_with_strain(
            pathogen_id, strain.strain_id, dose=100.0, epoch=0,
        )
    return agent


class _FakeEngine:
    """Only the surface ``clinical_genotype_mixtures`` reads of the engine."""

    def __init__(self, agents: list[KorkinAgent]) -> None:
        self.agents = agents


def _request(
    key: str,
    *,
    specimen: str = SPECIMEN_CLINICAL,
    request_id: str = "r1",
) -> LongReadVerificationRequest:
    return LongReadVerificationRequest(
        request_id=request_id,
        specimen_source=specimen,
        collection_key=key,
    )


class TestSpecimenMixtureHandoff:
    """The lab layer is handed truth per collection key, or nothing at all."""

    def test_clinical_request_carries_the_hosts_lineages(self):
        registry = StrainRegistry()
        engine = _FakeEngine([_infected(registry, ["GII.4"], aid=1)])
        mixtures = clinical_genotype_mixtures(
            [_request("1")], engine, registry, {PATHOGEN: PROFILE},
        )
        assert mixtures == {"1": {PATHOGEN: {"GII.4": 1.0}}}

    def test_no_registry_means_no_mixtures_at_all(self):
        registry = StrainRegistry()
        engine = _FakeEngine([_infected(registry, ["GII.4"], aid=1)])
        assert clinical_genotype_mixtures(
            [_request("1")], engine, None, {PATHOGEN: PROFILE},
        ) == {}

    def test_no_engine_and_no_profiles_are_both_inert(self):
        registry = StrainRegistry()
        assert clinical_genotype_mixtures(
            [_request("1")], None, registry, {PATHOGEN: PROFILE},
        ) == {}
        engine = _FakeEngine([_infected(registry, ["GII.4"], aid=1)])
        assert clinical_genotype_mixtures([_request("1")], engine, registry, {}) == {}

    def test_environmental_specimen_gets_no_clinical_truth(self):
        registry = StrainRegistry()
        engine = _FakeEngine([_infected(registry, ["GII.4"], aid=1)])
        mixtures = clinical_genotype_mixtures(
            [_request("1", specimen=SPECIMEN_WASTEWATER_METAGENOMICS)],
            engine, registry, {PATHOGEN: PROFILE},
        )
        assert mixtures == {}

    def test_non_agent_collection_key_is_skipped_not_guessed(self):
        registry = StrainRegistry()
        engine = _FakeEngine([_infected(registry, ["GII.4"], aid=1)])
        mixtures = clinical_genotype_mixtures(
            [_request("MainDining_L"), _request("99", request_id="r2")],
            engine, registry, {PATHOGEN: PROFILE},
        )
        assert mixtures == {}

    def test_untracked_pathogen_contributes_no_entry(self):
        registry = StrainRegistry()
        agent = _infected(registry, ["GII.4"], aid=1)
        engine = _FakeEngine([agent])
        mixtures = clinical_genotype_mixtures(
            [_request("1")], engine, registry,
            {PATHOGEN: PROFILE, OTHER_PATHOGEN: UNTRACKED_PROFILE},
        )
        assert set(mixtures["1"]) == {PATHOGEN}

    def test_uninfected_host_yields_no_specimen_entry(self):
        registry = StrainRegistry()
        engine = _FakeEngine([_agent(1)])
        assert clinical_genotype_mixtures(
            [_request("1")], engine, registry, {PATHOGEN: PROFILE},
        ) == {}


class _StubModality:
    """Captures what the observation layer forwards per request."""

    def __init__(self) -> None:
        self.seen: list[tuple[str, Any, int | None]] = []

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
        self.seen.append(
            (request.collection_key, genotype_mixtures, typing_read_depth),
        )
        return {"request_id": request.request_id}


class _NoQC:
    def should_run_control(self) -> bool:
        return False

    def run_negative_control(self) -> dict[str, Any]:  # pragma: no cover - unused
        raise AssertionError("QC control should not run in these tests")


def _runner(modality: _StubModality) -> LongReadVerificationSequencing:
    runner = LongReadVerificationSequencing.__new__(LongReadVerificationSequencing)
    runner.modality = modality
    runner.qc = _NoQC()
    return runner


class TestObservationForwarding:
    """Mixtures reach the assay keyed by collection key, or not at all."""

    def test_each_request_receives_only_its_own_specimen(self):
        modality = _StubModality()
        requests = [_request("1"), _request("2", request_id="r2")]
        _runner(modality).run_requests(
            requests,
            genotype_mixtures_by_key={"2": {PATHOGEN: {"GII.17": 1.0}}},
            typing_read_depth=800,
        )
        assert modality.seen == [
            ("1", None, 800),
            ("2", {PATHOGEN: {"GII.17": 1.0}}, 800),
        ]

    def test_absent_mixtures_leave_the_assay_pathogen_level(self):
        modality = _StubModality()
        results = _runner(modality).run_requests([_request("1")])
        assert modality.seen == [("1", None, None)]
        assert set(results) == {"r1"}


def _call(
    agent_id: int,
    pathogen_id: str,
    *,
    status: str = STATUS_TYPED,
    consensus: str | None = "GII.4",
) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "pathogen_id": pathogen_id,
        "status": status,
        "consensus_genotype": consensus,
    }


class TestTypedGenotypeHarvest:
    """Only delivered, typed calls become an observed genotype."""

    def test_typed_call_is_harvested(self):
        results = {"r1": {"genotype_calls": [_call(4, PATHOGEN)]}}
        assert typed_genotypes(results) == {4: "GII.4"}

    def test_untyped_and_empty_calls_are_ignored(self):
        results = {
            "r1": {"genotype_calls": [
                _call(4, PATHOGEN, status=STATUS_ABOVE_CT_THRESHOLD),
                _call(5, PATHOGEN, consensus=None),
            ]},
            "r2": {"genotype_calls": []},
            "r3": {},
        }
        assert typed_genotypes(results) == {}

    def test_no_results_at_all_is_empty(self):
        assert typed_genotypes(None) == {}

    def test_coinfected_host_reports_one_pathogen_deterministically(self):
        results = {
            "r1": {"genotype_calls": [
                _call(7, PATHOGEN, consensus="GII.4"),
                _call(7, OTHER_PATHOGEN, consensus="aer.1"),
            ]},
        }
        assert typed_genotypes(results) == {7: "aer.1"}

    def test_malformed_call_entries_are_skipped(self):
        results = {"r1": {"genotype_calls": ["not-a-call", _call(2, PATHOGEN)]}}
        assert typed_genotypes(results) == {2: "GII.4"}

    def test_a_call_without_an_agent_id_is_dropped(self):
        results = {"r1": {"genotype_calls": [
            {"pathogen_id": PATHOGEN, "status": STATUS_TYPED,
             "consensus_genotype": "GII.4"},
        ]}}
        assert typed_genotypes(results) == {}


def _agent_record(aid: int, **overrides: Any) -> dict[str, Any]:
    record = {
        "agent_id": aid,
        "infection_state": "infected",
        "symptom_presentation": "symptomatic",
        "location": "Cabin_1",
        "agent_class": "passenger",
        "role": "passenger",
        "pathogen_infections": {
            PATHOGEN: {"status": "INFECTED", "illness": "SYMPTOMATIC"},
        },
    }
    record.update(overrides)
    return record


class TestLineListGenotype:
    """The line list carries the reported call, including a wrong one."""

    def test_typed_call_reaches_the_record(self):
        ledger = SentinelLedger()
        ledger.observe_epoch(1, [_agent_record(1)], genotypes={1: "GII.4"})
        rows = {r.person_id: r for r in ledger.records()}
        assert rows["1"].genotype == "GII.4"

    def test_untyped_case_stays_null(self):
        ledger = SentinelLedger()
        ledger.observe_epoch(1, [_agent_record(1)])
        assert next(iter(ledger.records())).genotype is None

    def test_first_call_is_kept_when_a_case_is_retyped(self):
        ledger = SentinelLedger()
        ledger.observe_epoch(1, [_agent_record(1)], genotypes={1: "GII.4"})
        ledger.observe_epoch(2, [_agent_record(1)], genotypes={1: "GII.17"})
        rows = {r.person_id: r for r in ledger.records()}
        assert rows["1"].genotype == "GII.4"

    def test_blank_call_neither_records_nor_blocks_a_later_one(self):
        ledger = SentinelLedger()
        ledger.observe_epoch(1, [_agent_record(1)], genotypes={1: "  "})
        ledger.observe_epoch(2, [_agent_record(1)], genotypes={1: "GII.2"})
        rows = {r.person_id: r for r in ledger.records()}
        assert rows["1"].genotype == "GII.2"

    def test_a_miscalled_genotype_flows_through_as_observed(self):
        registry = StrainRegistry()
        agent = _infected(registry, ["GII.4"], aid=1)
        typing = ClinicalStrainTyping(
            {PATHOGEN: SequencingAssay.from_profile(
                {**PROFILE, "sequencing_assay": {
                    **PROFILE["sequencing_assay"],
                    "read_accuracy": 0.34,
                    "read_depth": 20,
                    "min_reads_for_genotype": 1,
                }},
            )},
            rng=np.random.default_rng(3),
        )
        miscalls = [
            result for _ in range(60)
            if (result := typing.type_specimen(
                agent.agent_id, PATHOGEN, AMPLE_MASS, {"GII.4": 1.0},
            ))["status"] == STATUS_TYPED
            and result["consensus_genotype"] != "GII.4"
        ]
        assert miscalls, "a 34%-accuracy assay must be able to name a wrong lineage"
        wrong = miscalls[0]["consensus_genotype"]
        ledger = SentinelLedger()
        ledger.observe_epoch(
            1, [_agent_record(1)],
            genotypes=typed_genotypes({"r1": {"genotype_calls": [miscalls[0]]}}),
        )
        rows = {r.person_id: r for r in ledger.records()}
        assert rows["1"].genotype == wrong != "GII.4"

    def test_payload_exports_the_genotype_field(self):
        ledger = SentinelLedger()
        ledger.observe_epoch(1, [_agent_record(1)], genotypes={1: "GII.17"})
        payload = ledger.to_payload(
            voyage_id="v1",
            ship_id="s1",
            n_passengers=1,
            n_crew=0,
            platform_class="s1",
            observation_end_epoch=1,
        )
        assert payload["clinical_cases"][0]["genotype"] == "GII.17"


class TestStrainCensus:
    """Per-epoch carrier counts, present only when lineages exist."""

    def _sim(self, registry: StrainRegistry | None, agents: list[KorkinAgent]):
        from picard_framework.simulation.ship_simulation import ShipSimulation

        sim = ShipSimulation.__new__(ShipSimulation)
        sim.engine = _FakeEngine(agents)
        sim.tx_core = type(
            "_TxCore", (), {
                "strain_registry": registry,
                "strain_configs": (
                    {} if registry is None else {PATHOGEN: object()}
                ),
            },
        )()
        return sim

    def _record(self, registry: StrainRegistry | None, agents, epoch: int = 3):
        sim = self._sim(registry, agents)
        work = type("_Work", (), {"epoch": epoch, "epoch_record": {}})()
        sim._attach_strain_census(work)
        return work.epoch_record

    def test_untracked_run_writes_no_census_key(self):
        assert self._record(None, [_agent(1)]) == {}

    def test_counts_and_dominance_reflect_the_population(self):
        registry = StrainRegistry()
        agents = [
            _infected(registry, ["GII.4"], aid=1),
            _infected(registry, ["GII.4"], aid=2),
            _infected(registry, ["GII.17"], aid=3),
        ]
        census = self._record(registry, agents)["strain_census"]
        assert len(census) == 1
        entry = census[0]
        assert entry["epoch"] == 3
        assert entry["pathogen_id"] == PATHOGEN
        assert entry["total_carriers"] == 3
        assert entry["num_lineages"] == 3
        assert entry["dominant_fraction"] == pytest.approx(1 / 3)

    def test_a_coinfected_host_is_counted_under_every_lineage(self):
        registry = StrainRegistry()
        agents = [_infected(registry, ["GII.4", "GII.2"], aid=1)]
        entry = self._record(registry, agents)["strain_census"][0]
        assert entry["num_lineages"] == 2
        assert sum(entry["lineage_counts"].values()) == 2

    def test_an_empty_epoch_records_a_zero_census(self):
        registry = StrainRegistry()
        entry = self._record(registry, [_agent(1)])["strain_census"][0]
        assert entry["total_carriers"] == 0
        assert entry["num_lineages"] == 0
        assert entry["dominant_strain_id"] == ""

    def test_the_census_series_accumulates_in_the_registry(self):
        registry = StrainRegistry()
        agents = [_infected(registry, ["GII.4"], aid=1)]
        sim = self._sim(registry, agents)
        for epoch in (1, 2):
            work = type("_Work", (), {"epoch": epoch, "epoch_record": {}})()
            sim._attach_strain_census(work)
        assert [s.epoch for s in registry.snapshots(PATHOGEN)] == [1, 2]


class TestNotebookRecordsTheCall:
    """The notebook logs a delivered long-read run, including its genotype call.

    Regression: ``run_observation_sampling`` has always called
    ``log_long_read_verification`` when escalation delivers a result, but the
    method did not exist — so the first real run that escalated crashed instead
    of writing a notebook row.
    """

    @staticmethod
    def _notebook(fidelity_name: str = "HIGH_FIDELITY"):
        from crusher_labs.lab_notebook import ArtificialLabNotebook, FidelityProfile

        return ArtificialLabNotebook(
            fidelity=FidelityProfile({
                "log_binary_states": True,
                "log_numeric_outputs": True,
                "log_raw_matrices": True,
                "log_qc_validation": True,
            }),
            fidelity_name=fidelity_name,
        )

    @staticmethod
    def _result() -> dict[str, Any]:
        return {
            "request_id": "LR-1",
            "specimen_source": SPECIMEN_CLINICAL,
            "collection_key": "7",
            "purpose": "clinical_confirmation",
            "read_depth": 5000,
            "total_classified_reads": 4800,
            "pathogen_calls": [{"pathogen_id": PATHOGEN, "classified_reads": 4800}],
            "genotype_calls": [{
                "pathogen_id": PATHOGEN,
                "agent_id": 7,
                "status": STATUS_TYPED,
                "consensus_genotype": "GII.4",
            }],
            "consensus_ready": True,
            "mixed_infection_flag": False,
            "trigger_reasons": ["discordant_modalities"],
        }

    def test_high_fidelity_row_carries_the_consensus_call(self) -> None:
        nb = self._notebook()
        nb.log_long_read_verification(4, {"LR-1": self._result()})
        (row,) = nb.records
        assert row["collection_point_type"] == "long_read_verification"
        assert row["binary_result"] == "DETECTED"
        assert row["genotype_calls"] == [{
            "pathogen_id": PATHOGEN,
            "status": STATUS_TYPED,
            "consensus_genotype": "GII.4",
        }]
        assert row["read_depth"] == 5000
        assert row["trigger_reasons"] == ["discordant_modalities"]

    def test_low_fidelity_row_drops_the_genotype(self) -> None:
        nb = self._notebook("LOW_FIDELITY")
        nb.log_long_read_verification(4, {"LR-1": self._result()})
        (row,) = nb.records
        assert row["stoplight"] == "RED"
        assert "genotype_calls" not in row
        assert "read_depth" not in row

    def test_a_run_with_no_pathogen_call_reads_as_negative(self) -> None:
        nb = self._notebook()
        payload = self._result() | {"pathogen_calls": [], "genotype_calls": []}
        nb.log_long_read_verification(4, {"LR-1": payload})
        (row,) = nb.records
        assert row["binary_result"] == "NOT DETECTED"
        assert row["inferred_anomaly_score"] == pytest.approx(0.0)
        assert row["genotype_calls"] == []
