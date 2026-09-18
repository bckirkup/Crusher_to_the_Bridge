"""AERO-CABIN-06: per-stateroom airborne pools inside a cabin block.

The airflow network is declared between ship zones, so a block's air is
transported as one node and then partitioned among its staterooms: what a
stateroom still holds of its own air after one epoch of its block's gross
outflow stays with it, and the rest of the block's post-transport mass is
shared out by berths. The partition conserves the transported mass exactly,
so no volume, flow or removal rate is introduced by it.
"""

from __future__ import annotations

import math
from collections.abc import Callable


def fold_stateroom_mass(
    masses: dict[str, float],
    parent_of: Callable[[str], str],
) -> dict[str, float]:
    """Sum stateroom keys into their parent block, dropping the keys."""
    folded: dict[str, float] = {}
    for key, mass in masses.items():
        parent = parent_of(key)
        folded[parent] = folded.get(parent, 0.0) + mass
    return folded


def partition_block_air(
    pre: dict[str, float],
    post: dict[str, float],
    shares_by_block: dict[str, dict[str, float]],
    outflow_rate_by_block: dict[str, float],
    dt: float,
) -> dict[str, float]:
    """Split each cabin block's post-transport mass among its staterooms.

    ``pre`` is the pre-transport map including stateroom keys, ``post`` the
    block-level result of one transport step, ``shares_by_block`` each block's
    stateroom berth shares, and ``outflow_rate_by_block`` its gross specific
    outflow rate [1/h] over the step ``dt`` [h]. A block with no registered
    staterooms keeps its own mass.
    """
    new = dict(post)
    for block, shares in shares_by_block.items():
        if not shares or block not in post:
            continue
        remaining = math.exp(-outflow_rate_by_block.get(block, 0.0) * dt)
        retained = {
            key: pre.get(key, 0.0) * remaining
            for key in shares
        }
        pooled = max(0.0, post[block] - sum(retained.values()))
        for key, share in shares.items():
            new[key] = retained[key] + share * pooled
        new[block] = 0.0
    return new
