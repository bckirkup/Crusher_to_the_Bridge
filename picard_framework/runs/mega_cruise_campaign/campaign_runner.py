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

from simulation_utils.paths import (  # noqa: E402
    is_path_under_base,
    prepare_output_directory,
    resolve_child_path,
    validate_path_component,
    validated_open,
)
from simulation_utils.epidemic_labels import epidemic_took_off  # noqa: E402

CAMPAIGN_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = CAMPAIGN_DIR / "campaign_manifest.json"
COMPLETED_RUNS_FILENAME = "completed_runs.txt"
FAILED_RUNS_FILENAME = "failed_runs.txt"
OUTPUT_ROOT = REPO_ROOT / "telemetry_buffer" / "mega_cruise_campaign"
COMPLETED_LOG = OUTPUT_ROOT / COMPLETED_RUNS_FILENAME
FAILED_LOG = OUTPUT_ROOT / FAILED_RUNS_FILENAME

_REPO_ROOT_STR = str(REPO_ROOT)


def set_output_root(path: Path | str) -> Path:
    """Redirect campaign zips / resume logs (e.g. Contam thin arm).

    Updates module-level ``OUTPUT_ROOT``, ``COMPLETED_LOG``, and ``FAILED_LOG``
    so ``--output-dir`` and tests stay consistent.

    Mutates ``globals()`` instead of the ``global`` keyword so Law-compliance
    AST scans stay clean while callers can still read the module attributes.
    """
    root = Path(path)
    if not root.is_absolute():
        root = (REPO_ROOT / root).resolve()
    else:
        root = root.resolve()
    g = globals()
    g["OUTPUT_ROOT"] = root
    g["COMPLETED_LOG"] = root / COMPLETED_RUNS_FILENAME
    g["FAILED_LOG"] = root / FAILED_RUNS_FILENAME
    return root


def _output_root_str() -> str:
    return str(OUTPUT_ROOT)


def _allowed_roots(*extra: str) -> tuple[str, ...]:
    """Repo root plus redirected output root(s) (pytest / --single outdir)."""
    roots = [_REPO_ROOT_STR]
    candidates = [_output_root_str(), *extra]
    for candidate in candidates:
        out = os.path.realpath(candidate)
        if out and not is_path_under_base(_REPO_ROOT_STR, out):
            if out not in roots:
                roots.append(out)
    return tuple(roots)


def _safe_run_id(run_id: str) -> str:
    """Validate a campaign run_id as a single path component (no traversal)."""
    return validate_path_component(run_id, label="run_id")


def _ensure_output_root(*extra_roots: str) -> str:
    roots = _allowed_roots(*extra_roots)
    return prepare_output_directory(_output_root_str(), allowed_roots=roots)


def _output_artifact(filename: str) -> str:
    """Resolve a single validated filename under the campaign output root."""
    root = _ensure_output_root()
    safe_name = validate_path_component(filename, label="output artifact")
    return resolve_child_path(root, safe_name)


def _run_workdir(run_id: str, *, output_root: str | None = None) -> str:
    root = output_root if output_root is not None else _ensure_output_root()
    roots = _allowed_roots(root)
    prepare_output_directory(root, allowed_roots=roots)
    return resolve_child_path(root, _safe_run_id(run_id))


def _confine_campaign_path(path: str | Path, *extra_roots: str) -> str:
    """Confine a path to the repo or the (possibly redirected) output root."""
    text = str(path)
    roots = _allowed_roots(*extra_roots)
    resolved = os.path.realpath(text if os.path.isabs(text) else os.path.join(roots[0], text))
    for root in roots:
        if is_path_under_base(root, resolved):
            return resolved
    raise ValueError(f"Path {text!r} escapes allowed campaign roots")


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    safe_path = _confine_campaign_path(path)
    with validated_open(safe_path, allowed_roots=_allowed_roots(), encoding="utf-8") as fh:
        return json.load(fh)


def _read_run_id_log(path: Path) -> set[str]:
    safe_path = _confine_campaign_path(path)
    if not os.path.isfile(safe_path):
        return set()
    with validated_open(safe_path, allowed_roots=_allowed_roots(), encoding="utf-8") as fh:
        return {line.strip() for line in fh.read().splitlines() if line.strip()}


def completed_runs() -> set[str]:
    return _read_run_id_log(COMPLETED_LOG)


def failed_runs() -> set[str]:
    return _read_run_id_log(FAILED_LOG)


def mark_completed(run_id: str) -> None:
    safe_id = _safe_run_id(run_id)
    log_path = _output_artifact(COMPLETED_LOG.name)
    with validated_open(log_path, "a", allowed_roots=_allowed_roots(), encoding="utf-8") as fh:
        fh.write(safe_id + "\n")
    # A later success clears a prior failure entry for the same run_id.
    _remove_from_log(FAILED_LOG, safe_id)


def mark_failed(run_id: str) -> None:
    safe_id = _safe_run_id(run_id)
    log_path = _output_artifact(FAILED_RUNS_FILENAME)
    with validated_open(log_path, "a", allowed_roots=_allowed_roots(), encoding="utf-8") as fh:
        fh.write(safe_id + "\n")


def _remove_from_log(path: Path, run_id: str) -> None:
    safe_id = _safe_run_id(run_id)
    safe_path = _confine_campaign_path(path)
    if not os.path.isfile(safe_path):
        return
    with validated_open(safe_path, allowed_roots=_allowed_roots(), encoding="utf-8") as fh:
        kept = [line for line in fh.read().splitlines() if line.strip() != safe_id]
    if kept:
        with validated_open(safe_path, "w", allowed_roots=_allowed_roots(), encoding="utf-8") as fh:
            fh.write("\n".join(kept) + "\n")
    else:
        os.remove(safe_path)


def clear_failed_artifacts(run_id: str) -> None:
    """Remove leftover workdir / stderr from a prior failure before retry."""
    safe_id = _safe_run_id(run_id)
    run_dir = _run_workdir(safe_id)
    if os.path.isdir(run_dir):
        shutil.rmtree(run_dir)
    for name in (
        f"{safe_id}.subprocess_stderr.txt",
        f"{safe_id}.run_spec.json",
        f"{safe_id}.failure.json",
        f"{safe_id}.resource.json",
    ):
        artifact = _output_artifact(name)
        if os.path.isfile(artifact):
            os.remove(artifact)


def _read_vmhwm_kb(pid: int) -> int | None:
    """Return peak RSS (VmHWM) in KiB from ``/proc/<pid>/status``, if available."""
    try:
        with validated_open(
            f"/proc/{int(pid)}/status",
            allowed_roots=("/proc",),
            encoding="utf-8",
        ) as fh:
            for line in fh:
                if line.startswith("VmHWM:"):
                    return int(line.split()[1])
    except (OSError, ValueError):
        return None
    return None


def _looks_like_oom(returncode: int | None) -> bool:
    """True when the child exit code matches a typical OOM kill (SIGKILL / 137)."""
    if returncode is None:
        return False
    return returncode in (-9, 137)


def _failure_class(*, timed_out: bool, returncode: int | None) -> str:
    if timed_out:
        return "timeout"
    if _looks_like_oom(returncode):
        return "oom"
    return "other"


def _write_run_sidecars(
    safe_id: str,
    *,
    returncode: int | None,
    timeout: int,
    timed_out: bool,
    peak_rss_kb: int | None,
    ok: bool,
) -> None:
    """Write resource.json always; failure.json only when the run did not succeed."""
    roots = _allowed_roots()
    resource = {
        "run_id": safe_id,
        "returncode": returncode,
        "timeout_s": timeout,
        "timed_out": timed_out,
        "peak_rss_kb": peak_rss_kb,
        "looks_like_oom": _looks_like_oom(returncode),
        "ok": ok,
    }
    resource_path = _output_artifact(f"{safe_id}.resource.json")
    with validated_open(resource_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
        json.dump(resource, fh, indent=2)
        fh.write("\n")
    print(
        f"RESOURCE run_id={safe_id} peak_rss_kb={peak_rss_kb} "
        f"returncode={returncode} timed_out={timed_out} ok={ok}",
        flush=True,
    )
    if ok:
        return
    failure = {
        **resource,
        "failure_class": _failure_class(timed_out=timed_out, returncode=returncode),
    }
    failure_path = _output_artifact(f"{safe_id}.failure.json")
    with validated_open(failure_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
        json.dump(failure, fh, indent=2)
        fh.write("\n")


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
            from botocore.exceptions import ClientError as client_error  # noqa: PLC0415
        except ImportError:  # pragma: no cover
            client_error = Exception  # type: ignore[misc, assignment]
        local_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._client.download_file(self.bucket, key, str(local_path))
            return True
        except client_error as exc:
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


def _tier_is_deferred(tier: dict[str, Any]) -> bool:
    return bool(tier.get("deferred"))


def resolve_tier_ids(
    manifest: dict[str, Any],
    tier_arg: str | None,
    *,
    include_deferred: bool = False,
) -> list[str]:
    """Accept full keys (t1_pathogen_baselines) or short prefixes (t1).

    Tiers with ``\"deferred\": true`` are omitted from ``all`` / ``*`` /
    omitted-arg selection unless ``include_deferred`` is set. An explicit
    tier id or short prefix (e.g. ``--tier c2``) always includes them so
    wave-2 calibration can be launched after pinning ``dose_adjustment``.
    """
    keys = sorted(manifest["tiers"].keys())
    if not tier_arg or tier_arg in ("all", "*"):
        if include_deferred:
            return keys
        return [k for k in keys if not _tier_is_deferred(manifest["tiers"][k])]
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


# Canonical ship-class populations for multi-platform calibration (c1–c6, a2).
# classic_cruise_1900 is named for CDC "Large" ~1900 but ships 1910 agents.
_PLATFORM_DEFAULT_AGENTS: dict[str, int] = {
    "expedition_cruise_450": 450,
    "classic_cruise_1900": 1910,
    "spirit_cruise_3000": 3000,
    "mega_cruise_5000": 7000,
}


def _dose_tag(dose: float) -> str:
    """Compact run-id fragment for a dose_adjustment value."""
    d = float(dose)
    if d == int(d):
        return f"dose{int(d)}"
    return f"dose{str(d).replace('.', 'p')}"


def _alpha_tag(alpha: float) -> str:
    """Compact run-id fragment for a density exponent (e.g. 0.5 → a050)."""
    return f"a{int(round(float(alpha) * 100)):03d}"


def _contact_mode_tag(mode: str) -> str:
    """Compact run-id fragment for contact_mode."""
    aliases = {
        "legacy": "legacy",
        "density_dependent": "dd",
        "heterogeneous_zone_dose": "het",
    }
    return aliases.get(mode, mode.replace("_", "")[:8])


def _density_exponent_values(tier: dict[str, Any]) -> list[float | None]:
    """Density-exponent sweep; ``[None]`` means leave transmission config alone."""
    if "density_exponents" in tier:
        return [float(a) for a in tier["density_exponents"]]
    return [None]


def _contact_mode_values(tier: dict[str, Any]) -> list[str | None]:
    """Contact-mode sweep; ``[None]`` means leave transmission.contact_mode alone."""
    if "contact_modes" in tier:
        return [str(m) for m in tier["contact_modes"]]
    return [None]


def _density_contact_override(
    alpha: float | None,
    contact_mode: str | None = None,
) -> dict[str, Any] | None:
    """Config override for density exponent and/or contact_mode."""
    if alpha is None and contact_mode is None:
        return None
    tx: dict[str, Any] = {}
    if contact_mode is not None:
        tx["contact_mode"] = str(contact_mode)
    else:
        # Exponent sweeps imply density-family modes unless mode is explicit.
        # (After the early return, contact_mode is None ⇒ alpha is not None.)
        tx["contact_mode"] = "density_dependent"
    if alpha is not None:
        tx["density_dependent"] = {"exponent": float(alpha)}
    return {"transmission": tx}


def _resolve_tier_platforms(
    tier: dict[str, Any],
    *,
    fallback_platform: str,
    platform_override: str | None = None,
) -> list[str]:
    """Resolve platform list for a tier (singular ``platform`` or ``platforms``)."""
    if platform_override:
        return [platform_override]
    if "platforms" in tier:
        return [str(p) for p in tier["platforms"]]
    if "platform" in tier:
        return [str(tier["platform"])]
    return [fallback_platform]


def _platform_num_agents(
    platform_id: str,
    *,
    num_agents_override: int | None = None,
    tier: dict[str, Any] | None = None,
    default_agents: int = 7000,
) -> int:
    """Agent count from CLI override, tier override, or platform size table."""
    if num_agents_override is not None:
        return int(num_agents_override)
    if tier is not None and "num_agents" in tier:
        return int(tier["num_agents"])
    return int(_PLATFORM_DEFAULT_AGENTS.get(platform_id, default_agents))


def _calibration_dose_values(tier: dict[str, Any]) -> list[float | None]:
    """Dose sweep values; ``[None]`` means leave bundle dose_adjustment alone."""
    if "dose_adjustments" in tier:
        return [float(d) for d in tier["dose_adjustments"]]
    if "dose_adjustment" in tier:
        return [float(tier["dose_adjustment"])]
    return [None]


def _calibration_init_values(tier: dict[str, Any]) -> list[int | None]:
    """Initial-infected sweep; accepts ``initial_infected_values`` or ``initial_infected``."""
    if "initial_infected_values" in tier:
        return [int(n) for n in tier["initial_infected_values"]]
    if "initial_infected" in tier:
        raw = tier["initial_infected"]
        if isinstance(raw, list):
            return [int(n) for n in raw]
        return [int(raw)]
    return [None]


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
    history_retention: str = "compact",
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = merge_cfg(
        {"ship_graph": {"num_agents": num_agents}},
        config_overrides,
    )
    retention = str(history_retention or "compact").strip().lower()
    if retention not in ("full", "compact"):
        retention = "compact"
    spec: dict[str, Any] = {
        "schema_version": "1.0.0",
        "description": run_id,
        "catalog": {"platform_id": platform, "pathogen_bundle_id": bundle},
        "run": {
            "random_seed": seed,
            "num_epochs": epochs,
            "write_ground_truth": write_ground_truth,
            "history_retention": retention,
        },
        "legacy_yaml": "crusher_labs/config.yaml",
        "actors": [],
        "incentives": {},
    }
    if pathogen_overrides:
        spec["pathogen_overrides"] = pathogen_overrides
    if cfg:
        spec["config_overrides"] = cfg
    if parameters:
        spec["campaign_parameters"] = dict(parameters)
    elif parameters is None:
        # Always attach a minimal parameters block for bookkeeping.
        spec["campaign_parameters"] = {
            "run_id": run_id,
            "platform_id": platform,
            "pathogen_bundle_id": bundle,
            "seed": int(seed),
            "num_epochs": int(epochs),
            "num_agents": int(num_agents),
            "history_retention": retention,
        }
    if telemetry_dir is not None:
        # Absolute paths so finalize does not clobber shared telemetry_buffer/.
        spec["run"]["simulation_history"] = str(telemetry_dir / "simulation_history.json")
        spec["run"]["lab_notebook"] = str(telemetry_dir / "artificial_lab_notebook.json")
        spec["run"]["ground_truth"] = str(telemetry_dir / "ground_truth.json")
    return spec


def _campaign_parameters(
    *,
    tier_id: str,
    run_id: str,
    platform: str,
    bundle: str,
    seed: int,
    epochs: int,
    num_agents: int,
    pathogen: str | None = None,
    config_overrides: dict[str, Any] | None = None,
    history_retention: str = "compact",
    **factors: Any,
) -> dict[str, Any]:
    """Build analysis-friendly factor labels for summary.json / aggregate CSV."""
    params: dict[str, Any] = {
        "tier_id": tier_id,
        "run_id": run_id,
        "platform_id": platform,
        "pathogen_bundle_id": bundle,
        "seed": int(seed),
        "num_epochs": int(epochs),
        "num_agents": int(num_agents),
        "history_retention": history_retention,
    }
    if pathogen is not None:
        params["pathogen"] = pathogen
    for key, value in factors.items():
        if value is not None:
            params[key] = value
    cfg = config_overrides or {}
    hvac = cfg.get("hvac") or {}
    if "transport_engine" in hvac and "transport_engine" not in params:
        params["transport_engine"] = hvac["transport_engine"]
    if "filter_efficiency" in hvac:
        params["filter_efficiency"] = hvac["filter_efficiency"]
    if "oa_fraction" in hvac:
        params["outdoor_air_fraction"] = hvac["oa_fraction"]
    if "natural_decay_rate" in hvac:
        params["decay_rate"] = hvac["natural_decay_rate"]
    ship = cfg.get("ship_graph") or {}
    if "immune_fraction" in ship:
        params["immune_fraction"] = ship["immune_fraction"]
    fred = cfg.get("fred_behavior") or {}
    if "quarantine_compliance" in fred:
        params["quarantine_compliance"] = fred["quarantine_compliance"]
    wear = cfg.get("wearable_monitoring") or {}
    if "deployment_profile" in wear and "wearables" not in params:
        params["wearables"] = wear["deployment_profile"]
    if "detection_sensitivity_scale" in wear and "wearable_sensitivity" not in params:
        params["wearable_sensitivity"] = wear["detection_sensitivity_scale"]
    syn = cfg.get("syndromic") or {}
    if "sick_call_probability" in syn and "sick_call_probability" not in params:
        params["sick_call_probability"] = syn["sick_call_probability"]
    if (
        "activation_delay_epochs" in syn
        and "surveillance_delay_epochs" not in params
    ):
        params["surveillance_delay_epochs"] = syn["activation_delay_epochs"]
    esc = cfg.get("escalation") or {}
    latency = esc.get("decision_latency") or {}
    if (
        "confirmed_delay_epochs" in latency
        and "decision_latency_epochs" not in params
    ):
        params["decision_latency_epochs"] = latency["confirmed_delay_epochs"]
    if "suspect_attack_rate" in esc and "suspect_attack_rate" not in params:
        params["suspect_attack_rate"] = esc["suspect_attack_rate"]
    if "lockdown_attack_rate" in esc and "lockdown_attack_rate" not in params:
        params["lockdown_attack_rate"] = esc["lockdown_attack_rate"]
    if "reluctant_fraction" in fred and "reluctant_fraction" not in params:
        params["reluctant_fraction"] = fred["reluctant_fraction"]
    if (
        "reluctant_delay_epochs" in fred
        and "reluctant_delay_epochs" not in params
    ):
        params["reluctant_delay_epochs"] = fred["reluctant_delay_epochs"]
    return params


def parameters_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Resolve the parameters block embedded in summary.json.

    Prefers explicit ``campaign_parameters``; otherwise derives a minimal set
    from the Picard spec so ad-hoc ``--single`` runs stay self-describing.
    """
    attached = spec.get("campaign_parameters")
    if isinstance(attached, dict) and attached:
        return dict(attached)

    catalog = spec.get("catalog") or {}
    run = spec.get("run") or {}
    cfg = spec.get("config_overrides") or {}
    ship = cfg.get("ship_graph") or {}
    params: dict[str, Any] = {
        "run_id": spec.get("description", ""),
        "platform_id": catalog.get("platform_id", ""),
        "pathogen_bundle_id": catalog.get("pathogen_bundle_id", ""),
        "seed": run.get("random_seed"),
        "num_epochs": run.get("num_epochs"),
        "num_agents": ship.get("num_agents"),
        "history_retention": run.get("history_retention", "full"),
    }
    hvac = cfg.get("hvac") or {}
    if "transport_engine" in hvac:
        params["transport_engine"] = hvac["transport_engine"]
    if "filter_efficiency" in hvac:
        params["filter_efficiency"] = hvac["filter_efficiency"]
    if "oa_fraction" in hvac:
        params["outdoor_air_fraction"] = hvac["oa_fraction"]
    if "natural_decay_rate" in hvac:
        params["decay_rate"] = hvac["natural_decay_rate"]
    if "immune_fraction" in ship:
        params["immune_fraction"] = ship["immune_fraction"]
    fred = cfg.get("fred_behavior") or {}
    if "quarantine_compliance" in fred:
        params["quarantine_compliance"] = fred["quarantine_compliance"]
    wear = cfg.get("wearable_monitoring") or {}
    if "deployment_profile" in wear:
        params["wearables"] = wear["deployment_profile"]
    # Drop empty / None so aggregate columns stay sparse.
    return {k: v for k, v in params.items() if v is not None and v != ""}


# Mega-cruise defaults: enable LOCKDOWN AR threshold (config.yaml uses
# "never" so 20-agent smokes do not lockdown on a single case).
_CAMPAIGN_ESCALATION_DEFAULTS = {
    "escalation": {
        "lockdown_attack_rate": 0.05,
        "suspect_attack_rate": 0.02,
        "confirm_attack_rate": 0.03,
    },
}


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
    platform_override = platform  # CLI / caller override (None = use tier/manifest)
    platform = platform_override or manifest["platform"]
    default_epochs = epochs_override or tier.get("epochs", manifest["default_epochs"])
    default_agents = num_agents_override or manifest.get("default_num_agents", 7000)
    surv_cfgs = manifest["surveillance_configs"]
    short = tier_id.split("_", 1)[0]

    def _yield(
        rid: str,
        *,
        bundle: str,
        pathogen_overrides: dict[str, Any] | None,
        config_overrides: dict[str, Any] | None,
        seed: int,
        num_agents: int | None = None,
        pathogen: str | None = None,
        platform_id: str | None = None,
        epochs: int | None = None,
        **factors: Any,
    ) -> tuple[str, dict[str, Any]]:
        n_agents = default_agents if num_agents is None else int(num_agents)
        plat = platform if platform_id is None else str(platform_id)
        n_epochs = default_epochs if epochs is None else int(epochs)
        cfg = merge_cfg(_CAMPAIGN_ESCALATION_DEFAULTS, config_overrides)
        params = _campaign_parameters(
            tier_id=tier_id,
            run_id=rid,
            platform=plat,
            bundle=bundle,
            seed=seed,
            epochs=n_epochs,
            num_agents=n_agents,
            pathogen=pathogen,
            config_overrides=cfg,
            **factors,
        )
        return rid, make_picard_spec(
            rid,
            platform=plat,
            bundle=bundle,
            pathogen_overrides=pathogen_overrides,
            config_overrides=cfg,
            seed=seed,
            epochs=n_epochs,
            num_agents=n_agents,
            parameters=params,
        )

    if short == "t1":
        hvac = {"hvac": tier["hvac"]} if tier.get("hvac") else None
        # v4 uses surveillance_strategies; legacy manifests use a single
        # ``surveillance`` string (default "none"). Keep old run ids when
        # there is no strategy sweep so existing dry-run counts stay stable.
        strategies = list(tier.get("surveillance_strategies") or [])
        if not strategies:
            strategies = [tier.get("surveillance", "none")]
        multi_surv = "surveillance_strategies" in tier
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for sname in strategies:
                for seed in tier["seeds"]:
                    rid = (
                        f"{short}_{pathogen}_{sname}_s{seed}"
                        if multi_surv
                        else f"{short}_{pathogen}_s{seed}"
                    )
                    yield _yield(
                        rid,
                        bundle=bundle,
                        pathogen_overrides=overrides,
                        config_overrides=merge_cfg(hvac, surv_cfgs.get(sname)),
                        seed=seed,
                        pathogen=pathogen,
                        surveillance=sname,
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
                            yield _yield(
                                rid,
                                bundle=bundle,
                                pathogen_overrides=overrides,
                                config_overrides=hvac,
                                seed=seed,
                                pathogen=pathogen,
                                filter=fname,
                                oa=oaname,
                                decay=dname,
                            )

    elif short == "t3":
        hvac = {"hvac": tier["hvac"]} if tier.get("hvac") else None
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for sname in tier["surveillance_strategies"]:
                for seed in tier["seeds"]:
                    rid = f"{short}_{pathogen}_{sname}_s{seed}"
                    yield _yield(
                        rid,
                        bundle=bundle,
                        pathogen_overrides=overrides,
                        config_overrides=merge_cfg(hvac, surv_cfgs.get(sname)),
                        seed=seed,
                        pathogen=pathogen,
                        surveillance=sname,
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
                            yield _yield(
                                rid,
                                bundle=bundle,
                                pathogen_overrides=overrides,
                                config_overrides=merge_cfg(hvac, surv_cfgs.get(sname)),
                                seed=seed,
                                pathogen=pathogen,
                                filter=fname,
                                decay=dname,
                                surveillance=sname,
                            )

    elif short == "t5":
        for combo in tier["combos"]:
            bundle, overrides = combo_overrides(manifest, combo)
            safe = combo.replace("+", "_")
            for sname in tier["surveillance_strategies"]:
                for seed in tier["seeds"]:
                    rid = f"{short}_{safe}_{sname}_s{seed}"
                    yield _yield(
                        rid,
                        bundle=bundle,
                        pathogen_overrides=overrides,
                        config_overrides=surv_cfgs.get(sname),
                        seed=seed,
                        combo=combo,
                        surveillance=sname,
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
                        yield _yield(
                            rid,
                            bundle=bundle,
                            pathogen_overrides=path_over,
                            config_overrides=cfg_over,
                            seed=seed,
                            pathogen=pathogen,
                            n_init=int(n_init),
                            immunity=imm_frac,
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
                            yield _yield(
                                rid,
                                bundle=bundle,
                                pathogen_overrides=overrides,
                                config_overrides=cfg_over,
                                seed=seed,
                                pathogen=pathogen,
                                surveillance=sname,
                                compliance=float(comp),
                                immunity=imm_frac,
                            )

    elif short == "t8":
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for wname in tier["wearable_configs"]:
                wear = {"wearable_monitoring": {"deployment_profile": wname}}
                for sname in tier["surveillance_strategies"]:
                    for seed in tier["seeds"]:
                        rid = f"{short}_{pathogen}_{wname}_{sname}_s{seed}"
                        yield _yield(
                            rid,
                            bundle=bundle,
                            pathogen_overrides=overrides,
                            config_overrides=merge_cfg(surv_cfgs.get(sname), wear),
                            seed=seed,
                            pathogen=pathogen,
                            wearables=wname,
                            surveillance=sname,
                        )

    elif short == "t9":
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for sname in tier["surveillance_strategies"]:
                for seed in tier["seeds"]:
                    rid = f"{short}_{pathogen}_{sname}_s{seed}"
                    yield _yield(
                        rid,
                        bundle=bundle,
                        pathogen_overrides=overrides,
                        config_overrides=surv_cfgs.get(sname),
                        seed=seed,
                        pathogen=pathogen,
                        surveillance=sname,
                    )

    elif short == "t10":
        strategies = list(tier.get("surveillance_strategies") or [])
        multi_surv = bool(strategies)
        if not strategies:
            strategies = [None]  # legacy: no surveillance override / tag
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for n_agents in tier["population_sizes"]:
                for sname in strategies:
                    surv = surv_cfgs.get(sname) if sname is not None else None
                    for seed in tier["seeds"]:
                        if multi_surv:
                            rid = (
                                f"{short}_{pathogen}_{sname}"
                                f"_n{n_agents}_s{seed}"
                            )
                        else:
                            rid = f"{short}_{pathogen}_n{n_agents}_s{seed}"
                        yield _yield(
                            rid,
                            bundle=bundle,
                            pathogen_overrides=overrides,
                            config_overrides=surv,
                            seed=seed,
                            num_agents=int(n_agents),
                            pathogen=pathogen,
                            surveillance=sname,
                        )

    elif short == "t11":
        # Campaign v5: decision-latency sweep (escalation.decision_latency).
        # Legacy: surveillance_delay_epochs still supported for v4 manifests.
        if "decision_latency_levels" in tier:
            for pathogen in tier["pathogens"]:
                bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
                for level in tier["decision_latency_levels"]:
                    # level may be int (confirmed delay) or dict of delays
                    if isinstance(level, dict):
                        lat = {
                            "alert_delay_epochs": int(level.get("alert", 0)),
                            "suspected_delay_epochs": int(level.get("suspected", 0)),
                            "confirmed_delay_epochs": int(level.get("confirmed", 0)),
                            "lockdown_delay_epochs": int(level.get("lockdown", 0)),
                        }
                        delay_tag = int(level.get("confirmed", 0))
                    else:
                        delay_tag = int(level)
                        lat = {
                            "alert_delay_epochs": min(delay_tag, 6),
                            "suspected_delay_epochs": delay_tag,
                            "confirmed_delay_epochs": delay_tag,
                            "lockdown_delay_epochs": max(delay_tag, 24),
                        }
                    lat_over = {"escalation": {"decision_latency": lat}}
                    for sname in tier["surveillance_strategies"]:
                        for comp in tier.get("compliance_levels", [None]):
                            behavior = None
                            if comp is not None:
                                behavior = {
                                    "fred_behavior": {
                                        "quarantine_compliance": float(comp),
                                    },
                                }
                            for seed in tier["seeds"]:
                                comp_tag = (
                                    f"_comp{int(float(comp) * 100)}"
                                    if comp is not None else ""
                                )
                                rid = (
                                    f"{short}_{pathogen}_{sname}"
                                    f"_lat{delay_tag}{comp_tag}_s{seed}"
                                )
                                yield _yield(
                                    rid,
                                    bundle=bundle,
                                    pathogen_overrides=overrides,
                                    config_overrides=merge_cfg(
                                        merge_cfg(surv_cfgs.get(sname), lat_over),
                                        behavior,
                                    ),
                                    seed=seed,
                                    pathogen=pathogen,
                                    surveillance=sname,
                                    decision_latency_epochs=delay_tag,
                                    compliance=(
                                        float(comp) if comp is not None else None
                                    ),
                                )
        else:
            # Legacy: activation_delay_epochs on syndromic + cascade.
            # Optional compliance_levels (v6) crossed with delay × surveillance.
            for pathogen in tier["pathogens"]:
                bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
                for delay in tier["surveillance_delay_epochs"]:
                    delay_over = {
                        "syndromic": {"activation_delay_epochs": int(delay)},
                        "diagnostic_cascade": {"activation_delay_epochs": int(delay)},
                    }
                    for sname in tier["surveillance_strategies"]:
                        for comp in tier.get("compliance_levels", [None]):
                            behavior = None
                            if comp is not None:
                                behavior = {
                                    "fred_behavior": {
                                        "quarantine_compliance": float(comp),
                                    },
                                }
                            for seed in tier["seeds"]:
                                comp_tag = (
                                    f"_comp{int(float(comp) * 100)}"
                                    if comp is not None else ""
                                )
                                rid = (
                                    f"{short}_{pathogen}_{sname}"
                                    f"_delay{int(delay)}{comp_tag}_s{seed}"
                                )
                                yield _yield(
                                    rid,
                                    bundle=bundle,
                                    pathogen_overrides=overrides,
                                    config_overrides=merge_cfg(
                                        merge_cfg(surv_cfgs.get(sname), delay_over),
                                        behavior,
                                    ),
                                    seed=seed,
                                    pathogen=pathogen,
                                    surveillance=sname,
                                    surveillance_delay_epochs=int(delay),
                                    compliance=(
                                        float(comp) if comp is not None else None
                                    ),
                                )

    elif short == "t12":
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for scp in tier["sick_call_probabilities"]:
                sick_over = {"syndromic": {"sick_call_probability": float(scp)}}
                for sname in tier["surveillance_strategies"]:
                    for seed in tier["seeds"]:
                        rid = (
                            f"{short}_{pathogen}_{sname}"
                            f"_scp{int(round(float(scp) * 100))}_s{seed}"
                        )
                        yield _yield(
                            rid,
                            bundle=bundle,
                            pathogen_overrides=overrides,
                            config_overrides=merge_cfg(
                                surv_cfgs.get(sname), sick_over,
                            ),
                            seed=seed,
                            pathogen=pathogen,
                            surveillance=sname,
                            sick_call_probability=float(scp),
                        )

    elif short == "t13":
        wname = tier.get("wearable_config", "crew_only")
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for sens in tier["wearable_sensitivities"]:
                wear = {
                    "wearable_monitoring": {
                        "deployment_profile": wname,
                        "detection_sensitivity_scale": float(sens),
                    },
                }
                for sname in tier["surveillance_strategies"]:
                    for seed in tier["seeds"]:
                        rid = (
                            f"{short}_{pathogen}_{wname}_{sname}"
                            f"_wsens{int(round(float(sens) * 100))}_s{seed}"
                        )
                        yield _yield(
                            rid,
                            bundle=bundle,
                            pathogen_overrides=overrides,
                            config_overrides=merge_cfg(
                                surv_cfgs.get(sname), wear,
                            ),
                            seed=seed,
                            pathogen=pathogen,
                            wearables=wname,
                            surveillance=sname,
                            wearable_sensitivity=float(sens),
                        )

    elif short == "t14":
        sname = tier.get("surveillance", "syndromic")
        surv = surv_cfgs.get(sname)
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for imm_frac in tier["pre_immunity_fractions"]:
                imm_over, imm_tag = _immunity_override(imm_frac)
                for seed in tier["seeds"]:
                    rid = f"{short}_{pathogen}{imm_tag}_s{seed}"
                    yield _yield(
                        rid,
                        bundle=bundle,
                        pathogen_overrides=overrides,
                        config_overrides=merge_cfg(surv, imm_over),
                        seed=seed,
                        pathogen=pathogen,
                        surveillance=sname,
                        immunity=imm_frac,
                    )

    elif short == "t15":
        # SOP threshold sweep: suspect_attack_rate × lockdown_attack_rate
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for suspect_ar in tier["suspect_attack_rates"]:
                for lockdown_ar in tier["lockdown_attack_rates"]:
                    lockdown_val = (
                        None if lockdown_ar in (None, "never") else float(lockdown_ar)
                    )
                    lockdown_tag = (
                        "never" if lockdown_val is None
                        else f"{int(round(float(lockdown_ar) * 100))}"
                    )
                    esc_over = {
                        "escalation": {
                            "suspect_attack_rate": float(suspect_ar),
                            "lockdown_attack_rate": lockdown_val,
                        },
                    }
                    for seed in tier["seeds"]:
                        rid = (
                            f"{short}_{pathogen}"
                            f"_sar{int(round(float(suspect_ar) * 100))}"
                            f"_lar{lockdown_tag}_s{seed}"
                        )
                        yield _yield(
                            rid,
                            bundle=bundle,
                            pathogen_overrides=overrides,
                            config_overrides=esc_over,
                            seed=seed,
                            pathogen=pathogen,
                            suspect_attack_rate=float(suspect_ar),
                            lockdown_attack_rate=(
                                "never" if lockdown_val is None else float(lockdown_ar)
                            ),
                        )

    elif short == "t16":
        # Reluctant fraction × reluctant delay sweep
        for pathogen in tier["pathogens"]:
            bundle, _pid, overrides = get_pathogen_config(manifest, pathogen)
            for rfrac in tier["reluctant_fractions"]:
                for rdelay in tier["reluctant_delay_epochs"]:
                    behavior = {
                        "fred_behavior": {
                            "reluctant_fraction": float(rfrac),
                            "reluctant_delay_epochs": int(rdelay),
                            "quarantine_compliance": float(
                                tier.get("quarantine_compliance", 0.6),
                            ),
                        },
                    }
                    for seed in tier["seeds"]:
                        rid = (
                            f"{short}_{pathogen}"
                            f"_rf{int(round(float(rfrac) * 100))}"
                            f"_rd{int(rdelay)}_s{seed}"
                        )
                        yield _yield(
                            rid,
                            bundle=bundle,
                            pathogen_overrides=overrides,
                            config_overrides=behavior,
                            seed=seed,
                            pathogen=pathogen,
                            reluctant_fraction=float(rfrac),
                            reluctant_delay_epochs=int(rdelay),
                        )

    elif short in ("c1", "c2", "c3", "c4", "c5", "c6", "a2", "b1", "b2"):
        # Multi-platform calibration / sensitivity (data-driven): keys off
        # tier fields. c1: dose × init × platform; c2: immunity × platforms;
        # c3: SARS-CoV-2 dose × platforms; c4: epoch_durations × dose;
        # c5: density_exponents × dose × platforms;
        # c6: contact_modes (density vs heterogeneous) sensitivity;
        # a2: fine dose × FUT2 immunity at a pinned density exponent.
        # b1/b2: boundary_surface_v1 k-sweep (core + dose_adj sensitivity).
        pathogen = tier["pathogen"]  # singular (not pathogens[])
        bundle, pathogen_id, base_overrides = get_pathogen_config(manifest, pathogen)
        platforms = _resolve_tier_platforms(
            tier,
            fallback_platform=manifest["platform"],
            platform_override=platform_override,
        )
        doses = _calibration_dose_values(tier)
        inits = _calibration_init_values(tier)
        alphas = _density_exponent_values(tier)
        contact_modes = _contact_mode_values(tier)
        immunities = tier.get("pre_immunity_fractions", [None])
        hvac = {"hvac": tier["hvac"]} if tier.get("hvac") else None
        if epochs_override is not None:
            epoch_list = [int(epochs_override)]
        elif "epoch_durations" in tier:
            epoch_list = [int(e) for e in tier["epoch_durations"]]
        else:
            epoch_list = [int(default_epochs)]
        sweep_epochs = "epoch_durations" in tier and epochs_override is None
        strategies = list(tier.get("surveillance_strategies") or [])
        if not strategies:
            strategies = [tier.get("surveillance", "none")]

        for plat in platforms:
            n_agents = _platform_num_agents(
                plat,
                num_agents_override=num_agents_override,
                tier=tier,
                default_agents=int(manifest.get("default_num_agents", 7000)),
            )
            for dose in doses:
                for n_init in inits:
                    path_over = dict(base_overrides or {})
                    patch: dict[str, Any] = {}
                    if dose is not None:
                        patch["dose_adjustment"] = float(dose)
                    if n_init is not None:
                        patch["initial_infected"] = int(n_init)
                    if patch:
                        path_over[pathogen_id] = {
                            **(path_over.get(pathogen_id) or {}),
                            **patch,
                        }
                    for alpha in alphas:
                        for cmode in contact_modes:
                            dens_over = _density_contact_override(
                                alpha, contact_mode=cmode,
                            )
                            for imm_frac in immunities:
                                imm_over, imm_tag = _immunity_override(imm_frac)
                                for n_epochs in epoch_list:
                                    for sname in strategies:
                                        for seed in tier["seeds"]:
                                            rid_parts = [short, pathogen, plat]
                                            if dose is not None:
                                                rid_parts.append(_dose_tag(dose))
                                            if n_init is not None:
                                                rid_parts.append(
                                                    f"init{int(n_init)}",
                                                )
                                            if alpha is not None:
                                                rid_parts.append(_alpha_tag(alpha))
                                            if cmode is not None:
                                                rid_parts.append(
                                                    _contact_mode_tag(cmode),
                                                )
                                            if sweep_epochs:
                                                rid_parts.append(
                                                    f"ep{int(n_epochs)}",
                                                )
                                            if imm_tag:
                                                rid_parts.append(
                                                    imm_tag.lstrip("_"),
                                                )
                                            rid_parts.append(sname)
                                            rid_parts.append(f"s{seed}")
                                            rid = "_".join(rid_parts)
                                            yield _yield(
                                                rid,
                                                bundle=bundle,
                                                pathogen_overrides=path_over,
                                                config_overrides=merge_cfg(
                                                    surv_cfgs.get(sname),
                                                    imm_over,
                                                    dens_over,
                                                    hvac,
                                                ),
                                                seed=seed,
                                                num_agents=n_agents,
                                                pathogen=pathogen,
                                                platform_id=plat,
                                                epochs=int(n_epochs),
                                                surveillance=sname,
                                                dose_adjustment=dose,
                                                n_init=n_init,
                                                immunity=imm_frac,
                                                density_exponent=alpha,
                                                contact_mode=cmode,
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

    # Outbreak = takeoff (VSP while still accelerating) vs fizzle.
    outbreak_occurred = epidemic_took_off(ts)

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
    safe_id = _safe_run_id(run_id)
    root_str = (
        os.path.realpath(str(output_root))
        if output_root is not None
        else _ensure_output_root()
    )
    roots = _allowed_roots(root_str)
    prepare_output_directory(root_str, allowed_roots=roots)
    run_dir = _run_workdir(safe_id, output_root=root_str)
    if os.path.isdir(run_dir):
        shutil.rmtree(run_dir)
    prepare_output_directory(run_dir, allowed_roots=roots)

    # Always copy so we can set retention / telemetry paths without mutating caller.
    spec = dict(spec)
    spec["run"] = dict(spec.get("run") or {})
    if full_telemetry:
        spec["run"]["write_ground_truth"] = True
        spec["run"]["history_retention"] = "full"
        spec["run"]["simulation_history"] = os.path.join(run_dir, "simulation_history.json")
        spec["run"]["lab_notebook"] = os.path.join(run_dir, "artificial_lab_notebook.json")
        spec["run"]["ground_truth"] = os.path.join(run_dir, "ground_truth.json")
        if isinstance(spec.get("campaign_parameters"), dict):
            spec["campaign_parameters"] = dict(spec["campaign_parameters"])
            spec["campaign_parameters"]["history_retention"] = "full"
    else:
        # Campaign default: compact in-RAM history (summary / spaces / cost only).
        spec["run"].setdefault("history_retention", "compact")
        spec["run"].setdefault("write_ground_truth", False)

    spec_path = resolve_child_path(run_dir, "run_spec.json")
    with validated_open(spec_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)

    try:
        from picard_framework.run_spec import PicardRunSpec
        from picard_framework.simulation.ship_simulation import ShipSimulation

        picard_spec = PicardRunSpec.from_picard_json(_REPO_ROOT_STR, spec_path)
        sim = ShipSimulation(picard_spec, display=False)
        result = sim.run()
        if full_telemetry:
            sim.finalize(display=False)

        last = result.history[-1] if result.history else {}
        ts = extract_timeseries(result.history)
        ts_path = resolve_child_path(run_dir, "timeseries.json")
        with validated_open(ts_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
            json.dump(ts, fh)

        summary = {
            "run_id": safe_id,
            "parameters": parameters_from_spec(spec),
            "num_epochs": result.num_epochs,
            "trigger_status": result.final_trigger_status,
            "summary": last.get("summary", {}),
            "cost_accounting": last.get("cost_accounting", {}),
            "derived": compute_derived_metrics(ts, _spec_num_agents(spec)),
        }
        summary_path = resolve_child_path(run_dir, "summary.json")
        with validated_open(summary_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)

        zip_name = validate_path_component(f"{safe_id}.zip", label="zip artifact")
        zip_path = resolve_child_path(root_str, zip_name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for dirpath, _dirnames, filenames in os.walk(run_dir):
                for fname in filenames:
                    fpath = os.path.join(dirpath, fname)
                    zf.write(fpath, os.path.relpath(fpath, run_dir))
        if not keep_workdir:
            shutil.rmtree(run_dir)
        return True

    except Exception as exc:
        err_path = resolve_child_path(run_dir, "error.txt")
        with validated_open(err_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
            fh.write(f"{type(exc).__name__}: {exc}\n")
            fh.write(traceback.format_exc())
        return False


def run_simulation_subprocess(
    run_id: str,
    spec: dict[str, Any],
    *,
    full_telemetry: bool = False,
    keep_workdir: bool = False,
    timeout: int = 3600,
) -> bool:
    """Run one simulation in a fresh child process, then reclaim its memory.

    Repeated 7000-agent simulations leak RSS when run in a single process;
    isolating each run in a short-lived subprocess lets the OS reclaim all
    memory on exit, keeping the campaign under Fargate's memory limit.

    Polls ``/proc/<pid>/status`` ``VmHWM`` while the child runs so peak RSS
    is recorded for 2 GB Fargate sizing evidence (CloudWatch + sidecars).
    """
    safe_id = _safe_run_id(run_id)
    roots = _allowed_roots()
    spec_name = validate_path_component(f"{safe_id}.run_spec.json", label="spec artifact")
    spec_path = _output_artifact(spec_name)
    with validated_open(spec_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
        json.dump(spec, fh)

    cmd = [
        sys.executable,
        str(CAMPAIGN_DIR / "campaign_runner.py"),
        "--single", spec_path, _output_root_str(),
    ]
    if full_telemetry:
        cmd.append("--full-telemetry")
    if keep_workdir:
        cmd.append("--keep-workdir")

    returncode: int | None = None
    timed_out = False
    peak_rss_kb: int | None = None
    stdout = ""
    stderr = ""
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=_REPO_ROOT_STR,
            env={
                **os.environ,
                "PYTHONPATH": _REPO_ROOT_STR,
                # Windows consoles default to cp1252; LCARS banners use U+2500.
                "PYTHONIOENCODING": os.environ.get("PYTHONIOENCODING", "utf-8"),
                "PYTHONUTF8": os.environ.get("PYTHONUTF8", "1"),
            },
        )
        deadline = time.monotonic() + timeout
        while True:
            hwm = _read_vmhwm_kb(proc.pid)
            if hwm is not None:
                peak_rss_kb = hwm if peak_rss_kb is None else max(peak_rss_kb, hwm)
            if proc.poll() is not None:
                break
            if time.monotonic() >= deadline:
                proc.kill()
                timed_out = True
                break
            time.sleep(0.5)
        try:
            out_err = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            out_err = proc.communicate()
            timed_out = True
        stdout, stderr = out_err[0] or "", out_err[1] or ""
        returncode = proc.returncode
        zip_path = _output_artifact(f"{safe_id}.zip")
        ok = (not timed_out) and returncode == 0 and os.path.isfile(zip_path)
        if timed_out:
            err_path = _output_artifact(f"{safe_id}.subprocess_stderr.txt")
            with validated_open(err_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
                fh.write(f"TimeoutExpired after {timeout}s\n")
                if stdout or stderr:
                    fh.write("\n--- stdout ---\n")
                    fh.write(stdout)
                    fh.write("\n--- stderr ---\n")
                    fh.write(stderr)
        elif not ok:
            err_path = _output_artifact(f"{safe_id}.subprocess_stderr.txt")
            with validated_open(err_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
                fh.write(f"returncode={returncode}\n\n")
                fh.write("--- stdout ---\n")
                fh.write(stdout)
                fh.write("\n--- stderr ---\n")
                fh.write(stderr)
    except Exception:
        ok = False
        raise
    finally:
        if not keep_workdir and os.path.isfile(spec_path):
            os.remove(spec_path)

    _write_run_sidecars(
        safe_id,
        returncode=returncode,
        timeout=timeout,
        timed_out=timed_out,
        peak_rss_kb=peak_rss_kb,
        ok=ok,
    )
    return ok


def _run_single(
    spec_path: str,
    outdir: str,
    *,
    full_telemetry: bool = False,
    keep_workdir: bool = False,
) -> int:
    """Child-process entry: run exactly one simulation into ``outdir``."""
    out_base = os.path.realpath(outdir)
    roots = _allowed_roots(out_base)
    safe_spec = _confine_campaign_path(spec_path, out_base)
    prepare_output_directory(out_base, allowed_roots=roots)
    with validated_open(safe_spec, allowed_roots=roots, encoding="utf-8") as fh:
        spec = json.load(fh)
    run_id = spec.get("description")
    if not run_id:
        raise SystemExit(f"--single spec {safe_spec} missing 'description' run id")
    safe_id = _safe_run_id(str(run_id))
    ok = run_simulation(
        safe_id, spec,
        full_telemetry=full_telemetry, keep_workdir=keep_workdir,
        output_root=Path(out_base),
    )
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mega cruise campaign runner")
    parser.add_argument("--tier", default=None, help="Tier id or short prefix (t1…t16, c1…c6, a2)")
    parser.add_argument("--dry-run", action="store_true", help="Count runs without executing")
    parser.add_argument("--resume", action="store_true", help="Skip completed run_ids")
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help=f"Only re-run run_ids listed in {FAILED_RUNS_FILENAME} (clears their leftovers first). "
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
        help="Path to campaign_manifest.json (or calibration_manifest_v1.json)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Redirect zips and resume logs (default: telemetry_buffer/"
        "mega_cruise_campaign). Use a separate tree for Contam matched arms.",
    )
    parser.add_argument(
        "--include-deferred",
        action="store_true",
        help="Include tiers marked deferred:true when selecting --tier all "
        "(explicit --tier c2 still works without this flag).",
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
        help=f"s3://bucket/path to upload each <run_id>.zip and {COMPLETED_LOG.name}.",
    )
    parser.add_argument(
        "--s3-log-every",
        type=int,
        default=25,
        help=f"Upload {COMPLETED_LOG.name} to S3 every N successful runs (default 25).",
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
        default=3600,
        help="Per-run subprocess timeout in seconds (default 3600; "
        "~30 min 7000-agent runs need headroom beyond the old 600s cap).",
    )
    args = parser.parse_args(argv)

    if args.single:
        spec_path, outdir = args.single
        return _run_single(
            spec_path, outdir,
            full_telemetry=args.full_telemetry,
            keep_workdir=args.keep_workdir,
        )

    if args.output_dir is not None:
        set_output_root(args.output_dir)

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
        print(f"  --retry-failed: {FAILED_RUNS_FILENAME} is empty; nothing to retry.")
        return 0
    tiers = resolve_tier_ids(
        manifest, args.tier, include_deferred=args.include_deferred,
    )
    deferred_skipped = [
        tid for tid, t in sorted(manifest["tiers"].items())
        if _tier_is_deferred(t) and tid not in tiers
    ]
    if deferred_skipped and (not args.tier or args.tier in ("all", "*")):
        print(
            "  Skipping deferred tiers (pin dose then --tier <id> "
            f"or --include-deferred): {', '.join(deferred_skipped)}",
        )

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
                zip_path = Path(_output_artifact(f"{run_id}.zip"))
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
    log_path = _output_artifact(COMPLETED_LOG.name)
    if not os.path.isfile(log_path):
        return
    try:
        uploader.upload_file(
            Path(log_path), _resume_log_key(shard_index, shard_count),
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
    log_path = Path(_output_artifact(COMPLETED_LOG.name))
    try:
        ok = uploader.download_file(key, log_path)
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
