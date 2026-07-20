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
import os
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = CAMPAIGN_DIR / "campaign_manifest.json"
OUTPUT_ROOT = REPO_ROOT / "telemetry_buffer" / "mega_cruise_campaign"
COMPLETED_LOG = OUTPUT_ROOT / "completed_runs.txt"
FAILED_LOG = OUTPUT_ROOT / "failed_runs.txt"


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _read_run_id_log(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def completed_runs() -> set[str]:
    return _read_run_id_log(COMPLETED_LOG)


def failed_runs() -> set[str]:
    return _read_run_id_log(FAILED_LOG)


def mark_completed(run_id: str) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    with open(COMPLETED_LOG, "a", encoding="utf-8") as fh:
        fh.write(run_id + "\n")
    # A later success clears a prior failure entry for the same run_id.
    _remove_from_log(FAILED_LOG, run_id)


def mark_failed(run_id: str) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    with open(FAILED_LOG, "a", encoding="utf-8") as fh:
        fh.write(run_id + "\n")


def _remove_from_log(path: Path, run_id: str) -> None:
    if not path.exists():
        return
    kept = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip() != run_id]
    if kept:
        path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    else:
        path.unlink(missing_ok=True)


def clear_failed_artifacts(run_id: str) -> None:
    """Remove leftover workdir / stderr from a prior failure before retry."""
    run_dir = OUTPUT_ROOT / run_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    stderr_path = OUTPUT_ROOT / f"{run_id}.subprocess_stderr.txt"
    stderr_path.unlink(missing_ok=True)
    spec_path = OUTPUT_ROOT / f"{run_id}.run_spec.json"
    spec_path.unlink(missing_ok=True)


def parse_s3_prefix(s3_prefix: str) -> tuple[str, str]:
    """Split ``s3://bucket/path`` into ``(bucket, key_prefix)``."""
    parsed = urlparse(s3_prefix)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise SystemExit(
            f"--s3-prefix must look like s3://bucket/path, got {s3_prefix!r}",
        )
    return parsed.netloc, parsed.path.lstrip("/")


class S3Uploader:
    """Thin boto3 wrapper. Imported lazily so non-S3 runs need no boto3."""

    def __init__(self, s3_prefix: str) -> None:
        self.bucket, self.key_prefix = parse_s3_prefix(s3_prefix)
        try:
            import boto3  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - depends on env
            raise SystemExit(
                "boto3 is required for --s3-prefix uploads "
                "(pip install boto3).",
            ) from exc
        self._client = boto3.client("s3")

    def _key(self, name: str) -> str:
        return f"{self.key_prefix.rstrip('/')}/{name}" if self.key_prefix else name

    def upload_file(self, local_path: Path, name: str) -> str:
        key = self._key(name)
        self._client.upload_file(str(local_path), self.bucket, key)
        return f"s3://{self.bucket}/{key}"

    def download_file(self, name: str, local_path: Path) -> bool:
        """Download ``name`` under the prefix to ``local_path``.

        Returns True on success, False if the object is missing. Other S3
        errors propagate so credential/network failures are visible.
        """
        key = self._key(name)
        try:
            from botocore.exceptions import ClientError  # noqa: PLC0415
        except ImportError:  # pragma: no cover
            ClientError = Exception  # type: ignore[misc, assignment]
        local_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._client.download_file(self.bucket, key, str(local_path))
            return True
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise
        except Exception as exc:  # noqa: BLE001
            # boto3 may raise different missing-key flavors depending on version.
            msg = str(exc).lower()
            if "nosuchkey" in msg or "not found" in msg or "404" in msg:
                return False
            raise

    def object_exists(self, name: str) -> bool:
        """Return True if ``name`` exists under the S3 prefix."""
        key = self._key(name)
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001
            return False


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


def _immunity_override(
    imm_frac: float | None,
) -> tuple[dict[str, Any] | None, str]:
    """Return (config_override, run_id_tag) for a pre-immunity fraction.

    ``None`` means "leave the engine default" (no override, no id tag), so
    tiers without a ``pre_immunity_fractions`` sweep keep their old run ids.
    """
    if imm_frac is None:
        return None, ""
    return (
        {"ship_graph": {"immune_fraction": float(imm_frac)}},
        f"_imm{int(round(imm_frac * 100))}",
    )


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
        oa_fractions = tier.get("oa_fractions") or {"oa20": 0.20}
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for fname, fval in tier["filter_efficiencies"].items():
                for oaname, oaval in oa_fractions.items():
                    for dname, dval in tier["decay_rates"].items():
                        hvac = {"hvac": {
                            "filter_efficiency": fval,
                            "natural_decay_rate": dval,
                            "oa_fraction": oaval,
                        }}
                        for seed in tier["seeds"]:
                            rid = f"{short}_{pathogen}_{fname}_{oaname}_{dname}_s{seed}"
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
        immunities = tier.get("pre_immunity_fractions", [None])
        for pathogen in tier["pathogens"]:
            bundle, pathogen_id, overrides = get_pathogen_config(manifest, pathogen)
            for n_init in tier["initial_infected"]:
                path_over = dict(overrides or {})
                path_over[pathogen_id] = {
                    **(path_over.get(pathogen_id) or {}),
                    "initial_infected": int(n_init),
                }
                for imm_frac in immunities:
                    cfg_over, imm_tag = _immunity_override(imm_frac)
                    for seed in tier["seeds"]:
                        rid = f"{short}_{pathogen}_init{n_init}{imm_tag}_s{seed}"
                        yield rid, make_picard_spec(
                            rid, platform=platform, bundle=bundle,
                            pathogen_overrides=path_over,
                            config_overrides=cfg_over,
                            seed=seed, epochs=default_epochs, num_agents=default_agents,
                        )

    elif short == "t7":
        immunities = tier.get("pre_immunity_fractions", [None])
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for sname in tier["surveillance_strategies"]:
                for comp in tier["compliance_levels"]:
                    behavior = {
                        "fred_behavior": {"quarantine_compliance": float(comp)},
                    }
                    for imm_frac in immunities:
                        imm_over, imm_tag = _immunity_override(imm_frac)
                        cfg_over = merge_cfg(
                            merge_cfg(surv_cfgs.get(sname), behavior), imm_over,
                        )
                        for seed in tier["seeds"]:
                            rid = (
                                f"{short}_{pathogen}_{sname}"
                                f"_comp{int(comp * 100)}{imm_tag}_s{seed}"
                            )
                            yield rid, make_picard_spec(
                                rid, platform=platform, bundle=bundle,
                                pathogen_overrides=overrides,
                                config_overrides=cfg_over,
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


def extract_timeseries(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract a compact per-epoch epidemic/contamination series from history.

    Keeps only the scalar fields needed for epidemic curves, detection lag,
    contamination spread and cost-effectiveness analysis — not the full
    per-agent / per-zone records — so it stays ~50 KB per run.

    ``new_infections`` is the per-epoch incidence estimator
    ``max(0, (I+R)_t − (I+R)_{t−1})``.
    """
    series: list[dict[str, Any]] = []
    prev_ever_infected = 0
    for epoch_idx, rec in enumerate(history):
        s = rec.get("summary", {})
        cost = rec.get("cost_accounting", {})
        spaces = rec.get("spaces", {})

        infected = int(s.get("infected", 0) or 0)
        recovered = int(s.get("recovered", 0) or 0)
        ever_infected = infected + recovered
        new_infections = max(0, ever_infected - prev_ever_infected)
        prev_ever_infected = ever_infected

        n_contaminated = 0
        max_conc = 0.0
        max_conc_zone = ""
        total_mass = 0.0
        for zname, zdata in spaces.items():
            conc = zdata.get("concentration_per_m3", 0.0)
            mass = zdata.get("pathogen_mass", 0.0)
            if isinstance(mass, dict):
                mass = sum(mass.values())
            total_mass += mass
            if conc > 1.0:
                n_contaminated += 1
            if conc > max_conc:
                max_conc = conc
                max_conc_zone = zname

        series.append({
            "epoch": epoch_idx,
            "susceptible": s.get("susceptible", 0),
            "infected": s.get("infected", 0),
            "symptomatic": s.get("symptomatic", 0),
            "recovered": s.get("recovered", 0),
            "immune": s.get("immune", 0),
            "quarantined": s.get("quarantined", 0),
            "isolated": s.get("isolated", 0),
            "new_infections": new_infections,
            "total_pathogen_mass": round(total_mass, 2),
            "n_zones_contaminated": n_contaminated,
            "max_concentration": round(max_conc, 4),
            "max_conc_zone": max_conc_zone,
            "cumulative_cost_usd": cost.get("total_financial_usd", 0),
            "cumulative_ois": cost.get("operational_impact_cumulative", 0),
            "trigger_status": rec.get(
                "trigger_status",
                rec.get("reactive_protocols", {}).get("trigger_status", "none"),
            ),
        })
    return series


def compute_derived_metrics(ts: list[dict[str, Any]], num_agents: int) -> dict[str, Any]:
    """Compute publication-ready scalar metrics from an epoch time series."""
    if not ts:
        return {}

    infected_by_epoch = [e["infected"] for e in ts]
    peak_infected = max(infected_by_epoch)
    peak_epoch = infected_by_epoch.index(peak_infected)

    final = ts[-1]
    recovered = int(final.get("recovered", 0) or 0)
    infected_final = int(final.get("infected", 0) or 0)
    # Cumulative attack: still-infectious + recovered (not recovered alone).
    ever_infected = infected_final + recovered
    attack_rate = ever_infected / num_agents if num_agents > 0 else 0

    # Outbreak threshold: more secondary cases than the initial index cases.
    outbreak_occurred = ever_infected > 2

    detection_epoch = None
    confirmation_epoch = None
    for e in ts:
        status = e.get("trigger_status", "none")
        if status in ("SUSPECTED", "CONFIRMED") and detection_epoch is None:
            detection_epoch = e["epoch"]
        if status == "CONFIRMED" and confirmation_epoch is None:
            confirmation_epoch = e["epoch"]

    total_quarantine_epochs = sum(e.get("quarantined", 0) for e in ts)

    # Crude R_effective at peak: new infections at peak / prevalence just before.
    r_eff_at_peak = None
    if peak_epoch > 0 and infected_by_epoch[peak_epoch - 1] > 0:
        new_at_peak = ts[peak_epoch].get("new_infections", 0)
        r_eff_at_peak = new_at_peak / infected_by_epoch[peak_epoch - 1]

    return {
        "attack_rate": round(attack_rate, 4),
        "peak_prevalence": peak_infected,
        "peak_epoch": peak_epoch,
        "outbreak_occurred": outbreak_occurred,
        "detection_epoch": detection_epoch,
        "confirmation_epoch": confirmation_epoch,
        "detection_lag": (
            peak_epoch - detection_epoch if detection_epoch is not None else None
        ),
        "total_quarantine_person_epochs": total_quarantine_epochs,
        "r_effective_at_peak": (
            round(r_eff_at_peak, 3) if r_eff_at_peak is not None else None
        ),
        "final_susceptible_fraction": round(
            final.get("susceptible", 0) / max(num_agents, 1), 4,
        ),
    }


def _spec_num_agents(spec: dict[str, Any]) -> int:
    """Best-effort resolve the ship population size from a run spec."""
    cfg = spec.get("config_overrides") or {}
    return int(cfg.get("ship_graph", {}).get("num_agents", 7000))


def run_simulation(
    run_id: str,
    spec: dict[str, Any],
    *,
    full_telemetry: bool = False,
    keep_workdir: bool = False,
    output_root: Path | None = None,
) -> bool:
    """Run one simulation, write summary zip, return success.

    ``output_root`` overrides where the run dir / zip are written (used by the
    subprocess child so it targets the parent's output directory); it defaults
    to the module-level ``OUTPUT_ROOT``.
    """
    root = output_root if output_root is not None else OUTPUT_ROOT
    run_dir = root / run_id
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
        ts = extract_timeseries(result.history)
        with open(run_dir / "timeseries.json", "w", encoding="utf-8") as fh:
            json.dump(ts, fh)

        summary = {
            "run_id": run_id,
            "num_epochs": result.num_epochs,
            "trigger_status": result.final_trigger_status,
            "summary": last.get("summary", {}),
            "cost_accounting": last.get("cost_accounting", {}),
            "derived": compute_derived_metrics(ts, _spec_num_agents(spec)),
        }
        with open(run_dir / "summary.json", "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)

        zip_path = root / f"{run_id}.zip"
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


def run_simulation_subprocess(
    run_id: str,
    spec: dict[str, Any],
    *,
    full_telemetry: bool = False,
    keep_workdir: bool = False,
    timeout: int = 600,
) -> bool:
    """Run one simulation in a fresh child process, then reclaim its memory.

    Repeated 7000-agent simulations leak RSS when run in a single process;
    isolating each run in a short-lived subprocess lets the OS reclaim all
    memory on exit, keeping the campaign under Fargate's memory limit.
    """
    spec_path = OUTPUT_ROOT / f"{run_id}.run_spec.json"
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    with open(spec_path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh)

    cmd = [
        sys.executable,
        str(CAMPAIGN_DIR / "campaign_runner.py"),
        "--single", str(spec_path), str(OUTPUT_ROOT),
    ]
    if full_telemetry:
        cmd.append("--full-telemetry")
    if keep_workdir:
        cmd.append("--keep-workdir")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        )
        ok = proc.returncode == 0 and (OUTPUT_ROOT / f"{run_id}.zip").is_file()
        if not ok:
            err_path = OUTPUT_ROOT / f"{run_id}.subprocess_stderr.txt"
            with open(err_path, "w", encoding="utf-8") as fh:
                fh.write(f"returncode={proc.returncode}\n\n")
                fh.write("--- stdout ---\n")
                fh.write(proc.stdout or "")
                fh.write("\n--- stderr ---\n")
                fh.write(proc.stderr or "")
    except subprocess.TimeoutExpired:
        err_path = OUTPUT_ROOT / f"{run_id}.subprocess_stderr.txt"
        with open(err_path, "w", encoding="utf-8") as fh:
            fh.write(f"TimeoutExpired after {timeout}s\n")
        ok = False
    finally:
        if not keep_workdir:
            spec_path.unlink(missing_ok=True)

    return ok


def _run_single(
    spec_path: str,
    outdir: str,
    *,
    full_telemetry: bool = False,
    keep_workdir: bool = False,
) -> int:
    """Child-process entry: run exactly one simulation into ``outdir``."""
    out = Path(outdir)
    with open(spec_path, encoding="utf-8") as fh:
        spec = json.load(fh)
    run_id = spec.get("description")
    if not run_id:
        raise SystemExit(f"--single spec {spec_path} missing 'description' run id")
    ok = run_simulation(
        run_id, spec,
        full_telemetry=full_telemetry, keep_workdir=keep_workdir,
        output_root=out,
    )
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mega cruise campaign runner")
    parser.add_argument("--tier", default=None, help="Tier id or short prefix (t1…t10)")
    parser.add_argument("--dry-run", action="store_true", help="Count runs without executing")
    parser.add_argument("--resume", action="store_true", help="Skip completed run_ids")
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Only re-run run_ids listed in failed_runs.txt (clears their leftovers first). "
        "Implies skipping completed runs.",
    )
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
    parser.add_argument(
        "--shard-count",
        type=int,
        default=None,
        help="Total number of shards (e.g. AWS Batch array size). "
        "A run executes only when global_index %% shard_count == shard_index.",
    )
    parser.add_argument(
        "--shard-index",
        type=int,
        default=None,
        help="This shard's index in [0, shard_count). Defaults to env "
        "AWS_BATCH_JOB_ARRAY_INDEX when present.",
    )
    parser.add_argument(
        "--s3-prefix",
        default=None,
        help="s3://bucket/path to upload each <run_id>.zip and completed_runs.txt.",
    )
    parser.add_argument(
        "--s3-log-every",
        type=int,
        default=25,
        help="Upload completed_runs.txt to S3 every N successful runs (default 25).",
    )
    parser.add_argument(
        "--single",
        nargs=2,
        metavar=("SPEC", "OUTDIR"),
        default=None,
        help="Child mode: run one simulation from SPEC (a run_spec.json) into OUTDIR.",
    )
    parser.add_argument(
        "--in-process",
        action="store_true",
        help="Run each simulation in-process instead of an isolated subprocess "
        "(faster for debugging; leaks memory across many large runs).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Per-run subprocess timeout in seconds (default 600).",
    )
    args = parser.parse_args(argv)

    if args.single:
        spec_path, outdir = args.single
        return _run_single(
            spec_path, outdir,
            full_telemetry=args.full_telemetry,
            keep_workdir=args.keep_workdir,
        )

    if args.smoke:
        args.tier = args.tier or "t1"
        args.platform = args.platform or "destroyer_baseline"
        args.epochs = args.epochs if args.epochs is not None else 2
        args.num_agents = args.num_agents if args.num_agents is not None else 20
        args.limit = args.limit if args.limit is not None else 1

    # Default shard index from the AWS Batch array job index when present.
    if args.shard_index is None:
        env_idx = os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX")
        if env_idx is not None:
            args.shard_index = int(env_idx)

    shard_count = args.shard_count
    shard_index = args.shard_index if args.shard_index is not None else 0
    if shard_count is not None:
        if shard_count < 1:
            raise SystemExit("--shard-count must be >= 1")
        if not 0 <= shard_index < shard_count:
            raise SystemExit(
                f"--shard-index {shard_index} out of range for "
                f"--shard-count {shard_count}",
            )

    uploader = S3Uploader(args.s3_prefix) if args.s3_prefix else None

    # Spot/Batch retries start with an empty local disk — pull this shard's
    # resume log from S3 before deciding what to skip.
    if uploader is not None and (args.resume or args.retry_failed):
        _download_completed_log(uploader, shard_index, shard_count)

    manifest = load_manifest(args.manifest)
    done = completed_runs() if (args.resume or args.retry_failed) else set()
    retry_only = failed_runs() if args.retry_failed else None
    if args.retry_failed and not retry_only:
        print("  --retry-failed: failed_runs.txt is empty; nothing to retry.")
        return 0
    tiers = resolve_tier_ids(manifest, args.tier)

    # Build the full flattened, ordered run list across selected tiers so the
    # global index is stable and independent of which shard is executing.
    all_runs: list[tuple[str, str, dict[str, Any]]] = []
    for tier_id in tiers:
        runs = list(generate_tier_runs(
            manifest,
            tier_id,
            platform=args.platform,
            epochs_override=args.epochs,
            num_agents_override=args.num_agents,
        ))
        for run_id, spec in runs:
            all_runs.append((tier_id, run_id, spec))
        print(f"\n{'=' * 60}")
        print(f"  {tier_id}: {len(runs)} runs")
        print(f"{'=' * 60}")

    def in_shard(global_index: int) -> bool:
        return shard_count is None or global_index % shard_count == shard_index

    shard_total = sum(1 for gi in range(len(all_runs)) if in_shard(gi))
    if shard_count is not None:
        print(
            f"\n  Shard {shard_index}/{shard_count}: "
            f"{shard_total} of {len(all_runs)} runs assigned to this shard",
        )

    total = 0
    succeeded = 0
    failed = 0
    skipped = 0
    executed = 0
    t0 = time.time()

    if args.dry_run:
        elapsed = time.time() - t0
        print(f"\n{'=' * 60}")
        print(f"  DRY RUN — {len(all_runs)} runs total across {len(tiers)} tier(s)")
        if shard_count is not None:
            print(f"  DRY RUN — {shard_total} runs would run on shard {shard_index}")
        print(f"  Output: {OUTPUT_ROOT}")
        print(f"{'=' * 60}")
        return 0

    for global_index, (_tier_id, run_id, spec) in enumerate(all_runs):
        if not in_shard(global_index):
            continue
        if args.limit is not None and executed >= args.limit:
            break
        total += 1
        if run_id in done:
            skipped += 1
            continue
        if retry_only is not None and run_id not in retry_only:
            skipped += 1
            continue
        # Belt-and-suspenders on resume: if the zip already landed in S3, treat
        # as done even when the resume log was truncated mid-upload.
        if (
            (args.resume or args.retry_failed)
            and uploader is not None
            and uploader.object_exists(f"{run_id}.zip")
        ):
            mark_completed(run_id)
            done.add(run_id)
            skipped += 1
            continue

        if args.retry_failed:
            clear_failed_artifacts(run_id)

        elapsed = time.time() - t0
        rate = max(executed, 1) / max(elapsed, 1e-6)
        remaining_n = max(shard_total - total, 0)
        eta_min = remaining_n / max(rate, 1e-6) / 60.0
        print(
            f"  [g{global_index + 1}/{len(all_runs)}] {run_id}  "
            f"({succeeded}ok {failed}err {skipped}skip  "
            f"~{eta_min:.0f}min left)",
            end="",
            flush=True,
        )

        if args.in_process:
            ok = run_simulation(
                run_id,
                spec,
                full_telemetry=args.full_telemetry,
                keep_workdir=args.keep_workdir,
            )
        else:
            ok = run_simulation_subprocess(
                run_id,
                spec,
                full_telemetry=args.full_telemetry,
                keep_workdir=args.keep_workdir,
                timeout=args.timeout,
            )
        executed += 1
        if ok:
            succeeded += 1
            mark_completed(run_id)
            if uploader is not None:
                zip_path = OUTPUT_ROOT / f"{run_id}.zip"
                try:
                    uploader.upload_file(zip_path, f"{run_id}.zip")
                    print(" OK+s3")
                except Exception as exc:  # noqa: BLE001
                    print(f" OK (s3 upload failed: {exc})")
                if args.s3_log_every > 0 and succeeded % args.s3_log_every == 0:
                    _upload_completed_log(uploader, shard_index, shard_count)
            else:
                print(" OK")
        else:
            failed += 1
            mark_failed(run_id)
            print(" FAIL")

    # Final upload of this shard's resume log so retries skip finished runs.
    if uploader is not None:
        _upload_completed_log(uploader, shard_index, shard_count)

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  Campaign: {total} listed, {succeeded} ok, {failed} err, {skipped} skip")
    print(f"  Time: {elapsed / 3600:.2f}h ({elapsed / max(executed, 1):.1f}s/run)")
    print(f"  Output: {OUTPUT_ROOT}")
    print(f"{'=' * 60}")
    return 1 if failed else 0


def _resume_log_key(shard_index: int, shard_count: int | None) -> str:
    suffix = f"shard-{shard_index}" if shard_count is not None else "single"
    return f"_resume/completed_runs.{suffix}.txt"


def _upload_completed_log(
    uploader: S3Uploader,
    shard_index: int,
    shard_count: int | None,
) -> None:
    """Upload this shard's completed_runs.txt under a shard-scoped key."""
    if not COMPLETED_LOG.exists():
        return
    try:
        uploader.upload_file(
            COMPLETED_LOG, _resume_log_key(shard_index, shard_count),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  (completed_runs.txt upload failed: {exc})")


def _download_completed_log(
    uploader: S3Uploader,
    shard_index: int,
    shard_count: int | None,
) -> None:
    """Seed local completed_runs.txt from S3 so Spot retries skip finished runs."""
    key = _resume_log_key(shard_index, shard_count)
    try:
        ok = uploader.download_file(key, COMPLETED_LOG)
    except Exception as exc:  # noqa: BLE001
        print(f"  (completed_runs.txt download failed: {exc})")
        return
    if ok:
        n = len(completed_runs())
        print(f"  Resumed from s3://…/{key} ({n} completed run_ids)")
    else:
        print(f"  No prior resume log at s3://…/{key}")


if __name__ == "__main__":
    raise SystemExit(main())
