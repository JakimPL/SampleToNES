from typing import Final, Optional, Sequence

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import MAX_VOLUME, SILENT_VOLUME
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.truncation import is_shortened
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.famitracker.sequences.features import (
    features_to_instrument_sequences,
    features_truncation,
    stored_length,
)
from sampletones_core.formats.famitracker.specification.sequences import (
    BEND_SEQUENCE_KINDS,
    LOOP_FROM_START,
    MAX_SEQUENCE_ITEMS,
    NO_LOOP_POINT,
    SequenceKind,
)

REFERENCE_PITCH: Final[int] = 60
RELEASE: Final[int] = SILENT_VOLUME


def sounding(length: int) -> Sequence[int]:
    """A volume dimension of ``length`` items that never falls silent."""
    return [MAX_VOLUME - index % MAX_VOLUME for index in range(length)]


def released(length: int) -> Sequence[int]:
    """A volume dimension of ``length`` items whose last one releases the note."""
    return list(sounding(length - 1)) + [RELEASE]


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


class TestTheArpeggioThatPinsABend:
    """A bend travels with an arpeggio, because that is what makes each item an offset.

    FamiTracker walks an instrument's sequences in slot order, and an absolute arpeggio reloads
    the period from the note before a bend adds to it. A bend the arpeggio covers therefore sounds
    in the tracker as the per-tick offset this project writes it as.
    """

    def test_a_bend_without_an_arpeggio_gains_a_repeating_one(self) -> None:
        arpeggio = features_to_instrument_sequences(build([15, 0], [], pitch=[3, -3]), repitched=False)[
            SequenceKind.ARPEGGIO
        ]

        assert arpeggio.enabled is True
        assert arpeggio.items == (0,)
        assert arpeggio.loop_point == LOOP_FROM_START

    def test_an_arpeggio_shorter_than_the_bend_reaches_its_length(self) -> None:
        arpeggio = features_to_instrument_sequences(build([15, 0], [4, 7], pitch=[1, 2, 3, 4]), repitched=False)[
            SequenceKind.ARPEGGIO
        ]

        assert arpeggio.items == (4, 7, 7, 7)

    def test_an_arpeggio_that_repeats_is_left_as_it_stands(self) -> None:
        sequences = features_to_instrument_sequences(
            build([15, 0], [0, 5], pitch=[1, 2, 3, 4], loop_point=LOOP_FROM_START),
            repitched=False,
        )

        assert sequences[SequenceKind.ARPEGGIO].items == (0, 5)
        assert sequences[SequenceKind.ARPEGGIO].loop_point == LOOP_FROM_START

    def test_an_arpeggio_already_covering_the_bend_is_left_as_it_stands(self) -> None:
        arpeggio = features_to_instrument_sequences(build([15, 0], [4, 7, 9], pitch=[1, 2]), repitched=False)[
            SequenceKind.ARPEGGIO
        ]

        assert arpeggio.items == (4, 7, 9)

    def test_an_instrument_writing_no_bend_gains_no_arpeggio(self) -> None:
        arpeggio = features_to_instrument_sequences(build([15, 0], []), repitched=False)[SequenceKind.ARPEGGIO]

        assert arpeggio.enabled is False


class TestFeaturesToInstrumentSequences:
    def test_all_five_kinds_present(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 0], [0]), repitched=False)
        assert set(sequences) == set(SequenceKind)

    def test_populated_dimension_is_enabled_with_items(self) -> None:
        volume = features_to_instrument_sequences(build([15, 12, 0], []), repitched=False)[SequenceKind.VOLUME]
        assert volume.enabled is True
        assert volume.items == (15, 12, 0)

    def test_missing_dimension_is_disabled(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 0], []), repitched=False)
        assert sequences[SequenceKind.PITCH].enabled is False
        assert sequences[SequenceKind.PITCH].items == ()
        assert sequences[SequenceKind.ARPEGGIO].enabled is False

    def test_items_are_python_ints(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 8], [-3]), repitched=False)
        assert all(isinstance(item, int) for item in sequences[SequenceKind.VOLUME].items)
        assert all(isinstance(item, int) for item in sequences[SequenceKind.ARPEGGIO].items)


class TestTheLoopPointEachSequenceCarries:
    def test_a_dimension_carries_the_point_it_states(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 10], [0, 2], loop_point=0), repitched=False)
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

        sequences = features_to_instrument_sequences(features, repitched=False)

        assert sequences[SequenceKind.VOLUME].loop_point == 2
        assert sequences[SequenceKind.ARPEGGIO].loop_point == 0
        assert sequences[SequenceKind.DUTY].loop_point == NO_LOOP_POINT

    def test_a_dimension_the_instrument_leaves_out_states_no_point(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 0], [], loop_point=0), repitched=False)
        assert sequences[SequenceKind.PITCH].loop_point == NO_LOOP_POINT

    def test_a_dimension_that_halts_states_no_point(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 10], [0]), repitched=False)
        assert sequences[SequenceKind.VOLUME].loop_point == NO_LOOP_POINT


class TestSequenceLengths:
    def test_every_dimension_stands_at_the_length_it_was_written(self) -> None:
        """A halted sequence holds its final value, so a shorter dimension governs the rest itself."""
        sequences = features_to_instrument_sequences(build([15, 12, 9, 0], [0, 2, 4], duty_cycle=[1]), repitched=False)
        assert sequences[SequenceKind.VOLUME].items == (15, 12, 9, 0)
        assert sequences[SequenceKind.ARPEGGIO].items == (0, 2, 4)
        assert sequences[SequenceKind.DUTY].items == (1,)

    def test_circling_costs_a_dimension_none_of_its_items(self) -> None:
        """Each dimension repeats on its own period, so a loop leaves every length as written."""
        sequences = features_to_instrument_sequences(
            build([15, 12, 9, 0], [0, 2, 4], duty_cycle=[1, 1, 2], loop_point=0),
            repitched=False,
        )
        assert sequences[SequenceKind.VOLUME].items == (15, 12, 9, 0)
        assert sequences[SequenceKind.ARPEGGIO].items == (0, 2, 4)
        assert sequences[SequenceKind.DUTY].items == (1, 1, 2)

    def test_disabled_dimensions_stay_empty(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 12, 0], []), repitched=False)
        assert sequences[SequenceKind.ARPEGGIO].items == ()
        assert sequences[SequenceKind.PITCH].items == ()

    def test_an_empty_envelope_differs_from_one_holding_a_single_zero(self) -> None:
        """An empty dimension leaves its sequence disabled; a single zero is a value the instrument sets."""
        cleared = features_to_instrument_sequences(build([15, 0], []), repitched=False)
        zeroed = features_to_instrument_sequences(build([15, 0], [0]), repitched=False)

        assert cleared[SequenceKind.ARPEGGIO].enabled is False
        assert zeroed[SequenceKind.ARPEGGIO].enabled is True
        assert zeroed[SequenceKind.ARPEGGIO].items == (0,)

    def test_all_dimensions_empty_stays_empty(self) -> None:
        sequences = features_to_instrument_sequences(build([], [], loop_point=0), repitched=False)
        assert all(not sequence.enabled for sequence in sequences.values())

    def test_an_over_long_envelope_builds_sequences_famitracker_accepts(self) -> None:
        length = MAX_SEQUENCE_ITEMS + 48

        sequences = features_to_instrument_sequences(
            build([index % 16 for index in range(length)], [0] * length), repitched=False
        )

        assert all(len(sequence.items) <= MAX_SEQUENCE_ITEMS for sequence in sequences.values())


class TestTheReleaseAnExportKeeps:
    """A volume dimension ending at silence is what releases a note, so the file keeps that item.

    FamiTracker halts a sequence on its last item and holds the value there for as long as the
    note sounds, so a shortened volume dimension that dropped its silence would sound forever.
    """

    def test_a_released_dimension_at_the_limit_is_written_whole(self) -> None:
        sequences = features_to_instrument_sequences(build(released(MAX_SEQUENCE_ITEMS), []), repitched=False)
        volume = sequences[SequenceKind.VOLUME]
        assert len(volume.items) == MAX_SEQUENCE_ITEMS
        assert volume.items[-1] == RELEASE

    def test_a_released_dimension_past_the_limit_still_ends_at_its_release(self) -> None:
        sequences = features_to_instrument_sequences(build(released(MAX_SEQUENCE_ITEMS + 1), []), repitched=False)
        volume = sequences[SequenceKind.VOLUME]
        assert len(volume.items) == MAX_SEQUENCE_ITEMS
        assert volume.items[-1] == RELEASE

    def test_the_release_displaces_the_last_item_that_would_not_fit(self) -> None:
        source = released(MAX_SEQUENCE_ITEMS + 1)
        volume = features_to_instrument_sequences(build(source, []), repitched=False)[SequenceKind.VOLUME]
        assert volume.items == tuple(source[: MAX_SEQUENCE_ITEMS - 1]) + (RELEASE,)

    def test_a_dimension_that_goes_on_sounding_keeps_its_opening_items(self) -> None:
        source = sounding(MAX_SEQUENCE_ITEMS + 8)
        volume = features_to_instrument_sequences(build(source, []), repitched=False)[SequenceKind.VOLUME]
        assert volume.items == tuple(source[:MAX_SEQUENCE_ITEMS])

    def test_a_circling_dimension_reads_its_final_silence_as_part_of_the_cycle(self) -> None:
        """A dimension repeating from a point never halts, so its last item releases nothing."""
        source = released(MAX_SEQUENCE_ITEMS + 1)
        volume = features_to_instrument_sequences(build(source, [], loop_point=0), repitched=False)[SequenceKind.VOLUME]
        assert volume.items == tuple(source[:MAX_SEQUENCE_ITEMS])

    def test_a_dimension_other_than_volume_keeps_its_opening_items(self) -> None:
        """Only a volume dimension releases a note; the rest are read at whatever they last stated."""
        source = [index % 8 for index in range(MAX_SEQUENCE_ITEMS + 8)]
        source[-1] = 0
        arpeggio = features_to_instrument_sequences(build(released(4), source), repitched=False)[SequenceKind.ARPEGGIO]
        assert arpeggio.items == tuple(source[:MAX_SEQUENCE_ITEMS])


class TestWhetherAnExportShortensADimension:
    def test_a_dimension_within_the_limit_is_written_whole(self) -> None:
        assert is_shortened(FeatureKey.VOLUME, envelope(released(MAX_SEQUENCE_ITEMS)), stored_length) is False

    def test_a_dimension_past_the_limit_is_shortened(self) -> None:
        assert is_shortened(FeatureKey.VOLUME, envelope(released(MAX_SEQUENCE_ITEMS + 1)), stored_length) is True

    def test_keeping_the_release_still_counts_as_shortening(self) -> None:
        """The release survives, so one sounding item is what the file leaves out."""
        source = envelope(released(MAX_SEQUENCE_ITEMS + 1))
        assert is_shortened(FeatureKey.VOLUME, source, stored_length) is True


class TestWhatAnExportReportsLeavingOut:
    def test_features_within_the_limit_report_nothing(self) -> None:
        assert features_truncation(build(released(MAX_SEQUENCE_ITEMS), [0])) is None

    def test_features_past_the_limit_report_both_counts(self) -> None:
        source_frames = MAX_SEQUENCE_ITEMS + 48
        truncation = features_truncation(build(released(source_frames), []))
        assert truncation is not None
        assert truncation.source_frames == source_frames
        assert truncation.frames == MAX_SEQUENCE_ITEMS
        assert truncation.instruments == 1


class TestTheSequencesANoteSlideReaches:
    """A note slide moves the channel's note, and only an arpeggio still running reloads the period from
    it every tick, so an instrument a slide reaches keeps its arpeggio running for as long as the note
    sounds. The bend is added to the period the arpeggio reloads and a halted bend adds nothing, so the
    bend keeps running too, each on the last item it plays.
    """

    def test_an_arpeggio_playing_once_circles_on_its_last_item(self) -> None:
        arpeggio = features_to_instrument_sequences(build([15, 0], [4, 7, 9]), repitched=True)[SequenceKind.ARPEGGIO]

        assert arpeggio.items == (4, 7, 9)
        assert arpeggio.loop_point == len(arpeggio.items) - 1

    def test_an_arpeggio_that_repeats_is_left_as_it_stands(self) -> None:
        arpeggio = features_to_instrument_sequences(
            build([15, 0], [4, 7, 9], loop_point=LOOP_FROM_START),
            repitched=True,
        )[SequenceKind.ARPEGGIO]

        assert arpeggio.loop_point == LOOP_FROM_START

    def test_an_instrument_writing_no_arpeggio_takes_one_running_at_its_own_note(self) -> None:
        arpeggio = features_to_instrument_sequences(build([15, 0], []), repitched=True)[SequenceKind.ARPEGGIO]

        assert (arpeggio.items, arpeggio.loop_point) == ((0,), LOOP_FROM_START)

    def test_a_bend_playing_once_circles_on_the_offset_it_ends_on(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 0], [0, 2], pitch=[1, 2, 3]), repitched=True)

        assert (sequences[SequenceKind.PITCH].items, sequences[SequenceKind.PITCH].loop_point) == ((1, 2, 3), 2)

    def test_a_bend_the_channel_governs_stays_disabled(self) -> None:
        sequences = features_to_instrument_sequences(build([15, 0], [0, 2]), repitched=True)

        assert not any(sequences[kind].enabled for kind in BEND_SEQUENCE_KINDS)

    def test_an_instrument_no_slide_reaches_keeps_its_arpeggio_halting(self) -> None:
        arpeggio = features_to_instrument_sequences(build([15, 0], [4, 7, 9]), repitched=False)[SequenceKind.ARPEGGIO]

        assert arpeggio.loop_point == NO_LOOP_POINT
