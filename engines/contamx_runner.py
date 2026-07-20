"""
engines.contamx_runner
~~~~~~~~~~~~~~~~~~~~~~~~

Thin, dependency-light seam for driving the **real** NIST ContamX solver as
an optional parallel airflow engine, plus a native reader for the binary
``.SIM`` results file ContamX produces.

This module is deliberately *offline-safe*:

- It never requires ContamX to import. ``find_contamx`` performs capability
  detection and returns ``None`` when no binary is configured/available, so
  the caller can fall back to the pure-Python ``ContamTransportEngine``
  (the default, CI-validated engine).
- ``run_contamx`` shells out to a configured ``contamx`` executable. This is
  the only external-process dependency in the project and is strictly
  opt-in (see ``docs/CONTAM_INTEROP.md``). It is **not** a bioinformatics
  instrument dependency (Law 5 governs the diagnostic-noise pipeline, not
  the airflow transport engine).
- ``SimResults`` parses the binary ``.SIM`` format documented in
  ``py-contam/documentation/SIM_file_format.txt``. The byte layout mirrors
  the read logic in the sibling ``py-contam`` repo's ``contam_output.py``
  (referenced read-only, Law 6); this is a fresh, numpy-only
  implementation (no pandas dependency) so it can live in the core engine
  path without pulling in the dashboard extras.

The ContamX binary is a NIST executable (not pip-installable) and is not
present in CI or the offline build environment, so every code path here is
unit-tested with crafted ``.SIM`` fixtures and capability stubs rather than
a live solver run.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any

import numpy as np

from simulation_utils.paths import is_path_under_base, validated_open

# Candidate executable names for the ContamX solver, most-specific first.
_CONTAMX_BINARY_NAMES = (
    "contamx",
    "contamx3",
    "ContamX3.exe",
    "contamx3.4.exe",
    "ContamX.exe",
    "ContamX3",
)

# Default in-repo drop directory for NIST binaries (gitignored contents).
_THIRD_PARTY_CONTAMX_REL = os.path.join("third_party", "contamx")

# Standard air density [kg/m³] used to convert ContamX mass flows (kg/s)
# back to volumetric flows (m³/h) when a node density is unavailable.
_DEFAULT_AIR_DENSITY = 1.2041
_SECONDS_PER_HOUR = 3600.0


class ContamXUnavailable(RuntimeError):
    """Raised when the ContamX solver cannot be located or executed."""


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _is_runnable_binary(path: str) -> bool:
    """Return True when *path* looks like an executable ContamX binary."""
    if not os.path.isfile(path):
        return False
    if os.name == "nt":
        lower = path.lower()
        if lower.endswith((".exe", ".bat", ".cmd")):
            return True
    return os.access(path, os.X_OK)


def _search_dir_for_contamx(directory: str) -> str | None:
    """Return the first known ContamX executable under *directory*."""
    if not directory or not os.path.isdir(directory):
        return None
    for name in _CONTAMX_BINARY_NAMES:
        candidate = os.path.join(directory, name)
        if _is_runnable_binary(candidate):
            return os.path.abspath(candidate)
    # Fall back: any ContamX*.exe in the folder (Windows install dumps)
    try:
        for entry in sorted(os.listdir(directory)):
            lower = entry.lower()
            if lower.startswith("contamx") and lower.endswith(".exe"):
                candidate = os.path.join(directory, entry)
                if _is_runnable_binary(candidate):
                    return os.path.abspath(candidate)
    except OSError:
        return None
    return None


def find_contamx(config: dict[str, Any] | None = None) -> str | None:
    """Locate a runnable ContamX executable.

    Resolution order:

    1. ``config['hvac']['contamx']['binary_path']`` (explicit config).
    2. ``CONTAMX_BINARY`` environment variable.
    3. ``CONTAMX_HOME`` directory (searched for known executable names).
    4. Repo ``third_party/contamx/`` drop directory.
    5. A known ContamX executable name on ``PATH``.

    Returns the resolved absolute path, or ``None`` when no usable binary is
    found (the caller should then fall back to the native engine).
    """
    candidates: list[str] = []

    if config:
        configured = (
            config.get("hvac", {})
            .get("contamx", {})
            .get("binary_path")
        )
        if configured:
            candidates.append(configured)

    env_binary = os.environ.get("CONTAMX_BINARY")
    if env_binary:
        candidates.append(env_binary)

    for explicit in candidates:
        expanded = os.path.expanduser(explicit)
        if _is_runnable_binary(expanded):
            return os.path.abspath(expanded)

    search_dirs: list[str] = []
    env_home = os.environ.get("CONTAMX_HOME")
    if env_home:
        search_dirs.append(os.path.expanduser(env_home))
    search_dirs.append(os.path.join(_repo_root(), _THIRD_PARTY_CONTAMX_REL))

    for directory in search_dirs:
        found = _search_dir_for_contamx(directory)
        if found:
            return found

    for name in _CONTAMX_BINARY_NAMES:
        found = shutil.which(name)
        if found:
            return os.path.abspath(found)

    return None


def run_contamx(
    prj_path: str,
    binary: str | None = None,
    *,
    config: dict[str, Any] | None = None,
    timeout_s: float = 300.0,
) -> str:
    """Run ContamX on *prj_path* and return the path to the ``.sim`` output.

    ContamX writes ``<project>.sim`` alongside the project file. Raises
    ``ContamXUnavailable`` when no binary is found or the solver exits
    non-zero / times out / produces no results file.
    """
    resolved = binary or find_contamx(config)
    if resolved is None:
        raise ContamXUnavailable(
            "No ContamX binary configured or on PATH "
            "(set hvac.contamx.binary_path or CONTAMX_BINARY)."
        )
    if not os.path.isfile(prj_path):
        raise ContamXUnavailable(f"Project file not found: {prj_path}")

    prj_dir = os.path.dirname(os.path.abspath(prj_path))
    prj_name = os.path.basename(prj_path)
    try:
        completed = subprocess.run(  # noqa: S603 - opt-in local solver
            [resolved, prj_name],
            cwd=prj_dir,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ContamXUnavailable(f"ContamX invocation failed: {exc}") from exc

    if completed.returncode != 0:
        raise ContamXUnavailable(
            f"ContamX exited with code {completed.returncode}: "
            f"{completed.stderr.strip()[:500]}"
        )

    sim_path = os.path.splitext(prj_path)[0] + ".sim"
    if not os.path.isfile(sim_path):
        raise ContamXUnavailable(
            f"ContamX produced no results file at {sim_path}"
        )
    return sim_path


@dataclass
class SimFrame:
    """A single output time step decoded from a ``.SIM`` file."""

    sim_time_s: int
    ambient: np.ndarray          # [Tambt, P, Ws, Wd, CC...]
    path_nr: np.ndarray          # Contam path number per slot (from record nr)
    path_flow_kg_s: np.ndarray   # Flow0 per airflow path [kg/s]
    node_density: np.ndarray     # air density per airflow node [kg/m³]
    node_concentration: np.ndarray  # (n_contaminant_nodes, nctm) mass fraction


class SimResults:
    """Native reader for the NIST ContamX binary ``.SIM`` results file.

    Implements the format documented in
    ``py-contam/documentation/SIM_file_format.txt``. Only 32-bit ints
    (``i4``), 16-bit ints (``i2``) and 32-bit floats (``f4``) appear in the
    format; this reader uses ``numpy`` (already a core dependency) and no
    pandas.

    Every output frame (time step *and* the interleaved daily-summary
    record, which is byte-identical in size) is decoded into a
    :class:`SimFrame`. ``steady_state_frame`` returns the last decoded
    *time-step* frame with valid node densities (trailing summary rows that
    repeat ``sim_time`` with a broken node block are skipped).

    Path flows are keyed by the ``nr`` embedded in each path record
    (``nr(i4) dP(f4) Flow0(f4) Flow1(f4)``), not by the header cross-reference
    table — ContamX 3.x xref ``(typ, nr)`` pairs are unreliable for mapping.
    """

    _HEADER_FIELDS = (
        "version_number", "nzone", "npath", "nctm", "njct", "ndct",
        "time_list", "date_0", "time_0", "date_1", "time_1",
        "pfsave", "zfsave", "zcsave", "nafnd", "nccnd", "nafpt",
    )

    def __init__(
        self,
        filename: str,
        *,
        allowed_roots: tuple[str, ...] | None = None,
    ) -> None:
        self.filename = filename
        resolved = os.path.realpath(filename)
        roots = allowed_roots
        if roots is None:
            # Default: repository root plus system temp (pytest / TemporaryDirectory).
            roots_list: list[str] = [_repo_root()]
            tmp_root = os.path.realpath(tempfile.gettempdir())
            if is_path_under_base(tmp_root, resolved):
                roots_list.append(tmp_root)
            roots = tuple(roots_list)
        with validated_open(resolved, "rb", allowed_roots=roots) as fp:
            raw = fp.read()
        self._buf = raw
        self._offset = 0

        header_vals = self._take_i4(len(self._HEADER_FIELDS))
        self.header = {
            name: int(val)
            for name, val in zip(self._HEADER_FIELDS, header_vals, strict=True)
        }

        nafnd = self.header["nafnd"]
        nafpt = self.header["nafpt"]

        # Cross-reference tables occupy a fixed byte span before the first
        # frame; content is retained for diagnostics but not used to key flows.
        self.airflow_node_xref = self._take_i4(2 * nafnd).reshape(nafnd, 2)
        self.contaminant_node_xref = self._take_i4(2 * nafnd).reshape(nafnd, 2)
        self.airflow_path_xref = self._take_i4(2 * nafpt).reshape(nafpt, 2)

        self._data_start = self._offset
        self.frames: list[SimFrame] = self._decode_frames()

    # ── low-level readers ────────────────────────────────────────────────

    def _take_i4(self, count: int) -> np.ndarray:
        n_bytes = count * 4
        chunk = self._buf[self._offset:self._offset + n_bytes]
        if len(chunk) < n_bytes:
            raise ValueError("Truncated .SIM file (int section)")
        self._offset += n_bytes
        return np.frombuffer(chunk, dtype="<i4", count=count).astype(np.int64)

    def _record_sizes(self) -> tuple[int, int, int, int]:
        nctm = self.header["nctm"]
        nafnd = self.header["nafnd"]
        nafpt = self.header["nafpt"]
        nccnd = self.header["nccnd"]
        ambient = (2 * 2) + (5 * 4) + nctm * 4
        # Path record: nr(i4) + dP(f4) + Flow0(f4) + Flow1(f4) = 16 bytes
        path = 16 * nafpt
        # Node record: nr(i4) + T(f4) + P(f4) + D(f4) = 16 bytes (ambient omitted)
        node = 16 * (nafnd - 1)
        contaminant = ((1 * 4) + nctm * 4) * (nccnd - 1)
        return ambient, path, node, contaminant

    def _decode_frames(self) -> list[SimFrame]:
        ambient_sz, path_sz, node_sz, ctm_sz = self._record_sizes()
        record_sz = ambient_sz + path_sz + node_sz + ctm_sz
        if record_sz <= 0:
            return []

        nctm = self.header["nctm"]
        nafnd = self.header["nafnd"]
        nafpt = self.header["nafpt"]
        nccnd = self.header["nccnd"]

        available = len(self._buf) - self._data_start
        n_records = available // record_sz

        frames: list[SimFrame] = []
        off = self._data_start
        for _ in range(n_records):
            # Ambient line: dayofy(i2) daytyp(i2) sim_time(i4) + (4+nctm) f4
            sim_time = int(np.frombuffer(
                self._buf, dtype="<i4", count=1, offset=off + 4,
            )[0])
            ambient = np.frombuffer(
                self._buf, dtype="<f4", count=4 + nctm, offset=off + 8,
            ).astype(np.float64)
            p_off = off + ambient_sz

            path_nr = np.empty(nafpt, dtype=np.int64)
            flow0 = np.empty(nafpt, dtype=np.float64)
            for i in range(nafpt):
                base = p_off + 16 * i
                path_nr[i] = int(np.frombuffer(
                    self._buf, dtype="<i4", count=1, offset=base,
                )[0])
                flow0[i] = float(np.frombuffer(
                    self._buf, dtype="<f4", count=1, offset=base + 8,
                )[0])
            n_off = p_off + path_sz

            density = np.empty(nafnd - 1, dtype=np.float64)
            for i in range(nafnd - 1):
                base = n_off + 16 * i
                density[i] = float(np.frombuffer(
                    self._buf, dtype="<f4", count=1, offset=base + 12,
                )[0])
            c_off = n_off + node_sz

            ctm = np.frombuffer(
                self._buf, dtype="<f4",
                count=(1 + nctm) * (nccnd - 1), offset=c_off,
            ).reshape(nccnd - 1, 1 + nctm)
            concentration = ctm[:, 1:].astype(np.float64)

            frames.append(SimFrame(
                sim_time_s=sim_time,
                ambient=ambient,
                path_nr=path_nr,
                path_flow_kg_s=flow0,
                node_density=density,
                node_concentration=concentration,
            ))
            off += record_sz
        return frames

    # ── public helpers ───────────────────────────────────────────────────

    def steady_state_frame(self) -> SimFrame:
        """Return the last usable time-step frame (not a trailing summary)."""
        if not self.frames:
            raise ValueError("No frames decoded from .SIM file")
        # ContamX may append a same-sim_time summary whose node block does not
        # match the time-step layout; prefer the last frame with real densities.
        for frame in reversed(self.frames):
            if frame.node_density.size and np.any(frame.node_density > 0.1):
                return frame
        return self.frames[-1]

    def path_volumetric_flow_m3h(
        self, frame: SimFrame | None = None,
    ) -> dict[int, float]:
        """Map CONTAM airflow-path number → volumetric flow [m³/h].

        Converts the primary mass flow ``Flow0`` [kg/s] to volumetric flow
        using mean positive node density (fallback ``_DEFAULT_AIR_DENSITY``),
        keyed by the path ``nr`` embedded in each path record.
        """
        frame = frame or self.steady_state_frame()
        density = _DEFAULT_AIR_DENSITY
        if frame.node_density.size:
            positive = frame.node_density[frame.node_density > 0]
            if positive.size:
                density = float(positive.mean())

        flows: dict[int, float] = {}
        for path_nr, mass_flow in zip(
            frame.path_nr, frame.path_flow_kg_s, strict=True,
        ):
            flows[int(path_nr)] = float(mass_flow) / density * _SECONDS_PER_HOUR
        return flows
