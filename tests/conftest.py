from typing import Callable, Iterator, TypeAlias

import pytest

from sampletones_application.utils.gui.modal_queue import ModalQueue
from sampletones_application.utils.gui.palette.palette import PaletteBindings
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction
from tests.suite.sequencer import sample_reconstruction

ReconstructionFactory: TypeAlias = Callable[[], Reconstruction]


@pytest.fixture(autouse=True)
def modal_queue() -> Iterator[None]:
    """Gives each test an empty modal line.

    The line holds the window standing on the screen and the ones waiting for it, and it outlives
    any one context, so each test starts with the screen free and leaves nothing waiting.
    """
    ModalQueue.clear()
    yield
    ModalQueue.clear()


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
