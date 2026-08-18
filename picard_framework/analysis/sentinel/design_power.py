"""Design-stage power and precision projections for the sentinel fleet.

Engine ``ceiling`` differentiates the existing numpy forward model and computes
an analytic Poisson Fisher-information ceiling.  Engine ``fit`` is deliberately
restricted to the fit-scale replica: the reference sampler cannot be run for a
regional fleet of 1,440 voyages in a practical design loop.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from fractions import Fraction
from importlib import resources
from statistics import NormalDist
from typing import Any, Mapping, Sequence

import numpy as np

from picard_framework.analysis._io import read_json
from picard_framework.analysis.sentinel.exposure import (
    ascertainment_fraction,
    build_exposure_design,
)
from picard_framework.analysis.sentinel.fleet import fleet_time_confounded_ports
from picard_framework.analysis.sentinel.incubation import (
    default_pathogen,
    delays_for_pathogen,
)
from picard_framework.analysis.sentinel.itinerary import voyage_from_config
from picard_framework.analysis.sentinel.observations import bundle_from_dict
from picard_framework.analysis.stan._sentinel_fleet_data import (
    FleetRates,
    FleetVoyage,
    build_sentinel_fleet_data,
    expected_onsets_fleet,
)
from picard_framework.analysis.stan._sentinel_fleet_reference import (
    fleet_reference_posterior,
)

START_DATE = date(2026, 3, 2)
FINITE_DIFFERENCE_LOG_STEP = 0.01
Z90 = 1.6448536269514722
DEFAULT_ALPHA = 0.10
DEFAULT_POWER = 0.80
DEFAULT_DRAWS = 120
DEFAULT_WARMUP = 400
DEFAULT_REPLICATES = 5
SMOKE_DRAWS = 40
SMOKE_WARMUP = 80
SMOKE_REPLICATES = 2
HOME_PORT = "HOME"
BASE_CALLS = 3
MAX_LOG_MDHR = math.log(np.finfo(float).max)

CAVEATS = [
    "Pooled lambda_port is identified only up to the fleet-time effect; per-visit hazards are the reportable per-call number (cite summarize_fleet_hazards / summarize_visit_hazards). The hot/background ratio is the fleet-time-free quantity.",
    "The numpy reference sampler is not NUTS; its intervals are indicative, not calibrated. Any coverage/power number from Engine B inherits that.",
    "Engine A is an information ceiling: other parameters treated as known, no week-to-week fleet-time variation -> widths are optimistic, MDHRs are best case.",
    "Regional-scale numbers are extrapolations: full-scale claims rest on Engine A. The pilot-scale sampler comparison produced narrower intervals with ratio coverage 0.6 versus 0.9 nominal, so it cannot certify calibration and no downward adjustment is applied.",
    "`lambda_background`, `r_onboard`, and ascertainment are assumptions, not fitted from data; MDHR scales roughly as 1/sqrt(expected observed imported cases), so halving assumed ascertainment inflates MDHR accordingly.",
    "The one-week information scaling shortcut is approximately 7-9% optimistic versus explicitly building three weeks in the measured pilot and Alaska checks.",
]


@dataclass(frozen=True)
class SentinelDesign:
    """One stakeholder-brief fleet geometry and generative truth."""

    name: str
    region_label: str
    n_ports: int
    n_ships: int
    n_weeks: int
    calls_per_ship_week: float
    n_passengers: int
    n_crew: int
    pax_ashore_fraction: float
    crew_ashore_fraction: float
    dwell_hours: int
    lambda_background: float
    hot_port_hazard_ratio: float
    lambda_aboard: float
    r_onboard: float
    ascertainment_reporting: float
    ascertainment_care_seeking: float
    ascertainment_testing: float
    voyage_days: int = 7
    fit_scale_ships: int = 8
    fit_scale_weeks: int = 3
    fit_scale_ports: int = 6

    def __post_init__(self) -> None:
        positive = (
            self.n_ports, self.n_ships, self.n_weeks, self.n_passengers,
            self.n_crew, self.dwell_hours, self.voyage_days,
            self.fit_scale_ships, self.fit_scale_weeks, self.fit_scale_ports,
        )
        if any(int(value) <= 0 for value in positive):
            raise ValueError("design sizes and dwell must be positive")
        if self.dwell_hours > 18 or self.calls_per_ship_week <= 0:
            raise ValueError("calls_per_ship_week must be positive and dwell <= 18")
        if self.hot_port_hazard_ratio <= 0.0:
            raise ValueError("hot_port_hazard_ratio must be positive")
        if self.lambda_background <= 0.0 or self.lambda_aboard <= 0.0:
            raise ValueError("hazards must be positive")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "SentinelDesign":
        """Construct a validated design from a preset object."""
        fields = {
            key: raw[key]
            for key in (
                "name", "region_label", "n_ports", "n_ships", "n_weeks",
                "calls_per_ship_week", "n_passengers", "n_crew",
                "pax_ashore_fraction", "crew_ashore_fraction", "dwell_hours",
                "lambda_background", "hot_port_hazard_ratio", "lambda_aboard",
                "r_onboard", "ascertainment_reporting",
                "ascertainment_care_seeking", "ascertainment_testing",
            )
        }
        optional = (
            "voyage_days", "fit_scale_ships", "fit_scale_weeks", "fit_scale_ports",
        )
        fields.update({key: raw[key] for key in optional if key in raw})
        return cls(**fields)

    def evolved(self, **changes: Any) -> "SentinelDesign":
        """Return a copy with selected fields replaced, typed as this class.

        ``dataclasses.replace`` is inferred as a generic dataclass instance, which
        then fails every caller that asks for ``SentinelDesign``. Reconstructing
        through the constructor keeps the public type.
        """
        payload = asdict(self)
        payload.update(changes)
        return SentinelDesign(**payload)

    def fit_design(self) -> "SentinelDesign":
        """Return the explicitly configured sub-scale replica for Engine B."""
        return self.evolved(
            n_ports=self.fit_scale_ports,
            n_ships=self.fit_scale_ships,
            n_weeks=self.fit_scale_weeks,
        )


DesignConfig = SentinelDesign


def _preset_payload(path: str | None) -> Mapping[str, Any]:
    if path is not None:
        payload = read_json(path)
    else:
        raw = resources.files("picard_framework.analysis.sentinel").joinpath(
            "data/design_presets.json",
        ).read_text(encoding="utf-8")
        payload = json.loads(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get("presets"), dict):
        raise ValueError("design presets must contain a presets object")
    return payload["presets"]


def load_presets(path: str | None = None) -> dict[str, SentinelDesign]:
    """Load all design presets, or raise on a malformed preset file."""
    return {
        str(name): SentinelDesign.from_mapping(raw)
        for name, raw in _preset_payload(path).items()
    }


def load_design(name: str, path: str | None = None) -> SentinelDesign:
    """Load one named design preset."""
    presets = load_presets(path)
    if name not in presets:
        raise ValueError(f"unknown design preset: {name}")
    return presets[name]


def _calls_for_voyage(design: SentinelDesign, ship: int, week: int) -> list[str]:
    fraction = Fraction(str(design.calls_per_ship_week))
    count = fraction.numerator // fraction.denominator
    if (ship + week) % fraction.denominator < fraction.numerator % fraction.denominator:
        count += 1
    ports = [f"P{((ship * 2) + (week * 3) + c) % design.n_ports:02d}" for c in range(count)]
    return list(dict.fromkeys(ports))


def _make_voyage(
    design: SentinelDesign,
    *,
    ship: int,
    week: int,
    calls: Sequence[str],
    incubation: Any,
) -> FleetVoyage:
    itinerary: list[dict[str, Any]] = [
        {"day": 1, "type": "embarkation", "port": "Home", "port_id": HOME_PORT},
    ]
    call_days = set(range(2, 2 + len(calls)))
    for day in range(2, design.voyage_days):
        if day in call_days:
            port_id = calls[day - 2]
            itinerary.append(
                {
                    "day": day,
                    "type": "port_day",
                    "port": port_id,
                    "port_id": port_id,
                    "disembark_fraction": design.pax_ashore_fraction,
                    "crew_shore_leave_fraction": design.crew_ashore_fraction,
                    "disembark_window_epochs": [2, 2],
                    "reembark_window_epochs": [2 + design.dwell_hours, 2 + design.dwell_hours],
                },
            )
        else:
            itinerary.append({"day": day, "type": "sea_day"})
    itinerary.append(
        {"day": design.voyage_days, "type": "disembarkation", "port": "Home", "port_id": HOME_PORT},
    )
    total_epochs = design.voyage_days * 24
    voyage_id = f"S{ship}W{week}"
    config = {
        "voyage": {
            "effects_enabled": True,
            "total_epochs": total_epochs,
            "epoch_duration_hours": 1,
            "embarkation_date": (START_DATE + timedelta(days=7 * week)).isoformat(),
            "itinerary": itinerary,
        },
    }
    voyage = voyage_from_config(
        config,
        voyage_id=voyage_id,
        ship_id=f"ship{ship}",
        n_passengers=design.n_passengers,
        n_crew=design.n_crew,
    )
    bundle = bundle_from_dict(
        {
            "voyage_id": voyage_id,
            "ship_id": f"ship{ship}",
            "n_passengers": design.n_passengers,
            "n_crew": design.n_crew,
            "observation_end_epoch": total_epochs,
            "clinical_cases": [],
            "wastewater_samples": [],
        },
    )
    exposure = build_exposure_design(
        voyage,
        bundle,
        incubation,
        ascertainment=ascertainment_fraction(
            reporting=design.ascertainment_reporting,
            care_seeking=design.ascertainment_care_seeking,
            testing=design.ascertainment_testing,
        ),
    )
    return FleetVoyage(design=exposure, voyage=voyage, bundle=bundle)


def build_synthetic_fleet(design: SentinelDesign) -> list[FleetVoyage]:
    """Build the crossover fleet using the prototype's itinerary pattern."""
    incubation, _ = delays_for_pathogen(default_pathogen(), epoch_hours=1.0)
    voyages = []
    for ship in range(design.n_ships):
        for week in range(design.n_weeks):
            calls = _calls_for_voyage(design, ship, week)
            voyages.append(
                _make_voyage(
                    design,
                    ship=ship,
                    week=week,
                    calls=calls,
                    incubation=incubation,
                ),
            )
    return voyages


def build_design_data(
    design: SentinelDesign,
    *,
    one_week: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build fleet Stan data, optionally retaining one exchangeable week."""
    actual = design.evolved(n_weeks=1) if one_week else design
    incubation, generation = delays_for_pathogen(default_pathogen(), epoch_hours=1.0)
    return build_sentinel_fleet_data(
        build_synthetic_fleet(actual),
        incubation,
        generation,
    )


def _truth_rates(data: Mapping[str, Any], design: SentinelDesign, ratio: float | None = None) -> FleetRates:
    hot_ratio = design.hot_port_hazard_ratio if ratio is None else ratio
    visits = np.asarray(data["visit_port"], dtype=int)
    hazards = np.where(
        visits == 1,
        design.lambda_background * hot_ratio,
        design.lambda_background,
    )
    return FleetRates(
        lambda_visit=hazards.tolist(),
        lambda_aboard=[design.lambda_aboard] * int(data["S"]),
        r_onboard=[design.r_onboard] * int(data["S"]),
    )


def _flatten_expected(data: Mapping[str, Any], rates: FleetRates) -> np.ndarray:
    expected = expected_onsets_fleet(data, rates)
    return np.concatenate(
        [np.asarray(mu, dtype=float)[:, : int(data["T"][i])].ravel() for i, mu in enumerate(expected)],
    )


def _information(data: Mapping[str, Any], design: SentinelDesign, ratio: float) -> np.ndarray:
    base = _truth_rates(data, design, ratio)
    mu0 = _flatten_expected(data, base)
    ports = np.asarray(data["visit_port"], dtype=int)
    hot = ports == 1
    background = ~hot

    def shifted(mask: np.ndarray, sign: float) -> np.ndarray:
        values = np.asarray(base.lambda_visit, dtype=float).copy()
        values[mask] *= math.exp(sign * FINITE_DIFFERENCE_LOG_STEP)
        return _flatten_expected(
            data,
            FleetRates(values, base.lambda_aboard, base.r_onboard),
        )

    d_hot = (shifted(hot, 1.0) - shifted(hot, -1.0)) / (2.0 * FINITE_DIFFERENCE_LOG_STEP)
    d_background = (
        shifted(background, 1.0) - shifted(background, -1.0)
    ) / (2.0 * FINITE_DIFFERENCE_LOG_STEP)
    valid = mu0 > 1.0e-12
    return np.array(
        [
            [np.sum(d_hot[valid] ** 2 / mu0[valid]), np.sum(d_hot[valid] * d_background[valid] / mu0[valid])],
            [np.sum(d_hot[valid] * d_background[valid] / mu0[valid]), np.sum(d_background[valid] ** 2 / mu0[valid])],
        ],
        dtype=float,
    )


def _mdhr(
    design: SentinelDesign,
    data: Mapping[str, Any],
    *,
    alpha: float,
    power: float,
    inflation: float | None,
) -> tuple[float, list[float], float | None]:
    z_alpha = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    z_power = NormalDist().inv_cdf(power)
    ratio = design.hot_port_hazard_ratio
    trace = [ratio]
    for _ in range(3):
        info = _information(data, design, ratio) * design.n_weeks
        covariance = np.linalg.inv(info)
        contrast_sd = math.sqrt(float(np.array([1.0, -1.0]) @ covariance @ np.array([1.0, -1.0])))
        ratio = math.exp(min((z_alpha + z_power) * contrast_sd, MAX_LOG_MDHR))
        trace.append(ratio)
    inflated = None if inflation is None else math.exp(inflation * math.log(ratio))
    return ratio, trace, inflated


def ceiling_projection(
    design: SentinelDesign,
    *,
    alpha: float = DEFAULT_ALPHA,
    power: float = DEFAULT_POWER,
    posterior_width_ratio_vs_ceiling: float | None = None,
) -> dict[str, Any]:
    """Compute Engine A at the design's full scale."""
    data, meta = build_design_data(design, one_week=True)
    info = _information(data, design, design.hot_port_hazard_ratio) * design.n_weeks
    covariance = np.linalg.inv(info)
    sd_hot = math.sqrt(float(covariance[0, 0]))
    sd_ratio = math.sqrt(float(np.array([1.0, -1.0]) @ covariance @ np.array([1.0, -1.0])))
    mdhr, trace, _ = _mdhr(
        design,
        data,
        alpha=alpha,
        power=power,
        inflation=posterior_width_ratio_vs_ceiling,
    )
    voyage_calls_per_port = (
        design.n_ships * design.n_weeks * design.calls_per_ship_week / design.n_ports
    )
    realized_hot_visits = int(np.count_nonzero(np.asarray(data["visit_port"]) == 1))
    adjusted_ratio = (
        None
        if posterior_width_ratio_vs_ceiling is None
        else max(1.0, posterior_width_ratio_vs_ceiling)
    )
    adjusted_mdhr = None if adjusted_ratio is None else math.exp(adjusted_ratio * math.log(mdhr))
    adjustment_applied = (
        None
        if posterior_width_ratio_vs_ceiling is None
        else posterior_width_ratio_vs_ceiling >= 1.0
    )
    return {
        "engine": "ceiling",
        "provenance": "Engine A analytic Fisher-information ceiling",
        "design": design.name,
        "sd_log_lambda_hot": sd_hot,
        "width90_log_lambda": 2.0 * Z90 * sd_hot,
        "sd_log_ratio": sd_ratio,
        "mdhr": mdhr,
        "mdhr_iteration_trace": trace,
        "mdhr_adjusted": adjusted_mdhr,
        "adjustment_applied": adjustment_applied,
        "adjustment_explanation": (
            None
            if posterior_width_ratio_vs_ceiling is None
            else "A ratio below 1 with under-nominal coverage means sampler intervals are too narrow; the ceiling MDHR is not conservative in that regime."
        ),
        "information": info.tolist(),
        "information_positive_definite": bool(np.linalg.eigvalsh(info).min() > 0.0),
        "n_voyages": int(data["V"]) * design.n_weeks,
        "voyage_calls_per_port": voyage_calls_per_port,
        "realized_hot_port_visit_count": realized_hot_visits * design.n_weeks,
        "meta": {"ports": meta["ports"], "visits": len(meta["visits"])},
        "caveats": list(CAVEATS),
    }


def week_scaling_check(design: SentinelDesign) -> dict[str, float | int]:
    """Compare one-week information scaling with an explicit small fleet."""
    explicit_weeks = min(3, design.n_weeks)
    check_design = design.evolved(n_weeks=explicit_weeks)
    one_week, _ = build_design_data(check_design, one_week=True)
    all_weeks, _ = build_design_data(check_design)
    scaled_info = _information(one_week, check_design, check_design.hot_port_hazard_ratio)
    exact_info = _information(all_weeks, check_design, check_design.hot_port_hazard_ratio)
    scaled_covariance = np.linalg.inv(scaled_info * explicit_weeks)
    exact_covariance = np.linalg.inv(exact_info)
    scaled_sd = math.sqrt(float(scaled_covariance[0, 0]))
    exact_sd = math.sqrt(float(exact_covariance[0, 0]))
    return {
        "explicit_weeks": explicit_weeks,
        "sd_log_lambda_hot_scaled": scaled_sd,
        "sd_log_lambda_hot_explicit": exact_sd,
        "scaled_to_explicit_ratio": scaled_sd / exact_sd,
    }


def _interval(values: Sequence[float]) -> tuple[float, float]:
    arr = np.asarray(values, dtype=float)
    return float(np.quantile(arr, 0.05)), float(np.quantile(arr, 0.95))


def _coverage(values: Sequence[float], truth: float) -> bool:
    low, high = _interval(values)
    return low <= truth <= high


def _fit_replicate(
    data: Mapping[str, Any],
    design: SentinelDesign,
    *,
    seed: int,
    draws: int,
    warmup: int,
    hot_ratio: float,
) -> dict[str, Any]:
    mu = expected_onsets_fleet(data, _truth_rates(data, design, hot_ratio))
    rng = np.random.default_rng(seed)
    onsets = []
    for voyage, means in enumerate(mu):
        padded = np.zeros((means.shape[0], int(data["Tmax"])), dtype=int)
        padded[:, : int(data["T"][voyage])] = rng.poisson(means)
        onsets.append(padded.tolist())
    simulated = dict(data)
    simulated["onsets"] = onsets
    posterior = fleet_reference_posterior(simulated, draws=draws, warmup=warmup, seed=seed + 1000)
    hot = np.asarray(posterior["lambda_port[1]"], dtype=float)
    background = np.column_stack(
        [posterior[f"lambda_port[{i}]"] for i in range(2, int(data["P"]) + 1)],
    )
    ratio = hot / np.exp(np.mean(np.log(np.maximum(background, 1.0e-18)), axis=1))
    ratio_low, ratio_high = _interval(ratio)
    return {
        "hot_width90_log": float(np.log(_interval(hot)[1]) - np.log(_interval(hot)[0])),
        "background_width90_log": float(np.log(_interval(background[:, 0])[1]) - np.log(_interval(background[:, 0])[0])),
        "pooled_lambda_hot_coverage": _coverage(hot, design.lambda_background * hot_ratio),
        "pooled_lambda_background_coverage": _coverage(background[:, 0], design.lambda_background),
        "ratio_width90_log": float(math.log(ratio_high) - math.log(ratio_low)),
        "ratio_coverage": ratio_low <= hot_ratio <= ratio_high,
        "detected": ratio_low > 1.0,
    }


def fit_projection(
    design: SentinelDesign,
    *,
    draws: int = DEFAULT_DRAWS,
    warmup: int = DEFAULT_WARMUP,
    replicates: int = DEFAULT_REPLICATES,
    seed: int = 1701,
    alpha: float = DEFAULT_ALPHA,
    power: float = DEFAULT_POWER,
    hot_ratio: float | None = None,
) -> dict[str, Any]:
    """Simulate and fit the fit-scale replica with the reference sampler."""
    truth_ratio = design.hot_port_hazard_ratio if hot_ratio is None else hot_ratio
    fit_design = design.fit_design().evolved(hot_port_hazard_ratio=truth_ratio)
    data, meta = build_design_data(fit_design)
    ceiling = ceiling_projection(fit_design, alpha=alpha, power=power)
    results = [
        _fit_replicate(
            data,
            fit_design,
            seed=seed + i,
            draws=draws,
            warmup=warmup,
            hot_ratio=truth_ratio,
        )
        for i in range(replicates)
    ]
    widths = np.asarray([row["ratio_width90_log"] for row in results], dtype=float)
    ceiling_width = ceiling["sd_log_ratio"] * 2.0 * Z90
    inflation = float(widths.mean() / ceiling_width)
    regional_ceiling = ceiling_projection(
        design.evolved(hot_port_hazard_ratio=truth_ratio),
        alpha=alpha,
        power=power,
        posterior_width_ratio_vs_ceiling=inflation,
    )
    return {
        "engine": "fit",
        "provenance": "Engine B numpy reference sampler at fit scale",
        "design": design.name,
        "true_hot_ratio": truth_ratio,
        "fit_scale": {"ships": fit_design.n_ships, "weeks": fit_design.n_weeks, "ports": fit_design.n_ports},
        "draws": draws,
        "warmup": warmup,
        "n_replicates": replicates,
        "replicates": results,
        "realized_width90_log_lambda_hot_mean": float(
            np.mean([r["hot_width90_log"] for r in results]),
        ),
        "realized_width90_log_lambda_background_mean": float(
            np.mean([r["background_width90_log"] for r in results]),
        ),
        "realized_width90_log_ratio_mean": float(widths.mean()),
        "coverage_pooled_lambda_hot_truth": float(
            np.mean([r["pooled_lambda_hot_coverage"] for r in results]),
        ),
        "coverage_pooled_lambda_background_truth": float(
            np.mean([r["pooled_lambda_background_coverage"] for r in results]),
        ),
        "nominal_interval_coverage": 0.90,
        "coverage_gap": 0.90 - float(np.mean([r["ratio_coverage"] for r in results])),
        "coverage_hot_background_ratio_truth": float(np.mean([r["ratio_coverage"] for r in results])),
        "detection_power": float(np.mean([r["detected"] for r in results])),
        "posterior_width_ratio_vs_ceiling": inflation,
        "ceiling_same_fit_scale": ceiling,
        "regional_mdhr_adjusted": regional_ceiling["mdhr_adjusted"],
        "regional_adjustment_applied": regional_ceiling["adjustment_applied"],
        "regional_adjustment_explanation": regional_ceiling["adjustment_explanation"],
        "week_scaling_check": week_scaling_check(fit_design),
        "fleet_time_confounded_ports": sorted(fleet_time_confounded_ports(meta)),
        "caveats": list(CAVEATS),
    }


def _sweep_design(
    design: SentinelDesign,
    dimension: str,
    value: float,
) -> SentinelDesign:
    if dimension == "ships":
        return design.evolved(n_ships=int(value))
    if dimension == "weeks":
        return design.evolved(n_weeks=int(value))
    if dimension == "calls":
        return design.evolved(calls_per_ship_week=float(value))
    raise ValueError(f"unknown sweep dimension: {dimension}")


def scaling_sweep(
    design: SentinelDesign,
    dimension: str,
    values: Sequence[float],
    *,
    alpha: float = DEFAULT_ALPHA,
    power: float = DEFAULT_POWER,
) -> list[dict[str, Any]]:
    """Rebuild one-week fleets while varying one design dimension."""
    rows = []
    for value in values:
        candidate = _sweep_design(design, dimension, value)
        result = ceiling_projection(candidate, alpha=alpha, power=power)
        rows.append(
            {
                "design": design.name,
                "dimension": dimension,
                "value": value,
                "sd_log_lambda_hot": result["sd_log_lambda_hot"],
                "width90_log_lambda": result["width90_log_lambda"],
                "sd_log_ratio": result["sd_log_ratio"],
                "mdhr": result["mdhr"],
                "provenance": result["provenance"],
            },
        )
    return rows
