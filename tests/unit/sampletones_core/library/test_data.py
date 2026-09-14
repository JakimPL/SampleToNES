from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, Optional
from unittest.mock import patch

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import LIBRARY_PHASES_PER_SAMPLE
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.data import Metadata
from sampletones_core.fft import CyclicArray, Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.fft.features.windowed import WindowedFeatureExtractor
from sampletones_core.generators import PulseGenerator
from sampletones_core.library import InstructionLibraryFragment
from sampletones_core.library.data import InstructionLibraryData
from sampletones_core.structures.histogram import Histogram
from sampletones_shared.application import SAMPLETONES_LIBRARY_DATA_VERSION
from sampletones_shared.exceptions import (
    DeserializationError,
    IncompatibleLibraryDataVersionError,
    InvalidLibraryDataValuesError,
    InvalidMetadataError,
    LoadLibraryError,
    UnhandledLibraryError,
)
from tests.suite.analysis import LIBRARY_TONE, REPAIR_TOLERANCE, analyzed_config
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.errors import DIRECTORY_READ_ERRORS

WINDOWED_GAMMA: Final[int] = 50
LIBRARY_DATA_VERSION_BEFORE_THE_MEAN_SPECTRUM: Final[str] = "2.0"


def _library(metadata: Optional[Metadata] = None) -> InstructionLibraryData:
    library = InstructionLibraryData.create(Config(), {})
    if metadata is not None:
        library = library.model_copy(update={"metadata": metadata})

    return library


class TestRoundTrip:
    def test_save_load_round_trip(self, tmp_path: Path) -> None:
        library = _library()
        path = tmp_path / "demo.ins"

        library.save(path)
        loaded = InstructionLibraryData.load(path)

        assert list(loaded.items) == []
        assert loaded.config == library.config


class TestLoadRejectsForeignFiles:
    def test_garbage_file_raises_load_library_error(
        self,
        tmp_path: Path,
    ) -> None:
        foreign = tmp_path / "foreign.ins"
        foreign.write_bytes(b"garbage-not-a-flatbuffer")

        with pytest.raises(LoadLibraryError):
            InstructionLibraryData.load(foreign)


class TestLoadFileAccess(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        make_path: Callable[[Path], Path]

    test_cases = (
        TestCase(
            label="missing_file",
            make_path=lambda root: root / "fake.ins",
            expected=FileNotFoundError,
        ),
        TestCase(
            label="directory",
            make_path=lambda root: root,
            expected=DIRECTORY_READ_ERRORS,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_inaccessible_path_raises(
        self,
        test_case: TestCase,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(test_case.expected):
            InstructionLibraryData.load(test_case.make_path(tmp_path))


class TestMetadataValidation:
    def test_incompatible_version_propagates(self, tmp_path: Path) -> None:
        library = _library(Metadata(library_data_version="0.0"))
        path = tmp_path / "old.ins"
        library.save(path)

        with pytest.raises(IncompatibleLibraryDataVersionError) as exc_info:
            InstructionLibraryData.load(path)

        assert exc_info.value.actual_version == "0.0"
        assert exc_info.value.expected_version == SAMPLETONES_LIBRARY_DATA_VERSION

    def test_foreign_application_name_propagates(self, tmp_path: Path) -> None:
        library = _library(Metadata(application_name="Foreign"))
        path = tmp_path / "foreign.ins"
        library.save(path)

        with pytest.raises(InvalidMetadataError):
            InstructionLibraryData.load(path)


class TestLoadWrapping(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        side_effect: Exception

    test_cases = (
        TestCase(
            label="invalid_values_wrapped",
            side_effect=TypeError("bad field"),
            expected=InvalidLibraryDataValuesError,
        ),
        TestCase(
            label="unexpected_wrapped_as_unhandled",
            side_effect=RuntimeError("runtime_error"),
            expected=UnhandledLibraryError,
        ),
        TestCase(
            label="domain_error_propagates_unchanged",
            side_effect=DeserializationError("missing getter"),
            expected=DeserializationError,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_load_maps_deserialize_error(
        self,
        test_case: TestCase,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "any.ins"
        path.write_bytes(b"x")
        with patch.object(
            InstructionLibraryData,
            "deserialize",
            side_effect=test_case.side_effect,
        ):
            with pytest.raises(test_case.expected):
                InstructionLibraryData.load(path)


class TestALibraryWrittenBeforeTheMeanSpectrum:
    """
    A 2.0 library averaged a windowed candidate's phases in feature space, and loads with each
    feature restated as the transformed mean of its phase spectra.
    """

    @staticmethod
    def _as_written_at_2_0(extractor: WindowedFeatureExtractor, sample: CyclicArray) -> Histogram:
        """The feature a 2.0 build stored for the sample: the transformed sum of its phase spectra over
        the transformed phase count."""
        transformer = extractor.transformer
        spectra = [
            extractor._normalized_spectrum(
                sample.get_windowed_fragment(phase / LIBRARY_PHASES_PER_SAMPLE, extractor.window)
            )
            for phase in range(LIBRARY_PHASES_PER_SAMPLE)
        ]
        total_values = np.sum([spectrum.values for spectrum in spectra], axis=0, dtype=np.float64)
        total = Histogram(edges=spectra[0].edges.astype(np.float64), values=total_values)
        divisor = transformer.forward(float(LIBRARY_PHASES_PER_SAMPLE))
        return transformer.forward(total).apply_with(lambda densities: densities / divisor).astype(np.float32)

    def test_loads_each_feature_as_the_transformed_mean(self, tmp_path: Path) -> None:
        config = analyzed_config(SpectrumMethod.FFT, gamma=WINDOWED_GAMMA)
        extractor = get_feature_extractor(config, Window.from_config(config))
        assert isinstance(extractor, WindowedFeatureExtractor)
        fragment = InstructionLibraryFragment.create(
            PulseGenerator(config, ChannelName.PULSE1), LIBRARY_TONE, extractor
        )
        written = fragment.model_copy(update={"feature": self._as_written_at_2_0(extractor, fragment.sample)})
        library = InstructionLibraryData.create(config, {LIBRARY_TONE: written}).model_copy(
            update={"metadata": Metadata(library_data_version=LIBRARY_DATA_VERSION_BEFORE_THE_MEAN_SPECTRUM)}
        )
        path = tmp_path / "written_at_2_0.ins"
        library.save(path)

        loaded = InstructionLibraryData.load(path)

        assert loaded.metadata.library_data_version == SAMPLETONES_LIBRARY_DATA_VERSION
        np.testing.assert_allclose(
            loaded.data[LIBRARY_TONE].feature.values, fragment.feature.values, rtol=REPAIR_TOLERANCE
        )
