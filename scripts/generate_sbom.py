from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4


class SbomGenerationError(RuntimeError):
    """Raised when the locked dependency audit cannot produce acceptable evidence."""


@dataclass(frozen=True)
class SbomReceipt:
    schema_version: int
    generated_at_utc: str
    generator: str
    requirements_path: str
    requirements_sha256: str
    sbom_path: str
    sbom_sha256: str
    component_count: int
    vulnerability_count: int
    audit_exit_code: int
    release_acceptable: bool


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write(path: Path, content: bytes) -> None:
    temporary = path.parent / f".{uuid4()}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def validate_sbom(path: Path) -> tuple[int, int]:
    try:
        payload = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SbomGenerationError("Generated SBOM is missing or invalid JSON.") from error
    if payload.get("bomFormat") != "CycloneDX" or not isinstance(
        payload.get("specVersion"), str
    ):
        raise SbomGenerationError("Generated document is not a CycloneDX SBOM.")
    components = payload.get("components")
    if not isinstance(components, list) or not components:
        raise SbomGenerationError("Generated SBOM contains no components.")
    vulnerabilities = payload.get("vulnerabilities", [])
    if not isinstance(vulnerabilities, list):
        raise SbomGenerationError("Generated SBOM vulnerability data is invalid.")
    return len(components), len(vulnerabilities)


def generate_sbom(
    requirements: Path,
    output: Path,
    cache_dir: Path,
    *,
    overwrite: bool = False,
) -> SbomReceipt:
    requirements = requirements.resolve()
    output = output.resolve()
    if not requirements.is_file():
        raise SbomGenerationError(f"Requirements lock does not exist: {requirements}")
    if output == requirements:
        raise SbomGenerationError("SBOM output must not overwrite the requirements lock.")
    if output.exists() and not overwrite:
        raise SbomGenerationError(f"SBOM output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    temporary = output.parent / f".{uuid4()}.sbom.tmp"
    command = [
        sys.executable,
        "-m",
        "pip_audit",
        "--requirement",
        str(requirements),
        "--require-hashes",
        "--disable-pip",
        "--strict",
        "--format",
        "cyclonedx-json",
        "--output",
        str(temporary),
        "--cache-dir",
        str(cache_dir),
        "--progress-spinner",
        "off",
    ]
    result = subprocess.run(command, check=False)
    try:
        component_count, vulnerability_count = validate_sbom(temporary)
        atomic_write(output, temporary.read_bytes())
    finally:
        temporary.unlink(missing_ok=True)

    receipt = SbomReceipt(
        schema_version=1,
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        generator=f"pip-audit {version('pip-audit')}",
        requirements_path=str(requirements),
        requirements_sha256=sha256_file(requirements),
        sbom_path=str(output),
        sbom_sha256=sha256_file(output),
        component_count=component_count,
        vulnerability_count=vulnerability_count,
        audit_exit_code=result.returncode,
        release_acceptable=result.returncode == 0 and vulnerability_count == 0,
    )
    receipt_path = output.with_suffix(f"{output.suffix}.receipt.json")
    atomic_write(
        receipt_path,
        json.dumps(asdict(receipt), indent=2, sort_keys=True).encode("utf-8") + b"\n",
    )
    if not receipt.release_acceptable:
        raise SbomGenerationError(
            "SBOM was generated, but the vulnerability audit did not pass; release is blocked."
        )
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a CycloneDX SBOM and vulnerability-audit receipt from requirements.lock"
        )
    )
    parser.add_argument("--requirements", type=Path, default=Path("requirements.lock"))
    parser.add_argument(
        "--output", type=Path, default=Path("outputs_v2/release/sbom.cdx.json")
    )
    parser.add_argument(
        "--cache-dir", type=Path, default=Path("outputs_v2/cache/pip-audit")
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        receipt = generate_sbom(
            args.requirements,
            args.output,
            args.cache_dir,
            overwrite=args.overwrite,
        )
    except (OSError, SbomGenerationError) as error:
        raise SystemExit(f"SBOM RELEASE CHECK FAILED: {error}") from error
    print(
        f"SBOM PASSED: components={receipt.component_count} "
        f"sha256={receipt.sbom_sha256}"
    )


if __name__ == "__main__":
    main()
