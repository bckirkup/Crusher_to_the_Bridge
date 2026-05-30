#!/usr/bin/env python3
"""One-shot generator for Star Trek Enterprise example platforms (fiction-adapted)."""
from __future__ import annotations

import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")


def _write(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def tos_spatial() -> dict:
    zones = [
        ("Bridge", "Free", "low", 220, "saucer_primary", 120, 8, "Command and navigation"),
        ("Sickbay", "Free", "low", 180, "saucer_primary", 95, 18, "Primary care and isolation"),
        ("Engineering", "Room", "medium", 520, "secondary_hull", 55, 42, "Warp core and engineering"),
        ("Transporter_Room", "Free", "low", 90, "saucer_primary", 78, 28, "Personnel transporter"),
        ("Rec_Deck", "Dining", "high", 380, "saucer_primary", 65, 12, "Recreation and crew mess"),
        ("Galley", "Dining", "medium", 140, "saucer_primary", 58, 16, "Food preparation"),
        ("Science_Lab", "Free", "low", 200, "saucer_primary", 88, 32, "Shipboard sciences"),
        ("Communications", "Free", "low", 110, "saucer_primary", 105, 22, "Subspace communications"),
        ("Security_Station", "Free", "low", 95, "saucer_primary", 72, 35, "Security and brig access"),
        ("Crew_Quarters", "Room", "medium", 480, "saucer_primary", 42, 8, "Enlisted berthing"),
        ("Officer_Quarters", "Room", "low", 320, "saucer_primary", 48, 22, "Officer staterooms"),
        ("Library", "Free", "low", 150, "saucer_primary", 62, 38, "Library and briefing"),
    ]
    return {
        "platform": "enterprise_constitution_tos",
        "description": "Constitution-class heavy cruiser (NCC-1701 era). Fiction-adapted 12-zone layout for Crusher-to-the-Bridge demos; ~430 crew complement.",
        "isolation_unit_capacity": 8,
        "deck_dimensions": {"length_m": 289, "beam_m": 127},
        "zones": [
            {
                "id": zid,
                "type": ztype,
                "traffic": traffic,
                "volume_m3": vol,
                "deck": deck,
                "display": {"x": x, "y": y},
                "description": desc,
            }
            for zid, ztype, traffic, vol, deck, x, y, desc in zones
        ],
    }


def tos_airflow() -> dict:
    return {
        "platform": "enterprise_constitution_tos",
        "description": "Constitution-class HVAC: saucer primary ring, engineering secondary hull, limited cross-hull ducting.",
        "hvac_zones": [
            {
                "id": "zone_saucer_command",
                "rooms": ["Bridge", "Communications", "Library"],
                "ach": 8.0,
                "description": "Forward saucer command spaces",
            },
            {
                "id": "zone_saucer_ops",
                "rooms": ["Sickbay", "Security_Station", "Transporter_Room", "Science_Lab"],
                "ach": 10.0,
                "description": "Mid-saucer operational deck",
            },
            {
                "id": "zone_saucer_living",
                "rooms": ["Rec_Deck", "Galley", "Crew_Quarters", "Officer_Quarters"],
                "ach": 7.0,
                "description": "Crew living and dining ring",
            },
            {
                "id": "zone_engineering",
                "rooms": ["Engineering"],
                "ach": 14.0,
                "description": "Secondary hull high-exchange engineering",
            },
        ],
        "cross_zone_links": [
            {
                "from": "zone_saucer_command",
                "to": "zone_saucer_ops",
                "flow_rate_m3h": 120,
                "path": "turbolift_shaft_fore",
                "is_hvac_ducted": True,
            },
            {
                "from": "zone_saucer_ops",
                "to": "zone_saucer_living",
                "flow_rate_m3h": 180,
                "path": "corridor_ring_mid",
                "is_hvac_ducted": False,
            },
            {
                "from": "zone_saucer_living",
                "to": "zone_engineering",
                "flow_rate_m3h": 90,
                "path": "connecting_tube_aft",
                "is_hvac_ducted": True,
            },
            {
                "from": "zone_saucer_command",
                "to": "zone_engineering",
                "flow_rate_m3h": 40,
                "path": "emergency_vent_shaft",
                "is_hvac_ducted": False,
            },
        ],
        "adjacency": [
            {"from": "Bridge", "to": "Communications", "type": "turbolift"},
            {"from": "Bridge", "to": "Library", "type": "passageway"},
            {"from": "Sickbay", "to": "Transporter_Room", "type": "passageway"},
            {"from": "Sickbay", "to": "Security_Station", "type": "passageway"},
            {"from": "Science_Lab", "to": "Library", "type": "passageway"},
            {"from": "Rec_Deck", "to": "Galley", "type": "service_hatch"},
            {"from": "Galley", "to": "Crew_Quarters", "type": "passageway"},
            {"from": "Crew_Quarters", "to": "Officer_Quarters", "type": "passageway"},
            {"from": "Officer_Quarters", "to": "Engineering", "type": "turbolift"},
            {"from": "Engineering", "to": "Sickbay", "type": "turbolift"},
            {"from": "Rec_Deck", "to": "Bridge", "type": "turbolift"},
        ],
    }


def tng_spatial() -> dict:
    zones = [
        ("Bridge", "Free", "low", 280, "saucer_1", 130, 10, "Command center"),
        ("Ten_Forward", "Dining", "high", 420, "saucer_10", 70, 8, "Forward lounge and observation"),
        ("Sickbay", "Free", "low", 350, "saucer_12", 90, 20, "Primary care"),
        ("Main_Engineering", "Room", "high", 680, "drive_section", 50, 45, "Warp core and EPS"),
        ("Holodeck", "Free", "medium", 260, "saucer_9", 75, 28, "Holodeck complex"),
        ("Crew_Quarters", "Room", "medium", 620, "saucer_25", 45, 12, "Enlisted berthing"),
        ("Family_Quarters", "Room", "medium", 540, "saucer_24", 55, 18, "Family staterooms"),
        ("Science_Labs", "Free", "low", 400, "saucer_15", 85, 32, "Research laboratories"),
        ("Shuttlebay", "Free", "low", 1200, "saucer_4", 40, 40, "Shuttlecraft bay"),
        ("Cargo_Bay", "Room", "low", 900, "saucer_6", 35, 38, "Cargo and stores"),
        ("Galley", "Dining", "medium", 200, "saucer_8", 60, 22, "Food preparation"),
        ("Crew_Lounge", "Dining", "high", 380, "saucer_10", 65, 14, "Off-duty crew lounge"),
        ("Security_Office", "Free", "low", 120, "saucer_11", 78, 35, "Security and brig"),
        ("Arboretum", "Free", "medium", 480, "saucer_17", 95, 42, "Hydroponics and arboretum"),
        ("Stellar_Cartography", "Free", "low", 180, "saucer_16", 100, 38, "Stellar cartography"),
        ("Schoolroom", "Free", "low", 160, "saucer_23", 52, 25, "Shipboard school"),
    ]
    return {
        "platform": "enterprise_galaxy_tng",
        "description": "Galaxy-class explorer (NCC-1701-D era). Fiction-adapted 16-zone layout; mixed crew and civilian families.",
        "isolation_unit_capacity": 24,
        "deck_dimensions": {"length_m": 642, "beam_m": 463},
        "zones": [
            {
                "id": zid,
                "type": ztype,
                "traffic": traffic,
                "volume_m3": vol,
                "deck": deck,
                "display": {"x": x, "y": y},
                "description": desc,
            }
            for zid, ztype, traffic, vol, deck, x, y, desc in zones
        ],
    }


def tng_airflow() -> dict:
    return {
        "platform": "enterprise_galaxy_tng",
        "description": "Galaxy-class multi-deck HVAC with saucer living ring and drive-section engineering plenum.",
        "hvac_zones": [
            {
                "id": "zone_saucer_command",
                "rooms": ["Bridge", "Stellar_Cartography", "Security_Office"],
                "ach": 9.0,
            },
            {
                "id": "zone_saucer_social",
                "rooms": ["Ten_Forward", "Crew_Lounge", "Holodeck", "Galley"],
                "ach": 8.0,
            },
            {
                "id": "zone_saucer_medical",
                "rooms": ["Sickbay", "Science_Labs", "Arboretum"],
                "ach": 11.0,
            },
            {
                "id": "zone_saucer_habitation",
                "rooms": ["Crew_Quarters", "Family_Quarters", "Schoolroom"],
                "ach": 6.5,
            },
            {
                "id": "zone_saucer_logistics",
                "rooms": ["Shuttlebay", "Cargo_Bay"],
                "ach": 12.0,
            },
            {
                "id": "zone_drive",
                "rooms": ["Main_Engineering"],
                "ach": 16.0,
            },
        ],
        "cross_zone_links": [
            {
                "from": "zone_saucer_command",
                "to": "zone_saucer_social",
                "flow_rate_m3h": 200,
                "path": "turbolift_forward",
                "is_hvac_ducted": True,
            },
            {
                "from": "zone_saucer_social",
                "to": "zone_saucer_medical",
                "flow_rate_m3h": 160,
                "path": "corridor_ring",
                "is_hvac_ducted": False,
            },
            {
                "from": "zone_saucer_medical",
                "to": "zone_saucer_habitation",
                "flow_rate_m3h": 140,
                "path": "habitation_trunk",
                "is_hvac_ducted": True,
            },
            {
                "from": "zone_saucer_habitation",
                "to": "zone_saucer_logistics",
                "flow_rate_m3h": 100,
                "path": "cargo_lift_shaft",
                "is_hvac_ducted": False,
            },
            {
                "from": "zone_saucer_logistics",
                "to": "zone_drive",
                "flow_rate_m3h": 220,
                "path": "engineering_connecting_spine",
                "is_hvac_ducted": True,
            },
            {
                "from": "zone_saucer_command",
                "to": "zone_drive",
                "flow_rate_m3h": 60,
                "path": "emergency_scrubber_loop",
                "is_hvac_ducted": True,
            },
        ],
        "adjacency": [
            {"from": "Bridge", "to": "Stellar_Cartography", "type": "turbolift"},
            {"from": "Ten_Forward", "to": "Crew_Lounge", "type": "passageway"},
            {"from": "Galley", "to": "Ten_Forward", "type": "service_hatch"},
            {"from": "Sickbay", "to": "Science_Labs", "type": "passageway"},
            {"from": "Family_Quarters", "to": "Schoolroom", "type": "passageway"},
            {"from": "Crew_Quarters", "to": "Holodeck", "type": "passageway"},
            {"from": "Arboretum", "to": "Science_Labs", "type": "passageway"},
            {"from": "Shuttlebay", "to": "Cargo_Bay", "type": "passageway"},
            {"from": "Cargo_Bay", "to": "Main_Engineering", "type": "turbolift"},
            {"from": "Main_Engineering", "to": "Sickbay", "type": "turbolift"},
            {"from": "Security_Office", "to": "Sickbay", "type": "passageway"},
        ],
    }


def _curve(peak: float, days: int = 15) -> list[float]:
    """Simple bell-shaped log10 shedding curve."""
    mid = days // 2
    return [round(peak - abs(i - mid) * (peak / max(mid, 1)) * 0.35, 2) for i in range(days)]


def tos_pathogens() -> dict:
    return {
        "meta": {
            "description": "TOS-inspired pathogen profiles (fiction-adapted, not clinical claims)",
            "version": "1.0",
            "notes": "rigelian_fever evokes Journey to Babel; psi_2000_polywater evokes The Naked Time shipwide behavioral outbreak.",
        },
        "pathogens": [
            {
                "pathogen_id": "rigelian_fever",
                "name": "Rigelian Fever (fiction-adapted)",
                "category": "bacterial",
                "transmission_routes": ["direct_contact", "droplet", "fomite", "hvac_airborne"],
                "shedding_curve_log10": [2.0, 4.0, 6.5, 8.0, 8.5, 8.0, 7.0, 6.0, 5.0, 4.0, 3.5, 3.0, 2.5, 2.0, 2.0],
                "asymptomatic_shedding_log10": [2.0, 3.0, 4.5, 5.5, 6.0, 5.5, 5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 2.0, 2.0, 2.0],
                "dose_adjustment": 2.5,
                "dose_response": {"model": "beta_poisson", "alpha": 0.15, "beta": 45.0},
                "illness_probability": {"eta": 0.55, "gamma": 0.10},
                "recovery_day": 9,
                "surface_deposition_fraction": 0.08,
                "base_susceptibility": 1.0,
                "microflora_disruption": {
                    "causes_disruption": True,
                    "disruption_type": "systemic_fever",
                    "disruption_magnitude": 0.5,
                    "affected_kingdoms": {
                        "Bacteria": {"Staphylococcus_epi": 2.5},
                        "Virus": {"Phage_community": 1.2},
                    },
                },
                "food_contamination": {"enabled": False},
                "introduction_epoch": 0,
                "initial_infected": 1,
                "initial_time_infected": 0,
            },
            {
                "pathogen_id": "psi_2000_polywater",
                "name": "Psi-2000 Polywater Analog (fiction-adapted)",
                "category": "respiratory_viral",
                "transmission_routes": ["hvac_airborne", "droplet", "direct_contact", "fomite"],
                "shedding_curve_log10": [1.5, 3.5, 6.0, 7.5, 8.5, 9.0, 8.5, 7.5, 6.5, 5.5, 4.5, 3.5, 3.0, 2.5, 2.0],
                "asymptomatic_shedding_log10": [1.5, 3.0, 5.0, 6.5, 7.0, 6.5, 6.0, 5.5, 5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 2.0],
                "dose_adjustment": 1.8,
                "dose_response": {"model": "beta_poisson", "alpha": 0.12, "beta": 28.0},
                "illness_probability": {"eta": 0.70, "gamma": 0.08},
                "recovery_day": 5,
                "surface_deposition_fraction": 0.02,
                "base_susceptibility": 1.0,
                "microflora_disruption": {
                    "causes_disruption": True,
                    "disruption_type": "respiratory",
                    "disruption_magnitude": 0.35,
                    "affected_kingdoms": {
                        "Bacteria": {"Pseudoalteromonas": 1.8},
                        "Fungi": {"Aspergillus_spp": 1.5},
                    },
                },
                "food_contamination": {"enabled": False},
                "introduction_epoch": 3,
                "initial_infected": 1,
                "initial_time_infected": 0,
            },
        ],
    }


def tng_pathogens() -> dict:
    return {
        "meta": {
            "description": "TNG-inspired pathogen profiles (fiction-adapted)",
            "version": "1.0",
            "notes": "barclay_protomorphosis evokes Genesis; tng_shipboard_influenza evokes generic epidemic story beats.",
        },
        "pathogens": [
            {
                "pathogen_id": "barclay_protomorphosis",
                "name": "Barclay Protomorphosis Virus (fiction-adapted)",
                "category": "respiratory_viral",
                "transmission_routes": ["droplet", "hvac_airborne", "direct_contact", "fomite", "bodily_fluids"],
                "shedding_curve_log10": [2.5, 4.5, 7.0, 8.5, 9.5, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.5, 3.0, 2.5, 2.0],
                "asymptomatic_shedding_log10": [2.5, 4.0, 6.0, 7.0, 7.5, 7.0, 6.5, 6.0, 5.5, 5.0, 4.5, 4.0, 3.5, 3.0, 2.5],
                "dose_adjustment": 2.2,
                "dose_response": {"model": "beta_poisson", "alpha": 0.10, "beta": 22.0},
                "illness_probability": {"eta": 0.62, "gamma": 0.09},
                "recovery_day": 12,
                "surface_deposition_fraction": 0.04,
                "base_susceptibility": 1.0,
                "microflora_disruption": {
                    "causes_disruption": True,
                    "disruption_type": "systemic",
                    "disruption_magnitude": 0.75,
                    "affected_kingdoms": {
                        "Bacteria": {"Enterobacter": 3.0, "Staphylococcus_epi": 2.8},
                        "Fungi": {"Candida_spp": 2.2},
                        "Virus": {"ssRNA_marine": 2.0},
                    },
                },
                "food_contamination": {"enabled": False},
                "introduction_epoch": 0,
                "initial_infected": 1,
                "initial_time_infected": 0,
            },
            {
                "pathogen_id": "tng_shipboard_influenza",
                "name": "Shipboard Influenza Analog (fiction-adapted)",
                "category": "respiratory_viral",
                "transmission_routes": ["droplet", "hvac_airborne", "direct_contact", "fomite"],
                "shedding_curve_log10": [3.0, 5.0, 7.0, 8.5, 9.0, 8.5, 7.5, 6.5, 5.5, 4.5, 3.5, 3.0, 2.5, 2.0, 2.0],
                "asymptomatic_shedding_log10": [3.0, 4.5, 6.0, 7.0, 7.5, 7.0, 6.0, 5.0, 4.0, 3.5, 3.0, 2.5, 2.0, 2.0, 2.0],
                "dose_adjustment": 2.8,
                "dose_response": {"model": "beta_poisson", "alpha": 0.18, "beta": 55.0},
                "illness_probability": {"eta": 0.42, "gamma": 0.11},
                "recovery_day": 7,
                "surface_deposition_fraction": 0.03,
                "base_susceptibility": 1.0,
                "microflora_disruption": {
                    "causes_disruption": True,
                    "disruption_type": "respiratory",
                    "disruption_magnitude": 0.45,
                    "affected_kingdoms": {
                        "Bacteria": {"Haemophilus_influenzae": 1.5},
                        "Fungi": {"Aspergillus_spp": 1.0},
                    },
                },
                "food_contamination": {"enabled": False},
                "introduction_epoch": 8,
                "initial_infected": 2,
                "initial_time_infected": 0,
            },
        ],
    }


def tos_template() -> dict:
    return {
        "meta": {
            "description": "USS Enterprise (Constitution class, TOS) scenario bundle",
            "platform": "enterprise_constitution_tos",
            "fiction_note": "Human crew only; no android or alien-specific agent classes.",
        },
        "recommended_ship_graph": {
            "num_agents": 200,
            "agent_roles": {"passenger_fraction": 0.0, "crew_fraction": 1.0},
            "spatial_layout": "data/platforms/enterprise_constitution_tos/spatial_layout.json",
            "air_flow_paths": "data/platforms/enterprise_constitution_tos/air_flow_paths.json",
            "pathogen_profiles": "data/pathogens/enterprise_tos_profiles.json",
            "graywater_zones": ["Engineering"],
        },
        "agent_classes": [
            {"class_id": "crew_command", "role_group": "crew", "fraction": 0.08, "home_zone_preference": "Officer_Quarters", "free_zone_preference": "Bridge", "duty_zone": "Bridge"},
            {"class_id": "crew_helm_ops", "role_group": "crew", "fraction": 0.10, "home_zone_preference": "Crew_Quarters", "free_zone_preference": "Bridge", "duty_zone": "Bridge"},
            {"class_id": "crew_security", "role_group": "crew", "fraction": 0.08, "home_zone_preference": "Crew_Quarters", "free_zone_preference": "Security", "duty_zone": "Security_Station"},
            {"class_id": "crew_engineering", "role_group": "crew", "fraction": 0.18, "home_zone_preference": "Crew_Quarters", "free_zone_preference": "Engineering", "duty_zone": "Engineering"},
            {"class_id": "crew_sciences", "role_group": "crew", "fraction": 0.12, "home_zone_preference": "Officer_Quarters", "free_zone_preference": "Science", "duty_zone": "Science_Lab"},
            {"class_id": "crew_medical", "role_group": "crew", "fraction": 0.08, "home_zone_preference": "Officer_Quarters", "free_zone_preference": "Sickbay", "duty_zone": "Sickbay"},
            {"class_id": "crew_communications", "role_group": "crew", "fraction": 0.06, "home_zone_preference": "Crew_Quarters", "free_zone_preference": "Communications", "duty_zone": "Communications"},
            {"class_id": "crew_services", "role_group": "crew", "fraction": 0.10, "home_zone_preference": "Crew_Quarters", "free_zone_preference": "Galley", "duty_zone": "Galley"},
            {"class_id": "crew_general", "role_group": "crew", "fraction": 0.20, "home_zone_preference": "Crew_Quarters", "free_zone_preference": "Rec", "duty_zone": "Rec_Deck"},
        ],
        "gender_distribution": {"male": 0.52, "female": 0.48},
    }


def tng_template() -> dict:
    return {
        "meta": {
            "description": "USS Enterprise-D (Galaxy class, TNG) scenario bundle",
            "platform": "enterprise_galaxy_tng",
            "fiction_note": "Includes civilian families; excludes android-specific classes.",
        },
        "recommended_ship_graph": {
            "num_agents": 400,
            "agent_roles": {"passenger_fraction": 0.25, "crew_fraction": 0.75},
            "spatial_layout": "data/platforms/enterprise_galaxy_tng/spatial_layout.json",
            "air_flow_paths": "data/platforms/enterprise_galaxy_tng/air_flow_paths.json",
            "pathogen_profiles": "data/pathogens/enterprise_tng_profiles.json",
            "graywater_zones": ["Main_Engineering", "Cargo_Bay"],
        },
        "agent_classes": [
            {"class_id": "crew_command", "role_group": "crew", "fraction": 0.06, "home_zone_preference": "Crew_Quarters", "free_zone_preference": "Bridge", "duty_zone": "Bridge"},
            {"class_id": "crew_helm_ops", "role_group": "crew", "fraction": 0.06, "home_zone_preference": "Crew_Quarters", "free_zone_preference": "Bridge", "duty_zone": "Bridge"},
            {"class_id": "crew_security", "role_group": "crew", "fraction": 0.07, "home_zone_preference": "Crew_Quarters", "free_zone_preference": "Security", "duty_zone": "Security_Office"},
            {"class_id": "crew_engineering", "role_group": "crew", "fraction": 0.15, "home_zone_preference": "Crew_Quarters", "free_zone_preference": "Engineering", "duty_zone": "Main_Engineering"},
            {"class_id": "crew_sciences", "role_group": "crew", "fraction": 0.10, "home_zone_preference": "Crew_Quarters", "free_zone_preference": "Science", "duty_zone": "Science_Labs"},
            {"class_id": "crew_medical", "role_group": "crew", "fraction": 0.07, "home_zone_preference": "Crew_Quarters", "free_zone_preference": "Sickbay", "duty_zone": "Sickbay"},
            {"class_id": "crew_operations", "role_group": "crew", "fraction": 0.05, "home_zone_preference": "Crew_Quarters", "free_zone_preference": "Ten_Forward", "duty_zone": "Ten_Forward"},
            {"class_id": "crew_services", "role_group": "crew", "fraction": 0.09, "home_zone_preference": "Crew_Quarters", "free_zone_preference": "Galley", "duty_zone": "Galley"},
            {"class_id": "passenger_family", "role_group": "passenger", "fraction": 0.15, "home_zone_preference": "Family", "free_zone_preference": "School", "duty_zone": "Schoolroom"},
            {"class_id": "passenger_civilian", "role_group": "passenger", "fraction": 0.10, "home_zone_preference": "Family", "free_zone_preference": "Ten_Forward", "duty_zone": ""},
            {"class_id": "crew_general", "role_group": "crew", "fraction": 0.20, "home_zone_preference": "Crew_Quarters", "free_zone_preference": "Holodeck", "duty_zone": "Crew_Lounge"},
        ],
        "gender_distribution": {"male": 0.50, "female": 0.50},
    }


def main() -> None:
    tos_dir = os.path.join(DATA, "platforms", "enterprise_constitution_tos")
    tng_dir = os.path.join(DATA, "platforms", "enterprise_galaxy_tng")
    _write(os.path.join(tos_dir, "spatial_layout.json"), tos_spatial())
    _write(os.path.join(tos_dir, "air_flow_paths.json"), tos_airflow())
    _write(os.path.join(tng_dir, "spatial_layout.json"), tng_spatial())
    _write(os.path.join(tng_dir, "air_flow_paths.json"), tng_airflow())
    _write(os.path.join(DATA, "pathogens", "enterprise_tos_profiles.json"), tos_pathogens())
    _write(os.path.join(DATA, "pathogens", "enterprise_tng_profiles.json"), tng_pathogens())
    _write(os.path.join(DATA, "templates", "enterprise_constitution_tos.json"), tos_template())
    _write(os.path.join(DATA, "templates", "enterprise_galaxy_tng.json"), tng_template())
    print("Wrote Enterprise platforms, pathogens, and templates.")


if __name__ == "__main__":
    main()
