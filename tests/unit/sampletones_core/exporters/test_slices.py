from typing import List, Sequence

import numpy as np

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters.slices import (
    iterate_instrument_entries,
    iterate_voice_slices,
)
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.voices.envelopes import ShapeEnvelopes
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.shape import Shape
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


def _shape(name: str) -> Shape:
    return Shape(name=name, envelopes=ShapeEnvelopes(volume=(15, 10), arpeggio=(0, 5)))


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

    def test_a_shape_contributes_a_slice_for_every_channel_it_sounds_on(self) -> None:
        project = _project([_shape("lead")])

        slices = list(iterate_voice_slices(project))

        assert [voice_slice.channel for voice_slice in slices] == ChannelName.items()

    def test_each_of_a_shapes_slices_is_measured_against_that_channels_root(self) -> None:
        shape = _shape("lead")
        project = _project([shape])

        for voice_slice in iterate_voice_slices(project):
            assert voice_slice.features.initial_pitch == shape.reference(voice_slice.channel)

    def test_a_shape_writing_nothing_contributes_no_slice(self) -> None:
        project = _project([Shape(name="empty")])

        assert list(iterate_voice_slices(project)) == []


class TestInstrumentEntries:
    """The instruments an export writes, and the channels whose rows reach each one."""

    def test_a_sample_yields_one_instrument_per_playing_channel(self) -> None:
        project = _project([_sample("lead", [ChannelName.PULSE1, ChannelName.NOISE])])

        entries = list(iterate_instrument_entries(project))

        assert [entry.index for entry in entries] == [0, 1]
        assert [list(entry.slots) for entry in entries] == [[ChannelName.PULSE1], [ChannelName.NOISE]]

    def test_a_shape_yields_one_instrument_every_channel_reaches(self) -> None:
        project = _project([_shape("lead")])

        entries = list(iterate_instrument_entries(project))

        assert len(entries) == 1
        assert list(entries[0].slots) == ChannelName.items()
        assert {slot.index for slot in entries[0].slots.values()} == {0}

    def test_a_shapes_slots_each_carry_that_channels_root(self) -> None:
        shape = _shape("lead")
        project = _project([shape])

        entry = next(iter(iterate_instrument_entries(project)))

        for channel, slot in entry.slots.items():
            assert slot.initial_pitch == shape.reference(channel)

    def test_a_shape_is_named_by_itself_and_a_sample_slice_by_its_channel(self) -> None:
        project = _project([_shape("lead"), _sample("pad", [ChannelName.TRIANGLE])])

        entries = list(iterate_instrument_entries(project))

        assert entries[0].name == "lead"
        assert entries[1].name == "pad (triangle)"

    def test_instruments_are_numbered_across_the_voices_in_order(self) -> None:
        project = _project(
            [
                _sample("lead", [ChannelName.PULSE1]),
                _shape("hand"),
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

    def test_a_shape_writing_nothing_takes_no_place_in_the_table(self) -> None:
        project = _project([Shape(name="empty"), _sample("pad", [ChannelName.TRIANGLE])])

        entries = list(iterate_instrument_entries(project))

        assert [entry.index for entry in entries] == [0]
        assert entries[0].name == "pad (triangle)"
