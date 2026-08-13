from typing import List, Sequence

import numpy as np

from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters.slices import iterate_sample_slices
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.structures import IdentifiedCollection
from tests.suite.sequencer import sample_reconstruction


def _project(samples: Sequence[Sample]) -> Project:
    collection: IdentifiedCollection[Sample] = IdentifiedCollection()
    for sample in samples:
        collection.append(sample)

    project = Project.create(title="Slices", author="Tester", settings=ProjectSettings())
    project.samples = collection
    return project


def _sample(name: str, generators: Sequence[GeneratorName]) -> Sample:
    return Sample(name=name, reconstruction=sample_reconstruction(list(generators)))


class TestSampleSlices:
    """The walk numbers the instruments a module writes, so it visits the channels that play.

    A sample carries every channel whatever it sounds, and one standing by is written nowhere,
    so it takes no place in the instrument table and shifts no index behind it.
    """

    def test_a_sample_contributes_one_slice_per_playing_channel(self) -> None:
        project = _project([_sample("lead", [GeneratorName.PULSE1, GeneratorName.NOISE])])

        slices = list(iterate_sample_slices(project))

        assert [sample_slice.generator for sample_slice in slices] == [
            GeneratorName.PULSE1,
            GeneratorName.NOISE,
        ]

    def test_a_channel_standing_by_takes_no_place_in_the_table(self) -> None:
        sample = _sample("lead", [GeneratorName.PULSE1, GeneratorName.PULSE2])
        sample.reconstruction.update_generator_data(
            GeneratorName.PULSE1,
            [],
            np.zeros(0, dtype=np.float32),
            sample.reconstruction.initial_pitches[GeneratorName.PULSE1],
            (FeatureKey.VOLUME, FeatureKey.ARPEGGIO, FeatureKey.DUTY_CYCLE),
        )
        project = _project([sample])

        slices = list(iterate_sample_slices(project))

        assert [(sample_slice.index, sample_slice.generator) for sample_slice in slices] == [
            (0, GeneratorName.PULSE2),
        ]

    def test_slices_are_numbered_across_the_samples_in_order(self) -> None:
        project = _project(
            [
                _sample("lead", [GeneratorName.PULSE1]),
                _sample("pad", [GeneratorName.TRIANGLE, GeneratorName.NOISE]),
            ]
        )

        indices: List[int] = [sample_slice.index for sample_slice in iterate_sample_slices(project)]

        assert indices == [0, 1, 2]
