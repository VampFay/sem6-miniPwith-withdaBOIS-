from __future__ import annotations

import fcntl
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from src.runtime import OperatingMode, sha256_bytes

AUDIT_LOCK = Lock()
AUDIT_SCHEMA_VERSION = 1
AUDIT_HEAD_NAME = ".chain-head"
AUDIT_PROCESS_LOCK_NAME = ".audit.lock"


def software_version() -> str:
    try:
        return version("attn-dist-net")
    except PackageNotFoundError:
        return "development"


@dataclass(frozen=True)
class AnalysisProvenance:
    analysis_uuid: str
    analysis_id: str
    created_at_utc: str
    software_version: str
    release_id: str
    operating_mode: OperatingMode
    input_sha256: str
    input_format: str
    input_width: int
    input_height: int
    checkpoint_name: str
    checkpoint_sha256: str
    runtime_device: str
    settings: dict[str, bool | float | int]

    @classmethod
    def create(
        cls,
        *,
        analysis_id: str,
        release_id: str,
        operating_mode: OperatingMode,
        input_sha256: str,
        input_format: str,
        input_width: int,
        input_height: int,
        checkpoint_name: str,
        checkpoint_sha256: str,
        runtime_device: str,
        settings: dict[str, bool | float | int],
    ) -> AnalysisProvenance:
        return cls(
            analysis_uuid=str(uuid4()),
            analysis_id=analysis_id,
            created_at_utc=datetime.now(UTC).isoformat(timespec="milliseconds"),
            software_version=software_version(),
            release_id=release_id,
            operating_mode=operating_mode,
            input_sha256=input_sha256,
            input_format=input_format,
            input_width=input_width,
            input_height=input_height,
            checkpoint_name=checkpoint_name,
            checkpoint_sha256=checkpoint_sha256,
            runtime_device=runtime_device,
            settings=settings,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> bytes:
        return canonical_json(self.as_dict())


def canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


@dataclass(frozen=True)
class AuditReceipt:
    sequence: int
    record_sha256: str
    previous_record_sha256: str | None


class AuditIntegrityError(RuntimeError):
    """Raised when an existing audit chain has been altered or truncated."""


class AuditStore:
    """Append-only, hash-chained event records for controlled operation."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    @contextmanager
    def _process_lock(self) -> Iterator[None]:
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(
            self.directory / AUDIT_PROCESS_LOCK_NAME,
            os.O_RDWR | os.O_CREAT,
            0o600,
        )
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def _read_head(self) -> tuple[int, str] | None:
        path = self.directory / AUDIT_HEAD_NAME
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_bytes())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AuditIntegrityError("Audit chain head is unreadable or invalid.") from error
        if (
            payload.get("schema_version") != AUDIT_SCHEMA_VERSION
            or not isinstance(payload.get("sequence"), int)
            or not isinstance(payload.get("record_sha256"), str)
        ):
            raise AuditIntegrityError("Audit chain head has an invalid schema.")
        return payload["sequence"], payload["record_sha256"]

    def _verify_chain_unlocked(self) -> tuple[int, str | None]:
        previous: str | None = None
        sequence = 0
        for expected_sequence, record in enumerate(
            sorted(self.directory.glob("*.json")), start=1
        ):
            prefix, separator, filename_digest = record.stem.partition("_")
            if not separator or not prefix.isdigit() or int(prefix) != expected_sequence:
                raise AuditIntegrityError(
                    f"Audit record sequence is invalid at: {record.name}"
                )
            encoded = record.read_bytes()
            digest = sha256_bytes(encoded)
            if digest != filename_digest:
                raise AuditIntegrityError(f"Audit record digest mismatch: {record.name}")
            try:
                payload = json.loads(encoded)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise AuditIntegrityError(
                    f"Audit record is not valid JSON: {record.name}"
                ) from error
            if payload.get("schema_version") != AUDIT_SCHEMA_VERSION:
                raise AuditIntegrityError(f"Audit record schema is invalid: {record.name}")
            if payload.get("sequence") != expected_sequence:
                raise AuditIntegrityError(f"Audit record sequence is invalid: {record.name}")
            if payload.get("previous_record_sha256") != previous:
                raise AuditIntegrityError(f"Audit chain is broken at: {record.name}")
            previous = digest
            sequence = expected_sequence

        stored_head = self._read_head()
        if sequence == 0:
            if stored_head is not None:
                raise AuditIntegrityError("Audit chain head exists without records.")
        elif stored_head != (sequence, previous):
            raise AuditIntegrityError("Audit chain head does not match the final record.")
        return sequence, previous

    def _write_head(self, sequence: int, digest: str) -> None:
        encoded = canonical_json(
            {
                "record_sha256": digest,
                "schema_version": AUDIT_SCHEMA_VERSION,
                "sequence": sequence,
            }
        )
        temporary = self.directory / f".{uuid4()}.head.tmp"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.directory / AUDIT_HEAD_NAME)
        finally:
            temporary.unlink(missing_ok=True)

    def _fsync_directory(self) -> None:
        descriptor = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def ensure_ready(self) -> str | None:
        with AUDIT_LOCK, self._process_lock():
            _, chain_head = self._verify_chain_unlocked()
            self._probe_writable()
            return chain_head

    def _probe_writable(self) -> None:
        probe = self.directory / f".{uuid4()}.probe"
        descriptor = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
            probe.unlink(missing_ok=True)
        self._fsync_directory()

    def verify_chain(self) -> str | None:
        with AUDIT_LOCK, self._process_lock():
            _, digest = self._verify_chain_unlocked()
            return digest

    def append(self, event: dict[str, Any]) -> AuditReceipt:
        with AUDIT_LOCK, self._process_lock():
            sequence, previous = self._verify_chain_unlocked()
            next_sequence = sequence + 1
            payload = {
                "event": event,
                "previous_record_sha256": previous,
                "schema_version": AUDIT_SCHEMA_VERSION,
                "sequence": next_sequence,
            }
            encoded = canonical_json(payload)
            digest = sha256_bytes(encoded)
            destination = self.directory / f"{next_sequence:020d}_{digest}.json"
            temporary = self.directory / f".{uuid4()}.tmp"
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
                temporary.replace(destination)
                self._fsync_directory()
                self._write_head(next_sequence, digest)
                self._fsync_directory()
            finally:
                temporary.unlink(missing_ok=True)
            return AuditReceipt(next_sequence, digest, previous)
