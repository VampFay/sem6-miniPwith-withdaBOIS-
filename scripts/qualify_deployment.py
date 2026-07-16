from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

SHA256 = re.compile(r"^[0-9a-f]{64}$")


class QualificationError(ValueError):
    """Raised when a deployed controlled runtime fails operational qualification."""


def validate_url(value: str, allow_http_localhost: bool) -> str:
    parsed = urlsplit(value)
    local = parsed.hostname in {"127.0.0.1", "localhost"}
    if parsed.scheme != "https" and not (
        allow_http_localhost and parsed.scheme == "http" and local
    ):
        raise QualificationError("Qualification URL must use HTTPS.")
    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise QualificationError("Qualification URL must be a simple origin without credentials.")
    return value.rstrip("/")


def require_status(response: httpx.Response, expected: int, operation: str) -> None:
    if response.status_code != expected:
        raise QualificationError(
            f"{operation} returned {response.status_code}, expected {expected}."
        )


def require_security_headers(response: httpx.Response) -> None:
    required = {
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        "referrer-policy": "no-referrer",
        "cache-control": "no-store",
    }
    missing = [
        f"{name}={value}"
        for name, value in required.items()
        if response.headers.get(name) != value
    ]
    if missing or not response.headers.get("x-request-id"):
        raise QualificationError(
            f"API response security headers are incomplete: {missing or ['x-request-id']}"
        )


def object_payload(response: httpx.Response, operation: str) -> dict[str, Any]:
    try:
        value = response.json()
    except json.JSONDecodeError as error:
        raise QualificationError(f"{operation} did not return JSON.") from error
    if not isinstance(value, dict):
        raise QualificationError(f"{operation} did not return a JSON object.")
    return value


def verify_ready(payload: dict[str, Any], release_id: str, checkpoint_sha256: str) -> None:
    expected = {
        "status": "ready",
        "ready": True,
        "operating_mode": "controlled",
        "release_id": release_id,
        "checkpoint_sha256": checkpoint_sha256,
    }
    mismatches = [key for key, value in expected.items() if payload.get(key) != value]
    if mismatches:
        raise QualificationError(f"Readiness identity mismatch: {mismatches}")
    if not isinstance(payload.get("checkpoint"), str) or "/" in payload["checkpoint"]:
        raise QualificationError("Readiness checkpoint must expose only an artifact filename.")
    if not isinstance(payload.get("postprocessing"), dict):
        raise QualificationError("Readiness did not expose locked postprocessing settings.")


def verify_analysis(
    payload: dict[str, Any],
    *,
    analysis_id: str,
    release_id: str,
    checkpoint_sha256: str,
    input_sha256: str,
) -> dict[str, Any]:
    provenance = payload.get("provenance")
    receipt = payload.get("audit_receipt")
    if payload.get("analysis_id") != analysis_id or not isinstance(provenance, dict):
        raise QualificationError("Analysis identity or provenance is missing.")
    expected = {
        "analysis_id": analysis_id,
        "release_id": release_id,
        "operating_mode": "controlled",
        "checkpoint_sha256": checkpoint_sha256,
        "input_sha256": input_sha256,
    }
    mismatches = [key for key, value in expected.items() if provenance.get(key) != value]
    if mismatches:
        raise QualificationError(f"Analysis provenance mismatch: {mismatches}")
    if not isinstance(receipt, dict) or not isinstance(receipt.get("sequence"), int):
        raise QualificationError("Analysis has no valid audit receipt.")
    for key in ("record_sha256", "previous_record_sha256"):
        value = receipt.get(key)
        if value is not None and (not isinstance(value, str) or not SHA256.fullmatch(value)):
            raise QualificationError(f"Audit receipt has invalid {key}.")
    return {
        "analysis_id": analysis_id,
        "request_id": provenance.get("request_id"),
        "input_sha256": input_sha256,
        "checkpoint_sha256": checkpoint_sha256,
        "release_id": release_id,
        "audit_receipt": receipt,
    }


def content_type(path: Path) -> str:
    value = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }.get(path.suffix.lower())
    if value is None:
        raise QualificationError("Qualification image must be PNG, JPEG or TIFF.")
    return value


def execute(args: argparse.Namespace) -> dict[str, Any]:
    url = validate_url(args.url, args.allow_http_localhost)
    token = os.getenv(args.token_env, "")
    if len(token) < 32:
        raise QualificationError(
            f"Environment variable {args.token_env} must contain the site service credential."
        )
    image = args.image.read_bytes()
    image_sha256 = hashlib.sha256(image).hexdigest()
    form = {"analysis_id": args.analysis_id}
    files = {"file": (args.image.name, image, content_type(args.image))}
    verify: bool | str = args.ca_bundle if args.ca_bundle else True
    with httpx.Client(base_url=url, timeout=args.timeout, verify=verify) as client:
        live = client.get("/api/live")
        require_status(live, 200, "Liveness")
        require_security_headers(live)
        if object_payload(live, "Liveness") != {"status": "alive"}:
            raise QualificationError("Liveness payload is invalid.")

        ready = client.get("/api/ready")
        require_status(ready, 200, "Readiness")
        require_security_headers(ready)
        verify_ready(object_payload(ready, "Readiness"), args.release_id, args.checkpoint_sha256)

        unauthenticated = client.post("/api/analyze", data=form, files=files)
        require_status(unauthenticated, 401, "Unauthenticated analysis")
        invalid_token = "0" * 32 if token != "0" * 32 else "1" * 32
        wrong_token = client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {invalid_token}", "X-Actor-ID": args.actor_id},
            data=form,
            files=files,
        )
        require_status(wrong_token, 401, "Wrong-token analysis")
        missing_actor = client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {token}"},
            data=form,
            files=files,
        )
        require_status(missing_actor, 400, "Missing-actor analysis")
        analyzed = client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {token}", "X-Actor-ID": args.actor_id},
            data=form,
            files=files,
        )
        require_status(analyzed, 200, "Authorized analysis")
        require_security_headers(analyzed)
        summary = verify_analysis(
            object_payload(analyzed, "Authorized analysis"),
            analysis_id=args.analysis_id,
            release_id=args.release_id,
            checkpoint_sha256=args.checkpoint_sha256,
            input_sha256=image_sha256,
        )
    return {
        "schema_version": 1,
        "qualification": "controlled-runtime-oq-smoke",
        "result": "passed",
        "url": url,
        **summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Qualify a deployed controlled runtime")
    parser.add_argument("image", type=Path)
    parser.add_argument("--url", required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    parser.add_argument("--token-env", default="ATTNDIST_QUALIFICATION_TOKEN")
    parser.add_argument("--actor-id", default="site-qualification")
    parser.add_argument("--analysis-id", default="SITE-OQ-SMOKE")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--ca-bundle")
    parser.add_argument("--allow-http-localhost", action="store_true")
    args = parser.parse_args()
    if not SHA256.fullmatch(args.checkpoint_sha256):
        parser.error("--checkpoint-sha256 must be 64 lowercase hex characters")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def main() -> None:
    args = parse_args()
    try:
        result = execute(args)
    except (OSError, httpx.HTTPError, QualificationError) as error:
        raise SystemExit(f"DEPLOYMENT QUALIFICATION FAILED: {error}") from error
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
