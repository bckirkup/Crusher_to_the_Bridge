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


def _seed_values(seeds: Any, label: str = "seeds") -> list[int]:
    """Seed list from either an explicit list or a ``{start, count}`` range."""
    if isinstance(seeds, list):
        return [int(seed) for seed in seeds]
    start = int(_require(seeds, "start", label))
    count = int(_require(seeds, "count", label))
    if count <= 0:
        raise ValueError(f"{label}.count must be positive")
    return [start + offset for offset in range(count)]


def _seed_list(design: dict[str, Any]) -> list[int]:
    return _seed_values(_require(design, "seeds", "design"), "seeds")


def _residence_tag(hours: float) -> str:
    """Run-id-safe tag for a residence time in hours (0.5 -> ``r0p5``)."""
    return "r" + f"{float(hours):g}".replace(".", "p")


def _ww_cell(
    block: str,
    cell_id: str,
    base: dict[str, Any],
    overrides: dict[str, Any],
    seeds: list[int],
) -> dict[str, Any]:
    """One scan cell: an operating point plus the seeds it is replicated over."""
    return {
        "cell_id": cell_id,
        "block": block,
        "seeds": list(seeds),
        "wastewater_surveillance": {**base, **overrides},
    }


def _core_cells(
    scan: dict[str, Any],
    base: dict[str, Any],
    seeds: list[int],
) -> list[dict[str, Any]]:
    """Cadence x residence grid: the interaction the scan exists to measure."""
    intervals = [
        int(v) for v in _require(scan, "sampling_interval_epochs", "wastewater_scan")
    ]
    residences = [
        float(v)
        for v in _require(scan, "holding_tank_residence_hours", "wastewater_scan")
    ]
    return [
        _ww_cell(
            "core",
            f"core_f{interval}_{_residence_tag(residence)}",
            base,
            {
                "sampling_interval_epochs": interval,
                "holding_tank_residence_hours": residence,
            },
            seeds,
        )
        for interval in intervals
        for residence in residences
    ]


def _depth_cells(
    scan: dict[str, Any],
    base: dict[str, Any],
    seeds: list[int],
) -> list[dict[str, Any]]:
    """Depth sensitivity at a fixed cadence and two residence levels."""
    block = scan.get("depth_sensitivity")
    if not block:
        return []
    interval = int(_require(block, "sampling_interval_epochs", "depth_sensitivity"))
    depths = [int(v) for v in _require(block, "sequencing_depth", "depth_sensitivity")]
    residences = [
        float(v)
        for v in _require(block, "holding_tank_residence_hours", "depth_sensitivity")
    ]
    return [
        _ww_cell(
            "depth",
            f"depth_d{depth}_{_residence_tag(residence)}",
            base,
            {
                "sampling_interval_epochs": interval,
                "holding_tank_residence_hours": residence,
                "sequencing_depth": depth,
            },
            seeds,
        )
        for depth in depths
        for residence in residences
    ]


def _collection_cells(
    scan: dict[str, Any],
    base: dict[str, Any],
    seeds: list[int],
) -> list[dict[str, Any]]:
    """Spatial resolution: one tap vs several, at the reference operating point."""
    block = scan.get("collection_sensitivity")
    if not block:
        return []
    interval = int(_require(block, "sampling_interval_epochs", "collection_sensitivity"))
    residence = float(
        _require(block, "holding_tank_residence_hours", "collection_sensitivity"),
    )
    tag = _residence_tag(residence)
    cells = []
    for points in _require(block, "collection_points", "collection_sensitivity"):
        names = [str(point) for point in points]
        cells.append(
            _ww_cell(
                "collection",
                f"collection_p{len(names)}_f{interval}_{tag}",
                base,
                {
                    "sampling_interval_epochs": interval,
                    "holding_tank_residence_hours": residence,
                    "collection_points": names,
                },
                seeds,
            ),
        )
    return cells


def _control_cells(
    scan: dict[str, Any],
    base: dict[str, Any],
    seeds: list[int],
) -> list[dict[str, Any]]:
    """Clinical-only control: the baseline every coverage gain is measured from."""
    if not scan.get("include_control", True):
        return []
    return [_ww_cell("control", "control_clinical_only", base, {"enabled": False}, seeds)]


def build_wastewater_cells(design: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand a ``wastewater_scan`` block into per-run operating points.

    The blocks are deliberately unbalanced. The cadence x residence core carries
    the full seed count because that is where the answer lives; depth and
    collection are one-factor slices off a reference cell with fewer seeds. A
    full cartesian of every factor would cost roughly an order of magnitude more
    runs to answer questions the core grid already conditions on.
    """
    scan = design.get("wastewater_scan")
    if not scan:
        return []
    base = dict(_require(scan, "base_wastewater", "wastewater_scan"))
    core_seeds = _seed_values(
        _require(scan, "core_seeds", "wastewater_scan"), "core_seeds",
    )
    sens_seeds = _seed_values(
        scan.get("sensitivity_seeds", scan.get("core_seeds")), "sensitivity_seeds",
    )
    cells = [
        *_core_cells(scan, base, core_seeds),
        *_depth_cells(scan, base, sens_seeds),
        *_collection_cells(scan, base, sens_seeds),
        *_control_cells(scan, base, core_seeds),
    ]
    ids = [cell["cell_id"] for cell in cells]
    if len(set(ids)) != len(ids):
        raise ValueError("wastewater_scan produced duplicate cell ids")
    return cells


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
    cells = build_wastewater_cells(design)
    tier: dict[str, Any] = {
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
    if cells:
        # Present only for wastewater scans, so existing manifests expand byte
        # for byte and the runner can tell the two campaign shapes apart.
        tier["wastewater_cells"] = cells
    return tier


def tier_run_count(tier: dict[str, Any], r_values: list[Any], seeds: list[int]) -> int:
    """Runs a tier generates: platform x R_onboard x (cells x their own seeds).

    Scan cells carry their own seed lists because the core grid and the
    sensitivity arms are replicated differently, so the tier's shared seed list
    only counts when there are no cells.
    """
    cells = tier.get("wastewater_cells")
    per_platform = (
        sum(len(cell["seeds"]) for cell in cells) if cells else len(seeds)
    )
    return len(tier["platforms"]) * len(r_values) * per_platform


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
            total += tier_run_count(tier, r_values, seeds)
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
