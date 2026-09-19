from typing import Final, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.bitphase.builder import project_to_bitphase
from sampletones_core.formats.bitphase.specification.instruments import LOOP_FROM_START
from sampletones_core.formats.bitphase.specification.macros import NesMacroField
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_on import NoteOn

ROWS_PER_PATTERN: Final[int] = 4
VOLUME: Final[Tuple[int, ...]] = (15, 12, 9)
ARPEGGIO: Final[Tuple[int, ...]] = (0, 4, 7)


def _project(*channels: ChannelName, loop_point: int | None = None) -> Tuple[Project, Instrument]:
    instrument = Instrument(
        name="Lead",
        envelopes=InstrumentEnvelopes(
            volume=Envelope(items=VOLUME, loop_point=loop_point),
            arpeggio=Envelope(items=ARPEGGIO, loop_point=loop_point),
            duty_cycle=Envelope(items=(1,)),
        ),
    )
    project = Project.create(title="Demo", rows_per_pattern=ROWS_PER_PATTERN)
    project.voices.append(instrument)
    for channel in channels:
        pattern = project.song[channel].ensure_pattern(0, ROWS_PER_PATTERN)
        pattern.rows[0] = Row(command=NoteOn(voice_id=instrument.id))
        project.song.set_order_entry(0, channel, 0)

    return project, instrument


class TestAnInstrumentReachesTheDocument:
    def test_each_channel_it_sounds_on_takes_an_instrument_of_its_own(self) -> None:
        """Bitphase bakes registers per tick, so a channel's rows carry that channel's reading."""
        project, _ = _project(ChannelName.PULSE1, ChannelName.NOISE)

        document = project_to_bitphase(project)

        assert len(document.instruments) == len(ChannelName.items())

    def test_every_instrument_runs_the_ticks_its_envelopes_describe(self) -> None:
        project, _ = _project(ChannelName.PULSE1)

        document = project_to_bitphase(project)

        assert all(
            len(instrument.macros[NesMacroField.VOLUME_OR_RATE].values) == len(VOLUME)
            for instrument in document.instruments
        )

    def test_a_looping_instrument_returns_to_its_loop_point(self) -> None:
        project, _ = _project(ChannelName.PULSE1, loop_point=1)

        document = project_to_bitphase(project)

        assert all(instrument.macros[NesMacroField.VOLUME_OR_RATE].loop == 1 for instrument in document.instruments)

    def test_a_one_shot_holds_its_final_value(self) -> None:
        project, _ = _project(ChannelName.PULSE1)

        document = project_to_bitphase(project)

        assert all(
            macro.loop == len(macro.values) - 1
            for instrument in document.instruments
            for macro in instrument.macros.values()
        )

    def test_the_table_carries_the_instruments_contour(self) -> None:
        project, _ = _project(ChannelName.PULSE1)

        document = project_to_bitphase(project)

        assert any(tuple(table.rows) == ARPEGGIO for table in document.tables)

    def test_every_point_stands_among_the_values_it_circles(self) -> None:
        project, _ = _project(ChannelName.PULSE1, loop_point=LOOP_FROM_START)

        document = project_to_bitphase(project)

        assert all(
            macro.loop < len(macro.values)
            for instrument in document.instruments
            for macro in instrument.macros.values()
        )
