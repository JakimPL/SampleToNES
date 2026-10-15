from typing import Final, List, Optional

import numpy as np
import pytest

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.keys import KeyArming, ReconstructionKeys
from sampletones_application.logic.shared.live import LiveKeysLogic, LiveNoteSource, LivePosition
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.logic.shared.preview_player import PreviewPlayer
from sampletones_core.audio import silence
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.performance import velocity_level
from sampletones_core.performance.audition import audition_audio
from sampletones_core.project.voices.instrument import Instrument
from sampletones_shared.constants.music import OCTAVE_OFFSET, OCTAVE_SEMITONES
from tests.suite.audio.output import FakeAudioOutput

from .conftest import Tab, lead

KEY_Z: Final[int] = 90
KEY_X: Final[int] = 88
SEMITONE_G: Final[int] = 7
NOTE_A: Final[int] = 69
SOFT: Final[int] = 30
LINGER_SECONDS: Final[float] = 0.0
HEARD_TICKS: Final[int] = 6
POSITION: Final[int] = 735
HARD: Final[int] = 127
OUTPUT_RATE: Final[int] = 44100
BLOCK: Final[int] = 4096


class Marks:
    """Where the plot card's mark was put, as the tab's follower puts it."""

    def __init__(self) -> None:
        self.positions: List[Optional[int]] = []

    def __call__(self, position: Optional[int]) -> None:
        self.positions.append(position)


@pytest.fixture
def output() -> FakeAudioOutput:
    return FakeAudioOutput()


@pytest.fixture
def live_keys(output: FakeAudioOutput) -> LiveKeysLogic:
    return LiveKeysLogic(PreviewPlayer(output), post=_now, failed=_unexpected, linger_seconds=LINGER_SECONDS)


@pytest.fixture
def marks() -> Marks:
    return Marks()


@pytest.fixture
def keys(arming: KeyArming, live_keys: LiveKeysLogic, session: SessionManager, marks: Marks) -> ReconstructionKeys:
    return ReconstructionKeys(arming, live_keys, session, follower=marks)


def _now(delivery: object) -> None:
    raise AssertionError(f"the keys posted {delivery!r} where nothing should fail")


def _unexpected(error: Exception) -> None:
    raise AssertionError(f"a key failed: {error}")


def _heard(output: FakeAudioOutput, sample_rate: int, ticks: int, frame_length: int) -> np.ndarray:
    """The first ``ticks`` ticks the latest key's playback sounds, its stream opened at ``sample_rate``."""
    source = output.claim(output.latest).source
    assert isinstance(source, LiveNoteSource)
    source.begin(sample_rate, _unexpected)
    block = silence(ticks * frame_length)
    source.read_into(block)
    return block


def _sounds_at(instrument: Instrument, controller: ProjectController, pitch: int, output: FakeAudioOutput) -> None:
    config = controller.project.settings.synthesis_config()
    expected = audition_audio(instrument, ChannelName.PULSE1, config, pitch=pitch, ticks=HEARD_TICKS)
    assert expected is not None
    heard = _heard(output, config.sample_rate, HEARD_TICKS, config.frame_length)
    np.testing.assert_allclose(heard, expected, atol=1e-6)


class TestAComputerKey:
    """A piano key plays the voice in front of the tab at the note the octave in force and the key name."""

    def test_a_key_sounds_the_instrument_at_the_note_it_names(
        self,
        keys: ReconstructionKeys,
        instrument: Instrument,
        controller: ProjectController,
        session: SessionManager,
        output: FakeAudioOutput,
    ) -> None:
        keys.press_computer_key(KEY_Z, SEMITONE_G)

        _sounds_at(instrument, controller, (session.octave + OCTAVE_OFFSET) * OCTAVE_SEMITONES + SEMITONE_G, output)

    def test_the_octave_in_force_moves_the_note_the_same_key_sounds(
        self,
        keys: ReconstructionKeys,
        instrument: Instrument,
        controller: ProjectController,
        session: SessionManager,
        output: FakeAudioOutput,
    ) -> None:
        session.set_octave(session.octave + 1)

        keys.press_computer_key(KEY_Z, SEMITONE_G)

        _sounds_at(instrument, controller, (session.octave + OCTAVE_OFFSET) * OCTAVE_SEMITONES + SEMITONE_G, output)

    def test_a_key_plays_as_a_preview(
        self,
        keys: ReconstructionKeys,
        instrument: Instrument,
        output: FakeAudioOutput,
    ) -> None:
        keys.press_computer_key(KEY_Z, SEMITONE_G)

        assert output.claim(output.latest).rank == PlaybackPriority.PREVIEW

    def test_a_key_pressed_as_a_voice_opens_plays_it(
        self,
        keys: ReconstructionKeys,
        arming: KeyArming,
        tab: Tab,
        controller: ProjectController,
        output: FakeAudioOutput,
    ) -> None:
        """A key arms what the tab shows as it is pressed, so a voice opened by the same frame plays."""
        arming.arm()
        tab.instrument = controller.add_instrument(lead())

        keys.press_computer_key(KEY_Z, SEMITONE_G)

        assert output.playbacks

    def test_a_key_with_nothing_in_front_plays_nothing(
        self,
        keys: ReconstructionKeys,
        tab: Tab,
        controller: ProjectController,
        output: FakeAudioOutput,
    ) -> None:
        keys.press_computer_key(KEY_Z, SEMITONE_G)

        assert output.playbacks == []
        tab.instrument = controller.add_instrument(lead())
        keys.press_computer_key(KEY_Z, SEMITONE_G)
        assert len(output.playbacks) == 1

    def test_a_lifted_key_ends_the_instrument_it_held(
        self,
        keys: ReconstructionKeys,
        instrument: Instrument,
        output: FakeAudioOutput,
    ) -> None:
        keys.press_computer_key(KEY_Z, SEMITONE_G)
        source = output.claim(output.latest).source
        assert isinstance(source, LiveNoteSource)
        source.begin(OUTPUT_RATE, _unexpected)

        keys.lift_computer_key(KEY_Z)

        assert source.read_into(silence(OUTPUT_RATE)).frames < OUTPUT_RATE

    def test_a_lift_of_another_key_leaves_the_note_held(
        self,
        keys: ReconstructionKeys,
        instrument: Instrument,
        output: FakeAudioOutput,
    ) -> None:
        keys.press_computer_key(KEY_Z, SEMITONE_G)
        source = output.claim(output.latest).source
        assert isinstance(source, LiveNoteSource)
        source.begin(OUTPUT_RATE, _unexpected)

        keys.lift_computer_key(KEY_X)

        assert source.read_into(silence(OUTPUT_RATE)).frames == OUTPUT_RATE


class TestAMidiKey:
    """A MIDI key plays the voice armed last at its own note, as hard as it was struck."""

    def test_a_midi_key_sounds_the_instrument_at_its_own_note(
        self,
        keys: ReconstructionKeys,
        arming: KeyArming,
        instrument: Instrument,
        controller: ProjectController,
        session: SessionManager,
        output: FakeAudioOutput,
    ) -> None:
        session.set_midi_settings(None, velocity_sets_volume=False)
        arming.arm()

        keys.press(NOTE_A, SOFT)

        _sounds_at(instrument, controller, NOTE_A, output)

    def test_a_soft_midi_key_plays_quieter_where_velocity_sets_the_volume(
        self,
        keys: ReconstructionKeys,
        arming: KeyArming,
        instrument: Instrument,
        output: FakeAudioOutput,
    ) -> None:
        arming.arm()

        keys.press(NOTE_A, SOFT)

        assert velocity_level(ChannelName.PULSE1, SOFT) < MAX_VOLUME
        source = output.claim(output.latest).source
        assert isinstance(source, LiveNoteSource)
        source.begin(OUTPUT_RATE, _unexpected)
        soft = silence(BLOCK)
        source.read_into(soft)
        keys.lift(NOTE_A)
        keys.press(NOTE_A, HARD)
        hard = silence(BLOCK)
        source.read_into(hard)
        assert np.abs(soft).max() < np.abs(hard).max()

    def test_a_midi_key_waits_for_the_render_thread_to_arm_a_voice(
        self,
        keys: ReconstructionKeys,
        arming: KeyArming,
        instrument: Instrument,
        output: FakeAudioOutput,
    ) -> None:
        """A MIDI key arrives off the render thread, so it plays only what a frame armed."""
        keys.press(NOTE_A, SOFT)

        assert output.playbacks == []
        arming.arm()
        keys.press(NOTE_A, SOFT)
        assert len(output.playbacks) == 1


class TestThePlotMark:
    def test_a_key_struck_on_the_tab_marks_the_plot(
        self,
        keys: ReconstructionKeys,
        live_keys: LiveKeysLogic,
        instrument: Instrument,
        output: FakeAudioOutput,
        marks: Marks,
    ) -> None:
        keys.press_computer_key(KEY_Z, SEMITONE_G)
        playback = output.latest
        source = output.claim(playback).source
        assert isinstance(source, LiveNoteSource)
        source.begin(OUTPUT_RATE, _unexpected)
        (tagged,) = source.read_into(silence(POSITION)).reports
        assert isinstance(tagged.report, LivePosition)

        output.report(playback, tagged.report)

        assert marks.positions == [tagged.report.position]
