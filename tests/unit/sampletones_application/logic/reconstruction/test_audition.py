from typing import Final, List, Optional

import numpy as np
import pytest

from sampletones_application.constants.instruments import AUDITION_GENERATOR, AUDITION_TICKS
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.reconstruction.audition import InstrumentAuditionLogic
from sampletones_application.view_model.reconstruction.waveform import (
    InstrumentWaveformViewModel,
)
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorName
from sampletones_core.features.envelope import Envelope
from sampletones_core.performance.audition import audition_audio, audition_ticks
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument

REFERENCE_PITCH: Final[int] = 60
REFERENCE_PERIOD: Final[int] = 8


class _Editor:
    """A tab holding one instrument, or none, which is all an audition reads of it."""

    def __init__(self, instrument: Optional[Instrument]) -> None:
        self._instrument = instrument

    @property
    def instrument(self) -> Optional[Instrument]:
        return self._instrument


def _instrument() -> Instrument:
    return Instrument(
        name="lead",
        envelopes=InstrumentEnvelopes(
            volume=Envelope[int](items=(15, 12)),
            arpeggio=Envelope[int](items=(0, 4)),
            duty_cycle=Envelope[int](items=(2,)),
        ),
        initial_pitch=REFERENCE_PITCH,
        initial_period=REFERENCE_PERIOD,
    )


@pytest.fixture
def controller() -> ProjectController:
    return ProjectController(ProjectManager())


def _logic(instrument: Optional[Instrument], controller: ProjectController) -> InstrumentAuditionLogic:
    return InstrumentAuditionLogic(_Editor(instrument), controller)


def _expected(
    instrument: Instrument,
    controller: ProjectController,
    channel_name: ChannelName,
    pitch: int,
) -> np.ndarray:
    settings = controller.project.settings
    config = Config().with_library(
        nes_frequency=settings.nes_frequency,
        sample_rate=settings.sample_rate,
    )
    audio = audition_audio(
        instrument,
        channel_name,
        config,
        pitch=pitch,
        ticks=audition_ticks(instrument, cap=AUDITION_TICKS),
    )
    assert audio is not None
    return audio


class TestTheWaveformTheCardDraws:
    def test_a_voice_is_first_heard_and_drawn_on_the_pulse(
        self,
        controller: ProjectController,
    ) -> None:
        assert AUDITION_GENERATOR is GeneratorName.PULSE

        logic = _logic(_instrument(), controller)
        drawn: List[Optional[InstrumentWaveformViewModel]] = []
        logic.on_waveform_changed = drawn.append

        logic.refresh()

        assert drawn[-1] is not None
        assert drawn[-1].channel_name is ChannelName.PULSE1

    def test_the_open_voice_is_drawn_at_the_pitch_it_stands_at(
        self,
        controller: ProjectController,
    ) -> None:
        """The card shows the voice as it is, at the pitch it is measured against."""
        instrument = _instrument()
        logic = _logic(instrument, controller)
        drawn: List[Optional[InstrumentWaveformViewModel]] = []
        logic.on_waveform_changed = drawn.append

        logic.refresh()

        expected = _expected(instrument, controller, ChannelName.PULSE1, REFERENCE_PITCH)
        assert drawn[-1] is not None
        assert np.array_equal(drawn[-1].audio, expected)

    def test_choosing_a_generator_redraws_the_voice_as_that_one(
        self,
        controller: ProjectController,
    ) -> None:
        logic = _logic(_instrument(), controller)
        drawn: List[Optional[InstrumentWaveformViewModel]] = []
        logic.on_waveform_changed = drawn.append

        logic.set_generator(GeneratorName.NOISE)

        assert drawn[-1] is not None
        assert drawn[-1].channel_name is ChannelName.NOISE

    def test_the_voice_is_drawn_under_its_own_name_and_frame_length(
        self,
        controller: ProjectController,
    ) -> None:
        instrument = _instrument()
        logic = _logic(instrument, controller)
        drawn: List[Optional[InstrumentWaveformViewModel]] = []
        logic.on_waveform_changed = drawn.append

        logic.refresh()

        settings = controller.project.settings
        config = Config().with_library(
            nes_frequency=settings.nes_frequency,
            sample_rate=settings.sample_rate,
        )
        assert drawn[-1] is not None
        assert drawn[-1].name == "lead"
        assert drawn[-1].frame_length == config.frame_length
        sounded = audition_ticks(instrument, cap=AUDITION_TICKS)
        assert drawn[-1].audio.shape == (sounded * config.frame_length,)

    def test_a_tab_holding_a_recording_leaves_the_card_to_it(
        self,
        controller: ProjectController,
    ) -> None:
        logic = _logic(None, controller)
        drawn: List[Optional[InstrumentWaveformViewModel]] = []
        logic.on_waveform_changed = drawn.append

        logic.refresh()

        assert drawn == [None]

    def test_a_voice_writing_no_envelope_draws_nothing(
        self,
        controller: ProjectController,
    ) -> None:
        logic = _logic(Instrument(name="silent"), controller)
        drawn: List[Optional[InstrumentWaveformViewModel]] = []
        logic.on_waveform_changed = drawn.append

        logic.refresh()

        assert drawn == [None]
