from typing import Callable, Iterator, TypeAlias

import pytest

from sampletones_application.utils.gui.palette.palette import PaletteBindings
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction
from tests.suite.sequencer import sample_reconstruction

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
        return sample_reconstruction([ChannelName.PULSE1])

    return build
