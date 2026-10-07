from typing import Callable, Iterator, TypeAlias

import pytest

from sampletones_application.utils.callbacks.failures import UnhandledFailures
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.gui.modal_queue import ModalQueue
from sampletones_application.utils.gui.palette.palette import PaletteBindings
from sampletones_application.utils.gui.render_thread import reset_render_thread
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
def frame_callbacks() -> Iterator[None]:
    """Gives each test no callbacks waiting for a frame.

    The callbacks wait in a heap that outlives any one context, and a suite renders no frame to run
    them, so each test starts with none and leaves none a later frame count would make due.
    """
    FrameCallbackManager.clear()
    yield
    FrameCallbackManager.clear()


@pytest.fixture(autouse=True)
def unhandled_failures() -> Iterator[None]:
    """Gives each test a failure channel with no presenter attached.

    An application built by a test attaches its presenter to the process-wide channel, together with
    the thread hook, so each test starts with failures logged alone and leaves the hook it found.
    """
    UnhandledFailures.detach()
    yield
    UnhandledFailures.detach()


@pytest.fixture(autouse=True)
def render_thread() -> Iterator[None]:
    """Gives each test a context no run has claimed.

    The thread a run claims outlives the run, and a test taking an application down leaves it named,
    so each test starts where an interface is built and leaves the next one the same.
    """
    reset_render_thread()
    yield
    reset_render_thread()


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
