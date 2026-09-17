from typing import Final

import numpy as np
import pytest

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.generators import PulseGenerator
from sampletones_core.instructions import PulseInstruction
from sampletones_core.library import InstructionLibraryFragment
from sampletones_core.library.data import InstructionLibraryData
from sampletones_shared.application import SAMPLETONES_LIBRARY_DATA_VERSION
from tests.suite.analysis import REPAIR_TOLERANCE
from tests.suite.compatibility import LIBRARY_VERSION, archived

STORED_TONES: Final[tuple[PulseInstruction, ...]] = (
    PulseInstruction(on=True, pitch=57, volume=12, duty_cycle=2),
    PulseInstruction(on=True, pitch=45, volume=8, duty_cycle=1),
)
STORED_SAMPLE_RATE: Final[int] = 11025
STORED_GAMMA: Final[int] = 50
DENSITY_FLOOR: Final[float] = 1e-6


@pytest.fixture(name="loaded")
def loaded_fixture() -> InstructionLibraryData:
    """The archived library read the way a build opens one."""
    return InstructionLibraryData.load(archived(ObjectKind.LIBRARY, LIBRARY_VERSION), fast=False)


class TestTheVersionAnUpgradedLibraryStates:
    def test_it_states_the_version_this_build_reads(self, loaded: InstructionLibraryData) -> None:
        assert loaded.metadata.library_data_version == SAMPLETONES_LIBRARY_DATA_VERSION


class TestWhatAnUpgradedLibraryDescribes:
    """The tones, and the terms they were measured under, stand as the file was written with them."""

    def test_it_was_measured_the_way_the_file_states(self, loaded: InstructionLibraryData) -> None:
        assert loaded.config.spectrum_method is SpectrumMethod.FFT
        assert loaded.config.transformation_gamma == STORED_GAMMA
        assert loaded.config.sample_rate == STORED_SAMPLE_RATE

    def test_every_tone_it_was_written_with_is_held(self, loaded: InstructionLibraryData) -> None:
        assert all(instruction in loaded.data for instruction in STORED_TONES)

    def test_each_tone_keeps_the_sound_it_was_measured_from(self, loaded: InstructionLibraryData) -> None:
        assert all(loaded.data[instruction].sample.array.size > 0 for instruction in STORED_TONES)


class TestTheRepairAnUpgradedLibraryTakes:
    """A 2.0 library averaged its phases in feature space, and reads as the transformed mean."""

    def test_each_feature_reads_as_this_build_measures_it(self, loaded: InstructionLibraryData) -> None:
        """The repair lands on the value the current build computes for the same tone.

        A stored spectrum holds single-precision densities, and recovering the mean runs them back
        through the transform, which spreads that precision widest at the bins nearest zero. The
        comparison therefore carries a floor beside the relative tolerance: every density lies
        within it, and the mass they sum to agrees far more closely still.
        """
        config = Config().model_copy(update={"library": loaded.config})
        extractor = get_feature_extractor(config, Window.from_config(config))
        generator = PulseGenerator(config, ChannelName.PULSE1)
        for instruction in STORED_TONES:
            measured = InstructionLibraryFragment.create(generator, instruction, extractor)
            np.testing.assert_allclose(
                loaded.data[instruction].feature.values,
                measured.feature.values,
                rtol=REPAIR_TOLERANCE,
                atol=DENSITY_FLOOR,
            )

    def test_the_mass_a_feature_sums_to_survives(self, loaded: InstructionLibraryData) -> None:
        """What the densities add up to is what the repair states, and it answers far more tightly."""
        config = Config().model_copy(update={"library": loaded.config})
        extractor = get_feature_extractor(config, Window.from_config(config))
        generator = PulseGenerator(config, ChannelName.PULSE1)
        for instruction in STORED_TONES:
            measured = InstructionLibraryFragment.create(generator, instruction, extractor)
            np.testing.assert_allclose(
                loaded.data[instruction].feature.values.sum(),
                measured.feature.values.sum(),
                rtol=REPAIR_TOLERANCE,
            )
