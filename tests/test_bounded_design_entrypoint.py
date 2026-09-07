"""Unit tests for the bounded-design Batch worker's shard command line."""

from __future__ import annotations

from pathlib import Path

import pytest

from deploy.aws.bounded_design_entrypoint import _region_argv, _screen_argv, parse_args


def _region_args(*extra: str):
    return parse_args([
        "--design", "region",
        "--s3-prefix", "s3://bucket/campaign/x/",
        "--shard-count", "4",
        *extra,
    ])


def test_a_region_shard_passes_the_seed_shard_count_it_was_given() -> None:
    argv = _region_argv(
        _region_args("--seed-shards", "8"),
        2,
        Path("/tmp/out.json"),
        Path("/tmp/rows.jsonl"),
    )
    assert argv[argv.index("--seed-shards") + 1] == "8"
    assert argv[argv.index("--shard-index") + 1] == "2"
    assert "--only-points" not in argv


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        ("", None),
        ("7", ["7"]),
        ("7,13,204", ["7", "13", "204"]),
        (" 7 , 13 ", ["7", "13"]),
    ],
)
def test_a_named_subset_reaches_the_gate_with_its_own_indices(
    selection: str,
    expected: list[str] | None,
) -> None:
    argv = _region_argv(
        _region_args("--only-points", selection),
        0,
        Path("/tmp/out.json"),
        Path("/tmp/rows.jsonl"),
    )
    if expected is None:
        assert "--only-points" not in argv
    else:
        assert argv[argv.index("--only-points") + 1:][:len(expected)] == expected


@pytest.mark.parametrize("selection", ["7,x", "-3", "1;2"])
def test_a_subset_that_is_not_design_indices_is_refused(selection: str) -> None:
    with pytest.raises(SystemExit, match="design indices"):
        _region_argv(
            _region_args("--only-points", selection),
            0,
            Path("/tmp/out.json"),
            Path("/tmp/rows.jsonl"),
        )


@pytest.mark.parametrize(
    ("arm", "flagged"),
    [("off", False), ("on", True)],
)
def test_the_duty_exclusion_arm_is_off_unless_the_submission_asks_for_it(
    arm: str,
    flagged: bool,
) -> None:
    """The matched baseline is the same command line minus one flag."""
    argv = _region_argv(
        _region_args("--crew-duty-exclusion", arm),
        0,
        Path("/tmp/out.json"),
        Path("/tmp/rows.jsonl"),
    )
    assert ("--crew-duty-exclusion" in argv) is flagged


def test_the_duty_exclusion_arm_defaults_to_the_baseline() -> None:
    argv = _region_argv(
        _region_args(),
        0,
        Path("/tmp/out.json"),
        Path("/tmp/rows.jsonl"),
    )
    assert "--crew-duty-exclusion" not in argv


def test_the_screen_shard_is_unaffected_by_the_region_subset_flags() -> None:
    args = parse_args([
        "--design", "screen",
        "--s3-prefix", "s3://bucket/campaign/x/",
        "--shard-count", "4",
        "--seed-shards", "5",
    ])
    argv = _screen_argv(args, 1, Path("/tmp/out.json"))
    assert argv[argv.index("--seed-shards") + 1] == "5"
    assert "--only-points" not in argv


def test_a_region_shard_starts_its_seeds_at_the_stage_base() -> None:
    argv = _region_argv(
        _region_args("--seed-base", "524", "--seeds", "24"),
        0,
        Path("/tmp/out.json"),
        Path("/tmp/rows.jsonl"),
    )
    assert argv[argv.index("--seed-base") + 1] == "524"
    assert argv[argv.index("--seeds") + 1] == "24"
