"""Unit tests for the onset-funnel readout's decomposition math.

The readout only restates committed payload echoes, so its correctness
is the bookkeeping on ``funnel_hosts`` + ``campaign_specimen_log``;
these pin it on synthetic cells.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "covid_onset_funnel_readout",
        _ROOT / "tools" / "covid_onset_funnel_readout.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cell_payload(
    hosts: dict[int, dict[str, int]],
    log: list[dict],
    observables: dict | None = None,
) -> dict:
    return {
        "arm_id": "boxed_s1s2",
        "design_id": "covid_crew_reach_01",
        "observables": observables or {},
        "funnel_hosts": {str(k): v for k, v in hosts.items()},
        "campaign_specimen_log": log,
    }


def _log_row(aid: int, day: int, symptomatic: bool | None = None) -> dict:
    return {
        "agent_id": aid,
        "day": day,
        "positive": True,
        "symptomatic_at_specimen": symptomatic,
    }


def test_channel_split_campaign_vs_passive(mod):
    payload = _cell_payload(
        hosts={
            1: {"infection_day": 3, "presented_day": 9, "confirmed_day": 16},
            2: {"infection_day": 4, "presented_day": 10, "confirmed_day": 8},
        },
        log=[
            _log_row(1, 16, True),
            _log_row(2, 16, True),
        ],
    )
    cell = mod._decompose_cell(payload)
    # Host 1's confirming specimen is the day-16 campaign swab; host 2 was
    # confirmed on day 8 before that campaign day.
    assert cell["confirmed_channel"] == {"campaign": 1, "passive": 1}
    assert cell["confirmed_pre_onset_catch"] == 1
    assert cell["confirmed_never_presented"] == 0


def test_campaign_positive_split_uses_symptomatic_flag(mod):
    payload = _cell_payload(
        hosts={
            1: {"infection_day": 3, "presented_day": 9},
            2: {"infection_day": 4, "presented_day": 8},
            3: {"infection_day": 5},
            # Host 4 presents the same day it is swabbed: the flag says the
            # swab came first, so it is a pre-onset catch, not post.
            4: {"infection_day": 6, "presented_day": 10},
        },
        log=[
            _log_row(1, 8, False),
            _log_row(2, 10, True),
            _log_row(3, 10, False),
            _log_row(4, 10, False),
        ],
    )
    cell = mod._decompose_cell(payload)
    assert cell["campaign_positive"]["specimens"] == {
        "never_presented": 1,
        "pre_onset": 2,
        "post_onset": 1,
    }
    assert cell["campaign_positive"]["hosts"] == {
        "never_presented": 1,
        "pre_onset": 2,
        "post_onset": 1,
    }


def test_unconfirmed_drain_modes(mod):
    payload = _cell_payload(
        hosts={
            1: {"infection_day": 3},  # never swabbed
            2: {"infection_day": 6, "specimen_day": 2},  # pre-infection swab
            3: {"infection_day": 4, "specimen_day": 9, "presented_day": 12},
            4: {"infection_day": 5, "specimen_day": 10},
        },
        log=[],
    )
    drains = mod._decompose_cell(payload)["unconfirmed_infected_drains"]
    assert drains == {
        "never_swabbed_never_presented": 1,
        "swabbed_only_pre_infection_never_presented": 1,
        "swabbed_while_infected_negative_presented": 1,
        "swabbed_while_infected_negative_never_presented": 1,
    }


def test_dated_share_and_pool_medians_use_scorer_takeoff_gate(mod):
    live = mod._decompose_cell(
        _cell_payload(
            hosts={
                1: {"infection_day": 1, "presented_day": 2, "confirmed_day": 3},
                2: {"infection_day": 2},
            },
            log=[],
            observables={"recorded_onsets": 15, "seed": 7},
        )
    )
    # Infectious but under the scorer's recorded_onsets >= 10 takeoff gate.
    quiet = mod._decompose_cell(
        _cell_payload(
            hosts={9: {"infection_day": 2, "presented_day": 3, "confirmed_day": 4}},
            log=[],
            observables={"recorded_onsets": 5},
        )
    )
    dead = mod._decompose_cell(
        _cell_payload(hosts={}, log=[], observables={"recorded_onsets": 0})
    )
    assert live["dated_share_of_confirmed"] == pytest.approx(15.0)
    pooled = mod._pool([live, quiet, dead], takeoff_onsets=10)
    assert pooled["cells"] == 3
    assert pooled["takeoff_cells"] == 1
    assert pooled["medians"]["infections_total"] == 2
    assert pooled["recorded_onsets"] == 20


def test_main_writes_report_and_summary(mod, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path)
    cells_dir = tmp_path / "cells"
    cells_dir.mkdir()
    (cells_dir / "cell_7.json").write_text(
        json.dumps(
            _cell_payload(
                hosts={
                    1: {
                        "infection_day": 1,
                        "presented_day": 2,
                        "confirmed_day": 3,
                    },
                    2: {"infection_day": 2},
                },
                log=[_log_row(1, 3, True)],
                observables={
                    "seed": 7,
                    "theta": 3.162e11,
                    "recorded_onsets": 12,
                    "campaign_positives": 1,
                    "asymptomatic_share": 0.5,
                },
            )
        )
    )
    out_rel = "out/report.json"
    assert mod.main(["--cells", "cells", "--out", out_rel]) == 0
    written = json.loads((tmp_path / out_rel).read_text())
    assert written["pooled"]["takeoff_cells"] == 1
    assert json.loads(capsys.readouterr().out)["cells"] == 1


def test_main_errors_on_empty_cells(mod, tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path)
    (tmp_path / "cells").mkdir()
    with pytest.raises(ValueError, match=r"no cell_\*\.json"):
        mod.main(["--cells", "cells", "--out", "out.json"])
