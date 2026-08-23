"""The units guard has to fail on the bug it was written for.

``scripts/clock_guard.py`` is the only mechanical defence against a day-valued
threshold being compared to an epoch counter, which is exactly the defect that
ran natural history 24x fast. A guard that cannot be shown to fire is not a
defence, so each rule is exercised on source that should trip it and on source
that should not.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
sys.path.insert(0, REPO_ROOT)

from scripts.clock_guard import (  # noqa: E402
    check_config_file,
    check_python_file,
    main,
)


def _write(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


# ── CLOCK001: mixed-unit comparison ──────────────────────────────────────

MIXED_SOURCES = [
    "if time_infected >= recovery_day:\n    pass\n",
    "if agent.time_infected > profile.onset_day:\n    pass\n",
    "if inf['time_infected'] >= prof['recovery_day']:\n    pass\n",
    "if recovery_day < epoch:\n    pass\n",
    "if dpi >= shed_epochs:\n    pass\n",
]


@pytest.mark.parametrize("body", MIXED_SOURCES)
def test_a_day_compared_to_an_epoch_is_refused(tmp_path: Path, body: str) -> None:
    findings = check_python_file(_write(tmp_path, "m.py", body))
    assert [f.rule for f in findings] == ["CLOCK001"]


CLEAN_SOURCES = [
    "if days_infected >= recovery_day:\n    pass\n",
    "if time_infected >= recovery_epochs:\n    pass\n",
    "if clock.days_elapsed(time_infected) >= recovery_day:\n    pass\n",
    "if epoch >= delay_epochs:\n    pass\n",
    "if name == 'recovery_day':\n    pass\n",
]


@pytest.mark.parametrize("body", CLEAN_SOURCES)
def test_same_unit_comparisons_pass(tmp_path: Path, body: str) -> None:
    assert check_python_file(_write(tmp_path, "c.py", body)) == []


def test_a_chained_comparison_is_inspected_pairwise(tmp_path: Path) -> None:
    body = "if 0 <= time_infected <= recovery_day:\n    pass\n"
    findings = check_python_file(_write(tmp_path, "chain.py", body))
    assert [f.rule for f in findings] == ["CLOCK001"]


def test_the_message_names_both_operands(tmp_path: Path) -> None:
    body = "if time_infected >= recovery_day:\n    pass\n"
    message = check_python_file(_write(tmp_path, "m.py", body))[0].message
    assert "'time_infected'" in message
    assert "'recovery_day'" in message


# ── CLOCK002: literal conversion factor ──────────────────────────────────

@pytest.mark.parametrize(
    "body",
    [
        "hours = days * 24\n",
        "days = hours / 24.0\n",
        "epochs = hours // 24\n",
    ],
)
def test_a_bare_twenty_four_is_refused(tmp_path: Path, body: str) -> None:
    findings = check_python_file(_write(tmp_path, "f.py", body))
    assert [f.rule for f in findings] == ["CLOCK002"]


def test_an_exempt_line_is_allowed(tmp_path: Path) -> None:
    body = "phase = (hour - 4) / 24.0  # clock-exempt: hour-of-day phase\n"
    assert check_python_file(_write(tmp_path, "e.py", body)) == []


def test_twenty_four_that_is_not_a_factor_passes(tmp_path: Path) -> None:
    body = "total = 24 + offset\nsize = 1024 * 1024\n"
    assert check_python_file(_write(tmp_path, "n.py", body)) == []


def test_the_clock_module_itself_may_convert(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(REPO_ROOT)
    findings = check_python_file(Path("engines/sim_clock.py"))
    assert [f for f in findings if f.rule == "CLOCK002"] == []


def test_unparseable_source_is_reported_not_skipped(tmp_path: Path) -> None:
    findings = check_python_file(_write(tmp_path, "bad.py", "def (:\n"))
    assert [f.rule for f in findings] == ["CLOCK000"]


# ── CLOCK003: two declared clocks ────────────────────────────────────────

def test_disagreeing_epoch_durations_are_refused(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "voyage_config.json",
        json.dumps({"epoch_duration_hours": 24, "voyage": {"epoch_duration_hours": 1}}),
    )
    findings = check_config_file(path)
    assert [f.rule for f in findings] == ["CLOCK003"]


def test_disagreeing_modes_are_refused(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "config.yaml",
        "natural_history_clock: hours\nvoyage:\n  natural_history_clock: legacy_epoch_day\n",
    )
    findings = check_config_file(path)
    assert [f.rule for f in findings] == ["CLOCK003"]


def test_agreeing_declarations_pass(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "voyage_config.json",
        json.dumps({"epoch_duration_hours": 1, "voyage": {"epoch_duration_hours": 1}}),
    )
    assert check_config_file(path) == []


def test_yaml_is_read_without_a_yaml_library(tmp_path: Path) -> None:
    """The guard runs in CI before dependencies are installed.

    It shares the lint job with ``sonar_guard``, which runs on a bare
    interpreter, so importing pyyaml made the job fail with
    ``ModuleNotFoundError`` rather than checking anything.
    """
    source = (Path(REPO_ROOT) / "scripts" / "clock_guard.py").read_text()
    assert "import yaml" not in source
    path = _write(
        tmp_path,
        "config.yaml",
        "# a comment\n"
        "epoch_duration_hours: 24  # trailing comment\n"
        "voyage:\n"
        "  natural_history_clock: hours\n"
        "  epoch_duration_hours: 1\n",
    )
    assert [f.rule for f in check_config_file(path)] == ["CLOCK003"]


def test_a_nested_block_is_not_mistaken_for_a_second_declaration(
    tmp_path: Path,
) -> None:
    """A key of the same name outside ``voyage:`` is a different setting."""
    path = _write(
        tmp_path,
        "config.yaml",
        "voyage:\n"
        "  epoch_duration_hours: 1\n"
        "reporting:\n"
        "  epoch_duration_hours: 24\n",
    )
    assert check_config_file(path) == []


def test_a_non_mapping_config_is_not_a_finding(tmp_path: Path) -> None:
    assert check_config_file(_write(tmp_path, "list.json", "[1, 2]")) == []


# ── the shipped tree is clean ────────────────────────────────────────────

GUARDED_TREES = [
    "engines",
    "crusher_labs",
    "picard_framework",
    "decision_engine",
    "scripts",
    "tools",
]


def test_the_shipped_sources_hold_the_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setattr(sys, "argv", ["clock_guard.py", *GUARDED_TREES])
    assert main() == 0


def test_the_shipped_configs_declare_one_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setattr(sys, "argv", ["clock_guard.py", "--configs"])
    assert main() == 0


def test_main_reports_a_violation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(tmp_path, "m.py", "if time_infected >= recovery_day:\n    pass\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["clock_guard.py", "."])
    assert main() == 1
    assert "CLOCK001" in capsys.readouterr().out


def test_a_named_config_may_be_checked_directly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write(
        tmp_path,
        "voyage_config.json",
        json.dumps({"epoch_duration_hours": 6, "voyage": {"epoch_duration_hours": 1}}),
    )
    monkeypatch.setattr(sys, "argv", ["clock_guard.py", "--configs", str(path)])
    assert main() == 1
