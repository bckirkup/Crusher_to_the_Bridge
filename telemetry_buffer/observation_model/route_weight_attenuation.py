"""Measure the realised route-weight attenuation, per pathogen, over a voyage.

Wraps TransmissionCore._apply_route_weights to accumulate the pre-weight dose
each pathway delivered and the post-weight dose that actually reached the
establishment draw, and writes one record per nonzero exposure event for
`route_weight_attribution.py` to attribute establishment across pathways.

Everything is keyed by pathogen: `active_profiles` seeds more than one arm and
this hook fires once per pathogen with that pathogen's own weight set, so an
unkeyed accumulator reports a blend of two weight sets as if it were one.

Usage: route_weight_attenuation.py [epochs] [agents] [platform] [seed]
Findings: route_weight_measurement_findings.md
"""

from __future__ import annotations

import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engines.transmission_core import (  # noqa: E402
    PATHWAY_WEIGHT_KEYS,
    TransmissionCore,
)
from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402

PRE: dict[tuple[str, str], float] = defaultdict(float)
POST: dict[tuple[str, str], float] = defaultdict(float)
_original = TransmissionCore._apply_route_weights


# One record per nonzero exposure event, pre- and post-weight, so establishment
# probability can be attributed across pathways instead of only summed as mass.
EVENTS: list[dict[str, object]] = []


def _instrumented(self, profile, agent_doses, agent_pathway_doses):
    # active_profiles.json seeds BOTH norwalk_gi and sars_cov2_resp
    # (initial_infected: 1 each), and this hook fires once per pathogen with
    # that pathogen's own route weights. Everything must be keyed by pathogen
    # or the two dose streams blend and the per-pathway post/pre ratios come
    # out as a mixture of the two weight sets.
    pid = str((profile or {}).get("pathogen_id", "_unknown"))
    pre_by_agent = {
        aid: {k: float(v) for k, v in pw.items()}
        for aid, pw in agent_pathway_doses.items()
    }
    for pw in pre_by_agent.values():
        for name, dose in pw.items():
            PRE[(pid, name)] += dose
    _original(self, profile, agent_doses, agent_pathway_doses)
    for pw in agent_pathway_doses.values():
        for name, dose in pw.items():
            POST[(pid, name)] += float(dose)
    for aid, total in agent_doses.items():
        t = float(total)
        if t <= 0.0:
            continue
        pre = pre_by_agent.get(aid, {})
        EVENTS.append({
            "pathogen_id": pid,
            "post_total": t,
            "post": {k: float(v) for k, v in agent_pathway_doses.get(aid, {}).items()},
            "pre_total": sum(pre.values()),
            "pre": pre,
        })


TransmissionCore._apply_route_weights = _instrumented


def main() -> int:
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 240
    agents = int(sys.argv[2]) if len(sys.argv) > 2 else 450
    platform = sys.argv[3] if len(sys.argv) > 3 else "expedition_cruise_450"
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 500
    spec = {
        "schema_version": "1.0.0",
        "description": "route_weight_attenuation",
        "catalog": {"platform_id": platform, "pathogen_bundle_id": "active_profiles"},
        "run": {
            "random_seed": seed,
            "num_epochs": epochs,
            "write_ground_truth": False,
            "history_retention": "compact",
        },
        "legacy_yaml": "crusher_labs/config.yaml",
        "actors": [],
        "incentives": {},
        "config_overrides": {"ship_graph": {"num_agents": agents}},
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "run_spec.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        picard = PicardRunSpec.from_picard_json(str(ROOT), str(path))
        ShipSimulation(picard, display=False).run()

    print(f"epochs={epochs} agents={agents} platform={platform} seed={seed}")
    for pid in sorted({k[0] for k in PRE}):
        keys = [k for k in PRE if k[0] == pid]
        pre_total = sum(PRE[k] for k in keys)
        post_total = sum(POST[k] for k in keys)
        print(f"\n--- {pid} ---")
        print(f"{'pathway':22} {'pre-weight':>14} {'share':>8} "
              f"{'post-weight':>14} {'share':>8} {'w':>6}")
        for key in sorted(keys, key=lambda k: -PRE[k]):
            name = key[1]
            wkey = PATHWAY_WEIGHT_KEYS.get(name, name)
            w = (POST[key] / PRE[key]) if PRE[key] else float("nan")
            print(f"{name:22} {PRE[key]:14.4g} {PRE[key]/pre_total:8.4f} "
                  f"{POST[key]:14.4g} {POST[key]/post_total:8.4f} "
                  f"{w:6.3f} ({wkey})")
        print(f"{'TOTAL':22} {pre_total:14.4g} {1.0:8.4f} "
              f"{post_total:14.4g} {1.0:8.4f}")
        if pre_total:
            print("realised attenuation sum(w_r D_r)/sum(D_r) = "
                  f"{post_total/pre_total:.4f}")

    out = Path(tempfile.gettempdir()) / f"exposure_events_{platform}_s{seed}.json"
    out.write_text(json.dumps(EVENTS), encoding="utf-8")
    print(f"\n{len(EVENTS)} nonzero exposure events written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
