from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import torch

from src.training.trainer import Trainer


def test_resume_loads_checkpoint_on_cpu(monkeypatch) -> None:
    checkpoint = {
        "format_version": 2,
        "artifact_type": "attn-dist-training",
        "epoch": 3,
        "model_state_dict": {},
        "optimizer_state_dict": {},
        "scheduler_state_dict": {},
        "scaler_state_dict": {},
        "best_iou": 0.75,
        "stale_epochs": 2,
        "torch_rng_state": torch.get_rng_state(),
        "numpy_rng_state": np.random.get_state(),
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

    load.assert_called_once_with(Path("last_model.pt"), map_location="cpu", weights_only=False)
    assert trainer.start_epoch == 4
    assert trainer.best_iou == 0.75
    assert trainer.stale_epochs == 2
