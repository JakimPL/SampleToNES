from pathlib import Path
from typing import Final, Sequence

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction

SAMPLE_LENGTH: Final[int] = 64


def sample_reconstruction(generators: Sequence[GeneratorName]) -> Reconstruction:
    """A reconstruction carrying one instruction on each of ``generators``.

    The channels a reconstruction covers are what a sample governs in the sequencer, so this is
    the knob a sequencer test turns: the audio itself is silent, since what is under test is which
    channels a sample reaches and not how it sounds.
    """
    instructions = {
        generator: [
            PulseInstruction(
                on=True,
                pitch=60,
                volume=8,
                duty_cycle=0,
            )
        ]
        for generator in generators
    }
    approximations = {generator: np.zeros(SAMPLE_LENGTH, dtype=np.float32) for generator in generators}
    return Reconstruction.create(
        approximation=np.zeros(SAMPLE_LENGTH, dtype=np.float32),
        approximations=approximations,
        instructions=instructions,
        config=Config(),
        coefficient=1.0,
        audio_filepath=Path("/dev/null"),
    )
