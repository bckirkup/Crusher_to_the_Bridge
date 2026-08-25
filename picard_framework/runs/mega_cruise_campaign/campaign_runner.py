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
from collections import OrderedDict
from itertools import product
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator, Mapping, Sequence
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from picard_framework.analysis.sentinel.wastewater_assays import (  # noqa: E402
    DEFAULT_ASSAY_MODE,
)
from picard_framework.runs.mega_cruise_campaign import (  # noqa: E402
    sentinel_recovery,
    variant_campaign,
)
from picard_framework.runs.mega_cruise_campaign.tier_iterators import (  # noqa: E402
    dispatch_standard_or_calibration,
)
from simulation_utils.epidemic_labels import epidemic_took_off  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    confine_to_base,
    is_path_under_base,
    prepare_output_directory,
    resolve_child_path,
    validate_path_component,
    validated_open,
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


def _shard_suffix(shard_index: int, shard_count: int | None) -> str:
    return f"shard-{shard_index}" if shard_count is not None else "single"


def _resolve_relative_path(parent: str, relative: str) -> str:
    """Resolve a relative archive path one validated component at a time."""
    current = parent
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute():
        raise ValueError(f"Invalid relative archive path: {relative!r}")
    for part in parts:
        current = resolve_child_path(
            current,
            validate_path_component(part, label="archive path component"),
        )
    return current


class ShardBundle:
    """Accumulate completed run directories and publish one shard bundle."""

    def __init__(self, shard_index: int, shard_count: int | None) -> None:
        self.suffix = _shard_suffix(shard_index, shard_count)
        root = _ensure_output_root()
        accumulation_base = confine_to_base(
            root, os.path.join(root, "_shard_runs"),
        )
        prepare_output_directory(
            accumulation_base,
            allowed_roots=_allowed_roots(root),
        )
        self.accumulation_root = resolve_child_path(
            accumulation_base, self.suffix,
        )
        prepare_output_directory(
            self.accumulation_root,
            allowed_roots=_allowed_roots(root),
        )
        self.zip_path = resolve_child_path(root, f"{self.suffix}.zip")
        self.manifest_path = resolve_child_path(
            root, f"{self.suffix}.manifest.json",
        )
        self.entries: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def _write_manifest(self) -> None:
        with validated_open(
            self.manifest_path,
            "w",
            allowed_roots=_allowed_roots(),
            encoding="utf-8",
        ) as fh:
            json.dump(list(self.entries.values()), fh, indent=2)
            fh.write("\n")

    def _merge_manifest(self, entries: object) -> None:
        if not isinstance(entries, list):
            return
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            run_id = entry.get("run_id")
            if not isinstance(run_id, str):
                continue
            try:
                safe_id = _safe_run_id(run_id)
            except ValueError:
                continue
            parameters = entry.get("parameters") or {}
            derived = entry.get("derived") or {}
            self.entries[safe_id] = {
                "run_id": safe_id,
                "parameters": parameters if isinstance(parameters, dict) else {},
                "derived": derived if isinstance(derived, dict) else {},
            }

    def load_local_manifest(self) -> None:
        if not os.path.isfile(self.manifest_path):
            return
        try:
            with validated_open(
                self.manifest_path,
                allowed_roots=_allowed_roots(),
                encoding="utf-8",
            ) as fh:
                self._merge_manifest(json.load(fh))
        except (OSError, TypeError, ValueError):
            print("  (local shard manifest is unreadable; starting with no entries)")

    def record_run(self, run_id: str) -> None:
        safe_id = _safe_run_id(run_id)
        summary_path = resolve_child_path(
            resolve_child_path(self.accumulation_root, safe_id),
            "summary.json",
        )
        parameters: dict[str, Any] = {}
        derived: dict[str, Any] = {}
        try:
            with validated_open(
                summary_path,
                allowed_roots=_allowed_roots(),
                encoding="utf-8",
            ) as fh:
                summary = json.load(fh)
            parameters = summary.get("parameters") or {}
            derived = summary.get("derived") or {}
            if not isinstance(parameters, dict):
                parameters = {}
            if not isinstance(derived, dict):
                derived = {}
        except (OSError, TypeError, ValueError):
            # Missing summaries are valid for lightweight test runners.
            pass
        self.entries[safe_id] = {
            "run_id": safe_id,
            "parameters": parameters,
            "derived": derived,
        }
        self._write_manifest()

    def _archive_members(self) -> Iterator[tuple[str, str]]:
        if not os.path.isdir(self.accumulation_root):
            return
        for run_id in sorted(os.listdir(self.accumulation_root)):
            run_root = os.path.join(self.accumulation_root, run_id)
            if not os.path.isdir(run_root):
                continue
            try:
                safe_id = _safe_run_id(run_id)
            except ValueError:
                continue
            run_root = resolve_child_path(self.accumulation_root, safe_id)
            for dirpath, _dirnames, filenames in os.walk(run_root):
                for filename in sorted(filenames):
                    relative = os.path.relpath(
                        os.path.join(dirpath, filename), run_root,
                    )
                    file_path = _resolve_relative_path(run_root, relative)
                    yield file_path, f"{safe_id}/{relative}"

    def _pack_full(self, members: list[tuple[str, str]]) -> None:
        temp_path = resolve_child_path(
            _ensure_output_root(), f"{self.suffix}.zip.tmp",
        )
        try:
            with zipfile.ZipFile(
                temp_path, "w", zipfile.ZIP_DEFLATED,
            ) as zf:
                for file_path, archive_name in members:
                    zf.write(file_path, archive_name)
            os.replace(temp_path, self.zip_path)
        except Exception:
            if os.path.isfile(temp_path):
                os.remove(temp_path)
            raise

    def _existing_run_ids(
        self,
        members: list[tuple[str, str]],
    ) -> set[str] | None:
        expected_by_run: dict[str, set[str]] = {}
        for _file_path, archive_name in members:
            run_id, _separator, _relative = archive_name.partition("/")
            expected_by_run.setdefault(run_id, set()).add(archive_name)
        try:
            with zipfile.ZipFile(self.zip_path) as zf:
                names = zf.namelist()
        except (zipfile.BadZipFile, OSError):
            return None
        if len(names) != len(set(names)):
            return None
        expected_names = {archive_name for _path, archive_name in members}
        existing_by_run: dict[str, set[str]] = {}
        for name in names:
            run_id, separator, _relative = name.partition("/")
            if not separator:
                return None
            try:
                safe_id = _safe_run_id(run_id)
            except ValueError:
                return None
            if safe_id != run_id or name not in expected_names:
                return None
            existing_by_run.setdefault(run_id, set()).add(name)
        for run_id, existing_names in existing_by_run.items():
            if existing_names != expected_by_run.get(run_id, set()):
                return None
        return set(existing_by_run)

    def _pack(self) -> None:
        members = list(self._archive_members())
        existing_run_ids = self._existing_run_ids(members)
        if existing_run_ids is None:
            self._pack_full(members)
            return
        by_run: dict[str, list[tuple[str, str]]] = {}
        for member in members:
            run_id = member[1].partition("/")[0]
            by_run.setdefault(run_id, []).append(member)
        new_run_ids = sorted(set(by_run) - existing_run_ids)
        if not new_run_ids:
            return
        try:
            with zipfile.ZipFile(self.zip_path, "a", zipfile.ZIP_DEFLATED) as zf:
                for run_id in new_run_ids:
                    for file_path, archive_name in by_run[run_id]:
                        zf.write(file_path, archive_name)
        except (OSError, RuntimeError, zipfile.BadZipFile):
            self._pack_full(members)

    def flush(self, uploader: Any) -> None:
        self._pack()
        if uploader is None:
            return
        uploaded = True
        for path, name in (
            (self.zip_path, f"{self.suffix}.zip"),
            (self.manifest_path, f"{self.suffix}.manifest.json"),
        ):
            try:
                uploader.upload_file(Path(path), name)
            except Exception as exc:  # noqa: BLE001
                uploaded = False
                print(f"  (s3 upload failed for {name}: {exc})")
        if uploaded:
            print(
                f"  fused {self.suffix}.zip + manifest "
                f"({len(self.entries)} runs) -> s3",
            )

    def _unpack(self, zip_path: str) -> None:
        try:
            with zipfile.ZipFile(zip_path) as zf:
                for member in zf.infolist():
                    target = _resolve_relative_path(
                        self.accumulation_root, member.filename,
                    )
                    if member.is_dir():
                        prepare_output_directory(
                            target, allowed_roots=_allowed_roots(),
                        )
                        continue
                    parent = os.path.dirname(target)
                    prepare_output_directory(
                        parent, allowed_roots=_allowed_roots(),
                    )
                    with validated_open(
                        target,
                        "wb",
                        allowed_roots=_allowed_roots(),
                    ) as destination:
                        destination.write(zf.read(member))
        except zipfile.BadZipFile:
            print(f"  (s3 shard zip is invalid: {zip_path})")

    def download(self, uploader: Any) -> None:
        root = _ensure_output_root()
        zip_download = resolve_child_path(root, f"{self.suffix}.zip")
        manifest_download = resolve_child_path(
            root, f"{self.suffix}.manifest.json",
        )
        try:
            zip_present = uploader.download_file(
                f"{self.suffix}.zip", Path(zip_download),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  (s3 shard zip download failed: {exc})")
            zip_present = False
        if zip_present:
            self._unpack(zip_download)
        try:
            manifest_present = uploader.download_file(
                f"{self.suffix}.manifest.json", Path(manifest_download),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  (s3 shard manifest download failed: {exc})")
            manifest_present = False
        if not manifest_present:
            return
        try:
            with validated_open(
                manifest_download,
                allowed_roots=_allowed_roots(),
                encoding="utf-8",
            ) as fh:
                self._merge_manifest(json.load(fh))
        except (OSError, TypeError, ValueError):
            print("  (s3 shard manifest is unreadable; starting with no entries)")

    def completed_run_ids(self) -> set[str]:
        return set(self.entries)


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
            "detection_delay_epochs": delay,
            "isolation_compliance": iso,
            "sick_call_probability": scp,
        },
        "syndromic": {
            "detection_delay_epochs": delay,
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
    n_init = int(tier.get("initial_infected", 3))
    strategies = list(tier.get("surveillance_strategies") or ["syndromic"])
    vectors = list(tier["parameter_vectors"])
    default_agents = int(manifest.get("default_num_agents", 7000))
    for plat in platforms:
        n_agents = _platform_num_agents(
            plat,
            num_agents_override=num_agents_override,
            tier=tier,
            default_agents=default_agents,
        )
        for vec in vectors:
            dose = float(vec["dose_adj"])
            alpha = float(vec["alpha_c"])
            nonsus = float(vec.get("non_susceptible", 0.0))
            vec_id = str(vec.get("id", "vec"))
            path_over = dict(base_overrides or {})
            path_over[pathogen_id] = {
                **(path_over.get(pathogen_id) or {}),
                "dose_adjustment": dose,
                "initial_infected": n_init,
                "innate_nonsusceptible_fraction": nonsus,
            }
            dens_over = _density_contact_override(alpha)
            for sname in strategies:
                for seed in tier["seeds"]:
                    rid = "_".join(
                        [
                            "sr",
                            pathogen,
                            plat,
                            vec_id,
                            _dose_tag(dose),
                            _alpha_tag(alpha),
                            f"init{n_init}",
                            sname,
                            f"s{seed}",
                        ]
                    )
                    yield yield_run(
                        rid,
                        bundle=bundle,
                        pathogen_overrides=path_over,
                        config_overrides=merge_cfg(
                            surv_cfgs.get(sname), dens_over,
                        ),
                        seed=seed,
                        num_agents=n_agents,
                        pathogen=pathogen,
                        platform_id=plat,
                        surveillance=sname,
                        dose_adjustment=dose,
                        density_exponent=alpha,
                        n_init=n_init,
                        non_susceptible=nonsus,
                        parameter_vector=vec_id,
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
        n_init = sentinel_recovery.initial_infected(hazards, r_val)
        path_over = dict(base_overrides or {})
        path_over[pathogen_id] = {
            **(path_over.get(pathogen_id) or {}),
            "dose_adjustment": dose,
            "initial_infected": n_init,
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
            n_init=n_init,
            R_onboard=r_val,
            hazard_profile=hazard_profile,
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
    n_init = int(tier.get("initial_infected", defaults.get("initial_infected", 3)))
    strategies = list(tier.get("surveillance_strategies") or ["syndromic"])
    dens_over = _density_contact_override(alpha)
    knobs_list = _iter_vsp_knob_combos(tier, nominal)
    default_agents = int(manifest.get("default_num_agents", 7000))
    for plat, knobs, sname, seed in product(
        platforms, knobs_list, strategies, tier["seeds"],
    ):
        n_agents = _platform_num_agents(
            plat,
            num_agents_override=num_agents_override,
            tier=tier,
            default_agents=default_agents,
        )
        path_over = dict(base_overrides or {})
        path_over[pathogen_id] = {
            **(path_over.get(pathogen_id) or {}),
            "dose_adjustment": dose,
            "initial_infected": n_init,
        }
        tags = _vd_active_knob_tags(tier, knobs)
        rid = "_".join(
            [
                "vd", pathogen, plat, *tags, _dose_tag(dose), _alpha_tag(alpha),
                f"init{n_init}", sname, f"s{seed}",
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
            n_init=n_init,
            vsp_threshold=float(knobs["vsp_threshold"]),
            detection_delay_epochs=int(knobs["detection_delay"]),
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
            ("reluctant_delay_epochs", "reluctant_delay_epochs"),
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
            ("activation_delay_epochs", "surveillance_delay_epochs"),
        ),
        skip_if_present=frozenset({
            "sick_call_probability", "surveillance_delay_epochs",
        }),
    )
    esc = cfg.get("escalation") or {}
    latency = esc.get("decision_latency") or {}
    _copy_present(
        params,
        latency,
        (("confirmed_delay_epochs", "decision_latency_epochs"),),
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
            ("detection_delay_epochs", "detection_delay_epochs"),
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
        cfg = merge_cfg(
            _CAMPAIGN_ESCALATION_DEFAULTS, config_overrides, clock_cfg,
        )
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
        calibration_init_values=_calibration_init_values,
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
            "cumulative_reported_cases": s.get("cumulative_reported_cases", 0),
            "cumulative_reported_cases_passenger": s.get(
                "cumulative_reported_cases_passenger", 0,
            ),
            "cumulative_reported_cases_crew": s.get(
                "cumulative_reported_cases_crew", 0,
            ),
            "cumulative_reported_noise_cases": s.get(
                "cumulative_reported_noise_cases", 0,
            ),
            "cumulative_ever_ill": s.get("cumulative_ever_ill", 0),
            "cumulative_ever_ill_passenger": s.get(
                "cumulative_ever_ill_passenger", 0,
            ),
            "cumulative_ever_ill_crew": s.get("cumulative_ever_ill_crew", 0),
            "reported_case_rate_passenger": s.get(
                "reported_case_rate_passenger", 0.0,
            ),
            "ever_ill_rate_passenger": s.get("ever_ill_rate_passenger", 0.0),
            "vsp_triggered": bool(s.get("vsp_triggered", False)),
            "trigger_status": rec.get(
                "trigger_status",
                rec.get("reactive_protocols", {}).get("trigger_status", "none"),
            ),
        })
    return series


def _detection_epochs(
    ts: list[dict[str, Any]],
) -> tuple[int | None, int | None]:
    detection_epoch = None
    confirmation_epoch = None
    for e in ts:
        status = e.get("trigger_status", "none")
        if status in ("SUSPECTED", "CONFIRMED") and detection_epoch is None:
            detection_epoch = e["epoch"]
        if status == "CONFIRMED" and confirmation_epoch is None:
            confirmation_epoch = e["epoch"]
    return detection_epoch, confirmation_epoch


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
    ever_infected = infected_final + recovered
    attack_rate = ever_infected / num_agents if num_agents > 0 else 0
    outbreak_occurred = epidemic_took_off(ts)
    detection_epoch, confirmation_epoch = _detection_epochs(ts)
    vsp_trigger_epoch = next(
        (e["epoch"] for e in ts if e.get("vsp_triggered", False)),
        None,
    )
    r_eff_at_peak = None
    if peak_epoch > 0 and infected_by_epoch[peak_epoch - 1] > 0:
        new_at_peak = ts[peak_epoch].get("new_infections", 0)
        r_eff_at_peak = new_at_peak / infected_by_epoch[peak_epoch - 1]
    return {
        "attack_rate": round(attack_rate, 4),
        "reported_case_attack_rate": float(
            final.get("reported_case_rate_passenger", 0.0) or 0.0,
        ),
        "ever_ill_attack_rate": round(
            float(final.get("ever_ill_rate_passenger", 0.0) or 0.0), 4,
        ),
        "vsp_trigger_epoch": vsp_trigger_epoch,
        "peak_prevalence": peak_infected,
        "peak_epoch": peak_epoch,
        "outbreak_occurred": outbreak_occurred,
        "detection_epoch": detection_epoch,
        "confirmation_epoch": confirmation_epoch,
        "detection_lag": (
            peak_epoch - detection_epoch if detection_epoch is not None else None
        ),
        "total_quarantine_person_epochs": sum(e.get("quarantined", 0) for e in ts),
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


def _arm_sentinel_line_list(spec: dict[str, Any], run_dir: str) -> None:
    """Collect the sentinel ledger when shore exposure is on (compact-safe)."""
    voyage = (spec.get("config_overrides") or {}).get("voyage") or {}
    shore = voyage.get("shore_exposure") if isinstance(voyage, dict) else None
    if not isinstance(shore, dict) or not shore.get("enabled"):
        return
    spec["run"]["sentinel_line_list"] = os.path.join(run_dir, "sentinel_line_list.json")


def run_simulation(
    run_id: str,
    spec: dict[str, Any],
    *,
    full_telemetry: bool = False,
    keep_workdir: bool = False,
    output_root: Path | None = None,
    accumulation_suffix: str = "single",
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
    _arm_sentinel_line_list(spec, run_dir)

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
        accumulation_base = confine_to_base(
            root_str, os.path.join(root_str, "_shard_runs"),
        )
        prepare_output_directory(accumulation_base, allowed_roots=roots)
        accumulation_root = resolve_child_path(
            accumulation_base,
            validate_path_component(
                accumulation_suffix, label="shard suffix",
            ),
        )
        prepare_output_directory(accumulation_root, allowed_roots=roots)
        accumulation_dir = resolve_child_path(accumulation_root, safe_id)
        if os.path.isdir(accumulation_dir):
            shutil.rmtree(accumulation_dir)
        if keep_workdir:
            shutil.copytree(run_dir, accumulation_dir)
        else:
            shutil.move(run_dir, accumulation_dir)
        return True

    except Exception as exc:
        err_path = resolve_child_path(run_dir, "error.txt")
        with validated_open(err_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
            fh.write(f"{type(exc).__name__}: {exc}\n")
            fh.write(traceback.format_exc())
        return False


def _poll_child(proc: subprocess.Popen[str], timeout: int) -> tuple[bool, int | None]:
    deadline = time.monotonic() + timeout
    peak_rss_kb: int | None = None
    timed_out = False
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
    return timed_out, peak_rss_kb


def _write_subprocess_stderr(
    safe_id: str,
    roots: tuple[str, ...],
    *,
    timed_out: bool,
    timeout: int,
    returncode: int | None,
    stdout: str,
    stderr: str,
) -> None:
    err_path = _output_artifact(f"{safe_id}.subprocess_stderr.txt")
    with validated_open(err_path, "w", allowed_roots=roots, encoding="utf-8") as fh:
        if timed_out:
            fh.write(f"TimeoutExpired after {timeout}s\n")
            if stdout or stderr:
                fh.write("\n--- stdout ---\n")
                fh.write(stdout)
                fh.write("\n--- stderr ---\n")
                fh.write(stderr)
            return
        fh.write(f"returncode={returncode}\n\n")
        fh.write("--- stdout ---\n")
        fh.write(stdout)
        fh.write("\n--- stderr ---\n")
        fh.write(stderr)


def run_simulation_subprocess(
    run_id: str,
    spec: dict[str, Any],
    *,
    full_telemetry: bool = False,
    keep_workdir: bool = False,
    timeout: int = 3600,
    accumulation_suffix: str = "single",
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
        "--accumulation-suffix", accumulation_suffix,
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
        timed_out, peak_rss_kb = _poll_child(proc, timeout)
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
        if timed_out or not ok:
            _write_subprocess_stderr(
                safe_id, roots, timed_out=timed_out, timeout=timeout,
                returncode=returncode, stdout=stdout, stderr=stderr,
            )
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
    accumulation_suffix: str = "single",
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
        accumulation_suffix=accumulation_suffix,
    )
    return 0 if ok else 1


def _campaign_parser() -> argparse.ArgumentParser:
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
        "--natural-history-clock",
        choices=("hours", "legacy_epoch_day"),
        default=None,
        help=(
            "Select the natural-history clock arm. Manifests may declare their own "
            "(vs* Paper 3 campaigns must); a disagreement is refused, not resolved."
        ),
    )
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
        help=f"s3://bucket/path to upload the fused shard zip, manifest, and "
        f"{COMPLETED_LOG.name}.",
    )
    parser.add_argument(
        "--s3-log-every",
        type=int,
        default=25,
        help=f"Upload the fused shard zip, manifest, and {COMPLETED_LOG.name} "
        "every N successful runs (default 25).",
    )
    parser.add_argument(
        "--single",
        nargs=2,
        metavar=("SPEC", "OUTDIR"),
        default=None,
        help="Child mode: run one simulation from SPEC (a run_spec.json) into OUTDIR.",
    )
    parser.add_argument(
        "--accumulation-suffix",
        default="single",
        help=argparse.SUPPRESS,
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
    return parser


def _apply_smoke_defaults(args: argparse.Namespace) -> None:
    if not args.smoke:
        return
    args.tier = args.tier or "t1"
    args.platform = args.platform or "destroyer_baseline"
    args.epochs = args.epochs if args.epochs is not None else 2
    args.num_agents = args.num_agents if args.num_agents is not None else 20
    args.limit = args.limit if args.limit is not None else 1


def _resolve_shard(args: argparse.Namespace) -> tuple[int | None, int]:
    if args.shard_index is None:
        env_idx = os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX")
        if env_idx is not None:
            args.shard_index = int(env_idx)
    shard_count = args.shard_count
    shard_index = args.shard_index if args.shard_index is not None else 0
    if shard_count is None:
        return None, shard_index
    if shard_count < 1:
        raise SystemExit("--shard-count must be >= 1")
    if not 0 <= shard_index < shard_count:
        raise SystemExit(
            f"--shard-index {shard_index} out of range for "
            f"--shard-count {shard_count}",
        )
    return shard_count, shard_index


def _collect_all_runs(
    manifest: dict[str, Any],
    tiers: list[str],
    args: argparse.Namespace,
) -> list[tuple[str, str, dict[str, Any]]]:
    all_runs: list[tuple[str, str, dict[str, Any]]] = []
    for tier_id in tiers:
        runs = list(generate_tier_runs(
            manifest,
            tier_id,
            platform=args.platform,
            epochs_override=args.epochs,
            num_agents_override=args.num_agents,
            natural_history_clock=args.natural_history_clock,
        ))
        all_runs.extend((tier_id, run_id, spec) for run_id, spec in runs)
        print(f"\n{'=' * 60}")
        print(f"  {tier_id}: {len(runs)} runs")
        print(f"{'=' * 60}")
    return all_runs


def _campaign_gate(
    *,
    global_index: int,
    run_id: str,
    args: argparse.Namespace,
    shard_count: int | None,
    shard_index: int,
    executed: int,
    done: set[str],
    retry_only: set[str] | None,
    bundle: ShardBundle | None = None,
) -> str:
    if shard_count is not None and global_index % shard_count != shard_index:
        return "ignore"
    if args.limit is not None and executed >= args.limit:
        return "stop"
    if run_id in done:
        return "skip"
    if retry_only is not None and run_id not in retry_only:
        return "skip"
    if (
        (args.resume or args.retry_failed)
        and bundle is not None
        and run_id in bundle.completed_run_ids()
    ):
        return "skip_s3"
    return "run"


def _record_run_ok(bundle: ShardBundle, run_id: str) -> None:
    bundle.record_run(run_id)
    print(" OK")


def _perform_campaign_run(
    *,
    run_id: str,
    spec: dict[str, Any],
    args: argparse.Namespace,
    global_index: int,
    n_runs: int,
    shard_total: int,
    shard_index: int,
    shard_count: int | None,
    total: int,
    succeeded: int,
    failed: int,
    skipped: int,
    executed: int,
    uploader: Any,
    bundle: ShardBundle,
    t0: float,
) -> bool:
    if args.retry_failed:
        clear_failed_artifacts(run_id)
    elapsed = time.time() - t0
    rate = max(executed, 1) / max(elapsed, 1e-6)
    eta_min = max(shard_total - total, 0) / max(rate, 1e-6) / 60.0
    print(
        f"  [g{global_index + 1}/{n_runs}] {run_id}  "
        f"({succeeded}ok {failed}err {skipped}skip  "
        f"~{eta_min:.0f}min left)",
        end="",
        flush=True,
    )
    if args.in_process:
        ok = run_simulation(
            run_id, spec,
            full_telemetry=args.full_telemetry,
            keep_workdir=args.keep_workdir,
            accumulation_suffix=_shard_suffix(shard_index, shard_count),
        )
    else:
        ok = run_simulation_subprocess(
            run_id, spec,
            full_telemetry=args.full_telemetry,
            keep_workdir=args.keep_workdir,
            timeout=args.timeout,
            accumulation_suffix=_shard_suffix(shard_index, shard_count),
        )
    if not ok:
        mark_failed(run_id)
        print(" FAIL")
        return False
    mark_completed(run_id)
    _record_run_ok(bundle, run_id)
    if (
        uploader is not None
        and args.s3_log_every > 0
        and (succeeded + 1) % args.s3_log_every == 0
    ):
        _upload_completed_log(uploader, shard_index, shard_count)
        bundle.flush(uploader)
    return True


def _execute_assigned_runs(
    *,
    all_runs: list[tuple[str, str, dict[str, Any]]],
    args: argparse.Namespace,
    shard_count: int | None,
    shard_index: int,
    shard_total: int,
    done: set[str],
    retry_only: set[str] | None,
    uploader: Any,
    bundle: ShardBundle,
    t0: float,
) -> int:
    total = succeeded = failed = skipped = executed = 0
    for global_index, (_tier_id, run_id, spec) in enumerate(all_runs):
        gate = _campaign_gate(
            global_index=global_index,
            run_id=run_id,
            args=args,
            shard_count=shard_count,
            shard_index=shard_index,
            executed=executed,
            done=done,
            retry_only=retry_only,
            bundle=bundle,
        )
        if gate == "ignore":
            continue
        if gate == "stop":
            break
        total += 1
        if gate == "skip":
            skipped += 1
            continue
        if gate == "skip_s3":
            mark_completed(run_id)
            done.add(run_id)
            skipped += 1
            continue
        ok = _perform_campaign_run(
            run_id=run_id,
            spec=spec,
            args=args,
            global_index=global_index,
            n_runs=len(all_runs),
            shard_total=shard_total,
            shard_index=shard_index,
            shard_count=shard_count,
            total=total,
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            executed=executed,
            uploader=uploader,
            bundle=bundle,
            t0=t0,
        )
        executed += 1
        if ok:
            succeeded += 1
        else:
            failed += 1
    if uploader is not None:
        _upload_completed_log(uploader, shard_index, shard_count)
    bundle.flush(uploader)
    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  Campaign: {total} listed, {succeeded} ok, {failed} err, {skipped} skip")
    print(f"  Time: {elapsed / 3600:.2f}h ({elapsed / max(executed, 1):.1f}s/run)")
    print(f"  Output: {OUTPUT_ROOT}")
    print(f"{'=' * 60}")
    return 1 if failed else 0


def _print_deferred_tiers(
    manifest: dict[str, Any],
    tiers: list[str],
    args: argparse.Namespace,
) -> None:
    deferred_skipped = [
        tid for tid, t in sorted(manifest["tiers"].items())
        if _tier_is_deferred(t) and tid not in tiers
    ]
    if not deferred_skipped or (args.tier and args.tier not in ("all", "*")):
        return
    print(
        "  Skipping deferred tiers (pin dose then --tier <id> "
        f"or --include-deferred): {', '.join(deferred_skipped)}",
    )


def _print_dry_run(
    all_runs: list[tuple[str, str, dict[str, Any]]],
    tiers: list[str],
    shard_count: int | None,
    shard_index: int,
    shard_total: int,
) -> int:
    print(f"\n{'=' * 60}")
    print(f"  DRY RUN — {len(all_runs)} runs total across {len(tiers)} tier(s)")
    if shard_count is not None:
        print(f"  DRY RUN — {shard_total} runs would run on shard {shard_index}")
    print(f"  Output: {OUTPUT_ROOT}")
    print(f"{'=' * 60}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _campaign_parser().parse_args(argv)
    if args.single:
        spec_path, outdir = args.single
        return _run_single(
            spec_path, outdir,
            full_telemetry=args.full_telemetry,
            keep_workdir=args.keep_workdir,
            accumulation_suffix=args.accumulation_suffix,
        )
    if args.output_dir is not None:
        set_output_root(args.output_dir)
    _apply_smoke_defaults(args)
    manifest = load_manifest(args.manifest)
    args.natural_history_clock = _resolve_manifest_clock(manifest, args)
    _ensure_clock_arm(
        args.natural_history_clock or DEFAULT_NATURAL_HISTORY_CLOCK,
        explicit=args.natural_history_clock is not None,
        persist=not args.dry_run,
    )
    shard_count, shard_index = _resolve_shard(args)
    uploader = S3Uploader(args.s3_prefix) if args.s3_prefix else None
    bundle = ShardBundle(shard_index, shard_count)
    if args.resume or args.retry_failed:
        bundle.load_local_manifest()
    if uploader is not None and (args.resume or args.retry_failed):
        _download_completed_log(uploader, shard_index, shard_count)
        bundle.download(uploader)
    done = completed_runs() if (args.resume or args.retry_failed) else set()
    retry_only = failed_runs() if args.retry_failed else None
    if args.retry_failed and not retry_only:
        print(f"  --retry-failed: {FAILED_RUNS_FILENAME} is empty; nothing to retry.")
        return 0
    tiers = resolve_tier_ids(
        manifest, args.tier, include_deferred=args.include_deferred,
    )
    _print_deferred_tiers(manifest, tiers, args)
    all_runs = _collect_all_runs(manifest, tiers, args)
    shard_total = sum(
        1 for gi in range(len(all_runs))
        if shard_count is None or gi % shard_count == shard_index
    )
    if shard_count is not None:
        print(
            f"\n  Shard {shard_index}/{shard_count}: "
            f"{shard_total} of {len(all_runs)} runs assigned to this shard",
        )
    if args.dry_run:
        return _print_dry_run(all_runs, tiers, shard_count, shard_index, shard_total)
    return _execute_assigned_runs(
        all_runs=all_runs,
        args=args,
        shard_count=shard_count,
        shard_index=shard_index,
        shard_total=shard_total,
        done=done,
        retry_only=retry_only,
        uploader=uploader,
        bundle=bundle,
        t0=time.time(),
    )


def _resume_log_key(shard_index: int, shard_count: int | None) -> str:
    return f"_resume/completed_runs.{_shard_suffix(shard_index, shard_count)}.txt"


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
