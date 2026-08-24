from typing import Dict, Mapping, Tuple

import pytest

from sampletones_core.features import RESTING_REFERENCE_PERIOD, RESTING_REFERENCE_PITCH
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.famitracker.builder import build_instrument
from sampletones_core.formats.famitracker.instrument import (
    fti_bytes_to_instrument,
    instrument_to_fti_bytes,
)
from sampletones_core.formats.famitracker.model.instrument import Instrument2A03
from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.instruments import (
    STANDALONE_INSTRUMENT_INDEX,
)
from sampletones_core.formats.famitracker.specification.sequences import SequenceKind
from sampletones_core.formats.famitracker.voice import (
    ImportedVoice,
    InstrumentOmission,
    instrument_to_voice,
)
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_shared.exceptions import InvalidInstrumentValuesError

ARPEGGIO_SCHEME_SETTING = 2


def written(
    kind: SequenceKind,
    items: Tuple[int, ...],
    **fields: int,
) -> InstrumentSequence:
    return InstrumentSequence(kind=kind, items=items, **fields)


def tracker_instrument(
    *sequences: InstrumentSequence,
    name: str = "Lead",
) -> Instrument2A03:
    written_sequences: Dict[SequenceKind, InstrumentSequence] = {
        kind: InstrumentSequence(kind=kind) for kind in SequenceKind
    }
    for sequence in sequences:
        written_sequences[sequence.kind] = sequence

    return Instrument2A03(
        index=STANDALONE_INSTRUMENT_INDEX,
        name=name,
        sequences=written_sequences,
    )


def imported(*sequences: InstrumentSequence) -> ImportedVoice:
    return instrument_to_voice(tracker_instrument(*sequences))


class TestTheEnvelopesAVoiceTakes:
    def test_the_three_dimensions_come_across(self) -> None:
        voice = imported(
            written(SequenceKind.VOLUME, (15, 8, 0)),
            written(SequenceKind.ARPEGGIO, (0, 3, 7)),
            written(SequenceKind.DUTY, (0, 1, 2)),
        ).voice

        assert voice.envelopes == InstrumentEnvelopes(
            volume=Envelope(items=(15, 8, 0)), arpeggio=Envelope(items=(0, 3, 7)), duty_cycle=Envelope(items=(0, 1, 2))
        )

    def test_a_dimension_the_instrument_leaves_out_stays_empty(self) -> None:
        voice = imported(written(SequenceKind.VOLUME, (15, 0))).voice
        assert voice.envelopes == InstrumentEnvelopes(volume=Envelope(items=(15, 0)))

    def test_the_name_comes_across(self) -> None:
        assert imported(written(SequenceKind.VOLUME, (15,))).voice.name == "Lead"

    def test_the_voice_rests_on_the_roots_a_voice_added_by_hand_does(self) -> None:
        voice = imported(written(SequenceKind.VOLUME, (15,))).voice
        assert voice.initial_pitch == RESTING_REFERENCE_PITCH
        assert voice.initial_period == RESTING_REFERENCE_PERIOD

    def test_an_item_outside_the_range_a_dimension_holds_is_refused(self) -> None:
        with pytest.raises(InvalidInstrumentValuesError):
            imported(written(SequenceKind.VOLUME, (99,)))


class TestTheLoopPointsAVoiceTakes:
    """A tracker states a point per sequence, and each dimension of the voice takes its own."""

    def test_each_sequence_brings_its_own_point(self) -> None:
        envelopes = imported(
            written(SequenceKind.VOLUME, (15, 8), loop_point=1),
            written(SequenceKind.ARPEGGIO, (0, 3), loop_point=0),
        ).voice.envelopes

        assert envelopes.volume.loop_point == 1
        assert envelopes.arpeggio.loop_point == 0

    def test_a_sequence_stating_no_loop_holds_its_last_item(self) -> None:
        envelopes = imported(written(SequenceKind.VOLUME, (15, 0))).voice.envelopes
        assert envelopes.volume.loop_point is None

    def test_an_instrument_with_nothing_written_states_no_point(self) -> None:
        assert all(envelope.loop_point is None for envelope in imported().voice.envelopes.envelope_map.values())

    def test_a_loop_point_before_the_first_item_holds_the_last_item(self) -> None:
        envelopes = imported(written(SequenceKind.VOLUME, (15, 0), loop_point=-4)).voice.envelopes
        assert envelopes.volume.loop_point is None

    def test_a_loop_point_past_the_items_holds_the_last_item(self) -> None:
        envelopes = imported(written(SequenceKind.VOLUME, (15, 0), loop_point=9)).voice.envelopes
        assert envelopes.volume.loop_point is None


class TestWhatTheInstrumentStatesPastTheVoice:
    @staticmethod
    def omissions(*sequences: InstrumentSequence) -> Mapping[InstrumentOmission, bool]:
        reported = imported(*sequences).omissions
        return {omission: omission in reported for omission in InstrumentOmission}

    def test_a_plain_instrument_leaves_nothing_behind(self) -> None:
        assert imported(written(SequenceKind.VOLUME, (15, 8, 0))).omissions == ()

    def test_a_pitch_bend_is_reported(self) -> None:
        assert self.omissions(written(SequenceKind.PITCH, (1, -1)))[InstrumentOmission.PITCH]

    def test_a_hi_pitch_bend_is_reported(self) -> None:
        assert self.omissions(written(SequenceKind.HI_PITCH, (1,)))[InstrumentOmission.HI_PITCH]

    def test_a_release_point_is_reported(self) -> None:
        volume = written(SequenceKind.VOLUME, (15, 8), release_point=1)
        assert self.omissions(volume)[InstrumentOmission.RELEASE_POINT]

    def test_an_arpeggio_mode_other_than_absolute_is_reported(self) -> None:
        arpeggio = written(SequenceKind.ARPEGGIO, (0, 3), setting=ARPEGGIO_SCHEME_SETTING)
        assert self.omissions(arpeggio)[InstrumentOmission.ARPEGGIO_MODE]

    def test_the_absolute_arpeggio_a_voice_reads_is_no_omission(self) -> None:
        arpeggio = written(SequenceKind.ARPEGGIO, (0, 3))
        assert not self.omissions(arpeggio)[InstrumentOmission.ARPEGGIO_MODE]

    def test_a_point_per_sequence_is_carried_rather_than_reported(self) -> None:
        """Each dimension holds a point of its own, so a file stating several leaves nothing behind."""
        assert (
            imported(
                written(SequenceKind.VOLUME, (15, 8), loop_point=1),
                written(SequenceKind.ARPEGGIO, (0, 3), loop_point=0),
            ).omissions
            == ()
        )

    def test_every_dimension_past_the_voice_is_named_at_once(self) -> None:
        reported = imported(
            written(SequenceKind.VOLUME, (15, 8), loop_point=1),
            written(SequenceKind.ARPEGGIO, (0, 3), setting=ARPEGGIO_SCHEME_SETTING),
            written(SequenceKind.PITCH, (1, -1), release_point=1),
            written(SequenceKind.HI_PITCH, (0,)),
        ).omissions

        assert set(reported) == set(InstrumentOmission)


class TestAVoiceThroughAFileAndBack:
    """A voice written here reaches a ``.fti`` and comes back holding what it held."""

    @staticmethod
    def round_trip(voice: Instrument) -> ImportedVoice:
        tracker = build_instrument(
            STANDALONE_INSTRUMENT_INDEX,
            voice.name,
            voice.instrument_features(),
        )
        return instrument_to_voice(fti_bytes_to_instrument(instrument_to_fti_bytes(tracker)))

    def test_the_envelopes_come_back(self) -> None:
        voice = Instrument(
            name="Pad",
            envelopes=InstrumentEnvelopes(
                volume=Envelope(items=(15, 10, 5), loop_point=1),
                arpeggio=Envelope(items=(0, 3, 7)),
                duty_cycle=Envelope(items=(0, 1, 2)),
            ),
        )
        assert self.round_trip(voice).voice.envelopes == voice.envelopes

    def test_each_dimension_keeps_its_own_loop_point(self) -> None:
        """A tracker advances every sequence on a counter of its own, and a file states each one."""
        voice = Instrument(
            name="Pad",
            envelopes=InstrumentEnvelopes(
                volume=Envelope(items=(15, 10, 5), loop_point=2),
                arpeggio=Envelope(items=(0, 3, 7, 12), loop_point=0),
                duty_cycle=Envelope(items=(0, 1)),
            ),
        )

        envelopes = self.round_trip(voice).voice.envelopes

        assert envelopes.volume.loop_point == 2
        assert envelopes.arpeggio.loop_point == 0
        assert envelopes.duty_cycle.loop_point is None

    def test_the_name_comes_back(self) -> None:
        voice = Instrument(name="Bass Line", envelopes=InstrumentEnvelopes(volume=Envelope(items=(15, 0))))
        assert self.round_trip(voice).voice.name == "Bass Line"

    def test_a_voice_of_its_own_making_leaves_nothing_behind(self) -> None:
        voice = Instrument(
            name="Pad",
            envelopes=InstrumentEnvelopes(
                volume=Envelope(items=(15, 10, 5), loop_point=1),
                arpeggio=Envelope(items=(0, 3, 7)),
            ),
        )
        assert self.round_trip(voice).omissions == ()

    def test_a_shorter_dimension_comes_back_at_its_own_length(self) -> None:
        """Every sequence stands at the length it was written, which is what a tracker reads."""
        voice = Instrument(
            name="Pad",
            envelopes=InstrumentEnvelopes(
                volume=Envelope(items=(15, 10, 5), loop_point=0),
                duty_cycle=Envelope(items=(2,)),
            ),
        )
        assert self.round_trip(voice).voice.envelopes.duty_cycle.items == (2,)
