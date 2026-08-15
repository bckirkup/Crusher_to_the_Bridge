"""Stage: author ContamW 3.4 starter PRJ for Path A side-chain (Target B).

Produces a ContamW-openable naval twin from synthesized Crusher JSON + optional
ShipDigest Contam/opening hints. Engineers refine ducts, leakage, and schedules
in ContamW afterward — those details are not on general-arrangement drawings.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from simulation_utils.paths import (
    prepare_output_directory,
    resolve_child_path,
    validated_open,
)
from tools.contam_hobbyist import load_hobbyist_pack, resolve_orifice_type
from tools.contam_prj_bridge import export_platform_to_prj
from tools.contamw34_prj import path_map_from_prj, simplify_contamw34
from tools.ship_blueprint_import.models import ContamHints, OpeningHint, ShipDigest

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

HANDOFF_MD = "CONTAM_HANDOFF.md"
OPENINGS_DRAFT = "openings_draft.json"
OVERRIDES_NAME = "hobbyist_overrides.json"


def _write_json(path: str, payload: Any, *, allowed_roots: tuple[str, ...]) -> None:
    prepare_output_directory(os.path.dirname(path) or ".", allowed_roots=allowed_roots)
    with validated_open(path, "w", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def _write_text(path: str, text: str, *, allowed_roots: tuple[str, ...]) -> None:
    prepare_output_directory(os.path.dirname(path) or ".", allowed_roots=allowed_roots)
    with validated_open(path, "w", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        fh.write(text)
        if not text.endswith("\n"):
            fh.write("\n")


def _load_json(path: str, *, allowed_roots: tuple[str, ...]) -> dict[str, Any]:
    with validated_open(path, "r", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def load_optional_digest(
    workdir: str | None,
    *,
    allowed_roots: tuple[str, ...],
) -> ShipDigest | None:
    if not workdir:
        return None
    path = os.path.join(workdir, "ship_digest.json")
    if not os.path.isfile(path):
        return None
    return ShipDigest.model_validate(_load_json(path, allowed_roots=allowed_roots))


def catalog_area_m2(adj_type: str, *, overrides: dict[str, Any] | None = None) -> float:
    pack = load_hobbyist_pack()
    ovr = overrides or {}
    key = resolve_orifice_type(adj_type, pack, ovr)
    types = pack["orifice_catalog"]["types"]
    meta = types.get(key) or types.get(pack["orifice_catalog"].get("default_type", "passageway"))
    return float(meta.get("area_m2", 2.0))


def build_openings_draft(
    airflow: dict[str, Any],
    digest: ShipDigest | None,
) -> list[dict[str, Any]]:
    """Merge adjacency + digest opening_hints into an engineer checklist."""
    hints: dict[tuple[str, str], OpeningHint] = {}
    if digest:
        for oh in digest.opening_hints:
            key = tuple(sorted((oh.from_, oh.to)))
            hints[key] = oh

    openings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for adj in airflow.get("adjacency", []):
        a, b = str(adj["from"]), str(adj["to"])
        key = tuple(sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        adj_type = str(adj.get("type") or "passageway")
        hint = hints.get(key)
        area = hint.area_m2 if hint and hint.area_m2 else catalog_area_m2(adj_type)
        openings.append(
            {
                "from": a,
                "to": b,
                "type": hint.type if hint else adj_type,
                "area_m2": round(float(area), 4),
                "area_source": (
                    "digest_opening_hint"
                    if hint and hint.area_m2
                    else "hobbyist_orifice_catalog"
                ),
                "schedule": hint.schedule if hint else None,
                "status": hint.status if hint else "draft",
                "notes": (hint.notes if hint else "")
                or "Starter opening from GA adjacency — confirm clear area in ContamW",
                "contam_element": "plr_orfc",
            }
        )

    # Digest-only openings not yet in adjacency
    if digest:
        for oh in digest.opening_hints:
            key = tuple(sorted((oh.from_, oh.to)))
            if key in seen:
                continue
            seen.add(key)
            area = oh.area_m2 or catalog_area_m2(oh.type)
            openings.append(
                {
                    "from": oh.from_,
                    "to": oh.to,
                    "type": oh.type,
                    "area_m2": round(float(area), 4),
                    "area_source": "digest_opening_hint",
                    "schedule": oh.schedule,
                    "status": oh.status,
                    "notes": oh.notes
                    or "Opening from digest; not yet mirrored in adjacency",
                    "contam_element": "plr_orfc",
                }
            )
    return openings


def apply_openings_to_airflow(
    airflow: dict[str, Any],
    openings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Ensure adjacency entries exist for every opening (type from checklist)."""
    out = dict(airflow)
    adj = list(out.get("adjacency") or [])
    index = {tuple(sorted((e["from"], e["to"]))): i for i, e in enumerate(adj)}
    for op in openings:
        key = tuple(sorted((op["from"], op["to"])))
        entry = {
            "from": op["from"],
            "to": op["to"],
            "type": op.get("type") or "passageway",
        }
        if key in index:
            adj[index[key]] = entry
        else:
            adj.append(entry)
            index[key] = len(adj) - 1
    out["adjacency"] = adj
    return out


def ensure_zone_geometry(spatial: dict[str, Any], digest: ShipDigest | None) -> dict[str, Any]:
    """Fill Contam geometry fields (floor area, height, elevation) when missing."""
    out = dict(spatial)
    zones = []
    ceiling_default = float(digest.ceiling_height_m) if digest else 2.8
    deck_elev: dict[str, float] = {}
    if digest:
        for i, deck in enumerate(digest.decks):
            if deck.elevation_m is not None:
                deck_elev[deck.id] = float(deck.elevation_m)
            else:
                deck_elev[deck.id] = float(i) * ceiling_default
        for z in digest.zones:
            if z.elevation_m is not None:
                deck_elev.setdefault(z.deck, float(z.elevation_m))

    # Stable stack for decks not in digest
    seen_decks: list[str] = []
    for z in out.get("zones", []):
        deck = str(z.get("deck") or "main")
        if deck not in seen_decks:
            seen_decks.append(deck)
    for i, deck in enumerate(seen_decks):
        deck_elev.setdefault(deck, float(i) * ceiling_default)

    zone_meta = digest.zone_by_id() if digest else {}
    for z in out.get("zones", []):
        zz = dict(z)
        zid = zz["id"]
        ceiling = float(zz.get("ceiling_height_m") or ceiling_default)
        zz["ceiling_height_m"] = ceiling
        if "floor_area_m2" not in zz or not zz["floor_area_m2"]:
            meta = zone_meta.get(zid)
            if meta and meta.floor_area_m2_est:
                zz["floor_area_m2"] = float(meta.floor_area_m2_est)
            else:
                zz["floor_area_m2"] = round(float(zz["volume_m3"]) / ceiling, 2)
        deck = str(zz.get("deck") or "main")
        if "elevation_m" not in zz or zz.get("elevation_m") is None:
            meta = zone_meta.get(zid)
            if meta and meta.elevation_m is not None:
                zz["elevation_m"] = float(meta.elevation_m)
            else:
                zz["elevation_m"] = float(deck_elev.get(deck, 0.0))
        zones.append(zz)
    out["zones"] = zones
    return out


def build_naval_hobbyist_overrides(
    *,
    platform_id: str,
    spatial: dict[str, Any],
    airflow: dict[str, Any],
    digest: ShipDigest | None,
) -> dict[str, Any]:
    hints = digest.contam_hints if digest else ContamHints()
    orifice_map = {
        "ladder_well": "ladder_well",
        "ladder": "ladder",
        "passageway": "passageway",
        "service_hatch": "hatch",
        "hatch": "hatch",
        "doorway": "doorway",
        "stairwell": "stairwell",
    }
    orifice_map.update(hints.orifice_type_map)

    deck_temps = dict(hints.deck_temp_offset_K)
    if not deck_temps:
        # Mild engineering heat bias for decks containing Engineering zones
        eng_decks = {
            z.get("deck")
            for z in spatial.get("zones", [])
            if z.get("type") == "Engineering"
        }
        for z in spatial.get("zones", []):
            deck = z.get("deck")
            if deck in eng_decks:
                deck_temps.setdefault(str(deck), 4.0)

    annotations = {
        z["id"]: (z.get("description") or z["id"])[:48]
        for z in spatial.get("zones", [])
        if z.get("description")
    }

    wall_az = {}
    length = float((spatial.get("deck_dimensions") or {}).get("length_m") or 100.0)
    for z in spatial.get("zones", []):
        x = float((z.get("display") or {}).get("x") or length / 2)
        # Bow=0°, stern=180°, port/stbd rough
        if x > 0.7 * length:
            wall_az[z["id"]] = 0.0
        elif x < 0.3 * length:
            wall_az[z["id"]] = 180.0
        else:
            y = float((z.get("display") or {}).get("y") or 0)
            beam = float((spatial.get("deck_dimensions") or {}).get("beam_m") or 12.0)
            wall_az[z["id"]] = 90.0 if y >= beam / 2 else 270.0

    hvac_filter: dict[str, str] = {}
    for hz in airflow.get("hvac_zones", []):
        hid = hz["id"]
        rooms = hz.get("rooms") or []
        # Medical / engineering AHUs get HEPA starter suggestion
        room_types = {
            z["id"]: z.get("type")
            for z in spatial.get("zones", [])
            if z["id"] in rooms
        }
        if any(t in ("Medical", "Engineering") for t in room_types.values()):
            hvac_filter[hid] = "HEPA"

    if digest:
        for hh in digest.hvac_hints:
            if hh.filter_preset:
                hvac_filter[hh.id] = hh.filter_preset

    duct_ids = list(hints.duct_hvac_ids)
    if hints.skip_duct_spines:
        duct_ids = []  # empty → exporter should skip; also set flag below

    overrides: dict[str, Any] = {
        "description": (
            f"Naval GA Contam starter for {platform_id} "
            "(Target B — openings/AHS drafted; ducts are engineer handwork)"
        ),
        "orifice_type_map": orifice_map,
        "wind_profile": hints.wind_profile,
        "filter_preset": hints.filter_preset,
        "hvac_filter": hvac_filter,
        "deck_temp_offset_K": deck_temps,
        "zone_annotations": annotations,
        "wall_azimuth_deg": wall_az,
        "night_setback": True,
        "duct_hvac_ids": duct_ids,
        "skip_duct_spines": bool(hints.skip_duct_spines),
        "naval_ga_import": True,
        "handoff_notes": list(hints.handoff_notes)
        + [
            "Confirm orifice clear areas against watertight door / hatch schedules",
            "Author real duct networks in ContamW (fiction Darcy spines omitted by default)",
            "Replace starter MERV/HEPA filters with ship NBC / HVAC design data",
            "Calibrate AHS Fahs / OAFrac against design ACH and TAB where available",
        ],
    }
    return overrides


def write_handoff_markdown(
    *,
    platform_id: str,
    openings_count: int,
    hvac_count: int,
    skip_ducts: bool,
) -> str:
    ducts = (
        "Fiction Darcy duct spines were **omitted** (naval GA default). "
        "Author real ducts / terminals in ContamW from HVAC drawings."
        if skip_ducts
        else "Placeholder Darcy duct spines were emitted for listed AHUs — replace with design ducts."
    )
    return f"""# ContamW handoff — `{platform_id}`

This ContamW **3.4** project is a **Target B starter** from naval general
arrangements via `tools.ship_blueprint_import.author_contam`.

It is meant to **run ContamX Path A** in Crusher-to-the-Bridge and to be
**opened in ContamW** so HVAC engineers can finish work that is **not on the
GA drawings**.

## Already drafted (from GA import)

- Contam **levels / zones** with volume, floor area, ceiling height, elevation
- SketchPad-ish display coordinates from zone overlays
- **{openings_count}** typed `plr_orfc` openings (doors / hatches / ladders) —
  see `openings_draft.json`
- **{hvac_count}** starter **AHS** branches from HVAC hints (ACH → Fahs)
- Cross-zone ladder/fan links from the synthesized airflow graph
- `path_map.json` for ContamX ↔ Crusher alignment

## Engineer handwork (Target C — not on GAs)

1. Confirm / edit opening areas and schedules (`openings_draft.json` checklist)
2. {ducts}
3. Fan curves, damper schedules, measured leakage, NBC filtration as Contam elements
4. Weather / wind as required for the analysis window
5. Re-export or keep editing this `.prj`; Path B simplify refreshes Crusher JSON if needed

## CtB Path A

Place / keep files under `data/platforms/{platform_id}/contam/`:

- `platform.prj`
- `path_map.json`
- `hobbyist_overrides.json` (starter only; ContamW edits are authoritative)

Set `hvac.transport_engine: contamx` (or `auto`) with `prj_path` pointing here.

## Commands

```bash
python3 -m tools.ship_blueprint_import author_contam \\
  --platform-dir data/platforms/{platform_id}

# Optional offline PRJ parse gate (no ContamX binary required):
python3 -m tools.ship_blueprint_import validate \\
  --platform-dir data/platforms/{platform_id} --contam-gate
```
"""


def validate_prj_offline(prj_path: str, *, allowed_roots: tuple[str, ...]) -> dict[str, Any]:
    """Parse PRJ + build path_map; optionally simplify — no ContamX binary."""
    with validated_open(prj_path, "r", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        text = fh.read()
    path_map = path_map_from_prj(text)
    warn: list[str] = []
    spatial, airflow = simplify_contamw34(text, warnings_out=warn)
    return {
        "ok": bool(spatial.get("zones")) and bool(path_map),
        "zone_count": len(spatial.get("zones") or []),
        "path_map_entries": len(path_map),
        "hvac_zones": len((airflow or {}).get("hvac_zones") or []),
        "simplify_warnings": warn[:20],
    }


def try_contamx_smoke(platform_id: str) -> dict[str, Any] | None:
    """Best-effort ContamX availability probe; None if binary/missing."""
    # ContamX is optional local install under third_party/contamx
    cand = os.path.join(_REPO_ROOT, "third_party", "contamx")
    if not os.path.isdir(cand):
        return None
    bin_names = [n for n in os.listdir(cand) if "contam" in n.lower()]
    if not bin_names:
        return None
    return {
        "available": True,
        "note": (
            f"ContamX install detected under third_party/contamx ({bin_names[0]}). "
            f"Run tools/contam_flow_compare.py --platform {platform_id} after SIM generation."
        ),
    }


def author_contam(
    *,
    platform_dir: str,
    workdir: str | None = None,
    allowed_roots: tuple[str, ...],
    hobbyist: bool = True,
    run_offline_gate: bool = True,
) -> dict[str, Any]:
    """Write contam/platform.prj + path_map + openings checklist + handoff doc."""
    platform_dir = os.path.realpath(platform_dir)
    spatial_path = resolve_child_path(platform_dir, "spatial_layout.json")
    airflow_path = resolve_child_path(platform_dir, "air_flow_paths.json")
    spatial = _load_json(spatial_path, allowed_roots=allowed_roots)
    airflow = _load_json(airflow_path, allowed_roots=allowed_roots)
    digest = load_optional_digest(workdir, allowed_roots=allowed_roots)
    platform_id = str(spatial.get("platform") or os.path.basename(platform_dir))

    spatial = ensure_zone_geometry(spatial, digest)
    openings = build_openings_draft(airflow, digest)
    airflow = apply_openings_to_airflow(airflow, openings)

    # Persist geometry / adjacency upgrades back to platform JSON
    _write_json(spatial_path, spatial, allowed_roots=allowed_roots)
    _write_json(airflow_path, airflow, allowed_roots=allowed_roots)

    if digest and digest.contam_hints.oa_fraction is not None:
        airflow["oa_fraction"] = float(digest.contam_hints.oa_fraction)
        airflow["hvac_duty"] = float(digest.contam_hints.hvac_duty)
        _write_json(airflow_path, airflow, allowed_roots=allowed_roots)

    contam_dir = os.path.join(platform_dir, "contam")
    prepare_output_directory(contam_dir, allowed_roots=allowed_roots)

    overrides = build_naval_hobbyist_overrides(
        platform_id=platform_id,
        spatial=spatial,
        airflow=airflow,
        digest=digest,
    )
    _write_json(
        resolve_child_path(contam_dir, OVERRIDES_NAME),
        overrides,
        allowed_roots=allowed_roots,
    )

    openings_payload = {
        "schema_version": "1.0",
        "platform_id": platform_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "description": (
            "Draft Contam orifice checklist from naval GA import. "
            "Engineers confirm areas/schedules in ContamW; as-built ducts are out of scope here."
        ),
        "openings": openings,
        "handwork_remaining": [
            "duct_networks",
            "fan_curves",
            "measured_leakage",
            "nbc_filtration_elements",
            "weather_wind_as_required",
        ],
    }
    _write_json(
        resolve_child_path(contam_dir, OPENINGS_DRAFT),
        openings_payload,
        allowed_roots=allowed_roots,
    )

    handoff = write_handoff_markdown(
        platform_id=platform_id,
        openings_count=len(openings),
        hvac_count=len(airflow.get("hvac_zones") or []),
        skip_ducts=bool(overrides.get("skip_duct_spines", True)),
    )
    _write_text(
        resolve_child_path(contam_dir, HANDOFF_MD),
        handoff,
        allowed_roots=allowed_roots,
    )

    prj_path = resolve_child_path(contam_dir, "platform.prj")
    export_platform_to_prj(
        platform_dir,
        prj_path,
        write_path_map=True,
        hobbyist=hobbyist,
    )

    gate = None
    if run_offline_gate:
        gate = validate_prj_offline(prj_path, allowed_roots=allowed_roots)

    contamx = try_contamx_smoke(platform_id)

    provenance = {
        "schema_version": "1.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "platform_id": platform_id,
        "target": "B_contam_starter",
        "hobbyist": hobbyist,
        "openings_count": len(openings),
        "skip_duct_spines": bool(overrides.get("skip_duct_spines", True)),
        "offline_gate": gate,
        "contamx": contamx,
        "workdir": workdir,
    }
    _write_json(
        resolve_child_path(contam_dir, "author_contam_provenance.json"),
        provenance,
        allowed_roots=allowed_roots,
    )

    return {
        "platform_id": platform_id,
        "contam_dir": contam_dir,
        "prj_path": prj_path,
        "path_map": os.path.join(contam_dir, "path_map.json"),
        "openings_draft": os.path.join(contam_dir, OPENINGS_DRAFT),
        "handoff": os.path.join(contam_dir, HANDOFF_MD),
        "openings_count": len(openings),
        "offline_gate": gate,
        "contamx": contamx,
    }
