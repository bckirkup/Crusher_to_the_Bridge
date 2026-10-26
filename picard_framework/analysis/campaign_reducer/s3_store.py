"""S3-backed create-only derived store for the campaign reducer (ticket D3).

``S3DerivedStore`` mirrors :class:`LocalDirStore` semantics over a single
bucket prefix: puts are create-only via ``PutObject`` conditioned on
``If-None-Match: *`` — S3 rejects the write when the key already exists,
so an overwrite is impossible at the transport level, not just by
convention. ``put_idempotent`` then fetches the existing body to decide
byte-identical resume vs. conflicting overwrite
(:class:`DerivedConflict`).

All boto3/botocore imports stay inside the class so offline paths never
touch the SDK; tests inject a stubbed client object.
"""
from __future__ import annotations

from .derived_store import DerivedConflict, DerivedStoreError, _sha

_KIND = {
    "NoSuchKey": "not_found",
    "NoSuchBucket": "not_found",
    "NoSuchVersion": "not_found",
    "404": "not_found",
    "AccessDenied": "denied",
    "403": "denied",
    "PreconditionFailed": "exists",
    "412": "exists",
    "SlowDown": "throttled",
    "503": "throttled",
    "InternalError": "transient",
    "500": "transient",
}


class S3DerivedStore:
    """Create-only derived store over ``s3://<bucket>/<prefix>``."""

    def __init__(self, client, bucket: str, prefix: str = "") -> None:
        self._client = client
        self._bucket = bucket
        self._prefix = prefix.strip("/")

    def _key(self, key: str) -> str:
        rel = key.lstrip("/")
        if ".." in rel.split("/"):
            raise DerivedStoreError("denied", f"{key} escapes store root")
        return f"{self._prefix}/{rel}" if self._prefix else rel

    def _call(self, fn, **kwargs):
        from botocore.exceptions import ClientError  # noqa: PLC0415

        try:
            return fn(**kwargs)
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            status = exc.response.get("ResponseMetadata", {}).get(
                "HTTPStatusCode",
            )
            raise DerivedStoreError(
                _KIND.get(code, _KIND.get(str(status), "transient")),
                code or str(exc),
            ) from exc

    def _put(self, key: str, body: bytes) -> None:
        self._call(
            self._client.put_object,
            Bucket=self._bucket,
            Key=self._key(key),
            Body=body,
            IfNoneMatch="*",
        )

    def _existing(self, key: str) -> bytes:
        resp = self._call(
            self._client.get_object,
            Bucket=self._bucket,
            Key=self._key(key),
        )
        return resp["Body"].read()

    def put_if_absent(self, key: str, body: bytes) -> str:
        """Conditional create-only put; returns the body sha256."""
        try:
            self._put(key, body)
        except DerivedStoreError as exc:
            if exc.kind != "exists":
                raise
            raise DerivedConflict(
                key, _sha(self._existing(key)), _sha(body)
            ) from exc
        return _sha(body)

    def put_idempotent(self, key: str, body: bytes) -> bool:
        """Create-only put tolerant of byte-identical resume."""
        try:
            self._put(key, body)
        except DerivedStoreError as exc:
            if exc.kind != "exists":
                raise
            existing = self._existing(key)
            if _sha(existing) == _sha(body):
                return False
            raise DerivedConflict(key, _sha(existing), _sha(body)) from exc
        return True

    def get(self, key: str) -> bytes:
        try:
            return self._existing(key)
        except DerivedStoreError as exc:
            if exc.kind == "not_found":
                raise DerivedStoreError("not_found", key) from exc
            raise

    def head(self, key: str) -> dict | None:
        try:
            out = self._call(
                self._client.head_object,
                Bucket=self._bucket,
                Key=self._key(key),
            )
        except DerivedStoreError as exc:
            if exc.kind == "not_found":
                return None
            raise
        return {
            "key": key,
            "bytes": int(out["ContentLength"]),
            "sha256": out.get("Metadata", {}).get("sha256"),
            "etag": out.get("ETag"),
            "version_id": out.get("VersionId"),
        }

    def list(self, prefix: str = "") -> list[str]:
        full = self._key(prefix) if prefix else (self._prefix + "/" if self._prefix else "")
        keys: list[str] = []
        token: str | None = None
        while True:
            kwargs: dict = {"Bucket": self._bucket, "Prefix": full}
            if token:
                kwargs["ContinuationToken"] = token
            page = self._call(self._client.list_objects_v2, **kwargs)
            for obj in page.get("Contents") or []:
                name = obj["Key"]
                keys.append(
                    name[len(self._prefix) + 1:]
                    if self._prefix and name.startswith(self._prefix + "/")
                    else name
                )
            token = page.get("NextContinuationToken")
            if not token:
                break
        return sorted(keys)
