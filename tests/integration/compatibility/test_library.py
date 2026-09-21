from typing import Final

import numpy as np
import pytest

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.upgrade import CURRENT_VERSIONS
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.library import LibraryHeader, LibraryState, library_state
from sampletones_core.library.data import InstructionLibraryData
from sampletones_shared.application import SAMPLETONES_LIBRARY_DATA_VERSION
from sampletones_shared.exceptions import IncompatibleLibraryDataVersionError
from sampletones_tools.compatibility.documents import corpus_library
from tests.suite.compatibility import LIBRARY_VERSION, archived

STORED_SAMPLE_RATE: Final[int] = 11025
STORED_GAMMA: Final[int] = 50
GENERATION_TOLERANCE: Final[float] = 1e-6


class TestTheLibraryTheLastReleaseWrote:
    """A library the last release wrote reads as out of date, which is what has it rebuilt."""

    def test_it_reads_as_out_of_date(self) -> None:
        assert library_state(archived(ObjectKind.LIBRARY, LIBRARY_VERSION)) is LibraryState.OUTDATED

    def test_it_states_the_settings_it_was_built_for(self) -> None:
        """The settings a rebuild takes up, so the rebuilt library lands in the file's own place."""
        config = LibraryHeader.read(archived(ObjectKind.LIBRARY, LIBRARY_VERSION)).config

        assert config is not None
        assert (config.spectrum_method, config.transformation_gamma, config.sample_rate) == (
            SpectrumMethod.FFT,
            STORED_GAMMA,
            STORED_SAMPLE_RATE,
        )

    def test_a_load_refuses_it_naming_both_versions(self) -> None:
        with pytest.raises(IncompatibleLibraryDataVersionError) as refused:
            InstructionLibraryData.load(archived(ObjectKind.LIBRARY, LIBRARY_VERSION), fast=False)

        assert (refused.value.actual_version, refused.value.expected_version) == (
            LIBRARY_VERSION,
            SAMPLETONES_LIBRARY_DATA_VERSION,
        )


class TestALibraryArchivedAtTheVersionThisBuildWrites:
    """A library written at the version this build writes is held to what this build generates.

    A library reads as current by its version alone, so a change to the generators or to feature
    extraction bumps the library version, which is what has every stored library rebuilt. Once a
    release archives a library at the version this build writes, this holds that version to the
    output it names.
    """

    def test_it_is_what_this_build_generates_for_the_same_tones(self) -> None:
        path = archived(ObjectKind.LIBRARY, CURRENT_VERSIONS[ObjectKind.LIBRARY])
        if not path.is_file():
            pytest.skip("a release archives a library at the version this build writes first")

        stored = InstructionLibraryData.load(path, fast=False)
        generated = corpus_library()

        assert (stored.config, set(stored.data)) == (generated.config, set(generated.data))
        for instruction, fragment in generated.data.items():
            np.testing.assert_array_equal(stored.data[instruction].sample.array, fragment.sample.array)
            np.testing.assert_allclose(
                stored.data[instruction].feature.values,
                fragment.feature.values,
                rtol=GENERATION_TOLERANCE,
            )
