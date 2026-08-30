"""Golden, sensitivity, and mechanism tests for zone_contact_summary."""

from __future__ import annotations

import numpy as np

from crusher_labs.modalities.syndromic import SyndromicSurveillance
from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.transmission_core import TransmissionCore
from telemetry_buffer.agent_axes import (
    COMPLIANCE_COMPLIANT,
    INFECTION_INFECTED,
    INFECTION_SUSCEPTIBLE,
    PRESENTATION_ASYMPTOMATIC,
    PRESENTATION_SYMPTOMATIC,
)


def _agent(aid: int, loc: str, infected: bool = False) -> KorkinAgent:
    a = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone=loc,
        dining_zone="MainDining_L",
        work_zone="Main_Pool_Deck",
        free_zone="Main_Pool_Deck",
        schedule=["home"] * 24,
    )
    if infected:
        a.infection_status = InfectionStatus.INFECTED
        a.illness_status = IllnessStatus.SYMPTOMATIC
        a.time_infected = 1
    a.current_location = loc
    return a


def _by_zone(summary: list[dict]) -> dict[str, dict]:
    return {row["zone"]: row for row in summary}


class TestZoneContactSummary:
    def test_golden_colocation_summary(self) -> None:
        """Two agents colocated with one shedder → expected zone summary."""
        berthing = "Berthing"
        medbay = "MedBay"
        shedder = _agent(1, berthing, infected=True)
        target = _agent(2, berthing)
        # MedBay registered but empty — must not appear in summary
        core = TransmissionCore(
            rng=np.random.default_rng(42),
            zone_volumes={berthing: 200.0, medbay: 45.0},
            zone_types={berthing: "Room", medbay: "Medical"},
        )
        core.initialize_zones([berthing, medbay])
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, target],
            zone_pathogen_mass={berthing: 0.0, medbay: 0.0},
        )
        by_zone = _by_zone(matrix.zone_contact_summary)
        assert medbay not in by_zone
        assert berthing in by_zone
        row = by_zone[berthing]
        assert row["occupant_count"] == 2
        assert row["occupant_ids"] == [1, 2]
        assert row["shedder_count"] == 1
        assert row["shedder_ids"] == [1]
        assert row["shared_room_exposure_count"] >= 1
        assert row["droplet_exposure_count"] >= 1
        # Change detector: the POLYMOD contact rate yields one infection.
        assert row["infection_count"] == 1

        as_dict = matrix.to_dict()
        assert "zone_contact_summary" in as_dict
        assert as_dict["zone_contact_summary"][0]["zone"] == berthing

    def test_sensitivity_relocation_changes_zone_counts(self) -> None:
        """Moving the susceptible to another zone changes zone summaries."""
        berthing = "Berthing"
        medbay = "MedBay"
        shedder = _agent(1, berthing, infected=True)
        target_colocated = _agent(2, berthing)
        target_medbay = _agent(2, medbay)

        def _run(agents: list[KorkinAgent]) -> dict[str, dict]:
            core = TransmissionCore(
                rng=np.random.default_rng(7),
                zone_volumes={berthing: 200.0, medbay: 45.0},
                zone_types={berthing: "Room", medbay: "Medical"},
            )
            core.initialize_zones([berthing, medbay])
            matrix, _ = core.execute_transmission(
                epoch=1,
                agents=agents,
                zone_pathogen_mass={berthing: 0.0, medbay: 0.0},
            )
            return _by_zone(matrix.zone_contact_summary)

        baseline = _run([shedder, target_colocated])
        moved = _run([shedder, target_medbay])

        assert baseline[berthing]["occupant_count"] == 2
        assert baseline[berthing]["shared_room_exposure_count"] >= 1
        assert medbay not in baseline

        assert moved[berthing]["occupant_count"] == 1
        assert moved[berthing]["shared_room_exposure_count"] == 0
        assert moved[medbay]["occupant_count"] == 1
        assert moved[medbay]["shedder_count"] == 0
        assert moved[medbay]["occupant_ids"] == [2]
        assert (
            baseline[berthing]["occupant_count"]
            != moved[berthing]["occupant_count"]
        )

    def test_sick_call_does_not_relocate_agents_to_medbay(self) -> None:
        """Sick-call is roster-only: locations and MedBay mixing unchanged."""
        berthing = "Berthing"
        medbay = "MedBay"
        shedder = _agent(1, berthing, infected=True)
        healthy = _agent(2, berthing)
        locations_before = {
            a.agent_id: a.current_location for a in (shedder, healthy)
        }

        syn = SyndromicSurveillance(
            sick_call_probability=0.0,
            background_noise_rate=0.0,
            rng=np.random.default_rng(0),
        )
        truth = {
            "epoch": 1,
            "agents": [{
                "agent_id": 1,
                "infection_state": INFECTION_INFECTED,
                "symptom_presentation": PRESENTATION_SYMPTOMATIC,
                "compliance_status": COMPLIANCE_COMPLIANT,
            }, {
                "agent_id": 2,
                "infection_state": INFECTION_SUSCEPTIBLE,
                "symptom_presentation": PRESENTATION_ASYMPTOMATIC,
                "compliance_status": COMPLIANCE_COMPLIANT,
            }],
        }
        result = syn.query_ground_truth(
            truth,
            behavioral_overrides={1: "report_sick_call"},
        )
        assert 1 in result["sick_call_agents"]

        # Syndromic must not mutate physical locations
        for a in (shedder, healthy):
            assert a.current_location == locations_before[a.agent_id]

        core = TransmissionCore(
            rng=np.random.default_rng(11),
            zone_volumes={berthing: 200.0, medbay: 45.0},
            zone_types={berthing: "Room", medbay: "Medical"},
        )
        core.initialize_zones([berthing, medbay])
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, healthy],
            zone_pathogen_mass={berthing: 0.0, medbay: 0.0},
        )
        by_zone = _by_zone(matrix.zone_contact_summary)

        # Sick-call IDs do not force MedBay occupancy
        assert medbay not in by_zone
        assert by_zone[berthing]["occupant_ids"] == [1, 2]
        sick_call_set = set(result["sick_call_agents"])
        assert sick_call_set.issubset(set(by_zone[berthing]["occupant_ids"]))
        assert medbay not in {
            a.current_location for a in (shedder, healthy)
        }
