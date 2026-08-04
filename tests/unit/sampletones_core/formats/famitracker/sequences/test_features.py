import numpy as np
import pytest

from sampletones_core.formats.famitracker.sequences.features import features_to_instrument_sequences
from sampletones_core.formats.famitracker.specification.sequences import (
    LOOP_FROM_START,
    MAX_SEQUENCE_ITEMS,
    NO_LOOP_POINT,
    SequenceKind,
)


class TestFeaturesToInstrumentSequences:
    def test_all_five_kinds_present(self) -> None:
        sequences = features_to_instrument_sequences(
            volume=np.array([15, 0]),
            arpeggio=np.array([0]),
            pitch=None,
            hi_pitch=None,
            duty_cycle=None,
            loop=False,
        )
        assert set(sequences) == set(SequenceKind)

    def test_populated_dimension_is_enabled_with_items(self) -> None:
        sequences = features_to_instrument_sequences(
            volume=np.array([15, 12, 0]),
            arpeggio=np.array([], dtype=int),
            pitch=None,
            hi_pitch=None,
            duty_cycle=None,
            loop=False,
        )
        volume = sequences[SequenceKind.VOLUME]
        assert volume.enabled is True
        assert volume.items == (15, 12, 0)

    def test_missing_dimension_is_disabled(self) -> None:
        sequences = features_to_instrument_sequences(
            volume=np.array([15, 0]),
            arpeggio=np.array([], dtype=int),
            pitch=None,
            hi_pitch=None,
            duty_cycle=None,
            loop=False,
        )
        assert sequences[SequenceKind.PITCH].enabled is False
        assert sequences[SequenceKind.PITCH].items == ()
        assert sequences[SequenceKind.ARPEGGIO].enabled is False

    def test_items_are_python_ints(self) -> None:
        sequences = features_to_instrument_sequences(
            volume=np.array([15, 8], dtype=np.int8),
            arpeggio=np.array([-3], dtype=np.int8),
            pitch=None,
            hi_pitch=None,
            duty_cycle=None,
            loop=False,
        )
        assert all(isinstance(item, int) for item in sequences[SequenceKind.VOLUME].items)
        assert all(isinstance(item, int) for item in sequences[SequenceKind.ARPEGGIO].items)

    def test_loop_sets_loop_point_on_populated_sequences(self) -> None:
        sequences = features_to_instrument_sequences(
            volume=np.array([15, 10]),
            arpeggio=np.array([0, 2]),
            pitch=None,
            hi_pitch=None,
            duty_cycle=None,
            loop=True,
        )
        assert sequences[SequenceKind.VOLUME].loop_point == LOOP_FROM_START
        assert sequences[SequenceKind.ARPEGGIO].loop_point == LOOP_FROM_START

    def test_loop_leaves_empty_sequences_unlooped(self) -> None:
        sequences = features_to_instrument_sequences(
            volume=np.array([15, 0]),
            arpeggio=np.array([], dtype=int),
            pitch=None,
            hi_pitch=None,
            duty_cycle=None,
            loop=True,
        )
        assert sequences[SequenceKind.PITCH].loop_point == NO_LOOP_POINT

    def test_no_loop_leaves_loop_point_disabled(self) -> None:
        sequences = features_to_instrument_sequences(
            volume=np.array([15, 10]),
            arpeggio=np.array([0]),
            pitch=None,
            hi_pitch=None,
            duty_cycle=None,
            loop=False,
        )
        assert sequences[SequenceKind.VOLUME].loop_point == NO_LOOP_POINT


class TestSequenceLengthsAreEqualized:
    def test_loop_drops_the_trailing_note_off_volume_item(self) -> None:
        sequences = features_to_instrument_sequences(
            volume=np.array([15, 12, 9, 0]),
            arpeggio=np.array([0, 2, 4]),
            pitch=None,
            hi_pitch=None,
            duty_cycle=np.array([1, 1, 2]),
            loop=True,
        )
        assert sequences[SequenceKind.VOLUME].items == (15, 12, 9)
        assert sequences[SequenceKind.ARPEGGIO].items == (0, 2, 4)
        assert sequences[SequenceKind.DUTY].items == (1, 1, 2)

    def test_one_shot_holds_the_shorter_dimensions_final_value(self) -> None:
        sequences = features_to_instrument_sequences(
            volume=np.array([15, 12, 9, 0]),
            arpeggio=np.array([0, 2, 4]),
            pitch=None,
            hi_pitch=None,
            duty_cycle=np.array([1, 1, 2]),
            loop=False,
        )
        assert sequences[SequenceKind.VOLUME].items == (15, 12, 9, 0)
        assert sequences[SequenceKind.ARPEGGIO].items == (0, 2, 4, 4)
        assert sequences[SequenceKind.DUTY].items == (1, 1, 2, 2)

    @pytest.mark.parametrize("loop", [False, True], ids=["one_shot", "loop"])
    def test_every_populated_dimension_shares_one_length(self, loop: bool) -> None:
        sequences = features_to_instrument_sequences(
            volume=np.array([15, 12, 9, 0]),
            arpeggio=np.array([0, 2, 4]),
            pitch=np.array([0, 1]),
            hi_pitch=None,
            duty_cycle=np.array([1, 1, 2]),
            loop=loop,
        )
        lengths = {len(sequence.items) for sequence in sequences.values() if sequence.enabled}
        assert len(lengths) == 1

    def test_disabled_dimensions_stay_empty(self) -> None:
        sequences = features_to_instrument_sequences(
            volume=np.array([15, 12, 0]),
            arpeggio=np.array([], dtype=int),
            pitch=None,
            hi_pitch=None,
            duty_cycle=None,
            loop=False,
        )
        assert sequences[SequenceKind.ARPEGGIO].items == ()
        assert sequences[SequenceKind.PITCH].items == ()

    def test_all_dimensions_empty_stays_empty(self) -> None:
        sequences = features_to_instrument_sequences(
            volume=np.array([], dtype=int),
            arpeggio=np.array([], dtype=int),
            pitch=None,
            hi_pitch=None,
            duty_cycle=None,
            loop=True,
        )
        assert all(not sequence.enabled for sequence in sequences.values())

    def test_an_over_long_envelope_builds_sequences_famitracker_accepts(self) -> None:
        length = MAX_SEQUENCE_ITEMS + 48

        sequences = features_to_instrument_sequences(
            volume=np.arange(length) % 16,
            arpeggio=np.zeros(length, dtype=int),
            pitch=None,
            hi_pitch=None,
            duty_cycle=None,
            loop=False,
        )

        assert all(len(sequence.items) <= MAX_SEQUENCE_ITEMS for sequence in sequences.values())
