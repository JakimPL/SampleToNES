from typing import List, Sequence

import numpy as np

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters.slices import (
    FIRST_INSTRUMENT_INDEX,
    InstrumentEntry,
    iterate_instrument_entries,
    iterate_voice_slices,
    voice_instrument_entries,
)
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion
from sampletones_core.structures import IdentifiedCollection
from tests.suite.sequencer import sample_reconstruction


def _project(voices: Sequence[VoiceUnion]) -> Project:
    collection: IdentifiedCollection[VoiceUnion] = IdentifiedCollection()
    for voice in voices:
        collection.append(voice)

    project = Project.create(title="Slices", author="Tester", settings=ProjectSettings())
    project.voices = collection
    return project


def _sample(name: str, channels: Sequence[ChannelName]) -> Sample:
    return Sample(name=name, reconstruction=sample_reconstruction(list(channels)))


def _instrument(name: str) -> Instrument:
    return Instrument(
        name=name, envelopes=InstrumentEnvelopes(volume=Envelope(items=(15, 10)), arpeggio=Envelope(items=(0, 5)))
    )


def _stand_by(sample: Sample, channel: ChannelName) -> None:
    sample.reconstruction.update_channel_data(
        channel,
        [],
        np.zeros(0, dtype=np.float32),
        sample.reconstruction.initial_pitches[channel],
        (FeatureKey.VOLUME, FeatureKey.ARPEGGIO, FeatureKey.DUTY_CYCLE),
    )


class TestVoiceSlices:
    """What every channel of every voice plays, which is what a per-channel backend reads."""

    def test_a_sample_contributes_one_slice_per_playing_channel(self) -> None:
        project = _project([_sample("lead", [ChannelName.PULSE1, ChannelName.NOISE])])

        slices = list(iterate_voice_slices(project))

        assert [voice_slice.channel for voice_slice in slices] == [
            ChannelName.PULSE1,
            ChannelName.NOISE,
        ]

    def test_a_channel_standing_by_takes_no_slice(self) -> None:
        sample = _sample("lead", [ChannelName.PULSE1, ChannelName.PULSE2])
        _stand_by(sample, ChannelName.PULSE1)
        project = _project([sample])

        slices = list(iterate_voice_slices(project))

        assert [voice_slice.channel for voice_slice in slices] == [ChannelName.PULSE2]

    def test_an_instrument_contributes_a_slice_for_every_channel_it_sounds_on(self) -> None:
        project = _project([_instrument("lead")])

        slices = list(iterate_voice_slices(project))

        assert [voice_slice.channel for voice_slice in slices] == ChannelName.items()

    def test_each_of_an_instruments_slices_is_measured_against_that_channels_root(self) -> None:
        instrument = _instrument("lead")
        project = _project([instrument])

        for voice_slice in iterate_voice_slices(project):
            assert voice_slice.features.initial_pitch == instrument.reference(voice_slice.channel)

    def test_an_instrument_writing_nothing_contributes_no_slice(self) -> None:
        project = _project([Instrument(name="empty")])

        assert list(iterate_voice_slices(project)) == []


class TestInstrumentEntries:
    """The instruments an export writes, and the channels whose rows reach each one."""

    def test_a_sample_yields_one_instrument_per_playing_channel(self) -> None:
        project = _project([_sample("lead", [ChannelName.PULSE1, ChannelName.NOISE])])

        entries = list(iterate_instrument_entries(project))

        assert [entry.index for entry in entries] == [0, 1]
        assert [list(entry.slots) for entry in entries] == [[ChannelName.PULSE1], [ChannelName.NOISE]]

    def test_an_instrument_takes_one_table_entry_every_channel_reaches(self) -> None:
        project = _project([_instrument("lead")])

        entries = list(iterate_instrument_entries(project))

        assert len(entries) == 1
        assert list(entries[0].slots) == ChannelName.items()
        assert {slot.index for slot in entries[0].slots.values()} == {0}

    def test_an_instruments_slots_each_carry_that_channels_root(self) -> None:
        instrument = _instrument("lead")
        project = _project([instrument])

        entry = next(iter(iterate_instrument_entries(project)))

        for channel, slot in entry.slots.items():
            assert slot.initial_pitch == instrument.reference(channel)

    def test_an_instrument_is_named_by_itself_and_a_sample_slice_by_its_channel(self) -> None:
        project = _project([_instrument("lead"), _sample("pad", [ChannelName.TRIANGLE])])

        entries = list(iterate_instrument_entries(project))

        assert entries[0].name == "lead"
        assert entries[1].name == "pad (triangle)"

    def test_instruments_are_numbered_across_the_voices_in_order(self) -> None:
        project = _project(
            [
                _sample("lead", [ChannelName.PULSE1]),
                _instrument("hand"),
                _sample("pad", [ChannelName.TRIANGLE, ChannelName.NOISE]),
            ]
        )

        indices: List[int] = [entry.index for entry in iterate_instrument_entries(project)]

        assert indices == [0, 1, 2, 3]

    def test_a_channel_standing_by_shifts_no_index_behind_it(self) -> None:
        sample = _sample("lead", [ChannelName.PULSE1, ChannelName.PULSE2])
        _stand_by(sample, ChannelName.PULSE1)
        project = _project([sample])

        entries = list(iterate_instrument_entries(project))

        assert [(entry.index, list(entry.slots)) for entry in entries] == [(0, [ChannelName.PULSE2])]

    def test_an_instrument_writing_nothing_takes_no_place_in_the_table(self) -> None:
        project = _project([Instrument(name="empty"), _sample("pad", [ChannelName.TRIANGLE])])

        entries = list(iterate_instrument_entries(project))

        assert [entry.index for entry in entries] == [0]
        assert entries[0].name == "pad (triangle)"


class TestOneVoicesInstruments:
    """The instruments one voice offers, which is the rule a whole-project export also reads."""

    @staticmethod
    def _entries(voice: VoiceUnion) -> List[InstrumentEntry]:
        return list(voice_instrument_entries(voice, start_index=FIRST_INSTRUMENT_INDEX))

    def test_a_sample_offers_one_per_playing_channel(self) -> None:
        sample = _sample("bass", [ChannelName.PULSE1, ChannelName.NOISE])

        assert [entry.channel for entry in self._entries(sample)] == [
            ChannelName.PULSE1,
            ChannelName.NOISE,
        ]

    def test_a_written_instrument_offers_one(self) -> None:
        """One set of envelopes every channel reads is one instrument, however many it sounds on."""
        assert len(self._entries(_instrument("lead"))) == 1

    def test_a_written_instrument_states_its_envelopes_for_no_channel(self) -> None:
        """One set every channel reads belongs to none of them, so the entry names none."""
        assert self._entries(_instrument("lead"))[0].channel is None

    def test_a_written_instrument_still_answers_for_every_channel_it_sounds_on(self) -> None:
        """Naming no channel of its own leaves the rows of every channel reaching it."""
        assert list(self._entries(_instrument("lead"))[0].slots) == ChannelName.items()

    def test_a_samples_slice_names_the_channel_it_was_reconstructed_for(self) -> None:
        sample = _sample("bass", [ChannelName.TRIANGLE])

        assert self._entries(sample)[0].channel is ChannelName.TRIANGLE

    def test_a_voice_writing_nothing_offers_nothing(self) -> None:
        assert self._entries(_instrument_writing_nothing()) == []

    def test_the_project_walk_reads_the_same_rule(self) -> None:
        """A reader is offered exactly the instruments a module would have held for that voice."""
        sample = _sample("bass", [ChannelName.PULSE1, ChannelName.NOISE])
        instrument = _instrument("lead")
        project = _project([sample, instrument])

        walked = list(iterate_instrument_entries(project))
        per_voice = self._entries(sample) + self._entries(instrument)

        assert [entry.name for entry in walked] == [entry.name for entry in per_voice]

    def test_the_numbering_starts_where_it_is_told_to(self) -> None:
        sample = _sample("bass", [ChannelName.PULSE1, ChannelName.NOISE])

        entries = list(voice_instrument_entries(sample, start_index=7))

        assert [entry.index for entry in entries] == [7, 8]


def _instrument_writing_nothing() -> Instrument:
    return Instrument(name="silent", envelopes=InstrumentEnvelopes())
