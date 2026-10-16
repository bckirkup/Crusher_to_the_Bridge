#!/usr/bin/env python3
"""Hull dynamics audit — the two dynamic realism checks (6-7).

Static audit (``tools/hull_audit.py``) reads the declared baseline; this
tool *runs* each hull:

Check 7 — retained-mass drainage fingerprint. Unit mass is injected into
every real zone and stepped through the native ``ContamTransportEngine``
with ``natural_decay_rate=0``: retained mass after N epochs is the hull's
drainage signature. ~1.0 retained = the network has no exhaust path (the
mass-trap class of defect that bit the cruise hulls); the per-zone
accumulation table names where it pools.

Check 6 — no-pathogen occupancy smoke. A 48-epoch voyage with zero
infectives; per-epoch zone occupancy is observed from agent locations.
Two arms per manifest-bearing hull:

* ``default`` — the engine's shipped ``ship_graph.agent_classes`` taxonomy
  (cruise hull classes: ``PC_``/``CC_`` home prefs, ``Medical_Center``/
  ``Engine``/``Galley`` duty). This is what a naval hull sails with today —
  substring prefs mostly miss naval zone ids and fall back to random
  draws, which the smoke makes *visible*.
* ``manifest`` — ``agent_classes`` generated from ``crew_manifest.json``
  (each class pins ``home_zone_preference``/``duty_zone`` to the manifest's
  exact zone ids). This is what the hull should sail like once the
  manifest is wired.

Findings: zones never entered (placement/adjacency errors), occupancy vs
rated ``max_occupancy`` overflow (``max_occupancy`` is a selection weight,
not a cap — real over-capacity shows up here), night-berthing
concentration, and per-arm berth fidelity (share of agents whose assigned
``home_zone`` is a manifest-declared berth zone; ~0% under the default
taxonomy is the manifest-wiring gap measured, not asserted).

Usage:
    python3 tools/hull_dynamics_audit.py [--platforms a,b] [--epochs 48]
        [--arms default,manifest|both] [--json-out F] [--md-out F]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engines.py_contam_bridge import ContamTransportEngine  # noqa: E402
from picard_framework.pathogen_overrides import (  # noqa: E402
    isolate_arm_overrides,
)
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils.paths import validated_open  # noqa: E402
from tools.diag.instrument_common import materialized_picard_spec  # noqa: E402
from tools.hull_audit import (  # noqa: E402
    PlatformBundle,
    _is_exterior,
    _zone_signature,
    load_platform,
)
from tools.noro_diag.per_host_dose_challenge import build_spec  # noqa: E402

PLATFORMS_DIR = REPO_ROOT / "data" / "platforms"
BUNDLE = "norwalk_only"
PATHOGEN_ID = "norwalk_gi"
NIGHT_HOURS = frozenset({22, 23, 0, 1, 2, 3, 4, 5})
_FILTER_EFFICIENCY = 0.50  # matches the ContamX divergence convention


# ---------------------------------------------------------------- drainage

def drainage_fingerprint(b: PlatformBundle, *, epochs: int = 48) -> dict[str, Any]:
    """Inject unit mass into every real zone; retention after `epochs` steps."""
    eng = ContamTransportEngine(
        b.spatial, b.airflow,
        filter_efficiency=_FILTER_EFFICIENCY, natural_decay_rate=0.0,
    )
    zones = eng._real_zone_ids
    mass = {z: 1.0 for z in zones}
    injected = float(len(zones))
    curve: list[dict[str, float]] = []
    marks = {12, 24, epochs}
    for step in range(1, epochs + 1):
        mass = eng.transport_step(mass, natural_decay_rate=0.0)
        if step in marks:
            curve.append({"epoch": step, "retained_frac": sum(mass.values()) / injected})
    top_sinks = sorted(mass.items(), key=lambda kv: -kv[1])[:5]
    return {
        "zones": len(zones),
        "retained_frac_final": sum(mass.values()) / injected,
        "curve": curve,
        "top_accumulating": [
            {"zone": z, "retained_mass": round(m, 4)} for z, m in top_sinks if m > 0.001
        ],
    }


# ---------------------------------------------------------------- occupancy

def _crew_source(b: PlatformBundle) -> tuple[int, str]:
    """num_agents for the smoke: manifest sum, else nominal complement."""
    manifest = b.manifest or {}
    rows = manifest.get("manifest") or []
    total = sum(int(r.get("count", 0) or 0) for r in rows)
    if total > 0:
        return total, "manifest"
    block = (b.spatial or {}).get("nominal_complement")
    if not isinstance(block, dict):
        return 0, "none"
    pax = block.get("passengers", 0) or 0
    crew = block.get("crew", 0) or 0
    return int(pax) + int(crew), "nominal_complement"


def _manifest_agent_classes(b: PlatformBundle) -> list[dict[str, Any]] | None:
    """crew_manifest -> ship_graph.agent_classes entries."""
    rows = (b.manifest or {}).get("manifest") or []
    total = sum(int(r.get("count", 0) or 0) for r in rows)
    if not rows or total <= 0:
        return None
    out = []
    for row in rows:
        count = int(row.get("count", 0) or 0)
        if count <= 0:
            continue
        out.append({
            "class_id": str(row.get("class_id", "cls")),
            "role_group": str(row.get("role_group", "crew")),
            "fraction": count / total,
            "home_zone_preference": str(row.get("berth_zone", "") or "Berthing"),
            "free_zone_preference": "",
            "duty_zone": str(row.get("duty_zone", "") or ""),
        })
    return out or None


def _null_infection_spec(platform: str, epochs: int, num_agents: int, seed: int) -> dict[str, Any]:
    spec = build_spec(
        seed=seed, platform=platform, bundle=BUNDLE, epochs=epochs,
        num_agents=num_agents, pathogen_id=PATHOGEN_ID,
        alpha=None, beta=0.0,
        high_touch_area_scale=None, high_touch_area_scale_by_zone_class=None,
        fomite_representation=None, fomite_touch_share=None,
        fomite_touch_share_table=None, cabin_confined_fomite=None,
    )
    spec["pathogen_overrides"] = isolate_arm_overrides(
        BUNDLE, PATHOGEN_ID, {PATHOGEN_ID: {"initial_infected": None}},
    )
    return spec


def _pin_resolution(b: PlatformBundle) -> dict[str, Any] | None:
    """Manifest pins vs the engine's real resolution domains.

    ``_resolve_class_zones`` resolves ``berth_zone``/``home_zone_preference``
    inside type Room/Cabin_Corridor zones, and ``duty_zone`` inside
    Free+Dining zones only. A pin outside its domain does not error — it
    silently degrades to a random draw. This measures that wiring gap
    statically (the occupancy smoke measures it dynamically).
    """
    rows = (b.manifest or {}).get("manifest") or []
    if not rows:
        return None
    types = {str(z.get("id") or z.get("name")): z.get("type") for z in b.zones}
    room = [z for z, t in types.items() if t in ("Room", "Cabin_Corridor")]
    work_domain = [z for z, t in types.items() if t in ("Free", "Dining")]

    def resolves(pin: str, domain: list[str]) -> bool:
        return any(pin.lower() in z.lower() for z in domain)

    bad_berth, bad_duty = [], []
    for row in rows:
        berth = str(row.get("berth_zone") or "")
        duty = str(row.get("duty_zone") or "")
        if berth and not resolves(berth, room):
            bad_berth.append({"class": row.get("class_id"), "pin": berth})
        if duty and not resolves(duty, work_domain):
            bad_duty.append({"class": row.get("class_id"), "pin": duty})
    return {"unresolvable_berth_pins": bad_berth,
            "unresolvable_duty_pins": bad_duty}


def _occupancy_smoke(b: PlatformBundle, *, epochs: int, seed: int,
                     arms: list[str]) -> dict[str, Any]:
    num_agents, source = _crew_source(b)
    if num_agents <= 0:
        return {"skipped": "no crew source (no manifest, no nominal_complement)"}
    manifest_classes = _manifest_agent_classes(b)
    manifest_berths = {
        str(r.get("berth_zone"))
        for r in (b.manifest or {}).get("manifest") or []
        if r.get("berth_zone")
    }
    zone_meta = {str(z.get("id") or z.get("name")): z for z in b.zones}
    results: dict[str, Any] = {
        "num_agents": num_agents,
        "crew_source": source,
        "pin_resolution": _pin_resolution(b),
    }

    for arm in arms:
        if arm == "manifest" and not manifest_classes:
            continue
        spec = _null_infection_spec(b.platform_id, epochs, num_agents, seed)
        if arm == "manifest":
            spec["config_overrides"].setdefault("ship_graph", {})[
                "agent_classes"
            ] = manifest_classes
        epoch_counts: list[Counter] = []
        home_counter: Counter = Counter()
        with materialized_picard_spec(spec, REPO_ROOT) as picard_spec:
            sim = ShipSimulation(picard_spec, display=False)

            def observer(sim_: Any, _work: Any) -> None:
                eng = sim_.engine
                per_zone: Counter = Counter()
                for a in eng.agents:
                    loc = getattr(a, "current_location", None) or "unknown"
                    per_zone[loc] += 1
                epoch_counts.append(per_zone)

            sim.epoch_observer = observer
            sim.run()
            for a in sim.engine.agents:
                home_counter[getattr(a, "home_zone", None) or "unknown"] += 1

        counts = defaultdict(set)
        for per_zone in epoch_counts:
            for z in per_zone:
                counts[z].add(1)
        visited = {z for z in counts if z not in ("Ashore", "Departed", "Isolated_In_Quarters")}
        interior = {z for z, m in zone_meta.items() if not _is_exterior(m)}
        never_occupied = sorted(
            z for z in interior if z not in visited
            and _zone_signature(zone_meta[z]) not in ("tank_hold", "magazine")
        )
        night_counts: Counter = Counter()
        zone_peak: Counter = Counter()
        for epoch_i, per_zone in enumerate(epoch_counts):
            if epoch_i % 24 in NIGHT_HOURS:
                night_counts.update(per_zone)
            for z, n in per_zone.items():
                if n > zone_peak[z]:
                    zone_peak[z] = n
        overflow = []
        for z, peak in zone_peak.items():
            meta = zone_meta.get(z)
            if not meta:
                continue
            cap = float(meta.get("max_occupancy") or 0) * max(
                int(meta.get("hot_bunk_ratio") or 1), 1)
            if cap > 0 and peak > cap:
                overflow.append({"zone": z, "peak": peak, "cap": cap})
        night_total = sum(night_counts.values()) or 1
        top_night = night_counts.most_common(3)
        berth_hits = sum(n for z, n in home_counter.items() if z in manifest_berths)
        results[arm] = {
            "visited_zones": len(visited),
            "never_occupied_interior": never_occupied,
            "overflow_zones": sorted(overflow, key=lambda r: -r["peak"] / r["cap"]),
            "night_top3": [
                {"zone": z, "share": round(n / night_total, 3)} for z, n in top_night
            ],
            "home_zone_distinct": len(home_counter),
            "home_on_manifest_berth_frac": round(berth_hits / num_agents, 3)
            if manifest_berths else None,
            "top_home_zones": [
                {"zone": z, "n": n} for z, n in home_counter.most_common(5)
            ],
        }
    return results


# ---------------------------------------------------------------- rendering

def render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = ["# Hull dynamics audit — fleet report", ""]
    lines.append("## Drainage fingerprint (check 7)")
    lines.append("")
    lines.append("| platform | zones | retained 12h | retained 24h | retained final | top accumulating |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        d = r.get("drainage") or {}
        if not d:
            continue
        curve = {c["epoch"]: c["retained_frac"] for c in d.get("curve", [])}
        top = ", ".join(
            f"{s['zone']}({s['retained_mass']:.0f})" for s in d.get("top_accumulating", [])[:3]
        )
        lines.append(
            f"| {r['platform']} | {d['zones']} | {curve.get(12, 0):.3f} | "
            f"{curve.get(24, 0):.3f} | {d['retained_frac_final']:.3f} | {top} |"
        )
    lines.append("")
    lines.append("## Occupancy smoke (check 6)")
    lines.append("")
    for r in rows:
        occ = r.get("occupancy") or {}
        if not occ or occ.get("skipped"):
            continue
        lines.append(f"### {r['platform']} ({occ.get('crew_source')}={occ.get('num_agents')})")
        pins = occ.get("pin_resolution") or {}
        for key, label in (
            ("unresolvable_berth_pins", "unresolvable berth pins"),
            ("unresolvable_duty_pins", "unresolvable duty pins"),
        ):
            bad = pins.get(key) or []
            if bad:
                lines.append(f"- **{label}: " + ", ".join(
                    f"{x['class']}→{x['pin']}" for x in bad[:8]) + "**")
        for arm, res in occ.items():
            if arm in ("num_agents", "crew_source", "pin_resolution"):
                continue
            lines.append(
                f"- `{arm}`: visited={res['visited_zones']} "
                f"never_occupied={len(res['never_occupied_interior'])} "
                f"overflow={len(res['overflow_zones'])} "
                f"home_distinct={res['home_zone_distinct']} "
                f"manifest_berth_hit={res['home_on_manifest_berth_frac']}"
            )
            if res["never_occupied_interior"]:
                lines.append(f"  - never entered: {', '.join(res['never_occupied_interior'][:8])}")
            if res["overflow_zones"]:
                lines.append("  - over cap: " + ", ".join(
                    f"{o['zone']} {o['peak']:.0f}/{o['cap']:.0f}"
                    for o in res["overflow_zones"][:5]))
            lines.append("  - night top: " + ", ".join(
                f"{t['zone']} {t['share']:.0%}" for t in res["night_top3"]))
    return "\n".join(lines) + "\n"


def _write(path: str, text: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    allowed = (str(out.parent.resolve()),)
    with validated_open(str(out), "w", allowed_roots=allowed, encoding="utf-8") as fh:
        fh.write(text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--platforms", default=None,
                    help="comma list; default = all dirs under data/platforms/")
    ap.add_argument("--epochs", type=int, default=48)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--arms", default="both",
                    choices=["default", "manifest", "both"])
    ap.add_argument("--skip-occupancy", action="store_true",
                    help="drainage fingerprint only")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--md-out", default=None)
    args = ap.parse_args(argv)

    if args.platforms:
        dirs = [PLATFORMS_DIR / p.strip() for p in args.platforms.split(",")]
    else:
        dirs = sorted(p for p in PLATFORMS_DIR.iterdir()
                      if (p / "spatial_layout.json").is_file())
    arms = ["default", "manifest"] if args.arms == "both" else [args.arms]

    rows: list[dict[str, Any]] = []
    for d in dirs:
        b = load_platform(d)
        row: dict[str, Any] = {"platform": b.platform_id}
        row["drainage"] = drainage_fingerprint(b, epochs=args.epochs)
        if not args.skip_occupancy:
            row["occupancy"] = _occupancy_smoke(
                b, epochs=args.epochs, seed=args.seed, arms=arms)
        rows.append(row)
        drain = row["drainage"]
        print(f"{b.platform_id}: retained={drain['retained_frac_final']:.3f} "
              f"zones={drain['zones']}", file=sys.stderr, flush=True)

    md = render_markdown(rows)
    if args.md_out:
        _write(args.md_out, md)
    else:
        print(md)
    if args.json_out:
        _write(args.json_out, json.dumps({"rows": rows}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
