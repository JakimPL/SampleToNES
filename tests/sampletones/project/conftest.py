from pathlib import Path

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction


@pytest.fixture
def reconstruction_factory():
    def build() -> Reconstruction:
        length = 64
        instructions = [PulseInstruction(on=True, pitch=60, volume=8, duty_cycle=0)]
        return Reconstruction.create(
            approximation=np.zeros(length, dtype=np.float32),
            approximations={GeneratorName.PULSE1: np.zeros(length, dtype=np.float32)},
            instructions={GeneratorName.PULSE1: instructions},
            config=Config(),
            coefficient=1.0,
            audio_filepath=Path("/dev/null"),
        )

    return build
