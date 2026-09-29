"""COVID-PACKET-01: packet-arrival emission + occupancy conversion.

Locks the two pieces that carry the cooperative-dose instrument: the
per-epoch per-channel dose-increment recording in
``TakeoffAttributionLedger`` (``--packet-arrivals``), and the declared
carrier-occupancy algebra in ``tools/covid_packet_analytic.py`` — a
few different increment fields produce a few different packet counts,
and the tail sums stay inside their mathematical bounds.
"""

from __future__ import annotations

from collections import Counter

import pytest
from scipy.stats import poisson

from tools.covid_packet_analytic import (
    cell_packet_read,
    channel_read,
    poisson_tail,
)
from tools.covid_takeoff_attribution import (
    PACKET_ARRIVAL_LOG10_HI,
    PACKET_ARRIVAL_LOG10_LO,
    TakeoffAttributionLedger,
    _log10_histogram,
    _packet_arrivals_block,
    _post_channel_doses,
)


class TestPostChannelDoses:
    # Pathway keys are the suffix-stripped names the challenge record
    # stores (resolve_wrapped strips ":<pathogen_id>").
    def test_droplet_split_by_naive_shares(self) -> None:
        pw = {"droplet": 10.0}
        parts = Counter({"near_field_plume": 3.0, "zone_pool": 1.0})
        out = _post_channel_doses(pw, parts)
        assert out["near_field_plume"] == pytest.approx(7.5)
        assert out["zone_pool"] == pytest.approx(2.5)

    def test_non_droplet_pathways_pass_through(self) -> None:
        pw = {"hvac_airborne": 2.0, "contact": 1.0}
        out = _post_channel_doses(pw, Counter())
        assert out["hvac_airborne"] == pytest.approx(2.0)
        assert out["contact"] == pytest.approx(1.0)

    def test_unattributed_droplet_keeps_the_dose(self) -> None:
        out = _post_channel_doses({"droplet": 4.0}, Counter())
        assert out["droplet_unattributed"] == pytest.approx(4.0)


class TestLog10Histogram:
    def test_counts_conserve_and_lie_in_range(self) -> None:
        vals = [1e-13, 1e-10, 1e-5, 1e0, 1e9, 3e-6, 5e-6]
        hist = _log10_histogram(vals)
        assert sum(hist["counts"]) == len(vals)
        n_bins = int(PACKET_ARRIVAL_LOG10_HI - PACKET_ARRIVAL_LOG10_LO)
        assert len(hist["counts"]) == n_bins + 2
        # 1e-13 underflows, 1e9 overflows.
        assert hist["counts"][0] == 1
        assert hist["counts"][-1] == 1

    def test_empty_is_zero(self) -> None:
        assert sum(_log10_histogram([])["counts"]) == 0


class TestArrivalRecording:
    def test_opt_in_records_per_epoch_per_channel(self) -> None:
        ledger = TakeoffAttributionLedger(packet_arrivals=True)
        ledger._challenges = {
            7: {"pathways": {"hvac_airborne": 2.0}},
        }
        parts = {5: Counter({"near_field_plume": 3.0, "zone_pool": 1.0})}
        ledger._challenges[5] = {
            "pathways": {"droplet": 10.0},
        }
        ledger._record_arrivals(3, parts)

        assert ledger.arrival_epoch_channel[(3, "hvac_airborne")] == [2.0]
        assert ledger.arrival_epoch_channel[(3, "zone_pool")] == [2.5]
        assert ledger.arrival_host_channel[7]["hvac_airborne"] == [2.0]
        assert ledger.arrival_host_channel[5]["near_field_plume"] == [7.5]

    def test_default_off_leaves_buffers_empty(self) -> None:
        ledger = TakeoffAttributionLedger()
        assert ledger._packet_arrivals is False
        ledger._challenges = {
            1: {"pathways": {"hvac_airborne": 1.0}},
        }
        # observe() guards on the flag; the method itself records only
        # when called, so default ledgers accumulate nothing.
        assert ledger.arrival_epoch_channel == {}
        assert ledger.arrival_host_channel == {}

    def test_emit_block_shape(self) -> None:
        ledger = TakeoffAttributionLedger(packet_arrivals=True)
        ledger._challenges = {
            9: {"pathways": {"hvac_airborne": 1.5}},
        }
        ledger._record_arrivals(0, {})
        block = _packet_arrivals_block(ledger)
        assert block["by_epoch_channel"][0]["epoch"] == 0
        assert block["by_epoch_channel"][0]["channel"] == "hvac_airborne"
        assert block["by_epoch_channel"][0]["n_hosts"] == 1
        by_chan = block["by_channel"]["hvac_airborne"]
        assert by_chan["n_increments"] == 1
        assert by_chan["dose_sum"] == pytest.approx(1.5)
        host = block["by_host_channel"][0]
        assert host["id"] == 9
        assert host["channels"]["hvac_airborne"]["n_epochs"] == 1


class TestPoissonTail:
    @pytest.mark.parametrize(
        "mu,n",
        [(0.004, 2), (0.1, 2), (0.1, 3), (1.0, 2), (3.0, 3),
         (100.0, 5), (500.0, 5)],
    )
    def test_matches_scipy(self, mu: float, n: int) -> None:
        assert poisson_tail(mu, n) == pytest.approx(
            float(poisson.sf(n - 1, mu)), rel=1e-9,
        )

    def test_bounds(self) -> None:
        assert poisson_tail(0.0, 2) == 0.0
        for mu in (0.001, 0.1, 1.0, 50.0):
            assert 0.0 <= poisson_tail(mu, 2) <= 1.0


class TestChannelRead:
    def test_soup_is_sub_cooperative(self) -> None:
        """A dry-class field puts almost no copies in multi-virion packets.

        The soup property is the *share*: at the declared dry mu range
        at most tail_2(0.1)/0.1 = 4.7% of delivered copies ride a
        >=2-copy carrier — the field is almost all singles.
        """
        copies = 1e6
        out = channel_read(copies / 5.8e7, "dry", 5.8e7)
        assert out[2]["expected_packets_interval"][1] < 0.05 * copies

    def test_wet_carriers_are_packets(self) -> None:
        """At mu=500 every wet carrier is a multi-copy packet."""
        out = channel_read(1.0, "wet", 5.8e7)
        # copies = 5.8e7; carriers at mu=500 ~1.16e5, all >=2 copies.
        assert out[2]["expected_packets_interval"][1] > 1e4


def _synthetic_cell(zone_dose: float, plume_dose: float) -> dict:
    return {
        "cell": {"index": 0, "class_id": "mega", "seed": 1,
                 "theta": 2.37e11},
        "summary": {
            "recorded_onsets": 1000.0,
            "infections_total": 1200.0,
            "mechanism": {
                "packet_arrivals": {
                    "by_channel": {
                        "zone_pool": {
                            "n_increments": 10,
                            "dose_sum": zone_dose,
                            "dose_max": zone_dose / 10,
                        },
                        "near_field_plume": {
                            "n_increments": 2,
                            "dose_sum": plume_dose,
                            "dose_max": plume_dose,
                        },
                        "contact": {
                            "n_increments": 1,
                            "dose_sum": 1e-3,
                            "dose_max": 1e-3,
                        },
                    },
                    "by_host_channel": [
                        {"id": 1, "channels": {
                            "zone_pool": {"dose_sum": zone_dose},
                        }},
                        {"id": 2, "channels": {
                            "near_field_plume": {"dose_sum": plume_dose},
                        }},
                    ],
                },
            },
        },
    }


class TestCellPacketRead:
    def test_graded_sensitivity(self) -> None:
        """Larger increments produce larger expected packet counts."""
        light = cell_packet_read(_synthetic_cell(1e-6, 1e-6))
        heavy = cell_packet_read(_synthetic_cell(1e-4, 1e-4))
        light_e = light["channels"]["zone_pool"]["n_ge_2"][
            "expected_packets_interval"
        ][1]
        heavy_e = heavy["channels"]["zone_pool"]["n_ge_2"][
            "expected_packets_interval"
        ][1]
        assert heavy_e > light_e > 0.0

    def test_contact_reported_without_packet_claim(self) -> None:
        read = cell_packet_read(_synthetic_cell(1e-4, 1e-4))
        row = read["channels"]["contact"]
        assert row["carrier_class"] == "contact"
        assert "n_ge_2" not in row

    def test_hosts_any_is_a_probability_sum(self) -> None:
        read = cell_packet_read(_synthetic_cell(1e-4, 1e-2))
        row = read["channels"]["near_field_plume"]["n_ge_2"]
        lo, hi = row["expected_hosts_any_interval"]
        assert 0.0 <= lo <= hi <= 1.0 + 1e-9
