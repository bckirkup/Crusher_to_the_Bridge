#!/usr/bin/env python3
"""FLU-RHYTHM-01 — paired rhythm-layer A/B on the influenza arm.

Runs the FLU-DELIVERY-01 confined-window conditioning (isolated
``influenza_a`` arm, an explicit passenger seed pair at epoch 0, declared
SOP-017 confinement held day 1 → end, ``k`` shipped at 0.0006/copy)
under the shared rhythm A/B wrappers: ``rhythm.enabled`` off is the
labelled baseline; on partitions non-confined co-presence by the daily
program. Confined passengers early-return out of the layer, so the
contrast runs through crew watch/cleaning structure, meals-to-cabin,
rhythm-owned port-day ashore handling and the post-prandial sentinel —
not through the confined pair's own schedule.

Each cell emits the noro-probe zip contract under
``<out>/<arm>/<tier>/<run_id>.zip``: ``summary.json`` in campaign layout
plus ``rhythm.json.gz`` carrying per-epoch state digests, dealt-day
commitment witnesses, the cabin-pair challenge table, the stage-resolved
delivery decomposition, per-epoch dosed-set sizes, challenged share and
the acquisition pedigree. ``tools/flu_rhythm_ab_readout.py`` folds the
cells per class per arm.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import re
import sys
import tempfile
import time
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines import transmission_core as tc  # noqa: E402
from picard_framework.pathogen_overrides import (  # noqa: E402
    isolate_arm_overrides,
    load_pathogen_bundle,
)
from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils import asset_defaults  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    resolve_child_path,
    resolve_repo_path,
    validated_open,
)
from simulation_utils.platform_complement import declared_total  # noqa: E402
from tools.cabin_floor_probe import DECLARED_CONFINEMENT, _party_size  # noqa: E402
from tools.covid_route_attribution import (  # noqa: E402
    CabinPairChallengeLedger,
    cabin_pair_challenge_table,
)
from tools.flu_confined_dose_probe import _confined_row_doses  # noqa: E402
from tools.flu_delivery_stages_probe import (  # noqa: E402
    StageRecorder,
    _cell_report,
)
from tools.noro_diag.per_host_dose_challenge import (  # noqa: E402
    _attach_voyage_blocks,
    build_spec,
)
from tools.noro_diag.rhythm_ab_probe import (  # noqa: E402
    RhythmRecorder,
    _epoch_observer,
    _inject_arm,
    instrumented,
)

PATHOGEN = "influenza_a"
ACTIVE_BUNDLE = asset_defaults.DEFAULT_PATHOGEN_BUNDLE_ID
DEFAULT_EPOCHS = 288
_DEPARTED_LOCATION = "Departed"


@dataclass
class FluMechanism:
    """Per-epoch dosed-set and challenged-host witness (covid conventions)."""

    pathogen_id: str = PATHOGEN
    dosed_by_epoch: dict[int, set[int]] = field(
        default_factory=lambda: defaultdict(set),
    )
    challenged_ids: set[int] = field(default_factory=set)


def _wrap_dosed_set(core_cls: type, mech: FluMechanism) -> Any:
    """Count hosts resolved with a positive influenza dose per epoch."""
    original = core_cls._resolve_pathogen_challenge

    def wrapper(
        self: Any, epoch: int, agent: Any, pathogen_id: str,
        agent_pathogen_doses: dict, agent_pathway_doses: Any,
        matrix: Any, events: list,
    ) -> None:
        if pathogen_id == mech.pathogen_id:
            aid = int(agent.agent_id)
            dose = float(
                agent_pathogen_doses.get(aid, {}).get(pathogen_id, 0.0),
            )
            if dose > 0.0:
                mech.dosed_by_epoch[int(epoch)].add(aid)
                mech.challenged_ids.add(aid)
        return original(
            self, epoch, agent, pathogen_id, agent_pathogen_doses,
            agent_pathway_doses, matrix, events,
        )

    return wrapper


def _fanout_observer(*observers: Any) -> Any:
    def observe(sim: Any, work: Any) -> None:
        for observer in observers:
            observer(sim, work)

    return observe


def flu_cell_spec(
    *,
    seed: int,
    platform: str,
    epochs: int,
    confinement: str = "declared",
) -> dict[str, Any]:
    """The FLU-DELIVERY-01 conditioning verbatim (no arm injected)."""
    profiles = load_pathogen_bundle(
        resolve_repo_path(
            str(REPO_ROOT),
            asset_defaults.pathogen_bundle_rel(ACTIVE_BUNDLE),
        ),
    )
    spec_dict = build_spec(
        seed=seed, platform=platform, bundle=ACTIVE_BUNDLE,
        epochs=epochs, num_agents=declared_total(platform),
        pathogen_id=PATHOGEN, alpha=None, beta=0.0,
        high_touch_area_scale=None, high_touch_area_scale_by_zone_class=None,
        fomite_representation=None, fomite_touch_share=None,
        fomite_touch_share_table=None,
    )
    spec_dict["pathogen_overrides"] = isolate_arm_overrides(
        ACTIVE_BUNDLE, PATHOGEN, {PATHOGEN: {"initial_infected": None}},
    )
    spec_dict["config_overrides"]["initiation"] = {
        "explicit_seeds": [{
            "pathogen": PATHOGEN,
            "count": _party_size(profiles[PATHOGEN]),
            "role": "passenger",
            "epoch": 0,
        }],
    }
    if confinement == "declared":
        spec_dict["config_overrides"]["scenario_schedule"] = {
            "protocols": [DECLARED_CONFINEMENT],
        }
    spec_dict["description"] = f"flu_rhythm_ab_{platform}_s{seed}"
    return spec_dict


def _mechanism_block(
    mech: FluMechanism, sim: Any, n_seeded: int,
) -> dict[str, Any]:
    infected_end = {
        int(a.agent_id)
        for a in sim.engine.agents
        if a.is_infected_with(PATHOGEN)
    }
    aboard_end = sum(
        1
        for a in sim.engine.agents
        if str(a.current_location) != _DEPARTED_LOCATION
        and not getattr(a, "departed", False)
    )
    denominator = max(aboard_end - n_seeded, 1)
    return {
        "dosed_set_sizes": {
            str(epoch): len(ids)
            for epoch, ids in sorted(mech.dosed_by_epoch.items())
        },
        "n_challenged": len(mech.challenged_ids),
        "n_infected_end": len(infected_end),
        "n_aboard_end": int(aboard_end),
        "n_seeded": int(n_seeded),
        "challenged_share": (
            len(mech.challenged_ids | infected_end) / denominator
        ),
    }


def _rhythm_payload(
    rec: RhythmRecorder,
    spec_dict: dict[str, Any],
    arm: str | None,
    engine: Any,
) -> dict[str, Any]:
    """Shared noro-probe witness fields minus the noro-only tables."""
    rhythm_cfg = (spec_dict.get("config_overrides") or {}).get("rhythm") or {}
    attached = getattr(engine, "_rhythm", None) is not None
    requested = rhythm_cfg.get("enabled")
    if arm == "on" and not attached:
        raise RuntimeError(
            "rhythm.enabled=true did not attach a layer "
            "(platform uncatalogued or non-hourly clock?)",
        )
    if arm == "off" and attached:
        raise RuntimeError("rhythm.enabled=false still attached a layer")
    voyage_digest = hashlib.sha256(
        "".join(rec.epoch_state_digests).encode(),
    ).hexdigest()
    return {
        "arm": arm,
        "rhythm_requested": requested,
        "rhythm_attached": attached,
        "commitments_total": rec.commitments_total,
        "dealt_days": rec.dealt_days,
        "ashore_dosed_epochs": rec.ashore_dosed_epochs,
        "ashore_dosed_rows": rec.ashore_dosed_rows,
        "n_acquired": len(rec.acquired_ids),
        "n_imports": len(rec.import_ids),
        "acquisition_rows": rec.acquisition_rows,
        "epoch_rows": rec.epoch_rows,
        "epoch_state_digests": rec.epoch_state_digests,
        "telemetry_sha256": voyage_digest,
    }


def run_cell(
    *,
    seed: int,
    platform: str,
    epochs: int,
    arm: str,
    confinement: str = "declared",
    spec_dict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One instrumented cell; returns the campaign-layout summary."""
    spec = copy.deepcopy(
        spec_dict if spec_dict is not None else flu_cell_spec(
            seed=seed, platform=platform, epochs=epochs,
            confinement=confinement,
        )
    )
    _inject_arm(spec, arm)
    num_agents = int(
        (spec.get("config_overrides") or {})
        .get("ship_graph", {})
        .get("num_agents", 0),
    )
    rec = RhythmRecorder(pathogen_id=PATHOGEN)
    mech = FluMechanism()
    stage = StageRecorder(PATHOGEN)
    ledger = CabinPairChallengeLedger()
    started_total = time.perf_counter()
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        spec_path = resolve_child_path(tmp, "run_spec.json")
        with validated_open(
            spec_path, "w", allowed_roots=(tmp,), encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(spec))
        picard_spec = PicardRunSpec.from_picard_json(
            str(REPO_ROOT), spec_path,
        )
        with instrumented(rec):
            stage.install()
            saved_challenge = tc.TransmissionCore._resolve_pathogen_challenge
            tc.TransmissionCore._resolve_pathogen_challenge = (
                _wrap_dosed_set(tc.TransmissionCore, mech)
            )
            try:
                sim = ShipSimulation(picard_spec, display=False)
                sim.epoch_observer = _fanout_observer(
                    ledger.observe, _epoch_observer(rec),
                )
                started_run = time.perf_counter()
                result = sim.run()
                wall_clock_run = time.perf_counter() - started_run
            finally:
                tc.TransmissionCore._resolve_pathogen_challenge = (
                    saved_challenge
                )
                stage.restore()
    summary: dict[str, Any] = {
        "run_id": str(spec.get("description", "")),
        "seed": int(spec["run"]["random_seed"]),
        "num_epochs": int(spec["run"]["num_epochs"]),
        "num_agents": num_agents,
        "platform": str(spec["catalog"]["platform_id"]),
        "wall_clock_seconds_run": wall_clock_run,
        "wall_clock_seconds_total": time.perf_counter() - started_total,
    }
    _attach_voyage_blocks(summary, spec, result, num_agents, "hours")
    payload = _rhythm_payload(rec, spec, arm, sim.engine)
    meta = {
        "seed": seed, "platform": platform, "epochs": epochs,
        "confinement": confinement, "arm": arm,
    }
    confined = _cell_report(ledger, stage, sim, meta)
    table = cabin_pair_challenge_table(ledger, sim)
    dose_all, dose_slots, n_slot_targets = _confined_row_doses(
        table["rows"], sim, ledger.confined_first,
    )
    confined["slot_dose_rows"] = dose_slots
    confined["n_dosed_confined_rows"] = len(dose_all)
    confined["n_slot_targets"] = n_slot_targets
    payload["confined"] = confined
    seeds_block = (
        (spec.get("config_overrides") or {}).get("initiation") or {}
    ).get("explicit_seeds") or [{}]
    payload["mechanism"] = _mechanism_block(
        mech, sim, n_seeded=int(seeds_block[0].get("count") or 0),
    )
    summary["rhythm"] = payload
    return summary


# ── CLI / cell plumbing ───────────────────────────────────────────────


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise argparse.ArgumentTypeError(f"invalid identifier: {value!r}")
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", default="classic_cruise_1900")
    parser.add_argument("--seed", type=int, default=8105)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument(
        "--arm", choices=("off", "on"), default=None,
        help="rhythm.enabled arm; unset leaves the spec rhythm-free "
             "(emit-spec mode for the byte-identity gate)",
    )
    parser.add_argument(
        "--confinement", choices=("declared", "organic"), default="declared",
    )
    parser.add_argument(
        "--tier", type=_identifier, default=None,
        help="zip subdirectory label (defaults to the platform id)",
    )
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--out-name", type=_identifier, default=None,
        help="zip filename stem (defaults to s<seed>)",
    )
    parser.add_argument(
        "--emit-spec", type=Path, default=None,
        help="write the cell spec JSON (with --arm injected when given) "
             "and exit without running — byte-identity witness source",
    )
    args = parser.parse_args(argv)
    if args.emit_spec is None and (args.out is None or args.arm is None):
        parser.error("running a cell requires --out and --arm")
    return args


def _write_run_zip(
    out_dir: Path, tier: str, run_id: str, payload: dict[str, Any],
) -> Path:
    """``summary.json`` (campaign layout) + ``rhythm.json.gz`` payload."""
    cell_dir = Path(resolve_child_path(str(out_dir), tier))
    cell_dir.mkdir(parents=True, exist_ok=True)
    zip_path = Path(resolve_child_path(str(cell_dir), f"{run_id}.zip"))
    anchor = {
        "run_id": run_id,
        "parameters": payload["parameters"],
        "num_epochs": payload["num_epochs"],
        "trigger_status": payload.get("trigger_status"),
        "summary": payload["summary"],
        "cost_accounting": payload["cost_accounting"],
        "derived": payload["derived"],
    }
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("summary.json", json.dumps(anchor))
        archive.writestr(
            "rhythm.json.gz",
            gzip.compress(json.dumps(payload["rhythm"]).encode()),
        )
    return zip_path


def _emit_spec(args: argparse.Namespace) -> None:
    spec = flu_cell_spec(
        seed=args.seed, platform=args.platform, epochs=args.epochs,
        confinement=args.confinement,
    )
    _inject_arm(spec, args.arm)
    out = Path(
        resolve_repo_path(str(REPO_ROOT), str(args.emit_spec)),
    )
    with validated_open(
        out, "w", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        handle.write(json.dumps(spec, indent=1, sort_keys=True))
    print(f"wrote {out}")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.emit_spec is not None:
        _emit_spec(args)
        return
    out_dir = Path(
        resolve_repo_path(str(REPO_ROOT), str(args.out)),
    ) / args.arm
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = args.out_name or f"s{args.seed}"
    summary = run_cell(
        seed=args.seed, platform=args.platform, epochs=args.epochs,
        arm=args.arm, confinement=args.confinement,
    )
    zip_path = _write_run_zip(
        out_dir, args.tier or args.platform, run_id, summary,
    )
    print(json.dumps({
        "zip": str(zip_path),
        "telemetry_sha256": summary["rhythm"]["telemetry_sha256"],
        "confined_secondaries": (
            summary["rhythm"]["confined"]["confined_secondaries"]
        ),
        "confined_slots": (
            summary["rhythm"]["confined"]["confined_slots"]
        ),
        "commitments_total": summary["rhythm"]["commitments_total"],
        "rhythm_attached": summary["rhythm"]["rhythm_attached"],
    }))


if __name__ == "__main__":
    main()
