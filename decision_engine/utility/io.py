"""Export utility bundles and import action envelopes for external optimizers."""

from __future__ import annotations

import json
import os
from typing import Any

from decision_engine.actions import ActionEnvelope
from simulation_utils.paths import prepare_output_directory, resolve_child_path


def export_utility_bundle(
    bundle: dict[str, Any],
    export_dir: str,
    epoch: int,
    cruise_id: str = "0",
    *,
    allowed_roots: tuple[str, ...],
) -> str:
    export_dir = prepare_output_directory(export_dir, allowed_roots=allowed_roots)
    path = resolve_child_path(
        export_dir,
        f"cruise_{cruise_id}_epoch_{epoch:04d}_utility.json",
    )
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, indent=2)
    return path


def import_action_envelope(
    import_dir: str,
    epoch: int,
    cruise_id: str = "0",
) -> ActionEnvelope | None:
    path = resolve_child_path(
        import_dir, f"cruise_{cruise_id}_epoch_{epoch:04d}_actions.json",
    )
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return ActionEnvelope(
        epoch=int(data.get("epoch", epoch)),
        actions=data.get("actions", {}),
    )
