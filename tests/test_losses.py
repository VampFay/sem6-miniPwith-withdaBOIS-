import pytest
import torch

from src.models.attn_dist_unet import ModelOutput
from src.utils.losses import AttnDistComboLoss, ForegroundDistanceLoss


def test_sigmoid_distance_activation_is_bounded() -> None:
    criterion = ForegroundDistanceLoss(activation="sigmoid")
    activated = criterion.activate(torch.tensor([-100.0, 0.0, 100.0]))

    assert torch.all((activated >= 0.0) & (activated <= 1.0))
    assert activated[1].item() == pytest.approx(0.5)


def test_background_area_does_not_dominate_distance_loss() -> None:
    criterion = ForegroundDistanceLoss(activation="identity", background_weight=0.25)
    small_prediction = torch.tensor([[[[0.5, 0.25]]]])
    small_target = torch.tensor([[[[1.0, 0.0]]]])
    small_mask = torch.tensor([[[[1.0, 0.0]]]])
    large_prediction = torch.cat(
        (small_prediction[..., :1], small_prediction[..., 1:].expand(1, 1, 1, 63)), dim=-1
    )
    large_target = torch.cat(
        (small_target[..., :1], small_target[..., 1:].expand(1, 1, 1, 63)), dim=-1
    )
    large_mask = torch.cat(
        (small_mask[..., :1], small_mask[..., 1:].expand(1, 1, 1, 63)), dim=-1
    )

    small = criterion(small_prediction, small_target, small_mask)
    large = criterion(large_prediction, large_target, large_mask)

    for small_component, large_component in zip(small, large, strict=True):
        assert small_component.item() == pytest.approx(large_component.item())


def test_foreground_distance_loss_has_finite_gradients_for_empty_regions() -> None:
    criterion = ForegroundDistanceLoss(activation="sigmoid")
    for mask_value in (0.0, 1.0):
        prediction = torch.zeros((1, 1, 4, 4), requires_grad=True)
        target = torch.full_like(prediction, mask_value)
        mask = torch.full_like(prediction, mask_value)

        total, foreground, background = criterion(prediction, target, mask)
        total.backward()

        assert all(torch.isfinite(value) for value in (total, foreground, background))
        assert prediction.grad is not None
        assert torch.isfinite(prediction.grad).all()


def test_combo_loss_reports_every_component() -> None:
    logits = torch.zeros((1, 1, 4, 4), requires_grad=True)
    output = ModelOutput(mask_logits=logits, distance=logits)
    target = torch.zeros_like(logits)

    losses = AttnDistComboLoss()(output, target, target)
    losses.total.backward()

    assert losses.total.item() > 0
    assert losses.distance.item() == pytest.approx(
        losses.distance_foreground.item() + 0.1 * losses.distance_background.item()
    )
    assert torch.isfinite(logits.grad).all()
