"""Shared, schema-validated dose-response lookup for the noro_diag readouts.

Both diagnostics report counterfactual frailty arithmetic derived from a
profile's ``dose_response.alpha``/``beta``. They resolve the bundle here so the
readout reads the same file the instrumented run loads through the catalog, and
so the pathogen bundle layout stays declared once in
:mod:`simulation_utils.asset_defaults`.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from picard_framework.pathogen_overrides import load_pathogen_bundle  # noqa: E402
from simulation_utils import asset_defaults  # noqa: E402
from simulation_utils.paths import resolve_repo_path  # noqa: E402


def load_dose_response(
    pathogen_id: str,
    bundle: str = asset_defaults.DEFAULT_PATHOGEN_BUNDLE_ID,
) -> tuple[float, float]:
    """Return the shipped ``(alpha, beta)`` for one profile of *bundle*.

    The bundle is validated against ``pathogen_profiles.schema.json`` on the
    path actually read, so a malformed profile is reported as a named schema
    violation rather than surfacing as a ``KeyError`` in the arithmetic.
    """
    path = resolve_repo_path(
        str(REPO_ROOT), asset_defaults.pathogen_bundle_rel(bundle),
    )
    profiles = load_pathogen_bundle(path)
    profile = profiles.get(pathogen_id)
    if profile is None:
        raise SystemExit(
            f"no profile with pathogen_id {pathogen_id!r} in bundle {bundle!r}",
        )
    dose_response = profile["dose_response"]
    return float(dose_response["alpha"]), float(dose_response["beta"])
