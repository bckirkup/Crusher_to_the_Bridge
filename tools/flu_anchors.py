"""The scored observables and confined-SAR floor constants of the influenza arm.

Single loader for ``data/observation/flu_fit_targets.json`` so the F1
endpoint, the F5 internal check and the dose-response ``k`` interval the
confined-SAR floor is derived from live at one definition site. The covid
idiom is ``data/observation/covid_fit_targets.json`` +
``picard_framework/covid_fit_targets.py``; the flu arm carries no train/test
split, so there is no split machinery here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGETS_PATH = REPO_ROOT / "data" / "observation" / "flu_fit_targets.json"


def load_targets(path: Path = TARGETS_PATH) -> dict[str, Any]:
    """The parsed flu fit-targets payload."""
    return json.loads(path.read_text())


def anchor(payload: dict[str, Any], anchor_id: str) -> dict[str, Any]:
    """One anchor row by id; raises KeyError on an unknown id."""
    for row in payload["anchors"]:
        if row["anchor_id"] == anchor_id:
            return row
    raise KeyError(anchor_id)


_TARGETS = load_targets()

# F1 — Lau 2012 PCR secondary-infection-rate spread; scored as Wilson-95%
# overlap against pooled confined secondaries/slots.
F1_BAND = tuple(anchor(_TARGETS, "flu.F1")["values"]["sar_spread"])

# F5 — Ward 2010 reported/infected internal check (0.7% presenting vs 8.9%
# NAT-confirmed).
F5_REPORTED_PER_INFECTION = float(
    anchor(_TARGETS, "flu.F5")["values"]["reported_per_infection"],
)

_FLOOR = _TARGETS["confined_sar_floor"]

# Declared sourced interval of influenza_a ``dose_response.k`` (per copy):
# Alford 1966 aerosol ID50 0.6-3 TCID50 divided by Van Wesenbeeck 2015
# >=1e3 copies/TCID50, shipped midpoint (FLU-DELIVERY-01). The floor band is
# [E[SAR](k_lo), E[SAR](k_hi)] on the cell's pooled slot doses —
# docs/confined_attack_floor_spec.md.
K_SOURCED_INTERVAL = tuple(_FLOOR["k_sourced_interval"])
K_DECLARED = float(_FLOOR["k_ship"])
