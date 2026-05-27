"""
test_cost_accounting.py – Ensure per-test costs are debited correctly
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.cost_ledger import CostLedger
from orchestrator_epoch import step_cost_accounting
from orchestrator_types import ProtocolContext


class TestStepCostAccounting:
    def test_debits_expected_per_test_types(self) -> None:
        ledger = CostLedger(
            starting_financial_usd=10_000.0,
            starting_labor_hours=100.0,
            starting_inventory={
                "air_sniffer_cartridges": 10,
                "swab_kits": 50,
                "pcr_kits": 50,
                "wastewater_collection_kits": 10,
                "library_prep_kits": 10,
                "rdt_kits": 10,
                "culture_media_sets": 10,
            },
        )
        resource_cfg = {
            "baseline_surveillance_costs_per_epoch": {
                "financial_usd": 1.0,
                "materials": {},
                "labor_person_hours": 0.0,
            },
            "per_test_costs": {
                "air_sniffer_sample": {
                    "financial_usd": 10.0,
                    "materials": {"air_sniffer_cartridges": 1},
                    "labor_person_hours": 0.5,
                },
                "surface_swab_pcr": {
                    "financial_usd": 5.0,
                    "materials": {"swab_kits": 1, "pcr_kits": 1},
                    "labor_person_hours": 0.25,
                },
                "wastewater_sequencing_panel": {
                    "financial_usd": 20.0,
                    "materials": {
                        "wastewater_collection_kits": 1,
                        "library_prep_kits": 1,
                        "pcr_kits": 1,
                    },
                    "labor_person_hours": 1.0,
                },
                "clinical_rdt": {
                    "financial_usd": 2.0,
                    "materials": {"rdt_kits": 1},
                    "labor_person_hours": 0.1,
                },
                "clinical_qpcr": {
                    "financial_usd": 3.0,
                    "materials": {"pcr_kits": 1, "swab_kits": 1},
                    "labor_person_hours": 0.2,
                },
                "clinical_microbiology": {
                    "financial_usd": 4.0,
                    "materials": {"swab_kits": 1, "culture_media_sets": 1},
                    "labor_person_hours": 0.3,
                },
            },
        }
        proto_ctx = ProtocolContext(
            protocol_engine=None,  # not used by step_cost_accounting
            cost_ledger=ledger,
            resource_costs_cfg=resource_cfg,
            standing_protocols=[],
            original_filter_eff=0.5,
        )

        air_results = {"Bridge": {}, "MedBay": {}}  # 2 samples
        swab_results = {"Bridge": {}}  # 1 sample
        ww_results = {"Engine_Room": {}, "Galley": {}}  # 2 samples
        clin_rdt_results = {0: {}, 1: {}, 2: {}}  # 3 patients
        clin_qpcr_results = {0: {}, 1: {}, 2: {}}
        clin_microbio_results = {0: {}, 1: {}, 2: {}}

        step_cost_accounting(
            0,
            proto_ctx,
            air_results,
            swab_results,
            ww_results,
            clin_rdt_results,
            clin_qpcr_results,
            clin_microbio_results,
        )

        # One baseline debit + one per-test debit per test type.
        assert proto_ctx.cost_ledger.get_epoch_summary(0)["entries_count"] == 7

        mats = proto_ctx.cost_ledger.get_epoch_summary(0)["materials_consumed"]
        assert mats["air_sniffer_cartridges"] == 2
        assert mats["library_prep_kits"] == 2
        assert mats["rdt_kits"] == 3
        assert mats["culture_media_sets"] == 3
        assert mats["swab_kits"] == 1 + 3 + 3
