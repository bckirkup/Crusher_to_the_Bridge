"""Generate the fixed post-confinement-fix pilot specifications."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from picard_framework.runs.mega_cruise_campaign.campaign_runner import (  # noqa: E402
    generate_tier_runs,
)

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = (
    REPO
    / "picard_framework"
    / "runs"
    / "mega_cruise_campaign"
    / "common_dose_containment_v4_manifest.json"
)
TIERS = (
    ("c1_fit_expedition_450", "expedition_cruise_450"),
    ("c1_fit_classic_1900", "classic_cruise_1900"),
)
DOSES = (2.0, 2.5, 3.0)
SEEDS = tuple(range(940, 950))
STRATEGIES = ("none_response", "syndromic_comp85")


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    spec_root = ROOT / "specs"
    generated: list[dict[str, object]] = []
    for tier_id, hull in TIERS:
        for dose in DOSES:
            local_manifest = copy.deepcopy(manifest)
            tier = local_manifest["tiers"][tier_id]
            tier["dose_adjustments"] = [dose]
            tier["surveillance_strategies"] = list(STRATEGIES)
            tier["seeds"] = list(SEEDS)
            tier["initial_infected_values"] = [1]
            tier["epochs"] = 168
            runs = generate_tier_runs(
                local_manifest,
                tier_id,
                natural_history_clock="hours",
            )
            selected = [
                (run_id, spec)
                for run_id, spec in runs
                if spec.get("campaign_parameters", {}).get("seed") in SEEDS
            ]
            expected = len(SEEDS) * len(STRATEGIES)
            if len(selected) != expected:
                raise RuntimeError(
                    f"{tier_id} dose={dose} generated {len(selected)} runs, "
                    f"expected {expected}",
                )
            for source_run_id, spec in selected:
                params = dict(spec["campaign_parameters"])
                strategy = str(params["surveillance"])
                seed = int(params["seed"])
                run_id = (
                    f"postfix_pilot_{hull}_"
                    f"dose{dose:g}_{strategy}_s{seed}"
                )
                spec["description"] = run_id
                params.update(
                    {
                        "run_id": run_id,
                        "pilot_source_run_id": source_run_id,
                        "num_epochs": 168,
                        "n_init": 1,
                    },
                )
                spec["campaign_parameters"] = params
                path = spec_root / hull / f"{run_id}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(spec, indent=2) + "\n",
                    encoding="utf-8",
                )
                generated.append(
                    {
                        "run_id": run_id,
                        "hull": hull,
                        "dose_adjustment": dose,
                        "surveillance": strategy,
                        "seed": seed,
                        "path": str(path),
                    },
                )
    metadata = {
        "source_manifest": str(MANIFEST_PATH),
        "mechanism": "manifest tier generation with pathogen_overrides",
        "branch_commit": "9d06492",
        "hulls": [hull for _, hull in TIERS],
        "strategies": list(STRATEGIES),
        "doses": list(DOSES),
        "seeds": list(SEEDS),
        "initial_infected": 1,
        "epochs": 168,
        "natural_history_clock": "hours",
        "run_count": len(generated),
        "runs": generated,
    }
    (ROOT / "pilot_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"generated {len(generated)} specs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
