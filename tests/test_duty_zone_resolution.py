"""Duty-zone pins resolve across every zone type, not just Free+Dining.

Regression cover for the duty-domain gap measured by the dynamic hull
audit: ``_resolve_class_zones`` used to match ``duty_zone`` against Free
and Dining zones only, so a manifest pin at an Engineering or Medical
compartment silently degraded to a random leisure draw.
"""

from engines.infection_dynamics_bridge import KorkinShipEngine

ZONES = [
    {"name": "Engine_Rm", "type": "Engineering", "capacity": "medium"},
    {"name": "Sick_Bay", "type": "Medical", "capacity": "low"},
    {"name": "Mess_Deck", "type": "Dining", "capacity": "high"},
    {"name": "Open_Deck", "type": "Free", "capacity": "high"},
    {"name": "Berthing", "type": "Room", "capacity": "medium"},
]

AGENT_CLASSES = [
    {
        "class_id": "crew_engineering",
        "role_group": "crew",
        "fraction": 0.4,
        "home_zone_preference": "Berthing",
        "free_zone_preference": "",
        "duty_zone": "Engine_Rm",
    },
    {
        "class_id": "crew_corpsman",
        "role_group": "crew",
        "fraction": 0.3,
        "home_zone_preference": "Berthing",
        "free_zone_preference": "",
        "duty_zone": "sick_bay",
    },
    {
        "class_id": "crew_unpinned",
        "role_group": "crew",
        "fraction": 0.3,
        "home_zone_preference": "Berthing",
        "free_zone_preference": "",
        "duty_zone": "No_Such_Station",
    },
]

GENDER = {"male": 0.5, "female": 0.5}


def _engine() -> KorkinShipEngine:
    return KorkinShipEngine(
        num_passengers=0,
        num_crew=30,
        initial_infected=0,
        zones=ZONES,
        seed=11,
        agent_classes=AGENT_CLASSES,
        gender_distribution=GENDER,
    )


def _work_zones(engine: KorkinShipEngine, class_id: str) -> set[str]:
    return {a.work_zone for a in engine.agents if a.agent_class == class_id}


def test_duty_pin_lands_on_engineering_typed_zone() -> None:
    engine = _engine()
    assert _work_zones(engine, "crew_engineering") == {"Engine_Rm"}


def test_duty_pin_lands_on_medical_typed_zone_case_insensitive() -> None:
    engine = _engine()
    assert _work_zones(engine, "crew_corpsman") == {"Sick_Bay"}


def test_unmatched_pin_still_falls_back_to_leisure_zones() -> None:
    engine = _engine()
    assert _work_zones(engine, "crew_unpinned") <= {"Mess_Deck", "Open_Deck"}


def test_every_crew_class_was_spawned() -> None:
    engine = _engine()
    spawned = {a.agent_class for a in engine.agents}
    assert spawned == {"crew_engineering", "crew_corpsman", "crew_unpinned"}
