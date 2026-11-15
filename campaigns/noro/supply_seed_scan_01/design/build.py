#!/usr/bin/env python3
"""Build campaigns/noro/supply_seed_scan_01/campaign.json.

The block ``seeds`` lists are chunk indices, not voyage seeds. Each chunk is
``chunk_size`` consecutive voyage seeds from the hull's dedicated range; the
campaign entry hook expands chunk index -> concrete seed range.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
OUT = REPO / "campaigns" / "noro" / "supply_seed_scan_01" / "campaign.json"

HULLS = [
    ("exp", "fl_exp_12d_sens_p06_paxv", 900000, 56000),
    ("cls", "fl_cls_12d_sens_p06_paxv", 960000, 34000),
    ("spr", "fl_spr_12d_sens_p06_paxv", 1000000, 19000),
    ("meg", "fl_meg_12d_sens_p06_paxv", 1020000, 17200),
]
ARMS = ["station_lots", "single_line_receipt", "declared_receipts"]
CHUNK_SIZE = 100
MANIFEST = "picard_framework/runs/mega_cruise_campaign/noro_provisioned_sensitivity_01_manifest.json"


def _n_chunks(seed_count: int) -> int:
    return -(-seed_count // CHUNK_SIZE)


def _blocks() -> dict[str, dict]:
    blocks: dict[str, dict] = {}
    for hull, tier, seed_start, seed_count in HULLS:
        for arm in ARMS:
            name = f"{hull}_{arm}"
            blocks[name] = {
                "worker": "tools/noro_diag/supply_seed_scan.py",
                "artifact": "supply_seed_scan_chunk{seed}.jsonl",
                "seeds": list(range(_n_chunks(seed_count))),
                "args": {
                    "tier": tier,
                    "arm": arm,
                    "hull": hull,
                    "seed_start": seed_start,
                    "seed_count": seed_count,
                    "chunk_size": CHUNK_SIZE,
                    "epochs": 1,
                    "num_agents": 100,
                    "artifact_stem": name,
                },
            }
    return blocks


def main() -> int:
    spec = {
        "name": "noro_supply_seed_scan_01",
        "pathogen": "norovirus",
        "manifest": MANIFEST,
        "pathogen_id": "norwalk_gi",
        "epochs": 1,
        "s3_prefix": "campaign/noro_supply_seed_scan_01/",
        "queue": "picard-campaign-queue",
        "image_tag": "noro-supply-seed01",
        "resources": {"vcpu": "1", "memory": "4096", "shm": 512},
        "blocks": _blocks(),
    }
    OUT.write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
    total_chunks = sum(len(block["seeds"]) for block in spec["blocks"].values())
    print(f"wrote {OUT.relative_to(REPO)} blocks={len(spec['blocks'])} chunks={total_chunks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
