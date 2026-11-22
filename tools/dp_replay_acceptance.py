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
import os
import re
import sys
import tempfile
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
        # Quarantine hours are whatever the arm's own order realizes:
        # active_sop_names includes orders scheduled later the same day
        # (dealing-day union), so bucket by the confined population the
        # modifiers actually produced, not the name set.
        if getattr(engine, "quarantined_ids", None):
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


def resolve_arg_paths(args) -> tuple[Path, Path | None]:
    """Confine --design to the repo tree and --out to repo/temp, before
    any simulation work runs."""
    design_path = Path(args.design).expanduser().resolve()
    if _REPO_ROOT != design_path and _REPO_ROOT not in design_path.parents:
        raise SystemExit(
            f"--design must be under the repo tree: {design_path}"
        )
    out_path = None
    if args.out:
        # The readout file is caller-named; confine it to the repo tree or
        # the system temp dir, and reject it before the simulation runs.
        out_path = Path(args.out).expanduser().resolve()
        allowed = (_REPO_ROOT, Path(tempfile.gettempdir()).resolve())
        if not any(
            out_path == base or base in out_path.parents for base in allowed
        ):
            raise SystemExit(
                f"--out must be under the repo or the temp dir: {out_path}"
            )
    return design_path, out_path


def load_zone_meta(raw: dict) -> dict[str, str]:
    """Resolve the spec's platform to a {zone_id: type} map, confining
    the layout read to data/platforms."""
    platform_id = str(
        raw.get("platform_id")
        or (raw.get("config_overrides") or {}).get("platform_id")
        or "diamond_princess"
    )
    if not re.fullmatch(r"[a-z0-9_]+", platform_id):
        raise SystemExit(f"unexpected platform id: {platform_id!r}")
    layout_path = (
        _REPO_ROOT / "data/platforms" / platform_id / "spatial_layout.json"
    ).resolve()
    if _REPO_ROOT / "data/platforms" not in layout_path.parents:
        raise SystemExit(f"layout path escapes data/platforms: {layout_path}")
    layout = json.loads(layout_path.read_text())
    return {str(z["id"]): str(z.get("type")) for z in layout["zones"]}


def build_sim(raw: dict):
    import contextlib  # noqa: E402
    import io  # noqa: E402

    from picard_framework.run_spec import PicardRunSpec  # noqa: E402
    from picard_framework.simulation.ship_simulation import (  # noqa: E402
        ShipSimulation,
    )

    spec = PicardRunSpec.from_picard_dict(str(_REPO_ROOT), raw)
    with contextlib.redirect_stdout(io.StringIO()):
        sim = ShipSimulation(spec, display=False)
        sim.initialize()
    return sim


def run_epochs(sim) -> None:
    import contextlib  # noqa: E402
    import io  # noqa: E402

    with contextlib.redirect_stdout(io.StringIO()):
        for _ in range(sim.num_epochs):
            sim.step()


def write_json(out_path: Path | None, text: str) -> None:
    """Write the readout, refusing a symlink planted after the upfront
    path check (O_NOFOLLOW where it exists; 0o666 so the umask decides)."""
    if out_path is None:
        return
    fd = os.open(
        str(out_path),
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0),
        0o666,
    )
    with os.fdopen(fd, "w") as fh:
        fh.write(text)


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

    design_path, out_path = resolve_arg_paths(args)
    design = load_design(str(design_path))
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

    zone_meta = load_zone_meta(raw)

    sim = build_sim(raw)
    home_zones = {
        int(a.agent_id): str(getattr(a, "home_zone", "") or "")
        for a in sim.engine.agents
    }
    ledger = MovementLedger(zone_meta, home_zones)
    sim.epoch_observer = ledger.observe
    run_epochs(sim)

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
    write_json(out_path, text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
