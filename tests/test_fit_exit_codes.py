"""No posterior is not success: the exit-code contract every fit CLI shares.

The campaign reads exit codes, not consoles. A ``skipped`` fit (CmdStan absent,
nothing sampled) used to exit 0, so a shard array could come back all-green with
no posteriors in it. These tests pin the three-way distinction — posterior (0),
failure (1), no posterior (2) — and the explicit opt-out that a deliberately
sampler-less caller uses.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.analysis._fit_exit import (
    EXIT_FAILED,
    EXIT_NO_POSTERIOR,
    EXIT_OK,
    POSTERIOR_STATUSES,
    fit_exit_code,
    worst_exit_code,
)
from picard_framework.analysis.stan import fit_sentinel_attribution, fit_sentinel_fleet

FLEET_MANIFEST = os.path.join(
    "picard_framework", "analysis", "sentinel", "data", "example_fleet.json",
)


@pytest.mark.parametrize("status", sorted(POSTERIOR_STATUSES))
def test_a_written_posterior_is_the_only_success(status: str) -> None:
    assert fit_exit_code({"status": status}) == EXIT_OK


def test_skipped_and_failed_are_different_operator_problems() -> None:
    """Install a toolchain versus debug a model: distinct codes, not both 1."""
    skipped = fit_exit_code({"status": "skipped", "reason": "no CmdStan"})
    failed = fit_exit_code({"status": "error", "reason": "compile failed"})
    assert skipped == EXIT_NO_POSTERIOR
    assert failed == EXIT_FAILED
    assert skipped != failed


def test_a_status_nobody_wrote_is_a_failure_not_a_shrug() -> None:
    assert fit_exit_code({}) == EXIT_FAILED
    assert fit_exit_code({"status": None}) == EXIT_FAILED


def test_allow_skipped_is_an_opt_in_and_nothing_else() -> None:
    assert fit_exit_code({"status": "skipped"}, allow_skipped=True) == EXIT_OK
    assert fit_exit_code({"status": "error"}, allow_skipped=True) == EXIT_FAILED


def test_the_skipped_message_names_the_way_out(capsys: pytest.CaptureFixture) -> None:
    fit_exit_code({"status": "skipped", "reason": "cmdstanpy missing"})
    err = capsys.readouterr().err
    assert "cmdstanpy missing" in err
    assert "--engine numpy" in err


def test_a_real_failure_outranks_a_skip_in_an_aggregate() -> None:
    """Otherwise a sweep with one broken cell reports only 'no toolchain'."""
    assert worst_exit_code([EXIT_OK, EXIT_NO_POSTERIOR, EXIT_FAILED]) == EXIT_FAILED
    assert worst_exit_code([EXIT_OK, EXIT_NO_POSTERIOR]) == EXIT_NO_POSTERIOR
    assert worst_exit_code([EXIT_OK, EXIT_OK]) == EXIT_OK
    assert worst_exit_code([]) == EXIT_OK


def _skipped(*_args: object, **_kwargs: object) -> dict[str, object]:
    return {"status": "skipped", "reason": "cmdstanpy/CmdStan not installed"}


def test_fleet_fit_cli_refuses_to_exit_clean_without_a_posterior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fit_sentinel_fleet, "fit_sentinel_fleet", _skipped)
    argv = [FLEET_MANIFEST, "--out", "out_test_fit_exit_fleet", "--no-show-progress"]
    assert fit_sentinel_fleet.main(argv) == EXIT_NO_POSTERIOR
    assert fit_sentinel_fleet.main([*argv, "--allow-skipped-fit"]) == EXIT_OK


def test_attribution_cli_shares_the_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        fit_sentinel_attribution, "fit_sentinel_attribution", _skipped,
    )
    argv = [
        "unused_itinerary.json",
        "unused_observations.json",
        "--out",
        "out_test_fit_exit_attribution",
        "--no-show-progress",
    ]
    assert fit_sentinel_attribution.main(argv) == EXIT_NO_POSTERIOR
    assert fit_sentinel_attribution.main([*argv, "--allow-skipped-fit"]) == EXIT_OK
