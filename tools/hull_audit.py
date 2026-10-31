#!/usr/bin/env python3
"""Fleet-wide hull-model audit — find design deviations without fleet data.

Audits the *declared* baseline of every ``data/platforms/*`` bundle for the
classes of realism defect that campaigns surfaced on the cruise hulls
(HD-sink traps, unventilated zones, capacity misreads, era-mismatched
ventilation). No simulation, no solver: the checks are graph bookkeeping
and derived-metric comparisons against the fleet's own distribution.

Checks (per platform, on the normal-steaming baseline):

  topology      every zone ventilated or classified exterior/void; adjacency
                connectivity (walk-path islands, orphan zones); referential
                integrity (group rooms, links, adjacency, serves, manifest)
  flow_closure  per-zone removal rate under the native engine's semantics
                (``ach x hvac_duty``; ``duty<=0 & oa>=1`` = dedicated
                exhaust); sealed volumes, starved exhausts, ventilation
                single-points (zones with no passive path if their group
                fails — the HVAC-casualty exposure map)
  metrics       m3/crew, dining seats/crew, sanitary capacity per 100 crew,
                berth capacity vs manifest assignment, removal ACH by zone
                class, evidence share, isolation capacity, deck coverage
  modes         zone_modes intent vs group-realized supply/exhaust
                direction; era-inconsistent modes (e.g. mech_ac on a WW2 hull)

Fleet pass: within-era IQR outlier flags on the metric panel, era-rule
contradictions (same-era platforms disagreeing on a zone class's inferred
vent mode), and the adjacency-type rate coverage table (which declared edge
types map to real passive rates vs the 10 m3/h default).

Operational statuses (lockdown, collective protection, HVAC casualty) are
*declared* deviations layered on this baseline — the audit flags only
unintentional design gaps, and reports whether a hull can express those
states (isolation capacity, sealable ventilation, passive fallbacks).

Usage::

    python3 tools/hull_audit.py                      # all platforms, markdown
    python3 tools/hull_audit.py --platforms midway_cv41 independence_cvl26
    python3 tools/hull_audit.py --json-out out.json --md-out report.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from simulation_utils.paths import validated_open  # noqa: E402

PLATFORMS_DIR = REPO_ROOT / "data" / "platforms"

# The passive-exchange rate table the CONTAM bridge honors; every other
# adjacency type silently receives the default below.
PASSIVE_RATES_M3H = {
    "passageway": 15.0,
    "service_hatch": 8.0,
    "ladder_well": 12.0,
    "sealed_door": 2.0,
}
PASSIVE_DEFAULT_M3H = 10.0

SEVERITY_ORDER = {"flag": 0, "note": 1}

# Modes whose declared intent is exhaust (from tools/ship_blueprint_import
# MODE_OA_FRACTION / ERA_RULES vocabulary).
_EXHAUST_MODES = {"mech_exhaust", "fume_exhaust", "exhaust_only"}
_SUPPLY_MODES = {"mech_supply_exhaust", "mech_ac", "nat_supply"}
_OPEN_MODES = {"open_air"}

# Zone-type buckets whose occupants make a sealed/unvented volume a defect.
_OCCUPIED_TYPES = {"Room", "Dining", "Medical", "Sanitary", "Engineering"}

_EXTERIOR_HINTS = (
    "open", "weather", "deck", "deckhouse_top", "deck_open", "fantail",
    "focsle", "poop", "flight", "gun_deck",
)
_VOID_HINTS = ("tank", "hold", "void", "peak", "ballast", "cofferdam")

_BERTH_HINTS = ("berth", "quarter", "qtrs", "country", "stateroom", "cabin", "mess_deck", "accom")
_MESS_HINTS = ("mess", "galley", "wardroom", "scullery", "dining")
_MACH_HINTS = ("engine", "fire_rm", "machinery", "pump", "boiler", "uptake", "aux")
_SAN_HINTS = ("hd_", "head", "sanitary", "wash", "toilet", "w.c", "wc_")
_MED_HINTS = ("sick", "medical", "hospital", "dental", "dispensary")
_TANK_HINTS = ("tank", "hold", "fuel", "avgas", "ballast", "peak")
_MAG_HINTS = ("magazine", "ordnance", "bomb", "ammo", "rocket")
_OFFICE_HINTS = ("office", "ops", "radio", "chart", "bridge", "station", "shop", "control", "island")


@dataclass
class Finding:
    """One audit finding. severity 'flag' = design-defect candidate,
    'note' = deviation worth engineer review."""

    check: str
    severity: str
    scope: str
    message: str


@dataclass
class PlatformBundle:
    platform_id: str
    root: Path
    spatial: dict[str, Any]
    airflow: dict[str, Any]
    manifest: dict[str, Any] | None = None
    systems_notes: dict[str, Any] | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    @property
    def zones(self) -> list[dict[str, Any]]:
        return list(self.spatial.get("zones", []))

    @property
    def zone_ids(self) -> set[str]:
        return {z["id"] for z in self.zones}

    @property
    def groups(self) -> list[dict[str, Any]]:
        return list(self.airflow.get("hvac_zones", []))

    @property
    def era(self) -> str:
        notes = self.systems_notes or {}
        return str(notes.get("era", "uninferred"))


def _read_json(path: Path, *, allowed_roots: tuple[str, ...]) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with validated_open(str(path), "r", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        return json.load(fh)


def load_platform(root: Path) -> PlatformBundle:
    """Load one platform bundle; missing optional files are allowed."""
    allowed = (str(root.resolve()),)
    spatial = _read_json(root / "spatial_layout.json", allowed_roots=allowed) or {}
    airflow = _read_json(root / "air_flow_paths.json", allowed_roots=allowed) or {}
    pid = str(airflow.get("platform") or spatial.get("platform") or root.name)
    return PlatformBundle(
        platform_id=pid,
        root=root,
        spatial=spatial,
        airflow=airflow,
        manifest=_read_json(root / "crew_manifest.json", allowed_roots=allowed),
        systems_notes=_read_json(root / "systems_notes.json", allowed_roots=allowed),
    )


def _zone_signature(zone: dict[str, Any]) -> str:
    """Coarse zone class shared by the metrics panel and the era-consistency
    pivot: type first, then id hints refine Room/Free."""
    zid = zone["id"].lower()
    ztype = zone.get("type", "Room")
    rules: tuple[tuple[bool, str], ...] = (
        (ztype == "Sanitary" or any(h in zid for h in _SAN_HINTS), "sanitary"),
        (any(h in zid for h in _BERTH_HINTS), "berthing"),
        (ztype == "Dining" or any(h in zid for h in _MESS_HINTS), "mess"),
        (any(h in zid for h in _MED_HINTS), "medical"),
        (ztype == "Engineering" or any(h in zid for h in _MACH_HINTS), "machinery"),
        (any(h in zid for h in _MAG_HINTS), "magazine"),
        (any(h in zid for h in _TANK_HINTS), "tank_hold"),
        (any(h in zid for h in _EXTERIOR_HINTS), "weather_open"),
        (ztype == "Free", "open_other"),
        (any(h in zid for h in _OFFICE_HINTS), "ops_office"),
    )
    for ok, label in rules:
        if ok:
            return label
    return "room_other"


def _is_occupied(zone: dict[str, Any]) -> bool:
    return _zone_signature(zone) in {
        "berthing", "mess", "medical", "sanitary", "machinery",
        "ops_office", "room_other",
    } and zone.get("type") in _OCCUPIED_TYPES


def _is_exterior(zone: dict[str, Any]) -> bool:
    zid = zone["id"].lower()
    return zone.get("type") == "Free" and any(h in zid for h in _EXTERIOR_HINTS)


def _removal_ach(b: PlatformBundle) -> dict[str, float]:
    """Zone -> air changes removed per hour, mirroring
    build_zone_air_exchange_map semantics: ach x duty per room; the
    duty<=0 & oa>=1 branch is a dedicated exhaust and removes at full ach;
    ungrouped zones get no entry (sealed-room baseline)."""
    default_duty = float(b.airflow.get("hvac_duty", 1.0))
    default_oa = float(b.airflow.get("oa_fraction", 0.2))
    rates: dict[str, float] = {}
    for group in b.groups:
        ach = float(group.get("ach", 6.0))
        duty = max(float(group.get("hvac_duty", default_duty)), 0.0)
        oa = float(group.get("oa_fraction", default_oa))
        rate = ach * duty
        if duty <= 0.0 and oa >= 1.0:
            rate = ach
        for room in group.get("rooms", []):
            rates[room] = rate
    return rates


def _adjacency_graph(b: PlatformBundle) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = defaultdict(set)
    for edge in b.airflow.get("adjacency", []):
        graph[edge["from"]].add(edge["to"])
        graph[edge["to"]].add(edge["from"])
    return graph


def _components(graph: dict[str, set[str]], zone_ids: set[str]) -> list[list[str]]:
    seen: set[str] = set()
    comps: list[list[str]] = []
    for zid in sorted(zone_ids):
        if zid in seen or zid not in graph:
            continue
        stack, comp = [zid], []
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            comp.append(node)
            stack.extend(graph[node] - seen)
        comps.append(sorted(comp))
    return sorted(comps, key=len, reverse=True)


def _add(b: PlatformBundle, check: str, severity: str, scope: str, msg: str) -> None:
    b.findings.append(Finding(check=check, severity=severity, scope=scope, message=msg))


def _check_hvac_group_rooms(b: PlatformBundle, zids: set[str]) -> None:
    for group in b.groups:
        for room in group.get("rooms", []):
            if room not in zids:
                _add(b, "topology", "flag", room, f"hvac group {group['id']} lists unknown room")


def _check_link_endpoints(
    b: PlatformBundle, zids: set[str], gids: set[str], links: list[dict[str, Any]]
) -> None:
    for link in links:
        for end in (link.get("from"), link.get("to")):
            if end not in zids and end not in gids:
                _add(
                    b, "topology", "flag", str(end),
                    "cross_zone_links endpoint resolves to no zone or group",
                )


def _check_adjacency_endpoints(b: PlatformBundle, zids: set[str]) -> None:
    for edge in b.airflow.get("adjacency", []):
        for end in (edge.get("from"), edge.get("to")):
            if end not in zids:
                _add(b, "topology", "flag", str(end), "adjacency endpoint resolves to no zone")


def _check_zone_serves(b: PlatformBundle, zids: set[str]) -> None:
    for zone in b.zones:
        for served in zone.get("serves", []):
            if served not in zids:
                _add(b, "topology", "flag", zone["id"], f"serves -> {served} resolves to no zone")


def _check_graywater_zones(b: PlatformBundle, zids: set[str]) -> None:
    for gz in b.spatial.get("graywater_zones", []):
        if gz not in zids:
            _add(b, "topology", "flag", str(gz), "graywater_zones entry resolves to no zone")


def _check_manifest_zone_pins(b: PlatformBundle, zids: set[str]) -> None:
    manifest = b.manifest or {}
    for cls in manifest.get("manifest", []):
        for key in ("berth_zone", "duty_zone"):
            if cls.get(key) not in zids:
                _add(
                    b, "topology", "flag", cls.get("class_id", "?"),
                    f"{key}={cls.get(key)} resolves to no zone",
                )


def _check_references(b: PlatformBundle) -> None:
    zids = b.zone_ids
    gids = {g["id"] for g in b.groups}
    _check_hvac_group_rooms(b, zids)
    _check_link_endpoints(b, zids, gids, b.airflow.get("cross_zone_links", []))
    _check_adjacency_endpoints(b, zids)
    _check_zone_serves(b, zids)
    _check_graywater_zones(b, zids)
    _check_manifest_zone_pins(b, zids)


def _classify_ungrouped(
    ungrouped: list[dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    exterior, interior, void = [], [], []
    for zone in ungrouped:
        if _is_exterior(zone) or _zone_signature(zone) in {"weather_open", "open_other"}:
            exterior.append(zone["id"])
        elif _is_occupied(zone):
            interior.append(zone["id"])
        else:
            void.append(zone["id"])
    return exterior, interior, void


def _passive_path_label(zid: str, adj: dict[str, set[str]], linked: set[str | None]) -> str:
    if zid in adj:
        return "adjacency"
    if zid in linked:
        return "links"
    return "none"


def _flag_ungrouped_zones(
    b: PlatformBundle,
    by_id: dict[str, dict[str, Any]],
    interior: list[str],
    void: list[str],
    adj: dict[str, set[str]],
    linked: set[str | None],
) -> None:
    for zid in interior:
        z = by_id[zid]
        paths = _passive_path_label(zid, adj, linked)
        _add(
            b, "topology", "flag", zid,
            f"occupied {_zone_signature(z)} zone on no hvac group (passive path: {paths})",
        )
    for zid in void:
        _add(b, "topology", "note", zid, "unvented zone (tank/hold/void class) — sealed by design?")


def _flag_adjacency_orphans(
    b: PlatformBundle, by_id: dict[str, dict[str, Any]], orphans: list[str]
) -> None:
    authored_head = [
        i for i in orphans if i.startswith("HD_") or by_id[i].get("type") == "Sanitary"
    ]
    for zid in orphans:
        if zid in authored_head:
            continue
        z = by_id[zid]
        sev = "flag" if _is_occupied(z) else "note"
        _add(
            b, "topology", sev, zid,
            f"{_zone_signature(z)} zone declares no passage (walk-island gap or closed compartment)",
        )


def _flag_adjacency_fragments(b: PlatformBundle, comps: list[list[str]]) -> None:
    if len(comps) <= 1:
        return
    for frag in comps[1:]:
        if len(frag) <= 1:
            continue
        _add(
            b, "topology", "note", "+".join(frag[:4]),
            f"adjacency fragment of {len(frag)} zones disconnected from main graph",
        )


def _check_topology(b: PlatformBundle) -> dict[str, Any]:
    """Zone coverage census + adjacency connectivity."""
    _check_references(b)
    grouped = {r for g in b.groups for r in g.get("rooms", [])}
    linked = {l.get(k) for l in b.airflow.get("cross_zone_links", []) for k in ("from", "to")}
    adj = _adjacency_graph(b)
    by_id = {z["id"]: z for z in b.zones}
    ungrouped = [by_id[i] for i in sorted(b.zone_ids - grouped) if i in by_id]
    exterior, interior, void = _classify_ungrouped(ungrouped)
    _flag_ungrouped_zones(b, by_id, interior, void, adj, linked)
    census = {"ungrouped_exterior": exterior, "ungrouped_void": void, "ungrouped_occupied": interior}
    comps = _components(adj, b.zone_ids)
    orphans = [i for i in sorted(b.zone_ids) if i not in adj]
    _flag_adjacency_orphans(b, by_id, orphans)
    _flag_adjacency_fragments(b, comps)
    census["adjacency_components"] = [len(c) for c in comps]
    census["orphan_zones"] = orphans
    return census


def _link_flow_totals(b: PlatformBundle) -> tuple[dict[str, float], dict[str, float]]:
    links_in: dict[str, float] = defaultdict(float)
    links_out: dict[str, float] = defaultdict(float)
    for link in b.airflow.get("cross_zone_links", []):
        links_out[link["from"]] += float(link.get("flow_rate_m3h", 0.0))
        links_in[link["to"]] += float(link.get("flow_rate_m3h", 0.0))
    return links_in, links_out


def _dedicated_exhaust_flag(
    b: PlatformBundle,
    gid: str,
    group: dict[str, Any],
    links_in: dict[str, float],
    by_id: dict[str, dict[str, Any]],
) -> bool:
    duty = float(group.get("hvac_duty", b.airflow.get("hvac_duty", 1.0)))
    oa = float(group.get("oa_fraction", b.airflow.get("oa_fraction", 0.2)))
    dedicated_exhaust = duty <= 0.0 and oa >= 1.0
    if dedicated_exhaust and links_in.get(gid, 0.0) <= 0.0:
        rooms = group.get("rooms", [])
        sev = "flag" if any(by_id.get(r, {}).get("type") == "Sanitary" for r in rooms) else "note"
        _add(
            b, "flow_closure", sev, gid,
            "dedicated-exhaust group declares no makeup link in — draws only via passive paths",
        )
    return dedicated_exhaust


def _audit_group_rooms(
    b: PlatformBundle,
    group: dict[str, Any],
    dedicated_exhaust: bool,
    removal: dict[str, float],
    by_id: dict[str, dict[str, Any]],
    adj: dict[str, set[str]],
    links_in: dict[str, float],
    zone_to_group: dict[str, str],
    single_path: list[str],
) -> None:
    for room in group.get("rooms", []):
        if not dedicated_exhaust and removal.get(room, 0.0) <= 0.0:
            if room in by_id and _is_occupied(by_id[room]):
                _add(b, "flow_closure", "flag", room, "grouped but effective removal ~0 ACH")
    for room in group.get("rooms", []):
        if removal.get(room, 0.0) <= 0.0:
            continue
        passive = room in adj or links_in.get(zone_to_group.get(room, ""), 0.0) > 0.0
        if not passive:
            single_path.append(room)


def _flag_sealed_ungrouped(
    b: PlatformBundle,
    census: dict[str, Any],
    adj: dict[str, set[str]],
    by_id: dict[str, dict[str, Any]],
) -> None:
    for zid in census.get("ungrouped_occupied", []) + census.get("ungrouped_void", []):
        if zid in adj:
            continue
        z = by_id.get(zid, {})
        sev = "flag" if _is_occupied(z) else "note"
        _add(
            b, "flow_closure", sev, zid,
            "sealed volume: no hvac entry, no links, no passage — mass injected never leaves",
        )


def _check_flow(b: PlatformBundle, census: dict[str, Any]) -> dict[str, float]:
    removal = _removal_ach(b)
    adj = _adjacency_graph(b)
    gids = {g["id"]: g for g in b.groups}
    zone_to_group = {r: g["id"] for g in b.groups for r in g.get("rooms", [])}
    links_in, _links_out = _link_flow_totals(b)
    by_id = {z["id"]: z for z in b.zones}
    single_path: list[str] = []
    for gid, group in gids.items():
        dedicated = _dedicated_exhaust_flag(b, gid, group, links_in, by_id)
        _audit_group_rooms(
            b, group, dedicated, removal, by_id, adj, links_in, zone_to_group, single_path,
        )
    _flag_sealed_ungrouped(b, census, adj, by_id)
    if single_path:
        _add(
            b, "flow_closure", "note", ",".join(single_path[:6]),
            f"{len(single_path)} zones ventilated only by their group — HVAC casualty leaves them sealed",
        )
    return removal


def _mode_direction(mode: str) -> str:
    if mode in _EXHAUST_MODES:
        return "exhaust"
    if mode in _SUPPLY_MODES:
        return "supply"
    if mode in _OPEN_MODES:
        return "open"
    return "unknown"


def _group_direction(group: dict[str, Any], default_duty: float, default_oa: float) -> str:
    duty = float(group.get("hvac_duty", default_duty))
    oa = float(group.get("oa_fraction", default_oa))
    if duty <= 0.0 and oa >= 1.0:
        return "exhaust"
    if oa >= 1.0:
        return "open"
    return "supply"


def _collect_mode_mismatches(
    b: PlatformBundle, zone_modes: dict[str, Any]
) -> list[tuple[str, Any, str, str]]:
    default_duty = float(b.airflow.get("hvac_duty", 1.0))
    default_oa = float(b.airflow.get("oa_fraction", 0.2))
    zone_to_group = {r: g for g in b.groups for r in g.get("rooms", [])}
    mismatched: list[tuple[str, Any, str, str]] = []
    for zid, rec in zone_modes.items():
        group = zone_to_group.get(zid)
        if group is None:
            continue
        want = _mode_direction(str(rec.get("mode", "")))
        got = _group_direction(group, default_duty, default_oa)
        if want != "unknown" and got != "open" and want != got:
            mismatched.append((zid, rec.get("mode"), got, group["id"]))
    return mismatched


def _flag_ww2_mech_ac(b: PlatformBundle, zone_modes: dict[str, Any]) -> None:
    era = b.era
    if era not in {"usn_ww2", "rn_ww2", "merchant_ww2"}:
        return
    ac = [zid for zid, r in zone_modes.items() if r.get("mode") == "mech_ac"]
    if ac:
        _add(
            b, "modes", "flag", ",".join(ac[:5]),
            f"{len(ac)} zones carry mech_ac on a {era} hull — anachronistic mode",
        )


def _check_modes(b: PlatformBundle) -> None:
    notes = b.systems_notes or {}
    zone_modes = notes.get("zone_modes") or {}
    if not zone_modes:
        return
    for zid, mode, got, gid in _collect_mode_mismatches(b, zone_modes):
        _add(
            b, "modes", "note", zid,
            f"declared {mode} sits in {gid} realized as {got} — intent vs field mismatch",
        )
    _flag_ww2_mech_ac(b, zone_modes)


def _dining_seats(b: PlatformBundle) -> tuple[int, float]:
    seats = sum(int(z.get("max_occupancy", 0)) for z in b.zones if _zone_signature(z) == "mess")
    seatings = 1.0
    for z in b.zones:
        if _zone_signature(z) == "mess" and z.get("meal_seatings"):
            seatings = max(seatings, float(z["meal_seatings"]))
    return seats, seatings


def _berth_audit(b: PlatformBundle) -> tuple[int, int, list[tuple[str, int, int]]]:
    """Manifest headcount per berth zone vs effective capacity.

    ``max_occupancy`` is simultaneous presence; ``hot_bunk_ratio`` scales it
    (watch-rotation bunk sharing — declared on fiction hulls today, the
    lever a historic hull would declare if its oversubscription is real).
    """
    manifest = b.manifest or {}
    assigned: dict[str, int] = defaultdict(int)
    for cls in manifest.get("manifest", []):
        assigned[cls.get("berth_zone", "")] += int(cls.get("count", 0))
    cap_of = {
        z["id"]: int(z.get("max_occupancy", 0)) * max(int(z.get("hot_bunk_ratio") or 1), 1)
        for z in b.zones
    }
    cap = sum(cap_of.get(k, 0) for k in assigned)
    over = [(k, need, cap_of.get(k, 0)) for k, need in assigned.items() if need > cap_of.get(k, 0)]
    return sum(assigned.values()), cap, over


def _manifest_role_totals(manifest: dict[str, Any]) -> dict[str, int]:
    manifest_by_role: dict[str, int] = defaultdict(int)
    for c in manifest.get("manifest", []):
        manifest_by_role[str(c.get("role_group", "crew"))] += int(c.get("count", 0))
    return manifest_by_role


def _check_complement_vs_manifest(
    b: PlatformBundle, nc: dict[str, Any], manifest_by_role: dict[str, int]
) -> None:
    for role in ("crew", "passenger"):
        want = int(nc.get("crew" if role == "crew" else "passengers", 0) or 0)
        got = manifest_by_role.get(role, 0)
        if manifest_by_role and want > 0 and got != want:
            _add(
                b, "metrics", "flag", b.platform_id,
                f"nominal_complement.{role}s {want} != manifest {role} sum {got}",
            )


def _deck_area_by_deck(zones: list[dict[str, Any]]) -> dict[str, float]:
    deck_area: dict[str, float] = defaultdict(float)
    for z in zones:
        deck_area[z.get("deck", "?")] += float(z.get("floor_area_m2", 0.0))
    return deck_area


def _flag_deck_envelope_overruns(
    b: PlatformBundle, deck_area: dict[str, float], dims: dict[str, Any]
) -> None:
    envelope = float(dims.get("length_m", 0.0) or 0.0) * float(dims.get("beam_m", 0.0) or 0.0)
    for d, a in deck_area.items():
        if envelope > 0.0 and a > envelope * 1.25:
            _add(
                b, "metrics", "flag", d,
                f"deck zones sum {a:.0f} m2 > 1.25x hull envelope {envelope:.0f} m2",
            )


def _flag_capacity_metrics(
    b: PlatformBundle,
    crew: int,
    seats: int,
    berth_need: int,
    berth_cap: int,
    over: list[tuple[str, int, int]],
) -> None:
    if crew > 0 and seats > 0 and crew / seats > 8.0:
        _add(
            b, "metrics", "flag", b.platform_id,
            f"dining seats {seats} for crew {crew} ({crew / seats:.1f} crew/seat)",
        )
    if crew > 0 and berth_cap > 0 and berth_need > berth_cap * 1.5:
        _add(
            b, "metrics", "flag", b.platform_id,
            f"manifest assigns {berth_need} to berth zones capped at {berth_cap} (>{1.5}x)",
        )
    for zid, need, cap in over:
        if cap > 0 and need > cap * 1.5:
            _add(
                b, "metrics", "flag", zid,
                f"{need} assigned to berth capacity {cap} — exceeds any hot-bunk interpretation",
            )


def _ach_means_by_class(
    zones: list[dict[str, Any]], removal: dict[str, float]
) -> dict[str, float]:
    ach_by_class: dict[str, list[float]] = defaultdict(list)
    for z in zones:
        ach_by_class[_zone_signature(z)].append(removal.get(z["id"], 0.0))
    return {k: round(sum(v) / len(v), 2) for k, v in ach_by_class.items()}


def _nominal_crew(nc: dict[str, Any]) -> int:
    return int(nc.get("passengers", 0) or 0) + int(nc.get("crew", 0) or 0)


def _volume_totals(zones: list[dict[str, Any]]) -> tuple[float, float]:
    vol = sum(float(z.get("volume_m3", 0.0)) for z in zones)
    weather_vol = sum(
        float(z.get("volume_m3", 0.0)) for z in zones
        if _zone_signature(z) in {"weather_open", "open_other"}
    )
    return vol, weather_vol


def _sanitary_panel(zones: list[dict[str, Any]]) -> tuple[int, int]:
    sanitary = [z for z in zones if _zone_signature(z) == "sanitary"]
    san_cap = sum(int(z.get("max_occupancy", 0)) for z in sanitary)
    return len(sanitary), san_cap


def _note_scaled_hvac_duty(b: PlatformBundle) -> None:
    duty = float(b.airflow.get("hvac_duty", 1.0))
    if duty < 1.0:
        _add(
            b, "metrics", "note", b.platform_id,
            f"top-level hvac_duty={duty} halves/scales every group ACH vs declared",
        )


def _metrics_record(
    b: PlatformBundle,
    *,
    crew: int,
    zones: list[dict[str, Any]],
    vol: float,
    weather_vol: float,
    seats: int,
    seatings: float,
    sanitary: tuple[int, int],
    berth: tuple[int, int],
    over: list[tuple[str, int, int]],
    ach_means: dict[str, float],
    dims: dict[str, Any],
    evidence: Counter[str],
) -> dict[str, Any]:
    return {
        "crew": crew, "zones": len(zones), "volume_m3": round(vol),
        "m3_per_crew": round(vol / crew, 1) if crew else None,
        "weather_share": round(weather_vol / vol, 3) if vol > 0 else None,
        "dining_seats": seats, "meal_seatings": seatings,
        "crew_per_seat": round(crew / seats, 2) if seats else None,
        "sanitary_zones": sanitary[0],
        "sanitary_per_100": round(sanitary[1] / crew * 100, 1) if crew else None,
        "berth_need": berth[0], "berth_cap": berth[1],
        "berth_ratio": round(berth[0] / berth[1], 2) if berth[1] else None,
        "berth_over": [f"{z} {n}>{c}" for z, n, c in over],
        "ach_by_class": ach_means,
        "isolation_beds": b.spatial.get("isolation_unit_capacity"),
        "evidence": dict(evidence),
        "deck_dims": dims,
        "ungrouped": None,
    }


def _check_metrics(b: PlatformBundle, removal: dict[str, float]) -> dict[str, Any]:
    manifest = b.manifest or {}
    nc = (manifest.get("nominal_complement") or b.spatial.get("nominal_complement") or {})
    crew = _nominal_crew(nc)
    _check_complement_vs_manifest(b, nc, _manifest_role_totals(manifest))
    zones = b.zones
    vol, weather_vol = _volume_totals(zones)
    seats, seatings = _dining_seats(b)
    sanitary_n, san_cap = _sanitary_panel(zones)
    berth_need, berth_cap, over = _berth_audit(b)
    ach_means = _ach_means_by_class(zones, removal)
    dims = b.spatial.get("deck_dimensions") or {}
    _flag_deck_envelope_overruns(b, _deck_area_by_deck(zones), dims)
    _flag_capacity_metrics(b, crew, seats, berth_need, berth_cap, over)
    _note_scaled_hvac_duty(b)
    zmodes = (b.systems_notes or {}).get("zone_modes") or {}
    evidence = Counter(str(r.get("evidence", "none")) for r in zmodes.values())
    return _metrics_record(
        b,
        crew=crew,
        zones=zones,
        vol=vol,
        weather_vol=weather_vol,
        seats=seats,
        seatings=seatings,
        sanitary=(sanitary_n, san_cap),
        berth=(berth_need, berth_cap),
        over=over,
        ach_means=ach_means,
        dims=dims,
        evidence=evidence,
    )


def audit_platform(root: Path) -> PlatformBundle:
    b = load_platform(root)
    census = _check_topology(b)
    removal = _check_flow(b, census)
    _check_modes(b)
    metrics = _check_metrics(b, removal)
    metrics["ungrouped"] = census
    b.metrics = metrics
    return b


def _index_era_inferred_modes(
    bundles: list[PlatformBundle],
) -> dict[tuple[str, str], dict[str, set[str]]]:
    by_era_class: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set))
    for b in bundles:
        notes = b.systems_notes or {}
        zmodes = notes.get("zone_modes") or {}
        sig = {z["id"]: _zone_signature(z) for z in b.zones}
        for zid, rec in zmodes.items():
            if rec.get("evidence") == "sheet_read":
                continue
            klass = sig.get(zid)
            if klass is None:
                continue
            by_era_class[(b.era, klass)][str(rec.get("mode", "?"))].add(b.platform_id)
    return by_era_class


def _era_disagreement_kind(mode_map: dict[str, set[str]]) -> str:
    shared = set.intersection(*mode_map.values())
    all_plats = set.union(*mode_map.values())
    if shared == all_plats:
        return "within-platform only (a hull self-disagrees by zone)"
    if shared:
        return f"cross-platform; {sorted(shared)} also self-disagree"
    return "cross-platform"


def _era_contradictions(bundles: list[PlatformBundle]) -> list[Finding]:
    """Same-era platforms should infer the same mode for the same zone class
    wherever the sheet itself did not speak."""
    by_era_class = _index_era_inferred_modes(bundles)
    findings = []
    for (era, klass), mode_map in sorted(by_era_class.items()):
        if len(mode_map) <= 1:
            continue
        detail = "; ".join(f"{m}: {sorted(p)}" for m, p in sorted(mode_map.items()))
        kind = _era_disagreement_kind(mode_map)
        findings.append(Finding("era_consistency", "flag", f"{era}/{klass}",
                                f"era-inferred modes disagree ({kind}): {detail}"))
    return findings


def _metric_rows_by_era(
    bundles: list[PlatformBundle], metric: str
) -> dict[str, list[tuple[str, float]]]:
    by_era: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for b in bundles:
        v = b.metrics.get(metric)
        if isinstance(v, (int, float)):
            by_era[b.era].append((b.platform_id, float(v)))
    return by_era


def _iqr_outlier_findings(
    metric: str, era: str, rows: list[tuple[str, float]]
) -> list[Finding]:
    vals = sorted(v for _, v in rows)
    if len(vals) < 4:
        return []
    q1, q3 = vals[len(vals) // 4], vals[(3 * len(vals)) // 4]
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    findings: list[Finding] = []
    for pid, v in rows:
        if v < lo or v > hi:
            findings.append(Finding(
                "fleet_outlier", "flag", pid,
                f"{metric}={v} outside {era} band [{lo:.2f},{hi:.2f}]",
            ))
    return findings


def _fleet_outliers(bundles: list[PlatformBundle]) -> list[Finding]:
    """IQR-fence outliers per metric within era class (needs >=4 hulls)."""
    metrics = ["m3_per_crew", "crew_per_seat", "sanitary_per_100", "berth_ratio"]
    findings: list[Finding] = []
    for metric in metrics:
        for era, rows in sorted(_metric_rows_by_era(bundles, metric).items()):
            findings.extend(_iqr_outlier_findings(metric, era, rows))
    return findings


def _adjacency_type_coverage(bundles: list[PlatformBundle]) -> dict[str, Any]:
    """Declared adjacency types vs the bridge's passive-rate table — an
    unmapped type silently gets the 10 m3/h default."""
    used: dict[str, set[str]] = defaultdict(set)
    for b in bundles:
        for edge in b.airflow.get("adjacency", []):
            used[str(edge.get("type", "passageway"))].add(b.platform_id)
    rows = []
    for t, plats in sorted(used.items()):
        rows.append({
            "type": t,
            "rate_m3h": PASSIVE_RATES_M3H.get(t, PASSIVE_DEFAULT_M3H),
            "mapped": t in PASSIVE_RATES_M3H,
            "platforms": sorted(plats),
        })
    return {"rows": rows, "unmapped": [r["type"] for r in rows if not r["mapped"]]}


def _operability(b: PlatformBundle) -> dict[str, Any]:
    """Can this hull express the declared operating deviations (lockdown,
    collective protection, HVAC casualty)?"""
    notes = b.systems_notes or {}
    zone_modes = notes.get("zone_modes") or {}
    nat_vol = sum(
        float(z.get("volume_m3", 0.0))
        for z in b.zones
        if str(zone_modes.get(z["id"], {}).get("mode", "")) in {"nat_supply", "open_air"}
        or _zone_signature(z) in {"weather_open", "open_other"}
    )
    vol = sum(float(z.get("volume_m3", 0.0)) for z in b.zones)
    return {
        "isolation_beds": b.spatial.get("isolation_unit_capacity", 0) or 0,
        "non_citadel_vol_share": round(nat_vol / vol, 3) if vol > 0 else None,
    }


def _fmt(v: Any) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _fleet_panel(bundles: list[PlatformBundle]) -> str:
    cols = ["platform", "era", "zones", "crew", "m3/crew", "seats/crew",
            "sanitary/100", "berth need/cap", "flags"]
    lines = ["| " + " | ".join(cols) + " |",
             "|" + "---|" * len(cols)]
    for b in bundles:
        m = b.metrics
        n_flag = sum(1 for f in b.findings if f.severity == "flag")
        row = [b.platform_id, b.era, _fmt(m.get("zones")), _fmt(m.get("crew")),
               _fmt(m.get("m3_per_crew")), _fmt(m.get("crew_per_seat")),
               _fmt(m.get("sanitary_per_100")),
               f"{m.get('berth_need')}/{m.get('berth_cap')}", str(n_flag)]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _platform_summary_lines(b: PlatformBundle) -> list[str]:
    m = b.metrics
    ach = " ".join(f"{k}={v}" for k, v in sorted((m.get("ach_by_class") or {}).items()))
    lines = [
        f"- era={b.era} crew={_fmt(m.get('crew'))} zones={_fmt(m.get('zones'))} "
        f"vol={_fmt(m.get('volume_m3'))} isolation={_fmt(m.get('isolation_beds'))}",
        f"- removal ACH by class: {ach}",
    ]
    ev = m.get("evidence") or {}
    if ev:
        lines.append("- zone-mode evidence: " + ", ".join(f"{k}={v}" for k, v in sorted(ev.items())))
    census = m.get("ungrouped") or {}
    if census.get("ungrouped_occupied") or census.get("ungrouped_void"):
        lines.append(
            f"- ungrouped: occupied={census.get('ungrouped_occupied')} void={census.get('ungrouped_void')}"
        )
    comps = census.get("adjacency_components") or []
    if len(comps) > 1:
        lines.append(f"- adjacency components: {comps}")
    if m.get("berth_over"):
        lines.append(f"- berth over-assignment: {', '.join(m['berth_over'])}")
    return lines


def _filtered_findings(b: PlatformBundle, min_sev: str) -> list[Finding]:
    findings = [
        f for f in b.findings if SEVERITY_ORDER.get(f.severity, 9) <= SEVERITY_ORDER[min_sev]
    ]
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.check, f.scope))
    return findings


def _render_platform(b: PlatformBundle, min_sev: str) -> str:
    lines = [f"## {b.platform_id}\n"]
    lines.extend(_platform_summary_lines(b))
    findings = _filtered_findings(b, min_sev)
    if not findings:
        lines.append("- no findings at this severity")
    for f in findings:
        lines.append(f"- **{f.severity}** [{f.check}] `{f.scope}` — {f.message}")
    return "\n".join(lines)


def render_markdown(bundles: list[PlatformBundle], fleet_findings: list[Finding],
                    adjacency: dict[str, Any], min_severity: str = "note") -> str:
    out = ["# Hull model audit — fleet report", ""]
    out.extend([
        "Scope: declared design baseline (normal steaming). Operational "
        "deviations (lockdown, CPS, HVAC casualty) are intentionally "
        "out of scope for the defect flags; the operability fields "
        "record whether a hull can express them.",
        "",
        "## Fleet panel",
        "",
    ])
    out.append(_fleet_panel(bundles))
    out.extend([
        "",
        "## Fleet findings",
    ])
    for f in sorted(fleet_findings, key=lambda x: (SEVERITY_ORDER.get(x.severity, 9), x.check)):
        out.append(f"- **{f.severity}** [{f.check}] `{f.scope}` — {f.message}")
    out.extend([
        "",
        "## Adjacency type → passive rate coverage",
        "",
    ])
    out.append("| type | rate m3/h | platforms |")
    out.append("|---|---|---|")
    for r in adjacency["rows"]:
        mark = "" if r["mapped"] else " **(default 10)**"
        out.append(f"| {r['type']} | {r['rate_m3h']:g}{mark} | {len(r['platforms'])} |")
    out.append("")
    for b in bundles:
        out.append(_render_platform(b, min_severity))
        out.append("")
    return "\n".join(out)


def _collect_platform_dirs(names: list[str] | None, platforms_dir: Path) -> list[Path]:
    if names:
        return [platforms_dir / n for n in names]
    return sorted(p for p in platforms_dir.iterdir() if (p / "spatial_layout.json").is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--platforms", nargs="*", default=None,
                        help="platform ids under data/platforms/ (default: all)")
    parser.add_argument("--platforms-dir", default=str(PLATFORMS_DIR))
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--md-out", default=None)
    parser.add_argument("--min-severity", choices=["flag", "note"], default="note")
    args = parser.parse_args(argv)

    dirs = _collect_platform_dirs(args.platforms, Path(args.platforms_dir))
    bundles = [audit_platform(d) for d in dirs]
    fleet = _era_contradictions(bundles) + _fleet_outliers(bundles)
    adjacency = _adjacency_type_coverage(bundles)

    for b in bundles:
        b.metrics["operability"] = _operability(b)

    md = render_markdown(bundles, fleet, adjacency, args.min_severity)
    print(md)

    if args.json_out:
        out = Path(args.json_out)
        allowed = (str(out.parent.resolve()),)
        payload = {
            "platforms": {
                b.platform_id: {
                    "metrics": b.metrics,
                    "findings": [vars(f) for f in b.findings],
                }
                for b in bundles
            },
            "fleet_findings": [vars(f) for f in fleet],
            "adjacency_types": adjacency,
        }
        with validated_open(str(out), "w", allowed_roots=allowed, encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1, sort_keys=True)
    if args.md_out:
        out = Path(args.md_out)
        allowed = (str(out.parent.resolve()),)
        with validated_open(str(out), "w", allowed_roots=allowed, encoding="utf-8") as fh:
            fh.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
