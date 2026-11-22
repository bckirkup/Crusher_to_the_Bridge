#!/usr/bin/env python3
"""DP-REPLAY-ENVIRON-01 local movement acceptance harness.

Runs the ``covid_dp_replay_01_design.json`` replay arm with the seed
initiation emptied — a declared no-transmission voyage, so placements are
pure dealt behavior — and reports, as JSON:

- per-role daily person-hours by location class (cabin / dining /
  indoor_free / outdoor / corridor / ashore / other), split
  pre-quarantine (days 1-15) vs quarantine (days 16+), against the
  Kosmos budget (cabin 15, indoor 5.5, dining 2.25, transit 0.75,
  outdoor 0.5);
- the confinement witness at epoch 391 (fraction of aboard passengers in
  their home zone before and after activation);
- ashore turnout on port days vs the declared 0.5 participation;
- exercise-outing telemetry (invited / willing / attended / group caps)
  versus the spec §6 entitlement shape.

Readout only — nothing here is scored against an epidemiological anchor.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
)

_OUTDOOR_ZONES = {
    "OceanFront", "TerracePool", "OpenAirCinema", "NeptunePool",
    "HorizonTerrace", "SportsCourt", "CenterCourt", "CalypsoPool",
}
_CORRIDOR_ZONES = {
    "GrandPlaza", "PromGalleria", "GuestServices", "Stairs",
}
_ASHORE = "Ashore"


class MovementLedger:
    """Epoch observer: aggregate person-hours by role x location class."""

    def __init__(self, zone_meta: dict[str, str], home_zones: dict[int, str]):
        self.zone_meta = zone_meta
        self.home_zones = home_zones
        # hours[(role, day_bucket)][loc_class] += agents aboard that epoch
        self.hours: dict[str, dict[str, float]] = {}
        self.ashore_by_day: dict[int, list[int]] = {}
        self.home_fraction: dict[int, tuple[int, int]] = {}

    def classify(self, loc: str, agent: object) -> str:
        if loc == _ASHORE:
            return "ashore"
        if loc in ("Isolated_In_Quarters",):
            return "isolated"
        meta = self.zone_meta.get(loc)
        if meta is None:
            return "other"
        if meta == "Cabin_Corridor":
            return "cabin" if loc == self.home_zones.get(
                getattr(agent, "agent_id", -1),
            ) else "corridor"
        if meta == "Dining":
            return "dining"
        if meta == "Sanitary":
            return "sanitary"
        if meta == "Medical":
            return "medical"
        if loc in _OUTDOOR_ZONES:
            return "outdoor"
        if loc in _CORRIDOR_ZONES:
            return "corridor"
        return "indoor_free"

    def observe(self, sim: object, work: object) -> None:
        engine = sim.engine
        epoch = int(getattr(sim, "epoch", getattr(engine, "epoch", 0)))
        day = epoch // 24  # clock-exempt: epoch→day index, not a unit conversion
        # Quarantine hours are whatever the arm's own schedule activates:
        # the dedicated order binds at epoch 391 (day 16, 07:00) while the
        # shipped baseline binds whole-day at day 16 — bucket by the live
        # SOP set, not a fixed window.
        active = getattr(engine, "active_sop_names", None) or []
        if any("Cabin Quarantine" in str(name) for name in active):
            bucket = "quarantine"
        elif day == 0:
            bucket = "day0"
        elif epoch < 391:
            bucket = "pre_quarantine"
        else:
            bucket = "post_release"
        aboard_pax = confined = 0
        for agent in engine.agents:
            role = str(getattr(agent, "role", "crew"))
            loc = str(getattr(agent, "current_location", ""))
            cls = self.classify(loc, agent)
            key = f"{role}|{bucket}"
            self.hours.setdefault(key, {})[cls] = (
                self.hours.setdefault(key, {}).get(cls, 0.0) + 1.0
            )
            if role == "passenger":
                day_ashore = self.ashore_by_day.setdefault(day, [0, 0])
                if loc == _ASHORE:
                    day_ashore[0] += 1
                else:
                    day_ashore[1] += 1
                if loc != _ASHORE:
                    aboard_pax += 1
                    if loc == self.home_zones.get(agent.agent_id):
                        confined += 1
        if aboard_pax:
            prev = self.home_fraction.get(epoch)
            if prev is None:
                self.home_fraction[epoch] = (confined, aboard_pax)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--design",
        default="picard_framework/runs/covid_dp_replay_01_design.json",
    )
    parser.add_argument("--arm", default="replay_niid")
    parser.add_argument("--seed", type=int, default=20200205)
    parser.add_argument(
        "--num-epochs", type=int, default=None,
        help="cap the voyage for a smoke pass",
    )
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    design = load_design(args.design)
    matches = [
        c for c in enumerate_cells(design)
        if c.arm_id == args.arm and c.seed == args.seed
    ]
    if len(matches) != 1:
        raise SystemExit(f"{len(matches)} cells match arm={args.arm}")
    cell = matches[0]
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=args.num_epochs, repo_root=str(_REPO_ROOT),
    )
    # Declared no-transmission acceptance: no infectives ever exist, so
    # placements are the dealt schedule alone. The screen writes the index
    # under config_overrides.initiation; clear every level it could sit at.
    overrides = raw.setdefault("config_overrides", {})
    for container in (raw, overrides):
        initiation = container.get("initiation") or {}
        initiation["explicit_seeds"] = []
        container["initiation"] = initiation

    platform_id = str(
        raw.get("platform_id")
        or (raw.get("config_overrides") or {}).get("platform_id")
        or "diamond_princess"
    )
    layout = json.loads(
        (_REPO_ROOT / "data/platforms" / platform_id / "spatial_layout.json")
        .read_text(),
    )
    zone_meta = {str(z["id"]): str(z.get("type")) for z in layout["zones"]}

    import contextlib  # noqa: E402
    import io  # noqa: E402

    from picard_framework.run_spec import PicardRunSpec  # noqa: E402
    from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402

    spec = PicardRunSpec.from_picard_dict(str(_REPO_ROOT), raw)
    with contextlib.redirect_stdout(io.StringIO()):
        sim = ShipSimulation(spec, display=False)
        sim.initialize()
    home_zones = {
        int(a.agent_id): str(getattr(a, "home_zone", "") or "")
        for a in sim.engine.agents
    }
    ledger = MovementLedger(zone_meta, home_zones)
    sim.epoch_observer = ledger.observe
    with contextlib.redirect_stdout(io.StringIO()):
        for _ in range(sim.num_epochs):
            sim.step()

    rhythm = getattr(sim.engine, "_rhythm", None)
    exercise = getattr(rhythm, "exercise_telemetry", None)
    conf_epochs = sorted(ledger.home_fraction)
    witness = {}
    for probe in (390, 391, 392, 408, 432, 768):
        cand = [e for e in conf_epochs if e >= probe]
        if cand:
            c, total = ledger.home_fraction[cand[0]]
            witness[f"epoch_{cand[0]}"] = {
                "passengers_at_home": c,
                "aboard_passengers": total,
                "fraction": round(c / total, 4),
            }

    readout = {
        "design": args.design,
        "arm": args.arm,
        "seed": args.seed,
        "epochs": int(sim.num_epochs),
        "person_hours": ledger.hours,
        "ashore_by_day": {
            str(d): {"ashore": v[0], "aboard": v[1]}
            for d, v in sorted(ledger.ashore_by_day.items())
        },
        "confinement_witness": witness,
        "exercise_telemetry": exercise,
    }
    text = json.dumps(readout, indent=1, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
