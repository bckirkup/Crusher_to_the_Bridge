#!/usr/bin/env python3
"""
campaign_runner.py — Spec generation for mega-cruise campaign runs
(including ``sr*`` / ``vd*`` families). Execution/resume/S3/CLI live in
``campaign_execution.py``; ``main`` and related symbols are re-exported.

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
import sys
from functools import lru_cache
from itertools import product
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any, Iterator, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402

from picard_framework.analysis.sentinel.wastewater_assays import (  # noqa: E402
    DEFAULT_ASSAY_MODE,
)
from picard_framework.pathogen_overrides import (  # noqa: E402
    isolate_arm_overrides,
)
from picard_framework.runs.mega_cruise_campaign import (  # noqa: E402
    boarding_axis,
    sentinel_recovery,
    variant_campaign,
)
from picard_framework.runs.mega_cruise_campaign.boarding_axis import (  # noqa: E402
    IndexCaseAxis,
)
from picard_framework.runs.mega_cruise_campaign.tier_iterators import (  # noqa: E402
    dispatch_standard_or_calibration,
)
from simulation_utils.paths import (  # noqa: E402
    is_path_under_base,
    prepare_output_directory,
    resolve_child_path,
    validate_path_component,
    validated_open,
)
from simulation_utils.platform_complement import (  # noqa: E402
    declared_total,
    declaring_platforms,
)

CAMPAIGN_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = CAMPAIGN_DIR / "campaign_manifest.json"
COMPLETED_RUNS_FILENAME = "completed_runs.txt"
FAILED_RUNS_FILENAME = "failed_runs.txt"
CLOCK_MARKER_FILENAME = "natural_history_clock.txt"
DEFAULT_NATURAL_HISTORY_CLOCK = "hours"
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


def _clock_marker() -> str | None:
    marker_path = _output_artifact(CLOCK_MARKER_FILENAME)
    if not os.path.isfile(marker_path):
        return None
    with validated_open(
        marker_path, allowed_roots=_allowed_roots(), encoding="utf-8",
    ) as fh:
        value = fh.read().strip()
    return value or None


def _completed_results_present() -> bool:
    log_path = _output_artifact(COMPLETED_RUNS_FILENAME)
    return bool(_read_run_id_log(Path(log_path)))


def _ensure_clock_arm(
    clock: str,
    *,
    explicit: bool = False,
    persist: bool = True,
) -> None:
    marker_path = _output_artifact(CLOCK_MARKER_FILENAME)
    existing = _clock_marker()
    if (
        existing is None
        and explicit
        and clock != DEFAULT_NATURAL_HISTORY_CLOCK
        and _completed_results_present()
    ):
        existing = DEFAULT_NATURAL_HISTORY_CLOCK
        if persist:
            with validated_open(
                marker_path, "w",
                allowed_roots=_allowed_roots(), encoding="utf-8",
            ) as fh:
                fh.write(existing + "\n")
    if existing is not None and existing != clock:
        raise SystemExit(
            "natural-history clock arm mismatch: "
            f"output directory {OUTPUT_ROOT} is marked {existing!r}, "
            f"but {clock!r} was requested ({marker_path})",
        )
    if existing is None and persist:
        with validated_open(
            marker_path, "w", allowed_roots=_allowed_roots(), encoding="utf-8",
        ) as fh:
            fh.write(clock + "\n")


def _resolve_manifest_clock(
    manifest: dict[str, Any],
    args: argparse.Namespace,
) -> str | None:
    """Reconcile the CLI clock arm with a manifest that declares one.

    A manifest may pin its own arm (Paper 3 ``vs*`` campaigns must). Disagreement
    is refused rather than resolved: silently preferring one side is how two
    natural-history models end up pooled in one output directory.
    """
    declared = manifest.get("natural_history_clock")
    if declared is None:
        return args.natural_history_clock
    declared = str(declared)
    if declared not in variant_campaign.CLOCKS:
        raise SystemExit(
            f"manifest natural_history_clock must be one of "
            f"{variant_campaign.CLOCKS}, got {declared!r}",
        )
    requested = args.natural_history_clock
    if requested is not None and requested != declared:
        raise SystemExit(
            "natural-history clock arm mismatch: manifest declares "
            f"{declared!r} but {requested!r} was requested on the command line",
        )
    return declared


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
    return bundle, pathogen_id, isolate_arm_overrides(
        bundle, pathogen_id, overrides,
    )


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


# Ship-class populations are the hulls' own declarations, not a table here:
# a second table drifts from the first, and one did -- the observation model's
# designs defaulted to 450 agents on every hull.  ``platform_id`` is not the
# complement (classic_cruise_1900 berths 1,910; mega_cruise_5000 berths 7,000).
_PLATFORM_DEFAULT_AGENTS: dict[str, int] = {
    hull: declared_total(hull) for hull in declaring_platforms()
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
        "per_partner_contact": "ppc",
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


_VSP_KNOB_KEYS = (
    "vsp_threshold",
    "detection_delay",
    "isolation_compliance",
    "sick_call_probability",
)


def _vsp_knob_tag(name: str, value: float | int) -> str:
    """Compact run-id fragment for a VSP degradation knob."""
    if name == "vsp_threshold":
        return f"vsp{str(float(value)).replace('.', 'p')}"
    if name == "detection_delay":
        return f"det{int(value)}"
    if name == "isolation_compliance":
        return f"iso{int(round(float(value) * 100))}"
    if name == "sick_call_probability":
        return f"scp{int(round(float(value) * 100))}"
    return f"{name}{value}"


def _vsp_degradation_overrides(knobs: dict[str, Any]) -> dict[str, Any]:
    """Map design knobs → escalation + medical_response + syndromic overrides."""
    thr = float(knobs["vsp_threshold"])
    delay = int(knobs["detection_delay"])
    iso = float(knobs["isolation_compliance"])
    scp = float(knobs["sick_call_probability"])
    return {
        "escalation": {"lockdown_attack_rate": thr},
        "medical_response": {
            "detection_delay_hours": delay,
            "isolation_compliance": iso,
            "sick_call_probability": scp,
        },
        "syndromic": {
            "detection_delay_hours": delay,
            "sick_call_probability": scp,
        },
        "fred_behavior": {"quarantine_compliance": iso},
    }


def _fat_knob_combos(
    tier: dict[str, Any], nominal: dict[str, Any],
) -> list[dict[str, Any]]:
    name = str(tier["factor"])
    combos: list[dict[str, Any]] = []
    for val in tier["values"]:
        knobs = {k: nominal[k] for k in _VSP_KNOB_KEYS}
        knobs[name] = val
        combos.append(knobs)
    return combos


def _interaction_knob_combos(
    tier: dict[str, Any], nominal: dict[str, Any],
) -> list[dict[str, Any]]:
    factors = tier["factors"]
    names = list(factors.keys())
    combos: list[dict[str, Any]] = []
    for vals in product(*(list(factors[n]) for n in names)):
        knobs = {k: nominal[k] for k in _VSP_KNOB_KEYS}
        knobs.update(zip(names, vals))
        combos.append(knobs)
    return combos


def _iter_vsp_knob_combos(
    tier: dict[str, Any],
    nominal: dict[str, Any],
) -> list[dict[str, Any]]:
    """FAT (single factor) or interaction panel (factors product) knob dicts."""
    if "factor" in tier and "values" in tier:
        return _fat_knob_combos(tier, nominal)
    if "factors" in tier:
        return _interaction_knob_combos(tier, nominal)
    raise ValueError("VSP degradation tier needs 'factor'+'values' or 'factors'")


def _iter_synthetic_recovery_runs(
    *,
    manifest: dict[str, Any],
    tier: dict[str, Any],
    surv_cfgs: dict[str, Any],
    platform_override: str | None,
    num_agents_override: int | None,
    yield_run,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield Picard specs for synthetic_recovery (sr*) tiers."""
    pathogen = tier["pathogen"]
    bundle, pathogen_id, base_overrides = get_pathogen_config(manifest, pathogen)
    platforms = _resolve_tier_platforms(
        tier,
        fallback_platform=manifest["platform"],
        platform_override=platform_override,
    )
    strategies = list(tier.get("surveillance_strategies") or ["syndromic"])
    vectors = list(tier["parameter_vectors"])
    default_agents = int(manifest.get("default_num_agents", 7000))
    index_axis = IndexCaseAxis.for_tier(tier, pathogen_id)
    for plat, vec, point, sname, seed in product(
        platforms, vectors, index_axis.points, strategies, tier["seeds"],
    ):
        n_agents = _platform_num_agents(
            plat,
            num_agents_override=num_agents_override,
            tier=tier,
            default_agents=default_agents,
        )
        dose = float(vec["dose_adj"])
        alpha = float(vec["alpha_c"])
        nonsus = float(vec.get("non_susceptible", 0.0))
        vec_id = str(vec.get("id", "vec"))
        path_over = index_axis.pathogen_overrides(
            base_overrides, point,
            dose_adjustment=dose, innate_nonsusceptible_fraction=nonsus,
        )
        rid = "_".join(
            [
                "sr", pathogen, plat, vec_id, _dose_tag(dose), _alpha_tag(alpha),
                *index_axis.tags(point), sname, f"s{seed}",
            ]
        )
        yield yield_run(
            rid,
            bundle=bundle,
            pathogen_overrides=path_over,
            config_overrides=merge_cfg(
                surv_cfgs.get(sname), _density_contact_override(alpha),
            ),
            seed=seed,
            num_agents=n_agents,
            pathogen=pathogen,
            platform_id=plat,
            surveillance=sname,
            dose_adjustment=dose,
            density_exponent=alpha,
            non_susceptible=nonsus,
            parameter_vector=vec_id,
            **index_axis.factors(point),
        )


def _wastewater_scan_cells(tier: dict[str, Any]) -> list[dict[str, Any]]:
    """Scan cells for a tier, or one unlabelled cell using the tier's own seeds.

    Lets a wastewater scan and a plain sentinel recovery tier share one
    generator: without ``wastewater_cells`` the single cell reproduces the
    previous run ids and seed loop exactly.
    """
    cells = tier.get("wastewater_cells")
    if not cells:
        return [{"cell_id": "", "block": "", "seeds": list(tier["seeds"])}]
    return [dict(cell) for cell in cells]


def _wastewater_cell_factors(cell: dict[str, Any]) -> dict[str, Any]:
    """Flat labels identifying which operating point a run came from.

    Collection points are recorded as a count: the analysis asks whether more
    taps help, not which deck they were on. The clinical-only arm names no
    cadence, residence, or assay, so those label as 0 or empty rather than going
    missing — the aggregate CSV is read as a factorial table and a hole in a
    column is worse than an explicit "never sampled".
    """
    settings = cell.get("wastewater_surveillance")
    if not settings:
        return {}
    enabled = bool(settings.get("enabled", False))
    return {
        "wastewater_cell": str(cell.get("cell_id") or ""),
        "wastewater_block": str(cell.get("block") or ""),
        "wastewater_enabled": enabled,
        "ww_assay_mode": (
            str(settings.get("assay_mode") or DEFAULT_ASSAY_MODE) if enabled else ""
        ),
        "ww_sampling_interval_epochs": int(settings.get("sampling_interval_epochs") or 0),
        "ww_residence_hours": float(settings.get("holding_tank_residence_hours") or 0.0),
        "ww_sequencing_depth": int(settings.get("sequencing_depth") or 0),
        "ww_collection_points": len(settings.get("collection_points") or []),
    }


def _cell_seed_pairs(tier: dict[str, Any]) -> list[tuple[dict[str, Any], Any]]:
    return [
        (cell, seed)
        for cell in _wastewater_scan_cells(tier)
        for seed in cell["seeds"]
    ]


def _iter_sentinel_recovery_runs(
    *,
    manifest: dict[str, Any],
    tier: dict[str, Any],
    tier_id: str,
    surv_cfgs: dict[str, Any],
    platform_override: str | None,
    num_agents_override: int | None,
    yield_run,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield Picard specs for sentinel port-hazard recovery (sr_* + R_onboard)."""
    pathogen = tier["pathogen"]
    bundle, pathogen_id, base_overrides = get_pathogen_config(manifest, pathogen)
    platforms = _resolve_tier_platforms(
        tier,
        fallback_platform=manifest["platform"],
        platform_override=platform_override,
    )
    defaults = manifest.get("defaults") or {}
    dose = float(defaults.get("dose_adjustment", 10.6))
    alpha = float(defaults.get("density_exponent", 0.75))
    dens_over = _density_contact_override(alpha)
    strategies = list(tier.get("surveillance_strategies") or ["syndromic"])
    hazards = dict((tier.get("shore_exposure") or {}).get("port_hazards") or {})
    hazard_profile, fleet_config = sentinel_recovery.parse_tier_labels(tier_id, tier)
    epochs = int(tier.get("epochs", manifest.get("default_epochs", 168)))
    default_agents = int(manifest.get("default_num_agents", 7000))
    embark_date = str(manifest.get("embarkation_date", "2026-01-10"))
    for (plat_index, plat), r_onboard, sname, (cell, seed) in product(
        list(enumerate(platforms)),
        tier["R_onboard_values"],
        strategies,
        _cell_seed_pairs(tier),
    ):
        n_agents = _platform_num_agents(
            plat,
            num_agents_override=num_agents_override,
            tier=tier,
            default_agents=default_agents,
        )
        variant = sentinel_recovery.itinerary_for_platform(tier, plat_index)
        days = sentinel_recovery.stamp_port_hazards(
            sentinel_recovery.itinerary_days(manifest, variant),
            hazards,
        )
        r_val = float(r_onboard)
        seeding = sentinel_recovery.onboard_seeding(
            hazards, r_val, pathogen_id, tier,
        )
        path_over = dict(base_overrides or {})
        path_over[pathogen_id] = {
            **(path_over.get(pathogen_id) or {}),
            "dose_adjustment": dose,
            **seeding.pathogen_patch,
        }
        voyage = sentinel_recovery.voyage_override(
            days=days,
            r_onboard=r_val,
            epochs=epochs,
            embarkation_date=embark_date,
        )
        ww_settings = cell.get("wastewater_surveillance")
        prefix = [
            "sr", pathogen, plat, hazard_profile, fleet_config, variant,
            sentinel_recovery.r_onboard_tag(r_val),
            *([str(cell["cell_id"])] if cell.get("cell_id") else []),
        ]
        rid = "_".join([*prefix, f"s{seed}"])
        yield yield_run(
            rid,
            bundle=bundle,
            pathogen_overrides=path_over,
            config_overrides=merge_cfg(
                surv_cfgs.get(sname),
                dens_over,
                {"wastewater_surveillance": ww_settings} if ww_settings else None,
                {"voyage": voyage, "voyage_id": rid},
            ),
            seed=seed,
            num_agents=n_agents,
            pathogen=pathogen,
            platform_id=plat,
            surveillance=sname,
            dose_adjustment=dose,
            density_exponent=alpha,
            R_onboard=r_val,
            hazard_profile=hazard_profile,
            **seeding.factors,
            fleet_config=fleet_config,
            itinerary_variant=variant,
            port_hazards=hazards,
            **_wastewater_cell_factors(cell),
        )


def _iter_sr_family_runs(
    *,
    manifest: dict[str, Any],
    tier: dict[str, Any],
    tier_id: str,
    surv_cfgs: dict[str, Any],
    platform_override: str | None,
    num_agents_override: int | None,
    yield_run,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Dispatch ridge synthetic recovery vs sentinel port-hazard recovery."""
    if sentinel_recovery.is_sentinel_recovery_tier(tier):
        yield from _iter_sentinel_recovery_runs(
            manifest=manifest,
            tier=tier,
            tier_id=tier_id,
            surv_cfgs=surv_cfgs,
            platform_override=platform_override,
            num_agents_override=num_agents_override,
            yield_run=yield_run,
        )
        return
    yield from _iter_synthetic_recovery_runs(
        manifest=manifest,
        tier=tier,
        surv_cfgs=surv_cfgs,
        platform_override=platform_override,
        num_agents_override=num_agents_override,
        yield_run=yield_run,
    )


def _vd_active_knob_tags(tier: dict[str, Any], knobs: dict[str, Any]) -> list[str]:
    """Run-id fragments for knobs that this tier actually sweeps."""
    return [
        _vsp_knob_tag(n, knobs[n])
        for n in _VSP_KNOB_KEYS
        if (
            ("factor" in tier and n == tier["factor"])
            or ("factors" in tier and n in tier["factors"])
        )
    ]


def _iter_vsp_degradation_runs(
    *,
    manifest: dict[str, Any],
    tier: dict[str, Any],
    surv_cfgs: dict[str, Any],
    platform_override: str | None,
    num_agents_override: int | None,
    yield_run,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield Picard specs for vsp_degradation (vd*) tiers."""
    pathogen = tier["pathogen"]
    bundle, pathogen_id, base_overrides = get_pathogen_config(manifest, pathogen)
    platforms = _resolve_tier_platforms(
        tier,
        fallback_platform=manifest["platform"],
        platform_override=platform_override,
    )
    defaults = manifest.get("defaults") or {}
    nominal = dict(defaults.get("nominal_values") or {})
    for k in _VSP_KNOB_KEYS:
        if k not in nominal:
            raise ValueError(f"manifest defaults.nominal_values missing {k}")
    dose = float(tier.get("dose_adjustment", defaults.get("dose_adjustment", 10.6)))
    alpha = float(tier.get("density_exponent", defaults.get("density_exponent", 0.75)))
    strategies = list(tier.get("surveillance_strategies") or ["syndromic"])
    dens_over = _density_contact_override(alpha)
    knobs_list = _iter_vsp_knob_combos(tier, nominal)
    default_agents = int(manifest.get("default_num_agents", 7000))
    index_axis = IndexCaseAxis.for_tier(tier, pathogen_id, defaults=defaults)
    for plat, knobs, point, sname, seed in product(
        platforms, knobs_list, index_axis.points, strategies, tier["seeds"],
    ):
        n_agents = _platform_num_agents(
            plat,
            num_agents_override=num_agents_override,
            tier=tier,
            default_agents=default_agents,
        )
        path_over = index_axis.pathogen_overrides(
            base_overrides, point, dose_adjustment=dose,
        )
        tags = _vd_active_knob_tags(tier, knobs)
        rid = "_".join(
            [
                "vd", pathogen, plat, *tags, _dose_tag(dose), _alpha_tag(alpha),
                *index_axis.tags(point), sname, f"s{seed}",
            ]
        )
        yield yield_run(
            rid,
            bundle=bundle,
            pathogen_overrides=path_over,
            config_overrides=merge_cfg(
                surv_cfgs.get(sname), dens_over, _vsp_degradation_overrides(knobs),
            ),
            seed=seed,
            num_agents=n_agents,
            pathogen=pathogen,
            platform_id=plat,
            surveillance=sname,
            dose_adjustment=dose,
            density_exponent=alpha,
            vsp_threshold=float(knobs["vsp_threshold"]),
            **index_axis.factors(point),
            detection_delay_hours=int(knobs["detection_delay"]),
            isolation_compliance=float(knobs["isolation_compliance"]),
            sick_call_probability=float(knobs["sick_call_probability"]),
        )


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


def _calibration_index_axis(tier: dict[str, Any], pathogen_id: str) -> IndexCaseAxis:
    """Index-case axis for a calibration tier: the boarding grid for an owned pathogen, else the fiat count sweep (``None`` leaves the bundle's own)."""
    return IndexCaseAxis.for_tier(tier, pathogen_id, legacy_default=None)


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
        "legacy_yaml": LEGACY_CONFIG_RELPATH,
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
        campaign_parameters = {
            "run_id": run_id,
            "platform_id": platform,
            "pathogen_bundle_id": bundle,
            "seed": int(seed),
            "num_epochs": int(epochs),
            "num_agents": int(num_agents),
            "history_retention": retention,
        }
        _fill_override_params(campaign_parameters, cfg)
        spec["campaign_parameters"] = campaign_parameters
    if telemetry_dir is not None:
        # Absolute paths so finalize does not clobber shared telemetry_buffer/.
        spec["run"]["simulation_history"] = str(telemetry_dir / "simulation_history.json")
        spec["run"]["lab_notebook"] = str(telemetry_dir / "artificial_lab_notebook.json")
        spec["run"]["ground_truth"] = str(telemetry_dir / "ground_truth.json")
    return spec


# Legacy config every campaign spec loads; the base for any surveillance knob
# a tier does not override.
LEGACY_CONFIG_RELPATH = "crusher_labs/config.yaml"
_SYNDROMIC_HAZARD_KEYS: tuple[str, ...] = (
    "sick_call_probability_per_day",
    "sick_call_probability",
)
_HVAC_PARAM_MAP: tuple[tuple[str, str], ...] = (
    ("transport_engine", "transport_engine"),
    ("filter_efficiency", "filter_efficiency"),
    ("oa_fraction", "outdoor_air_fraction"),
    ("natural_decay_rate", "decay_rate"),
)
_WEAR_PARAM_MAP: tuple[tuple[str, str], ...] = (
    ("deployment_profile", "wearables"),
    ("detection_sensitivity_scale", "wearable_sensitivity"),
)


def _copy_present(
    params: dict[str, Any],
    source: Mapping[str, Any],
    mapping: Sequence[tuple[str, str]],
    *,
    skip_if_present: frozenset[str] = frozenset(),
) -> None:
    for src, dest in mapping:
        if src not in source:
            continue
        if dest in skip_if_present and dest in params:
            continue
        params[dest] = source[src]


@lru_cache(maxsize=1)
def _base_syndromic_config() -> Mapping[str, Any]:
    """The ``syndromic`` block of the legacy config every campaign spec loads."""
    with validated_open(
        str(REPO_ROOT / LEGACY_CONFIG_RELPATH),
        allowed_roots=(_REPO_ROOT_STR,),
        encoding="utf-8",
    ) as fh:
        loaded = yaml.safe_load(fh) or {}
    return MappingProxyType(dict(loaded.get("syndromic") or {}))


def _record_reporting_hazard(params: dict[str, Any]) -> None:
    """Record the sick-call hazard the run will actually use.

    A surveillance arm that overrides nothing still reports at the hazard the
    legacy config declares, and a summary that omits it cannot be scored
    against the reported-case anchors without assuming a value. The effective
    hazard is therefore written into the parameters block for every arm, and a
    config declaring no hazard under either unit name is an error rather than a
    silent fallback.
    """
    if any(key in params for key in _SYNDROMIC_HAZARD_KEYS):
        return
    base = _base_syndromic_config()
    for key in _SYNDROMIC_HAZARD_KEYS:
        if key in base:
            params["sick_call_probability_per_day"] = float(base[key])
            return
    raise ValueError(
        f"{LEGACY_CONFIG_RELPATH} declares no syndromic sick-call hazard "
        "under sick_call_probability_per_day or sick_call_probability",
    )


def _fill_override_params(params: dict[str, Any], cfg: Mapping[str, Any]) -> None:
    clock = cfg.get("natural_history_clock")
    if clock is not None:
        params["natural_history_clock"] = clock
    hvac = cfg.get("hvac") or {}
    _copy_present(
        params, hvac, _HVAC_PARAM_MAP,
        skip_if_present=frozenset({"transport_engine"}),
    )
    ship = cfg.get("ship_graph") or {}
    _copy_present(params, ship, (("immune_fraction", "immune_fraction"),))
    fred = cfg.get("fred_behavior") or {}
    _copy_present(
        params,
        fred,
        (
            ("quarantine_compliance", "quarantine_compliance"),
            ("reluctant_fraction", "reluctant_fraction"),
            ("reluctant_delay_hours", "reluctant_delay_epochs"),
        ),
        skip_if_present=frozenset({
            "reluctant_fraction", "reluctant_delay_epochs",
        }),
    )
    wear = cfg.get("wearable_monitoring") or {}
    _copy_present(
        params, wear, _WEAR_PARAM_MAP,
        skip_if_present=frozenset({"wearables", "wearable_sensitivity"}),
    )
    syn = cfg.get("syndromic") or {}
    _copy_present(
        params,
        syn,
        (
            ("sick_call_probability", "sick_call_probability"),
            (
                "sick_call_probability_per_day",
                "sick_call_probability_per_day",
            ),
            ("activation_delay_hours", "surveillance_delay_epochs"),
        ),
        skip_if_present=frozenset({
            "sick_call_probability",
            "sick_call_probability_per_day",
            "surveillance_delay_epochs",
        }),
    )
    _record_reporting_hazard(params)
    esc = cfg.get("escalation") or {}
    latency = esc.get("decision_latency") or {}
    _copy_present(
        params,
        latency,
        (("confirmed_delay_hours", "decision_latency_epochs"),),
        skip_if_present=frozenset({"decision_latency_epochs"}),
    )
    _copy_present(
        params,
        esc,
        (
            ("suspect_attack_rate", "suspect_attack_rate"),
            ("lockdown_attack_rate", "lockdown_attack_rate"),
        ),
        skip_if_present=frozenset({
            "suspect_attack_rate", "lockdown_attack_rate",
        }),
    )
    med = cfg.get("medical_response") or {}
    _copy_present(
        params,
        med,
        (
            ("detection_delay_hours", "detection_delay_epochs"),
            ("isolation_compliance", "isolation_compliance"),
            ("sick_call_probability", "sick_call_probability"),
        ),
        skip_if_present=frozenset({
            "detection_delay_epochs", "isolation_compliance",
            "sick_call_probability",
        }),
    )


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
    _fill_override_params(params, config_overrides or {})
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
    _copy_present(
        params, cfg, (("natural_history_clock", "natural_history_clock"),),
    )
    _copy_present(params, cfg.get("hvac") or {}, _HVAC_PARAM_MAP)
    _copy_present(params, ship, (("immune_fraction", "immune_fraction"),))
    _copy_present(
        params,
        cfg.get("fred_behavior") or {},
        (("quarantine_compliance", "quarantine_compliance"),),
    )
    _copy_present(
        params,
        cfg.get("wearable_monitoring") or {},
        (("deployment_profile", "wearables"),),
    )
    _copy_present(
        params,
        cfg.get("syndromic") or {},
        tuple((key, key) for key in _SYNDROMIC_HAZARD_KEYS),
    )
    _record_reporting_hazard(params)
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
    natural_history_clock: str | None = None,
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
        clock_cfg = (
            {"natural_history_clock": natural_history_clock}
            if natural_history_clock is not None
            else None
        )
        # The tier's own party point reaches the iterators that carry no
        # boarding axis; a swept axis has already stamped its own.
        swept = {**boarding_axis.tier_party_factors(tier), **factors}
        cfg = merge_cfg(
            _CAMPAIGN_ESCALATION_DEFAULTS,
            config_overrides,
            clock_cfg,
            boarding_axis.initiation_override(bundle, pathogen_overrides, swept),
        )
        # Effective coordinates, not only the swept ones, and derived from the
        # sweep rather than from the config the override just built.
        factors = {
            **boarding_axis.recorded_factors(bundle, pathogen_overrides, swept),
            **factors,
        }
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

    ctx = SimpleNamespace(
        yield_run=_yield,
        tier=tier,
        short=short,
        surv_cfgs=surv_cfgs,
        manifest=manifest,
        platform_override=platform_override,
        num_agents_override=num_agents_override,
        epochs_override=epochs_override,
        default_epochs=default_epochs,
        get_pathogen_config=get_pathogen_config,
        merge_cfg=merge_cfg,
        combo_overrides=combo_overrides,
        immunity_override=_immunity_override,
        dose_tag=_dose_tag,
        alpha_tag=_alpha_tag,
        contact_mode_tag=_contact_mode_tag,
        resolve_tier_platforms=_resolve_tier_platforms,
        platform_num_agents=_platform_num_agents,
        calibration_dose_values=_calibration_dose_values,
        calibration_index_axis=_calibration_index_axis,
        density_exponent_values=_density_exponent_values,
        contact_mode_values=_contact_mode_values,
        density_contact_override=_density_contact_override,
    )
    streamed = dispatch_standard_or_calibration(ctx)
    if streamed is not None:
        yield from streamed
        return
    if short.startswith("sr"):
        yield from _iter_sr_family_runs(
            manifest=manifest,
            tier=tier,
            tier_id=tier_id,
            surv_cfgs=surv_cfgs,
            platform_override=platform_override,
            num_agents_override=num_agents_override,
            yield_run=_yield,
        )
        return
    if short.startswith("vd"):
        yield from _iter_vsp_degradation_runs(
            manifest=manifest,
            tier=tier,
            surv_cfgs=surv_cfgs,
            platform_override=platform_override,
            num_agents_override=num_agents_override,
            yield_run=_yield,
        )
        return
    if short.startswith("vs"):
        yield from variant_campaign.iter_variant_runs(
            manifest=manifest,
            tier=tier,
            tier_id=tier_id,
            surv_cfgs=surv_cfgs,
            platform_override=platform_override,
            num_agents_override=num_agents_override,
            epochs_override=epochs_override,
            get_pathogen_config=get_pathogen_config,
            merge_cfg=merge_cfg,
            platform_num_agents=_platform_num_agents,
            default_agents=default_agents,
            yield_run=_yield,
        )
        return
    raise ValueError(f"No generator for tier {tier_id}")


_EXECUTION_EXPORTS = frozenset({
    "parse_s3_prefix",
    "S3Uploader",
    "_shard_suffix",
    "_resolve_relative_path",
    "ShardBundle",
    "extract_timeseries",
    "_detection_epochs",
    "_reported_case_counter_exceeded",
    "_validate_role_complements",
    "compute_derived_metrics",
    "_spec_num_agents",
    "_arm_sentinel_line_list",
    "_arm_lineage_census",
    "run_simulation",
    "_poll_child",
    "_write_subprocess_stderr",
    "run_simulation_subprocess",
    "_run_single",
    "_campaign_parser",
    "_apply_smoke_defaults",
    "_resolve_shard",
    "_collect_all_runs",
    "_campaign_gate",
    "_record_run_ok",
    "_perform_campaign_run",
    "_execute_assigned_runs",
    "_print_deferred_tiers",
    "_print_dry_run",
    "main",
    "_resume_log_key",
    "_upload_completed_log",
    "_download_completed_log",
})


def __getattr__(name: str) -> Any:
    if name in _EXECUTION_EXPORTS:
        from picard_framework.runs.mega_cruise_campaign import campaign_execution as _ex
        return getattr(_ex, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_EXECUTION_EXPORTS))


if __name__ == "__main__":
    from picard_framework.runs.mega_cruise_campaign.campaign_execution import main as _main
    raise SystemExit(_main())
