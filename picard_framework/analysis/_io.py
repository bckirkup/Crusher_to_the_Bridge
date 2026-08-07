"""Path-safe I/O helpers for the campaign analysis package.

CLI path arguments are confined to the process CWD (Sonar S8707 / S2083).
"""

from __future__ import annotations

import csv
import gzip
import json
import os
import zipfile
from pathlib import Path
from typing import Any, Iterable, Sequence

from simulation_utils.paths import (
    confine_to_base,
    prepare_output_directory,
    validated_open,
)


def cwd_root() -> str:
    """Real path of the current working directory."""
    return os.path.realpath(os.getcwd())


def allowed_roots() -> tuple[str, ...]:
    """Roots permitted for analysis CLI reads/writes."""
    return (cwd_root(),)


def safe_path(path: Path | str) -> str:
    """Resolve ``path`` and confine it to the current working directory."""
    try:
        return confine_to_base(cwd_root(), str(path))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def ensure_out_dir(path: Path | str) -> str:
    """Create an output directory under the CWD with restrictive permissions."""
    resolved = safe_path(path)
    return prepare_output_directory(resolved, allowed_roots=allowed_roots())


def read_json(path: str) -> Any:
    """Load JSON from a path under allowed roots."""
    with validated_open(path, allowed_roots=allowed_roots(), encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: str, payload: Any) -> None:
    """Write JSON with indentation under allowed roots."""
    parent = os.path.dirname(path)
    if parent:
        prepare_output_directory(parent, allowed_roots=allowed_roots())
    with validated_open(
        path, "w", allowed_roots=allowed_roots(), encoding="utf-8"
    ) as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")


def write_csv(path: str, rows: Sequence[dict[str, Any]], columns: Sequence[str]) -> None:
    """Write a CSV table with a stable column order."""
    parent = os.path.dirname(path)
    if parent:
        prepare_output_directory(parent, allowed_roots=allowed_roots())
    with validated_open(
        path, "w", allowed_roots=allowed_roots(), encoding="utf-8", newline=""
    ) as fh:
        writer = csv.DictWriter(fh, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c) for c in columns})


def write_csv_gz(
    path: str, rows: Sequence[dict[str, Any]], columns: Sequence[str]
) -> None:
    """Write a gzip-compressed CSV table."""
    parent = os.path.dirname(path)
    if parent:
        prepare_output_directory(parent, allowed_roots=allowed_roots())
    # gzip.open is not Path.write_text; contain path then open via validated binary handle.
    import io

    with validated_open(path, "wb", allowed_roots=allowed_roots()) as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb") as gz:
            buf = io.TextIOWrapper(gz, encoding="utf-8", newline="")
            writer = csv.DictWriter(buf, fieldnames=list(columns), extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({c: row.get(c) for c in columns})
            buf.flush()
            buf.detach()


def write_timeseries_table(
    out_dir: str,
    rows: Sequence[dict[str, Any]],
    columns: Sequence[str],
) -> str:
    """Write epoch timeseries as parquet when pyarrow is available, else csv.gz.

    Returns the basename written (``epoch_timeseries.parquet`` or
    ``epoch_timeseries.csv.gz``).
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        path = os.path.join(out_dir, "epoch_timeseries.csv.gz")
        write_csv_gz(path, rows, columns)
        return "epoch_timeseries.csv.gz"

    table_dict: dict[str, list[Any]] = {c: [] for c in columns}
    for row in rows:
        for c in columns:
            table_dict[c].append(row.get(c))
    table = pa.table(table_dict)
    path = os.path.join(out_dir, "epoch_timeseries.parquet")
    parent = os.path.dirname(path)
    if parent:
        prepare_output_directory(parent, allowed_roots=allowed_roots())
    # Write via temporary bytes then validated_open to satisfy path hardening.
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink)
    data = sink.getvalue().to_pybytes()
    with validated_open(path, "wb", allowed_roots=allowed_roots()) as fh:
        fh.write(data)
    return "epoch_timeseries.parquet"


def iter_result_zips(results_dir: str) -> Iterable[str]:
    """Yield absolute paths of ``*.zip`` files under ``results_dir``."""
    root = safe_path(results_dir)
    if not os.path.isdir(root):
        raise SystemExit(f"Not a directory: {results_dir}")
    for dirpath, _dirnames, filenames in os.walk(root):
        # Confine walked paths (they are under root already).
        for name in sorted(filenames):
            if not name.endswith(".zip"):
                continue
            yield os.path.join(dirpath, name)


def load_zip_json(zip_path: str, suffix: str) -> Any | None:
    """Read the first JSON member in ``zip_path`` whose name ends with ``suffix``."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = [n for n in zf.namelist() if n.endswith(suffix)]
            if not names:
                return None
            raw = zf.read(names[0]).decode("utf-8")
            return json.loads(raw)
    except (zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None


def load_run_zip(zip_path: str) -> dict[str, Any] | None:
    """Load summary / timeseries / run_spec from a campaign result zip."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()

            def _read(suffix: str) -> Any | None:
                hits = [n for n in names if n.endswith(suffix)]
                if not hits:
                    return None
                try:
                    return json.loads(zf.read(hits[0]).decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return None

            summary = _read("summary.json")
            if summary is None:
                return None
            return {
                "zip_path": zip_path,
                "run_id": str(summary.get("run_id") or Path(zip_path).stem),
                "summary": summary,
                "timeseries": _read("timeseries.json") or [],
                "run_spec": _read("run_spec.json") or {},
            }
    except (zipfile.BadZipFile, OSError):
        return None
