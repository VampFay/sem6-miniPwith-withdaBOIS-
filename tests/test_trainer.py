from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
import torch

from src.training.trainer import Trainer


def test_resume_loads_checkpoint_on_cpu(monkeypatch) -> None:
    numpy_rng_state = np.random.get_state()
    checkpoint = {
        "format_version": 3,
        "artifact_type": "attn-dist-training",
        "epoch": 3,
        "model_state_dict": {},
        "optimizer_state_dict": {},
        "scheduler_state_dict": {},
        "scaler_state_dict": {},
        "best_iou": 0.75,
        "stale_epochs": 2,
        "torch_rng_state": torch.get_rng_state(),
        "numpy_rng_state": {
            "bit_generator": numpy_rng_state[0],
            "state": torch.from_numpy(numpy_rng_state[1].copy()),
            "position": numpy_rng_state[2],
            "has_gauss": numpy_rng_state[3],
            "cached_gaussian": numpy_rng_state[4],
        },
    }
    load = Mock(return_value=checkpoint)
    monkeypatch.setattr(torch, "load", load)

    trainer = Trainer.__new__(Trainer)
    trainer.config = SimpleNamespace(device=torch.device("mps"))
    trainer.model = Mock()
    trainer.optimizer = Mock()
    trainer.scheduler = Mock()
    trainer.scaler = Mock()

    trainer.resume(Path("last_model.pt"))

    load.assert_called_once_with(Path("last_model.pt"), map_location="cpu", weights_only=True)
    assert trainer.start_epoch == 4
    assert trainer.best_iou == 0.75
    assert trainer.stale_epochs == 2


def test_training_checkpoint_is_atomic_and_uses_weights_only_safe_rng_schema(
    tmp_path,
) -> None:
    trainer = Trainer.__new__(Trainer)
    trainer.model = Mock()
    trainer.model.state_dict.return_value = {}
    trainer.optimizer = Mock()
    trainer.optimizer.state_dict.return_value = {}
    trainer.scheduler = Mock()
    trainer.scheduler.state_dict.return_value = {}
    trainer.scaler = Mock()
    trainer.scaler.state_dict.return_value = {}
    trainer.config = Mock()
    trainer.config.as_serializable_dict.return_value = {}
    trainer.best_iou = 0.5
    trainer.stale_epochs = 1

    path = tmp_path / "training.pt"
    trainer.save_training_checkpoint(path, epoch=2)
    restored = torch.load(path, map_location="cpu", weights_only=True)

    assert restored["format_version"] == 3
    assert isinstance(restored["numpy_rng_state"]["state"], torch.Tensor)
    assert not list(tmp_path.glob("*.tmp"))


def test_resume_rejects_legacy_unsafe_checkpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        torch,
        "load",
        Mock(return_value={"format_version": 2, "artifact_type": "attn-dist-training"}),
    )
    trainer = Trainer.__new__(Trainer)

    with pytest.raises(ValueError, match="Unsupported checkpoint format: 2"):
        trainer.resume(Path("legacy.pt"))
