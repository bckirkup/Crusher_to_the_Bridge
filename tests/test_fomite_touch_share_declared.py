"""Behavioral guards for the declared touch-share arm (NORO-TOUCH-SHARE-01).

The shipped ``data/config/fomite_touch_share_declared.json`` must parse,
enumerate exactly the classes the engine enumerates under the ``shared``
reading, and stay inert under ``areal``; graded per-class sensitivity is
measured on a single ``public`` unit, per ci-test-design (no goldens).
"""

from __future__ import annotations

import gzip
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import engines.fomite_surfaces as fomite_surfaces  # noqa: E402
from engines.fomite_surfaces import (  # noqa: E402
    PerSurfaceConfig,
    PerSurfaceFomiteState,
    load_declared_share_table,
    parse_per_surface_config,
    unit_item_counts,
)
from tests.test_fomite_per_surface import (  # noqa: E402
    PATHOGEN,
    PER_SURFACE,
    POOLED,
    _core,
    _drive,
    _population,
)
from tools.noro_diag import (  # noqa: E402
    per_host_dose_challenge as challenge,
)
from tools.noro_diag import (  # noqa: E402
    touch_share_coincidence_readout as readout,
)

TABLE_PATH = REPO_ROOT / "data" / "config" / "fomite_touch_share_declared.json"

PROVENANCE_KEYS = {"source", "setting", "counted", "grade", "mapping", "derivation"}


def _declared_config(table: dict) -> PerSurfaceConfig:
    return parse_per_surface_config(
        {
            **PER_SURFACE,
            "fomite_touch_share": "declared",
            "fomite_touch_share_table": table,
        },
    )


def test_shipped_table_parses_and_matches_unit_inventory() -> None:
    table = load_declared_share_table(TABLE_PATH)
    cfg = _declared_config(table)
    assert cfg.touch_share == "declared"
    for zone_class, shares in table.items():
        assert sum(shares.values()) == pytest.approx(1.0, abs=1e-9)
        assert set(shares) == set(
            unit_item_counts(zone_class, "shared", 1),
        )
    raw = json.loads(TABLE_PATH.read_text())
    declared_zones = set(raw["shares"])
    fallback_zones = set(raw["areal_fallback"])
    assert declared_zones | fallback_zones == set(
        fomite_surfaces.ZONE_ITEM_SETS,
    )
    assert not declared_zones & fallback_zones
    for entry in raw["provenance"].values():
        assert PROVENANCE_KEYS <= set(entry)


def test_shipped_table_shares_are_within_bounds() -> None:
    table = load_declared_share_table(TABLE_PATH)
    for shares in table.values():
        for share in shares.values():
            assert 0.0 < share <= 1.0


def test_incomplete_table_is_refused() -> None:
    with pytest.raises(ValueError, match="fomite_touch_share_table"):
        _declared_config({"public": {"button_or_dispenser": 1.0}})


def test_item_reading_mismatch_is_refused() -> None:
    with pytest.raises(ValueError, match="item_reading"):
        load_declared_share_table(TABLE_PATH, item_reading="hardware")


def test_table_is_inert_under_areal() -> None:
    table = load_declared_share_table(TABLE_PATH)
    plain = _core({**PER_SURFACE, "fomite_touch_share": "areal"}, seed=11)
    with_table = _core(
        {
            **PER_SURFACE,
            "fomite_touch_share": "areal",
            "fomite_touch_share_table": table,
        },
        seed=11,
    )
    hist_plain = _drive(plain, _population())
    hist_table = _drive(with_table, _population())
    for step_p, step_t in zip(hist_plain, hist_table):
        for zone, mass in step_p["pools"].items():
            assert mass == pytest.approx(step_t["pools"][zone], rel=1e-12)
        assert step_p["rng"] == step_t["rng"]


def test_per_surface_areal_matches_pooled_short_run() -> None:
    pooled = _core(POOLED, seed=11)
    arm = _core(PER_SURFACE, seed=11)
    hist_p = _drive(pooled, _population(), epochs=4)
    hist_a = _drive(arm, _population(), epochs=4)
    for step_p, step_a in zip(hist_p, hist_a):
        for zone, mass in step_p["pools"].items():
            assert mass == pytest.approx(step_a["pools"][zone], rel=1e-9)
        assert step_p["rng"] == step_a["rng"]


def _public_state(button_share: float) -> PerSurfaceFomiteState:
    """One public unit with the given declared share for the button class.

    The residual is split door_lever:grab_rail_m at the shipped areal ratio
    (0.0128 : 2.0 area-weighted over counts 8 : 20).
    """
    residual = 1.0 - button_share
    door_share = residual * (0.0128 / 2.0128)
    cfg = PerSurfaceConfig(
        touch_share="declared",
        declared_shares={
            "public": {
                "door_lever": door_share,
                "button_or_dispenser": button_share,
                "grab_rail_m": residual - door_share,
            },
        },
    )
    return PerSurfaceFomiteState(cfg)


def test_graded_button_share_moves_class_mass_and_request() -> None:
    deposit_mass = 1.0e6
    mass_by_share: dict[float, dict[str, float]] = {}
    request_by_share: dict[float, dict[str, float]] = {}
    for share in (0.1, 0.4, 0.8):
        state = _public_state(share)
        inv = state.register_unit("Lounge_A", "public", 40.0, 1, 0.5)
        state.deposit("Lounge_A", PATHOGEN, deposit_mass, inv)
        mass_by_share[share] = {
            c: state.mass.get(("Lounge_A", PATHOGEN, c), 0.0)
            for c in inv.counts
        }
        request_by_share[share] = state.pickup_requests(
            inv, "Lounge_A", PATHOGEN, 10.0, 0.1, 0.01, 0.5,
        )
    for per_class in mass_by_share.values():
        assert sum(per_class.values()) == pytest.approx(deposit_mass)
    for item_class in ("button_or_dispenser",):
        masses = [mass_by_share[s][item_class] for s in (0.1, 0.4, 0.8)]
        assert masses[0] < masses[1] < masses[2]
    rails = [mass_by_share[s]["grab_rail_m"] for s in (0.1, 0.4, 0.8)]
    assert rails[0] > rails[1] > rails[2]
    buttons = [
        request_by_share[s]["button_or_dispenser"] for s in (0.1, 0.4, 0.8)
    ]
    assert buttons[0] < buttons[1] < buttons[2]
    for share, requests in request_by_share.items():
        for item_class, request in requests.items():
            assert 0.0 <= request <= mass_by_share[share][item_class]
            assert math.isfinite(request)


def _cell(
    seed: int,
    delivered: dict[int, float],
    by_class: dict,
    credited: float,
    secondaries: int,
    witness: dict | None = None,
) -> dict:
    return {
        "seed": seed,
        "hosts": [
            {"agent_id": aid, "fomite_delivered_gec": mass}
            for aid, mass in delivered.items()
        ],
        "fomite_delivered_by_host": {
            str(aid): mass for aid, mass in delivered.items() if mass > 0.0
        },
        "fomite_by_class": by_class,
        "fomite_witness": dict(witness or {}),
        "reconciliation": {"sum_credited_scaled_gec": credited},
        "transmission": {"secondaries": secondaries},
    }


def test_readout_deposit_event_alignment() -> None:
    witness = {
        "surface_deposit_calls": 27,
        "surface_mass_deposited_gec": 6832.0,
        "hand_to_mouth_calls": 1036,
    }
    base = _cell(1, {1: 1.0}, {}, 10.0, 1, witness)
    arm_aligned = _cell(1, {1: 1.0}, {}, 10.0, 1, dict(witness))
    row = readout.compare_seed(
        base, arm_aligned, "public.button_or_dispenser",
    )
    assert row["deposit_events_aligned"] is True
    assert row["deposit_calls_areal"] == 27
    assert row["deposit_calls_declared"] == 27
    assert row["deposited_gec_areal"] == pytest.approx(6832.0)
    assert row["hand_to_mouth_calls_declared"] == 1036
    arm_diverged = _cell(1, {1: 1.0}, {}, 10.0, 1, {
        **witness, "surface_deposit_calls": 26,
        "hand_to_mouth_calls": 13771,
    })
    row_diff = readout.compare_seed(
        base, arm_diverged, "public.button_or_dispenser",
    )
    assert row_diff["deposit_events_aligned"] is False
    assert row_diff["hand_to_mouth_calls_declared"] == 13771
    agg = readout.aggregate([row, row_diff])
    assert agg["n_seeds_deposit_aligned"] == 1
    assert agg["deposit_calls_declared"]["max"] == 27
    assert agg["hand_to_mouth_calls_declared"]["max"] == 13771


def _write_cell(directory: Path, tag: str, cell: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (
        f"per_host_dose_challenge_{tag}_seed{cell['seed']}.json.gz"
    )
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(cell, handle)


def test_readout_seed_statistics() -> None:
    base = _cell(
        1,
        {1: 1.0, 2: 1.0},
        {
            "public.button_or_dispenser": {
                "requested_gec": 4.0, "delivered_gec": 2.0,
                "calls": 4, "capped_calls": 0, "hosts_credited": 2,
            },
            "public.grab_rail_m": {
                "requested_gec": 4.0, "delivered_gec": 6.0,
                "calls": 4, "capped_calls": 0, "hosts_credited": 2,
            },
            "cabin.door_lever": {
                "requested_gec": 1.0, "delivered_gec": 2.0,
                "calls": 2, "capped_calls": 0, "hosts_credited": 1,
            },
        },
        10.0, 3,
    )
    arm = _cell(
        1,
        {1: 1.0, 3: 1.0},
        {
            "public.button_or_dispenser": {
                "requested_gec": 8.0, "delivered_gec": 6.0,
                "calls": 4, "capped_calls": 1, "hosts_credited": 3,
            },
            "public.grab_rail_m": {
                "requested_gec": 8.0, "delivered_gec": 2.0,
                "calls": 4, "capped_calls": 0, "hosts_credited": 3,
            },
            "cabin.door_lever": {
                "requested_gec": 2.0, "delivered_gec": 4.0,
                "calls": 4, "capped_calls": 0, "hosts_credited": 2,
            },
        },
        20.0, 5,
    )
    row = readout.compare_seed(base, arm, "public.button_or_dispenser")
    assert row["jaccard"] == pytest.approx(1.0 / 3.0)
    assert row["n_hosts_areal"] == 2
    assert row["n_hosts_declared"] == 2
    assert row["gini_areal"] == pytest.approx(0.0)
    assert row["gini_declared"] == pytest.approx(0.0)
    assert row["delivered_ratio"] == pytest.approx(1.0)
    assert row["credited_scaled_ratio"] == pytest.approx(2.0)
    assert row["secondaries_delta"] == 2
    button = row["per_class"]["public.button_or_dispenser"]
    assert button["delivered_share_areal"] == pytest.approx(0.2)
    assert button["delivered_share_declared"] == pytest.approx(0.5)
    assert button["zone_share_areal"] == pytest.approx(0.25)
    assert button["zone_share_declared"] == pytest.approx(0.75)
    assert row["focus_share_gain"] == pytest.approx(0.75 - 0.25)
    assert button["capped_share_declared"] == pytest.approx(0.25)


def test_readout_gini_and_verdict() -> None:
    assert readout.gini([1.0, 1.0, 2.0]) == pytest.approx(1.0 / 6.0)
    assert readout.top_decile_share([1.0, 1.0, 2.0]) == pytest.approx(0.5)
    base = _cell(1, {1: 5.0, 2: 3.0}, {}, 10.0, 3)
    arm = _cell(1, {1: 4.0, 2: 4.0}, {}, 10.0, 3)
    row = readout.compare_seed(base, arm, "public.button_or_dispenser")
    assert row["jaccard"] == pytest.approx(1.0)
    agg = readout.aggregate([row])
    assert agg["identical_host_sets_all_seeds"] is True
    assert agg["verdict"] == "inert"


def test_readout_loads_gz_cells(tmp_path: Path) -> None:
    for seed in (7, 8):
        _write_cell(tmp_path / "a", "per_surface_areal", _cell(
            seed, {1: 1.0}, {}, 10.0, 1,
        ))
        _write_cell(tmp_path / "d", "per_surface_declared", _cell(
            seed, {1: 1.0}, {}, 10.0, 2,
        ))
    result = readout.readout(
        tmp_path / "d", "per_surface_declared",
        tmp_path / "a", "per_surface_areal",
        "public.button_or_dispenser",
    )
    assert result["seeds"] == [7, 8]
    assert result["aggregate"]["verdict"] == "inert"


def _repo_tmp() -> Path:
    """A scratch directory under the repo root (removed by the caller)."""
    return Path(tempfile.mkdtemp(dir=REPO_ROOT))


def test_declared_table_outside_repo_is_refused(tmp_path: Path) -> None:
    outside = tmp_path / "x.json"
    outside.write_text(
        json.dumps({"item_reading": "shared", "shares": {}}),
    )
    with pytest.raises(ValueError, match="outside the repository"):
        load_declared_share_table(outside)


def test_declared_table_missing_shares_is_refused() -> None:
    scratch = _repo_tmp()
    try:
        target = scratch / "x.json"
        target.write_text(json.dumps({"item_reading": "shared"}))
        with pytest.raises(ValueError, match="shares"):
            load_declared_share_table(target)
    finally:
        shutil.rmtree(scratch)


def test_readout_safe_path_refuses_outside() -> None:
    with pytest.raises(ValueError, match="outside the allowed directory"):
        readout._safe_path("/etc/hostname")


def test_readout_empty_host_sets_and_zero_denominators() -> None:
    base = _cell(1, {}, {}, 0.0, 0)
    arm = _cell(1, {}, {}, 0.0, 0)
    row = readout.compare_seed(base, arm, "public.button_or_dispenser")
    assert row["jaccard"] == pytest.approx(1.0)
    assert row["gini_declared"] == pytest.approx(0.0)
    assert row["top_decile_declared"] == pytest.approx(0.0)
    assert row["delivered_ratio"] is None
    assert row["credited_scaled_ratio"] is None
    assert row["focus_share_gain"] == pytest.approx(0.0)
    assert readout.gini([7.0]) == pytest.approx(0.0)
    assert readout.top_decile_share([]) == pytest.approx(0.0)
    assert readout.top_decile_share([0.0]) == pytest.approx(0.0)


def _fabricated_row(jaccard: float, gain: float, capped: float) -> dict:
    return {
        "n_hosts_areal": 10,
        "n_hosts_declared": 10,
        "jaccard": jaccard,
        "gini_areal": 0.5,
        "gini_declared": 0.5,
        "top_decile_areal": 0.5,
        "top_decile_declared": 0.5,
        "delivered_ratio": 1.0,
        "credited_scaled_ratio": 1.0,
        "secondaries_delta": 0,
        "focus_share_gain": gain,
        "deposit_calls_areal": 10,
        "deposit_calls_declared": 10,
        "hand_to_mouth_calls_areal": 100,
        "hand_to_mouth_calls_declared": 100,
        "deposit_events_aligned": True,
        "per_class": {
            "public.button_or_dispenser": {"capped_share_declared": capped},
        },
    }


def test_readout_verdict_branches() -> None:
    changed = readout.aggregate(
        [_fabricated_row(0.5, 0.2, 0.2) for _ in range(15)],
    )
    assert changed["verdict"] == "changes_coincidence"
    assert changed["focus_class_share_gain_seeds"] == 15
    assert changed["cap_flags"] == ["public.button_or_dispenser"]
    indeterminate = readout.aggregate(
        [_fabricated_row(0.5, 0.0, 0.0)],
    )
    assert indeterminate["verdict"] == "indeterminate"
    assert indeterminate["identical_host_sets_all_seeds"] is False


def test_readout_no_shared_seeds_exits(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        readout.readout(
            tmp_path / "d", "per_surface_declared",
            tmp_path / "a", "per_surface_areal",
            "public.button_or_dispenser",
        )


def test_readout_main_end_to_end_deterministic() -> None:
    scratch = _repo_tmp()
    try:
        for seed in (7, 8):
            _write_cell(scratch / "a", "per_surface_areal", _cell(
                seed, {1: 1.0, 2: 0.5}, {}, 10.0, 1,
            ))
            _write_cell(scratch / "d", "per_surface_declared", _cell(
                seed, {1: 1.0, 3: 0.5}, {}, 10.0, 2,
            ))
        _write_cell(scratch / "d", "per_surface_declared", _cell(
            9, {1: 1.0}, {}, 10.0, 2,
        ))
        out_dir = scratch / "out"
        argv = [
            "--arm-dir", str(scratch / "d"),
            "--base-dir", str(scratch / "a"),
            "--out", str(out_dir),
        ]
        assert readout.main(list(argv)) == 0
        written = out_dir / "touch_share_coincidence_per_surface_declared.json"
        first = written.read_bytes()
        result = json.loads(first)
        assert result["aggregate"]["verdict"] == "indeterminate"
        assert len(result["per_seed"]) == 2
        assert result["seeds_only_in_arm"] == [9]
        assert readout.main(list(argv)) == 0
        assert written.read_bytes() == first
    finally:
        shutil.rmtree(scratch)


def _parse(argv: list[str]):
    return challenge.parse_args([*argv, "--out", "tmp_tsc_smoke"])


def test_cli_requires_table_for_declared() -> None:
    with pytest.raises(SystemExit):
        _parse(
            [
                "--fomite-representation", "per_surface",
                "--fomite-touch-share", "declared",
            ],
        )


def test_cli_requires_per_surface_for_touch_share() -> None:
    with pytest.raises(SystemExit):
        _parse(["--fomite-touch-share", "areal"])


def test_cli_refuses_table_outside_repo() -> None:
    with pytest.raises(SystemExit):
        _parse(
            [
                "--fomite-representation", "per_surface",
                "--fomite-touch-share", "declared",
                "--fomite-touch-share-table", "/etc/passwd",
            ],
        )


def test_cli_accepts_shipped_table() -> None:
    args = _parse(
        [
            "--fomite-representation", "per_surface",
            "--fomite-touch-share", "declared",
            "--fomite-touch-share-table", str(TABLE_PATH),
        ],
    )
    assert args.fomite_touch_share == "declared"
    assert args.fomite_touch_share_table == str(
        TABLE_PATH.resolve(),
    )
