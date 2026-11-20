#!/usr/bin/env python3
"""TRANSPORT-FIT-01 paired descriptive readout: native vs ContamX, per seed.

Standard library only. Two commands:

``build``  reads the 140 synced cell payloads, the saved AWS Batch
           ``describe-jobs`` responses and the unpacked fleet-workup
           package 02, checks them against ``campaign.json`` and writes
           the aggregate base tables to ``--out`` (not committed; the
           raw payloads hold per-host records and stay private).
``verify`` needs only that directory: it re-hashes the tables, checks the
           exact expected seed/arm/job sets and recomputes every summary
           statistic from the base tables. No network, no repository.

Voyage-wide endpoints only. An undefined share is blank, never zero. The
independent unit is a seed; every interval is a pointwise paired
descriptive interval conditional on these seeds and this configuration.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAKEOFF_MIN = 10
DAY31 = 31
# Two-sided 95% Student t critical values, t(0.975, n-1), keyed by n.
T975 = {16: 2.131449545559323, 20: 2.093024054408263, 50: 2.009575234489209,
        19: 2.10092204024096, 49: 2.010634757624232}
REPLAYS = {
    "dp": {"design_id": "covid_transport_fit_01_dp", "hull": "mega_cruise_5000",
           "scenario": "diamond_princess_2020", "native": "dp_native",
           "contamx": "dp_contamx_canary", "pairs": 20},
    "gm": {"design_id": "covid_transport_fit_01_gm", "hull": "expedition_cruise_450",
           "scenario": "greg_mortimer_2020", "native": "gm_native",
           "contamx": "gm_contamx", "pairs": 50},
}
PARENT_JOBS = {  # LEDGER.md section 5
    "dp_contamx_canary": "0a894bc5-0dca-4554-816f-0ebc853067ae",
    "dp_native": "bec97e14-7e51-4a49-9b1c-37a2eb60ad5c",
    "gm_native": "da861223-2b85-4479-80d3-21a343502fee",
    "gm_contamx": "a02bd464-8cb5-4ece-b427-351c0473f70c",
}
BENCH_PHASES = {
    "native": {("measured", p) for p in (
        "input_read", "native_construct", "field_reduce", "downstream",
        "end_to_end", "process_total")} | {("cached", "downstream")},
    "contamx": {("measured", p) for p in (
        "input_read", "contamx_export", "contamx_solve", "contamx_import",
        "field_reduce", "downstream", "end_to_end", "process_total")}
    | {("cached", "downstream")},
}
RESOLVED = {"native": "ContamTransportEngine", "contamx": "ContamXTransportEngine"}
COUNTS = ["recorded_onsets", "lab_confirmed", "campaign_positives",
          "campaign_specimens", "infections_total", "aboard_total"]
SHARES = ["attack_share", "positive_share", "dated_share", "lab_crew_share",
          "before_share", "asym_share_final", "asym_share_day31",
          "campaign_asym_share"]
TIMING = ["first_onset_day"]
ENDPOINTS = COUNTS + SHARES + TIMING
SEED_COLS = ["replay", "arm", "block", "seed", *ENDPOINTS, "takeoff"]
SOURCE_COLS = ["block", "seed", "s3_key", "bytes", "sha256"]
JOB_COLS = ["replay", "arm", "block", "array_index", "seed", "job_id",
            "job_definition_revision", "image_digest", "attempts", "exit_code",
            "started_at_ms", "stopped_at_ms", "run_ms", "host_token"]
BENCH_COLS = ["hull", "cohort", "lane", "repeat_kind", "phase", "n", "timeouts",
              "wall_median_ns", "wall_min_ns", "wall_max_ns"]
BENCH_HULLS = ["classic_cruise_1900", "expedition_cruise_450",
               "mega_cruise_5000", "spirit_cruise_3000"]
BENCH_LANES = {"native_prescribed": "native",
               "contamx_commissioned_export": "contamx"}
PACKAGE02_SHA256 = "3bc0e40f4d7a03082bbb6caf01ff76257163d7da8daee672f55a80c406f9684d"
TABLES = ["seed_endpoints.csv", "source_cells.csv", "batch_children.csv",
          "microbench.csv", "microbench_cohorts.csv", "paired_summary.json"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _spec() -> dict:
    return json.loads((HERE / "campaign.json").read_text(encoding="utf-8"))


def _share(num: float, den: float) -> float | None:
    return num / den if den else None


def _funnel(payload: dict, day_cap: int | None) -> tuple[int, int]:
    """(asymptomatic-at-confirmation, confirmed) host counts, the
    source readout's definition, optionally capped by confirmation day."""
    conf = [h for h in (payload.get("funnel_hosts") or {}).values()
            if h.get("confirmed_day") is not None
            and (day_cap is None or int(h["confirmed_day"]) <= day_cap)]
    asym = [h for h in conf if h.get("presented_day") is None
            or int(h["presented_day"]) > int(h["confirmed_day"])]
    return len(asym), len(conf)


def endpoints(p: dict) -> dict:
    """Voyage-wide endpoints of one cell. Counts absent from the payload
    stay None (blank); shares with a zero denominator are None."""
    obs = p["observables"]
    rec = obs["recorded_onsets"]
    lab = p["lab_confirmed_total"]
    spec = obs["campaign_specimens"]
    asym, conf = _funnel(p, None)
    asym31, conf31 = _funnel(p, DAY31)
    return {
        "recorded_onsets": rec,
        "lab_confirmed": lab,
        "campaign_positives": obs["campaign_positives"],
        "campaign_specimens": spec,
        "infections_total": p["infections_total"],
        "aboard_total": p["aboard_total"],
        "attack_share": _share(p["infections_total"], p["aboard_total"]),
        "positive_share": _share(obs["campaign_positives"], spec),
        "dated_share": _share(rec, lab),
        "lab_crew_share": _share((p.get("lab_confirmed_by_role") or {}).get("crew", 0), lab),
        "before_share": _share(obs["onsets_before_split_day"], rec),
        "asym_share_final": _share(asym, conf),
        "asym_share_day31": _share(asym31, conf31),
        "campaign_asym_share": _share(obs["campaign_asymptomatic_positives"],
                                      obs["campaign_positives"]),
        "first_onset_day": p.get("first_onset_day"),
        "takeoff": int(rec >= TAKEOFF_MIN),
    }


def _fmt(v: object) -> str:
    if v is None:
        return ""
    return repr(float(v)) if isinstance(v, float) else str(v)


def _write_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            w.writerow([_fmt(r.get(c)) for c in cols])


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _num(text: str) -> float | int | None:
    if text == "":
        return None
    return float(text) if any(c in text for c in ".e") else int(text)


# ---------------------------------------------------------------- build

def _strip_engine(delivery: dict) -> dict:
    return {k: v for k, v in delivery.items()
            if k not in ("transport_engine", "transport_engine_resolved")}


def _audit_cell(p: dict, replay: str, arm: str, seed: int, design: dict,
                problems: list[str]) -> None:
    tag = f"{replay}/{arm}/{seed}"
    cell = p["cell"]
    want = {
        "design_id": (p["design_id"], REPLAYS[replay]["design_id"]),
        "arm": (cell["arm_id"], arm), "arm_top": (p["arm_id"], arm),
        "seed": (cell["seed"], seed), "obs_seed": (p["observables"]["seed"], seed),
        "scenario": (cell["scenario_id"], design["scenario_id"]),
        "theta": (cell["theta"], design["thetas"][0]),
        "infection_age_days": (cell["infection_age_days"], design["infection_age_days"][0]),
        "imports": (cell["imports"], design["imports"][0]),
        "sanitary_visit_mode": (p["sanitary_visit_mode"], design["sanitary_visit_mode"]),
        "engine_declared": (p["delivery"]["transport_engine"], arm),
        "engine_resolved": (p["delivery"]["transport_engine_resolved"], RESOLVED[arm]),
        "binary_echo": (p["transport_engine_binary"] is not None, arm == "contamx"),
    }
    problems.extend(f"{tag}: {k} {got!r} != {exp!r}"
                    for k, (got, exp) in want.items() if got != exp)


PAIR_EQUAL = ["dose_response", "aboard_total", "ship_graph_immune",
              "propensity_draw", "index_onset_day", "onset_eligibility_by_severity",
              "exposure_cap_active", "crew_duty_exclusion"]


def _audit_pair(nat: dict, cx: dict, tag: str, problems: list[str]) -> None:
    """Configuration echoes and pre-voyage draws equal inside a seed pair."""
    if _strip_engine(nat["delivery"]) != _strip_engine(cx["delivery"]):
        problems.append(f"{tag}: delivery echo differs beyond the engine keys")
    problems.extend(f"{tag}: {k} differs inside the pair"
                    for k in PAIR_EQUAL if nat[k] != cx[k])
    for k in ("seed_spec", "seeded_count"):
        if nat["seed_ring"][k] != cx["seed_ring"][k]:
            problems.append(f"{tag}: seed_ring.{k} differs inside the pair")


def _load_cells(cells_dir: Path, spec: dict, problems: list[str]):
    seed_rows, source_rows = [], []
    for replay, meta in REPLAYS.items():
        design = json.loads((HERE.parents[2] / spec["blocks"][meta["native"]]["args"]["design"])
                            .read_text(encoding="utf-8"))
        loaded: dict[str, dict[int, dict]] = {}
        for arm in ("native", "contamx"):
            block = meta[arm]
            seeds = spec["blocks"][block]["seeds"]
            found = sorted(f.name for f in (cells_dir / block).iterdir())
            if found != sorted(f"cell_{s}.json" for s in seeds):
                problems.append(f"{block}: file set is not the declared seed set")
            loaded[arm] = {}
            for seed in seeds:
                path = cells_dir / block / f"cell_{seed}.json"
                p = json.loads(path.read_text(encoding="utf-8"))
                _audit_cell(p, replay, arm, seed, design, problems)
                loaded[arm][seed] = p
                seed_rows.append({"replay": replay, "arm": arm, "block": block,
                                  "seed": seed, **endpoints(p)})
                source_rows.append({
                    "block": block, "seed": seed,
                    "s3_key": f"{spec['s3_prefix']}{block}/cell_{seed}.json",
                    "bytes": path.stat().st_size, "sha256": _sha(path)})
        for seed, nat in loaded["native"].items():
            _audit_pair(nat, loaded["contamx"][seed], f"{replay}/{seed}", problems)
    return seed_rows, source_rows


def _job_row(k: dict, block: str, index: int, seed: int, host: str) -> dict:
    att = k["attempts"]
    return {
        "block": block, "array_index": index, "seed": seed, "job_id": k["jobId"],
        "job_definition_revision": k["jobDefinition"].rsplit(":", 1)[-1],
        "image_digest": k["container"]["image"].rsplit("@", 1)[-1],
        "attempts": len(att), "exit_code": att[-1]["container"]["exitCode"],
        "started_at_ms": k["startedAt"], "stopped_at_ms": k["stoppedAt"],
        "run_ms": k["stoppedAt"] - k["startedAt"], "host_token": host}


def _audit_parent(parent: dict, block: str, seeds: list[int],
                  problems: list[str]) -> None:
    """The array that wrote the cells, not a later resubmission (whose
    children skip existing cells and would time no voyage)."""
    if parent["jobId"] != PARENT_JOBS[block]:
        problems.append(f"{block}: parent job is not the ledger's run")
    cmd = parent["container"]["command"]
    if cmd[cmd.index("--block") + 1] != block or \
            cmd[cmd.index("--seeds") + 1] != ",".join(map(str, seeds)):
        problems.append(f"{block}: submitted command is not the declared block/seeds")


def _load_block_jobs(batch_dir: Path, block: str, seeds: list[int],
                     hosts: dict[str, str], problems: list[str]) -> list[dict]:
    parent = json.loads((batch_dir / f"parent_{block}.json").read_text())["jobs"][0]
    kids = json.loads((batch_dir / f"children_{block}.json").read_text())["jobs"]
    _audit_parent(parent, block, seeds, problems)
    by_index = {k["arrayProperties"]["index"]: k for k in kids}
    if sorted(by_index) != list(range(len(seeds))):
        problems.append(f"{block}: child indices are not 0..{len(seeds) - 1}")
        return []
    rows = []
    for index, seed in enumerate(seeds):
        k = by_index[index]
        if k["status"] != "SUCCEEDED" or k["jobId"] != f"{parent['jobId']}:{index}":
            problems.append(f"{block}:{index}: not a SUCCEEDED child of the parent")
        inst = k["attempts"][-1]["container"]["containerInstanceArn"].rsplit("/", 1)[-1]
        hosts.setdefault(inst, f"host_{len(hosts) + 1:02d}")
        rows.append(_job_row(k, block, index, seed, hosts[inst]))
    return rows


def _load_jobs(batch_dir: Path, spec: dict, problems: list[str]) -> list[dict]:
    rows: list[dict] = []
    hosts: dict[str, str] = {}
    for replay, meta in REPLAYS.items():
        for arm in ("native", "contamx"):
            block = meta[arm]
            rows.extend({"replay": replay, "arm": arm, **r} for r in _load_block_jobs(
                batch_dir, block, spec["blocks"][block]["seeds"], hosts, problems))
    return rows


def _load_bench(pkg: Path) -> tuple[list[dict], list[dict]]:
    rows = [
        {**{c: r[c] for c in BENCH_COLS if c in r}, "lane": BENCH_LANES[r["lane"]]}
        for r in _read_csv(pkg / "data" / "timing_summary.csv")
        if r["hull"] in BENCH_HULLS and r["setting_id"] == "baseline"
        and r["lane"] in BENCH_LANES
    ]
    rows.sort(key=lambda r: (r["hull"], r["lane"], r["repeat_kind"], r["phase"]))
    keep = ["cohort", "batch_job_id", "job_definition", "image_digest",
            "runner_commit", "attempts", "instance_type", "cpu_model",
            "cpu_affinity", "thread_env_all_1", "loadavg_1m_max",
            "contamx_version", "contamx_binary_sha256"]
    used = {r["cohort"] for r in rows}
    cohorts = [{c: r[c] for c in keep}
               for r in _read_csv(pkg / "data" / "cohorts.csv") if r["cohort"] in used]
    return rows, cohorts


# -------------------------------------------------------------- summary

def _dist(vals: list[float]) -> dict:
    return {"n": len(vals), "mean": statistics.fmean(vals),
            "median": statistics.median(vals), "min": min(vals), "max": max(vals)}


def _nearest_rank(vals: list[float], q: float) -> float:
    """The source readout's quantile: index round(q*(n-1)) of the sorted
    values (Python banker's rounding). Not an interpolated percentile."""
    s = sorted(vals)
    return s[max(0, min(len(s) - 1, int(round(q * (len(s) - 1)))))]


def _paired(nat: dict[int, float | None], cx: dict[int, float | None]) -> dict:
    seeds = [s for s in sorted(nat) if nat[s] is not None and cx[s] is not None]
    out: dict = {
        "pairs_declared": len(nat), "pairs_defined": len(seeds),
        "native_undefined": sum(v is None for v in nat.values()),
        "contamx_undefined": sum(v is None for v in cx.values()),
    }
    if not seeds:
        return out
    a = [nat[s] for s in seeds]
    b = [cx[s] for s in seeds]
    d = [y - x for x, y in zip(a, b)]
    n = len(d)
    mean = statistics.fmean(d)
    sd = statistics.stdev(d) if n > 1 else None
    out.update({
        "native": _dist(a), "contamx": _dist(b),
        "native_src_q05_q95": [_nearest_rank(a, 0.05), _nearest_rank(a, 0.95)],
        "contamx_src_q05_q95": [_nearest_rank(b, 0.05), _nearest_rank(b, 0.95)],
        "delta": {**_dist(d), "sd": sd,
                  "src_q05_q95": [_nearest_rank(d, 0.05), _nearest_rank(d, 0.95)]},
        "positive": sum(x > 0 for x in d), "negative": sum(x < 0 for x in d),
        "tied": sum(x == 0 for x in d),
    })
    if n > 1:
        tot = sum(d)
        loo = [(tot - x) / (n - 1) for x in d]
        out["delta"]["leave_one_seed_out_mean_range"] = [min(loo), max(loo)]
        out["delta"]["largest_abs_delta_share_of_sum_abs"] = (
            max(abs(x) for x in d) / sum(abs(x) for x in d) if any(d) else None)
    t = T975.get(n)
    if t is not None and sd is not None:
        half = t * sd / math.sqrt(n)
        out["delta"]["mean_ci95_paired_t"] = [mean - half, mean + half]
    return out


def _takeoff(nat: dict[int, int], cx: dict[int, int]) -> dict:
    cell = {(i, j): sum(nat[s] == i and cx[s] == j for s in nat)
            for i in (0, 1) for j in (0, 1)}
    return {
        "pairs": len(nat), "threshold_recorded_onsets_ge": TAKEOFF_MIN,
        "both_takeoff": cell[1, 1], "neither_takeoff": cell[0, 0],
        "native_only": cell[1, 0], "contamx_only": cell[0, 1],
        "native_takeoff": cell[1, 1] + cell[1, 0],
        "contamx_takeoff": cell[1, 1] + cell[0, 1],
        "discordant_native_to_no_takeoff": [cell[1, 0], cell[1, 1] + cell[1, 0]],
        "discordant_no_takeoff_to_takeoff": [cell[0, 1], cell[0, 0] + cell[0, 1]],
    }


def _timing(jobs: list[dict]) -> dict:
    out: dict = {}
    for replay, meta in REPLAYS.items():
        for arm in ("native", "contamx"):
            rows = [r for r in jobs if r["block"] == meta[arm]]
            secs = [int(r["run_ms"]) / 1000 for r in rows]
            out[f"{replay}_{arm}"] = {
                "block": meta[arm], "children": len(rows),
                "attempts_max": max(int(r["attempts"]) for r in rows),
                "image_digests": sorted({r["image_digest"] for r in rows}),
                "job_definition_revisions": sorted({r["job_definition_revision"] for r in rows}),
                "hosts": len({r["host_token"] for r in rows}),
                "run_seconds": _dist(secs),
            }
    return out


def summarize(seed_rows: list[dict], jobs: list[dict]) -> dict:
    out: dict = {"replays": {}, "batch_child_run_time": _timing(jobs)}
    for replay, meta in REPLAYS.items():
        arms = {arm: {int(r["seed"]): r for r in seed_rows
                      if r["replay"] == replay and r["arm"] == arm}
                for arm in ("native", "contamx")}
        col = lambda arm, k: {s: _num(r[k]) if isinstance(r[k], str) else r[k]  # noqa: E731
                              for s, r in arms[arm].items()}
        out["replays"][replay] = {
            "design_id": meta["design_id"], "hull": meta["hull"],
            "scenario": meta["scenario"], "pairs": meta["pairs"],
            "endpoints": {k: _paired(col("native", k), col("contamx", k))
                          for k in ENDPOINTS},
            "takeoff_2x2": _takeoff(col("native", "takeoff"), col("contamx", "takeoff")),
        }
    return out


def _dump(obj: object) -> str:
    return json.dumps(obj, indent=1, sort_keys=True) + "\n"


def build(args: argparse.Namespace) -> int:
    spec, problems = _spec(), []
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    seed_rows, source_rows = _load_cells(Path(args.cells_dir), spec, problems)
    jobs = _load_jobs(Path(args.batch_dir), spec, problems)
    bench, cohorts = _load_bench(Path(args.package02))
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    _write_csv(out / "seed_endpoints.csv", SEED_COLS, seed_rows)
    _write_csv(out / "source_cells.csv", SOURCE_COLS, source_rows)
    _write_csv(out / "batch_children.csv", JOB_COLS, jobs)
    _write_csv(out / "microbench.csv", BENCH_COLS, bench)
    _write_csv(out / "microbench_cohorts.csv", list(cohorts[0]), cohorts)
    summary = summarize(_read_csv(out / "seed_endpoints.csv"),
                        _read_csv(out / "batch_children.csv"))
    (out / "paired_summary.json").write_text(_dump(summary), encoding="utf-8")
    sums = "".join(f"{_sha(out / t)}  {t}\n" for t in TABLES)
    (out / "SHA256SUMS").write_text(sums, encoding="utf-8")
    print(f"WROTE {out} ({len(seed_rows)} cells, {len(jobs)} jobs, {len(bench)} timing rows)")
    return 0


# --------------------------------------------------------------- verify

def _close(a: object, b: object) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return (isinstance(a, (int, float)) and isinstance(b, (int, float))
                and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12))
    return a == b


def _check_seed_row(r: dict) -> bool:
    """Shares re-derive from the row's own counts; blank iff denominator 0."""
    v = {k: _num(r[k]) for k in ENDPOINTS}
    ok = all(v[k] is not None for k in COUNTS)
    ok &= _close(v["attack_share"], _share(v["infections_total"], v["aboard_total"]))
    ok &= _close(v["positive_share"], _share(v["campaign_positives"], v["campaign_specimens"]))
    ok &= _close(v["dated_share"], _share(v["recorded_onsets"], v["lab_confirmed"]))
    ok &= (v["lab_crew_share"] is None) == (v["lab_confirmed"] == 0)
    ok &= (v["before_share"] is None) == (v["recorded_onsets"] == 0)
    ok &= (v["campaign_asym_share"] is None) == (v["campaign_positives"] == 0)
    ok &= (v["first_onset_day"] is None) == (v["recorded_onsets"] == 0)
    ok &= all(v[k] is None or 0.0 <= v[k] <= 1.0 for k in SHARES if k != "dated_share")
    return bool(ok and int(r["takeoff"]) == int(v["recorded_onsets"] >= TAKEOFF_MIN))


def verify(args: argparse.Namespace) -> int:
    d = Path(args.dir)
    checks: list[tuple[str, bool]] = []
    sums = dict(reversed(line.split("  ")) for line in
                (d / "SHA256SUMS").read_text(encoding="utf-8").splitlines())
    checks.append(("table set is exact", sorted(sums) == sorted(TABLES)))
    checks.extend((f"sha256 {t}", _sha(d / t) == sums.get(t)) for t in TABLES)
    spec = json.loads(Path(args.campaign).read_text(encoding="utf-8")) if args.campaign else None
    seed_rows = _read_csv(d / "seed_endpoints.csv")
    sources = _read_csv(d / "source_cells.csv")
    jobs = _read_csv(d / "batch_children.csv")
    for name, rows in (("seed_endpoints", seed_rows), ("source_cells", sources),
                       ("batch_children", jobs)):
        keys = [(r["block"], int(r["seed"])) for r in rows]
        want = sorted((meta[arm], 20200205 + i) for meta in REPLAYS.values()
                      for arm in ("native", "contamx") for i in range(meta["pairs"]))
        checks.append((f"{name}: 140 rows, exact block x seed set, no duplicate",
                       sorted(keys) == want and len(keys) == 140))
        if spec is not None:
            declared = sorted((b, s) for b, v in spec["blocks"].items() for s in v["seeds"])
            checks.append((f"{name}: matches campaign.json blocks", sorted(keys) == declared))
    checks.append(("seed rows: shares re-derive, blank iff undefined, takeoff flag",
                   all(_check_seed_row(r) for r in seed_rows)))
    checks.append(("sources: 140 distinct keys, 64-hex digests",
                   len({r["s3_key"] for r in sources}) == 140
                   and all(len(r["sha256"]) == 64 for r in sources)))
    checks.append(("jobs: one attempt, exit 0, index maps to seed, run_ms consistent", all(
        r["attempts"] == "1" and r["exit_code"] == "0"
        and int(r["seed"]) == 20200205 + int(r["array_index"])
        and r["job_id"].endswith(f":{r['array_index']}")
        and int(r["run_ms"]) == int(r["stopped_at_ms"]) - int(r["started_at_ms"]) > 0
        for r in jobs)))
    digests = {r["block"]: r["image_digest"] for r in jobs}
    checks.append(("jobs: two image identities, canary block differs from the other three",
                   len(set(digests.values())) == 2
                   and len({digests[b] for b in ("dp_native", "gm_native", "gm_contamx")}) == 1
                   and digests["dp_contamx_canary"] != digests["dp_native"]
                   and all(len({j["image_digest"] for j in jobs if j["block"] == b}) == 1
                           for b in digests)))
    bench = _read_csv(d / "microbench.csv")
    checks.append(("microbench: four hulls x two lanes, 5 repeats, no timeout",
                   {(r["hull"], r["lane"]) for r in bench}
                   == {(h, ln) for h in BENCH_HULLS for ln in ("native", "contamx")}
                   and all(r["n"] == "5" and r["timeouts"] == "0" for r in bench)))
    checks.append(("microbench: every hull x lane has exactly its cold and repeated phases", all(
        {(r["repeat_kind"], r["phase"]) for r in bench
         if (r["hull"], r["lane"]) == (h, ln)} == BENCH_PHASES[ln]
        and sum((r["hull"], r["lane"]) == (h, ln) for r in bench) == len(BENCH_PHASES[ln])
        for h in BENCH_HULLS for ln in BENCH_PHASES)))
    checks.append(("jobs: parent ids are the ledger's four runs", all(
        r["job_id"].rsplit(":", 1)[0] == PARENT_JOBS.get(r["block"]) for r in jobs)))
    stored = json.loads((d / "paired_summary.json").read_text(encoding="utf-8"))
    checks.append(("paired_summary.json recomputes from the base tables",
                   _close(json.loads(_dump(summarize(seed_rows, jobs))), stored)))
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    failed = sum(not ok for _, ok in checks)
    print(f"{len(checks) - failed} of {len(checks)} checks passed")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--cells-dir", required=True)
    b.add_argument("--batch-dir", required=True)
    b.add_argument("--package02", required=True, help="unpacked package 02 directory")
    b.add_argument("--out", required=True)
    b.set_defaults(fn=build)
    v = sub.add_parser("verify")
    v.add_argument("--dir", required=True)
    v.add_argument("--campaign", default=None, help="optional campaign.json cross-check")
    v.set_defaults(fn=verify)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
