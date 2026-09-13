"""Informative run ordering and the in-loop campaign stopping rule.

Ordering: a pure, deterministic permutation of the run list that keeps the
modulo shard partition complete and disjoint and spreads early runs across
design points. Stop rule: Beta-Binomial posterior on a declared event; fires on
a synthetic unexpected trend, stays quiet on an in-band series, and produces
an orderly, resumable shutdown when wired through ``main()``.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
    generate_tier_runs,
    load_manifest,
    main,
)
from picard_framework.runs.mega_cruise_campaign.informative_ordering import (
    ORDER_INFORMATIVE,
    ORDER_MANIFEST,
    design_point_key,
    group_design_points,
    order_runs,
    order_runs_informative,
    van_der_corput_order,
)
from picard_framework.runs.mega_cruise_campaign.stop_rule import (
    CONTINUE,
    STOP_ABOVE,
    STOP_BELOW,
    StopRuleSpecError,
    parse_stop_rule,
)
from telemetry_buffer.observation_model.staged_posting_readout import (
    JEFFREYS,
    STOP_MASS,
)

Run = tuple[str, str, dict[str, Any]]


@pytest.fixture(scope="module")
def t1_runs() -> list[Run]:
    manifest = load_manifest()
    return [
        ("t1_pathogen_baselines", run_id, spec)
        for run_id, spec in generate_tier_runs(manifest, "t1_pathogen_baselines")
    ]


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n", [0, 1, 2, 3, 5, 8, 10, 13, 64])
def test_van_der_corput_order_is_a_permutation(n: int) -> None:
    order = van_der_corput_order(n)
    assert sorted(order) == list(range(n))


def test_van_der_corput_prefix_spreads_across_range() -> None:
    order = van_der_corput_order(16)
    assert order[:4] == [0, 8, 4, 12]


def test_informative_order_is_deterministic_permutation(t1_runs: list[Run]) -> None:
    once = order_runs_informative(t1_runs)
    twice = order_runs_informative(list(t1_runs))
    assert once == twice
    assert len(once) == len(t1_runs) == 300
    assert sorted(r[1] for r in once) == sorted(r[1] for r in t1_runs)
    assert once != t1_runs  # it does something


def test_informative_order_ignores_input_shuffle(t1_runs: list[Run]) -> None:
    """Design-point grouping is by content, so a reversed input reorders only replicates."""
    reversed_order = order_runs_informative(list(reversed(t1_runs)))
    forward = order_runs_informative(t1_runs)
    forward_points = [design_point_key(t, s) for t, _r, s in forward]
    reversed_points = [design_point_key(t, s) for t, _r, s in reversed_order]
    # Per-wave multiset of design points is identical either way.
    n_points = len(group_design_points(t1_runs))
    for wave in range(0, 300, n_points):
        assert set(forward_points[wave:wave + n_points]) == set(
            reversed_points[wave:wave + n_points],
        )


def test_informative_order_visits_every_design_point_before_replicating(
    t1_runs: list[Run],
) -> None:
    groups = group_design_points(t1_runs)
    n_points = len(groups)
    assert n_points == 10  # 10 pathogens x 30 seeds
    ordered = order_runs_informative(t1_runs)
    keys = [design_point_key(t, s) for t, _r, s in ordered]
    for wave in range(0, len(ordered), n_points):
        assert len(set(keys[wave:wave + n_points])) == n_points
    # Manifest order, by contrast, clusters the first 30 runs on one pathogen.
    manifest_keys = [design_point_key(t, s) for t, _r, s in t1_runs]
    assert len(set(manifest_keys[:n_points])) == 1


@pytest.mark.parametrize("shard_count", [1, 3, 7, 300, 301])
def test_informative_order_keeps_shard_partition_complete_and_disjoint(
    t1_runs: list[Run], shard_count: int,
) -> None:
    ordered = order_runs_informative(t1_runs)
    claimed: dict[str, int] = {}
    for shard_index in range(shard_count):
        # Each shard recomputes the order independently from the same list.
        mine = order_runs_informative(list(t1_runs))
        assert mine == ordered
        for gi, (_t, run_id, _s) in enumerate(mine):
            if gi % shard_count == shard_index:
                assert run_id not in claimed
                claimed[run_id] = shard_index
    assert set(claimed) == {r[1] for r in t1_runs}


def test_order_runs_manifest_is_identity_and_unknown_rejected(t1_runs: list[Run]) -> None:
    assert order_runs(t1_runs, ORDER_MANIFEST) == t1_runs
    assert order_runs(t1_runs, ORDER_INFORMATIVE) == order_runs_informative(t1_runs)
    with pytest.raises(ValueError):
        order_runs(t1_runs, "random")


def test_dry_run_informative_shard_counts_sum_to_total(capsys: pytest.CaptureFixture[str]) -> None:
    shard_count = 7
    counts: list[int] = []
    for shard_index in range(shard_count):
        assert main([
            "--tier", "t1", "--dry-run", "--order", "informative",
            "--shard-count", str(shard_count), "--shard-index", str(shard_index),
        ]) == 0
        out = capsys.readouterr().out
        line = next(ln for ln in out.splitlines() if "assigned to this shard" in ln)
        counts.append(int(line.split(":")[1].split()[0]))
    assert sum(counts) == 300
    assert max(counts) - min(counts) <= 1


# ---------------------------------------------------------------------------
# Stop rule: statistics
# ---------------------------------------------------------------------------


def test_stop_rule_reuses_readout_constants() -> None:
    rule = parse_stop_rule("outbreak_occurred:0.2:0.6:5")
    assert rule.prior == JEFFREYS == (0.5, 0.5)
    assert rule.stop_mass == STOP_MASS == 0.95


@pytest.mark.parametrize(
    "spec",
    [
        "outbreak_occurred:0.2:0.6",  # three fields
        "outbreak_occurred:0.6:0.2:5",  # inverted band
        "outbreak_occurred:0.2:1.2:5",  # band beyond 1
        "outbreak_occurred:0.2:0.6:0",  # min_n < 1
        "attack_rate>=x:0.2:0.6:5",  # non-numeric threshold
        "9bad:0.2:0.6:5",  # bad metric name
    ],
)
def test_stop_rule_rejects_malformed_specs(spec: str) -> None:
    with pytest.raises(StopRuleSpecError):
        parse_stop_rule(spec)


def test_stop_rule_fires_above_on_unexpected_trend() -> None:
    rule = parse_stop_rule("outbreak_occurred:0.2:0.6:5")
    decisions = []
    for i in range(12):
        rule.observe(f"r{i}", {"outbreak_occurred": True})
        decisions.append(rule.decision())
    assert decisions[:4] == [CONTINUE] * 4  # min_n holds it
    assert STOP_ABOVE in decisions
    first = decisions.index(STOP_ABOVE)
    assert all(d == STOP_ABOVE for d in decisions[first:])
    assert rule.mass()["above"] >= STOP_MASS


def test_stop_rule_fires_below_on_absent_events() -> None:
    rule = parse_stop_rule("attack_rate>=0.3:0.4:0.8:5")
    for i in range(15):
        rule.observe(f"r{i}", {"attack_rate": 0.05})
    assert rule.decision() == STOP_BELOW
    assert rule.k == 0 and rule.n == 15


def test_stop_rule_stays_quiet_inside_band() -> None:
    rule = parse_stop_rule("outbreak_occurred:0.2:0.6:5")
    for i in range(40):
        rule.observe(f"r{i}", {"outbreak_occurred": i % 5 in (0, 1)})  # 40%
    assert rule.decision() == CONTINUE
    assert not rule.triggered
    assert rule.mass()["inside"] > 0.5


def test_stop_rule_posterior_mass_is_graded_in_evidence() -> None:
    """More consistent evidence -> more mass above the band, monotone in n."""
    above = []
    for n in (5, 10, 20, 40):
        rule = parse_stop_rule("outbreak_occurred:0.2:0.6:1")
        for i in range(n):
            rule.observe(f"r{i}", {"outbreak_occurred": True})
        above.append(rule.mass()["above"])
    assert above == sorted(above)
    assert 0.0 < above[0] < above[-1] <= 1.0


def test_stop_rule_skips_unscorable_runs() -> None:
    rule = parse_stop_rule("attack_rate>=0.3:0.2:0.6:3")
    assert rule.observe("a", {}) is None
    assert rule.observe("b", {"attack_rate": None}) is None
    assert rule.observe("c", {"attack_rate": "n/a"}) is None
    assert rule.observe("d", {"attack_rate": 0.5}) is True
    assert rule.n == 1 and rule.unscored == 3
    assert rule.decision() == CONTINUE


def test_stop_rule_verdict_round_trips_spec() -> None:
    rule = parse_stop_rule("peak_epoch<40:0.1:0.3:7")
    rule.observe_entries({"x": {"derived": {"peak_epoch": 12}}, "y": {"derived": {}}})
    verdict = rule.verdict()
    assert verdict["spec"] == "peak_epoch<40:0.1:0.3:7"
    assert verdict["scored_runs"] == 1 and verdict["events"] == 1
    assert verdict["unscored_runs"] == 1
    assert verdict["decision"] == CONTINUE
    assert parse_stop_rule(verdict["spec"]).render_spec() == verdict["spec"]


# ---------------------------------------------------------------------------
# Stop rule: orderly shutdown through main()
# ---------------------------------------------------------------------------


class _MemoryUploader:
    storage: dict[str, bytes] = {}

    def __init__(self, _prefix: str) -> None:
        pass

    def download_file(self, name: str, local_path: Path) -> bool:
        payload = self.storage.get(name)
        if payload is None:
            return False
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(payload)
        return True

    def upload_file(self, local_path: Path, name: str) -> str:
        self.storage[name] = local_path.read_bytes()
        return f"s3://fake/{name}"


def _wire_fake_campaign(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outbreak: bool,
) -> tuple[Path, list[str], dict[str, bytes]]:
    out = tmp_path / "mega_cruise_campaign"
    prefix = "picard_framework.runs.mega_cruise_campaign.campaign_runner."
    monkeypatch.setattr(prefix + "OUTPUT_ROOT", out)
    monkeypatch.setattr(prefix + "COMPLETED_LOG", out / "completed_runs.txt")
    monkeypatch.setattr(prefix + "FAILED_LOG", out / "failed_runs.txt")
    _MemoryUploader.storage = {}
    calls: list[str] = []

    def fake_run(run_id: str, spec: dict, **kwargs: Any) -> bool:
        calls.append(run_id)
        suffix = kwargs.get("accumulation_suffix", "single")
        run_dir = out / "_shard_runs" / suffix / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "run_id": run_id,
            "parameters": {"seed": spec["run"]["random_seed"]},
            "derived": {"outbreak_occurred": outbreak, "attack_rate": 0.9 if outbreak else 0.01},
        }
        (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
        (run_dir / "timeseries.json").write_text("[]", encoding="utf-8")
        (out / f"{run_id}.zip").write_bytes(b"local")
        return True

    exec_prefix = "picard_framework.runs.mega_cruise_campaign.campaign_execution."
    monkeypatch.setattr(exec_prefix + "S3Uploader", _MemoryUploader)
    monkeypatch.setattr(exec_prefix + "run_simulation", fake_run)
    monkeypatch.setattr(exec_prefix + "run_simulation_subprocess", fake_run)
    return out, calls, _MemoryUploader.storage


_BASE_ARGS = [
    "--tier", "t1", "--platform", "destroyer_baseline",
    "--epochs", "2", "--num-agents", "20", "--in-process",
    "--s3-prefix", "s3://fake-bucket/campaign/", "--s3-log-every", "0",
    "--shard-count", "3", "--shard-index", "1",
]


def test_stop_rule_triggers_orderly_resumable_shutdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    out, calls, storage = _wire_fake_campaign(tmp_path, monkeypatch, outbreak=True)
    args = [*_BASE_ARGS, "--limit", "50", "--stop-rule", "outbreak_occurred:0.2:0.6:5"]

    rc = main(args)

    assert rc == 0, "a fired stop rule is not an error"
    # Fired after min_n (5) once P(above) >= 0.95: exactly 5 all-outbreak runs.
    assert len(calls) == 5
    assert len(calls) < 50  # well short of --limit
    # Orderly shutdown: bundle flushed, log uploaded, verdict published.
    assert {"shard-1.zip", "shard-1.manifest.json", "_resume/completed_runs.shard-1.txt",
            "shard-1.stop_rule.json"} <= set(storage)
    with zipfile.ZipFile(out / "shard-1.zip") as zf:
        assert all(f"{run_id}/summary.json" in zf.namelist() for run_id in calls)
    verdict = json.loads(storage["shard-1.stop_rule.json"])
    assert verdict["decision"] == STOP_ABOVE
    assert verdict["scored_runs"] == 5 and verdict["events"] == 5
    assert verdict["posterior"]["above"] >= STOP_MASS
    assert verdict["scored_run_ids"] == calls
    completed = (out / "completed_runs.txt").read_text(encoding="utf-8").split()
    assert set(completed) == set(calls)

    # Resume with the same rule: re-armed from the bundle, it stops at once.
    assert main([*args, "--resume"]) == 0
    assert len(calls) == 5
    assert json.loads(storage["shard-1.stop_rule.json"])["decision"] == STOP_ABOVE

    # Resume without the rule: the shard continues past the verdict.
    assert main([*_BASE_ARGS, "--limit", "2", "--resume"]) == 0
    assert len(calls) == 7
    assert len(set(calls)) == 7  # no run repeated across the three launches
    with zipfile.ZipFile(out / "shard-1.zip") as zf:
        assert all(f"{run_id}/summary.json" in zf.namelist() for run_id in calls)


def test_stop_rule_does_not_trigger_when_trend_is_inside_band(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fake runs are all-outbreak; a band that contains 1.0 cannot be left."""
    _out, calls, storage = _wire_fake_campaign(tmp_path, monkeypatch, outbreak=True)
    rc = main([*_BASE_ARGS, "--limit", "8", "--stop-rule", "outbreak_occurred:0.5:1.0:3"])
    assert rc == 0
    assert len(calls) == 8  # ran to --limit
    verdict = json.loads(storage["shard-1.stop_rule.json"])
    assert verdict["decision"] == CONTINUE
    assert verdict["scored_runs"] == 8


def test_stop_rule_triggers_below_when_events_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _out, calls, storage = _wire_fake_campaign(tmp_path, monkeypatch, outbreak=False)
    rc = main([*_BASE_ARGS, "--limit", "30", "--stop-rule", "attack_rate>=0.3:0.4:0.9:4"])
    assert rc == 0
    assert 4 <= len(calls) < 30
    assert json.loads(storage["shard-1.stop_rule.json"])["decision"] == STOP_BELOW


def test_campaign_without_stop_rule_publishes_no_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _out, calls, storage = _wire_fake_campaign(tmp_path, monkeypatch, outbreak=True)
    assert main([*_BASE_ARGS, "--limit", "3"]) == 0
    assert len(calls) == 3
    assert not any(name.endswith(".stop_rule.json") for name in storage)


def test_malformed_stop_rule_exits_before_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _out, calls, _storage = _wire_fake_campaign(tmp_path, monkeypatch, outbreak=True)
    with pytest.raises(SystemExit):
        main([*_BASE_ARGS, "--limit", "3", "--stop-rule", "outbreak_occurred:0.6:0.2:5"])
    assert calls == []
