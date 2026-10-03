#!/usr/bin/env python3
"""Shared scaffolding for the instrumented-voyage probes.

Every noro_diag probe runs a voyage the same way: write the spec dict
to a private repo-local file, load it as a ``PicardRunSpec``, and run
the sim under read-only wrappers installed on ``TransmissionCore`` (and
occasionally module-level functions). This module carries the pieces
each probe used to re-implement: the spec materialization, the
attribute-swap bookkeeping, the ``_emit_emesis`` before/after
record-slicing wrapper, and the epoch-0 import marking.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ),
)

from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    resolve_child_path,
    validated_open,
)


@contextmanager
def materialized_picard_spec(
    spec_dict: dict[str, Any], repo_root: Any,
) -> Iterator[Any]:
    """Write *spec_dict* to a private temp file, yield its PicardRunSpec.

    ``validated_open`` refuses publicly writable roots, so the temp
    directory is a fresh private ``TemporaryDirectory`` under the
    repository root — the file itself never leaves it.
    """
    with tempfile.TemporaryDirectory(dir=repo_root) as tmp:
        spec_path = resolve_child_path(tmp, "run_spec.json")
        with validated_open(
            spec_path, "w", allowed_roots=(tmp,), encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(spec_dict))
        yield PicardRunSpec.from_picard_json(str(repo_root), spec_path)


class _AttrPatches:
    """Recorded attribute swaps; restores each first-seen original."""

    def __init__(self) -> None:
        self._seen: set[tuple[int, str]] = set()
        self._saved: list[tuple[Any, str, Any]] = []

    def _record(self, target: Any, name: str, original: Any) -> None:
        key = (id(target), name)
        if key not in self._seen:
            self._seen.add(key)
            self._saved.append((target, name, original))

    def swap(self, target: Any, name: str, value: Any) -> None:
        """Set ``target.name = value``, remembering the current value."""
        self._record(target, name, getattr(target, name))
        setattr(target, name, value)

    def note(self, target: Any, originals: dict[str, Any]) -> None:
        """Record originals another installer already swapped.

        First-seen originals win — the ``saved.setdefault(...)`` idiom,
        where a second installer stacking on the same name keeps the
        pre-instrumentation value.
        """
        for name, original in originals.items():
            self._record(target, name, original)

    def note_all(self, target: Any, originals: dict[str, Any]) -> None:
        """Record originals without dedup — restore order preserved.

        The sequential-restore idiom (``saved.update(group)`` or one
        restore loop per group) applies each captured dict in order, so
        when two installers touched the same name the later group's
        captured value is what lands last; appending reproduces that.
        """
        for name, original in originals.items():
            self._saved.append((target, name, original))

    def restore(self) -> None:
        for target, name, original in self._saved:
            setattr(target, name, original)


@contextmanager
def attr_patches() -> Iterator[_AttrPatches]:
    """Record ``swap``/``note`` edits; restore all originals on exit.

    First-seen originals win: when a later wrapper stacks on a name an
    earlier swap already recorded, the restore still lands the true
    pre-instrumentation method.
    """
    patches = _AttrPatches()
    try:
        yield patches
    finally:
        patches.restore()


def install_wrappers(
    target: Any, replacements: dict[str, Any],
) -> dict[str, Any]:
    """``setattr`` each name to its wrapper; return the originals."""
    originals = {name: getattr(target, name) for name in replacements}
    for name, wrapper in replacements.items():
        setattr(target, name, wrapper)
    return originals


def restore_wrappers(target: Any, originals: dict[str, Any]) -> None:
    """Undo :func:`install_wrappers`."""
    for name, method in originals.items():
        setattr(target, name, method)


def emesis_records(agent: Any, pathogen_id: str) -> list:
    """The agent's deposition records for *pathogen_id* (empty if none)."""
    return getattr(
        agent, "emesis_deposition_records_by_pathogen", {},
    ).get(pathogen_id, [])


def wrap_emit_emesis(
    core_cls: type,
    on_emit: Callable,
    *,
    pre: Callable | None = None,
) -> Any:
    """An ``_emit_emesis`` witness built on the before/after slice idiom.

    The engine appends the call's deposition records inside the original
    method, so the wrapper counts them beforehand and reports the
    pre-call count to *on_emit* (``before``); each probe slices
    ``emesis_records(agent, pathogen_id)[before:]`` for the records this
    call filed. ``pre`` runs before the original to capture per-call
    state (patch-pool depth, schedule length); its return is passed to
    *on_emit* as ``ctx``.

    ``on_emit(self, agent, pathogen_id, zone_name, epoch, pool_gain,
    before, ctx)`` — the pathogen filter lives in the callback.

    The wrapper tail-forwards ``*args``/``**kwargs`` so a growing
    ``_emit_emesis`` signature (e.g. the accumulator args added under
    CAREGIVER-V1) passes through untouched.
    """
    original = core_cls._emit_emesis

    def wrapper(
        self: Any,
        agent: Any,
        pathogen_id: str,
        profile: dict,
        zone_name: str,
        epoch: int,
        *args: Any,
        **kwargs: Any,
    ) -> float:
        ctx = (
            pre(self, agent, pathogen_id, zone_name, epoch)
            if pre is not None else None
        )
        # NB: the engine creates this list via setdefault *inside* the
        # call, so it must be re-fetched afterwards — a pre-call .get()
        # misses the host's first emit entirely.
        before = len(emesis_records(agent, pathogen_id))
        pool_gain = original(
            self, agent, pathogen_id, profile, zone_name, epoch,
            *args, **kwargs,
        )
        on_emit(
            self, agent, pathogen_id, zone_name, epoch,
            pool_gain, before, ctx,
        )
        return pool_gain

    return wrapper


def mark_epoch0_imports(rec: Any, engine: Any) -> None:
    """First-epoch marking: agents infected before epoch 0 are imports.

    Everything infected at the first observation is an import rather
    than an onboard acquisition — the recorder's ``import_ids`` and
    ``host_gen`` get seeded once, on the first call only.
    """
    if rec.epoch0_done:
        return
    rec.epoch0_done = True
    for agent in engine.agents:
        if agent.is_infected_with(rec.pathogen_id):
            aid = int(agent.agent_id)
            if aid not in rec.acquired_ids:
                rec.import_ids.add(aid)
                rec.host_gen.setdefault(aid, 0)
