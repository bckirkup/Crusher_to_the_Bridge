"""Every tracked input a container reads must survive the build context.

Twice now an image has shipped without a file the model reads -- the social
inputs under ``presidio/data/`` (PKG-02) and the VSP series the admissibility
gate scores against (PKG-03) -- and both times the repair enumerated the one
file that broke, so the next untracked-by-any-test input was free to go
missing. Enumeration is the defect: it tests the files we already know about.

The tracked source tree is the enumeration. Git already separates the model's
inputs from its outputs: an input is committed because a run needs it, a result
is committed because a run produced it. So the invariant here is a difference of
two sets rather than a list of files -- every git-tracked file under a directory
an image ``COPY``s reaches the image, except the result artifacts and viewer
assets named in ``NON_INPUTS`` with a reason. A new data file is covered on the
day it is committed, and the only way to drop one is to write it down here.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

IMAGES = (
    REPO_ROOT / "Dockerfile",
    REPO_ROOT / "deploy" / "aws" / "Dockerfile.design",
    REPO_ROOT / "deploy" / "aws" / "Dockerfile.analysis",
)

# Tracked files a container is meant to run without: simulation output committed
# as a record, and assets only the dashboard renders. Each entry must still match
# something, so a stale exclusion cannot sit here shielding a future input.
NON_INPUTS: tuple[tuple[str, str], ...] = (
    ("telemetry_buffer/.gitkeep", "keeps the output directory in git"),
    ("telemetry_buffer/observation_model/*.json", "screen and gate results"),
    ("telemetry_buffer/observation_model/*.md", "analysis notes"),
    ("telemetry_buffer/observation_model/*.txt", "captured probe stdout"),
    ("telemetry_buffer/observation_model/post*_anchor_pilot_*/**", "pilot reports"),
    ("telemetry_buffer/ww_assay/**", "wastewater assay run output and fits"),
    ("telemetry_buffer/ww_test/**", "wastewater probe output"),
    ("telemetry_buffer/portout*/**", "port-call run output"),
    ("telemetry_buffer/postfix_pilot/**", "pilot run output"),
    ("telemetry_buffer/v4_results/**", "campaign v4 run output"),
    ("data/platforms/*/deck_blueprint_bg.png", "dashboard deck art"),
    ("data/platforms/*/deck_hull.png", "dashboard deck art"),
    ("data/platforms/*/deck_graphics.geojson", "dashboard deck geometry"),
)


def _pattern_regex(pattern: str) -> re.Pattern[str]:
    """A Docker-style path pattern: ``*`` stays within one path segment."""
    escaped = re.escape(pattern.rstrip("/"))
    escaped = escaped.replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
    return re.compile(rf"^{escaped}(/.*)?$")


def _dockerignore_rules() -> list[tuple[bool, re.Pattern[str]]]:
    rules: list[tuple[bool, re.Pattern[str]]] = []
    text = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rules.append((line.startswith("!"), _pattern_regex(line.lstrip("!"))))
    return rules


def _dockerignored(relative: str) -> bool:
    """Whether the build context drops ``relative`` (last matching rule wins)."""
    ignored = False
    for negated, regex in _dockerignore_rules():
        if regex.match(relative):
            ignored = not negated
    return ignored


def _copied_directories(dockerfile: Path) -> list[str]:
    """The build-context directories this image copies wholesale."""
    copied: list[str] = []
    for raw in dockerfile.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("COPY ") or "--from=" in line:
            continue
        copied.extend(part for part in line.split()[1:-1] if part.endswith("/"))
    return copied


def _tracked_files() -> list[str]:
    listing = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [entry for entry in listing.stdout.split("\0") if entry]


def _declared_non_input(relative: str) -> bool:
    return any(
        _pattern_regex(pattern).match(relative) for pattern, _ in NON_INPUTS
    )


def _dropped_under(directories: list[str]) -> list[str]:
    return [
        path
        for path in _tracked_files()
        if any(path.startswith(directory) for directory in directories)
        and _dockerignored(path)
    ]


@pytest.mark.parametrize("dockerfile", IMAGES, ids=lambda path: path.name)
def test_no_tracked_input_is_dropped_from_an_image(dockerfile: Path) -> None:
    surprises = [
        path
        for path in _dropped_under(_copied_directories(dockerfile))
        if not _declared_non_input(path)
    ]
    assert not surprises, (
        f"{dockerfile.name} copies these tracked files' directories but "
        f".dockerignore drops them: {surprises}. Either re-admit them with a "
        "'!' rule or declare them in NON_INPUTS with a reason."
    )


@pytest.mark.parametrize("pattern", [pattern for pattern, _ in NON_INPUTS])
def test_every_declared_non_input_still_matches_something(pattern: str) -> None:
    directories = sorted(
        {
            directory
            for dockerfile in IMAGES
            for directory in _copied_directories(dockerfile)
        },
    )
    regex = _pattern_regex(pattern)
    assert any(
        regex.match(path) for path in _dropped_under(directories)
    ), f"{pattern} matches no dropped tracked file; delete the exclusion"


def test_a_new_input_beside_a_result_is_caught() -> None:
    """The check must fail on the file class that has now failed twice.

    A CSV committed beside the gate's series is an input by construction, and
    the ``telemetry_buffer/*`` rule drops it; ``NON_INPUTS`` admits results by
    suffix, so it must not admit this one.
    """
    candidate = "telemetry_buffer/observation_model/vsp_new_series.csv"
    assert _dockerignored(candidate)
    assert not _declared_non_input(candidate)


def test_the_gates_scoring_series_reaches_the_design_image() -> None:
    series = "telemetry_buffer/observation_model/vsp_outbreak_series.csv"
    assert (REPO_ROOT / series).is_file()
    assert not _dockerignored(series)
    assert "telemetry_buffer/" in _copied_directories(
        REPO_ROOT / "deploy" / "aws" / "Dockerfile.design",
    )


def test_the_ignore_matcher_reads_docker_rules_as_docker_does() -> None:
    assert _dockerignored("telemetry_buffer/observation_model/local_merged.json")
    assert _dockerignored("third_party/contamx/bin/contamx3")
    assert not _dockerignored("telemetry_buffer/observation_model/admissible_region.py")
    assert not _dockerignored("engines/transmission_core.py")
