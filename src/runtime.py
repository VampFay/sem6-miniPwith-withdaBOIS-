from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlsplit

OperatingMode = Literal["research", "controlled"]
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RELEASE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class RuntimeConfigurationError(ValueError):
    """Raised when controlled-operation safeguards are incomplete."""


def parse_allowed_origins(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(origin.strip() for origin in value.split(",") if origin.strip()))


def is_secure_origin(origin: str) -> bool:
    try:
        parsed = urlsplit(origin)
        _ = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname not in {None, "*"}
        and not any(character.isspace() for character in origin)
        and parsed.username is None
        and parsed.password is None
        and parsed.path == ""
        and parsed.query == ""
        and parsed.fragment == ""
    )


@dataclass(frozen=True)
class RuntimeConfig:
    operating_mode: OperatingMode
    release_id: str
    approved_checkpoint_sha256: str | None
    audit_dir: Path | None
    api_token: str | None
    allowed_origins: tuple[str, ...]

    @classmethod
    def from_environment(cls) -> RuntimeConfig:
        mode = os.getenv("ATTNDIST_OPERATING_MODE", "research").strip().lower()
        if mode not in {"research", "controlled"}:
            raise RuntimeConfigurationError(
                "ATTNDIST_OPERATING_MODE must be 'research' or 'controlled'."
            )
        digest = os.getenv("ATTNDIST_APPROVED_CHECKPOINT_SHA256", "").strip().lower() or None
        audit_value = os.getenv("ATTNDIST_AUDIT_DIR", "").strip()
        config = cls(
            operating_mode=cast(OperatingMode, mode),
            release_id=os.getenv("ATTNDIST_RELEASE_ID", "development").strip(),
            approved_checkpoint_sha256=digest,
            audit_dir=Path(audit_value).expanduser() if audit_value else None,
            api_token=os.getenv("ATTNDIST_API_TOKEN", "").strip() or None,
            allowed_origins=parse_allowed_origins(
                os.getenv("ATTNDIST_ALLOWED_ORIGINS", "")
            ),
        )
        config.validate()
        return config

    @property
    def is_controlled(self) -> bool:
        return self.operating_mode == "controlled"

    def validate(self) -> None:
        if not RELEASE_PATTERN.fullmatch(self.release_id):
            raise RuntimeConfigurationError("ATTNDIST_RELEASE_ID has an invalid format.")
        if self.approved_checkpoint_sha256 is not None and not SHA256_PATTERN.fullmatch(
            self.approved_checkpoint_sha256
        ):
            raise RuntimeConfigurationError(
                "ATTNDIST_APPROVED_CHECKPOINT_SHA256 must be a lowercase SHA-256 digest."
            )
        if not self.is_controlled:
            return
        missing: list[str] = []
        if self.release_id == "development":
            missing.append("a non-development release ID")
        if self.approved_checkpoint_sha256 is None:
            missing.append("an approved checkpoint digest")
        if self.audit_dir is None:
            missing.append("an audit directory")
        if self.api_token is None or len(self.api_token) < 32:
            missing.append("an API token of at least 32 characters")
        if not self.allowed_origins:
            missing.append("at least one explicit HTTPS allowed origin")
        if missing:
            raise RuntimeConfigurationError(
                "Controlled mode requires " + ", ".join(missing) + "."
            )
        invalid_origins = [
            origin for origin in self.allowed_origins if not is_secure_origin(origin)
        ]
        if invalid_origins:
            raise RuntimeConfigurationError(
                "Controlled ATTNDIST_ALLOWED_ORIGINS must contain only exact HTTPS origins."
            )


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def read_verified_checkpoint(path: Path, expected_sha256: str | None) -> tuple[bytes, str]:
    content = path.read_bytes()
    digest = sha256_bytes(content)
    if expected_sha256 is not None and digest != expected_sha256:
        raise RuntimeConfigurationError("Installed checkpoint does not match the approved digest.")
    return content, digest
