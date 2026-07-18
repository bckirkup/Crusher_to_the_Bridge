#!/usr/bin/env python3
"""
campaign_runner.py — Generate and execute mega-cruise campaign runs
from campaign_manifest.json.

Usage (from repo root):
    python3 picard_framework/runs/mega_cruise_campaign/campaign_runner.py --dry-run
    python3 picard_framework/runs/mega_cruise_campaign/campaign_runner.py --tier t1
    python3 picard_framework/runs/mega_cruise_campaign/campaign_runner.py --resume
    python3 picard_framework/runs/mega_cruise_campaign/campaign_runner.py --smoke

Windows:
    run_campaign.bat --tier t1
    run_campaign.bat --smoke
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import traceback
import zipfile
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = CAMPAIGN_DIR / "campaign_manifest.json"
OUTPUT_ROOT = REPO_ROOT / "telemetry_buffer" / "mega_cruise_campaign"
COMPLETED_LOG = OUTPUT_ROOT / "completed_runs.txt"


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def completed_runs() -> set[str]:
    if COMPLETED_LOG.exists():
        return {line.strip() for line in COMPLETED_LOG.read_text(encoding="utf-8").splitlines() if line.strip()}
    return set()


def mark_completed(run_id: str) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    with open(COMPLETED_LOG, "a", encoding="utf-8") as fh:
        fh.write(run_id + "\n")


def resolve_tier_ids(manifest: dict[str, Any], tier_arg: str | None) -> list[str]:
    """Accept full keys (t1_pathogen_baselines) or short prefixes (t1)."""
    keys = sorted(manifest["tiers"].keys())
    if not tier_arg or tier_arg in ("all", "*"):
        return keys
    if tier_arg in manifest["tiers"]:
        return [tier_arg]
    matches = [k for k in keys if k == tier_arg or k.startswith(f"{tier_arg}_")]
    if not matches:
        raise SystemExit(
            f"Unknown tier {tier_arg!r}. Choose from: "
            + ", ".join(k.split("_", 1)[0] for k in keys),
        )
    return matches


def get_pathogen_config(
    manifest: dict[str, Any], pathogen: str,
) -> tuple[str, str, dict[str, Any] | None]:
    cfg = manifest["pathogen_configs"][pathogen]
    bundle = cfg.get("bundle", "active_profiles")
    pathogen_id = cfg["pathogen_id"]
    overrides = cfg.get("overrides")
    if isinstance(overrides, list):
        overrides = {"remove": overrides}
    return bundle, pathogen_id, overrides


def combo_overrides(manifest: dict[str, Any], combo: str) -> tuple[str, dict[str, Any]]:
    cfg = manifest["combo_configs"][combo]
    bundle = cfg["bundle"]
    keep = set(cfg["keep"])
    remove = [pid for pid in manifest["edison_all_pathogen_ids"] if pid not in keep]
    return bundle, {"remove": remove}


def merge_cfg(*parts: dict[str, Any] | None) -> dict[str, Any] | None:
    merged: dict[str, Any] = {}
    for part in parts:
        if not part:
            continue
        for key, value in part.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
    return merged or None


def make_picard_spec(
    run_id: str,
    *,
    platform: str,
    bundle: str,
    pathogen_overrides: dict[str, Any] | None,
    config_overrides: dict[str, Any] | None,
    seed: int,
    epochs: int,
    num_agents: int,
    telemetry_dir: Path | None = None,
    write_ground_truth: bool = False,
) -> dict[str, Any]:
    cfg = merge_cfg(
        {"ship_graph": {"num_agents": num_agents}},
        config_overrides,
    )
    spec: dict[str, Any] = {
        "schema_version": "1.0.0",
        "description": run_id,
        "catalog": {"platform_id": platform, "pathogen_bundle_id": bundle},
        "run": {
            "random_seed": seed,
            "num_epochs": epochs,
            "write_ground_truth": write_ground_truth,
        },
        "legacy_yaml": "crusher_labs/config.yaml",
        "actors": [],
        "incentives": {},
    }
    if pathogen_overrides:
        spec["pathogen_overrides"] = pathogen_overrides
    if cfg:
        spec["config_overrides"] = cfg
    if telemetry_dir is not None:
        # Absolute paths so finalize does not clobber shared telemetry_buffer/.
        spec["run"]["simulation_history"] = str(telemetry_dir / "simulation_history.json")
        spec["run"]["lab_notebook"] = str(telemetry_dir / "artificial_lab_notebook.json")
        spec["run"]["ground_truth"] = str(telemetry_dir / "ground_truth.json")
    return spec


def generate_tier_runs(
    manifest: dict[str, Any],
    tier_id: str,
    *,
    platform: str | None = None,
    epochs_override: int | None = None,
    num_agents_override: int | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield (run_id, picard_spec_dict) for a tier."""
    tier = manifest["tiers"][tier_id]
    platform = platform or manifest["platform"]
    default_epochs = epochs_override or tier.get("epochs", manifest["default_epochs"])
    default_agents = num_agents_override or manifest.get("default_num_agents", 7000)
    surv_cfgs = manifest["surveillance_configs"]
    short = tier_id.split("_", 1)[0]

    if short == "t1":
        hvac = {"hvac": tier["hvac"]} if tier.get("hvac") else None
        surv = surv_cfgs.get(tier.get("surveillance", "none"))
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for seed in tier["seeds"]:
                rid = f"{short}_{pathogen}_s{seed}"
                yield rid, make_picard_spec(
                    rid, platform=platform, bundle=bundle,
                    pathogen_overrides=overrides,
                    config_overrides=merge_cfg(hvac, surv),
                    seed=seed, epochs=default_epochs, num_agents=default_agents,
                )

    elif short == "t2":
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for fname, fval in tier["filter_efficiencies"].items():
                for dname, dval in tier["decay_rates"].items():
                    hvac = {"hvac": {
                        "filter_efficiency": fval,
                        "natural_decay_rate": dval,
                    }}
                    for seed in tier["seeds"]:
                        rid = f"{short}_{pathogen}_{fname}_{dname}_s{seed}"
                        yield rid, make_picard_spec(
                            rid, platform=platform, bundle=bundle,
                            pathogen_overrides=overrides,
                            config_overrides=hvac,
                            seed=seed, epochs=default_epochs, num_agents=default_agents,
                        )

    elif short == "t3":
        hvac = {"hvac": tier["hvac"]} if tier.get("hvac") else None
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for sname in tier["surveillance_strategies"]:
                for seed in tier["seeds"]:
                    rid = f"{short}_{pathogen}_{sname}_s{seed}"
                    yield rid, make_picard_spec(
                        rid, platform=platform, bundle=bundle,
                        pathogen_overrides=overrides,
                        config_overrides=merge_cfg(hvac, surv_cfgs.get(sname)),
                        seed=seed, epochs=default_epochs, num_agents=default_agents,
                    )

    elif short == "t4":
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for fname, fval in tier["filter_efficiencies"].items():
                for dname, dval in tier["decay_rates"].items():
                    for sname in tier["surveillance_strategies"]:
                        hvac = {"hvac": {
                            "filter_efficiency": fval,
                            "natural_decay_rate": dval,
                        }}
                        for seed in tier["seeds"]:
                            rid = f"{short}_{pathogen}_{fname}_{dname}_{sname}_s{seed}"
                            yield rid, make_picard_spec(
                                rid, platform=platform, bundle=bundle,
                                pathogen_overrides=overrides,
                                config_overrides=merge_cfg(hvac, surv_cfgs.get(sname)),
                                seed=seed, epochs=default_epochs, num_agents=default_agents,
                            )

    elif short == "t5":
        for combo in tier["combos"]:
            bundle, overrides = combo_overrides(manifest, combo)
            safe = combo.replace("+", "_")
            for sname in tier["surveillance_strategies"]:
                for seed in tier["seeds"]:
                    rid = f"{short}_{safe}_{sname}_s{seed}"
                    yield rid, make_picard_spec(
                        rid, platform=platform, bundle=bundle,
                        pathogen_overrides=overrides,
                        config_overrides=surv_cfgs.get(sname),
                        seed=seed, epochs=default_epochs, num_agents=default_agents,
                    )

    elif short == "t6":
        for pathogen in tier["pathogens"]:
            bundle, pathogen_id, overrides = get_pathogen_config(manifest, pathogen)
            for n_init in tier["initial_infected"]:
                path_over = dict(overrides or {})
                path_over[pathogen_id] = {
                    **(path_over.get(pathogen_id) or {}),
                    "initial_infected": int(n_init),
                }
                for seed in tier["seeds"]:
                    rid = f"{short}_{pathogen}_init{n_init}_s{seed}"
                    yield rid, make_picard_spec(
                        rid, platform=platform, bundle=bundle,
                        pathogen_overrides=path_over,
                        config_overrides=None,
                        seed=seed, epochs=default_epochs, num_agents=default_agents,
                    )

    elif short == "t7":
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for sname in tier["surveillance_strategies"]:
                for comp in tier["compliance_levels"]:
                    behavior = {
                        "fred_behavior": {"quarantine_compliance": float(comp)},
                    }
                    for seed in tier["seeds"]:
                        rid = f"{short}_{pathogen}_{sname}_comp{int(comp * 100)}_s{seed}"
                        yield rid, make_picard_spec(
                            rid, platform=platform, bundle=bundle,
                            pathogen_overrides=overrides,
                            config_overrides=merge_cfg(surv_cfgs.get(sname), behavior),
                            seed=seed, epochs=default_epochs, num_agents=default_agents,
                        )

    elif short == "t8":
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for wname in tier["wearable_configs"]:
                wear = {"wearable_monitoring": {"deployment_profile": wname}}
                for sname in tier["surveillance_strategies"]:
                    for seed in tier["seeds"]:
                        rid = f"{short}_{pathogen}_{wname}_{sname}_s{seed}"
                        yield rid, make_picard_spec(
                            rid, platform=platform, bundle=bundle,
                            pathogen_overrides=overrides,
                            config_overrides=merge_cfg(surv_cfgs.get(sname), wear),
                            seed=seed, epochs=default_epochs, num_agents=default_agents,
                        )

    elif short == "t9":
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for sname in tier["surveillance_strategies"]:
                for seed in tier["seeds"]:
                    rid = f"{short}_{pathogen}_{sname}_s{seed}"
                    yield rid, make_picard_spec(
                        rid, platform=platform, bundle=bundle,
                        pathogen_overrides=overrides,
                        config_overrides=surv_cfgs.get(sname),
                        seed=seed, epochs=default_epochs, num_agents=default_agents,
                    )

    elif short == "t10":
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for n_agents in tier["population_sizes"]:
                for seed in tier["seeds"]:
                    rid = f"{short}_{pathogen}_n{n_agents}_s{seed}"
                    yield rid, make_picard_spec(
                        rid, platform=platform, bundle=bundle,
                        pathogen_overrides=overrides,
                        config_overrides=None,
                        seed=seed, epochs=default_epochs, num_agents=int(n_agents),
                    )

    else:
        raise ValueError(f"No generator for tier {tier_id}")


def run_simulation(
    run_id: str,
    spec: dict[str, Any],
    *,
    full_telemetry: bool = False,
    keep_workdir: bool = False,
) -> bool:
    """Run one simulation, write summary zip, return success."""
    run_dir = OUTPUT_ROOT / run_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    if full_telemetry:
        spec = dict(spec)
        spec["run"] = dict(spec["run"])
        spec["run"]["write_ground_truth"] = True
        spec["run"]["simulation_history"] = str(run_dir / "simulation_history.json")
        spec["run"]["lab_notebook"] = str(run_dir / "artificial_lab_notebook.json")
        spec["run"]["ground_truth"] = str(run_dir / "ground_truth.json")

    spec_path = run_dir / "run_spec.json"
    with open(spec_path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)

    try:
        from picard_framework.run_spec import PicardRunSpec
        from picard_framework.simulation.ship_simulation import ShipSimulation

        picard_spec = PicardRunSpec.from_picard_json(str(REPO_ROOT), str(spec_path))
        sim = ShipSimulation(picard_spec, display=False)
        result = sim.run()
        if full_telemetry:
            sim.finalize(display=False)

        last = result.history[-1] if result.history else {}
        summary = {
            "run_id": run_id,
            "num_epochs": result.num_epochs,
            "trigger_status": result.final_trigger_status,
            "summary": last.get("summary", {}),
            "cost_accounting": last.get("cost_accounting", {}),
        }
        with open(run_dir / "summary.json", "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)

        zip_path = OUTPUT_ROOT / f"{run_id}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fpath in run_dir.rglob("*"):
                if fpath.is_file():
                    zf.write(fpath, fpath.relative_to(run_dir))
        if not keep_workdir:
            shutil.rmtree(run_dir)
        return True

    except Exception as exc:
        with open(run_dir / "error.txt", "w", encoding="utf-8") as fh:
            fh.write(f"{type(exc).__name__}: {exc}\n")
            fh.write(traceback.format_exc())
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mega cruise campaign runner")
    parser.add_argument("--tier", default=None, help="Tier id or short prefix (t1…t10)")
    parser.add_argument("--dry-run", action="store_true", help="Count runs without executing")
    parser.add_argument("--resume", action="store_true", help="Skip completed run_ids")
    parser.add_argument("--limit", type=int, default=None, help="Max runs to execute")
    parser.add_argument("--epochs", type=int, default=None, help="Override epochs for all runs")
    parser.add_argument("--platform", default=None, help="Override platform_id")
    parser.add_argument("--num-agents", type=int, default=None, help="Override ship_graph.num_agents")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Fast local smoke: destroyer_baseline, 2 epochs, 20 agents, t1, limit 1",
    )
    parser.add_argument(
        "--full-telemetry",
        action="store_true",
        help="Write full history/lab notebook into each run zip (much slower/larger)",
    )
    parser.add_argument(
        "--keep-workdir",
        action="store_true",
        help="Keep unzipped run directories under telemetry_buffer/mega_cruise_campaign/",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST_PATH,
        help="Path to campaign_manifest.json",
    )
    args = parser.parse_args(argv)

    if args.smoke:
        args.tier = args.tier or "t1"
        args.platform = args.platform or "destroyer_baseline"
        args.epochs = args.epochs if args.epochs is not None else 2
        args.num_agents = args.num_agents if args.num_agents is not None else 20
        args.limit = args.limit if args.limit is not None else 1

    manifest = load_manifest(args.manifest)
    done = completed_runs() if args.resume else set()
    tiers = resolve_tier_ids(manifest, args.tier)

    total = 0
    succeeded = 0
    failed = 0
    skipped = 0
    executed = 0
    t0 = time.time()

    for tier_id in tiers:
        runs = list(generate_tier_runs(
            manifest,
            tier_id,
            platform=args.platform,
            epochs_override=args.epochs,
            num_agents_override=args.num_agents,
        ))
        print(f"\n{'=' * 60}")
        print(f"  {tier_id}: {len(runs)} runs")
        print(f"{'=' * 60}")

        if args.dry_run:
            total += len(runs)
            continue

        for i, (run_id, spec) in enumerate(runs):
            if args.limit is not None and executed >= args.limit:
                break
            total += 1
            if run_id in done:
                skipped += 1
                continue

            elapsed = time.time() - t0
            rate = max(executed, 1) / max(elapsed, 1e-6)
            remaining_n = max(len(runs) - i - 1, 0)
            eta_min = remaining_n / max(rate, 1e-6) / 60.0
            print(
                f"  [{i + 1}/{len(runs)}] {run_id}  "
                f"({succeeded}ok {failed}err {skipped}skip  "
                f"~{eta_min:.0f}min left)",
                end="",
                flush=True,
            )

            ok = run_simulation(
                run_id,
                spec,
                full_telemetry=args.full_telemetry,
                keep_workdir=args.keep_workdir,
            )
            executed += 1
            if ok:
                succeeded += 1
                mark_completed(run_id)
                print(" OK")
            else:
                failed += 1
                print(" FAIL")

        if args.limit is not None and executed >= args.limit:
            break

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  Campaign: {total} listed, {succeeded} ok, {failed} err, {skipped} skip")
    print(f"  Time: {elapsed / 3600:.2f}h ({elapsed / max(executed, 1):.1f}s/run)")
    if args.dry_run:
        print(f"  DRY RUN — {total} runs would be generated")
    print(f"  Output: {OUTPUT_ROOT}")
    print(f"{'=' * 60}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
