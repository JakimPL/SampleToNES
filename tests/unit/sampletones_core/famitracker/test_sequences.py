import numpy as np

from sampletones_core.famitracker.sequences import features_to_instrument_sequences
from sampletones_core.famitracker.specification.sequences import (
    LOOP_FROM_START,
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
        assert sequences[SequenceKind.ARPEGGIO].items == (-3,)

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
