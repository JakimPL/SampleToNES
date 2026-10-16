from pathlib import Path
from typing import Dict, Final, List, Optional

from sampletones_core.configs import Config
from sampletones_core.constants.enums import DEFAULT_CHANNELS, ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features.envelope import Envelope
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TriangleInstruction
from sampletones_core.performance import LiveNote
from sampletones_core.performance.modifiers import pulse_volume
from sampletones_core.project.patterns.pitch import Note, RowPitch, Step
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion
from sampletones_core.reconstructions import Reconstruction
from tests.suite.performance import make_pulse_reconstruction
from tests.suite.stems import single_entry_stems_data

REFERENCE_PITCH: Final[int] = 60
STRUCK_PITCH: Final[int] = 67
STEP: Final[int] = 5
QUIET_LEVEL: Final[int] = 8
WRITTEN_TICKS: Final[int] = 3
SAMPLE_FRAMES: Final[int] = 4
LONGER_FRAMES: Final[int] = 6
HELD_TICKS: Final[int] = 200
PULSE: Final[ChannelName] = ChannelName.PULSE1
TRIANGLE: Final[ChannelName] = ChannelName.TRIANGLE


def _instrument(volume: Envelope[int]) -> Instrument:
    """A voice writing a volume and an arpeggio on every channel, measured against :data:`REFERENCE_PITCH`."""
    return Instrument(
        name="lead",
        envelopes=InstrumentEnvelopes(volume=volume, arpeggio=Envelope[int](items=(0, 4, 7))),
        initial_pitch=REFERENCE_PITCH,
    )


def _decaying() -> Instrument:
    return _instrument(Envelope[int](items=(15, 12, 9)))


def _sample(frames: int) -> Sample:
    return Sample(name="take", reconstruction=make_pulse_reconstruction(pitch=REFERENCE_PITCH, count=frames))


def _two_channel_sample() -> Sample:
    """A recording of :data:`SAMPLE_FRAMES` frames on Pulse 1 and :data:`LONGER_FRAMES` on the triangle."""
    instructions: Dict[ChannelName, List[InstructionUnion]] = {
        PULSE: [PulseInstruction(on=True, pitch=REFERENCE_PITCH, volume=MAX_VOLUME, duty_cycle=0)] * SAMPLE_FRAMES,
        TRIANGLE: [TriangleInstruction(on=True, pitch=REFERENCE_PITCH)] * LONGER_FRAMES,
    }
    reconstruction = Reconstruction.create(
        instructions=instructions,
        config=Config(),
        coefficient=1.0,
        audio_filepath=(Path("/dev/null"),),
        stems_data=single_entry_stems_data(list(DEFAULT_CHANNELS), instructions),
    )
    return Sample(name="two", reconstruction=reconstruction)


def _struck(voice: VoiceUnion, pitch: RowPitch, *, level: int = MAX_VOLUME) -> LiveNote:
    return LiveNote.of_voice(voice, pitches={PULSE: pitch}, levels={PULSE: level})


def _sounded(note: LiveNote, ticks: int, channel_name: ChannelName = PULSE) -> List[Optional[InstructionUnion]]:
    return [note.tick()[channel_name] for _ in range(ticks)]


def _pitches(note: LiveNote, ticks: int) -> List[int]:
    return [instruction.pitch for instruction in _sounded(note, ticks) if isinstance(instruction, PulseInstruction)]


def _volumes(note: LiveNote, ticks: int) -> List[int]:
    return [instruction.volume for instruction in _sounded(note, ticks) if isinstance(instruction, PulseInstruction)]


class TestAStrike:
    """A strike starts the voice at the step the key's pitch asks of its reference, at the level asked for."""

    def test_an_instrument_sounds_at_the_note_the_key_names(self) -> None:
        assert _pitches(_struck(_decaying(), Note(value=STRUCK_PITCH)), WRITTEN_TICKS) == [
            STRUCK_PITCH,
            STRUCK_PITCH + 4,
            STRUCK_PITCH + 7,
        ]

    def test_an_instrument_struck_at_its_reference_sounds_its_frames_as_written(self) -> None:
        instrument = _decaying()

        sounded = _sounded(_struck(instrument, Note(value=REFERENCE_PITCH)), WRITTEN_TICKS)

        assert sounded == instrument.instructions(PULSE)

    def test_a_sample_moves_by_the_step_from_its_root(self) -> None:
        assert (
            _pitches(_struck(_sample(SAMPLE_FRAMES), Step(value=STEP)), SAMPLE_FRAMES)
            == [REFERENCE_PITCH + STEP] * SAMPLE_FRAMES
        )

    def test_a_sample_at_no_step_sounds_as_it_was_recorded(self) -> None:
        assert (
            _pitches(_struck(_sample(SAMPLE_FRAMES), Step(value=0)), SAMPLE_FRAMES) == [REFERENCE_PITCH] * SAMPLE_FRAMES
        )

    def test_a_quieter_level_scales_every_frame(self) -> None:
        volumes = _volumes(_struck(_decaying(), Note(value=STRUCK_PITCH), level=QUIET_LEVEL), WRITTEN_TICKS)

        assert volumes == [pulse_volume(volume, QUIET_LEVEL) for volume in (15, 12, 9)]

    def test_the_full_level_leaves_every_frame_as_written(self) -> None:
        assert _volumes(_struck(_decaying(), Note(value=STRUCK_PITCH)), WRITTEN_TICKS) == [15, 12, 9]

    def test_the_note_sounds_on_the_channels_the_key_names(self) -> None:
        note = _struck(_decaying(), Note(value=STRUCK_PITCH))

        assert note.channel_names == (PULSE,)

    def test_a_channel_the_voice_has_no_frames_on_stays_out_of_the_note(self) -> None:
        note = LiveNote.of_voice(
            _sample(SAMPLE_FRAMES),
            pitches={PULSE: Step(value=0), TRIANGLE: Step(value=0)},
            levels={PULSE: MAX_VOLUME, TRIANGLE: MAX_VOLUME},
        )

        assert note.channel_names == (PULSE,)


class TestAHeldNote:
    """A held instrument sounds past its written frames the way a held tracker row sounds it."""

    def test_each_dimension_holds_its_last_item_once_the_written_frames_run_out(self) -> None:
        assert _volumes(_struck(_decaying(), Note(value=REFERENCE_PITCH)), WRITTEN_TICKS + 2) == [15, 12, 9, 9, 9]

    def test_a_dimension_circles_from_the_item_it_repeats_from(self) -> None:
        note = _struck(_instrument(Envelope[int](items=(15, 12, 9), loop_point=1)), Note(value=REFERENCE_PITCH))

        assert _volumes(note, 6) == [15, 12, 9, 12, 9, 12]

    def test_an_instrument_that_never_releases_sounds_on_while_held(self) -> None:
        note = _struck(_instrument(Envelope[int](items=(15,), loop_point=0)), Note(value=REFERENCE_PITCH))

        sounded = _sounded(note, HELD_TICKS)

        assert all(instruction is not None for instruction in sounded)
        assert not note.finished


class TestTheNoteEnding:
    """A release silences the note on every channel, and a note runs out once every channel has."""

    def test_a_release_silences_every_channel_at_once(self) -> None:
        note = LiveNote.of_voice(
            _decaying(),
            pitches={PULSE: Note(value=STRUCK_PITCH), TRIANGLE: Note(value=STRUCK_PITCH)},
            levels={PULSE: MAX_VOLUME, TRIANGLE: MAX_VOLUME},
        )
        sounding = note.tick()

        note.release()

        assert all(instruction is not None for instruction in sounding.values())
        assert note.tick() == {PULSE: None, TRIANGLE: None}
        assert note.finished

    def test_a_sample_runs_out_once_its_frames_are_played(self) -> None:
        note = _struck(_sample(SAMPLE_FRAMES), Step(value=0))

        _sounded(note, SAMPLE_FRAMES - 1)
        sounding = note.finished
        _sounded(note, 1)

        assert not sounding
        assert note.finished
        assert _sounded(note, 1) == [None]

    def test_an_instrument_releasing_at_silence_runs_out_at_its_release(self) -> None:
        note = _struck(_instrument(Envelope[int](items=(15, 9, 0))), Note(value=REFERENCE_PITCH))

        _sounded(note, 2)
        sounding = note.finished
        _sounded(note, 1)

        assert not sounding
        assert note.finished

    def test_a_note_runs_out_once_its_last_channel_has(self) -> None:
        note = LiveNote.of_voice(
            _two_channel_sample(),
            pitches={PULSE: Step(value=0), TRIANGLE: Step(value=0)},
            levels={PULSE: MAX_VOLUME, TRIANGLE: MAX_VOLUME},
        )

        for _ in range(SAMPLE_FRAMES):
            note.tick()
        after_the_pulse = note.finished
        for _ in range(LONGER_FRAMES - SAMPLE_FRAMES):
            note.tick()

        assert not after_the_pulse
        assert note.finished
