from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest
import torch

from scripts.build_model_evidence import ModelEvidenceError, build_evidence


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path, *, license_name: str = "CC BY-NC-SA 4.0") -> tuple[Path, Path, Path]:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    array = data_dir / "images.npy"
    array.write_bytes(b"fixture-array")
    manifest = {
        "format": "prepared-pannuke-v2",
        "sample_count": 1,
        "fold_counts": {"1": 1},
        "arrays": [{"file": "images.npy", "sha256": _digest(array)}],
    }
    (data_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (data_dir / "provenance.json").write_text(
        json.dumps({"source": "fixture", "revision": "abc", "license": license_name}),
        encoding="utf-8",
    )
    checkpoint = tmp_path / "model.pt"
    torch.save(
        {
            "artifact_type": "attn-dist-inference",
            "format_version": 2,
            "epoch": 1,
            "config": {
                "epochs": 3,
                "train_fold": 1,
                "validation_fold": 2,
                "test_fold": 3,
            },
            "validation": {"iou": 0.5},
            "dataset": {"manifest_sha256": _digest(data_dir / "manifest.json")},
            "model_state_dict": {"weight": torch.ones(1)},
        },
        checkpoint,
    )
    metrics = tmp_path / "metrics.csv"
    with metrics.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["epoch", "validation_loss", "validation_dice", "validation_iou"],
        )
        writer.writeheader()
        writer.writerow(
            {"epoch": 1, "validation_loss": 0.8, "validation_dice": 0.6, "validation_iou": 0.5}
        )
        writer.writerow(
            {"epoch": 2, "validation_loss": 0.7, "validation_dice": 0.7, "validation_iou": 0.6}
        )
    return data_dir, checkpoint, metrics


def test_build_evidence_blocks_incomplete_noncommercial_research(tmp_path: Path) -> None:
    data_dir, checkpoint, metrics = _fixture(tmp_path)
    evidence = build_evidence(data_dir, checkpoint, metrics)
    assert evidence["release_disposition"] == "blocked"
    assert evidence["dataset"]["commercially_restricted"] is True
    assert evidence["training_complete"] is False
    assert evidence["training_metrics"]["best_validation_iou"]["epoch"] == 2
    assert len(evidence["release_blockers"]) >= 6


def test_build_evidence_rejects_dataset_digest_mismatch(tmp_path: Path) -> None:
    data_dir, checkpoint, metrics = _fixture(tmp_path)
    (data_dir / "images.npy").write_bytes(b"tampered")
    with pytest.raises(ModelEvidenceError, match="digest mismatch"):
        build_evidence(data_dir, checkpoint, metrics)
