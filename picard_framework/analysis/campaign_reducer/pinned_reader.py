"""Pinned bounded object readers for the campaign reducer (ticket D1).

Every read of a source object is pinned: HEAD first, then either a
``VersionId`` pin (non-null literal = immutable version) or an ``If-Match``
ETag condition on every ranged GET. An object that only reports
``VersionId="null"`` uses If-Match — it is never accepted as immutable. A
412/identity drift between HEAD and a ranged GET yields the typed outcome
``source_changed``; bytes from different identities are never mixed.

All byte flow is charged to one :class:`ReadBudget` shared across retries
and shards — caps are cumulative, not per call. Data-path failures surface
as typed outcomes (``source_objects.read_state`` literals), never as
exceptions-as-data; only genuinely unexpected infrastructure failures raise.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

# --- source_objects.read_state literals (FIELD_CONTRACTS.json enum) ---
STATE_AVAILABLE = "available"
STATE_MISSING_MEMBER = "missing_member"
STATE_MISSING_OBJECT = "missing_object"
STATE_ACCESS_DENIED = "access_denied"
STATE_ARCHIVED = "archived_unrestored"
STATE_CORRUPT = "corrupt_archive"
STATE_CRC_FAILURE = "crc_failure"
STATE_DECODE_FAILURE = "decode_failure"
STATE_SOURCE_CHANGED = "source_changed"
STATE_UNSUPPORTED_SCHEMA = "unsupported_schema"
STATE_UNSUPPORTED_COMPRESSION = "unsupported_compression"
STATE_RESOURCE_LIMIT = "resource_limit"
STATE_NOT_YET_READ = "not_yet_read"

# Reducer-internal states (not contract literals; canonical_* maps them to
# the nearest contract literal for row emission).
STATE_DUPLICATE_MEMBER = "duplicate_members"
STATE_UNPINNED_BLOCKED = "unpinned_blocked"
STATE_TRANSPORT_ERROR = "transport_error"

CONTRACT_READ_STATES = frozenset({
    STATE_AVAILABLE, STATE_MISSING_MEMBER, STATE_MISSING_OBJECT,
    STATE_ACCESS_DENIED, STATE_ARCHIVED, STATE_CORRUPT, STATE_CRC_FAILURE,
    STATE_DECODE_FAILURE, STATE_SOURCE_CHANGED, STATE_UNSUPPORTED_SCHEMA,
    STATE_UNSUPPORTED_COMPRESSION, STATE_RESOURCE_LIMIT, STATE_NOT_YET_READ,
})

# source_objects.read_state for reducer-internal outcomes; the precise
# reason is always preserved alongside in ``detail``.
_CANONICAL_SOURCE_STATE = {
    STATE_DUPLICATE_MEMBER: STATE_CORRUPT,
    STATE_UNPINNED_BLOCKED: STATE_ACCESS_DENIED,
    STATE_TRANSPORT_ERROR: STATE_NOT_YET_READ,
}

PIN_VERSION_ID = "version_id"
PIN_IF_MATCH_ETAG = "if_match_etag"
PIN_UNPINNED_BLOCKED = "unpinned_blocked"

_KIB = 1 << 10
_MIB = 1 << 20

_RETRYABLE_KINDS = frozenset({"throttled", "timeout", "transient"})

_ERROR_KIND_STATE = {
    "not_found": STATE_MISSING_OBJECT,
    "access_denied": STATE_ACCESS_DENIED,
    "invalid_object_state": STATE_ARCHIVED,
    "precondition_failed": STATE_SOURCE_CHANGED,
}

_CONTENT_RANGE = re.compile(r"bytes (\d+)-(\d+)/(\d+|\*)")


def canonical_source_read_state(state: str) -> str:
    """The contract ``source_objects.read_state`` literal for a read state."""
    return _CANONICAL_SOURCE_STATE.get(state, state)


class TransportError(Exception):
    """Classified transport failure raised by an :class:`ObjectTransport`.

    ``kind`` is a coarse classifier the reader maps to typed states:
    ``not_found``, ``access_denied``, ``invalid_object_state``
    (archive-class object mid-restore), ``precondition_failed`` (412),
    ``throttled``/``timeout``/``transient`` (retryable).
    """

    def __init__(self, kind: str, detail: str = "", *, status: int | None = None):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail
        self.status = status


class SourceReadError(Exception):
    """A data-path read failure carrying its typed ``read_state``."""

    def __init__(self, state: str, detail: str = ""):
        super().__init__(f"{state}: {detail}")
        self.state = state
        self.detail = detail


class BudgetExceeded(SourceReadError):
    """An admitted byte/request/member ceiling was hit (resource_limit)."""

    def __init__(self, detail: str = ""):
        super().__init__(STATE_RESOURCE_LIMIT, detail)


@dataclass(frozen=True)
class HeadInfo:
    """HEAD evidence for one object."""

    content_length: int
    etag: str | None = None
    version_id: str | None = None
    storage_class: str | None = None
    last_modified: str | None = None
    restore_status: str | None = None


@dataclass(frozen=True)
class GetResponse:
    """One GET/ranged-GET response."""

    status: int
    body: bytes
    content_range: str | None = None
    etag: str | None = None
    version_id: str | None = None


@runtime_checkable
class ObjectTransport(Protocol):
    """Minimal object-store surface the readers are written against."""

    def head(self, key: str) -> HeadInfo: ...

    def get(
        self,
        key: str,
        *,
        start: int | None = None,
        end: int | None = None,
        version_id: str | None = None,
        if_match: str | None = None,
    ) -> GetResponse: ...


@dataclass
class ReadBudget:
    """Cumulative admitted ceilings, shared across retries and shards.

    ``requests_used``/``bytes_used`` accumulate over every GET (including
    retries) charged through this instance, so a shard's total spend — not
    one call's — is what the caps bound.
    """

    max_requests: int = 512
    max_total_bytes: int = 512 * _MIB
    max_range_bytes: int = 16 * _MIB
    max_object_bytes: int = 64 * _MIB
    max_cd_bytes: int = 16 * _MIB
    max_members: int = 4096
    max_member_bytes: int = 64 * _MIB
    max_decoded_bytes: int = 256 * _MIB
    max_retries: int = 3
    requests_used: int = 0
    bytes_used: int = 0

    def charge_request(self, detail: str = "") -> None:
        self.requests_used += 1
        if self.requests_used > self.max_requests:
            raise BudgetExceeded(
                f"request budget {self.max_requests} exceeded {detail}"
            )

    def charge_bytes(self, n: int, detail: str = "") -> None:
        self.bytes_used += n
        if self.bytes_used > self.max_total_bytes:
            raise BudgetExceeded(
                f"cumulative byte budget {self.max_total_bytes} exceeded {detail}"
            )


@dataclass(frozen=True)
class SourcePin:
    """The conditional identity every subsequent read carries."""

    kind: str  # PIN_VERSION_ID | PIN_IF_MATCH_ETAG | PIN_UNPINNED_BLOCKED
    version_id: str | None
    etag: str | None


@dataclass(frozen=True)
class ReadOutcome:
    """Typed result of one read — never an exception-as-data."""

    state: str
    detail: str = ""
    body: bytes | None = None

    @property
    def ok(self) -> bool:
        return self.state == STATE_AVAILABLE


def _outcome_of(exc: SourceReadError) -> ReadOutcome:
    return ReadOutcome(state=exc.state, detail=exc.detail)


def _state_of_transport(exc: TransportError) -> str:
    return _ERROR_KIND_STATE.get(exc.kind, STATE_TRANSPORT_ERROR)


class PinnedObject:
    """One HEAD-pinned object: all ranged reads carry the same pin."""

    def __init__(
        self,
        transport: ObjectTransport,
        bucket: str,
        key: str,
        head: HeadInfo,
        pin: SourcePin,
        budget: ReadBudget,
    ) -> None:
        self.transport = transport
        self.bucket = bucket
        self.key = key
        self.head = head
        self.pin = pin
        self.budget = budget

    @property
    def size(self) -> int:
        return self.head.content_length

    def _get(self, start: int | None, end: int | None) -> GetResponse:
        kwargs = (
            {"version_id": self.pin.version_id}
            if self.pin.kind == PIN_VERSION_ID
            else {"if_match": self.pin.etag}
        )
        if start is not None:
            kwargs["start"] = start
            kwargs["end"] = end
        attempts = 0
        while True:
            self.budget.charge_request(f"on GET {self.key}")
            try:
                return self.transport.get(self.key, **kwargs)
            except TransportError as exc:
                attempts = self._classify_transport(exc, attempts)
            except Exception as exc:  # noqa: BLE001 — transport bugs are typed, not leaked
                raise SourceReadError(STATE_TRANSPORT_ERROR, repr(exc)) from exc

    def _classify_transport(self, exc: TransportError, attempts: int) -> int:
        """Map a TransportError to a typed state or the next retry count."""
        if exc.kind in _ERROR_KIND_STATE:
            raise SourceReadError(
                _state_of_transport(exc), exc.detail or exc.kind,
            ) from exc
        if exc.kind in _RETRYABLE_KINDS and attempts < self.budget.max_retries:
            return attempts + 1
        raise SourceReadError(
            STATE_TRANSPORT_ERROR,
            f"unclassified transport failure {exc.kind}: {exc.detail}",
        ) from exc

    def _validate_range(self, start: int, end: int, resp: GetResponse) -> bytes:
        if end - start + 1 > self.budget.max_range_bytes:
            raise SourceReadError(
                STATE_RESOURCE_LIMIT,
                f"range {end - start + 1}B exceeds per-range cap "
                f"{self.budget.max_range_bytes}B",
            )
        if resp.status == 206:
            return self._check_206(start, end, resp)
        if resp.status == 200:
            return self._check_whole_for_range(start, end, resp)
        raise SourceReadError(
            STATE_TRANSPORT_ERROR, f"unexpected GET status {resp.status}"
        )

    def _check_206(self, start: int, end: int, resp: GetResponse) -> bytes:
        match = _CONTENT_RANGE.fullmatch(resp.content_range or "")
        if match is None:
            raise SourceReadError(
                STATE_CORRUPT,
                f"ranged GET missing/invalid Content-Range {resp.content_range!r}",
            )
        first, last, total = int(match[1]), int(match[2]), match[3]
        if first != start or last - first + 1 != len(resp.body):
            raise SourceReadError(
                STATE_CORRUPT,
                f"Content-Range {resp.content_range!r} inconsistent with "
                f"request {start}-{end} and {len(resp.body)}B returned",
            )
        if last > end or len(resp.body) > end - start + 1:
            raise SourceReadError(
                STATE_CORRUPT,
                "ranged GET returned more bytes than requested",
            )
        if total != "*" and int(total) != self.head.content_length:
            raise SourceReadError(
                STATE_SOURCE_CHANGED,
                f"Content-Range total {total} != HEAD size "
                f"{self.head.content_length}",
            )
        if len(resp.body) < end - start + 1:
            raise SourceReadError(
                STATE_CORRUPT,
                f"ranged GET truncated: {len(resp.body)}B of "
                f"{end - start + 1}B",
            )
        self.budget.charge_bytes(len(resp.body), "ranged GET")
        return resp.body

    def _check_whole_for_range(
        self, start: int, end: int, resp: GetResponse,
    ) -> bytes:
        body = resp.body
        if len(body) != self.head.content_length:
            raise SourceReadError(
                STATE_SOURCE_CHANGED,
                f"whole-body reply to range request: {len(body)}B != HEAD "
                f"{self.head.content_length}B",
            )
        if len(body) > self.budget.max_range_bytes:
            raise SourceReadError(
                STATE_RESOURCE_LIMIT,
                f"server ignored Range; whole body {len(body)}B exceeds "
                f"per-range cap {self.budget.max_range_bytes}B",
            )
        if end >= len(body):
            raise SourceReadError(
                STATE_CORRUPT,
                f"range {start}-{end} outside {len(body)}B object",
            )
        self.budget.charge_bytes(len(body), "whole-body range fallback")
        return body[start : end + 1]

    def read_range(self, start: int, end: int) -> bytes:
        """Bounded conditional ranged GET; raises SourceReadError."""
        if start < 0 or end < start or end >= self.head.content_length:
            raise SourceReadError(
                STATE_CORRUPT,
                f"range {start}-{end} outside {self.head.content_length}B object",
            )
        resp = self._get(start, end)
        return self._validate_range(start, end, resp)

    def read_tail(self, n: int) -> bytes:
        """The last ``min(n, size)`` bytes of the object."""
        tail = min(n, self.head.content_length)
        return self.read_range(
            self.head.content_length - tail, self.head.content_length - 1,
        )

    def read_whole(self, max_bytes: int | None = None) -> bytes:
        """Bounded whole-object GET — the small-object fallback path."""
        cap = self.budget.max_object_bytes if max_bytes is None else max_bytes
        if self.head.content_length > cap:
            raise SourceReadError(
                STATE_RESOURCE_LIMIT,
                f"object {self.head.content_length}B exceeds whole-body cap "
                f"{cap}B; ranged reads required",
            )
        resp = self._get(None, None)
        if resp.status not in (200, 206):
            raise SourceReadError(
                STATE_TRANSPORT_ERROR, f"unexpected GET status {resp.status}"
            )
        body = resp.body
        if len(body) != self.head.content_length:
            raise SourceReadError(
                STATE_SOURCE_CHANGED,
                f"whole GET {len(body)}B != HEAD {self.head.content_length}B",
            )
        if len(body) > cap:
            raise SourceReadError(
                STATE_RESOURCE_LIMIT,
                f"returned body {len(body)}B exceeds whole-body cap {cap}B",
            )
        self.budget.charge_bytes(len(body), "whole-body GET")
        return body


def pin_for(head: HeadInfo) -> SourcePin:
    """Choose the conditional pin from HEAD evidence.

    A non-empty ``VersionId`` other than the literal ``"null"`` is the
    immutable pin; otherwise the ETag carries an ``If-Match`` condition on
    every read; an object offering neither is ``unpinned_blocked``.
    """
    if head.version_id not in (None, "", "null"):
        return SourcePin(PIN_VERSION_ID, head.version_id, head.etag)
    if head.etag:
        return SourcePin(PIN_IF_MATCH_ETAG, None, head.etag)
    return SourcePin(PIN_UNPINNED_BLOCKED, None, None)


def open_pinned(
    transport: ObjectTransport,
    bucket: str,
    key: str,
    budget: ReadBudget | None = None,
) -> PinnedObject:
    """HEAD ``key`` and return its pinned handle; raises SourceReadError."""
    budget = budget if budget is not None else ReadBudget()
    budget.charge_request(f"on HEAD {key}")
    try:
        head = transport.head(key)
    except TransportError as exc:
        raise SourceReadError(_state_of_transport(exc), exc.detail or exc.kind) from exc
    except Exception as exc:  # noqa: BLE001
        raise SourceReadError(STATE_TRANSPORT_ERROR, repr(exc)) from exc
    return PinnedObject(transport, bucket, key, head, pin_for(head), budget)


def read_object(
    transport: ObjectTransport,
    bucket: str,
    key: str,
    budget: ReadBudget | None = None,
    *,
    max_bytes: int | None = None,
) -> ReadOutcome:
    """Typed whole-object read: HEAD-pin then bounded conditional GET."""
    try:
        obj = open_pinned(transport, bucket, key, budget)
        if obj.pin.kind == PIN_UNPINNED_BLOCKED:
            return ReadOutcome(
                STATE_UNPINNED_BLOCKED,
                "HEAD returned neither a usable VersionId nor an ETag; "
                "reads cannot be pinned",
            )
        return ReadOutcome(STATE_AVAILABLE, body=obj.read_whole(max_bytes))
    except SourceReadError as exc:
        return _outcome_of(exc)
    except BudgetExceeded as exc:
        return ReadOutcome(STATE_RESOURCE_LIMIT, str(exc))


class MemoryTransport:
    """In-memory ``ObjectTransport`` for offline fixtures and tests.

    Versions are immutable once ``put``; ``mutate`` replaces the live object
    (new ETag) so conditional If-Match reads observe a 412 — the
    ``source_changed`` signature. Failure hooks model access-denied,
    archived (InvalidObjectState) and range-unhonored transports.
    """

    def __init__(self) -> None:
        self._objects: dict[str, dict] = {}
        self.fail_head: dict[str, str] = {}
        self.fail_get: dict[str, str] = {}
        self.honor_ranges = True
        self.calls: list[tuple] = []

    def put(
        self,
        key: str,
        body: bytes,
        *,
        etag: str | None = None,
        version_id: str | None = "v1",
        storage_class: str = "STANDARD",
    ) -> None:
        import hashlib

        entry = self._objects.setdefault(key, {})
        entry["body"] = body
        entry["etag"] = etag or '"' + hashlib.md5(body).hexdigest() + '"'  # noqa: S324 — fixture identity, not security
        entry["version_id"] = version_id
        entry["storage_class"] = storage_class
        entry["last_modified"] = "1970-01-01T00:00:00Z"
        versions = entry.setdefault("versions", {})
        if version_id:
            versions[version_id] = (body, entry["etag"])

    def mutate(self, key: str, body: bytes, *, etag: str | None = None) -> None:
        """Overwrite the live object — the source-changed signature."""
        entry = self._objects[key]
        entry["body"] = body
        entry["etag"] = etag or '"' + hashlib.md5(body).hexdigest() + '"'  # noqa: S324

    def head(self, key: str) -> HeadInfo:
        self.calls.append(("head", key))
        if key in self.fail_head:
            raise TransportError(self.fail_head[key], key)
        if key not in self._objects:
            raise TransportError("not_found", key)
        entry = self._objects[key]
        return HeadInfo(
            content_length=len(entry["body"]),
            etag=entry["etag"],
            version_id=entry["version_id"],
            storage_class=entry["storage_class"],
            last_modified=entry["last_modified"],
        )

    def get(
        self,
        key: str,
        *,
        start: int | None = None,
        end: int | None = None,
        version_id: str | None = None,
        if_match: str | None = None,
    ) -> GetResponse:
        self.calls.append(("get", key, start, end, version_id, if_match))
        if key in self.fail_get:
            raise TransportError(self.fail_get[key], key)
        if key not in self._objects:
            raise TransportError("not_found", key)
        entry = self._objects[key]
        if if_match is not None and if_match != entry["etag"]:
            raise TransportError("precondition_failed", key, status=412)
        body = entry["body"]
        etag = entry["etag"]
        if version_id is not None:
            versions = entry.get("versions", {})
            if version_id not in versions:
                raise TransportError("not_found", f"{key}?versionId={version_id}")
            body, etag = versions[version_id]
        if start is None:
            return GetResponse(200, body, etag=etag, version_id=version_id)
        if not self.honor_ranges:
            return GetResponse(200, body, etag=etag, version_id=version_id)
        total = len(body)
        last = min(end, total - 1)
        chunk = body[start : last + 1]
        return GetResponse(
            206,
            chunk,
            content_range=f"bytes {start}-{last}/{total}",
            etag=etag,
            version_id=version_id,
        )


def boto3_transport(client, bucket: str) -> ObjectTransport:
    """Adapt an ``s3`` boto3 client to :class:`ObjectTransport` (lazy import).

    Keys are plain object keys within ``bucket``; all boto3/botocore imports
    stay inside the call so offline paths never touch the SDK.
    """
    from botocore.exceptions import ClientError  # noqa: PLC0415

    _KIND = {
        "NoSuchKey": "not_found",
        "NoSuchVersion": "not_found",
        "404": "not_found",
        "AccessDenied": "access_denied",
        "403": "access_denied",
        "InvalidObjectState": "invalid_object_state",
        "PreconditionFailed": "precondition_failed",
        "412": "precondition_failed",
        "SlowDown": "throttled",
        "503": "throttled",
        "InternalError": "transient",
        "500": "transient",
    }

    class _Boto3Transport:
        def _call(self, fn, **kwargs):
            try:
                return fn(**kwargs)
            except ClientError as exc:
                code = str(exc.response.get("Error", {}).get("Code", ""))
                status = exc.response.get("ResponseMetadata", {}).get(
                    "HTTPStatusCode",
                )
                raise TransportError(
                    _KIND.get(code, _KIND.get(str(status), "transient")),
                    code or str(exc),
                    status=status,
                ) from exc

        def head(self, key: str) -> HeadInfo:
            resp = self._call(
                client.head_object, Bucket=bucket, Key=key,
            )
            return HeadInfo(
                content_length=int(resp["ContentLength"]),
                etag=resp.get("ETag"),
                version_id=resp.get("VersionId"),
                storage_class=resp.get("StorageClass"),
                last_modified=str(resp.get("LastModified") or "") or None,
                restore_status=resp.get("Restore"),
            )

        def get(
            self,
            key: str,
            *,
            start: int | None = None,
            end: int | None = None,
            version_id: str | None = None,
            if_match: str | None = None,
        ) -> GetResponse:
            kwargs: dict = {"Bucket": bucket, "Key": key}
            if version_id:
                kwargs["VersionId"] = version_id
            if if_match:
                kwargs["IfMatch"] = if_match
            if start is not None:
                kwargs["Range"] = f"bytes={start}-{end}"
            resp = self._call(client.get_object, **kwargs)
            return GetResponse(
                status=int(
                    resp.get("ResponseMetadata", {}).get("HTTPStatusCode", 200),
                ),
                body=resp["Body"].read(),
                content_range=resp.get("ContentRange"),
                etag=resp.get("ETag"),
                version_id=resp.get("VersionId"),
            )

    return _Boto3Transport()


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """``(bucket, key)`` from an ``s3://bucket/key`` URI."""
    if not uri.startswith("s3://"):
        raise ValueError(f"expected an s3:// URI, got {uri!r}")
    rest = uri[len("s3://"):]
    bucket, _, key = rest.partition("/")
    return bucket, key
