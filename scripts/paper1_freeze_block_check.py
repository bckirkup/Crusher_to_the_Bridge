#!/usr/bin/env python3
"""Verify the Paper-1 frozen config block against the config machinery.

Reads the verbatim JSON block out of the freeze design contract, loads it
through the loader path NORO-GENO-02 used (manifest tier ``config_overrides``
-> ``generate_tier_runs`` -> ``PicardRunSpec.from_picard_dict`` ->
``ShipSimulation.initialize()``, zero epochs stepped) and checks, per pinned
leaf: the path resolves in the merged config, a named consumer file reads the
key, and - where the consumer resolves the key at ``initialize()`` - flipping
the leaf moves the resolved engine state (so the pin is not dead).

Evidence is reported in two categories that are never added together:
*resolved-state* (the engine's own attribute after ``initialize()``) and
*configuration-only* (merged cfg carries the value and the consumer file
names the key; nothing to probe before an epoch runs). Grouped dictionaries
are expanded and checked leaf by leaf. An exception during a flip fails the
check unless that exact rejection is declared in ``EXPECTED_REJECTIONS``.
Resolved-state probes, declared role counts and the committed example run
specifications are checked on every reference hull, on the cell the runner
generates after all of its axes are applied.

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
from typing import Any, NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

CONTRACT = "docs/norovirus/paper1_freeze_design_contract_2026_11_20.md"
BLOCK_MARKER = "<!-- paper1-frozen-config-block -->"
POPULATION_MARKER = "<!-- paper1-reference-population -->"
ANNEX = "docs/norovirus/paper1_reference_run_specs_2026_11_21.json"
LEGACY_YAML = "crusher_labs/config.yaml"
SOURCE_REGISTRY = "data/config/provisioning_sources.json"
STRATEGY = "syndromic_comp65"
PATHOGEN_ID = "norwalk_gi"
NAMED_COMMIT_PLACEHOLDER = "<named commit>"
LINE_LIST_REQUEST = "<run_dir>/sentinel_line_list.json"
TEMPLATE_MANIFEST = (
    "picard_framework/runs/mega_cruise_campaign/noro_geno_02_mixture_manifest.json"
)
TEMPLATE_TIER = "fl_exp_7d_rep_mixture"
DOSE_ADJUSTMENT = 7.57
# Example voyage length per hull. The joint-evaluation lengths (168/288/504)
# differ only in ``run.num_epochs``; 192 is the Explorer reconstruction's.
HULLS: dict[str, int] = {
    "expedition_cruise_450": 168,
    "classic_cruise_1900": 168,
    "spirit_cruise_3000": 168,
    "mega_cruise_5000": 168,
    "explorer_seas_06": 192,
}
FLIP_HULL = "expedition_cruise_450"

TX = "engines/transmission_core.py"
CONTAM = "engines/py_contam_bridge.py"
SIM = "picard_framework/simulation/ship_simulation.py"
EPOCH_READ = "cfg-read"
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
     "tx.activity_contacts?"),
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


# Flips the engine is *expected* to refuse at initialize(), with the message
# fragment that identifies the refusal. Any other exception fails the check.
EXPECTED_REJECTIONS: dict[str, tuple[str, str]] = {
    "transmission.contact_mode": (
        "ValueError",
        "activity_contacts requires contact_mode per_partner_contact",
    ),
    "transmission.intra_epoch_substeps": (
        "ValueError",
        "intra_epoch_substeps > 1 requires",
    ),
}

# Pins the engine reads but that cannot move a run while another pinned value
# holds. They are live keys, not independently influential ones.
CONDITIONAL: dict[str, str] = {
    "transmission.intra_epoch_causal_order":
        "inactive while contamination_solver = continuous",
    "transmission.intra_epoch_substeps":
        "inactive while contamination_solver = continuous",
    "transmission.flush_cabin_emission":
        "inactive while flush_aerosol_fraction = 0.0",
}

# Grouped units: every scalar leaf of the pinned dictionary -> (probe, index
# path into the probed value). A pinned leaf with no entry fails the check.
_RATE_KEYS = ("cabin", "corridor", "work_service", "work_other",
              "dining_table", "dining_venue", "leisure", "other")
GROUP_PROBES: dict[str, dict[str, tuple[str, tuple[str, ...]]]] = {
    "transmission.activity_contacts.rates_per_hour": {
        key: ("tx.activity_contacts", (key,)) for key in _RATE_KEYS
    },
    "transmission.surface_cleaning.routine": {
        "coverage": ("tx.routine_cleaning_coverage", ()),
        "log10_reduction": ("tx.routine_cleaning_log10_reduction", ()),
        "events_per_day": ("tx.routine_cleaning_events_per_day", ()),
    },
    "transmission.surface_cleaning.outbreak_response": {
        "coverage": ("tx.outbreak_cleaning_coverage", ()),
        "log10_reduction": ("tx.outbreak_cleaning_log10_reduction", ()),
        "events_per_day": ("tx.outbreak_cleaning_events_per_day", ()),
        "by_zone_class.cabin.events_per_day": (
            "tx.outbreak_cleaning_by_zone_class", ("cabin", "events_per_day"),
        ),
    },
    "transmission.common_source.provisioned_source": {
        "source_id": ("tx._cs_ps_source_id", ()),
        "lot_layer_mode": ("tx._cs_ps_lot_layer_mode", ()),
    },
}
GROUP_ALTERNATES: dict[str, Any] = {
    "transmission.common_source.provisioned_source.source_id":
        "paper1_absent_source",
    "transmission.common_source.provisioned_source.lot_layer_mode":
        "single_line_receipt",
}

# (hull, leaf) whose effective state is known not to follow the pin, and the
# work that resolves it. Reported, not failed; an entry that no longer
# reproduces fails the check so it cannot outlive its fix.
PENDING_EFFECTIVE: dict[tuple[str, str], str] = {
    ("explorer_seas_06", "transmission.exposure_cap.enabled"):
        "platform absent from the rhythm/event catalog; WP1c eligibility "
        "correction",
}


class Leaf(NamedTuple):
    """One scalar pin, or one presence pin, of a declared unit."""

    unit: str
    path: str
    pinned: Any
    alt: Any
    consumer: str
    expr: str
    keys: tuple[str, ...]

    @property
    def config_only(self) -> bool:
        return self.expr == EPOCH_READ


def load_marked_json(contract: Path, marker: str) -> dict[str, Any]:
    """Return the JSON block that follows ``marker`` in the contract."""
    text = contract.read_text(encoding="utf-8")
    match = re.search(
        re.escape(marker) + r"\s*```json\n(.*?)\n```", text, re.DOTALL,
    )
    if match is None:
        raise SystemExit(f"no JSON block after {marker} in {contract}")
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


def scalar_leaves(tree: Any, prefix: str = "") -> dict[str, Any]:
    """Every scalar leaf of a nested mapping, by dotted path."""
    if not isinstance(tree, dict):
        return {prefix.rstrip("."): tree}
    out: dict[str, Any] = {}
    for key, value in tree.items():
        out.update(scalar_leaves(value, f"{prefix}{key}."))
    return out


def unit_paths(tree: dict[str, Any], prefix: str = "") -> list[str]:
    """Dotted paths of the block, stopping at the granularity ROWS declares."""
    declared = {row[0] for row in ROWS}
    out: list[str] = []
    for key, value in tree.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict) and path not in declared:
            out.extend(unit_paths(value, f"{path}."))
        else:
            out.append(path)
    return out


def numeric_alternate(value: Any) -> Any:
    return value * 0.5 if value else 0.5


def build_leaves(block: dict[str, Any]) -> tuple[list[Leaf], list[str]]:
    """Expand ROWS to scalar leaves; return them with any coverage gaps."""
    leaves: list[Leaf] = []
    gaps: list[str] = []
    for unit, alt, consumer, expr in ROWS:
        pinned = get_path(block, unit)
        if not isinstance(pinned, dict):
            leaves.append(Leaf(unit, unit, pinned, alt, consumer, expr, ()))
            continue
        probes = GROUP_PROBES.get(unit, {})
        pinned_leaves = scalar_leaves(pinned)
        gaps += [f"{unit}.{sub}: no probe" for sub in pinned_leaves
                 if sub not in probes]
        gaps += [f"{unit}.{sub}: probe without a pinned leaf" for sub in probes
                 if sub not in pinned_leaves]
        for sub, value in pinned_leaves.items():
            if sub not in probes:
                continue
            path = f"{unit}.{sub}"
            leaf_alt = (GROUP_ALTERNATES[path] if path in GROUP_ALTERNATES
                        else numeric_alternate(value))
            leaves.append(Leaf(unit, path, value, leaf_alt, consumer,
                               probes[sub][0], probes[sub][1]))
    return leaves, gaps


def reference_classes(counts: dict[str, int]) -> list[dict[str, Any]]:
    """The YAML agent classes with exact ``count`` in place of ``fraction``."""
    import yaml

    cfg = yaml.safe_load((REPO_ROOT / LEGACY_YAML).read_text(encoding="utf-8"))
    classes = copy.deepcopy(cfg["ship_graph"]["agent_classes"])
    if {cls["class_id"] for cls in classes} != set(counts):
        raise SystemExit("reference class_counts do not name the YAML classes")
    for cls in classes:
        cls.pop("fraction", None)
        cls["count"] = int(counts[cls["class_id"]])
    return classes


def build_raw(
    overrides: dict[str, Any] | None,
    hull: str,
    population: dict[str, Any],
    *,
    exact_counts: bool = True,
) -> dict[str, Any]:
    """One generated cell through the NORO-GENO-02 manifest path.

    The returned mapping is what the runner emits after its own axes
    (escalation, surveillance strategy, boarding, ``ship_graph.num_agents``).
    """
    from picard_framework.runs.mega_cruise_campaign import campaign_runner

    manifest = json.loads(
        (REPO_ROOT / TEMPLATE_MANIFEST).read_text(encoding="utf-8"),
    )
    declared = population["hulls"][hull]
    tier = manifest["tiers"][TEMPLATE_TIER]
    tier["platform"] = hull
    tier["num_agents"] = declared["num_agents"]
    tier["epoch_durations"] = [HULLS[hull]]
    tier["seeds"] = tier["seeds"][:1]
    tier["dose_adjustments"] = [DOSE_ADJUSTMENT]
    tier["surveillance_strategies"] = [STRATEGY]
    cell = copy.deepcopy(overrides) if overrides is not None else {}
    if exact_counts:
        cell["ship_graph"] = {"agent_classes": reference_classes(
            declared["reference"]["class_counts"],
        )}
    if cell:
        tier["config_overrides"] = cell
    else:
        tier.pop("config_overrides", None)
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


def probe(sim: Any, expr: str, keys: tuple[str, ...] = ()) -> Any:
    """Read a resolved value; a trailing ``?`` reads presence / class name."""
    presence = expr.endswith("?")
    root, *attrs = expr.rstrip("?").split(".")
    node = sim.tx_core if root == "tx" else sim
    for attr in attrs:
        node = getattr(node, attr)
    if presence:
        return None if node is None else type(node).__name__
    for key in keys:
        node = node[key]
    if isinstance(node, dict) and set(node) == {"passenger", "crew"} and (
        node["passenger"] == node["crew"]
    ):
        node = node["passenger"]  # one declared rate applied to both roles
    return copy.deepcopy(node)


def honoured(leaf: Leaf, resolved: Any) -> bool:
    """Whether the engine's resolved state is the pinned value."""
    if leaf.expr.endswith("?"):
        wanted = bool(leaf.pinned) and leaf.pinned != "none"
        return (resolved is not None) == wanted
    if isinstance(resolved, SCALARS) and isinstance(leaf.pinned, SCALARS):
        return resolved == leaf.pinned
    return True


def flip_moves_state(
    block: dict[str, Any], leaf: Leaf, alt: Any, resolved: Any,
    population: dict[str, Any],
) -> str:
    """Flip one leaf; classify what the engine did with the alternate."""
    try:
        sim = init_sim(parse_spec(build_raw(
            with_leaf(block, leaf.path, alt), FLIP_HULL, population,
        )))
    except Exception as exc:  # classified below; never silently "live"
        name = type(exc).__name__
        expected = EXPECTED_REJECTIONS.get(leaf.path)
        if expected and expected[0] == name and expected[1] in str(exc):
            return f"expected rejection ({name}: {expected[1]})"
        return f"UNEXPECTED {name}: {str(exc)[:120]}"
    if leaf.path in EXPECTED_REJECTIONS:
        return "UNEXPECTED: declared rejection did not occur"
    return "live" if probe(sim, leaf.expr, leaf.keys) != resolved else "DEAD"


def default_value(default_cfg: dict[str, Any], dotted: str) -> str:
    try:
        return json.dumps(get_path(default_cfg, dotted))
    except (KeyError, TypeError):
        return "absent"


def check_leaf(
    leaf: Leaf,
    block: dict[str, Any],
    cfgs: dict[str, dict[str, Any]],
    sims: dict[str, Any],
    population: dict[str, Any],
) -> dict[str, Any]:
    name = leaf.path.split(".")[-1]
    source = (REPO_ROOT / leaf.consumer).read_text(encoding="utf-8")
    result: dict[str, Any] = {
        "unit": leaf.unit,
        "path": leaf.path,
        "pinned": json.dumps(leaf.pinned),
        "default": default_value(cfgs["default"], leaf.path),
        "consumer": leaf.consumer,
        "evidence": "configuration-only" if leaf.config_only
        else "resolved-state",
        "reads_key": f'"{name}"' in source,
        "merged": get_path(cfgs["pinned"], leaf.path) == leaf.pinned,
        "honoured": True,
        "conditional": CONDITIONAL.get(leaf.path, ""),
    }
    if leaf.config_only:
        result.update(resolved=EPOCH_READ, default_resolved=EPOCH_READ,
                      liveness="cfg + consumer read")
    else:
        resolved = probe(sims["pinned"], leaf.expr, leaf.keys)
        fallback = probe(sims["default"], leaf.expr, leaf.keys)
        alt = fallback if leaf.alt == leaf.pinned else leaf.alt
        result.update(
            honoured=honoured(leaf, resolved),
            resolved=repr(resolved),
            default_resolved=repr(fallback),
            liveness=flip_moves_state(block, leaf, alt, resolved, population),
        )
    if not result["honoured"]:
        result["liveness"] = "NOT HONOURED (resolved value is not the pin)"
    bad = any(tag in result["liveness"]
              for tag in ("DEAD", "UNEXPECTED", "NOT HONOURED"))
    result["ok"] = bool(result["reads_key"] and result["merged"] and not bad)
    return result


def role_counts(sim: Any) -> dict[str, Any]:
    """Role and class head counts of the initialized agents."""
    agents = sim.engine.agents
    classes: dict[str, int] = {}
    for agent in agents:
        classes[agent.agent_class] = classes.get(agent.agent_class, 0) + 1
    crew = sum(1 for agent in agents if agent.role == "crew")
    return {"num_agents": len(agents), "passenger": len(agents) - crew,
            "crew": crew, "class_counts": classes}


def check_population(
    hull: str, sim: Any, baseline_sim: Any, population: dict[str, Any],
) -> list[str]:
    """Declared role counts against initialized agents, both allocations."""
    declared = population["hulls"][hull]
    layout = json.loads(
        (REPO_ROOT / "data/platforms" / hull / "spatial_layout.json")
        .read_text(encoding="utf-8"),
    )
    nominal = layout["nominal_complement"]
    reference = declared["reference"]
    got = role_counts(sim)
    base = role_counts(baseline_sim)
    template = declared["archetype_template_baseline"]
    problems: list[str] = []
    if (reference["passenger"], reference["crew"]) != (
        nominal["passengers"], nominal["crew"],
    ):
        problems.append(f"{hull}: declared reference is not the platform's "
                        "nominal_complement")
    for key in ("passenger", "crew", "class_counts"):
        if got[key] != reference[key]:
            problems.append(f"{hull}: initialized {key} {got[key]} != "
                            f"declared {reference[key]}")
    if got["num_agents"] != declared["num_agents"]:
        problems.append(f"{hull}: initialized {got['num_agents']} agents")
    for key in ("passenger", "crew"):
        if base[key] != template[key]:
            problems.append(f"{hull}: template-allocation {key} {base[key]} "
                            f"!= declared baseline {template[key]}")
    return problems


def check_hull_state(
    hull: str, spec: Any, sim: Any, block: dict[str, Any], leaves: list[Leaf],
) -> tuple[list[str], list[str]]:
    """Post-runner cfg and resolved state of one hull; (failures, pending)."""
    failures = [
        f"{hull}: cfg MISMATCH at {path}"
        for path, value in scalar_leaves(block).items()
        if get_path(spec.legacy_cfg, path) != value
    ]
    pending: list[str] = []
    for leaf in leaves:
        if leaf.config_only:
            continue
        held = honoured(leaf, probe(sim, leaf.expr, leaf.keys))
        reason = PENDING_EFFECTIVE.get((hull, leaf.path))
        if reason and held:
            failures.append(f"{hull}: stale PENDING entry {leaf.path}")
        elif reason:
            pending.append(f"{hull}: {leaf.path} not effective ({reason})")
        elif not held:
            failures.append(f"{hull}: resolved state is not the pin at "
                            f"{leaf.path}")
    return failures, pending


def resolved_record(
    hull: str, spec: Any, sim: Any, leaves: list[Leaf],
) -> dict[str, Any]:
    """What the generated cell resolves to, for the run-spec annex."""
    cfg = spec.legacy_cfg
    graph = cfg["ship_graph"]
    tx = sim.tx_core
    profile = sim.pathogen_profiles[PATHOGEN_ID]
    registry = json.loads(
        (REPO_ROOT / SOURCE_REGISTRY).read_text(encoding="utf-8"),
    )["sources"][tx._cs_ps_source_id]
    return {
        "population": role_counts(sim),
        "introduction": cfg["initiation"],
        "reporting": {
            "infection_counters": graph["infection_counters"],
            "counter_confinement_enabled": graph["counter_confinement_enabled"],
            "syndromic": cfg["syndromic"],
            "escalation": cfg["escalation"],
        },
        "strategy": {
            "name": STRATEGY,
            "fred_behavior": cfg["fred_behavior"],
            "diagnostic_cascade_enabled": cfg["diagnostic_cascade"]["enabled"],
        },
        "source": {
            "source_id": tx._cs_ps_source_id,
            "lot_layer_mode": tx._cs_ps_lot_layer_mode,
            "prevalence_scale": tx._cs_ps_prevalence_scale,
            "preparation_survival_mode": tx._cs_ps_preparation_survival_mode,
            "q_source": registry["q_source"],
            "q_source_by_item_line": registry["q_source_by_item_line"],
        },
        "pathogen": {
            "pathogen_id": PATHOGEN_ID,
            "dose_adjustment": profile.get("dose_adjustment"),
            "shedding_variance_log10": profile.get("shedding_variance_log10"),
            "airborne_emission_mode": profile.get("airborne_emission_mode"),
        },
        "mechanism_state": {
            leaf.path: probe(sim, leaf.expr, leaf.keys)
            for leaf in leaves if not leaf.config_only
        },
        "pending_effective_state": {
            path: reason for (name, path), reason in PENDING_EFFECTIVE.items()
            if name == hull
        },
    }


def annex_entry(
    hull: str, raw: dict[str, Any], spec: Any, sim: Any, leaves: list[Leaf],
) -> dict[str, Any]:
    """One hull's example run specification, as the generated cell sees it."""
    run_spec = copy.deepcopy(raw)
    # Output requests the cell worker adds; neither is a config override.
    run_spec["run"]["sentinel_line_list"] = LINE_LIST_REQUEST
    run_spec["campaign_parameters"]["engine_git_sha"] = NAMED_COMMIT_PLACEHOLDER
    return {
        "run_spec": run_spec,
        "resolved": resolved_record(hull, spec, sim, leaves),
    }


def print_leaf_results(results: list[dict[str, Any]], markdown: bool) -> None:
    for res in results:
        note = f"; conditional: {res['conditional']}" if res["conditional"] else ""
        if markdown:
            print(
                f"| `{res['path']}` | `{res['default']}` | "
                f"`{res['default_resolved']}` | `{res['pinned']}` | "
                f"`{res['consumer']}` | {res['evidence']} | "
                f"{res['liveness']}{note} |",
            )
        else:
            flag = "ok  " if res["ok"] else "FAIL"
            print(f"{flag} [{res['evidence']}] {res['path']} = {res['pinned']} "
                  f"[default {res['default']}; resolved {res['resolved']}; "
                  f"{res['liveness']}{note}]")


def check_hulls(
    block: dict[str, Any], leaves: list[Leaf], population: dict[str, Any],
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Every reference hull: generated cell, resolved state, role counts."""
    annex: dict[str, Any] = {}
    failures: list[str] = []
    pending: list[str] = []
    for hull in HULLS:
        raw = build_raw(block, hull, population)
        spec = parse_spec(raw)
        sim = init_sim(spec)
        baseline = init_sim(parse_spec(
            build_raw(block, hull, population, exact_counts=False),
        ))
        hull_failures, hull_pending = check_hull_state(
            hull, spec, sim, block, leaves,
        )
        hull_failures += check_population(hull, sim, baseline, population)
        counts = role_counts(sim)
        print(f"{hull}: generated cell initialises; "
              f"{counts['passenger']} passengers / {counts['crew']} crew; "
              f"{len(hull_failures)} failures, {len(hull_pending)} pending")
        failures += hull_failures
        pending += hull_pending
        annex[hull] = annex_entry(hull, raw, spec, sim, leaves)
    return annex, failures, pending


def check_annex(annex: dict[str, Any], write: bool) -> list[str]:
    """Write the annex, or require the committed one to match."""
    path = REPO_ROOT / ANNEX
    text = json.dumps(annex, indent=1, sort_keys=True) + "\n"
    if write:
        path.write_text(text, encoding="utf-8")
        print(f"annex written: {ANNEX}")
        return []
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        return [f"{ANNEX} is not what the generated cells resolve to "
                "(re-run with --write-annex and review the diff)"]
    print(f"annex matches: {ANNEX}")
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--markdown", action="store_true",
                        help="emit the per-leaf table as Markdown rows")
    parser.add_argument("--write-annex", action="store_true",
                        help="regenerate the example run-spec annex")
    args = parser.parse_args()

    contract = REPO_ROOT / CONTRACT
    block = load_marked_json(contract, BLOCK_MARKER)
    population = load_marked_json(contract, POPULATION_MARKER)
    declared = {row[0] for row in ROWS}
    units = set(unit_paths(block))
    if units != declared:
        print("block/ROWS mismatch:", sorted(units ^ declared))
        return 1
    leaves, gaps = build_leaves(block)

    specs = {"pinned": parse_spec(build_raw(block, FLIP_HULL, population)),
             "default": parse_spec(build_raw(None, FLIP_HULL, population))}
    cfgs = {name: spec.legacy_cfg for name, spec in specs.items()}
    sims = {name: init_sim(spec) for name, spec in specs.items()}
    results = [check_leaf(leaf, block, cfgs, sims, population)
               for leaf in leaves]
    print_leaf_results(results, args.markdown)
    if args.markdown:
        return 0

    annex, failed, pending = check_hulls(block, leaves, population)
    failed += check_annex(annex, args.write_annex)
    failed += gaps
    failed += [r["path"] for r in results if not r["ok"]]
    moved = [r["path"] for r in results
             if r["resolved"] != r["default_resolved"]]
    config_only = sum(1 for leaf in leaves if leaf.config_only)
    rejected = [r["path"] for r in results
                if r["liveness"].startswith("expected rejection")]
    conditional = [r["path"] for r in results if r["conditional"]]
    print(f"declared units: {len(ROWS)}; scalar leaves: {len(leaves)} "
          f"(block scalar leaves: {len(scalar_leaves(block))})")
    print(f"evidence: resolved-state {len(leaves) - config_only}; "
          f"configuration-only {config_only}")
    print(f"expected validation rejections: {len(rejected)}; "
          f"conditionally inactive pins: {len(conditional)}")
    print(f"failures: {len(failed)}; pending: {len(pending)}; resolved state "
          f"differing from no-block default: {len(moved)}")
    for label, items in (("EXPECTED REJECTION", rejected),
                         ("CONDITIONAL", conditional),
                         ("DIFFERS FROM DEFAULT", moved),
                         ("PENDING", pending), ("FAILED", failed)):
        for item in items:
            print(f"{label}: {item}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
