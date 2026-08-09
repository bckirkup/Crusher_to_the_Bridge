"""Outbreak outcome surfaces keyed by introductions k (Stan or fixture)."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from importlib import resources
from typing import Any, Iterable

from picard_framework.analysis._io import allowed_roots, read_json, safe_path
from simulation_utils.paths import validated_open


@dataclass(frozen=True)
class SurfacePoint:
    P_trigger: float
    E_AR: float
    P_accel: float
    E_cost_onboard: float
    E_peak_epoch: float | None = None


@dataclass
class OutbreakSurface:
    """Collection of response curves keyed by (platform, pathogen, response)."""

    curves: dict[tuple[str, str, str], dict[str, list[float]]]
    source: str

    def lookup(
        self,
        *,
        platform_class: str,
        pathogen: str,
        baseline_response: str,
        k: float,
    ) -> SurfacePoint:
        key = (platform_class, pathogen, baseline_response)
        curve = self.curves.get(key)
        if curve is None:
            # Fall back: same platform/response any pathogen, then any pathogen mega.
            curve = self._fallback_curve(platform_class, pathogen, baseline_response)
        return _interpolate_curve(curve, float(k))

    def _fallback_curve(
        self,
        platform_class: str,
        pathogen: str,
        baseline_response: str,
    ) -> dict[str, list[float]]:
        for cand in (
            (platform_class, pathogen, baseline_response),
            (platform_class, "norovirus", baseline_response),
            ("mega", pathogen, baseline_response),
            ("mega", "norovirus", "vsp"),
        ):
            if cand in self.curves:
                return self.curves[cand]
        if not self.curves:
            raise KeyError("OutbreakSurface has no curves")
        return next(iter(self.curves.values()))


def _interpolate_curve(curve: dict[str, list[float]], k: float) -> SurfacePoint:
    ks = curve["k"]
    if not ks:
        raise ValueError("empty outbreak curve")
    if k <= ks[0]:
        i = 0
        return SurfacePoint(
            P_trigger=curve["P_trigger"][i],
            E_AR=curve["E_AR"][i],
            P_accel=curve["P_accel"][i],
            E_cost_onboard=curve["E_cost_onboard"][i],
            E_peak_epoch=(curve.get("E_peak_epoch") or [None])[i]
            if curve.get("E_peak_epoch")
            else None,
        )
    if k >= ks[-1]:
        i = -1
        peak = curve.get("E_peak_epoch")
        return SurfacePoint(
            P_trigger=curve["P_trigger"][i],
            E_AR=curve["E_AR"][i],
            P_accel=curve["P_accel"][i],
            E_cost_onboard=curve["E_cost_onboard"][i],
            E_peak_epoch=peak[i] if peak else None,
        )

    # Linear interpolate between bracketing k.
    for i in range(len(ks) - 1):
        k0, k1 = ks[i], ks[i + 1]
        if k0 <= k <= k1:
            if k1 == k0:
                t = 0.0
            else:
                t = (k - k0) / (k1 - k0)

            def lerp(a: list[float]) -> float:
                return float(a[i]) * (1.0 - t) + float(a[i + 1]) * t

            peak_list = curve.get("E_peak_epoch")
            peak_val = lerp(peak_list) if peak_list else None
            return SurfacePoint(
                P_trigger=lerp(curve["P_trigger"]),
                E_AR=lerp(curve["E_AR"]),
                P_accel=lerp(curve["P_accel"]),
                E_cost_onboard=lerp(curve["E_cost_onboard"]),
                E_peak_epoch=peak_val,
            )
    # Nearest
    nearest = min(range(len(ks)), key=lambda i: abs(ks[i] - k))
    peak = curve.get("E_peak_epoch")
    return SurfacePoint(
        P_trigger=curve["P_trigger"][nearest],
        E_AR=curve["E_AR"][nearest],
        P_accel=curve["P_accel"][nearest],
        E_cost_onboard=curve["E_cost_onboard"][nearest],
        E_peak_epoch=peak[nearest] if peak else None,
    )


def _curve_from_row_lists(
    k: list[float],
    p_trigger: list[float],
    e_ar: list[float],
    p_accel: list[float],
    e_cost: list[float],
    e_peak: list[float] | None = None,
) -> dict[str, list[float]]:
    order = sorted(range(len(k)), key=lambda i: k[i])
    curve: dict[str, list[float]] = {
        "k": [float(k[i]) for i in order],
        "P_trigger": [float(p_trigger[i]) for i in order],
        "E_AR": [float(e_ar[i]) for i in order],
        "P_accel": [float(p_accel[i]) for i in order],
        "E_cost_onboard": [float(e_cost[i]) for i in order],
    }
    if e_peak is not None:
        curve["E_peak_epoch"] = [float(e_peak[i]) for i in order]
    return curve


def _parse_surface_payload(payload: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, list[float]]]:
    curves: dict[tuple[str, str, str], dict[str, list[float]]] = {}
    for entry in payload.get("surfaces", []):
        key = (
            str(entry["platform_class"]),
            str(entry["pathogen"]),
            str(entry.get("baseline_response", "vsp")),
        )
        peak = entry.get("E_peak_epoch")
        curves[key] = _curve_from_row_lists(
            list(entry["k"]),
            list(entry["P_trigger"]),
            list(entry["E_AR"]),
            list(entry["P_accel"]),
            list(entry["E_cost_onboard"]),
            list(peak) if peak is not None else None,
        )
    return curves


def _load_default_fixture_payload() -> dict[str, Any]:
    root = resources.files("picard_framework.analysis.boundary")
    text = (root / "fixtures" / "outbreak_surface.json").read_text(encoding="utf-8")
    return json.loads(text)


def load_fixture_surface(path: str | None = None) -> OutbreakSurface:
    """Load packaged or explicit fixture JSON (CLI path must be under CWD)."""
    if path is None:
        payload = _load_default_fixture_payload()
        return OutbreakSurface(
            curves=_parse_surface_payload(payload), source="fixture:default"
        )

    resolved = safe_path(path)
    payload = read_json(resolved)
    return OutbreakSurface(
        curves=_parse_surface_payload(payload), source=f"fixture:{resolved}"
    )


def _load_surface_csv(path: str) -> dict[tuple[str, str, str], dict[str, list[float]]]:
    grouped: dict[tuple[str, str, str], dict[str, list[float]]] = {}
    with validated_open(path, allowed_roots=allowed_roots(), encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            key = (
                str(row["platform_class"]),
                str(row["pathogen"]),
                str(row.get("baseline_response") or "vsp"),
            )
            bucket = grouped.setdefault(
                key,
                {
                    "k": [],
                    "P_trigger": [],
                    "E_AR": [],
                    "P_accel": [],
                    "E_cost_onboard": [],
                    "E_peak_epoch": [],
                },
            )
            bucket["k"].append(float(row["k"]))
            bucket["P_trigger"].append(float(row["P_trigger"]))
            bucket["E_AR"].append(float(row["E_AR"]))
            bucket["P_accel"].append(float(row.get("P_accel") or 0.0))
            bucket["E_cost_onboard"].append(float(row.get("E_cost_onboard") or 0.0))
            if row.get("E_peak_epoch") not in (None, ""):
                bucket["E_peak_epoch"].append(float(row["E_peak_epoch"]))
            else:
                bucket["E_peak_epoch"].append(float("nan"))

    curves: dict[tuple[str, str, str], dict[str, list[float]]] = {}
    for key, raw in grouped.items():
        peak = raw["E_peak_epoch"]
        peak_out = None if all(x != x for x in peak) else peak  # all NaN
        curves[key] = _curve_from_row_lists(
            raw["k"],
            raw["P_trigger"],
            raw["E_AR"],
            raw["P_accel"],
            raw["E_cost_onboard"],
            peak_out,
        )
    return curves


def _find_stan_surface_files(stan_fit_dir: str) -> list[str]:
    """Candidate outbreak surface files under a Stan fit directory."""
    root = safe_path(stan_fit_dir)
    candidates = [
        os.path.join(root, "outbreak_surface.json"),
        os.path.join(root, "outbreak_surface.csv"),
        os.path.join(root, "posterior", "outbreak_surface.json"),
        os.path.join(root, "posterior", "outbreak_surface.csv"),
        os.path.join(root, "boundary", "outbreak_surface.json"),
        os.path.join(root, "boundary", "outbreak_surface.csv"),
    ]
    return [p for p in candidates if os.path.isfile(p)]


def load_stan_surface(stan_fit_dir: str) -> OutbreakSurface:
    """Load outbreak surface tables exported beside a Stan fit.

    Expected formats:
    - outbreak_surface.json (same schema as fixtures)
    - outbreak_surface.csv with columns platform_class,pathogen,baseline_response,k,...
    """
    files = _find_stan_surface_files(stan_fit_dir)
    if not files:
        raise FileNotFoundError(
            f"No outbreak_surface.{{json,csv}} under {stan_fit_dir}; "
            "export a k-indexed surface or use --lookup fixture"
        )
    path = files[0]
    if path.endswith(".json"):
        payload = read_json(path)
        curves = _parse_surface_payload(payload)
    else:
        curves = _load_surface_csv(path)
    if not curves:
        raise ValueError(f"Empty outbreak surface at {path}")
    return OutbreakSurface(curves=curves, source=f"stan:{path}")


def load_outbreak_surface(
    *,
    lookup: str = "auto",
    stan_fit_dir: str | None = None,
    fixture_path: str | None = None,
) -> OutbreakSurface:
    """Resolve outbreak surface from Stan fit and/or fixture.

    ``lookup``: ``auto`` | ``fixture`` | ``stan``
    """
    mode = (lookup or "auto").lower()
    if mode not in ("auto", "fixture", "stan"):
        raise ValueError(f"Unknown lookup mode: {lookup}")

    if mode == "fixture":
        return load_fixture_surface(fixture_path)

    if mode == "stan":
        if not stan_fit_dir:
            raise ValueError("--stan-fit is required when --lookup stan")
        return load_stan_surface(stan_fit_dir)

    # auto
    if stan_fit_dir:
        try:
            return load_stan_surface(stan_fit_dir)
        except FileNotFoundError:
            pass
    return load_fixture_surface(fixture_path)


def surface_keys(surface: OutbreakSurface) -> Iterable[tuple[str, str, str]]:
    return surface.curves.keys()
