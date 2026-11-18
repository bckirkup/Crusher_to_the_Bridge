#!/usr/bin/env python3
"""ROOM-AIR-01-AMBIENT-EXCHANGE-01 attribution evidence.

Declared before the runs (stochastic-attribution Rule A):

* arms: ``ambient_off`` = labelled pre-change HVAC-only ACH map;
  ``ambient_on`` = ``build_zone_air_exchange_map`` with positive
  ``ambient_openings`` exchange added as ``sum(exchange_m3h)/volume_m3``.
* paired seeds: the same seed list on both arms, compared seed by seed.
* statistic: the COVID hull witness fields from ``simulate_hull`` plus the
  ACH/residence-factor map census; paired differences are arm_on - arm_off.
* effect threshold: an opened-deck zone is attributed when its residence
  factor falls by the declared exchange ratio (fleet evidence: about
  10-586x); a stochastic move inside the 5-13% stream-disruption band with
  no opened-deck dose witness is reported as unattributed, not as the
  mechanism.
* norovirus gate: ``norwalk_gi`` is ``emesis_conditioned``; the continuous
  droplet share is zero by ``_droplet_emission_fraction`` and the near field
  refuses it by ``_near_field_admits``. The only residence-factor consumer
  left is the per-emesis bolus, so a continuous-emission null is the
  declared expectation; any material norovirus move is a finding.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_OUT = (
    REPO_ROOT
    / "docs/audits/2026-11-18_room_air_01_ambient_exchange/evidence"
    / "ambient_exchange_attribution.json"
)


def _residence_factor(ach: float, hours: float = 1.0) -> float:
    x = max(float(ach), 0.0) * float(hours)
    if x <= 0.0:
        return 1.0
    return -math.expm1(-x) / x


def _hvac_only_zone_air_exchange_map(airflow_paths: dict) -> dict[str, float]:
    """Labelled pre-change ROOM-AIR-01 map: HVAC ACH only, no openings."""
    default_duty = float(airflow_paths.get("hvac_duty", 1.0))
    default_oa = float(airflow_paths.get("oa_fraction", 0.2))
    rates: dict[str, float] = {}
    for hvac_zone in airflow_paths.get("hvac_zones", []):
        ach = float(hvac_zone.get("ach", 6.0))
        duty = max(float(hvac_zone.get("hvac_duty", default_duty)), 0.0)
        oa = float(hvac_zone.get("oa_fraction", default_oa))
        rate = ach * duty
        if duty <= 0.0 and oa >= 1.0:
            rate = ach
        for room in hvac_zone.get("rooms", []):
            rates[room] = rate
    return rates


def _map_builder(mode: str):
    def _build(airflow_paths, zone_volumes=None, ambient_exchange_m3h=None):
        if mode == "ambient_off":
            return _hvac_only_zone_air_exchange_map(airflow_paths)
        from engines.transmission_core import build_zone_air_exchange_map

        return build_zone_air_exchange_map(
            airflow_paths,
            zone_volumes=zone_volumes,
            ambient_exchange_m3h=ambient_exchange_m3h,
        )

    return _build


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _safe_output_path(path: Path) -> Path:
    candidate = path if path.is_absolute() else REPO_ROOT / path
    resolved = candidate.resolve()
    if not resolved.is_relative_to(REPO_ROOT):
        raise ValueError(f"--out must stay under the repository root: {path}")
    return resolved


def _platform_paths(platform_id: str) -> tuple[Path, Path, Path]:
    root = REPO_ROOT / "data" / "platforms" / platform_id
    return (
        root / "air_flow_paths.json",
        root / "spatial_layout.json",
        root / "platform_config.json",
    )


def _zone_volumes(spatial_layout: dict) -> dict[str, float]:
    return {
        str(zone.get("id")): float(zone.get("volume_m3", 0.0) or 0.0)
        for zone in spatial_layout.get("zones", [])
        if zone.get("id") is not None
    }


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(math.ceil(q * len(ordered))) - 1))
    return ordered[idx]


def map_census(platform_ids: list[str] | None = None) -> dict:
    from engines.py_contam_bridge import (
        ambient_opening_records,
        parse_ambient_exchange_axis,
    )

    platforms_root = REPO_ROOT / "data" / "platforms"
    if platform_ids is None:
        platform_ids = sorted(
            path.parent.name
            for path in platforms_root.glob("*/air_flow_paths.json")
        )
    rows = []
    for platform_id in platform_ids:
        airflow_path, layout_path, config_path = _platform_paths(platform_id)
        if not airflow_path.exists():
            continue
        airflow = _read_json(airflow_path)
        records = ambient_opening_records(airflow)
        if not records:
            continue
        layout = _read_json(layout_path) if layout_path.exists() else {}
        config = _read_json(config_path) if config_path.exists() else {}
        hvac_cfg = config.get("hvac", {}) if isinstance(config, dict) else {}
        axis = parse_ambient_exchange_axis(hvac_cfg if isinstance(hvac_cfg, dict) else {})
        from engines.transmission_core import build_zone_air_exchange_map

        old = _hvac_only_zone_air_exchange_map(airflow)
        new = build_zone_air_exchange_map(
            airflow,
            zone_volumes=_zone_volumes(layout),
            ambient_exchange_m3h=axis,
        )
        for zone in sorted(set(old) | set(new)):
            old_ach = float(old.get(zone, 0.0))
            new_ach = float(new.get(zone, 0.0))
            if abs(new_ach - old_ach) <= 1e-12:
                continue
            old_f = _residence_factor(old_ach)
            new_f = _residence_factor(new_ach)
            rows.append({
                "platform": platform_id,
                "zone": zone,
                "ach_old": old_ach,
                "ach_new": new_ach,
                "factor_old": old_f,
                "factor_new": new_f,
                "factor_ratio": (old_f / new_f) if new_f > 0.0 else None,
            })
    ratios = [row["factor_ratio"] for row in rows if row["factor_ratio"]]
    return {
        "platforms_with_ambient_openings": len(
            {row["platform"] for row in rows}
        ),
        "changed_zone_rows": len(rows),
        "factor_ratio_min": min(ratios) if ratios else None,
        "factor_ratio_median": _median(ratios),
        "factor_ratio_p90": _percentile(ratios, 0.90),
        "factor_ratio_max": max(ratios) if ratios else None,
        "rows": rows,
    }


def _simulate_hull_with_map_mode(
    scenario_id: str,
    theta: float,
    seed: int,
    mode: str,
    num_epochs: int | None = None,
):
    import picard_framework.covid_theta_fit as ctf
    import picard_framework.simulation.ship_simulation as ship_simulation

    with patch.object(
        ship_simulation,
        "build_zone_air_exchange_map",
        _map_builder(mode),
    ):
        return ctf.simulate_hull(
            scenario_id, theta, seed, num_epochs=num_epochs,
        )


def paired_hull_runs(
    scenario_id: str,
    theta: float,
    seeds: list[int],
    num_epochs: int | None = None,
) -> dict:
    rows = []
    for seed in seeds:
        for mode in ("ambient_off", "ambient_on"):
            kwargs = {}
            if num_epochs is not None:
                kwargs["num_epochs"] = num_epochs
            obs = _simulate_hull_with_map_mode(
                scenario_id, theta, seed, mode, **kwargs,
            )
            rows.append({"arm": mode, **obs.as_dict()})
    by_seed = {}
    for seed in seeds:
        off = next(r for r in rows if r["seed"] == seed and r["arm"] == "ambient_off")
        on = next(r for r in rows if r["seed"] == seed and r["arm"] == "ambient_on")
        fields = [
            "recorded_onsets", "onsets_before_split_day",
            "onsets_on_or_after_split_day", "campaign_specimens",
            "campaign_positives", "campaign_asymptomatic_positives",
        ]
        by_seed[str(seed)] = {
            "ambient_off": {k: off[k] for k in fields},
            "ambient_on": {k: on[k] for k in fields},
            "paired_delta_on_minus_off": {
                k: int(on[k]) - int(off[k]) for k in fields
            },
        }
    return {"scenario_id": scenario_id, "theta": theta, "seeds": seeds, "by_seed": by_seed, "rows": rows}


def norovirus_route_gate() -> dict:
    profiles = _read_json(REPO_ROOT / "data/pathogens/active_profiles.json")
    profile = next(
        p for p in profiles["pathogens"] if p["pathogen_id"] == "norwalk_gi"
    )
    return {
        "pathogen_id": "norwalk_gi",
        "airborne_emission_mode": profile.get("airborne_emission_mode"),
        "has_airborne_emission_fraction": "airborne_emission_fraction" in profile,
        "expected": (
            "zero continuous droplet/aerosol feed; only the per-emesis "
            "bolus consumes _room_air_residence_factor"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--platform", action="append", dest="platforms")
    parser.add_argument("--scenario", default="greg_mortimer_2020")
    parser.add_argument("--theta", type=float, default=1e10)
    parser.add_argument("--seeds", type=int, nargs="+", default=[20200333, 20200334])
    parser.add_argument("--num-epochs", type=int, default=None)
    parser.add_argument("--skip-hull", action="store_true")
    args = parser.parse_args(argv)

    payload = {
        "criterion": {
            "arms": ["ambient_off", "ambient_on"],
            "paired_seeds": args.seeds,
            "statistic": "paired seed-by-seed witness deltas + ACH map census",
            "effect_threshold": "opened-deck residence factor ratio matches declared exchange; stochastic move outside 5-13% stream band is unattributed",
            "null_expectation": "zones without openings byte-identical; norwalk_gi continuous airborne feed zero",
        },
        "map_census": map_census(args.platforms),
        "norovirus_route_gate": norovirus_route_gate(),
    }
    if not args.skip_hull:
        payload["paired_hull_runs"] = paired_hull_runs(
            args.scenario, args.theta, args.seeds, args.num_epochs,
        )
    out = _safe_output_path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "out": str(out),
        "changed_zone_rows": payload["map_census"]["changed_zone_rows"],
        "factor_ratio_min": payload["map_census"]["factor_ratio_min"],
        "factor_ratio_median": payload["map_census"]["factor_ratio_median"],
        "factor_ratio_max": payload["map_census"]["factor_ratio_max"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
