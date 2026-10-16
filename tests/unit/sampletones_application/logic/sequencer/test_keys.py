from typing import Final

import numpy as np
import pytest

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.channels import SequencerChannelsLogic
from sampletones_application.logic.sequencer.keys import SequencerKeys
from sampletones_application.logic.sequencer.tracker import SequencerTrackerLogic
from sampletones_application.logic.shared.live import Keyboard, LiveKey, LiveKeysLogic, LiveNoteSource
from sampletones_application.logic.shared.preview_player import PreviewPlayer
from sampletones_core.audio import silence
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.performance.audition import audition_audio
from sampletones_core.project.patterns.pitch import Note
from sampletones_core.project.voices.instrument import Instrument
from tests.suite.audio.output import FakeAudioOutput
from tests.suite.live import held_instrument
from tests.suite.sequencer import sample_reconstruction

ROW: Final[int] = 2
NOTE_G: Final[int] = 67
QUIET: Final[int] = 4
LINGER_SECONDS: Final[float] = 0.0
HEARD_TICKS: Final[int] = 6
OUTPUT_RATE: Final[int] = 44100
BLOCK: Final[int] = 4096
KEY: Final[LiveKey] = LiveKey(keyboard=Keyboard.MIDI, number=NOTE_G)


def _unexpected(error: Exception) -> None:
    raise AssertionError(f"a key failed: {error}")


def _posted(delivery: object) -> None:
    raise AssertionError(f"the keys posted {delivery!r} where nothing should fail")


@pytest.fixture
def controller() -> ProjectController:
    return ProjectController(ProjectManager())


@pytest.fixture
def tracker(controller: ProjectController) -> SequencerTrackerLogic:
    return SequencerTrackerLogic(controller)


@pytest.fixture
def channels() -> SequencerChannelsLogic:
    return SequencerChannelsLogic()


@pytest.fixture
def output() -> FakeAudioOutput:
    return FakeAudioOutput()


@pytest.fixture
def keys(
    tracker: SequencerTrackerLogic,
    channels: SequencerChannelsLogic,
    controller: ProjectController,
    output: FakeAudioOutput,
) -> SequencerKeys:
    live_keys = LiveKeysLogic(PreviewPlayer(output), post=_posted, failed=_unexpected, linger_seconds=LINGER_SECONDS)
    return SequencerKeys(tracker, channels, controller, live_keys)


@pytest.fixture
def instrument(controller: ProjectController) -> Instrument:
    return controller.add_instrument(held_instrument())


def _source(output: FakeAudioOutput) -> LiveNoteSource:
    source = output.claim(output.latest).source
    assert isinstance(source, LiveNoteSource)
    source.begin(OUTPUT_RATE, _unexpected)
    return source


def _heard(output: FakeAudioOutput, frames: int) -> np.ndarray:
    block = silence(frames)
    _source(output).read_into(block)
    return block


class TestTheRowAKeyWroteSounds:
    """A key's row sounds the voice it names at its pitch and volume, as the song plays the row."""

    def test_an_instrument_row_sounds_at_the_pitch_it_states(
        self,
        keys: SequencerKeys,
        tracker: SequencerTrackerLogic,
        controller: ProjectController,
        instrument: Instrument,
        output: FakeAudioOutput,
    ) -> None:
        tracker.write_cell(ROW, ChannelName.PULSE1, instrument.id, Note(value=NOTE_G), None, None)

        keys.strike(KEY, ROW, ChannelName.PULSE1)

        config = controller.project.settings.synthesis_config()
        expected = audition_audio(instrument, ChannelName.PULSE1, config, pitch=NOTE_G, ticks=HEARD_TICKS)
        assert expected is not None
        source = output.claim(output.latest).source
        assert isinstance(source, LiveNoteSource)
        source.begin(config.sample_rate, _unexpected)
        heard = silence(HEARD_TICKS * config.frame_length)
        source.read_into(heard)
        np.testing.assert_allclose(heard, expected, atol=1e-6)

    def test_the_rows_volume_sets_the_level(
        self,
        keys: SequencerKeys,
        tracker: SequencerTrackerLogic,
        instrument: Instrument,
        output: FakeAudioOutput,
    ) -> None:
        tracker.write_cell(ROW, ChannelName.PULSE1, instrument.id, Note(value=NOTE_G), QUIET, None)
        keys.strike(KEY, ROW, ChannelName.PULSE1)
        quiet = _heard(output, BLOCK)
        keys.lift(KEY)

        tracker.write_cell(ROW, ChannelName.PULSE1, None, None, MAX_VOLUME, None)
        keys.strike(KEY, ROW, ChannelName.PULSE1)
        loud = _heard(output, BLOCK)

        assert np.abs(quiet).max() < np.abs(loud).max()

    def test_a_sample_in_the_sample_column_sounds_every_channel_it_reaches(
        self,
        keys: SequencerKeys,
        tracker: SequencerTrackerLogic,
        channels: SequencerChannelsLogic,
        controller: ProjectController,
        output: FakeAudioOutput,
    ) -> None:
        sample = controller.add_sample(sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]), name="lead")
        tracker.write_cell(ROW, None, sample.id, Note(value=NOTE_G), None, None)
        keys.strike(KEY, ROW, None)
        both = _heard(output, BLOCK)
        keys.lift(KEY)

        channels.toggle(ChannelName.TRIANGLE)
        keys.strike(KEY, ROW, None)
        pulse_alone = _heard(output, BLOCK)

        assert np.any(both != pulse_alone)
        assert np.any(pulse_alone)

    def test_a_lift_ends_the_instrument_it_held(
        self,
        keys: SequencerKeys,
        tracker: SequencerTrackerLogic,
        instrument: Instrument,
        output: FakeAudioOutput,
    ) -> None:
        tracker.write_cell(ROW, ChannelName.PULSE1, instrument.id, Note(value=NOTE_G), None, None)
        keys.strike(KEY, ROW, ChannelName.PULSE1)
        source = _source(output)

        keys.lift(KEY)

        assert source.read_into(silence(OUTPUT_RATE)).frames < OUTPUT_RATE


class TestARowThatSoundsNothing:
    """A row starting no note, a channel the reader silenced, and a voice the project lost all stay silent."""

    def test_a_pitch_moving_a_note_it_did_not_start_sounds_nothing(
        self,
        keys: SequencerKeys,
        tracker: SequencerTrackerLogic,
        instrument: Instrument,
        output: FakeAudioOutput,
    ) -> None:
        tracker.write_cell(ROW, ChannelName.PULSE1, None, Note(value=NOTE_G), None, None)

        keys.strike(KEY, ROW, ChannelName.PULSE1)

        assert output.playbacks == []
        tracker.write_cell(ROW, ChannelName.PULSE1, instrument.id, None, None, None)
        keys.strike(KEY, ROW, ChannelName.PULSE1)
        assert len(output.playbacks) == 1

    def test_a_silenced_channel_sounds_nothing(
        self,
        keys: SequencerKeys,
        tracker: SequencerTrackerLogic,
        channels: SequencerChannelsLogic,
        instrument: Instrument,
        output: FakeAudioOutput,
    ) -> None:
        tracker.write_cell(ROW, ChannelName.PULSE1, instrument.id, Note(value=NOTE_G), None, None)
        channels.toggle(ChannelName.PULSE1)

        keys.strike(KEY, ROW, ChannelName.PULSE1)

        assert output.playbacks == []
        channels.toggle(ChannelName.PULSE1)
        keys.strike(KEY, ROW, ChannelName.PULSE1)
        assert len(output.playbacks) == 1

    def test_a_row_on_another_channel_sounds_nothing_here(
        self,
        keys: SequencerKeys,
        tracker: SequencerTrackerLogic,
        instrument: Instrument,
        output: FakeAudioOutput,
    ) -> None:
        tracker.write_cell(ROW, ChannelName.PULSE2, instrument.id, Note(value=NOTE_G), None, None)

        keys.strike(KEY, ROW, ChannelName.PULSE1)

        assert output.playbacks == []
