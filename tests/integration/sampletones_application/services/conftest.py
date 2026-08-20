from pathlib import Path

import numpy as np
import pytest

from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_application.logic.reconstruction.feature import FeatureData
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MIN_PITCH
from sampletones_core.exporters import Features, PulseExporter
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from tests.suite.application import synchronous_executor, synchronous_queue

__all__ = ["synchronous_executor", "synchronous_queue"]


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
    return PulseExporter().to_features(
        pulse_instructions,
        PulseExporter.derive_initial_pitch(pulse_instructions),
        (),
    )


@pytest.fixture
def minimal_reconstruction(default_config, pulse_instructions) -> Reconstruction:
    length = 256
    return Reconstruction.create(
        approximation=np.zeros(length, dtype=np.float32),
        approximations={ChannelName.PULSE1: np.zeros(length, dtype=np.float32)},
        instructions={ChannelName.PULSE1: pulse_instructions},
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
        stem_audios=(),
        feature_data=feature_data,
        filepath=Path("/dev/null"),
        name="null",
    )
