"""Committed-prj zone-name normalization (CONTAM-PRJNAME-01).

Committed GA prjs mangle zone names to the CONTAMW 15-char field
(underscores stripped, colliding names deduplicated as ``<base>_<N>``);
a handful of zones were also renamed in JSON after the prj was written.
``prj_zone_aliases`` resolves mangled names back to canonical ids so
``path_map_from_prj`` no longer silently aliases or drops endpoints.
"""

from __future__ import annotations

import json
import os

import pytest

from simulation_utils.paths import REPO_ROOT, validated_open
from tools.contam_hobbyist import load_hobbyist_overrides
from tools.contamw34_prj import (
    _is_phantom_zone,
    _section_blocks,
    normalize_prj_zone_name,
    path_map_from_prj,
    prj_zone_aliases,
)

PLATFORMS = os.path.join(REPO_ROOT, "data", "platforms")
PRJ_REL = os.path.join("contam", "platform.prj")


def _real_prj_names(text: str) -> list[str]:
    names = []
    for ln in dict(_section_blocks(text)).get("zones", []):
        if ln.strip().startswith("!"):
            continue
        toks = ln.split()
        if len(toks) >= 11 and toks[0].isdigit() and not _is_phantom_zone(
            int(toks[1]), toks[10]
        ):
            names.append(toks[10])
    return names


def _read(path: str) -> str:
    with validated_open(path, "r", allowed_roots=(REPO_ROOT,),
                        encoding="utf-8") as fh:
        return fh.read()


def _hull(pid: str) -> tuple[str, list[str], dict]:
    pdir = os.path.join(PLATFORMS, pid)
    text = _read(os.path.join(pdir, PRJ_REL))
    spatial = json.loads(_read(os.path.join(pdir, "spatial_layout.json")))
    canon = [z["id"] for z in spatial.get("zones", [])]
    return text, canon, load_hobbyist_overrides(pdir)


class TestNormalize:
    def test_strip_and_truncate(self):
        assert normalize_prj_zone_name("Aux_Machinery_Room") == "AuxMachineryRoo"

    def test_short_name_unchanged(self):
        assert normalize_prj_zone_name("Bridge") == "Bridge"


class TestPrjZoneAliases:
    def test_exact_match(self):
        out = prj_zone_aliases(["Bridge"], ["Bridge", "Galley"])
        assert out == {"Bridge": "Bridge"}

    def test_normalized_match(self):
        out = prj_zone_aliases(
            ["AuxMachineryRoo"], ["Aux_Machinery_Room", "Bridge"],
        )
        assert out["AuxMachineryRoo"] == "Aux_Machinery_Room"

    def test_norm_collision_claims_declaration_order(self):
        # ContamW dedup: both zones normalize to MDOfficersCabin; the first
        # claims the first canonical candidate, the _N name falls through
        # to positional (indices must agree for positional to fire).
        canon = ["MD_Officers_Cabins_Port", "MD_Officers_Cabins_Stb"]
        out = prj_zone_aliases(
            ["MDOfficersCabin", "MDOfficersCab_1"], canon,
        )
        assert out["MDOfficersCabin"] == "MD_Officers_Cabins_Port"
        assert out["MDOfficersCab_1"] == "MD_Officers_Cabins_Stb"

    def test_positional_resolves_true_rename(self):
        # Post-prj rename unrecoverable by normalization: positional
        # alignment fills it when counts and every resolved index agree.
        canon = ["Admirals_Quarters", "Bridge"]
        out = prj_zone_aliases(["Admirals_Qtrs", "Bridge"], canon)
        assert out["Admirals_Qtrs"] == "Admirals_Quarters"

    def test_positional_refused_on_count_mismatch(self):
        # An inserted json-only zone breaks index alignment: the renamed
        # prj name must stay unresolved rather than guess.
        canon = ["Inserted_Sup", "Admirals_Quarters", "Bridge"]
        out = prj_zone_aliases(
            ["Admirals_Qtrs", "Bridge"], canon,
            declared_aliases={"Admirals_Qtrs": "Admirals_Quarters"},
        )
        assert out["Admirals_Qtrs"] == "Admirals_Quarters"
        out = prj_zone_aliases(["Admirals_Qtrs", "Bridge"], canon)
        assert out["Admirals_Qtrs"] == "Admirals_Qtrs"

    def test_positional_refused_when_indices_inconsistent(self):
        # Norm resolves GalleyX to index 1 while it sits at prj index 0 —
        # order is broken, so positional must not guess the residue.
        canon = ["Bridge", "GalleyX"]
        out = prj_zone_aliases(["GalleyX", "Renamed"], canon)
        assert out["GalleyX"] == "GalleyX"
        assert out["Renamed"] == "Renamed"

    def test_declared_alias_beats_positional(self):
        canon = ["Galley_Complex_Up", "Bridge"]
        out = prj_zone_aliases(
            ["Galley_Cx_Up", "Bridge"], canon,
            declared_aliases={"Galley_Cx_Up": "Galley_Complex_Up"},
        )
        assert out["Galley_Cx_Up"] == "Galley_Complex_Up"

    def test_declared_alias_target_must_exist(self):
        out = prj_zone_aliases(
            ["OldName", "Bridge"], ["Galley", "Bridge"],
            declared_aliases={"OldName": "No_Such_Zone"},
        )
        assert out["OldName"] != "No_Such_Zone"

    def test_unresolved_maps_to_self(self):
        # Count mismatch disables positional, so nothing can claim it.
        out = prj_zone_aliases(["Phantom_X"], ["Bridge", "Galley"])
        assert out["Phantom_X"] == "Phantom_X"


class TestPathMapNormalization:
    def test_raw_parse_unchanged_without_zone_ids(self):
        # Backward compat: no canonical ids → raw ContamW names, as before.
        text, _canon, _ov = _hull("erie_pg50")
        names = {e["from_zone"] for e in path_map_from_prj(text)}
        assert "AuxMachineryRoo" in names  # mangled name stays raw

    def test_committed_hull_endpoints_resolve(self):
        text, canon, ov = _hull("erie_pg50")
        canon_set = set(canon)
        entries = path_map_from_prj(
            text, canon, declared_aliases=ov.get("zone_aliases"),
        )
        bad = {
            e[k] for e in entries for k in ("from_zone", "to_zone")
            if e[k] != "ambient" and e[k] not in canon_set
            and not _is_phantom_zone(0, e[k])
        }
        assert bad == set()

    def test_normalization_only_increases_coverage(self):
        # Graded sensitivity: supplying canonical ids strictly raises the
        # number of canonical endpoints on a hull with mangled names.
        text, canon, ov = _hull("erie_pg50")
        canon_set = set(canon)
        raw = path_map_from_prj(text)
        res = path_map_from_prj(
            text, canon, declared_aliases=ov.get("zone_aliases"),
        )
        assert len(res) == len(raw)  # renaming never adds/drops entries

        def canon_count(entries):
            return sum(
                1 for e in entries
                if e["from_zone"] in canon_set or e["to_zone"] in canon_set
            )

        assert canon_count(res) > canon_count(raw)


class TestFleetInvariant:
    @pytest.mark.parametrize("pid", sorted(
        d for d in os.listdir(PLATFORMS)
        if os.path.exists(os.path.join(PLATFORMS, d, PRJ_REL))
        and os.path.exists(os.path.join(PLATFORMS, d, "spatial_layout.json"))
    ))
    def test_all_real_prj_zones_resolve(self, pid):
        text, canon, ov = _hull(pid)
        canon_set = set(canon)
        aliases = prj_zone_aliases(
            _real_prj_names(text), canon,
            declared_aliases=ov.get("zone_aliases"),
        )
        unresolved = [
            n for n, resolved in aliases.items()
            if resolved == n and n not in canon_set
        ]
        assert unresolved == [], f"{pid}: {unresolved}"
