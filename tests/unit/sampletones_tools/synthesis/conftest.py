from typing import Final

import numpy as np
import pytest

SAMPLE_RATE: Final[int] = 22050
SIGNAL_SECONDS: Final[float] = 1.0
SEED: Final[int] = 1234


@pytest.fixture(scope="session")
def sample_rate() -> int:
    return SAMPLE_RATE


@pytest.fixture(scope="session")
def time_axis(sample_rate: int) -> np.ndarray:
    return np.arange(int(SIGNAL_SECONDS * sample_rate), dtype=np.float64) / sample_rate


@pytest.fixture
def generator() -> np.random.Generator:
    return np.random.default_rng(SEED)
