"""Paired-seed invariance + baseline agreement for the role-checkpoint sidecar.

Two distinct checks (PAPER1-SENS Child A), both local and few-seed:

1. **Paired replay, emitter off vs on, same implementation.** Every venue02
   tier spec is run twice through the campaign worker's own ``run_seed``
   (``tools/noro_diag/growth_chain_census.py``) with only
   ``config_overrides.role_checkpoints.enabled`` flipped. The voyage blocks
   (``summary``, ``timeseries``, ``derived``, ``cost_accounting``,
   ``parameters``, ``trigger_status``), the census payload and the
   initiation witness must be canonically identical once the ``on`` arm's
   ``role_checkpoints`` block is removed; the ``off`` arm must carry no such
   block. A direct ``ShipSimulation`` pair additionally records the final
   RNG bit-generator state on both arms (no added draws).

2. **Baseline agreement.** The ``on`` arm's voyage blocks are compared with
   the same seeds run by the delivered venue02 implementation
   (``--baseline-dir``: zips produced by a checkout at SHA 526cf856). Leaf
   differences are classified: two floats within ``FLOAT_DRIFT_REL_TOL``
   relative are ``float_drift`` (recorded, reported, not a disagreement);
   anything else is ``material`` and fails the check. Separately,
   the day-12 (terminal) checkpoint counts are compared with the
   ``summary`` endpoints both arms emit (``cumulative_ever_infected_*``,
   ``cumulative_ever_ill_*``, ``cumulative_reported_cases_*``,
   ``cumulative_reported_noise_cases``).

Writes one JSON ledger; exit 0 only when every check passes.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
_CAMPAIGN_DIR = REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
if str(_CAMPAIGN_DIR) not in sys.path:
    sys.path.insert(0, str(_CAMPAIGN_DIR))

from campaign_runner import generate_tier_runs  # noqa: E402

from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from tools.diag.instrument_common import materialized_picard_spec  # noqa: E402
from tools.noro_diag.growth_chain_census import (  # noqa: E402
    _load_manifest,
    filter_runs_by_seeds,
    run_seed,
)

VOLATILE_META = ("wall_clock_s", "voyage_rss_mb", "fold_rss_mb")
ENDPOINT_PAIRS = (
    ("infected", "cumulative_ever_infected_{role}"),
    ("ill", "cumulative_ever_ill_{role}"),
    ("unique_etiologic_reporters", "cumulative_reported_cases_{role}"),
)


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


FLOAT_DRIFT_REL_TOL = 1e-6


def _diff_paths(a: Any, b: Any, prefix: str = "",
                out: list[dict[str, Any]] | None = None,
                limit: int = 200) -> list[dict[str, Any]]:
    """Leaf-level differences as ``{path, a, b, kind}``.

    ``kind`` is ``float_drift`` when both leaves are floats within
    ``FLOAT_DRIFT_REL_TOL`` relative (a summation-order / dispatch-level
    move, recorded but not an epidemiological disagreement) and
    ``material`` otherwise.
    """
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                out.append({"path": f"{prefix}/{key}", "a": a.get(key),
                            "b": b.get(key), "kind": "material"})
            else:
                _diff_paths(a[key], b[key], f"{prefix}/{key}", out, limit)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append({"path": prefix, "a": len(a), "b": len(b),
                        "kind": "material"})
        for i, (x, y) in enumerate(zip(a, b)):
            _diff_paths(x, y, f"{prefix}[{i}]", out, limit)
    elif a != b and _canon(a) != _canon(b):
        out.append({"path": prefix, "a": a, "b": b, "kind": _leaf_kind(a, b)})
    return out


def _leaf_kind(a: Any, b: Any) -> str:
    if isinstance(a, float) and isinstance(b, float):
        scale = max(abs(a), abs(b), 1e-300)
        if abs(a - b) / scale < FLOAT_DRIFT_REL_TOL:
            return "float_drift"
    return "material"


def _material(diffs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [d for d in diffs if d["kind"] == "material"]


def _with_emitter(spec: dict[str, Any], enabled: bool) -> dict[str, Any]:
    out = copy.deepcopy(spec)
    out.setdefault("config_overrides", {})["role_checkpoints"] = {
        "enabled": enabled, "days": [3, 7, 10, 12],
    }
    return out


def _strip_meta(payload: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(payload)
    for key in VOLATILE_META:
        out.get("meta", {}).pop(key, None)
    return out


def _rng_witness(spec: dict[str, Any]) -> dict[str, Any]:
    """Direct ShipSimulation pair: final RNG state + history equality."""
    states: dict[str, Any] = {}
    histories: dict[str, Any] = {}
    for arm in ("off", "on"):
        with materialized_picard_spec(_with_emitter(spec, arm == "on"), REPO_ROOT) as ps:
            sim = ShipSimulation(ps, display=False)
            result = sim.run()
        states[arm] = _canon(sim.rng.bit_generator.state)
        hist = copy.deepcopy(result.history)
        if arm == "on":
            hist[-1].pop("role_checkpoints", None)
        histories[arm] = _canon(hist)
    return {
        "rng_state_equal": states["off"] == states["on"],
        "history_equal_minus_sidecar": histories["off"] == histories["on"],
    }


def _endpoint_agreement(block: dict[str, Any], summary: dict[str, Any],
                        terminal_day: int) -> dict[str, Any]:
    cp = block["checkpoints"].get(f"day_{terminal_day}", {})
    checks: dict[str, Any] = {"available": cp.get("available")}
    ok = bool(cp.get("available"))
    for role in ("passenger", "crew"):
        for measure, template in ENDPOINT_PAIRS:
            key = template.format(role=role)
            emitted, baseline = cp[role][measure], summary.get(key)
            checks[f"{role}.{measure}=={key}"] = [emitted, baseline]
            ok &= emitted == baseline
        comp = summary.get(f"{role}_complement")
        checks[f"{role}.complement"] = [cp[role]["complement"], comp]
        ok &= cp[role]["complement"] == comp
    noise = cp["all"]["unique_clinical_noise_reporters"]
    checks["all.noise==cumulative_reported_noise_cases"] = [
        noise, summary.get("cumulative_reported_noise_cases"),
    ]
    ok &= noise == summary.get("cumulative_reported_noise_cases")
    checks["agree"] = ok
    return checks


def _baseline_zip(baseline_dir: Path | None, tier: str, seed: int) -> Path | None:
    if baseline_dir is None:
        return None
    hits = sorted((baseline_dir / tier).glob(f"*_s{seed}.zip"))
    return hits[0] if hits else None


def _baseline_compare(path: Path, voyage: dict[str, Any], payload: dict[str, Any],
                      block: dict[str, Any]) -> dict[str, Any]:
    with zipfile.ZipFile(path) as zf:
        base = json.loads(zf.read("summary.json"))
    diffs: dict[str, list[str]] = {}
    for key in ("summary", "timeseries", "derived", "cost_accounting", "trigger_status"):
        diffs[key] = _diff_paths(base.get(key), voyage.get(key))
    census = {
        "ignited": payload["ignited"], "n_imports": payload["n_imports"],
        "n_acquired": payload["n_acquired"],
        "acquisitions_by_gen": payload["acquisitions_by_gen"],
    }
    diffs["census"] = _diff_paths(base.get("census"), census)
    flat = [d | {"block": k} for k, v in diffs.items() for d in v]
    return {
        "zip": str(path),
        "baseline_has_sidecar": "role_checkpoints" in base,
        "blocks_equal": not flat,
        "blocks_equal_modulo_float_drift": not _material(flat),
        "n_float_drift_leaves": len(flat) - len(_material(flat)),
        "float_drift_paths": sorted({d["block"] + d["path"].split("[")[0]
                                     for d in flat if d["kind"] != "material"}),
        "diffs": flat[:40],
        "day12_vs_baseline_summary": _endpoint_agreement(block, base["summary"], 12),
    }


def check_run(tier: str, run_id: str, spec: dict[str, Any], *, pathogen_id: str,
              clock: str | None, baseline_dir: Path | None,
              rng_witness: bool) -> dict[str, Any]:
    seed = int(spec["run"]["random_seed"])
    arms: dict[str, tuple[dict, dict, dict]] = {}
    for arm in ("off", "on"):
        arms[arm] = run_seed(
            pathogen_id=pathogen_id, spec_dict=_with_emitter(spec, arm == "on"),
            natural_history_clock=clock, payload_profile="lean",
        )
    payload_off, voyage_off, init_off = arms["off"]
    payload_on, voyage_on, init_on = arms["on"]
    voyage_on = copy.deepcopy(voyage_on)
    block = voyage_on.pop("role_checkpoints", None)
    rec: dict[str, Any] = {
        "tier": tier, "run_id": run_id, "seed": seed,
        "off_has_sidecar": "role_checkpoints" in voyage_off,
        "on_has_sidecar": block is not None,
        "voyage_equal": _canon(voyage_off) == _canon(voyage_on),
        "census_equal": _canon(_strip_meta(payload_off)) == _canon(_strip_meta(payload_on)),
        "initiation_equal": _canon(init_off) == _canon(init_on),
        "voyage_diffs": _diff_paths(voyage_off, voyage_on),
        "census_diffs": _diff_paths(_strip_meta(payload_off), _strip_meta(payload_on)),
    }
    if block is not None:
        rec["epoch_mapping"] = block["clock"]["epoch_mapping"]
        rec["day12_vs_own_summary"] = _endpoint_agreement(block, voyage_on["summary"], 12)
        rec["checkpoints"] = {
            day: {role: cp[role] for role in ("passenger", "crew", "all")}
            | {"epoch_index": cp["epoch_index"], "available": cp["available"]}
            for day, cp in block["checkpoints"].items()
        }
        bz = _baseline_zip(baseline_dir, tier, seed)
        rec["baseline"] = (
            _baseline_compare(bz, voyage_on, payload_on, block) if bz else None
        )
    if rng_witness:
        rec["rng_witness"] = _rng_witness(spec)
    rec["pass"] = _passes(rec)
    print(json.dumps({k: rec[k] for k in ("tier", "seed", "pass", "voyage_equal",
                                          "census_equal")}), flush=True)
    return rec


def _passes(rec: dict[str, Any]) -> bool:
    ok = (
        not rec["off_has_sidecar"] and rec["on_has_sidecar"]
        and rec["voyage_equal"] and rec["census_equal"] and rec["initiation_equal"]
        and rec["day12_vs_own_summary"]["agree"]
    )
    if rec.get("baseline") is not None:
        ok &= rec["baseline"]["blocks_equal_modulo_float_drift"]
        ok &= rec["baseline"]["day12_vs_baseline_summary"]["agree"]
    if rec.get("rng_witness") is not None:
        ok &= all(rec["rng_witness"].values())
    return bool(ok)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--tier", action="append", required=True)
    p.add_argument("--seeds", type=int, nargs="+", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--baseline-dir", type=Path, default=None)
    p.add_argument("--pathogen-id", default="norwalk_gi")
    p.add_argument("--rng-witness-tier", action="append", default=[])
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = _load_manifest(args.manifest)
    clock = manifest.get("natural_history_clock")
    clock = str(clock) if clock is not None else None
    records = []
    for tier in args.tier:
        runs = filter_runs_by_seeds(
            list(generate_tier_runs(manifest, tier, natural_history_clock=clock)),
            args.seeds,
        )
        for run_id, spec in runs:
            records.append(check_run(
                tier, run_id, spec, pathogen_id=args.pathogen_id, clock=clock,
                baseline_dir=args.baseline_dir,
                rng_witness=tier in args.rng_witness_tier,
            ))
    ledger = {
        "manifest": str(args.manifest), "tiers": args.tier, "seeds": args.seeds,
        "baseline_dir": str(args.baseline_dir) if args.baseline_dir else None,
        "n_runs": len(records), "all_pass": all(r["pass"] for r in records),
        "runs": records,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(ledger, indent=1, sort_keys=True) + "\n")
    print(f"written: {args.out} all_pass={ledger['all_pass']}")
    return 0 if ledger["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
