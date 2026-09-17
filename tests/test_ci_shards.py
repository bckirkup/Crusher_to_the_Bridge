"""The CI shard split is a partition of the collected suite, module by module.

``.github/workflows/ci.yml`` runs the fast tier as several jobs, each passing
``--ci-shard-count N --ci-shard-index i``; the union of those jobs has to be
exactly the ``-m 'not slow'`` selection or the split would silently drop tests.
"""

from __future__ import annotations

import glob
import os
from collections import Counter

import pytest

from tests.conftest import REPO_ROOT, shard_of

TEST_MODULES = sorted(
    os.path.relpath(p, REPO_ROOT)
    for p in glob.glob(os.path.join(REPO_ROOT, "tests", "**", "test_*.py"), recursive=True)
)


@pytest.mark.parametrize("count", [2, 3, 4, 6])
def test_every_module_lands_in_exactly_one_shard(count: int) -> None:
    assignments = {path: shard_of(path, count) for path in TEST_MODULES}
    assert all(0 <= shard < count for shard in assignments.values())
    per_shard = Counter(assignments.values())
    assert sum(per_shard.values()) == len(TEST_MODULES)
    # Every job gets work; an empty shard means pytest exits 5 and the job fails.
    assert set(per_shard) == set(range(count)), per_shard


def test_shard_assignment_is_a_pure_function_of_the_relative_path() -> None:
    assert shard_of("tests/test_a.py", 4) == shard_of("tests/test_a.py", 4)
    assert shard_of("tests/test_a.py", 4) == shard_of(os.path.join("tests", "test_a.py"), 4)


def test_adding_a_module_does_not_move_the_others() -> None:
    before = {path: shard_of(path, 4) for path in TEST_MODULES}
    after = {path: shard_of(path, 4) for path in [*TEST_MODULES, "tests/test_zzz_new.py"]}
    assert all(after[path] == before[path] for path in TEST_MODULES)


def test_the_shard_options_reject_an_index_outside_the_count(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(open(os.path.join(REPO_ROOT, "tests", "conftest.py"), encoding="utf-8").read())
    pytester.makepyfile(test_x="def test_ok():\n    pass\n")
    result = pytester.runpytest("--ci-shard-count", "2", "--ci-shard-index", "2")
    assert result.ret == pytest.ExitCode.USAGE_ERROR


def test_the_shards_partition_a_collected_session(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(open(os.path.join(REPO_ROOT, "tests", "conftest.py"), encoding="utf-8").read())
    for name in ("a", "b", "c", "d", "e"):
        pytester.makepyfile(**{f"test_{name}": "def test_one():\n    pass\n\ndef test_two():\n    pass\n"})
    seen: Counter[str] = Counter()
    for index in range(3):
        result = pytester.runpytest("-v", "--ci-shard-count", "3", "--ci-shard-index", str(index))
        for line in result.outlines:
            if " PASSED" in line:
                seen[line.split(" ")[0]] += 1
    assert set(seen.values()) == {1}, seen
    assert len(seen) == 10
