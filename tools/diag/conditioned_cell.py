"""The conditioned confined-cell spec shared by the floor probes.

Every conditioned-cell campaign — cabin floor census, flu rhythm A/B,
confined challenge trace — builds the same spec shape: an isolated arm
(every other bundle pathogen removed, own ``initial_infected`` nulled),
a passenger seed party at epoch 0 via ``initiation.explicit_seeds``,
and — under ``declared`` — SOP-017 held by the replay calendar from
day 1 to voyage end. The bundle constants and the spec builder live
here so a new probe does not fork them; ``tools/cabin_floor_probe.py``
re-exports the names its own callers use.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from picard_framework.pathogen_overrides import (  # noqa: E402
    isolate_arm_overrides,
    load_pathogen_bundle,
)
from simulation_utils import asset_defaults  # noqa: E402
from simulation_utils.paths import resolve_repo_path  # noqa: E402
from simulation_utils.platform_complement import declared_total  # noqa: E402
from tools.noro_diag.per_host_dose_challenge import build_spec  # noqa: E402

EDISON = "edison_10pathogen_profiles"
ACTIVE = asset_defaults.DEFAULT_PATHOGEN_BUNDLE_ID

# Replay calendar confinement: SOP-017 confines every passenger while all
# crew classes stay working, held from the first full simulated day (after
# embarkation churn settles) through voyage end.
DECLARED_CONFINEMENT = {
    "protocol_id": "SOP-017",
    "start_day": 1,
    "end_day": None,
}


def party_size(profile: dict[str, Any]) -> int:
    """The declared party size when the profile imports as a party, else 2."""
    party = (profile.get("boarding") or {}).get("party") or {}
    return int(party.get("size") or 0) or 2


def conditioned_spec(
    *,
    bundle: str,
    pathogen_id: str,
    seed: int,
    platform: str,
    epochs: int,
    confinement: str = "organic",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The conditioned spec shared by the confined-window probes.

    Isolated arm (every other bundle pathogen removed, own
    ``initial_infected`` nulled), a passenger seed party at epoch 0 via
    ``initiation.explicit_seeds``, and — under ``declared`` — SOP-017 held
    by the replay calendar from day 1 to voyage end. Returns the spec and
    the pathogen's bundle profile.
    """
    profiles = load_pathogen_bundle(
        resolve_repo_path(str(REPO_ROOT), asset_defaults.pathogen_bundle_rel(bundle)),
    )
    profile = profiles[pathogen_id]
    spec_dict = build_spec(
        seed=seed, platform=platform, bundle=bundle,
        epochs=epochs, num_agents=declared_total(platform),
        pathogen_id=pathogen_id, alpha=None, beta=0.0,
        high_touch_area_scale=None, high_touch_area_scale_by_zone_class=None,
        fomite_representation=None, fomite_touch_share=None,
        fomite_touch_share_table=None,
    )
    spec_dict["pathogen_overrides"] = isolate_arm_overrides(
        bundle, pathogen_id, {pathogen_id: {"initial_infected": None}},
    )
    spec_dict["config_overrides"]["initiation"] = {
        "explicit_seeds": [{
            "pathogen": pathogen_id,
            "count": party_size(profile),
            "role": "passenger",
            "epoch": 0,
        }],
    }
    if confinement == "declared":
        spec_dict["config_overrides"]["scenario_schedule"] = {
            "protocols": [DECLARED_CONFINEMENT],
        }
    return spec_dict, profile
