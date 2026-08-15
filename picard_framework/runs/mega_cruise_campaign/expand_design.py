"""Expand a sentinel recovery design spec into a campaign manifest.

A design spec (``*_design.json``, validated by
``schemas/sentinel_recovery_design.schema.json``) declares the port registry,
itinerary templates, hazard profiles, fleet configurations, R_onboard levels
and seeds once. This module expands it into the tier-per-cell manifest that
``campaign_runner`` consumes, so the runnable artifact is generated from the
design rather than transcribed alongside it.

Usage::

    python3 -m picard_framework.runs.mega_cruise_campaign.expand_design \\
        --design picard_framework/runs/mega_cruise_campaign/\\
sentinel_synthetic_recovery_v1_design.json --check

``--check`` compares the expansion against the manifest on disk and exits
non-zero on drift; ``--out`` writes the manifest.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from simulation_utils.paths import prepare_output_directory, validated_open

CAMPAIGN_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CAMPAIGN_DIR)))
_PORT_DAY_FIELDS = (
    "port",
    "region",
    "disembark_fraction",
    "crew_shore_leave_fraction",
    "disembark_window_epochs",
    "reembark_window_epochs",
)


def load_json(path: str) -> dict[str, Any]:
    """Read a JSON document confined to the repository."""
    with validated_open(
        path, encoding="utf-8", allowed_roots=(REPO_ROOT,),
    ) as handle:
        return dict(json.load(handle))


def _require(mapping: dict[str, Any], key: str, label: str) -> Any:
    if key not in mapping:
        raise ValueError(f"{label} is missing required key {key!r}")
    return mapping[key]


def _homeport_slot(design: dict[str, Any], kind: str, day: int) -> dict[str, Any]:
    """Embarkation/disembarkation day slot from the design's homeport block."""
    spec = dict(_require(_require(design, "homeport", "design"), kind, "homeport"))
    port_id = str(_require(spec, "port_id", f"homeport.{kind}"))
    port = dict(_require(_require(design, "ports", "design"), port_id, "ports"))
    slot: dict[str, Any] = {"day": day, "type": kind}
    slot["port"] = port["port"]
    slot["port_id"] = port_id
    slot["region"] = port["region"]
    for key, value in spec.items():
        if key != "port_id":
            slot[key] = value
    return slot


def _port_day_slot(design: dict[str, Any], day: int, port_id: str) -> dict[str, Any]:
    """Port-call day slot built from the port registry entry."""
    ports = _require(design, "ports", "design")
    if port_id not in ports:
        raise ValueError(f"itinerary references unknown port_id {port_id!r}")
    port = dict(ports[port_id])
    slot: dict[str, Any] = {"day": day, "type": "port_day"}
    slot["port"] = port["port"]
    slot["port_id"] = port_id
    for key in _PORT_DAY_FIELDS:
        if key == "port" or key not in port:
            continue
        slot[key] = port[key]
    return slot


def build_template_days(
    design: dict[str, Any],
    template: dict[str, Any],
) -> list[dict[str, Any]]:
    """Expand one itinerary template into ordered voyage day slots."""
    length = int(_require(template, "length_days", "itinerary template"))
    port_days = {
        int(day): str(port_id)
        for day, port_id in _require(template, "port_days", "itinerary template").items()
    }
    if any(day <= 1 or day >= length for day in port_days):
        raise ValueError(
            "port_days must fall strictly between embarkation and disembarkation",
        )
    days: list[dict[str, Any]] = []
    for day in range(1, length + 1):
        if day == 1:
            days.append(_homeport_slot(design, "embarkation", day))
        elif day == length:
            days.append(_homeport_slot(design, "disembarkation", day))
        elif day in port_days:
            days.append(_port_day_slot(design, day, port_days[day]))
        else:
            days.append({"day": day, "type": "sea_day"})
    return days


def build_itinerary_templates(design: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Resolve every declared itinerary template to day slots."""
    templates = _require(design, "itinerary_templates", "design")
    return {
        name: build_template_days(design, dict(template))
        for name, template in templates.items()
    }


def _seed_list(design: dict[str, Any]) -> list[int]:
    seeds = _require(design, "seeds", "design")
    if isinstance(seeds, list):
        return [int(seed) for seed in seeds]
    start = int(_require(seeds, "start", "seeds"))
    count = int(_require(seeds, "count", "seeds"))
    if count <= 0:
        raise ValueError("seeds.count must be positive")
    return [start + offset for offset in range(count)]


def _validate_fleet(
    design: dict[str, Any],
    fleet_name: str,
    fleet: dict[str, Any],
) -> list[dict[str, Any]]:
    ships = [dict(ship) for ship in _require(fleet, "ships", f"fleet {fleet_name}")]
    if not ships:
        raise ValueError(f"fleet config {fleet_name!r} has no ships")
    templates = _require(design, "itinerary_templates", "design")
    for ship in ships:
        itinerary = str(_require(ship, "itinerary", f"fleet {fleet_name} ship"))
        if itinerary not in templates:
            raise ValueError(
                f"fleet config {fleet_name!r} references unknown itinerary {itinerary!r}",
            )
    return ships


def _hazard_ports(design: dict[str, Any], profile_name: str) -> dict[str, float]:
    profile = _require(
        _require(design, "hazard_profiles", "design"), profile_name, "hazard_profiles",
    )
    hazards = {
        str(port_id): float(value)
        for port_id, value in _require(
            profile, "port_hazards", f"hazard profile {profile_name}",
        ).items()
    }
    ports = _require(design, "ports", "design")
    unknown = sorted(set(hazards) - set(ports))
    if unknown:
        raise ValueError(
            f"hazard profile {profile_name!r} references unknown ports: {unknown}",
        )
    if any(value < 0.0 for value in hazards.values()):
        raise ValueError(f"hazard profile {profile_name!r} has a negative hazard")
    return hazards


def build_tier(
    design: dict[str, Any],
    hazard_name: str,
    fleet_name: str,
) -> dict[str, Any]:
    """One manifest tier: a hazard profile crossed with a fleet configuration."""
    fleet = dict(_require(design, "fleet_configs", "design")[fleet_name])
    ships = _validate_fleet(design, fleet_name, fleet)
    return {
        "description": f"Hazard={hazard_name}, Fleet={fleet_name}",
        "pathogen": str(_require(design, "pathogen", "design")),
        "hazard_profile": hazard_name,
        "fleet_config": fleet_name,
        "platforms": [str(ship["platform"]) for ship in ships],
        "itineraries": [str(ship["itinerary"]) for ship in ships],
        "shore_exposure": {
            "enabled": True,
            "port_hazards": _hazard_ports(design, hazard_name),
        },
        "R_onboard_values": [
            float(value) for value in _require(design, "R_onboard_values", "design")
        ],
        "seeds": _seed_list(design),
        "epochs": int(_require(design, "default_epochs", "design")),
    }


def build_manifest(design: dict[str, Any]) -> dict[str, Any]:
    """Expand a design spec into the campaign manifest the runner consumes."""
    seeds = _seed_list(design)
    r_values = list(_require(design, "R_onboard_values", "design"))
    tiers: dict[str, Any] = {}
    total = 0
    for hazard_name in _require(design, "hazard_profiles", "design"):
        for fleet_name in _require(design, "fleet_configs", "design"):
            tier = build_tier(design, hazard_name, fleet_name)
            tiers[f"sr_{hazard_name}_{fleet_name}"] = tier
            total += len(tier["platforms"]) * len(r_values) * len(seeds)
    return {
        "campaign": str(_require(design, "campaign", "design")),
        "description": str(design.get("description", "")),
        "generated_from": os.path.basename(
            str(design.get("design_file", "sentinel_synthetic_recovery_v1_design.json")),
        ),
        "platform": str(_require(design, "platform", "design")),
        "default_epochs": int(_require(design, "default_epochs", "design")),
        "default_num_agents": int(_require(design, "default_num_agents", "design")),
        "embarkation_date": str(_require(design, "embarkation_date", "design")),
        "pathogen_configs": _require(design, "pathogen_configs", "design"),
        "surveillance_configs": _require(design, "surveillance_configs", "design"),
        "defaults": _require(design, "defaults", "design"),
        "itinerary_templates": build_itinerary_templates(design),
        "tiers": tiers,
        "total_runs": total,
    }


def manifest_from_design_file(design_path: str) -> dict[str, Any]:
    """Load a design file and expand it, recording the source file name."""
    design = load_json(design_path)
    design["design_file"] = os.path.basename(design_path)
    return build_manifest(design)


def write_manifest(manifest: dict[str, Any], out_path: str) -> str:
    """Write *manifest* as formatted JSON inside the repository."""
    resolved = os.path.abspath(out_path)
    prepare_output_directory(os.path.dirname(resolved), allowed_roots=(REPO_ROOT,))
    with validated_open(
        resolved, mode="w", encoding="utf-8", allowed_roots=(REPO_ROOT,),
    ) as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    return resolved


def _default_manifest_path(design_path: str) -> str:
    name = os.path.basename(design_path).replace("_design.json", "_manifest.json")
    return os.path.join(os.path.dirname(os.path.abspath(design_path)), name)


def report_drift(expected: dict[str, Any], actual: dict[str, Any]) -> int:
    if expected == actual:
        print(f"manifest matches design: {expected['total_runs']} runs")
        return 0
    print("manifest does not match the expansion of its design spec")
    for key in sorted(set(expected) | set(actual)):
        if expected.get(key) != actual.get(key):
            print(f"  differs: {key}")
    return 1


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", required=True, help="design spec JSON path")
    parser.add_argument("--out", default=None, help="manifest path to write")
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare against the manifest on disk instead of writing it",
    )
    args = parser.parse_args(argv)
    manifest = manifest_from_design_file(args.design)
    target = args.out or _default_manifest_path(args.design)
    if args.check:
        return report_drift(manifest, load_json(target))
    written = write_manifest(manifest, target)
    print(f"wrote {written}: {manifest['total_runs']} runs")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    sys.exit(main())
