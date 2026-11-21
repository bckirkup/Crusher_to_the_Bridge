#!/usr/bin/env python3
"""Verify the Paper-1 frozen config block against the config machinery.

Reads the verbatim JSON block out of the freeze design contract, loads it
through the loader path NORO-GENO-02 used (manifest tier ``config_overrides``
-> ``generate_tier_runs`` -> ``PicardRunSpec.from_picard_dict`` ->
``ShipSimulation.initialize()``, zero epochs stepped) and checks, per pinned
leaf: the path resolves in the merged config, a named consumer file reads the
key, and - where the consumer resolves the key at ``initialize()`` - flipping
the leaf moves the resolved engine state (so the pin is not dead).

The flip probes run on one hull. Platform-gated mechanisms can resolve
differently per hull under the same block, so the exposure cap's effective
state is additionally resolved on every reference hull and must equal the
block's request on each of them.

No voyage epoch is stepped. Re-run on the final named commit at freeze time.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

CONTRACT = "docs/norovirus/paper1_freeze_design_contract_2026_11_20.md"
BLOCK_MARKER = "<!-- paper1-frozen-config-block -->"
TEMPLATE_MANIFEST = (
    "picard_framework/runs/mega_cruise_campaign/noro_geno_02_mixture_manifest.json"
)
TEMPLATE_TIER = "fl_exp_7d_rep_mixture"
DOSE_ADJUSTMENT = 7.57
HULLS: dict[str, int] = {
    "expedition_cruise_450": 450,
    "classic_cruise_1900": 1910,
    "spirit_cruise_3000": 3000,
    "mega_cruise_5000": 7000,
    "explorer_seas_06": 4428,
}
FLIP_HULL = "expedition_cruise_450"

TX = "engines/transmission_core.py"
CONTAM = "engines/py_contam_bridge.py"
SIM = "picard_framework/simulation/ship_simulation.py"
EPOCH_READ = "cfg-read"
CAP_ENABLED = "transmission.exposure_cap.enabled"
CAP_RINGS = "transmission.exposure_cap.include_fixed_rings"
SCALARS = (str, bool, int, float)

# (dotted path, alternate value, consumer file, resolved-state probe).
# ``EPOCH_READ`` marks a key whose consumer leaves nothing to probe after
# initialize(): it is read from cfg inside the epoch loop, or (transport_engine)
# its alternate needs the ContamX binary and falls back to native without it.
# Liveness then rests on the merged cfg carrying the value and the consumer
# file reading the key.
ROWS: tuple[tuple[str, Any, str, str], ...] = (
    ("transmission.contact_mode", "legacy", TX, "tx.contact_mode"),
    ("transmission.droplet_emission_mode", "shipped_uniform", TX,
     "tx.droplet_emission_mode"),
    ("transmission.droplet_field_split.mode", "off", TX,
     "tx.droplet_field_split.mode"),
    ("transmission.droplet_field_split.far_field_share", 0.3, TX,
     "tx.droplet_field_split.far_field_share"),
    ("transmission.droplet_field_split.settled_share", 0.1, TX,
     "tx.droplet_field_split.settled_share"),
    ("transmission.near_field_air.mode", "off", TX, "tx.near_field_air.mode"),
    ("transmission.near_field_air.interzonal_airflow_m3_per_hour", 100.0, TX,
     "tx.near_field_air.interzonal_airflow_m3_per_hour"),
    ("transmission.near_field_air.neighbour_table_ratio", 0.2, TX,
     "tx.near_field_air.neighbour_table_ratio"),
    ("transmission.room_air_removal.mode", "sealed", TX,
     "tx.room_air_removal.mode"),
    ("transmission.room_air_removal.map_arm", "ambient_off", TX,
     "tx.room_air_removal.map_arm"),
    ("transmission.room_air_removal.default_ach_per_hour", 1.0, TX,
     "tx.room_air_removal.default_ach_per_hour"),
    ("transmission.cabin_air_mode", "zone_pool", TX, "tx.cabin_air_mode"),
    ("transmission.cabin_cooccupancy.mode", "off", TX,
     "tx.cabin_cooccupancy.mode"),
    ("transmission.cabin_confined_fomite.mode", "off", TX,
     "tx.cabin_confined_fomite"),
    ("transmission.isolated_quarters_deposits.mode", "off", TX,
     "tx.isolated_quarters_deposits"),
    ("transmission.caregiver.mode", "off", TX, "tx.caregiver_mode"),
    ("transmission.caregiver.budget_mode", "additive", TX,
     "tx.caregiver_budget_mode"),
    ("transmission.sanitary_visit_mode", "dwell_weighted", TX,
     "tx.sanitary_visit_mode"),
    ("transmission.flush_aerosol_fraction", 1e-8, TX,
     "tx.flush_aerosol_fraction"),
    ("transmission.flush_cabin_emission", False, TX, "tx.flush_cabin_emission"),
    ("transmission.blackwater_plumbing", False, TX, "tx.blackwater_tank?"),
    ("transmission.hand_reservoir_mode", "wash_reuptake", TX,
     "tx.hand_reservoir_mode"),
    ("transmission.hand_redeposit_mode", "carriers", TX,
     "tx.hand_redeposit_mode"),
    ("transmission.contamination_solver", "discrete", TX,
     "tx.contamination_solver"),
    ("transmission.intra_epoch_causal_order", "ordered", TX,
     "tx.intra_epoch_order"),
    ("transmission.intra_epoch_substeps", 2, TX, "tx.intra_epoch_substeps"),
    ("transmission.high_touch_area_scale", 2.0, TX, "tx.high_touch_area_scale"),
    ("transmission.dining_party_contact_share", 0.5, TX,
     "tx.dining_party_contact_share"),
    ("transmission.contact_class_exponent", 0.5, TX,
     "tx.contact_class_exponent"),
    ("transmission.exposure_cap.enabled", False, TX, "tx._exposure_cap_active"),
    ("transmission.exposure_cap.include_fixed_rings", True, TX,
     "tx._exposure_cap_include_fixed_rings"),
    ("transmission.activity_contacts.enabled", False, TX,
     "tx.activity_contacts"),
    ("transmission.activity_contacts.rates_per_hour",
     {"cabin": 0.5, "corridor": 0.25, "work_service": 2.9, "work_other": 0.5,
      "dining_table": 2.0, "dining_venue": 2.0, "leisure": 1.0, "other": 0.0},
     TX, "tx.activity_contacts"),
    ("transmission.surface_cleaning.enabled", False, TX,
     "tx.surface_cleaning_enabled"),
    ("transmission.surface_cleaning.routine",
     {"coverage": 0.5, "log10_reduction": 1.29, "events_per_day": 1.0},
     TX, "tx.routine_cleaning_coverage"),
    ("transmission.surface_cleaning.outbreak_response",
     {"coverage": 0.9, "log10_reduction": 4.29, "events_per_day": 24.0},
     TX, "tx.outbreak_cleaning_coverage"),
    ("transmission.common_source.mode", "off", TX, "tx.common_source_mode"),
    ("transmission.common_source.lot_mode", "independent", TX,
     "tx._cs_lot_mode"),
    ("transmission.common_source.handler_mode", "independent", TX,
     "tx._cs_handler_mode"),
    ("transmission.common_source.diner_mode", "independent", TX,
     "tx._cs_diner_mode"),
    ("transmission.common_source.lot_mint_model", "fiat", TX,
     "tx._cs_lot_mint_model"),
    ("transmission.common_source.titre_draw_mode", "background", TX,
     "tx._cs_titre_mode"),
    ("transmission.common_source.lot_extent_mode", "declared", TX,
     "tx._cs_lot_extent_mode"),
    ("transmission.common_source.provisioned_source",
     {"source_id": "generic_cruise_port",
      "lot_layer_mode": "single_line_receipt"},
     TX, "tx._cs_ps_lot_layer_mode"),
    ("hvac.pathogen_pool_transport", "none", CONTAM,
     "sim.pathogen_pool_transport"),
    ("hvac.duty0_terminal_mode", "sealed", CONTAM,
     "sim.contam_engine.duty0_terminal_mode"),
    ("hvac.passive_link_mode", "oneway", CONTAM,
     "sim.contam_engine.passive_link_mode"),
    ("hvac.transport_engine", "contamx", CONTAM, EPOCH_READ),
    ("observation.enabled", False, SIM, EPOCH_READ),
    ("observation.surface_swab_source", "airborne_fraction",
     "orchestrator_epoch.py", EPOCH_READ),
    ("observation.wastewater_assay_mode", "legacy_reads",
     "orchestrator_init.py", "sim.obs.wastewater_assay?"),
    ("service_surface_knockout.enabled", True, TX,
     "tx.service_surface_knockout"),
    ("crew_duty_exclusion.enabled", True, SIM,
     "sim.crew_exclusion.policy.enabled"),
    ("variant_surveillance.enabled", True, SIM, EPOCH_READ),
    ("escalation.suspect_attack_rate", 0.01, "orchestrator_init.py",
     EPOCH_READ),
    ("escalation.confirm_attack_rate", 0.05, "orchestrator_init.py",
     EPOCH_READ),
    ("escalation.lockdown_attack_rate", 0.1, "orchestrator_init.py",
     EPOCH_READ),
)


def load_block(contract: Path) -> dict[str, Any]:
    """Return the JSON block that follows ``BLOCK_MARKER`` in the contract."""
    text = contract.read_text(encoding="utf-8")
    match = re.search(
        re.escape(BLOCK_MARKER) + r"\s*```json\n(.*?)\n```", text, re.DOTALL,
    )
    if match is None:
        raise SystemExit(f"no frozen block after {BLOCK_MARKER} in {contract}")
    return json.loads(match.group(1))


def get_path(tree: Any, dotted: str) -> Any:
    node = tree
    for part in dotted.split("."):
        node = node[part]
    return node


def with_leaf(block: dict[str, Any], dotted: str, value: Any) -> dict[str, Any]:
    out = copy.deepcopy(block)
    parts = dotted.split(".")
    node = out
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = value
    return out


def leaf_paths(tree: dict[str, Any], prefix: str = "") -> list[str]:
    """Dotted paths of the block, stopping at the granularity ROWS declares."""
    declared = {row[0] for row in ROWS}
    out: list[str] = []
    for key, value in tree.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict) and path not in declared:
            out.extend(leaf_paths(value, f"{path}."))
        else:
            out.append(path)
    return out


def build_raw(overrides: dict[str, Any] | None, hull: str) -> dict[str, Any]:
    """One run-spec mapping through the NORO-GENO-02 manifest path."""
    from picard_framework.runs.mega_cruise_campaign import campaign_runner

    manifest = json.loads(
        (REPO_ROOT / TEMPLATE_MANIFEST).read_text(encoding="utf-8"),
    )
    tier = manifest["tiers"][TEMPLATE_TIER]
    tier["platform"] = hull
    tier["num_agents"] = HULLS[hull]
    tier["seeds"] = tier["seeds"][:1]
    tier["dose_adjustments"] = [DOSE_ADJUSTMENT]
    if overrides is None:
        tier.pop("config_overrides", None)
    else:
        tier["config_overrides"] = overrides
    _run_id, raw = next(iter(
        campaign_runner.generate_tier_runs(manifest, TEMPLATE_TIER),
    ))
    return raw


def parse_spec(raw: dict[str, Any]) -> Any:
    from picard_framework.run_spec import PicardRunSpec

    return PicardRunSpec.from_picard_dict(str(REPO_ROOT), raw)


def init_sim(spec: Any) -> Any:
    from picard_framework.simulation.ship_simulation import ShipSimulation

    with contextlib.redirect_stdout(io.StringIO()):
        sim = ShipSimulation(spec, display=False)
        sim.initialize()
    return sim


def probe(sim: Any, expr: str) -> Any:
    """Read a resolved value; a trailing ``?`` reads presence / class name."""
    presence = expr.endswith("?")
    root, *attrs = expr.rstrip("?").split(".")
    node = sim.tx_core if root == "tx" else sim
    for attr in attrs:
        node = getattr(node, attr)
    if presence:
        return None if node is None else type(node).__name__
    return copy.deepcopy(node)


def flip_moves_state(
    block: dict[str, Any], dotted: str, alt: Any, expr: str, pinned: Any,
) -> str:
    """Flip one leaf; report whether the engine's resolved state follows it."""
    try:
        sim = init_sim(parse_spec(build_raw(with_leaf(block, dotted, alt),
                                            FLIP_HULL)))
    except Exception as exc:  # a rejected value is still a consumed key
        return f"live (flip rejected: {type(exc).__name__})"
    return "live" if probe(sim, expr) != pinned else "DEAD"


def flip_value(alt: Any, pinned: Any, fallback: Any) -> Any:
    """The alternate to flip to; the no-block default when the pin is ``alt``."""
    return fallback if alt == pinned else alt


def default_value(default_cfg: dict[str, Any], dotted: str) -> str:
    try:
        return json.dumps(get_path(default_cfg, dotted))
    except (KeyError, TypeError):
        return "absent"


def check_row(
    row: tuple[str, Any, str, str],
    block: dict[str, Any],
    cfgs: dict[str, dict[str, Any]],
    sims: dict[str, Any],
) -> dict[str, Any]:
    dotted, alt, consumer, expr = row
    pinned = get_path(block, dotted)
    leaf = dotted.split(".")[-1]
    source = (REPO_ROOT / consumer).read_text(encoding="utf-8")
    result: dict[str, Any] = {
        "path": dotted,
        "pinned": json.dumps(pinned),
        "default": default_value(cfgs["default"], dotted),
        "consumer": consumer,
        "reads_key": f'"{leaf}"' in source,
        "merged": get_path(cfgs["pinned"], dotted) == pinned,
    }
    result["honoured"] = True
    if expr == EPOCH_READ:
        result.update(resolved=EPOCH_READ, default_resolved=EPOCH_READ,
                      liveness="cfg + consumer read")
    else:
        resolved = probe(sims["pinned"], expr)
        fallback = probe(sims["default"], expr)
        # A parser that substitutes its default for an unknown value leaves
        # the pin unhonoured; comparable scalars must resolve to the pin.
        comparable = isinstance(resolved, SCALARS) and isinstance(pinned, SCALARS)
        if comparable and not expr.endswith("?"):
            result["honoured"] = resolved == pinned
        result.update(
            resolved=repr(resolved),
            default_resolved=repr(fallback),
            liveness=flip_moves_state(
                block, dotted, flip_value(alt, pinned, fallback), expr,
                resolved,
            ),
        )
    if not result["honoured"]:
        result["liveness"] = "NOT HONOURED (resolved value is not the pin)"
    result["ok"] = bool(
        result["reads_key"] and result["merged"] and result["honoured"]
        and "DEAD" not in result["liveness"],
    )
    return result


def cap_state(sim: Any) -> dict[str, bool]:
    """The exposure cap's effective state after ``initialize()``."""
    return {
        "active": probe(sim, "tx._exposure_cap_active"),
        "include_fixed_rings": probe(
            sim, "tx._exposure_cap_include_fixed_rings",
        ),
        "cap_stream": probe(sim, "tx._exposure_cap_rng?") is not None,
    }


def requested_cap_state(block: dict[str, Any]) -> dict[str, bool]:
    """What the block asks for; the cap stream exists exactly when armed."""
    enabled = get_path(block, CAP_ENABLED)
    return {
        "active": enabled,
        "include_fixed_rings": get_path(block, CAP_RINGS),
        "cap_stream": enabled,
    }


def hull_parse(block: dict[str, Any], hull: str) -> tuple[str, Any]:
    """Parse + initialize one hull; the sim is None on a merge mismatch."""
    spec = parse_spec(build_raw(block, hull))
    for dotted in leaf_paths(block):
        if get_path(spec.legacy_cfg, dotted) != get_path(block, dotted):
            return f"{hull}: MISMATCH at {dotted}", None
    return f"{hull}: parse + initialize OK", init_sim(spec)


def hull_cap_line(hull: str, sim: Any, requested: dict[str, bool]) -> str:
    """One hull's effective cap state against the block's request."""
    if sim is None:
        return f"{hull}: exposure cap UNRESOLVED (no initialized sim)"
    state = cap_state(sim)
    verdict = "ok" if state == requested else "DIVERGES"
    return (f"{hull}: exposure cap {verdict} - effective {state}; "
            f"requested {requested}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contract", default=CONTRACT)
    parser.add_argument("--markdown", action="store_true",
                        help="emit the per-key table as Markdown rows")
    args = parser.parse_args()

    block = load_block(REPO_ROOT / args.contract)
    declared = {row[0] for row in ROWS}
    leaves = set(leaf_paths(block))
    if leaves != declared:
        print("block/ROWS mismatch:", sorted(leaves ^ declared))
        return 1

    specs = {"pinned": parse_spec(build_raw(block, FLIP_HULL)),
             "default": parse_spec(build_raw(None, FLIP_HULL))}
    cfgs = {name: spec.legacy_cfg for name, spec in specs.items()}
    sims = {name: init_sim(spec) for name, spec in specs.items()}
    results = [check_row(row, block, cfgs, sims) for row in ROWS]

    for res in results:
        if args.markdown:
            print(
                f"| `{res['path']}` | `{res['default']}` | "
                f"`{res['default_resolved']}` | `{res['pinned']}` | "
                f"`{res['consumer']}` | {res['liveness']} |",
            )
        else:
            flag = "ok  " if res["ok"] else "FAIL"
            print(f"{flag} {res['path']} = {res['pinned']} "
                  f"[default {res['default']}; resolved {res['resolved']}; "
                  f"{res['liveness']}]")
    parsed = {hull: hull_parse(block, hull) for hull in HULLS}
    hull_lines = [line for line, _sim in parsed.values()]
    print("\n".join(hull_lines))
    requested = requested_cap_state(block)
    cap_lines = [hull_cap_line(hull, sim, requested)
                 for hull, (_line, sim) in parsed.items()]
    print("\n".join(cap_lines))
    failed = [r["path"] for r in results if not r["ok"]]
    failed += [line for line in hull_lines if "MISMATCH" in line]
    failed += [line for line in cap_lines if "exposure cap ok" not in line]
    moved = [r["path"] for r in results
             if r["resolved"] != r["default_resolved"]]
    print(f"pinned keys: {len(results)}; failures: {len(failed)}; "
          f"resolved state differing from no-block default: {len(moved)}")
    for item in moved:
        print("DIFFERS FROM DEFAULT:", item)
    for item in failed:
        print("FAILED:", item)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
