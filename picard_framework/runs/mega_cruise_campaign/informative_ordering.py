"""Order campaign runs by expected informativeness before sharding.

The manifest order walks each tier's cartesian product one axis at a time, so
the first runs a shard completes are clustered replicates of one design point
in one tier. Under a modulo shard partition every shard inherits that
clustering: after a tenth of the wall clock, the campaign has resolved a tenth
of the grid finely and the rest not at all.

``order_runs_informative`` is a *pure function of the run list*: it takes the
flattened ``all_runs`` and returns a permutation of it that depends on nothing
else -- not on the shard index, not on the shard count, not on the clock.
Every shard therefore computes the same global order and the positional
partition ``global_index % shard_count == shard_index`` stays complete and
disjoint. That invariant is what makes the reordering safe to apply before the
partition, and it is tested.

The order itself is two nested rules:

1. **Design points before replicates.** Runs are grouped by their swept
   coordinates (every ``campaign_parameters`` entry except ``seed`` and
   ``run_id``). The output is built in *waves*: wave 0 holds the first
   replicate of every design point, wave 1 the second, and so on. No design
   point receives a second seed until every design point has had its first.
2. **Coarse-to-fine across the grid within a wave.** Design points are indexed
   in manifest order and visited in van der Corput (bit-reversal) order, so a
   prefix of a wave samples the whole grid at low resolution rather than
   walking one end of one axis. An early stop after k runs then leaves every
   tier and every axis sparsely covered instead of one tier densely covered.

Nothing here reads a result: the ordering is fixed before the first run and
is the same on a resumed shard as on the first launch.
"""
from __future__ import annotations

from typing import Any, Hashable, Sequence

from picard_framework.runs.mega_cruise_campaign import campaign_runner as _cr

Run = tuple[str, str, dict[str, Any]]

ORDER_MANIFEST = "manifest"
ORDER_INFORMATIVE = "informative"
ORDER_CHOICES: tuple[str, ...] = (ORDER_MANIFEST, ORDER_INFORMATIVE)

# Replicate coordinates: a run differing only here is the same design point.
REPLICATE_KEYS: frozenset[str] = frozenset({"seed", "run_id"})


def _freeze(value: Any) -> Hashable:
    if isinstance(value, dict):
        return tuple(sorted((str(k), _freeze(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value if isinstance(value, Hashable) else repr(value)


def design_point_key(tier_id: str, spec: dict[str, Any]) -> Hashable:
    """The swept coordinates of a run, with the replicate axis removed."""
    params = _cr.parameters_from_spec(spec)
    coords = tuple(
        sorted((k, _freeze(v)) for k, v in params.items() if k not in REPLICATE_KEYS)
    )
    return (tier_id, coords)


def van_der_corput_order(n: int) -> list[int]:
    """Indices ``0..n-1`` visited in bit-reversal order.

    The permutation of the smallest power of two not below ``n``, filtered to
    the indices that exist, so a prefix of the result is spread across the
    whole range rather than clustered at its start.
    """
    if n <= 0:
        return []
    bits = max(1, (n - 1).bit_length())
    order = [int(format(i, f"0{bits}b")[::-1], 2) for i in range(1 << bits)]
    return [i for i in order if i < n]


def group_design_points(runs: Sequence[Run]) -> list[list[Run]]:
    """Runs grouped by design point, groups and members in manifest order."""
    groups: dict[Hashable, list[Run]] = {}
    for run in runs:
        tier_id, _run_id, spec = run
        groups.setdefault(design_point_key(tier_id, spec), []).append(run)
    return list(groups.values())


def order_runs_informative(runs: Sequence[Run]) -> list[Run]:
    """Return a shard-independent permutation of ``runs`` (see module doc)."""
    groups = group_design_points(runs)
    visit = van_der_corput_order(len(groups))
    depth = max((len(g) for g in groups), default=0)
    ordered: list[Run] = []
    for wave in range(depth):
        ordered.extend(groups[i][wave] for i in visit if wave < len(groups[i]))
    return ordered


def order_runs(runs: Sequence[Run], order: str) -> list[Run]:
    if order == ORDER_MANIFEST:
        return list(runs)
    if order == ORDER_INFORMATIVE:
        return order_runs_informative(runs)
    raise ValueError(f"unknown run order {order!r}; choose from {ORDER_CHOICES}")
