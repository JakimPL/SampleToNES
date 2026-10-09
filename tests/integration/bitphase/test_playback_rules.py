from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import HI_PITCH_FACTOR, NUM_PERIODS
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.implementation.noise import NoiseExporter
from sampletones_core.exports.request import InstrumentExport, SampleExport
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.bitphase.btp import write_btp
from sampletones_core.formats.bitphase.builder import instrument_to_bitphase, sample_to_bitphase
from sampletones_core.formats.bitphase.notes import pitch_to_note_index
from sampletones_core.formats.bitphase.specification.channels import CHANNEL_LABELS, ChannelIndex
from sampletones_core.formats.bitphase.specification.chip import PERIOD_OVER_TIMER
from sampletones_core.formats.bitphase.specification.instruments import (
    MAX_VOLUME_OR_RATE,
    MIN_VOLUME_OR_RATE,
)
from sampletones_core.formats.bitphase.specification.macros import MAX_MACRO_LENGTH
from sampletones_core.formats.bitphase.specification.patterns import (
    FIRST_OCTAVE,
    NOTE_RANGE,
    TABLE_COLUMN_OFFSET,
    NoteName,
)
from sampletones_core.instructions import NoiseInstruction
from sampletones_core.timers.arithmetic import bent_timer
from sampletones_core.timers.utils import get_timer_table
from sampletones_player.registers.noise import NoiseRegisters
from sampletones_shared.constants.music import OCTAVE_SEMITONES
from sampletones_shared.music import Tuning
from tests.suite.bitphase import (
    BITPHASE_MAX_PERIOD,
    BITPHASE_SILENT_PERIOD,
    LoadedInstrument,
    LoadedNote,
    LoadedProject,
    LoadedTable,
    noise_register,
    parse_btp,
    reached_note,
    sounded_period,
)
from tests.suite.case import BaseRegularTestCase

NES_FREQUENCY: Final[int] = 60
REFERENCE_PITCH: Final[int] = 60
VOLUME_ENVELOPE: Final[Tuple[int, ...]] = (15, 12, 9, 6, 3, 0)
PITCH_CONTOUR: Final[Tuple[int, ...]] = (0, 0, 5, 5, 7, 7)
BEND_STEPS: Final[Tuple[int, ...]] = (0, -4, -9, -15, -22, -30)
COARSE_STEPS: Final[Tuple[int, ...]] = (0, 0, 0, 1, 1, 2)
TICKS_SAMPLED: Final[int] = 64
LOWERED_A4_FREQUENCY: Final[float] = 432.0
C5_PITCH: Final[int] = 72
SEMITONES_FROM_A4_TO_C5: Final[int] = 3
NOISE_WALK: Final[Tuple[int, ...]] = (3, 4, 9, 15, 0, 1, 12, 7, 2)
NOISE_VOLUME: Final[int] = 12
NOISE_PERIOD_BITS: Final[int] = NUM_PERIODS - 1


@dataclass(frozen=True, kw_only=True)
class TuningCase(BaseRegularTestCase):
    tuning: Tuning


TUNING_CASES: Final[Tuple[TuningCase, ...]] = (
    TuningCase(
        tuning=Tuning(),
        label="concert",
    ),
    TuningCase(
        tuning=Tuning(a4_frequency=LOWERED_A4_FREQUENCY),
        label="lowered",
    ),
    TuningCase(
        tuning=Tuning(
            a4_frequency=LOWERED_A4_FREQUENCY * 2 ** (SEMITONES_FROM_A4_TO_C5 / OCTAVE_SEMITONES),
            a4_pitch=C5_PITCH,
        ),
        label="named_at_c5",
    ),
)


@pytest.fixture(
    name="test_case",
    params=TUNING_CASES,
    ids=lambda test_case: test_case.label,
)
def test_case_fixture(request: pytest.FixtureRequest) -> TuningCase:
    """The tuning a reconstruction was built against, once per case."""
    test_case: TuningCase = request.param
    return test_case


def bent_slice(channel: ChannelName, tuning: Tuning) -> InstrumentExport:
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
        tuning=tuning,
    )


@pytest.fixture(name="bent_document")
def bent_document_fixture(tmp_path: Path, test_case: TuningCase) -> LoadedProject:
    request = SampleExport(
        name="Bent",
        instruments=(
            bent_slice(ChannelName.PULSE1, test_case.tuning),
            bent_slice(ChannelName.TRIANGLE, test_case.tuning),
        ),
        nes_frequency=NES_FREQUENCY,
        tuning=test_case.tuning,
    )
    destination = tmp_path / "Bent.btp"
    write_btp(destination, sample_to_bitphase(request))
    return parse_btp(destination.read_bytes(), list(CHANNEL_LABELS))


def voices(document: LoadedProject) -> List[Tuple[LoadedInstrument, LoadedTable]]:
    return list(zip(document.instruments, document.tables))


class TestAPeriodTheEngineResolves:
    """Bitphase reads a period out of three readings at once — the note the pattern names, the
    step its table stands at, and the offset its instrument's tone macro holds — so the period
    a tick sounds is what those three make of the document as written, at whatever tuning the
    reconstruction was built against.
    """

    def test_every_tick_sounds_the_divider_the_reconstruction_renders(
        self,
        bent_document: LoadedProject,
        test_case: TuningCase,
    ) -> None:
        timers = get_timer_table(test_case.tuning)
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
            assert all(BITPHASE_SILENT_PERIOD < period <= BITPHASE_MAX_PERIOD for period in periods)


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


def noise_walk() -> List[NoiseInstruction]:
    """A noise stream stepping through periods on both sides of where it opens, wrapping past either end."""
    return [NoiseInstruction(on=True, period=period, volume=NOISE_VOLUME, short=False) for period in NOISE_WALK]


def cell_note_index(note: LoadedNote) -> int:
    """The tuning-table index Bitphase's pattern processor reads back from a note cell."""
    return note.name - int(NoteName.C) + (note.octave - FIRST_OCTAVE) * NOTE_RANGE


class TestANoisePeriodTheEngineWrites:
    """The project counts noise periods from the slowest and the register counts them from the
    fastest, so the NSF player writes a period as its complement. A document sounds the same
    register on every tick of a noise slice, the base note and the table step read together.
    """

    @pytest.fixture(name="noise_document")
    def noise_document_fixture(self, tmp_path: Path) -> LoadedProject:
        instructions = noise_walk()
        initial_period = NoiseExporter.derive_initial_pitch(instructions)
        request = InstrumentExport(
            name="Walk",
            channel=ChannelName.NOISE,
            features=NoiseExporter.to_features(instructions, initial_period, ()),
            nes_frequency=NES_FREQUENCY,
            tuning=Tuning(),
        )
        destination = tmp_path / "Walk.btp"
        write_btp(destination, instrument_to_bitphase(request))
        return parse_btp(destination.read_bytes(), list(CHANNEL_LABELS))

    def test_every_tick_writes_the_register_the_nsf_player_writes(self, noise_document: LoadedProject) -> None:
        song = noise_document.songs[0]
        rows = song.patterns[0].channels[int(ChannelIndex.NOISE)].rows
        trigger = next(row for row in rows if row.note.name != int(NoteName.NONE))
        table = noise_document.tables[trigger.table - TABLE_COLUMN_OFFSET]
        note_index = cell_note_index(trigger.note)

        written = [
            noise_register(reached_note(song.tuning_table, note_index, table, tick)) for tick in range(len(NOISE_WALK))
        ]
        played = [registers.period & NOISE_PERIOD_BITS for registers in NoiseRegisters.from_instructions(noise_walk())]

        assert written == played[: len(NOISE_WALK)]
