"""Structural checks on the Paper-1 WP2 joint-evaluation campaign.

Invariants and graded behaviour only: the builder is deterministic, every
arm keeps the frozen baseline except where it says otherwise, the frozen
selection rule orders seeds the way it claims, and the readout's gate and
continuation respond to their inputs. No voyage is run.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = REPO_ROOT / "campaigns" / "noro" / "paper1_joint_eval_01"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


build = _load("paper1_je_build", CAMPAIGN / "design" / "build.py")
readout = _load("paper1_je_readout", CAMPAIGN / "readout.py")
cell = _load("paper1_je_cell", CAMPAIGN / "cell.py")


def _selection(n: int = build.BRIDGE_SEEDS) -> dict:
    hulls = {}
    for hull, start in build.CENSUS_START.items():
        def sample(offset: int) -> dict:
            return {
                "seeds": list(range(start + offset, start + offset + n)),
                "frame_n": 1000, "inclusion_probability": n / 1000,
                "source_weight": 0.5,
            }
        hulls[hull] = {
            "census_n": 2000,
            "diagnostic": {
                s: list(range(start + i * 100, start + i * 100 + n))
                for i, s in enumerate(build.BRIDGE_STRATA)
            },
            "evaluation": {
                "uncontaminated": sample(1000), "contaminated": sample(2000),
            },
        }
    return {"campaign": build.NAME, "hulls": hulls}


@pytest.fixture()
def stage_b(monkeypatch):
    monkeypatch.setattr(build, "load_selection", _selection)
    return build.build()


def test_committed_files_reproduce_from_the_builder():
    manifest, campaign = build.build()
    assert (CAMPAIGN / "manifest.json").read_text() == build.render(manifest)
    assert (CAMPAIGN / "campaign.json").read_text() == build.render(campaign)


def test_stage_a_count_matches_the_design():
    _, campaign = build.build()
    runs = sum(len(b["seeds"]) for b in campaign["blocks"].values())
    assert runs == 4 * 200 + 16


def test_stage_b_is_the_small_complete_bridge_plus_pilot(stage_b):
    manifest, campaign = stage_b
    arms = [t["joint_eval"]["arm"] for t in manifest["tiers"].values()]
    assert arms.count("bridge") == 4 * 3 * 3
    assert arms.count("pilot") == 4 * 2
    stage_b_runs = sum(
        len(t["seeds"]) for t in manifest["tiers"].values()
        if t["joint_eval"]["arm"] in ("bridge", "pilot")
    )
    assert stage_b_runs == 36 * 20 + 8 * 20
    cells = {
        (t["joint_eval"]["hull"], t["joint_eval"]["epochs"])
        for t in manifest["tiers"].values()
        if t["joint_eval"]["arm"] == "bridge"
    }
    assert {e for _, e in cells} == {168, 288, 504}
    assert len({h for h, _ in cells}) == 4
    assert not any("explorer" in h for h, _ in cells)


def test_every_block_arm_is_the_contract_block_plus_its_class_mix(stage_b):
    manifest, _ = stage_b
    block = build.load_block()
    assert manifest["joint_eval"]["baseline_block"] == block
    for tier_id, tier in manifest["tiers"].items():
        meta = tier["joint_eval"]
        if meta["arm"] == "reproduction":
            assert len(meta["changed_paths"]) > 1, tier_id
            continue
        effective = dict(tier["config_overrides"])
        assert set(effective.pop("ship_graph")) == {"agent_classes"}, tier_id
        assert effective == block, tier_id
        assert [c["path"] for c in meta["changed_paths"]] == [
            build.CLASS_MIX_PATH,
        ], tier_id


@pytest.mark.parametrize("hull", sorted(build.HULLS))
def test_class_mix_places_the_declared_roles_exactly(hull):
    spec = build.HULLS[hull]
    shipped = build.shipped_classes()
    mix = build.class_mix(hull)
    assert [c["class_id"] for c in mix] == [c["class_id"] for c in shipped]
    for role, total in spec["intended_roles"].items():
        counts = [
            c["fraction"] * spec["num_agents"]
            for c in mix if c["role_group"] == role
        ]
        assert all(abs(x - round(x)) < 1e-9 for x in counts)
        assert round(sum(counts)) == total
        old = [c["fraction"] for c in shipped if c["role_group"] == role]
        for count, fraction in zip(counts, old):
            assert abs(count - fraction / sum(old) * total) < 1.0
    untouched = [
        {k: v for k, v in c.items() if k != "fraction"} for c in mix
    ]
    assert untouched == [
        {k: v for k, v in c.items() if k != "fraction"} for c in shipped
    ]


def test_class_mix_refuses_a_platform_that_disagrees_with_the_design(monkeypatch):
    monkeypatch.setattr(build, "declared_complement", lambda _p: (350, 100))
    with pytest.raises(SystemExit):
        build.class_mix("exp")


def test_bridge_seeds_are_paired_across_lengths(stage_b):
    manifest, _ = stage_b
    seen: dict[tuple[str, str], set] = {}
    for tier in manifest["tiers"].values():
        meta = tier["joint_eval"]
        if meta["arm"] == "bridge":
            seen.setdefault((meta["hull"], meta["stratum"]), set()).add(
                tuple(tier["seeds"]),
            )
    assert len(seen) == 12
    assert all(len(lists) == 1 for lists in seen.values())


def test_intended_roles_sum_to_the_complement(stage_b):
    manifest, _ = stage_b
    for tier in manifest["tiers"].values():
        meta = tier["joint_eval"]
        if meta["arm"] == "census":
            continue
        for key in ("intended_roles", "template_roles"):
            assert sum(meta[key].values()) == tier["num_agents"]


def test_materialize_keeps_siblings_and_declares_exactly_what_changed():
    block = build.load_block()
    effective = build.materialize(
        block, {"transmission.intra_epoch_substeps": 4},
    )
    assert effective["transmission"]["intra_epoch_substeps"] == 4
    untouched = {k: v for k, v in effective["transmission"].items()
                 if k != "intra_epoch_substeps"}
    assert untouched == {k: v for k, v in block["transmission"].items()
                         if k != "intra_epoch_substeps"}
    assert [c["path"] for c in build.changed_paths(block, effective)] == [
        "transmission.intra_epoch_substeps",
    ]
    assert block["transmission"]["intra_epoch_substeps"] == 1


def test_worker_refuses_an_undeclared_arm_difference(stage_b):
    manifest, _ = stage_b
    tier_id = "fl_je_exp_7d_quiet"
    assert [
        c["path"] for c in cell.check_arm(manifest, tier_id)["changed_paths"]
    ] == [build.CLASS_MIX_PATH]
    drifted = copy.deepcopy(manifest)
    drifted["tiers"][tier_id]["config_overrides"]["hvac"].pop(
        "transport_engine",
    )
    with pytest.raises(SystemExit):
        cell.check_arm(drifted, tier_id)


def _census_row(seed: int, burden_servings: float | None) -> dict:
    objects = [] if burden_servings is None else [{
        "source_kind": "provisioned_lot", "lot_servings": burden_servings,
        "lot_titre_gec_per_g": 100.0,
    }]
    return {
        "seed": seed, "objects": objects,
        "provisioned_source": {"norwalk_gi": {"n_contaminated": len(objects)}},
    }


def test_selection_rule_orders_by_boarding_burden_only():
    rows = [_census_row(s, None) for s in range(1000, 1400)]
    rows += [_census_row(2000 + i, float(i + 1)) for i in range(100)]
    picked = build.select_hull(rows)
    diag = picked["diagnostic"]
    assert diag["quiet"] == list(range(1000, 1020))
    assert diag["outbreak"] == list(range(2080, 2100))
    assert diag["near"] == list(range(2000, 2020))
    assert not set(diag["near"]) & set(diag["outbreak"])
    for source, frame_n in (("uncontaminated", 400), ("contaminated", 100)):
        sample = picked["evaluation"][source]
        assert len(sample["seeds"]) == build.PILOT_SEEDS
        assert sample["frame_n"] == frame_n
        assert sample["inclusion_probability"] == pytest.approx(20 / frame_n)
        assert sample["source_weight"] == pytest.approx(frame_n / 500)


def test_evaluation_sample_ignores_burden():
    base = [_census_row(2000 + i, float(i + 1)) for i in range(100)]
    flipped = [_census_row(2000 + i, float(100 - i)) for i in range(100)]
    quiet = [_census_row(s, None) for s in range(1000, 1100)]
    a = build.select_hull(quiet + base)["evaluation"]["contaminated"]["seeds"]
    b = build.select_hull(quiet + flipped)["evaluation"]["contaminated"]["seeds"]
    assert a == b


def _series(pax: list[int], crew: list[int]) -> list[dict]:
    return [
        {"epoch": i, "passenger_complement": 100, "crew_complement": 100,
         "cumulative_reported_cases_passenger": p,
         "cumulative_reported_cases_crew": c}
        for i, (p, c) in enumerate(zip(pax, crew))
    ]


@pytest.mark.parametrize(("pax", "crew", "expected"), [
    ([0, 3, 3], [0, 0, 3], "passenger_first"),
    ([0, 0, 3], [0, 3, 3], "crew_first"),
    ([0, 3, 3], [0, 3, 3], "same_epoch"),
    ([0, 2, 2], [0, 2, 2], "neither"),
])
def test_first_role_classes(pax, crew, expected):
    assert cell.first_role(_series(pax, crew))["first_role"] == expected


def test_first_role_is_missing_not_neither_without_a_role_series():
    assert cell.first_role([])["first_role"] == "missing"
    broken = _series([0, 5], [0, 5])
    del broken[1]["cumulative_reported_cases_crew"]
    assert cell.first_role(broken)["first_role"] == "missing"


def test_reporting_curve_day_zero_holds_the_embarkation_reports():
    series = _series([2] * 24 + [5] * 24, [0] * 48)
    block = cell.curves(
        series, {"clinical_cases": []}, 24, {"passenger": 1, "crew": 0},
    )
    assert block["preboarding_declared_passenger"] == 1
    assert block["epoch0_cumulative_reported_passenger"] == 2
    assert block["reported_daily_passenger"] == [2, 3]
    assert "pre-boarding" in block["day0_label"]
    assert block["line_list_received"] is True
    assert cell.curves(series, {}, 24)["line_list_received"] is False


def test_zero_event_bound_follows_the_declared_convention():
    assert readout.zero_event_upper(300) == pytest.approx(0.00994, abs=5e-5)
    assert readout.zero_event_upper(20) == pytest.approx(0.139, abs=1e-3)
    assert readout.zero_event_upper(300) < readout.zero_event_upper(20)


@pytest.mark.parametrize(("states", "defects", "expected"), [
    ({"a": "in", "b": "in"}, [], "precision"),
    ({"a": "in", "b": "undetermined"}, [], "uncertainty"),
    ({"a": "in", "b": "out"}, [], "population_geometry"),
    ({"a": "out", "b": "out"}, [], "reconstruction"),
    ({"a": "in", "b": "in"}, ["repro 15/16"], "justified_defect_fix"),
])
def test_continuation_map(states, defects, expected):
    assert readout.continuation(states, defects)["continuation"] == expected


def _rate(posted: int, n: int) -> dict:
    low, high = readout.clopper_pearson(posted, n)
    return {"posting_rate": posted / n, "posting_rate_ci95": [low, high]}


def test_a_posting_quiet_stratum_is_a_diagnostic_state_not_a_gate():
    bands = build.DIAGNOSTIC_BANDS
    rows = {"quiet": _rate(0, 20), "near": _rate(8, 20), "outbreak": _rate(18, 20)}
    assert readout.band_state(rows, bands)["state"] == "in"
    rows["quiet"] = _rate(1, 20)
    assert readout.band_state(rows, bands)["state"] == "undetermined"
    rows["quiet"] = _rate(12, 20)
    assert readout.band_state(rows, bands)["state"] == "out"
    assert "posting" not in json.dumps(build.TECHNICAL_COMPLETION)


def test_readout_without_archives_is_incomplete_not_a_verdict(stage_b, tmp_path):
    manifest, _ = stage_b
    result = readout.build_readout(manifest, tmp_path)
    assert result["gate"]["technically_complete"] is False
    assert result["continuation"]["continuation"] is None


def test_worker_and_readout_fingerprints_agree_and_ignore_the_commit():
    voyage = {
        "parameters": {"seed": 7, "engine_git_sha": "aaa", "x": (1, 2)},
        "timeseries": [{"epoch": 0, "v": 0.1}], "derived": {"a": None},
        "summary": {"n": 1}, "cost_accounting": {}, "trigger_status": "ok",
    }
    archived = json.loads(json.dumps({**voyage, "joint_eval": {"extra": 1}}))
    assert cell.fingerprint(voyage) == readout.archive_fingerprint(archived)
    later = copy.deepcopy(voyage)
    later["parameters"]["engine_git_sha"] = "bbb"
    later["parameters"]["tier_id"] = "renamed"
    assert cell.fingerprint(later) == cell.fingerprint(voyage)
    moved = copy.deepcopy(voyage)
    moved["timeseries"][0]["v"] = 0.2
    assert cell.fingerprint(moved) != cell.fingerprint(voyage)


def test_selection_refuses_a_census_that_is_not_the_declared_frame(tmp_path):
    for hull, start in build.CENSUS_START.items():
        seeds = list(range(start, start + build.CENSUS_SEEDS_PER_HULL))
        if hull == "meg":
            seeds[-1] = seeds[0]
        (tmp_path / f"je_census_{hull}_chunk000000.jsonl").write_text(
            "\n".join(json.dumps(_census_row(s, None)) for s in seeds),
        )
    with pytest.raises(SystemExit, match="meg"):
        build.select(tmp_path)


def test_median_of_an_even_ensemble_averages_the_middle_pair():
    cells = [
        {"posted_epoch": None, "first_role": "neither", "environment": {},
         "burden": {"passenger_complement": 90, "crew_complement": 10,
                    "rep_pax_n": n, "rep_crew_n": 0}}
        for n in (0, 2, 4, 10)
    ]
    row = readout.rate_row("t", {"hull": "h", "epochs": 168}, cells)
    assert row["reported_ar_median"] == pytest.approx(0.03)


def _archive(root, tier_id, seed, value):
    import zipfile
    path = root / tier_id
    path.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path / f"s{seed}.zip", "w") as archive:
        archive.writestr("summary.json", json.dumps({
            "parameters": {"seed": seed, "tier_id": tier_id},
            "timeseries": [{"epoch": 0, "v": value}],
        }))


def test_reference_fingerprints_come_from_the_source_tier_only(tmp_path):
    _archive(tmp_path, "continuous", 1, 0.1)
    _archive(tmp_path, "discrete", 1, 0.9)
    got = readout.reference_fingerprints(tmp_path, "continuous")
    want = readout.archive_fingerprint({
        "parameters": {"seed": 1, "tier_id": "anything"},
        "timeseries": [{"epoch": 0, "v": 0.1}],
    })
    assert got == {"1": want}


def test_partial_reproduction_evidence_does_not_pass_the_gate():
    tiers = {"r": {"seeds": [1, 2], "joint_eval": {
        "arm": "reproduction", "reference_fingerprints": {"1": "x"},
    }}}
    cells = {"r": [{"seed": 1, "fingerprint": "x"},
                   {"seed": 2, "fingerprint": "y"}]}
    row = readout.reproduction_rows(tiers, cells)[0]
    assert (row["n_expected"], row["n_compared"]) == (2, 1)


def test_a_shortened_voyage_is_not_an_intended_input(stage_b):
    manifest, _ = stage_b
    tier = manifest["tiers"]["fl_je_exp_7d_quiet"]
    meta = tier["joint_eval"]
    good = {
        "num_epochs": 168, "engine_git_sha": "abc",
        "arm": {"changed_paths": meta["changed_paths"],
                "effective_sha256": "h"},
        "effective": {"mismatched": [], "runner_changed_paths": []},
        "roles": {"initialised": meta["intended_roles"],
                  "payload": meta["intended_roles"]},
    }
    assert readout.inputs_ok(good, tier, "h")
    assert not readout.inputs_ok({**good, "num_epochs": 48}, tier, "h")
