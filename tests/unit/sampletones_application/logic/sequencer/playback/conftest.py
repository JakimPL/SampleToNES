from pathlib import Path
from typing import Callable, FrozenSet, Iterable

import numpy as np
import pytest

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.channels import ALL_CHANNELS
from sampletones_application.logic.sequencer.playback.synthesizer import RowSynthesizer
from sampletones_core.configs import Config
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE
from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.reconstructions import Reconstruction


def make_controller() -> ProjectController:
    return ProjectController(ProjectManager())


def all_channels() -> FrozenSet[ChannelName]:
    """The fully audible mask a synthesiser renders under unless a test moves it."""
    return ALL_CHANNELS


def make_synthesizer(
    controller: ProjectController,
    config: Config,
    *,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    active_channels: Callable[[], FrozenSet[ChannelName]] = all_channels,
) -> RowSynthesizer:
    """A synthesiser rendering at ``sample_rate``, standing in for the output a caller supplies."""
    return RowSynthesizer(
        controller,
        config,
        active_channels=active_channels,
        sample_rate=lambda: sample_rate,
    )


def add_sample(
    controller: ProjectController,
    reconstruction: Reconstruction,
    *,
    loop: bool = False,
    name: str = "test",
) -> Sample:
    sample = controller.add_sample(reconstruction, name)
    if loop:
        controller.set_sample_loop(sample.id, loop=True)
    return sample


def place_row(
    controller: ProjectController,
    *,
    channel: ChannelName,
    row_index: int = 0,
    sample_id: str,
    transpose: int | None = None,
    volume: int | None = None,
) -> None:
    pattern_index = controller.project.song.order[0][channel]
    controller.set_row(
        channel,
        pattern_index,
        row_index,
        command=Instrument(sample_id=sample_id, channel_name=channel),
        transpose=transpose,
        volume=volume,
    )


def place_note_off(
    controller: ProjectController,
    *,
    channel: ChannelName,
    row_index: int,
) -> None:
    """Place an explicit note-off command on a channel row."""
    pattern_index = controller.project.song.order[0][channel]
    controller.set_row(channel, pattern_index, row_index, command=NoteOff())


def place_modifier_row(
    controller: ProjectController,
    *,
    channel: ChannelName,
    row_index: int,
    transpose: int | None = None,
    volume: int | None = None,
) -> None:
    """Place a row with only modifiers (no instrument)."""
    pattern_index = controller.project.song.order[0][channel]
    controller.update_row(
        channel,
        pattern_index,
        row_index,
        transpose=transpose,
        volume=volume,
    )


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture
def controller() -> ProjectController:
    return make_controller()


@pytest.fixture
def synthesizer(controller: ProjectController, config: Config) -> RowSynthesizer:
    return make_synthesizer(controller, config)
