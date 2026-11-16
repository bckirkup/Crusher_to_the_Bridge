#!/usr/bin/env python3
"""Build the campaign-local manifest for noro_supply_worst_cases_redeposit_01."""

from __future__ import annotations

import copy
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
BASE = REPO / "campaigns/noro/supply_worst_cases_01/manifest.json"
SOURCE = (
    REPO
    / "picard_framework/runs/mega_cruise_campaign/noro_provisioned_sensitivity_01_manifest.json"
)
OUT = Path(__file__).resolve().parents[1] / "manifest.json"
SOURCE_TIER = "fl_meg_12d_sens_p06_paxv"

# Top four mega seeds by burden_est in campaigns/noro/supply_worst_cases_01/ranking.json.
ARMS = {
    "station_lots": {
        "seeds": [1020931, 1036232],
        "fields": {},
    },
    "single_line_receipt": {
        "seeds": [1030001],
        "fields": {"lot_layer_mode": "single_line_receipt"},
    },
    "declared_receipts": {
        "seeds": [1031386],
        "fields": {
            "lot_layer_mode": "declared_receipts",
            "receipts_per_item_line": 2,
        },
    },
}
REDEPOSIT_MODES = ("shedders_only", "carriers")


def main() -> None:
    base = json.loads(BASE.read_text(encoding="utf-8"))
    source = json.loads(SOURCE.read_text(encoding="utf-8"))["tiers"][SOURCE_TIER]

    manifest = {key: value for key, value in base.items() if key != "tiers"}
    manifest["campaign"] = "noro_supply_worst_cases_redeposit_01"
    manifest["description"] = (
        "FOOD-SUPPLY-01 worst-case mega supply seeds crossed with "
        "transmission.hand_redeposit_mode shedders_only vs carriers; all other "
        "p06 passenger-venue settings held fixed."
    )

    tiers: dict[str, dict] = {}
    for arm, arm_spec in ARMS.items():
        for mode in REDEPOSIT_MODES:
            tier = copy.deepcopy(source)
            tier["seeds"] = list(arm_spec["seeds"])
            provisioned = tier["config_overrides"]["transmission"][
                "common_source"
            ]["provisioned_source"]
            provisioned.pop("lot_layer_mode", None)
            provisioned.pop("receipts_per_item_line", None)
            provisioned.update(arm_spec["fields"])
            tier["config_overrides"]["transmission"][
                "hand_redeposit_mode"
            ] = mode
            tier["description"] = (
                "FOOD-SUPPLY-01 worst-case mega redeposit contrast: "
                f"p06 passenger_venue pin ['MainDining_L'], supply arm "
                f"{arm}, hand_redeposit_mode={mode}, seeds "
                f"{tier['seeds']}, 288 epochs, comp65, dose 7.57."
            )
            tiers[f"fl_meg_12d_sens_p06_paxv_{arm}_{mode}"] = tier

    manifest["tiers"] = tiers
    OUT.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT} with {len(tiers)} tiers")


if __name__ == "__main__":
    main()
