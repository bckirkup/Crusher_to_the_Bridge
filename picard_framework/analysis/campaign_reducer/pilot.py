"""D6 pilot specimen selection + reuse audit (analysis-only, offline).

Derives the stratified pilot specimen set from a frozen inventory
artifact — the register's family rows plus the manifest page rows and
version rows the ``inventory`` op emits — deterministically, with a
self-explaining ``why`` per pick. Every specimen carries its pin
(``version_id`` when the versions pass listed the key, else ``etag``);
a registered family with no fresh observation is itself a specimen
class (``missing_witness``) — absence is a pilot outcome, never a
silent skip.

The reuse audit joins a parent ``_scan_rows`` doc's embedded source
keys against the raw sibling object keys the listing saw (acceptance:
exact mega raw sibling keys must join — a rev5 renamed key is absent
only when no row's embedded source key names it, not because its
key-shape drifted) and classifies reuse state as ``complete_summary``,
``partial_precision``, ``census_missingness`` or
``unknown_provenance``.

Nothing here touches the network; inputs are parsed inventory
artifacts.
"""
from __future__ import annotations

from typing import Iterable

SPECIMEN_DOC_SCHEMA = "crusher-reducer-pilot-specimens/v1"
PS01_PROGRAM_GROUP = "norovirus_provisioned_source_PS01"

# Schema-family classes from the D6 spec: one or two deterministic
# specimens each, pinned from the fresh listing. ``count`` specimens are
# drawn from distinct register records in stable prefix order.
_FAMILY_CLASSES: tuple[tuple[str, tuple[str, ...], int], ...] = (
    ("summary_archive", ("campaign_summary_zip",), 1),
    ("census", ("growth_census_zip",), 2),
    ("embedded_timeseries", ("observation_jsonl",), 1),
    ("legacy_nested", ("unknown_legacy",), 1),
    ("clinical_non_age", ("covid_screen_json", "flu_cell_json"), 1),
)

_META_SCHEMA_CANDIDATES = frozenset({"unknown_candidate"})

# Fields a ``_scan_rows`` row may embed the raw sibling key under, in
# preference order (first field populated wins).
_SCAN_KEY_FIELDS = (
    "source_key", "source_uri", "key", "object_key", "member_key",
    "raw_key", "path",
)


def _family_prefixes(frozen: dict) -> dict[str, dict]:
    """Map record prefix -> frozen family row (first row wins)."""
    out: dict[str, dict] = {}
    for row in frozen.get("families") or []:
        out.setdefault(row.get("prefix") or "", row)
    return out


def _ps01_vessels(register: list[dict]) -> dict[str, list[str]]:
    """vessel -> PS01 record prefixes that host it (register order)."""
    vessels: dict[str, list[str]] = {}
    for rec in register:
        if rec.get("program_group") != PS01_PROGRAM_GROUP:
            continue
        for vessel in rec.get("vessels") or []:
            vessels.setdefault(vessel, [])
            if rec["prefix"] not in vessels[vessel]:
                vessels[vessel].append(rec["prefix"])
    return vessels


def _objects_under(
    object_rows: Iterable[dict], prefix: str,
) -> list[dict]:
    """Listing rows under ``prefix`` that are payload objects (not the
    manifest/_scan_rows meta objects the audit consumes separately)."""
    return [
        r for r in object_rows
        if str(r.get("key") or "").startswith(prefix)
        and not r.get("is_manifest_key")
        and not r.get("is_scan_rows_key")
    ]


def _pick(candidates: list[dict], max_specimen_bytes: int | None) -> dict | None:
    """Deterministic pick: largest object under the cap, ties by key —
    size-extreme coverage with a stable, explainable rule."""
    pool = sorted(candidates, key=lambda r: (-int(r.get("bytes") or 0),
                                             r.get("key") or ""))
    if max_specimen_bytes is not None:
        pool = [r for r in pool
                if int(r.get("bytes") or 0) <= max_specimen_bytes]
    return pool[0] if pool else None


def _pin(row: dict, version_index: dict[str, str]) -> dict:
    """Strongest available pin for an object row."""
    key = row.get("key") or ""
    version_id = version_index.get(key)
    if version_id:
        return {
            "pin_kind": "version_id",
            "version_id": version_id,
            "etag": row.get("etag"),
        }
    if row.get("etag"):
        return {
            "pin_kind": "etag",
            "version_id": None,
            "etag": row.get("etag"),
        }
    return {"pin_kind": "unpinned", "version_id": None, "etag": None}


def _specimen(
    cls: str,
    fam: dict,
    row: dict,
    version_index: dict[str, str],
    candidate_count: int,
    why_extra: str,
) -> dict:
    key = row.get("key") or ""
    return {
        "class": cls,
        "family": fam.get("schema_family"),
        "record_id": fam.get("record_id"),
        "prefix": fam.get("prefix"),
        "key": key,
        "uri": key,
        "bytes": int(row.get("bytes") or 0),
        "storage_class": row.get("storage_class"),
        "source_id": key.split("/")[-1],
        "pin": _pin(row, version_index),
        "candidate_count": candidate_count,
        "why": [
            f"class {cls} matched record {fam.get('record_id')} "
            f"({fam.get('schema_family')})",
            why_extra,
            "largest payload object under prefix "
            f"({candidate_count} candidates, ties by key)",
        ],
    }


def _fresh_prefixes(
    families: dict[str, dict], schema_families: tuple[str, ...],
    *, exclude_program_group: str | None = None,
) -> list[dict]:
    rows = [
        fam for fam in families.values()
        if fam.get("schema_family") in schema_families
        and fam.get("fresh_observation") == "present"
        and (exclude_program_group is None
             or fam.get("program_group") != exclude_program_group)
    ]
    return sorted(rows, key=lambda f: (f.get("prefix") or "",
                                       f.get("record_id") or ""))


def _select_ps01(
    specimens: list[dict], uncovered: list[dict],
    frozen: dict, register: list[dict], object_rows: list[dict],
    version_index: dict[str, str], max_specimen_bytes: int | None,
) -> None:
    families = _family_prefixes(frozen)
    ps01_records = [
        r for r in register if r.get("program_group") == PS01_PROGRAM_GROUP
    ]
    vessels_by_prefix = {
        r["prefix"]: set(r.get("vessels") or ()) for r in ps01_records
    }
    for vessel, prefixes in sorted(_ps01_vessels(register).items()):
        cls = f"ps01_hull:{vessel}"
        picked = None
        picked_fam = None
        for prefix in prefixes:
            fam = families.get(prefix)
            if not fam or fam.get("fresh_observation") != "present":
                continue
            pool = _objects_under(object_rows, prefix)
            if len(vessels_by_prefix.get(prefix) or ()) > 1:
                # Shared hull prefix: only keys naming this vessel count.
                pool = [r for r in pool if vessel in (r.get("key") or "")]
            picked = _pick(pool, max_specimen_bytes)
            if picked is not None:
                picked_fam = fam
                break
        if picked is None:
            uncovered.append({
                "class": cls,
                "reason": "no fresh payload object carrying the vessel "
                          "token under PS01 prefixes",
                "prefixes_considered": prefixes,
            })
            continue
        specimens.append(_specimen(
            cls, picked_fam, picked, version_index,
            len(_objects_under(object_rows, picked_fam["prefix"])),
            f"vessel {vessel} resolved via PS01 prefixes {prefixes}",
        ))


def select_specimens(
    frozen: dict,
    register: list[dict],
    object_rows: list[dict],
    version_rows: list[dict],
    *,
    max_specimen_bytes: int | None = None,
) -> dict:
    """Derive the stratified specimen set from a frozen inventory doc.

    ``object_rows``/``version_rows`` are the parsed manifest page and
    version page rows the ``inventory`` op emits. Deterministic: the
    same artifacts always select the same pins.
    """
    families = _family_prefixes(frozen)
    version_index = {
        r["key"]: r["version_id"]
        for r in version_rows
        if r.get("key") and r.get("is_latest") and r.get("version_id")
    }
    specimens: list[dict] = []
    uncovered: list[dict] = []
    _select_ps01(specimens, uncovered, frozen, register, object_rows,
                 version_index, max_specimen_bytes)
    for cls, fams, count in _FAMILY_CLASSES:
        seen_records: set[str] = set()
        matched = 0
        for fam in _fresh_prefixes(
            families, fams, exclude_program_group=PS01_PROGRAM_GROUP,
        ):
            if matched >= count:
                break
            if fam.get("record_id") in seen_records:
                continue
            pool = _objects_under(object_rows, fam["prefix"])
            picked = _pick(pool, max_specimen_bytes)
            if picked is None:
                continue
            seen_records.add(fam["record_id"])
            specimens.append(_specimen(
                cls, fam, picked, version_index, len(pool),
                f"family class {cls} (distinct record "
                f"{matched + 1}/{count})",
            ))
            matched += 1
        if matched < count:
            uncovered.append({
                "class": cls,
                "reason": f"{matched}/{count} required distinct records "
                          "had fresh payload objects",
            })
    _select_object_level(
        specimens, uncovered, families, object_rows, version_index,
        max_specimen_bytes,
    )
    classes = [
        {
            "class": s["class"],
            "status": "covered",
            "specimen_key": s["key"],
        }
        for s in specimens
    ] + [
        {"class": u["class"], "status": "uncovered", "reason": u["reason"]}
        for u in uncovered
    ]
    return {
        "schema": SPECIMEN_DOC_SCHEMA,
        "request_id": frozen.get("request_id"),
        "source_bucket": frozen.get("source_bucket"),
        "observation_window": frozen.get("observation_window"),
        "specimens": specimens,
        "uncovered": uncovered,
        "classes": classes,
    }


def _select_object_level(
    specimens: list[dict], uncovered: list[dict],
    families: dict[str, dict], object_rows: list[dict],
    version_index: dict[str, str], max_specimen_bytes: int | None,
) -> None:
    """Classes keyed off the object rows themselves, not schema_family:
    an unsupported object (unknown_candidate under a present prefix) and
    a registered prefix with no fresh observation (missing witness)."""
    present = {
        p for p, f in families.items() if f.get("fresh_observation") == "present"
    }
    pool = [
        r for r in object_rows
        if r.get("schema_candidate") in _META_SCHEMA_CANDIDATES
        and any(str(r.get("key") or "").startswith(p) for p in present)
    ]
    picked = _pick(pool, max_specimen_bytes)
    if picked is not None:
        fam = next(
            families[p] for p in present
            if (picked.get("key") or "").startswith(p)
        )
        specimens.append(_specimen(
            "unsupported_witness", fam, picked, version_index, len(pool),
            "schema_candidate=unknown_candidate under a fresh prefix",
        ))
    else:
        uncovered.append({
            "class": "unsupported_witness",
            "reason": "no unknown_candidate object under a present prefix",
        })
    missing = sorted(
        (fam for fam in families.values()
         if fam.get("fresh_observation") in {"absent", "blocked"}),
        key=lambda f: (f.get("prefix") or "", f.get("record_id") or ""),
    )
    if missing:
        fam = missing[0]
        specimens.append({
            "class": "missing_witness",
            "family": fam.get("schema_family"),
            "record_id": fam.get("record_id"),
            "prefix": fam.get("prefix"),
            "key": None,
            "uri": None,
            "bytes": 0,
            "storage_class": None,
            "source_id": fam.get("record_id"),
            "pin": {"pin_kind": "unpinned", "version_id": None,
                    "etag": None},
            "candidate_count": len(missing),
            "why": [
                f"registered record {fam.get('record_id')} observed "
                f"{fam.get('fresh_observation')} in the fresh listing — "
                "absence is the pilot outcome",
            ],
            "fresh_observation": fam.get("fresh_observation"),
        })
    else:
        uncovered.append({
            "class": "missing_witness",
            "reason": "no registered record is fresh-absent or blocked",
        })


def _embedded_key(row: dict) -> str | None:
    """The embedded source key a ``_scan_rows`` row carries, if any."""
    for field in _SCAN_KEY_FIELDS:
        val = row.get(field)
        if isinstance(val, str) and val:
            if val.startswith("s3://"):
                val = val.split("/", 3)[-1] if val.count("/") >= 3 else val
            return val
    return None


def _norm_key(k: str) -> str:
    return k.lstrip("/")


def join_scan_rows(
    scan_rows: list[dict], sibling_keys: list[str],
) -> dict:
    """Join raw sibling keys to ``_scan_rows`` rows by embedded source key.

    Exact normalized-key match first, basename match second (a rev5
    rename changes directory shape, not the embedded source key — the
    join must not report a false absence). Returns matched pairs plus
    unmatched raw keys and rows that named no listed sibling (stale).
    """
    rows = scan_rows or []
    embedded = [(r, _embedded_key(r)) for r in rows]
    matched: list[dict] = []
    unmatched: list[str] = []
    used_rows: set[int] = set()
    for raw_key in sibling_keys:
        norm = _norm_key(raw_key)
        base = norm.rsplit("/", 1)[-1]
        hit = None
        hit_kind = None
        for i, (row, ek) in enumerate(embedded):
            if ek is None:
                continue
            ne = _norm_key(ek)
            if ne == norm:
                hit, hit_kind = i, "exact"
                break
            if hit is None and ne.rsplit("/", 1)[-1] == base:
                hit, hit_kind = i, "basename"
        if hit is not None:
            used_rows.add(hit)
            matched.append({
                "raw_key": raw_key,
                "embedded_key": embedded[hit][1],
                "match_kind": hit_kind,
            })
        else:
            unmatched.append(raw_key)
    stale = [
        embedded[i][1] or f"row-{i}"
        for i in range(len(rows)) if i not in used_rows
    ]
    return {
        "matched": matched,
        "unmatched_keys": unmatched,
        "stale_rows": stale,
        "rows_with_source_key": sum(1 for _, ek in embedded if ek),
        "rows_total": len(rows),
    }


def reuse_audit(
    scan_rows: list[dict] | None,
    sibling_keys: list[str],
    *,
    census_keys: list[str] | None = None,
) -> dict:
    """Classify what a parent ``_scan_rows`` doc lets the reducer reuse.

    ``scan_rows=None`` means the prefix listed no ``_scan_rows`` object —
    the source must be parsed (nothing to reuse, but not a defect).
    ``census_keys`` names the sibling keys a census member should join;
    an unmatched census key is a typed census missingness, not a silent
    gap.
    """
    census = census_keys or []
    if scan_rows is None:
        return {
            "classification": "no_scan_rows",
            "matched": [],
            "unmatched_keys": list(sibling_keys),
            "stale_rows": [],
            "why": ["no _scan_rows object listed under the prefix"],
        }
    join = join_scan_rows(scan_rows, sibling_keys)
    if join["rows_with_source_key"] == 0 and join["rows_total"] > 0:
        classification = "unknown_provenance"
    elif any(k in join["unmatched_keys"] for k in census):
        classification = "census_missingness"
    elif not join["unmatched_keys"] and not join["stale_rows"]:
        classification = "complete_summary"
    else:
        classification = "partial_precision"
    join["classification"] = classification
    join["why"] = [
        f"{len(join['matched'])}/{len(sibling_keys)} raw sibling keys "
        "joined an embedded source key",
        f"{join['rows_with_source_key']}/{join['rows_total']} rows "
        "carried a recognizable source key",
    ]
    return join
