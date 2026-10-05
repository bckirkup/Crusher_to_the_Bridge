"""Single-pathogen diagnostic bundles stay byte-identical to their
``active_profiles`` block.

``data/pathogens/norwalk_only.json`` is the noro arm's isolated-bundle
diagnostic image: every ``--bundle norwalk_only`` probe must measure the
same profile every ``active_profiles`` fleet cell runs (convention in
``docs/ledger/NORO-CHANNEL-02.md`` and the bundle's own ``meta.description``).
It has drifted once — HOST-AGE-02/03's ``*_by_age_band`` keys landed on the
fleet bundle but not the diagnostic one — so the mirror is asserted, not
documented.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict:
    return json.loads((REPO / path).read_text())


def _profile(bundle: dict, pathogen_id: str) -> dict:
    for profile in bundle["pathogens"]:
        if profile.get("pathogen_id") == pathogen_id:
            return profile
    raise KeyError(pathogen_id)


def test_norwalk_only_mirrors_active_profiles() -> None:
    """The diagnostic bundle's only profile equals the fleet bundle's."""
    only = _load("data/pathogens/norwalk_only.json")
    active = _load("data/pathogens/active_profiles.json")
    assert _profile(only, "norwalk_gi") == _profile(active, "norwalk_gi")
