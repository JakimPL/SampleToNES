from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_application.logic.reconstruction.feature import FeatureData
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.thread import SingleThreadExecutor
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MIN_PITCH
from sampletones_core.exporters import Features, PulseExporter
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction


@pytest.fixture(autouse=True)
def synchronous_queue():
    """Replace CallbackQueue.add with a direct call-through.

    Makes _emit() synchronous so tests do not need a running queue worker thread.
    CallbackQueue.add signature: add(callback, *args, priority=0, delay=0, **kwargs)
    """
    with patch.object(
        CallbackQueue,
        "add",
        side_effect=lambda callback, *args, priority=0, delay=0, **kwargs: callback(*args),
    ):
        yield


@pytest.fixture(autouse=True)
def synchronous_executor():
    """Replace SingleThreadExecutor.execute with a synchronous call.

    Makes background tasks run inline so tests remain deterministic without
    threading.Event barriers. Tests that specifically verify debounce or
    non-preemptive cancellation must override this fixture locally.
    """

    def execute_sync(self: SingleThreadExecutor, target, wait: bool = True) -> bool:
        target()
        return True

    with patch.object(SingleThreadExecutor, "execute", execute_sync):
        yield


@pytest.fixture
def default_config() -> Config:
    return Config()


@pytest.fixture
def pulse_instructions() -> list:
    return [
        PulseInstruction(on=True, pitch=60, volume=8, duty_cycle=0),
        PulseInstruction(on=True, pitch=60, volume=8, duty_cycle=0),
        PulseInstruction(on=True, pitch=60, volume=4, duty_cycle=0),
        PulseInstruction(on=False, pitch=MIN_PITCH, volume=0, duty_cycle=0),
    ]


@pytest.fixture
def pulse_features(pulse_instructions) -> Features:
    return PulseExporter().to_features(pulse_instructions)


@pytest.fixture
def minimal_reconstruction(default_config, pulse_instructions) -> Reconstruction:
    length = 256
    return Reconstruction.create(
        approximation=np.zeros(length, dtype=np.float32),
        approximations={GeneratorName.PULSE1: np.zeros(length, dtype=np.float32)},
        instructions={GeneratorName.PULSE1: pulse_instructions},
        config=default_config,
        coefficient=1.0,
        audio_filepath=Path("/dev/null"),
    )


@pytest.fixture
def reconstruction_data(default_config, minimal_reconstruction) -> ReconstructionData:
    feature_data = FeatureData.load(minimal_reconstruction)
    return ReconstructionData(
        config=default_config,
        reconstruction=minimal_reconstruction,
        original_audio=np.zeros(256, dtype=np.float32),
        feature_data=feature_data,
        filepath=Path("/dev/null"),
        name="null",
    )
