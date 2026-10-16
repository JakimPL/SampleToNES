from typing import Final, Optional

import numpy as np

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.playback.synthesizer import RowSynthesizer
from sampletones_application.logic.shared.synthesis import ChannelBank, EngineRates, synthesize_tick
from sampletones_core.audio import clip_audio_inplace, silence
from sampletones_core.configs import Config
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE
from sampletones_core.constants.enums import ALL_CHANNELS, ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features.envelope import Envelope
from sampletones_core.performance import LiveNote
from sampletones_core.project.patterns.pitch import Note, RowPitch, Step
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.voice import VoiceUnion
from sampletones_core.timing import SONG_TICK_BOUNDS, SongTiming
from tests.suite.performance import make_pulse_reconstruction

CHANNEL: Final[ChannelName] = ChannelName.PULSE1
REFERENCE_PITCH: Final[int] = 60
STRUCK_PITCH: Final[int] = 67
OTHER_PITCH: Final[int] = 64
STEP: Final[int] = 5
QUIET_LEVEL: Final[int] = 8
SAMPLE_FRAMES: Final[int] = 40


def _instrument() -> Instrument:
    """A voice whose every frame differs, so a tick out of place shows in the audio."""
    return Instrument(
        name="lead",
        envelopes=InstrumentEnvelopes(
            volume=Envelope[int](items=(15, 13, 11, 9), loop_point=2),
            arpeggio=Envelope[int](items=(0, 4, 7)),
            duty_cycle=Envelope[int](items=(2, 1)),
        ),
        initial_pitch=REFERENCE_PITCH,
    )


def _row_of(controller: ProjectController, voice: VoiceUnion, pitch: RowPitch, volume: Optional[int]) -> np.ndarray:
    """The audio the song's first row sounds while it holds ``voice`` at ``pitch`` on :data:`CHANNEL`."""
    pattern_index = controller.project.song.order[0][CHANNEL]
    controller.set_row(CHANNEL, pattern_index, 0, command=NoteOn(voice_id=voice.id), pitch=pitch, volume=volume)
    synthesizer = RowSynthesizer(
        controller,
        Config(),
        active_channels=lambda: ALL_CHANNELS,
        sample_rate=lambda: DEFAULT_SAMPLE_RATE,
    )
    audio, _ = synthesizer.render_row()
    return audio


def _live(controller: ProjectController, note: LiveNote) -> np.ndarray:
    """The audio ``note`` sounds through the shared synthesis for the ticks the song's first row lasts."""
    project = controller.project
    bank = ChannelBank(Config(), EngineRates.from_project(project, DEFAULT_SAMPLE_RATE))
    ticks = SongTiming.from_project(project, bounds=SONG_TICK_BOUNDS).row_ticks(0, 0)
    blocks = []
    for tick in range(ticks):
        frame_length = bank.clock.frame_length(tick)
        block = silence(frame_length)
        for channel_name, instruction in note.tick().items():
            block += synthesize_tick(bank.generator(channel_name), instruction, frame_length)

        blocks.append(clip_audio_inplace(block))

    return np.concatenate(blocks)


def _struck(voice: VoiceUnion, pitch: RowPitch, level: int) -> LiveNote:
    return LiveNote.of_voice(voice, pitches={CHANNEL: pitch}, levels={CHANNEL: level})


class TestALiveNoteSoundsWhatARowSounds:
    """A key sounds what a row holding the key's pitch sounds: the same frames through the same generators.

    A held instrument struck at a note, and a sample stepped from its root, render the samples the song
    renders for a one-row pattern holding that pitch, and a live note at another pitch renders other audio.
    """

    def test_a_held_instrument_sounds_as_a_row_holding_its_note(self) -> None:
        controller = ProjectController(ProjectManager())
        instrument = controller.add_instrument(_instrument())

        row = _row_of(controller, instrument, Note(value=STRUCK_PITCH), None)
        live = _live(controller, _struck(instrument, Note(value=STRUCK_PITCH), MAX_VOLUME))

        assert np.any(row)
        np.testing.assert_array_equal(live, row)

    def test_a_sample_stepped_from_its_root_sounds_as_a_row_holding_the_step(self) -> None:
        controller = ProjectController(ProjectManager())
        sample = controller.add_sample(make_pulse_reconstruction(pitch=REFERENCE_PITCH, count=SAMPLE_FRAMES), "take")

        row = _row_of(controller, sample, Step(value=STEP), None)
        live = _live(controller, _struck(sample, Step(value=STEP), MAX_VOLUME))

        assert np.any(row)
        np.testing.assert_array_equal(live, row)

    def test_a_level_sounds_as_a_row_stating_that_volume(self) -> None:
        controller = ProjectController(ProjectManager())
        instrument = controller.add_instrument(_instrument())

        row = _row_of(controller, instrument, Note(value=STRUCK_PITCH), QUIET_LEVEL)
        live = _live(controller, _struck(instrument, Note(value=STRUCK_PITCH), QUIET_LEVEL))

        assert np.any(row)
        np.testing.assert_array_equal(live, row)

    def test_a_live_note_at_another_pitch_sounds_otherwise(self) -> None:
        controller = ProjectController(ProjectManager())
        instrument = controller.add_instrument(_instrument())

        row = _row_of(controller, instrument, Note(value=STRUCK_PITCH), None)
        live = _live(controller, _struck(instrument, Note(value=OTHER_PITCH), MAX_VOLUME))

        assert len(live) == len(row)
        assert not np.array_equal(live, row)
