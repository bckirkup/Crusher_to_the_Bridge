#!/usr/bin/env python3
"""FOOD-SUPPLY-01 seed-initiation scanner.

Runs one chunk of manifest-tier voyages at ``epochs=1`` / small agent count
and emits one JSONL row per seed carrying only the supply-chain witnesses:
provisioned-source census, receipt states, contaminated receipts, and
provisioned-lot objects with lot size/titre/venue fields.

This is a boarding/prevalence census, not an outbreak readout: it selects
seeds for later paired full-fidelity runs and never scores an anchor.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# Seed selection must be reusable across local canaries and Batch children;
# re-exec under a fixed hash seed before importing the engine.
if os.environ.get("PYTHONHASHSEED") != "1":
    _env = dict(os.environ)
    _env["PYTHONHASHSEED"] = "1"
    os.execve(sys.executable, [sys.executable, *sys.argv], _env)

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_CAMPAIGN_DIR = REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
if str(_CAMPAIGN_DIR) not in sys.path:
    sys.path.insert(0, str(_CAMPAIGN_DIR))

from campaign_runner import generate_tier_runs  # noqa: E402

from tools.noro_diag.growth_chain_census import run_seed  # noqa: E402

_ARMS = ("station_lots", "single_line_receipt", "declared_receipts")
_TELEMETRY_KEYS = (
    "events_provisioned_lot",
    "events_ill_handler",
    "events_ill_diner",
    "takers_served",
    "dose_credited",
    "objects_provisioned_lot",
    "objects_ill_handler",
    "objects_ill_diner",
    "pans_emitted",
    "object_windows",
    "multi_pan_windows",
    "objects_exhausted",
    "objects_perished",
)
_RECEIPT_KEYS = (
    "receipt_id",
    "pathogen_id",
    "source_id",
    "supply_stratum",
    "item_line",
    "scale_class",
    "preparation_class",
    "quantity_servings",
    "quantity_g",
    "venues_served",
    "contamination",
    "lot_id",
    "q_line",
    "prevalence_scale",
    "receipt_index",
)
_OBJECT_KEYS = (
    "object_id",
    "pathogen_id",
    "source_kind",
    "item_label",
    "zone",
    "venues_served",
    "lot_id",
    "receipt_id",
    "lot_servings",
    "quantity_servings",
    "quantity_g",
    "lot_titre_gec_per_g",
    "preparation_class",
    "preparation_survival_mode",
    "scale_class",
    "supply_stratum",
    "provisioned_source_id",
    "source_agent_id",
    "strain_id",
    "seeded_epoch",
    "end_reason",
    "servings_served",
    "dose_credited",
    "windows_covered",
    "pans_emitted",
    "exhausted_epoch",
)


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _natural_clock(manifest: dict[str, Any]) -> str | None:
    clock = manifest.get("natural_history_clock")
    return str(clock) if clock is not None else None


def _template_spec(
    manifest: dict[str, Any],
    tier: str,
    *,
    epochs: int,
    num_agents: int,
) -> dict[str, Any]:
    for _run_id, spec in generate_tier_runs(
        manifest,
        tier,
        epochs_override=epochs,
        num_agents_override=num_agents,
        natural_history_clock=_natural_clock(manifest),
    ):
        return spec
    raise SystemExit(f"tier {tier!r} produced no runs")


def _arm_fields(arm: str) -> dict[str, Any]:
    if arm == "station_lots":
        return {}
    if arm == "single_line_receipt":
        return {"lot_layer_mode": "single_line_receipt"}
    if arm == "declared_receipts":
        return {
            "lot_layer_mode": "declared_receipts",
            "receipts_per_item_line": 2,
        }
    raise ValueError(f"unknown arm {arm!r}")


def _apply_arm(spec: dict[str, Any], arm: str) -> None:
    fields = _arm_fields(arm)
    cfg = (
        spec.get("config_overrides", {})
        .get("transmission", {})
        .get("common_source", {})
        .get("provisioned_source")
    )
    params = (
        (spec.get("campaign_parameters") or {})
        .get("common_source", {})
        .get("provisioned_source")
    )
    for target in (cfg, params):
        if isinstance(target, dict):
            target.update(fields)


def _spec_for_seed(
    template: dict[str, Any],
    *,
    seed: int,
    run_id: str,
    epochs: int,
    num_agents: int,
) -> dict[str, Any]:
    spec = copy.deepcopy(template)
    spec["description"] = run_id
    run = spec.setdefault("run", {})
    run["random_seed"] = int(seed)
    run["num_epochs"] = int(epochs)
    params = spec.setdefault("campaign_parameters", {})
    params.update(
        {
            "run_id": run_id,
            "seed": int(seed),
            "num_epochs": int(epochs),
            "num_agents": int(num_agents),
        }
    )
    return spec


def _pick(row: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: row[key] for key in keys if key in row}


def _receipt_counts(receipts: list[dict[str, Any]]) -> dict[str, int]:
    return {
        str(state): count
        for state, count in sorted(
            Counter(str(r.get("contamination")) for r in receipts).items()
        )
    }


def _receipts_by_item_line(receipts: list[dict[str, Any]]) -> dict[str, int]:
    return {
        str(item): count
        for item, count in sorted(
            Counter(str(r.get("item_line")) for r in receipts).items()
        )
    }


def _scan_row(
    *,
    payload: dict[str, Any],
    seed: int,
    tier: str,
    arm: str,
    hull: str,
    epochs: int,
    num_agents: int,
) -> dict[str, Any]:
    meta = payload.get("meta") or {}
    cs = payload.get("common_source") or {}
    receipts = list(cs.get("receipts") or [])
    objects = list(cs.get("objects") or [])
    telemetry = cs.get("telemetry") or {}
    contaminated_receipts = [
        _pick(receipt, _RECEIPT_KEYS)
        for receipt in receipts
        if str(receipt.get("contamination")) not in ("", "none", "None")
    ]
    return {
        "seed": int(seed),
        "tier": tier,
        "arm": arm,
        "hull": hull,
        "platform": meta.get("platform"),
        "epochs": int(epochs),
        "num_agents": int(num_agents),
        "sim_wall_clock_s": meta.get("wall_clock_s"),
        "provisioned_source": cs.get("provisioned_source") or {},
        "n_receipts": len(receipts),
        "receipt_counts": _receipt_counts(receipts),
        "receipts_by_item_line": _receipts_by_item_line(receipts),
        "contaminated_receipts": contaminated_receipts,
        "n_contaminated_receipts": len(contaminated_receipts),
        "objects": [_pick(obj, _OBJECT_KEYS) for obj in objects],
        "objects_by_source_kind": {
            str(kind): count
            for kind, count in sorted(
                Counter(str(o.get("source_kind")) for o in objects).items()
            )
        },
        "telemetry": _pick(telemetry, _TELEMETRY_KEYS),
    }


def _error_row(
    *,
    seed: int,
    tier: str,
    arm: str,
    hull: str,
    epochs: int,
    num_agents: int,
    exc: Exception,
) -> dict[str, Any]:
    return {
        "seed": int(seed),
        "tier": tier,
        "arm": arm,
        "hull": hull,
        "epochs": int(epochs),
        "num_agents": int(num_agents),
        "error": f"{type(exc).__name__}: {exc}",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--tier", required=True)
    parser.add_argument("--arm", choices=_ARMS, required=True)
    parser.add_argument("--hull", default=None)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seed-count", type=int, required=True)
    parser.add_argument("--chunk-index", type=int, required=True)
    parser.add_argument("--chunk-size", type=int, default=100)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--num-agents", type=int, default=100)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--artifact", required=True)
    return parser.parse_args(argv)


def _chunk_seeds(args: argparse.Namespace) -> range:
    n_chunks = -(-args.seed_count // args.chunk_size)
    if not 0 <= args.chunk_index < n_chunks:
        raise SystemExit(
            f"chunk_index {args.chunk_index} outside 0..{n_chunks - 1}",
        )
    first = args.seed_start + args.chunk_index * args.chunk_size
    last = min(first + args.chunk_size, args.seed_start + args.seed_count)
    return range(first, last)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = _load_manifest(args.manifest)
    clock = _natural_clock(manifest)
    template = _template_spec(
        manifest, args.tier, epochs=args.epochs, num_agents=args.num_agents,
    )
    _apply_arm(template, args.arm)
    hull = args.hull or (
        args.tier.split("_")[1] if args.tier.startswith("fl_") else args.tier
    )
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / args.artifact
    seeds = _chunk_seeds(args)
    errors = 0
    with artifact.open("w", encoding="utf-8") as handle:
        for seed in seeds:
            run_id = f"{args.tier}_{args.arm}_s{seed}"
            spec = _spec_for_seed(
                template,
                seed=seed,
                run_id=run_id,
                epochs=args.epochs,
                num_agents=args.num_agents,
            )
            try:
                payload, _voyage, _initiation = run_seed(
                    pathogen_id=args.pathogen_id,
                    spec_dict=spec,
                    natural_history_clock=clock,
                    payload_profile="lean",
                )
                row = _scan_row(
                    payload=payload,
                    seed=seed,
                    tier=args.tier,
                    arm=args.arm,
                    hull=hull,
                    epochs=args.epochs,
                    num_agents=args.num_agents,
                )
            except Exception as exc:  # noqa: BLE001 - per-seed census row
                errors += 1
                row = _error_row(
                    seed=seed,
                    tier=args.tier,
                    arm=args.arm,
                    hull=hull,
                    epochs=args.epochs,
                    num_agents=args.num_agents,
                    exc=exc,
                )
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    print(
        json.dumps(
            {
                "artifact": str(artifact),
                "chunk_index": args.chunk_index,
                "seeds": len(seeds),
                "errors": errors,
            },
            indent=2,
        )
    )
    # A nonzero exit keeps campaign_entrypoint from uploading the chunk, so
    # Batch retries instead of _already_uploaded treating error rows as done.
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
