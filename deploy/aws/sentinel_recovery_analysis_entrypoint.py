#!/usr/bin/env python3
"""AWS Batch worker for sentinel_synthetic_recovery_v1 Stan fits.

Phases:
  fit    — one recovery cell (array child via AWS_BATCH_JOB_ARRAY_INDEX)
  score  — aggregate fits into recovery.csv / report.md

Expects a prior extract under ``--s3-analysis``::

  cells.json
  manifests/<cell_id>.json
  voyages/<run_id>/{itinerary,observations,meta}.json

Fit outputs land at ``fits/<cell_id>/``. MCMC stays On-Demand (not Spot).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from simulation_utils.paths import (  # noqa: E402
    confine_to_base,
    validate_path_component,
    validated_open,
)


def _load_boundary_helpers() -> Any:
    path = Path(__file__).with_name("boundary_analysis_entrypoint.py")
    spec = importlib.util.spec_from_file_location("boundary_analysis_entrypoint", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_boundary = _load_boundary_helpers()
_parse_s3 = _boundary._parse_s3
_require_s3_uri = _boundary._require_s3_uri
_s3_client = _boundary._s3_client
_s3_download_prefix = _boundary._s3_download_prefix


def _read_json(path: str) -> Any:
    with validated_open(path, allowed_roots=(os.getcwd(),), encoding="utf-8") as fh:
        return json.load(fh)


def _download_object(bucket: str, key: str, dest: str) -> None:
    parent = os.path.dirname(dest)
    if parent:
        os.makedirs(parent, mode=0o700, exist_ok=True)
    print(f"+ s3://{bucket}/{key} -> {dest}", flush=True)
    _s3_client().download_file(bucket, key, dest)


def _upload_file(local: str, bucket: str, key: str) -> None:
    print(f"+ {local} -> s3://{bucket}/{key}", flush=True)
    _s3_client().upload_file(local, bucket, key)


def _analysis_prefix(s3_analysis: str) -> tuple[str, str]:
    bucket, prefix = _parse_s3(s3_analysis)
    prefix = prefix.rstrip("/")
    base = f"{prefix}/" if prefix else ""
    return bucket, base


def _load_sorted_cells(cells_path: str) -> list[str]:
    payload = _read_json(cells_path)
    if not isinstance(payload, dict) or not payload:
        raise SystemExit("cells.json missing or empty")
    return sorted(str(cid) for cid in payload)


def _resolve_cell_id(
    cell_ids: list[str],
    *,
    cell_id: str | None,
    cell_index: int | None,
) -> str:
    if cell_id:
        return validate_path_component(cell_id, label="cell_id")
    if cell_index is None:
        raise SystemExit("--cell-index or AWS_BATCH_JOB_ARRAY_INDEX required")
    if cell_index < 0 or cell_index >= len(cell_ids):
        raise SystemExit(
            f"array index {cell_index} out of range for {len(cell_ids)} cells",
        )
    return validate_path_component(cell_ids[cell_index], label="cell_id")


def _voyage_run_id(rel: str) -> str:
    # Manifests may have been written on Windows (``..\voyages\...``).
    normalized = str(rel).replace("\\", "/")
    parts = [p for p in normalized.split("/") if p and p not in {".", ".."}]
    if len(parts) < 3 or parts[0] != "voyages":
        raise SystemExit(f"unexpected manifest path {rel!r}")
    return validate_path_component(parts[1], label="run_id")


def _posix_relpath(rel: str) -> str:
    """Normalize a manifest-relative path to POSIX form for Linux workers."""
    return str(rel).replace("\\", "/")


def _posix_voyage_fields(entry: dict[str, Any]) -> bool:
    changed = False
    for field in ("itinerary", "observations"):
        raw = entry.get(field)
        if not isinstance(raw, str) or not raw:
            continue
        fixed = _posix_relpath(raw)
        if fixed != raw:
            entry[field] = fixed
            changed = True
    return changed


def _rewrite_manifest_paths(manifest_path: str) -> None:
    """Ensure voyage paths in ``manifest_path`` use forward slashes."""
    payload = _read_json(manifest_path)
    voyages = payload.get("voyages") or []
    if not isinstance(voyages, list):
        return
    changed = any(
        isinstance(entry, dict) and _posix_voyage_fields(entry) for entry in voyages
    )
    if not changed:
        return
    parent = os.path.dirname(manifest_path)
    if parent:
        os.makedirs(parent, mode=0o700, exist_ok=True)
    with validated_open(
        manifest_path, "w", allowed_roots=(os.getcwd(),), encoding="utf-8",
    ) as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")


def _download_run_json(bucket: str, base: str, run_id: str) -> None:
    for name in ("itinerary.json", "observations.json"):
        dest = f"analysis/voyages/{run_id}/{name}"
        if os.path.isfile(dest):
            continue
        _download_object(bucket, f"{base}voyages/{run_id}/{name}", dest)


def _cell_run_ids(voyages: list[Any], cell_id: str) -> list[str]:
    if not voyages:
        raise SystemExit(f"manifest {cell_id} lists no voyages")
    seen: list[str] = []
    for entry in voyages:
        if not isinstance(entry, dict):
            continue
        rel = str(entry.get("itinerary") or entry.get("observations") or "")
        if not rel:
            continue
        run_id = _voyage_run_id(rel)
        if run_id not in seen:
            seen.append(run_id)
    return seen


def _existing_fit_ok(s3_analysis: str, cell_id: str) -> bool:
    """True when this cell already has an ok/smoke fit artifact on S3."""
    bucket, base = _analysis_prefix(s3_analysis)
    key = f"{base}fits/{cell_id}/fit_status.json"
    client = _s3_client()
    try:
        resp = client.get_object(Bucket=bucket, Key=key)
        payload = json.loads(resp["Body"].read())
    except client.exceptions.NoSuchKey:
        return False
    except Exception as exc:  # pragma: no cover - network
        print(f"warn: could not read s3://{bucket}/{key}: {exc}", flush=True)
        return False
    return isinstance(payload, dict) and payload.get("status") in {"ok", "smoke"}


def _download_cell_inputs(s3_analysis: str, cell_id: str) -> str:
    """Pull cells.json, one manifest, and that cell's voyage JSON only."""
    bucket, base = _analysis_prefix(s3_analysis)
    _download_object(bucket, f"{base}cells.json", "analysis/cells.json")
    manifest = f"analysis/manifests/{cell_id}.json"
    _download_object(bucket, f"{base}manifests/{cell_id}.json", manifest)
    payload = _read_json(manifest)
    voyages = payload.get("voyages") or []
    if not isinstance(voyages, list):
        raise SystemExit(f"manifest {cell_id} lists no voyages")
    for run_id in _cell_run_ids(voyages, cell_id):
        _download_run_json(bucket, base, run_id)
    return manifest


def _ww_fit_kwargs_from_meta(meta: dict[str, Any]) -> dict[str, Any]:
    from picard_framework.analysis.sentinel_recovery_postprocess import (
        _ww_fit_fields,
    )

    fields = _ww_fit_fields(meta)
    kwargs: dict[str, Any] = {"wastewater": bool(fields.get("wastewater", False))}
    if fields.get("wastewater_residence_hours") is not None:
        kwargs["wastewater_residence_hours"] = fields["wastewater_residence_hours"]
    if fields.get("wastewater_max_effective_reads") is not None:
        kwargs["wastewater_max_effective_reads"] = fields[
            "wastewater_max_effective_reads"
        ]
    return kwargs


def _fit_cell(
    manifest: str,
    fit_dir: str,
    *,
    cell_id: str,
    chains: int,
    iter_warmup: int,
    iter_sampling: int,
    seed: int,
) -> dict[str, Any]:
    from picard_framework.analysis.sentinel_recovery_priors import (
        fleet_config_from_cell_id,
        recovery_fleet_priors,
    )
    from picard_framework.analysis.stan._sampler_options import SamplerOptions
    from picard_framework.analysis.stan.fit_sentinel_fleet import fit_sentinel_fleet

    payload = _read_json(manifest)
    voyages = payload.get("voyages") or []
    meta: dict[str, Any] = {}
    if isinstance(voyages, list) and voyages:
        first = voyages[0]
        if isinstance(first, dict):
            rel = str(first.get("itinerary") or first.get("observations") or "")
            run_id = _voyage_run_id(rel) if rel else ""
            if run_id:
                meta_path = f"analysis/voyages/{run_id}/meta.json"
                if os.path.isfile(meta_path):
                    loaded = _read_json(meta_path)
                    if isinstance(loaded, dict):
                        meta = loaded

    return fit_sentinel_fleet(
        manifest,
        fit_dir,
        pathogen="norovirus",
        engine="stan",
        sampler=SamplerOptions(
            chains=chains,
            iter_warmup=iter_warmup,
            iter_sampling=iter_sampling,
            seed=seed,
            show_progress=True,
        ),
        priors=recovery_fleet_priors(
            fleet_config=fleet_config_from_cell_id(cell_id),
        ),
        **_ww_fit_kwargs_from_meta(meta),
    )


def _upload_fit_dir(fit_dir: str, s3_analysis: str, cell_id: str) -> None:
    bucket, base = _analysis_prefix(s3_analysis)
    for root, _dirs, files in os.walk(fit_dir):
        for name in files:
            local = os.path.join(root, name)
            rel = os.path.relpath(local, fit_dir).replace("\\", "/")
            for part in rel.split("/"):
                validate_path_component(part, label="fit artifact")
            _upload_file(local, bucket, f"{base}fits/{cell_id}/{rel}")


def _phase_fit(
    s3_analysis: str,
    *,
    cell_id: str | None,
    cell_index: int | None,
    chains: int,
    iter_warmup: int,
    iter_sampling: int,
    seed: int,
) -> None:
    bucket, base = _analysis_prefix(s3_analysis)
    _download_object(bucket, f"{base}cells.json", "analysis/cells.json")
    cell_ids = _load_sorted_cells("analysis/cells.json")
    chosen = _resolve_cell_id(cell_ids, cell_id=cell_id, cell_index=cell_index)
    print(f"Fitting cell={chosen} index={cell_ids.index(chosen)}", flush=True)

    if _existing_fit_ok(s3_analysis, chosen):
        print(f"skip cell={chosen} (ok fit already on S3)", flush=True)
        return

    manifest = _download_cell_inputs(s3_analysis, chosen)
    _rewrite_manifest_paths(manifest)
    fit_dir = f"analysis/fits/{chosen}"
    status = _fit_cell(
        manifest,
        fit_dir,
        cell_id=chosen,
        chains=chains,
        iter_warmup=iter_warmup,
        iter_sampling=iter_sampling,
        seed=seed,
    )
    print(f"status={status.get('status')}", flush=True)
    if status.get("status") not in {"ok", "smoke"}:
        raise SystemExit(f"fit failed: {status}")
    _upload_fit_dir(fit_dir, s3_analysis, chosen)


def _download_score_metas(s3_analysis: str) -> None:
    """Pull one ``meta.json`` per cell so scoring need not sync all voyages."""
    payload = _read_json("analysis/cells.json")
    if not isinstance(payload, dict):
        raise SystemExit("cells.json missing or empty")
    bucket, base = _analysis_prefix(s3_analysis)
    seen: set[str] = set()
    for run_ids in payload.values():
        if not isinstance(run_ids, list) or not run_ids:
            continue
        run_id = validate_path_component(str(run_ids[0]), label="run_id")
        if run_id in seen:
            continue
        seen.add(run_id)
        dest = f"analysis/voyages/{run_id}/meta.json"
        _download_object(bucket, f"{base}voyages/{run_id}/meta.json", dest)


def _phase_score(s3_analysis: str) -> None:
    from picard_framework.analysis._io import write_csv
    from picard_framework.analysis.sentinel_recovery_postprocess import (
        RECOVERY_COLUMNS,
        cells_from_out,
        score_cell,
        write_report,
    )

    _s3_download_prefix(
        s3_analysis,
        Path("analysis"),
        exclude=("voyages/*", "fits/*/draws.csv"),
    )
    _download_score_metas(s3_analysis)
    cells = cells_from_out("analysis")
    rows: list[dict[str, Any]] = []
    for cell in cells:
        status_path = os.path.join(cell["fit_dir"], "fit_status.json")
        if not os.path.isfile(status_path):
            status: dict[str, Any] = {"status": "missing"}
        else:
            status = _read_json(status_path)
        rows.extend(score_cell(cell, status))
    write_csv("analysis/recovery.csv", rows, RECOVERY_COLUMNS)
    report = write_report("analysis", rows)
    print(f"report={report}", flush=True)
    bucket, base = _analysis_prefix(s3_analysis)
    for name in ("recovery.csv", "report.md"):
        _upload_file(f"analysis/{name}", bucket, f"{base}{name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("fit", "score"), default="fit")
    parser.add_argument(
        "--s3-analysis",
        required=True,
        help="s3://bucket/campaign/sentinel_synthetic_recovery_v1/analysis/",
    )
    parser.add_argument("--cell", default=None, help="fit this cell id")
    parser.add_argument(
        "--cell-index",
        type=int,
        default=None,
        help="0-based index into sorted cells.json keys",
    )
    parser.add_argument("--chains", type=int, default=2)
    parser.add_argument("--iter-warmup", type=int, default=400)
    parser.add_argument("--iter-sampling", type=int, default=400)
    parser.add_argument("--seed", type=int, default=1701)
    args = parser.parse_args(argv)

    s3_analysis = _require_s3_uri(args.s3_analysis, label="--s3-analysis")
    env_index = os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX")
    cell_index = args.cell_index
    if cell_index is None and env_index is not None and str(env_index).strip() != "":
        cell_index = int(env_index)

    work = Path(tempfile.mkdtemp(prefix="sentinel_recovery_"))
    work_s = confine_to_base(str(work), str(work))
    os.chdir(work_s)
    os.makedirs("analysis", mode=0o700, exist_ok=True)

    if args.phase == "fit":
        _phase_fit(
            s3_analysis,
            cell_id=args.cell,
            cell_index=cell_index,
            chains=args.chains,
            iter_warmup=args.iter_warmup,
            iter_sampling=args.iter_sampling,
            seed=args.seed,
        )
    else:
        _phase_score(s3_analysis)
    print(f"phase={args.phase} done work={work_s}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
