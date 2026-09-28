"""Tests for tools/noro_diag/import_map_readout.py."""
import json
import sys
import zipfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "noro_diag"))

import import_map_readout as readout  # noqa: E402


def _write_run_zip(
    root: Path, tier: str, run_id: str, params: dict,
    *, ignited: bool, peak: float, posted: bool, census: dict | None = None,
) -> None:
    tier_dir = root / tier
    tier_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "run_id": run_id,
        "parameters": {"run_id": run_id, "tier_id": tier, **params},
        "census": {"ignited": ignited, "n_acquired": 3 if ignited else 0},
        "derived": {
            "peak_prevalence": peak,
            "vsp_trigger_epoch": 40 if posted else None,
        },
        "initiation": {
            "resolved": {
                "rate_mode": "renewal",
                "symptomatic_stream": {"enabled": True},
                "symptomatic_passenger_prevalence": 0.0002746,
            },
            "manifest": {"boarding": {"norwalk_gi": {
                "composition": {"symptomatic": 1},
            }}},
        },
    }
    payload = census or {
        "census_epochs": [
            {"epoch": 0, "infected": 1},
            {"epoch": 1, "infected": 5},
        ],
        "emits": [
            {"zone_type": "Cabin_Corridor", "episode_load": 1.0},
            {"zone_type": "Dining", "episode_load": 1.0},
        ],
    }
    with zipfile.ZipFile(tier_dir / f"{run_id}.zip", "w") as zf:
        zf.writestr("summary.json", json.dumps(summary))
        zf.writestr("growth_census.json.gz", __import__("gzip").compress(
            json.dumps(payload).encode(),
        ))


def _params(seed: int, rung: str, nsf: float = 0.29, **kw) -> dict:
    rid = f"fl_x_{rung}_nsf{nsf}_s{seed}"
    return {
        "run_id": rid,
        "boarding_mechanism_rung": rung,
        "never_symptomatic_fraction": nsf,
        "dose_adjustment": 7.57,
        "pathogen": "norovirus",
        "num_agents": 450,
        **kw,
    }


def test_collect_groups_runs_into_cells(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    for seed in (8105, 8106):
        _write_run_zip(
            root, "fl_spr_12d_ren",
            f"fl_x_renewal_stationary_s{seed}",
            _params(seed, "renewal_stationary"),
            ignited=seed == 8105, peak=12.0, posted=False,
        )
        _write_run_zip(
            root, "fl_spr_12d_ren",
            f"fl_x_reportable_s{seed}",
            _params(seed, "reportable"),
            ignited=True, peak=42.0, posted=True,
        )
    report = readout.build_report(root)
    cells = report["tiers"]["fl_spr_12d_ren"]["cells"]
    assert len(cells) == 2
    for key, entry in cells.items():
        assert len(entry["rows"]) == 2
    disc = report["discordance"]
    assert len(disc) == 1
    row = disc[0]
    assert row["shared"] == 2
    assert row["b_only"] == 1
    assert row["a_only"] == 0


def test_cell_metrics_and_labels(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    _write_run_zip(
        root, "fl_exp_12d_scr", "fl_x_shipped_s8000",
        _params(8000, "shipped",
                boarding_passenger_prevalence=0.0325,
                boarding_crew_prevalence=0.0185),
        ignited=True, peak=3.0, posted=False,
    )
    report = readout.build_report(root)
    (row,) = report["tiers"]["fl_exp_12d_scr"]["table"]
    assert row["n"] == 1
    assert row["ignited"] == 1
    assert row["took_off"] == 0
    assert row["posted"] == 0
    assert "screening" in row["label"]
    assert row["depth_max"] == 5
    assert row["placement"]["total_emits"] == 2


def test_stream_witness_counts_drawn_symptomatic(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    _write_run_zip(
        root, "fl_exp_12d_ren", "fl_x_reportable_s8000",
        _params(8000, "reportable"), ignited=True, peak=0.0, posted=False,
    )
    report = readout.build_report(root)
    (witness,) = report["tiers"]["fl_exp_12d_ren"]["witness"]
    assert witness["resolved_rate_mode"] == "renewal"
    assert witness["resolved_stream"] is True
    assert witness["symptomatic_drawn_total"] == 1
    assert witness["fields_uniform"] is True


def test_render_markdown_smoke(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    _write_run_zip(
        root, "fl_exp_12d_alpha", "fl_x_reportable_s8000",
        _params(8000, "reportable"), ignited=False, peak=0.0, posted=False,
    )
    md = readout.render_markdown(readout.build_report(root))
    assert "fl_exp_12d_alpha" in md
    assert "flagged" in md.lower()
    assert "Symptomatic-stream witness" in md


def test_missing_summary_member_skipped(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    tier_dir = root / "fl_exp_12d_ren"
    tier_dir.mkdir(parents=True)
    with zipfile.ZipFile(tier_dir / "broken.zip", "w") as zf:
        zf.writestr("other.json", "{}")
    report = readout.build_report(root)
    assert report["tiers"]["fl_exp_12d_ren"]["table"] == []
