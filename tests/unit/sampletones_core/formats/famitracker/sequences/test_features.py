from typing import Final, Optional, Sequence

from sampletones_core.exporters.feature import Features
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.famitracker.sequences.features import (
    features_to_instrument_sequences,
)
from sampletones_core.formats.famitracker.specification.sequences import (
    LOOP_FROM_START,
    MAX_SEQUENCE_ITEMS,
    NO_LOOP_POINT,
    SequenceKind,
)
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT

REFERENCE_PITCH: Final[int] = 60


def envelope(items: Sequence[int], loop_point: Optional[int] = None) -> Envelope[int]:
    return Envelope[int](items=tuple(items), loop_point=loop_point if items else None)


def build(
    volume: Sequence[int],
    arpeggio: Sequence[int],
    *,
    pitch: Optional[Sequence[int]] = None,
    duty_cycle: Optional[Sequence[int]] = None,
    loop_point: Optional[int] = None,
) -> Features:
    """One channel slice's envelopes, each dimension carrying the point it repeats from."""
    return Features(
        initial_pitch=REFERENCE_PITCH,
        volume=envelope(volume, loop_point),
        arpeggio=envelope(arpeggio, loop_point),
        pitch=None if pitch is None else envelope(pitch, loop_point),
        hi_pitch=None,
        duty_cycle=None if duty_cycle is None else envelope(duty_cycle, loop_point),
    )


class TestFeaturesToInstrumentSequences:
    def test_all_five_kinds_present(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 0], [0]))
        assert set(sequences) == set(SequenceKind)

    def test_populated_dimension_is_enabled_with_items(self) -> None:
        volume = features_to_instrument_sequences(build([15, 12, 0], []))[SequenceKind.VOLUME]
        assert volume.enabled is True
        assert volume.items == (15, 12, 0)

    def test_missing_dimension_is_disabled(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 0], []))
        assert sequences[SequenceKind.PITCH].enabled is False
        assert sequences[SequenceKind.PITCH].items == ()
        assert sequences[SequenceKind.ARPEGGIO].enabled is False

    def test_items_are_python_ints(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 8], [-3]))
        assert all(isinstance(item, int) for item in sequences[SequenceKind.VOLUME].items)
        assert all(isinstance(item, int) for item in sequences[SequenceKind.ARPEGGIO].items)


class TestTheLoopPointEachSequenceCarries:
    def test_a_dimension_carries_the_point_it_states(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 10], [0, 2], loop_point=WHOLE_LOOP_POINT))
        assert sequences[SequenceKind.VOLUME].loop_point == LOOP_FROM_START
        assert sequences[SequenceKind.ARPEGGIO].loop_point == LOOP_FROM_START

    def test_each_dimension_repeats_from_its_own_item(self) -> None:
        """A tracker advances every sequence on a counter of its own, so the points stand apart."""
        features = Features(
            initial_pitch=REFERENCE_PITCH,
            volume=envelope([15, 12, 9, 0], 2),
            arpeggio=envelope([0, 2, 4], 0),
            pitch=None,
            hi_pitch=None,
            duty_cycle=envelope([1, 1]),
        )

        sequences = features_to_instrument_sequences(features)

        assert sequences[SequenceKind.VOLUME].loop_point == 2
        assert sequences[SequenceKind.ARPEGGIO].loop_point == 0
        assert sequences[SequenceKind.DUTY].loop_point == NO_LOOP_POINT

    def test_a_dimension_the_instrument_leaves_out_states_no_point(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 0], [], loop_point=WHOLE_LOOP_POINT))
        assert sequences[SequenceKind.PITCH].loop_point == NO_LOOP_POINT

    def test_a_dimension_that_halts_states_no_point(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 10], [0]))
        assert sequences[SequenceKind.VOLUME].loop_point == NO_LOOP_POINT


class TestSequenceLengths:
    def test_every_dimension_stands_at_the_length_it_was_written(self) -> None:
        """A halted sequence holds its final value, so a shorter dimension governs the rest itself."""
        sequences = features_to_instrument_sequences(build([15, 12, 9, 0], [0, 2, 4], duty_cycle=[1]))
        assert sequences[SequenceKind.VOLUME].items == (15, 12, 9, 0)
        assert sequences[SequenceKind.ARPEGGIO].items == (0, 2, 4)
        assert sequences[SequenceKind.DUTY].items == (1,)

    def test_circling_costs_a_dimension_none_of_its_items(self) -> None:
        """Each dimension repeats on its own period, so a loop leaves every length as written."""
        sequences = features_to_instrument_sequences(
            build([15, 12, 9, 0], [0, 2, 4], duty_cycle=[1, 1, 2], loop_point=WHOLE_LOOP_POINT)
        )
        assert sequences[SequenceKind.VOLUME].items == (15, 12, 9, 0)
        assert sequences[SequenceKind.ARPEGGIO].items == (0, 2, 4)
        assert sequences[SequenceKind.DUTY].items == (1, 1, 2)

    def test_disabled_dimensions_stay_empty(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 12, 0], []))
        assert sequences[SequenceKind.ARPEGGIO].items == ()
        assert sequences[SequenceKind.PITCH].items == ()

    def test_an_empty_envelope_differs_from_one_holding_a_single_zero(self) -> None:
        """An empty dimension leaves its sequence disabled; a single zero is a value the instrument sets."""
        cleared = features_to_instrument_sequences(build([15, 0], []))
        zeroed = features_to_instrument_sequences(build([15, 0], [0]))

        assert cleared[SequenceKind.ARPEGGIO].enabled is False
        assert zeroed[SequenceKind.ARPEGGIO].enabled is True
        assert zeroed[SequenceKind.ARPEGGIO].items == (0,)

    def test_all_dimensions_empty_stays_empty(self) -> None:
        sequences = features_to_instrument_sequences(build([], [], loop_point=WHOLE_LOOP_POINT))
        assert all(not sequence.enabled for sequence in sequences.values())

    def test_an_over_long_envelope_builds_sequences_famitracker_accepts(self) -> None:
        length = MAX_SEQUENCE_ITEMS + 48

        sequences = features_to_instrument_sequences(build([index % 16 for index in range(length)], [0] * length))

        assert all(len(sequence.items) <= MAX_SEQUENCE_ITEMS for sequence in sequences.values())
