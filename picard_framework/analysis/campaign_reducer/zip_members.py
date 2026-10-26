"""Bounded ranged ZIP central-directory/member access (ticket D1).

This extends the ranged approach proven in
``tools/noro_diag/outbreak_anchor_readout.py::_s3_member_blob`` and
``onset_curve_readout.py::_census_prefix`` (EOCD → central directory →
local header → member blob) with the D1 hardening the spec requires:

- EOCD located in a tail window covering the maximum 65,535-byte ZIP
  comment plus the ZIP64 locator/record that precede it; the found record
  must be self-consistent (comment reaches EOF), else earlier candidates
  are tried — a ``PK\\x05\\x06`` inside a comment cannot masquerade.
- ZIP64 EOCD locator/record resolve 0xFFFF/0xFFFFFFFF sentinel fields, and
  the 0x0001 extra field resolves per-entry sentinel sizes/offsets.
- Stored (0) and deflate (8) members only; encrypted or other methods are
  typed ``unsupported_compression`` rejections.
- Member data is CRC-checked and decoded-size checked against the central
  directory; compressed, decoded, member-count and CD sizes are all bound
  to the shared :class:`~.pinned_reader.ReadBudget`, and truncated member
  payloads are ``corrupt_archive``, never short reads.
- Duplicate member names are surfaced, never silently collapsed to the
  first entry (``duplicate_members`` state).
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field

from .pinned_reader import (
    STATE_AVAILABLE,
    STATE_CORRUPT,
    STATE_CRC_FAILURE,
    STATE_DECODE_FAILURE,
    STATE_DUPLICATE_MEMBER,
    STATE_MISSING_MEMBER,
    STATE_RESOURCE_LIMIT,
    STATE_UNSUPPORTED_COMPRESSION,
    PinnedObject,
    ReadBudget,
    ReadOutcome,
    SourceReadError,
)

_EOCD_SIG = b"PK\x05\x06"
_EOCD_LEN = 22
_ZIP64_LOCATOR_SIG = b"PK\x06\x07"
_ZIP64_LOCATOR_LEN = 20
_ZIP64_EOCD_SIG = b"PK\x06\x06"
_ZIP64_EOCD_LEN = 56
_CD_SIG = b"PK\x01\x02"
_CD_LEN = 46
_LH_SIG = b"PK\x03\x04"
_LH_LEN = 30

# Tail window must cover EOCD + max comment + ZIP64 locator + ZIP64 record.
TAIL_WINDOW = _EOCD_LEN + 0xFFFF + _ZIP64_LOCATOR_LEN + _ZIP64_EOCD_LEN

_U16_SENTINEL = 0xFFFF
_U32_SENTINEL = 0xFFFFFFFF

_METHODS = {0: "stored", 8: "deflate"}

_GENERAL_PURPOSE_ENCRYPTED = 0x0001
_GENERAL_PURPOSE_DATA_DESCRIPTOR = 0x0008


@dataclass(frozen=True)
class CdEntry:
    """One central-directory member record."""

    name: str
    method: int
    flags: int
    crc32: int
    comp_size: int
    uncomp_size: int
    lh_off: int
    comment: str = ""

    @property
    def compression(self) -> str:
        return _METHODS.get(self.method, f"method_{self.method}")


@dataclass
class ZipIndex:
    """Parsed central directory of a pinned archive object."""

    entries: list[CdEntry]
    duplicates: dict[str, list[CdEntry]] = field(default_factory=dict)
    zip64: bool = False
    comment: str = ""

    def member_names(self) -> list[str]:
        return [entry.name for entry in self.entries]

    def members_named(self, name: str) -> list[CdEntry]:
        return [entry for entry in self.entries if entry.name == name]

    def run_groups(self) -> dict[str, list[CdEntry]]:
        """Group members into fused/nested run folders.

        Members under a directory prefix (``run_123/summary.json``) group by
        that prefix; top-level members group under ``""`` (a per-run archive
        is one implicit run folder).
        """
        groups: dict[str, list[CdEntry]] = {}
        for entry in self.entries:
            group = entry.name.rsplit("/", 1)[0] if "/" in entry.name else ""
            groups.setdefault(group, []).append(entry)
        return groups


def _fail(state: str, detail: str) -> SourceReadError:
    return SourceReadError(state, detail)


def _find_eocd(tail: bytes) -> int:
    """Offset of a self-consistent EOCD in the tail window, or raise."""
    pos = len(tail)
    while True:
        pos = tail.rfind(_EOCD_SIG, 0, pos)
        if pos < 0:
            raise _fail(STATE_CORRUPT, "EOCD signature not found in tail window")
        if pos + _EOCD_LEN > len(tail):
            continue
        comment_len = struct.unpack_from("<H", tail, pos + 20)[0]
        # A real EOCD's comment runs exactly to EOF; a signature inside a
        # comment fails this check and the earlier-candidate scan continues
        # (the slice end ``pos`` excludes the just-tested candidate).
        if pos + _EOCD_LEN + comment_len == len(tail):
            return pos


def _zip64_location(tail: bytes, eocd_tail_off: int, size: int) -> int:
    """Absolute offset of the ZIP64 EOCD record via its locator.

    ``eocd_tail_off`` is the EOCD's offset within ``tail``; the locator is
    the 20 bytes immediately before it.
    """
    loc_off = eocd_tail_off - _ZIP64_LOCATOR_LEN
    if loc_off < 0 or tail[loc_off : loc_off + 4] != _ZIP64_LOCATOR_SIG:
        raise _fail(STATE_CORRUPT, "ZIP64 sentinel fields but no EOCD locator")
    eocd64_off = struct.unpack_from("<Q", tail, loc_off + 8)[0]
    if eocd64_off + _ZIP64_EOCD_LEN > size:
        raise _fail(STATE_CORRUPT, "ZIP64 EOCD record outside object")
    return eocd64_off


def _parse_eocd(tail: bytes, size: int) -> dict:
    """EOCD fields, with the ZIP64 chain resolved through sentinels."""
    eocd_off = _find_eocd(tail)
    n_disk, n_total, cd_size, cd_off = struct.unpack_from("<HHII", tail, eocd_off + 8)
    comment_len = struct.unpack_from("<H", tail, eocd_off + 20)[0]
    needs64 = _U16_SENTINEL in (n_disk, n_total) or _U32_SENTINEL in (
        cd_size,
        cd_off,
    )
    out = {
        "cd_off": cd_off,
        "cd_size": cd_size,
        "count": n_total,
        "zip64": needs64,
        "comment": tail[eocd_off + _EOCD_LEN :].decode("utf-8", "replace"),
        "comment_len": comment_len,
    }
    if needs64:
        out["zip64_eocd_off"] = _zip64_location(tail, eocd_off, size)
    return out


def _read_zip64(obj: PinnedObject, eocd64_off: int) -> tuple[int, int, int]:
    blob = obj.read_range(eocd64_off, eocd64_off + _ZIP64_EOCD_LEN - 1)
    if blob[:4] != _ZIP64_EOCD_SIG:
        raise _fail(STATE_CORRUPT, "ZIP64 EOCD signature mismatch")
    # Record layout: sig(4) size(8) ver(2) ver(2) disk(4) cd_disk(4)
    # n_disk(8) n_total(8)@32 cd_size(8)@40 cd_off(8)@48.
    n_total, cd_size, cd_off = struct.unpack_from("<QQQ", blob, 32)
    return cd_off, cd_size, n_total


def _zip64_extra(entry: CdEntry, extra: bytes) -> CdEntry:
    """Resolve 0x0001 extra-field sentinels in CD-order."""
    pos = 0
    while pos + 4 <= len(extra):
        tag, length = struct.unpack_from("<HH", extra, pos)
        if tag == 0x0001:
            vals: list[int] = []
            off = pos + 4
            for _ in range(3):
                vals.append(struct.unpack_from("<Q", extra, off)[0])
                off += 8
            vals.append(struct.unpack_from("<I", extra, off)[0])
            return CdEntry(
                name=entry.name,
                method=entry.method,
                flags=entry.flags,
                crc32=entry.crc32,
                uncomp_size=vals[0] if entry.uncomp_size == _U32_SENTINEL else entry.uncomp_size,
                comp_size=vals[1] if entry.comp_size == _U32_SENTINEL else entry.comp_size,
                lh_off=vals[2] if entry.lh_off == _U32_SENTINEL else entry.lh_off,
                comment=entry.comment,
            )
        pos += 4 + length
    return entry


def _parse_cd(cd: bytes, budget: ReadBudget) -> tuple[list[CdEntry], dict[str, list[CdEntry]]]:
    entries: list[CdEntry] = []
    duplicates: dict[str, list[CdEntry]] = {}
    seen: dict[str, CdEntry] = {}
    pos = 0
    while pos + _CD_LEN <= len(cd):
        if cd[pos : pos + 4] != _CD_SIG:
            break
        (flags, method, _mt, _md, crc, comp, uncomp,
         n_len, x_len, c_len, _disk, _iattr, _xattr, lh_off) = struct.unpack_from(
            "<HHHHIIIHHHHHII", cd, pos + 8,
        )
        end = pos + _CD_LEN + n_len + x_len + c_len
        if end > len(cd):
            raise _fail(
                STATE_CORRUPT,
                f"CD entry overruns central directory at offset {pos}",
            )
        raw_name = cd[pos + _CD_LEN : pos + _CD_LEN + n_len]
        name = raw_name.decode("utf-8", "replace")
        entry = CdEntry(
            name=name,
            method=method,
            flags=flags,
            crc32=crc,
            comp_size=comp,
            uncomp_size=uncomp,
            lh_off=lh_off,
            comment=cd[
                pos + _CD_LEN + n_len + x_len : end
            ].decode("utf-8", "replace"),
        )
        if _U32_SENTINEL in (comp, uncomp, lh_off):
            entry = _zip64_extra(entry, cd[pos + _CD_LEN + n_len : pos + _CD_LEN + n_len + x_len])
        if name in seen:
            duplicates.setdefault(name, [seen[name]]).append(entry)
        else:
            seen[name] = entry
        entries.append(entry)
        if len(entries) > budget.max_members:
            raise _fail(
                STATE_RESOURCE_LIMIT,
                f"central directory exceeds member cap {budget.max_members}",
            )
        pos = end
    return entries, duplicates


def index_zip(obj: PinnedObject) -> ZipIndex:
    """Ranged EOCD→CD parse of one pinned archive; raises SourceReadError."""
    size = obj.size
    if size < _EOCD_LEN:
        raise _fail(STATE_CORRUPT, "object too small to be a ZIP archive")
    tail = obj.read_tail(TAIL_WINDOW)
    eocd = _parse_eocd(tail, size)
    if eocd["zip64"]:
        cd_off, cd_size, count = _read_zip64(obj, eocd["zip64_eocd_off"])
    else:
        cd_off, cd_size, count = (
            eocd["cd_off"], eocd["cd_size"], eocd["count"],
        )
    if cd_size > obj.budget.max_cd_bytes:
        raise _fail(
            STATE_RESOURCE_LIMIT,
            f"central directory {cd_size}B exceeds cap "
            f"{obj.budget.max_cd_bytes}B",
        )
    if cd_off + cd_size > size or cd_off < 0:
        raise _fail(STATE_CORRUPT, "central directory outside object bounds")
    cd = obj.read_range(cd_off, cd_off + cd_size - 1) if cd_size else b""
    entries, duplicates = _parse_cd(cd, obj.budget)
    if count != len(entries):
        raise _fail(
            STATE_CORRUPT,
            f"EOCD declares {count} entries, parsed {len(entries)}",
        )
    return ZipIndex(
        entries=entries,
        duplicates=duplicates,
        zip64=eocd["zip64"],
        comment=eocd["comment"],
    )


def _local_data_start(obj: PinnedObject, entry: CdEntry) -> int:
    """Member payload offset from the local header (CD sizes are authority)."""
    lh = obj.read_range(entry.lh_off, entry.lh_off + _LH_LEN - 1)
    if lh[:4] != _LH_SIG:
        raise _fail(
            STATE_CORRUPT,
            f"local header for {entry.name!r} has no PK\\x03\\x04 signature",
        )
    n_len, x_len = struct.unpack_from("<HH", lh, 26)
    data_start = entry.lh_off + _LH_LEN + n_len + x_len
    if data_start > obj.size:
        raise _fail(
            STATE_CORRUPT,
            f"member {entry.name!r} data start beyond object end",
        )
    return data_start


def _inflate_bounded(blob: bytes, entry: CdEntry, budget: ReadBudget) -> bytes:
    """Deflate ``blob`` with a hard decoded-size ceiling."""
    decoder = zlib.decompressobj(-15)
    limit = min(entry.uncomp_size + 1, budget.max_decoded_bytes + 1)
    try:
        out = decoder.decompress(blob, limit)
    except zlib.error as exc:
        raise _fail(
            STATE_DECODE_FAILURE, f"deflate stream invalid for {entry.name!r}"
        ) from exc
    if decoder.unconsumed_tail:
        raise _fail(
            STATE_RESOURCE_LIMIT,
            f"member {entry.name!r} decoded beyond cap {limit}B",
        )
    if not decoder.eof:
        raise _fail(
            STATE_CORRUPT,
            f"member {entry.name!r} deflate stream truncated",
        )
    if len(out) != entry.uncomp_size:
        raise _fail(
            STATE_DECODE_FAILURE,
            f"member {entry.name!r} decoded {len(out)}B != declared "
            f"{entry.uncomp_size}B",
        )
    return out


def _verify_member(payload: bytes, entry: CdEntry) -> None:
    if zlib.crc32(payload) & 0xFFFFFFFF != entry.crc32:
        raise _fail(
            STATE_CRC_FAILURE,
            f"member {entry.name!r} CRC32 mismatch",
        )


def read_member(obj: PinnedObject, entry: CdEntry) -> bytes:
    """Bounded, CRC-verified member payload; raises SourceReadError."""
    if entry.flags & _GENERAL_PURPOSE_ENCRYPTED:
        raise _fail(
            STATE_UNSUPPORTED_COMPRESSION,
            f"member {entry.name!r} is encrypted",
        )
    if entry.method not in _METHODS:
        raise _fail(
            STATE_UNSUPPORTED_COMPRESSION,
            f"member {entry.name!r} uses method {entry.method}",
        )
    if entry.comp_size > obj.budget.max_member_bytes:
        raise _fail(
            STATE_RESOURCE_LIMIT,
            f"member {entry.name!r} stores {entry.comp_size}B > cap "
            f"{obj.budget.max_member_bytes}B",
        )
    if entry.uncomp_size > obj.budget.max_decoded_bytes:
        raise _fail(
            STATE_RESOURCE_LIMIT,
            f"member {entry.name!r} decodes to {entry.uncomp_size}B > cap "
            f"{obj.budget.max_decoded_bytes}B",
        )
    data_start = _local_data_start(obj, entry)
    if data_start + entry.comp_size > obj.size:
        raise _fail(
            STATE_CORRUPT,
            f"member {entry.name!r} payload truncated at object end",
        )
    blob = obj.read_range(data_start, data_start + entry.comp_size - 1) if entry.comp_size else b""
    if entry.method == 0:
        if entry.comp_size != entry.uncomp_size:
            raise _fail(
                STATE_CORRUPT,
                f"stored member {entry.name!r} comp/uncomp sizes disagree",
            )
        payload = blob
    else:
        payload = _inflate_bounded(blob, entry, obj.budget)
    _verify_member(payload, entry)
    return payload


def read_member_named(obj: PinnedObject, index: ZipIndex, name: str) -> ReadOutcome:
    """Typed outcome for one exact member name."""
    matches = index.members_named(name)
    if not matches:
        return ReadOutcome(
            STATE_MISSING_MEMBER, f"member {name!r} not in archive",
        )
    if len(matches) > 1:
        return ReadOutcome(
            STATE_DUPLICATE_MEMBER,
            f"{len(matches)} members named {name!r}; ambiguous, quarantined",
        )
    try:
        return ReadOutcome(STATE_AVAILABLE, body=read_member(obj, matches[0]))
    except SourceReadError as exc:
        return ReadOutcome(exc.state, exc.detail)


def open_zip(obj: PinnedObject) -> tuple[ZipIndex | None, ReadOutcome | None]:
    """``(index, None)`` or ``(None, failure outcome)`` for a pinned object."""
    try:
        return index_zip(obj), None
    except SourceReadError as exc:
        return None, ReadOutcome(exc.state, exc.detail)
