"""Sampler knobs shared by the sentinel runners.

One dataclass rather than five parameters on every fit function: the sentinel
runners all take the same knobs, and a CLI that grows a sixth should not have to
thread it through two signatures.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SamplerOptions:
    """Sampler knobs, kept together so they travel as one argument.

    The numpy reference walkers read ``iter_sampling``/``iter_warmup`` as draws and
    warmup; the rest apply to CmdStan only.
    """

    chains: int = 4
    iter_sampling: int = 1000
    iter_warmup: int = 1000
    seed: int = 1701
    show_progress: bool = True
