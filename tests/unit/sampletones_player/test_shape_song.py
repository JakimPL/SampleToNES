from typing import Final, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.voices.envelopes import ShapeEnvelopes
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.shape import Shape
from sampletones_player.builder import song_from_project

ROWS_PER_PATTERN: Final[int] = 4
VOLUME: Final[Tuple[int, ...]] = (15, 12, 9)
VOLUME_NIBBLE: Final[int] = 0x0F


def _project() -> Project:
    shape = Shape(
        name="Lead",
        envelopes=ShapeEnvelopes(volume=VOLUME, arpeggio=(0, 4, 7), duty_cycle=(1,)),
    )
    project = Project.create(title="Demo", rows_per_pattern=ROWS_PER_PATTERN)
    project.voices.append(shape)
    pattern = project.song[ChannelName.PULSE1].ensure_pattern(0, ROWS_PER_PATTERN)
    pattern.rows[0] = Row(command=NoteOn(voice_id=shape.id))
    project.song.set_order_entry(0, ChannelName.PULSE1, 0)
    return project


class TestAShapeReachesTheConsole:
    """The player reads the same walk the sequencer plays, so a shape needs nothing of its own."""

    def test_a_project_holding_a_shape_compiles(self) -> None:
        song = song_from_project(_project(), loop_tick=None)

        assert song.planes.ticks > 0

    def test_the_compiled_song_sounds_the_shape_on_the_channel_it_was_placed_on(self) -> None:
        song = song_from_project(_project(), loop_tick=None)

        levels = [registers.control & VOLUME_NIBBLE for registers in song.streams.pulse1[: len(VOLUME)]]
        assert levels == list(VOLUME)

    def test_the_channels_it_was_not_placed_on_stay_silent(self) -> None:
        song = song_from_project(_project(), loop_tick=None)

        assert {registers.control & VOLUME_NIBBLE for registers in song.streams.pulse2} == {0}
