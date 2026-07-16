from __future__ import annotations

import pytest

from scripts.qualify_deployment import (
    QualificationError,
    validate_url,
    verify_analysis,
    verify_ready,
)


def test_qualification_url_requires_https_except_explicit_localhost() -> None:
    with pytest.raises(QualificationError, match="HTTPS"):
        validate_url("http://lab.example", False)
    assert validate_url("http://127.0.0.1:8000/", True) == "http://127.0.0.1:8000"


def test_qualification_verifies_runtime_and_analysis_identity() -> None:
    digest = "a" * 64
    verify_ready(
        {
            "status": "ready",
            "ready": True,
            "operating_mode": "controlled",
            "release_id": "release-1",
            "checkpoint": "model.pt",
            "checkpoint_sha256": digest,
            "postprocessing": {"mask_threshold": 0.5},
        },
        "release-1",
        digest,
    )
    summary = verify_analysis(
        {
            "analysis_id": "SITE-OQ-SMOKE",
            "provenance": {
                "analysis_id": "SITE-OQ-SMOKE",
                "release_id": "release-1",
                "operating_mode": "controlled",
                "checkpoint_sha256": digest,
                "input_sha256": "b" * 64,
            },
            "audit_receipt": {
                "sequence": 1,
                "record_sha256": "c" * 64,
                "previous_record_sha256": None,
            },
        },
        analysis_id="SITE-OQ-SMOKE",
        release_id="release-1",
        checkpoint_sha256=digest,
        input_sha256="b" * 64,
    )
    assert summary["audit_receipt"]["sequence"] == 1


def test_qualification_rejects_provenance_mismatch() -> None:
    with pytest.raises(QualificationError, match="provenance mismatch"):
        verify_analysis(
            {
                "analysis_id": "A",
                "provenance": {
                    "analysis_id": "A",
                    "release_id": "wrong",
                    "operating_mode": "controlled",
                    "checkpoint_sha256": "a" * 64,
                    "input_sha256": "b" * 64,
                },
                "audit_receipt": {
                    "sequence": 1,
                    "record_sha256": "c" * 64,
                    "previous_record_sha256": None,
                },
            },
            analysis_id="A",
            release_id="expected",
            checkpoint_sha256="a" * 64,
            input_sha256="b" * 64,
        )
