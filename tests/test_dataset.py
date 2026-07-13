from pathlib import Path

import numpy as np

from src.preprocessing.dataset import PanNukeDataset
from src.preprocessing.instances import merge_instance_channels
from src.preprocessing.transforms import training_transforms


def create_dataset_files(directory: Path, samples: int = 3) -> tuple[Path, Path, Path]:
    images = np.zeros((samples, 32, 32, 3), dtype=np.uint8)
    images[:, 8:24, 8:24] = 255
    instances = np.zeros((samples, 32, 32), dtype=np.uint16)
    instances[:, 8:24, 8:24] = 1
    distances = np.zeros((samples, 32, 32), dtype=np.float16)
    distances[:, 8:24, 8:24] = 0.8
    paths = directory / "images.npy", directory / "instances.npy", directory / "distances.npy"
    for path, array in zip(paths, (images, instances, distances), strict=True):
        np.save(path, array)
    return paths


def test_dataset_returns_aligned_training_targets(tmp_path: Path) -> None:
    image_path, instance_path, distance_path = create_dataset_files(tmp_path)
    dataset = PanNukeDataset(
        image_path,
        instance_path,
        distance_path,
        transforms=training_transforms(),
        stain_aug=False,
    )

    item = dataset[0]

    assert item["image"].shape == (3, 32, 32)
    assert item["mask"].shape == (1, 32, 32)
    assert item["dist"].shape == (1, 32, 32)
    assert item["instances"].shape == (32, 32)
    np.testing.assert_array_equal(item["mask"][0] > 0, item["dist"][0] > 0)
    np.testing.assert_array_equal(item["mask"][0] > 0, item["instances"] > 0)


def test_dataset_indices_create_real_independent_subsets(tmp_path: Path) -> None:
    paths = create_dataset_files(tmp_path, samples=5)
    dataset = PanNukeDataset(*paths, indices=[4, 1])

    assert len(dataset) == 2
    assert dataset[0]["index"].item() == 4
    assert dataset[1]["index"].item() == 1


def test_merge_instance_channels_ignores_background_and_assigns_global_ids() -> None:
    mask = np.zeros((8, 8, 6), dtype=np.uint16)
    mask[1:3, 1:3, 0] = 4
    mask[4:6, 4:6, 2] = 4
    mask[..., 5] = 99

    merged = merge_instance_channels(mask)

    assert set(np.unique(merged)) == {0, 1, 2}
    assert merged[1, 1] != merged[4, 4]
    assert merged[0, 0] == 0
