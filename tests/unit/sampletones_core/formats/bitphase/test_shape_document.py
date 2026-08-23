from typing import Final, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.formats.bitphase.builder import project_to_bitphase
from sampletones_core.formats.bitphase.specification.instruments import LOOP_FROM_START
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.voices.envelopes import ShapeEnvelopes
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.shape import Shape

ROWS_PER_PATTERN: Final[int] = 4
VOLUME: Final[Tuple[int, ...]] = (15, 12, 9)
ARPEGGIO: Final[Tuple[int, ...]] = (0, 4, 7)


def _project(*channels: ChannelName, loop_point: int | None = None) -> Tuple[Project, Shape]:
    shape = Shape(
        name="Lead",
        envelopes=ShapeEnvelopes(volume=VOLUME, arpeggio=ARPEGGIO, duty_cycle=(1,)),
        loop_point=loop_point,
    )
    project = Project.create(title="Demo", rows_per_pattern=ROWS_PER_PATTERN)
    project.voices.append(shape)
    for channel in channels:
        pattern = project.song[channel].ensure_pattern(0, ROWS_PER_PATTERN)
        pattern.rows[0] = Row(command=NoteOn(voice_id=shape.id))
        project.song.set_order_entry(0, channel, 0)

    return project, shape


class TestAShapeReachesTheDocument:
    def test_each_channel_it_sounds_on_takes_an_instrument_of_its_own(self) -> None:
        """Bitphase bakes registers per tick, so a channel's rows carry that channel's reading."""
        project, _ = _project(ChannelName.PULSE1, ChannelName.NOISE)

        document = project_to_bitphase(project)

        assert len(document.instruments) == len(ChannelName.items())

    def test_every_instrument_runs_the_ticks_its_envelopes_describe(self) -> None:
        project, _ = _project(ChannelName.PULSE1)

        document = project_to_bitphase(project)

        assert all(len(instrument.rows) == len(VOLUME) for instrument in document.instruments)

    def test_a_looping_shape_returns_to_its_loop_point(self) -> None:
        project, _ = _project(ChannelName.PULSE1, loop_point=1)

        document = project_to_bitphase(project)

        assert all(instrument.loop == 1 for instrument in document.instruments)

    def test_a_one_shot_rests_on_its_final_row(self) -> None:
        project, _ = _project(ChannelName.PULSE1)

        document = project_to_bitphase(project)

        assert all(instrument.loop == len(instrument.rows) - 1 for instrument in document.instruments)

    def test_the_table_carries_the_shapes_contour(self) -> None:
        project, _ = _project(ChannelName.PULSE1)

        document = project_to_bitphase(project)

        assert any(tuple(table.rows) == ARPEGGIO for table in document.tables)

    def test_the_document_is_written_without_a_loop_past_its_rows(self) -> None:
        project, _ = _project(ChannelName.PULSE1, loop_point=LOOP_FROM_START)

        document = project_to_bitphase(project)

        assert all(instrument.loop < len(instrument.rows) for instrument in document.instruments)
