"""Fit the Phase-1 norovirus trajectory Stan model on an analysis bundle.

Usage::

    python3 -m picard_framework.analysis.stan.fit_norovirus_trajectory analysis/ --out stan_fit/
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sys
from typing import Any

from picard_framework.analysis._io import (
    allowed_roots,
    ensure_out_dir,
    safe_path,
    write_json,
)
from picard_framework.analysis.metrics import encode_trigger_status
from picard_framework.analysis.parse_run_id import is_norovirus
from picard_framework.analysis.stan.posterior_summaries import summarize_fit
from simulation_utils.paths import validated_open

DEFAULT_D0 = 10.6
DEFAULT_VSP_REF = 0.05


def _read_csv(path: str) -> list[dict[str, Any]]:
    with validated_open(
        path, allowed_roots=allowed_roots(), encoding="utf-8", newline=""
    ) as fh:
        return list(csv.DictReader(fh))


def _read_epoch_table(analysis_dir: str) -> list[dict[str, Any]]:
    parquet_path = os.path.join(analysis_dir, "epoch_timeseries.parquet")
    gz_path = os.path.join(analysis_dir, "epoch_timeseries.csv.gz")
    csv_path = os.path.join(analysis_dir, "epoch_timeseries.csv")

    if os.path.isfile(parquet_path):
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq

            with validated_open(parquet_path, "rb", allowed_roots=allowed_roots()) as fh:
                data = fh.read()
            table = pq.read_table(pa.BufferReader(data))
            return table.to_pylist()
        except ImportError:
            pass

    if os.path.isfile(gz_path):
        with validated_open(gz_path, "rb", allowed_roots=allowed_roots()) as raw:
            with gzip.GzipFile(fileobj=raw, mode="rb") as gz:
                text = gz.read().decode("utf-8").splitlines()
        return list(csv.DictReader(text))

    if os.path.isfile(csv_path):
        return _read_csv(csv_path)

    raise FileNotFoundError(
        f"No epoch_timeseries table under {analysis_dir} "
        "(expected .parquet, .csv.gz, or .csv)"
    )


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def filter_norovirus_runs(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep rows whose pathogen labels indicate norovirus."""
    return [
        r
        for r in run_rows
        if is_norovirus(r.get("pathogen"), r.get("pathogen_id"))
    ]


def build_stan_data(
    run_rows: list[dict[str, Any]],
    epoch_rows: list[dict[str, Any]],
    *,
    d0: float = DEFAULT_D0,
    vsp_ref: float = DEFAULT_VSP_REF,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build Stan data dict + metadata from bundle tables (norovirus only)."""
    noro = filter_norovirus_runs(run_rows)
    if not noro:
        raise ValueError("No norovirus runs found in run_summary")

    run_ids = [str(r["run_id"]) for r in noro]
    run_index = {rid: i for i, rid in enumerate(run_ids)}

    platforms = sorted({str(r.get("platform_id") or "unknown") for r in noro})
    surveillances = sorted(
        {str(r.get("surveillance_strategy") or "none") for r in noro}
    )
    plat_idx = {p: i + 1 for i, p in enumerate(platforms)}
    surv_idx = {s: i + 1 for i, s in enumerate(surveillances)}

    # Determine T as max epoch+1 among selected runs
    epochs_by_run: dict[str, dict[int, dict[str, Any]]] = {rid: {} for rid in run_ids}
    max_epoch = 0
    for row in epoch_rows:
        rid = str(row.get("run_id"))
        if rid not in run_index:
            continue
        ep = _as_int(row.get("epoch"), -1)
        if ep < 0:
            continue
        epochs_by_run[rid][ep] = row
        max_epoch = max(max_epoch, ep)
    T = max_epoch + 1
    if T < 1:
        raise ValueError("No epoch rows for norovirus runs")

    N_runs = len(noro)
    N_agents = [_as_int(r.get("num_agents"), 1) for r in noro]
    platform = [plat_idx[str(r.get("platform_id") or "unknown")] for r in noro]
    surveillance = [
        surv_idx[str(r.get("surveillance_strategy") or "none")] for r in noro
    ]
    dose_adj = [_as_float(r.get("dose_adjustment"), d0) for r in noro]
    vsp_threshold = []
    for r in noro:
        thr = r.get("vsp_lockdown_threshold")
        if thr in (None, "", "never"):
            vsp_threshold.append(1.0)  # "off" sentinel (>= 1)
        else:
            vsp_threshold.append(_as_float(thr, 1.0))
    seeds = [_as_int(r.get("seed"), 0) for r in noro]

    def _mat(field: str, default: int = 0) -> list[list[int]]:
        mat = [[default for _ in range(T)] for _ in range(N_runs)]
        for rid, by_ep in epochs_by_run.items():
            ri = run_index[rid]
            for t in range(T):
                point = by_ep.get(t)
                if point is None:
                    continue
                if field == "trigger_state":
                    if "trigger_state" in point and point["trigger_state"] != "":
                        mat[ri][t] = _as_int(point["trigger_state"], 0)
                    else:
                        mat[ri][t] = encode_trigger_status(point.get("trigger_status"))
                else:
                    mat[ri][t] = _as_int(point.get(field), default)
        return mat

    data = {
        "N_runs": N_runs,
        "T": T,
        "P": len(platforms),
        "S": len(surveillances),
        "N_agents": N_agents,
        "platform": platform,
        "surveillance": surveillance,
        "dose_adj": dose_adj,
        "vsp_threshold": vsp_threshold,
        "seed": seeds,
        "infected": _mat("infected"),
        "symptomatic": _mat("symptomatic"),
        "recovered": _mat("recovered"),
        "new_infections": _mat("new_infections"),
        "quarantined": _mat("quarantined"),
        "trigger_state": _mat("trigger_state"),
        "d0": float(d0),
        "vsp_ref": float(vsp_ref),
    }
    meta = {
        "platforms": platforms,
        "surveillances": surveillances,
        "run_ids": run_ids,
        "d0": float(d0),
        "vsp_ref": float(vsp_ref),
        "N_runs": N_runs,
        "T": T,
    }
    return data, meta


def _cmdstan_available() -> bool:
    try:
        import cmdstanpy  # noqa: F401
        from cmdstanpy import cmdstan_path

        try:
            cmdstan_path()
            return True
        except Exception:
            return False
    except ImportError:
        return False


def fit_model(
    analysis_dir: str,
    out_dir: str,
    *,
    chains: int = 2,
    iter_sampling: int = 200,
    iter_warmup: int = 200,
    seed: int = 42,
    d0: float = DEFAULT_D0,
    vsp_ref: float = DEFAULT_VSP_REF,
) -> dict[str, Any]:
    """Compile/fit the Stan model and write posterior summaries."""
    analysis_dir = safe_path(analysis_dir)
    out = ensure_out_dir(out_dir)

    run_rows = _read_csv(os.path.join(analysis_dir, "run_summary.csv"))
    epoch_rows = _read_epoch_table(analysis_dir)
    data, meta = build_stan_data(run_rows, epoch_rows, d0=d0, vsp_ref=vsp_ref)

    write_json(os.path.join(out, "stan_data_meta.json"), meta)
    # Persist a compact JSON of shapes (not full matrices) for debugging.
    write_json(
        os.path.join(out, "stan_data_shapes.json"),
        {
            "N_runs": data["N_runs"],
            "T": data["T"],
            "P": data["P"],
            "S": data["S"],
            "platforms": meta["platforms"],
            "surveillances": meta["surveillances"],
        },
    )

    if not _cmdstan_available():
        write_json(
            os.path.join(out, "fit_status.json"),
            {
                "status": "skipped",
                "reason": "cmdstanpy/CmdStan not installed",
                "hint": "pip install 'crusher-to-the-bridge[analysis]' && "
                "python -c 'import cmdstanpy; cmdstanpy.install_cmdstan()'",
            },
        )
        print(
            "CmdStan not available; wrote stan data metadata only. "
            "Install analysis extra + CmdStan to fit.",
            file=sys.stderr,
        )
        return {"status": "skipped", "meta": meta}

    from cmdstanpy import CmdStanModel

    stan_file = os.path.join(os.path.dirname(__file__), "norovirus_trajectory.stan")
    model = CmdStanModel(stan_file=stan_file)
    fit = model.sample(
        data=data,
        chains=chains,
        iter_sampling=iter_sampling,
        iter_warmup=iter_warmup,
        seed=seed,
        show_progress=False,
    )

    # Persist draws CSV via cmdstanpy → validated_open
    draws_path = os.path.join(out, "draws.csv")
    try:
        import io

        buf = io.StringIO()
        fit.draws_pd().to_csv(buf, index=False)
        with validated_open(
            draws_path, "w", allowed_roots=allowed_roots(), encoding="utf-8"
        ) as fh:
            fh.write(buf.getvalue())
    except Exception:
        pass

    noro_rows = filter_norovirus_runs(run_rows)
    artifacts = summarize_fit(
        fit=fit,
        meta=meta,
        out_dir=out,
        run_summary_rows=noro_rows,
    )
    status = {"status": "ok", "artifacts": artifacts, "meta": meta}
    write_json(os.path.join(out, "fit_status.json"), status)
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fit norovirus_trajectory.stan on a campaign analysis bundle",
    )
    parser.add_argument("analysis_dir", help="Bundle directory from campaign_bundle")
    parser.add_argument(
        "--out",
        default="stan_fit",
        help="Output directory for Stan fit / posterior (default: stan_fit/)",
    )
    parser.add_argument("--chains", type=int, default=2)
    parser.add_argument("--iter-sampling", type=int, default=200)
    parser.add_argument("--iter-warmup", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--d0", type=float, default=DEFAULT_D0)
    parser.add_argument("--vsp-ref", type=float, default=DEFAULT_VSP_REF)
    args = parser.parse_args(argv)

    result = fit_model(
        args.analysis_dir,
        args.out,
        chains=args.chains,
        iter_sampling=args.iter_sampling,
        iter_warmup=args.iter_warmup,
        seed=args.seed,
        d0=args.d0,
        vsp_ref=args.vsp_ref,
    )
    print(json.dumps({"status": result.get("status"), "out": args.out}))
    return 0 if result.get("status") in {"ok", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
