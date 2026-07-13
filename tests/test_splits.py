import numpy as np

from src.training.data import official_fold_split


def test_official_fold_split_is_disjoint() -> None:
    folds = np.asarray([1, 2, 3, 1, 2, 3], dtype=np.uint8)
    train, validation, test = official_fold_split(folds, 1, 2, 3)
    assert not set(train) & set(validation)
    assert not set(train) & set(test)
    assert not set(validation) & set(test)
    np.testing.assert_array_equal(train, [0, 3])
    np.testing.assert_array_equal(validation, [1, 4])
    np.testing.assert_array_equal(test, [2, 5])
