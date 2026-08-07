from pathlib import Path
from typing import Callable, Iterator, TypeAlias

import numpy as np
import pytest

from sampletones_application.utils.gui.palette.palette import PaletteBindings
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction

ReconstructionFactory: TypeAlias = Callable[[], Reconstruction]


@pytest.fixture(autouse=True)
def palette_bindings() -> Iterator[None]:
    """Gives each test an empty palette binding registry.

    The registry holds DearPyGui item identifiers and outlives any one context, and a fresh
    context hands out the same identifiers again, so each test starts from nothing and leaves
    nothing that a later one could repaint.
    """
    PaletteBindings.clear()
    yield
    PaletteBindings.clear()


@pytest.fixture
def reconstruction_factory() -> ReconstructionFactory:
    def build() -> Reconstruction:
        length = 64
        instructions = [
            PulseInstruction(
                on=True,
                pitch=60,
                volume=8,
                duty_cycle=0,
            )
        ]
        return Reconstruction.create(
            approximation=np.zeros(length, dtype=np.float32),
            approximations={
                GeneratorName.PULSE1: np.zeros(
                    length,
                    dtype=np.float32,
                )
            },
            instructions={GeneratorName.PULSE1: instructions},
            config=Config(),
            coefficient=1.0,
            audio_filepath=Path("/dev/null"),
        )

    return build
