"""Hand-built synthetic ZIP archives for D1 reader regression tests.

Deliberately byte-level: fixtures need sentinel fields, decoy signatures,
wrong CRCs and truncated members that ``zipfile`` refuses to produce.
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

LH_SIG = b"PK\x03\x04"
CD_SIG = b"PK\x01\x02"
EOCD_SIG = b"PK\x05\x06"
Z64_EOCD_SIG = b"PK\x06\x06"
Z64_LOC_SIG = b"PK\x06\x07"

U16 = 0xFFFF
U32 = 0xFFFFFFFF


@dataclass
class Member:
    name: str
    data: bytes
    method: int = 0  # 0 stored, 8 deflate, anything else unsupported
    flags: int = 0
    crc_override: int | None = None  # write a wrong CRC into headers
    comp_override: int | None = None  # lie about compressed size in CD+LH
    uncomp_override: int | None = None
    extra: bytes = b""

    @property
    def encoded_name(self) -> bytes:
        return self.name.encode("utf-8")

    @property
    def compressed(self) -> bytes:
        if self.method == 0:
            return self.data
        if self.method == 8:
            obj = zlib.compressobj(9, zlib.DEFLATED, -15)
            return obj.compress(self.data) + obj.flush()
        return self.data

    @property
    def crc(self) -> int:
        if self.crc_override is not None:
            return self.crc_override
        return zlib.crc32(self.data) & 0xFFFFFFFF


def member(name: str, data: bytes, **kwargs) -> Member:
    return Member(name=name, data=data, **kwargs)


def _local_header(mem: Member, zip64: bool) -> bytes:
    comp, uncomp = len(mem.compressed), len(mem.data)
    if zip64:
        extra = mem.extra + struct.pack(
            "<HHQQ", 0x0001, 16, uncomp, comp,
        )
        return struct.pack(
            "<IHHHHHIIIHH", 0x04034B50, 45, mem.flags, mem.method,
            0, 0, mem.crc, U32, U32,
            len(mem.encoded_name), len(extra),
        ) + mem.encoded_name + extra
    return struct.pack(
        "<IHHHHHIIIHH", 0x04034B50, 20, mem.flags, mem.method,
        0, 0, mem.crc,
        mem.comp_override if mem.comp_override is not None else comp,
        mem.uncomp_override if mem.uncomp_override is not None else uncomp,
        len(mem.encoded_name), len(mem.extra),
    ) + mem.encoded_name + mem.extra


def _cd_entry(mem: Member, lh_off: int, zip64: bool) -> bytes:
    comp = mem.comp_override if mem.comp_override is not None else len(mem.compressed)
    uncomp = mem.uncomp_override if mem.uncomp_override is not None else len(mem.data)
    if zip64:
        extra = mem.extra + struct.pack(
            "<HHQQQI", 0x0001, 28, uncomp, comp, lh_off, 0,
        )
        comp_f, uncomp_f, off_f = U32, U32, U32
    else:
        extra = mem.extra
        comp_f, uncomp_f, off_f = comp, uncomp, lh_off
    return struct.pack(
        "<IHHHHHHIIIHHHHHII", 0x02014B50, 45, 45, mem.flags,
        mem.method, 0, 0, mem.crc, comp_f, uncomp_f,
        len(mem.encoded_name), len(extra), 0, 0, 0, 0, off_f,
    ) + mem.encoded_name + extra


def build_zip(members: list[Member], *, comment: bytes = b"", zip64: bool = False) -> bytes:
    """Assemble local headers + data + CD + optional ZIP64 chain + EOCD."""
    blob = bytearray()
    cd_entries: list[bytes] = []
    for mem in members:
        lh_off = len(blob)
        blob += _local_header(mem, zip64)
        blob += mem.compressed
        cd_entries.append(_cd_entry(mem, lh_off, zip64))
    cd_off = len(blob)
    cd = b"".join(cd_entries)
    blob += cd
    if zip64:
        eocd64_off = len(blob)
        blob += struct.pack(
            "<IQHHIIQQQQ", 0x06064B50, 44, 45, 45, 0, 0,
            len(members), len(members), len(cd), cd_off,
        )
        blob += struct.pack(
            "<IIQI", 0x07064B50, 0, eocd64_off, 1,
        )
        blob += struct.pack(
            "<IHHHHIIH", 0x06054B50, 0, 0, U16, U16, U32, U32,
            len(comment),
        )
    else:
        blob += struct.pack(
            "<IHHHHIIH", 0x06054B50, 0, 0, len(members), len(members),
            len(cd), cd_off, len(comment),
        )
    blob += comment
    return bytes(blob)


def gzip_wrap(data: bytes) -> bytes:
    import gzip

    return gzip.compress(data)
