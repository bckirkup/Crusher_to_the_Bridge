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
from simulation_utils.paths import (  # noqa: E402
    resolve_child_path,
    resolve_repo_path,
    validated_open,
)

PRE: dict[tuple[str, str], float] = defaultdict(float)
POST: dict[tuple[str, str], float] = defaultdict(float)
_original = TransmissionCore._apply_route_weights


# One record per nonzero exposure event, pre- and post-weight, so establishment
# probability can be attributed across pathways instead of only summed as mass.
EVENTS: list[dict[str, object]] = []


def build_run_spec(epochs: int, agents: int, platform: str, seed: int) -> dict:
    """The Picard run spec the harness drives the instrumented voyage with."""
    return {
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


def accumulate(
    pid: str,
    agent_pathway_doses: dict,
    target: dict[tuple[str, str], float],
) -> None:
    """Add every agent's pathway doses into *target*, keyed by (pathogen, pathway)."""
    for pw in agent_pathway_doses.values():
        for name, dose in pw.items():
            target[(pid, name)] += float(dose)


def exposure_records(
    pid: str,
    agent_doses: dict,
    pre_by_agent: dict,
    post_pathways: dict,
) -> list[dict[str, object]]:
    """One record per nonzero exposure, carrying both dose streams."""
    records: list[dict[str, object]] = []
    for aid, total in agent_doses.items():
        t = float(total)
        if t <= 0.0:
            continue
        pre = pre_by_agent.get(aid, {})
        records.append({
            "pathogen_id": pid,
            "post_total": t,
            "post": {k: float(v) for k, v in post_pathways.get(aid, {}).items()},
            "pre_total": sum(pre.values()),
            "pre": pre,
        })
    return records


def summary_lines(
    pre: dict[tuple[str, str], float],
    post: dict[tuple[str, str], float],
) -> list[str]:
    """The per-pathogen pre/post pathway report, one line per output row."""
    lines: list[str] = []
    for pid in sorted({k[0] for k in pre}):
        keys = [k for k in pre if k[0] == pid]
        pre_total = sum(pre[k] for k in keys)
        post_total = sum(post[k] for k in keys)
        lines.append(f"\n--- {pid} ---")
        lines.append(f"{'pathway':22} {'pre-weight':>14} {'share':>8} "
                     f"{'post-weight':>14} {'share':>8} {'w':>6}")
        for key in sorted(keys, key=lambda k: -pre[k]):
            name = key[1]
            wkey = PATHWAY_WEIGHT_KEYS.get(name, name)
            w = (post[key] / pre[key]) if pre[key] else float("nan")
            lines.append(f"{name:22} {pre[key]:14.4g} {pre[key]/pre_total:8.4f} "
                         f"{post[key]:14.4g} {post[key]/post_total:8.4f} "
                         f"{w:6.3f} ({wkey})")
        lines.append(f"{'TOTAL':22} {pre_total:14.4g} {1.0:8.4f} "
                     f"{post_total:14.4g} {1.0:8.4f}")
        if pre_total:
            lines.append("realised attenuation sum(w_r D_r)/sum(D_r) = "
                         f"{post_total/pre_total:.4f}")
    return lines


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
    accumulate(pid, pre_by_agent, PRE)
    _original(self, profile, agent_doses, agent_pathway_doses)
    accumulate(pid, agent_pathway_doses, POST)
    EVENTS.extend(
        exposure_records(pid, agent_doses, pre_by_agent, agent_pathway_doses)
    )


TransmissionCore._apply_route_weights = _instrumented


def main() -> int:
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 240
    agents = int(sys.argv[2]) if len(sys.argv) > 2 else 450
    platform = sys.argv[3] if len(sys.argv) > 3 else "expedition_cruise_450"
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 500
    spec = build_run_spec(epochs, agents, platform, seed)
    with tempfile.TemporaryDirectory() as tmp:
        path = resolve_repo_path(tmp, "run_spec.json")
        with validated_open(
            path, "w", allowed_roots=(tmp,), encoding="utf-8"
        ) as handle:
            handle.write(json.dumps(spec))
        picard = PicardRunSpec.from_picard_json(str(ROOT), str(path))
        ShipSimulation(picard, display=False).run()

    print(f"epochs={epochs} agents={agents} platform={platform} seed={seed}")
    for line in summary_lines(PRE, POST):
        print(line)

    # mkdtemp gives a 0700 directory under gettempdir(); the shared temp root
    # itself is world-writable, which validated_open refuses to write into.
    temp_root = tempfile.mkdtemp(prefix="route_weight_")
    out = resolve_child_path(
        temp_root, f"exposure_events_{platform}_s{seed}.json"
    )
    with validated_open(
        out, "w", allowed_roots=(temp_root,), encoding="utf-8"
    ) as handle:
        handle.write(json.dumps(EVENTS))
    print(f"\n{len(EVENTS)} nonzero exposure events written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
