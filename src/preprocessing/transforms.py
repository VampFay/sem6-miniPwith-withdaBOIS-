import albumentations as A


def training_transforms() -> A.Compose:
    return A.Compose(
        [A.HorizontalFlip(p=0.5), A.VerticalFlip(p=0.5), A.RandomRotate90(p=0.5)],
        additional_targets={"distance": "mask", "instances": "mask"},
    )
