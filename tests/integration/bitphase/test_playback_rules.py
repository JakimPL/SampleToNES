from pathlib import Path
from typing import Final, List, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import HI_PITCH_FACTOR
from sampletones_core.exporters.feature import Features
from sampletones_core.exports.request import InstrumentExport, SampleExport
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.bitphase.btp import write_btp
from sampletones_core.formats.bitphase.builder import sample_to_bitphase
from sampletones_core.formats.bitphase.notes import pitch_to_note_index
from sampletones_core.formats.bitphase.specification.channels import CHANNEL_LABELS
from sampletones_core.formats.bitphase.specification.chip import (
    MAX_TUNING_PERIOD,
    MIN_TUNING_PERIOD,
)
from sampletones_core.formats.bitphase.specification.instruments import (
    MAX_VOLUME_OR_RATE,
    MIN_VOLUME_OR_RATE,
)
from sampletones_core.formats.bitphase.specification.macros import MAX_MACRO_LENGTH
from sampletones_core.timers.arithmetic import bent_timer
from sampletones_core.timers.utils import get_timer_table
from sampletones_shared.music import Tuning
from tests.suite.bitphase import (
    LoadedInstrument,
    LoadedProject,
    LoadedTable,
    parse_btp,
    sounded_period,
)

NES_FREQUENCY: Final[int] = 60
REFERENCE_PITCH: Final[int] = 60
VOLUME_ENVELOPE: Final[Tuple[int, ...]] = (15, 12, 9, 6, 3, 0)
PITCH_CONTOUR: Final[Tuple[int, ...]] = (0, 0, 5, 5, 7, 7)
BEND_STEPS: Final[Tuple[int, ...]] = (0, -4, -9, -15, -22, -30)
COARSE_STEPS: Final[Tuple[int, ...]] = (0, 0, 0, 1, 1, 2)
TICKS_SAMPLED: Final[int] = 64
PERIOD_OVER_TIMER: Final[int] = 1


def bent_slice(channel: ChannelName) -> InstrumentExport:
    """One bent channel slice, moving its note by a contour and its period by a bend."""
    return InstrumentExport(
        name=f"Bent ({channel})",
        channel=channel,
        features=Features(
            initial_pitch=REFERENCE_PITCH,
            volume=Envelope[int](items=VOLUME_ENVELOPE),
            arpeggio=Envelope[int](items=PITCH_CONTOUR),
            pitch=Envelope[int](items=BEND_STEPS),
            hi_pitch=Envelope[int](items=COARSE_STEPS),
            duty_cycle=None,
        ),
        nes_frequency=NES_FREQUENCY,
        tuning=Tuning(),
    )


@pytest.fixture(name="bent_document")
def bent_document_fixture(tmp_path: Path) -> LoadedProject:
    request = SampleExport(
        name="Bent",
        instruments=(bent_slice(ChannelName.PULSE1), bent_slice(ChannelName.TRIANGLE)),
        nes_frequency=NES_FREQUENCY,
        tuning=Tuning(),
    )
    destination = tmp_path / "Bent.btp"
    write_btp(destination, sample_to_bitphase(request))
    return parse_btp(destination.read_bytes(), list(CHANNEL_LABELS))


def voices(document: LoadedProject) -> List[Tuple[LoadedInstrument, LoadedTable]]:
    return list(zip(document.instruments, document.tables))


class TestAPeriodTheEngineResolves:
    """Bitphase reads a period out of three readings at once — the note the pattern names, the
    step its table stands at, and the offset its instrument's tone macro holds — so the period
    a tick sounds is what those three make of the document as written.
    """

    def test_every_tick_sounds_the_divider_the_reconstruction_renders(
        self,
        bent_document: LoadedProject,
    ) -> None:
        timers = get_timer_table(Tuning())
        table = bent_document.songs[0].tuning_table
        note_index = pitch_to_note_index(REFERENCE_PITCH)

        for instrument, contour in voices(bent_document):
            for tick, (step, steps, coarse) in enumerate(zip(PITCH_CONTOUR, BEND_STEPS, COARSE_STEPS)):
                rendered = bent_timer(timers[REFERENCE_PITCH + step], steps + HI_PITCH_FACTOR * coarse)
                sounded = sounded_period(table, note_index, instrument, contour, tick)
                assert sounded == rendered + PERIOD_OVER_TIMER

    def test_a_channel_goes_on_sounding_for_as_long_as_the_note_does(
        self,
        bent_document: LoadedProject,
    ) -> None:
        """A period of zero silences a channel, so every tick resolves above it."""
        table = bent_document.songs[0].tuning_table
        note_index = pitch_to_note_index(REFERENCE_PITCH)

        for instrument, contour in voices(bent_document):
            periods = [sounded_period(table, note_index, instrument, contour, tick) for tick in range(TICKS_SAMPLED)]
            assert all(MIN_TUNING_PERIOD <= period <= MAX_TUNING_PERIOD for period in periods)


class TestWhatEveryTickOfADocumentReads:
    def test_every_level_sampled_is_one_the_channel_reads(self, document: LoadedProject) -> None:
        levels = [
            instrument.value("volumeOrRate", tick)
            for instrument in document.instruments
            for tick in range(TICKS_SAMPLED)
        ]
        assert all(MIN_VOLUME_OR_RATE <= level <= MAX_VOLUME_OR_RATE for level in levels)

    def test_a_note_played_past_its_envelope_holds_what_the_slice_ends_on(
        self,
        bent_document: LoadedProject,
    ) -> None:
        """Every dimension circles from the value it states, so a tick past the end reads the
        value the slice rests on.
        """
        instrument = bent_document.instruments[0]
        assert instrument.value("volumeOrRate", len(VOLUME_ENVELOPE) + 10) == VOLUME_ENVELOPE[-1]

    def test_every_macro_holds_the_values_a_bitphase_instrument_stores(self, document: LoadedProject) -> None:
        assert all(
            len(macro.values) <= MAX_MACRO_LENGTH
            for instrument in document.instruments
            for macro in instrument.macros.values()
        )
