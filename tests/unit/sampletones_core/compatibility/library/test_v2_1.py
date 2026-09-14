import copy
from dataclasses import dataclass
from typing import Any, Dict, Final, List

import numpy as np
import pytest

from sampletones_core.compatibility.fields import (
    CONFIG,
    EDGES,
    FEATURE,
    FRAGMENT,
    ITEMS,
    SPECTRUM_METHOD,
    TRANSFORMATION_GAMMA,
    VALUES,
)
from sampletones_core.compatibility.library.v2_1 import PHASES_PER_SAMPLE, update
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.fft.transformer import FFTTransformer
from sampletones_core.structures.histogram import Histogram
from tests.suite.analysis import REPAIR_TOLERANCE
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase

SAMPLE_RATE: Final[int] = 44100
BINS: Final[int] = 6
SEED: Final[int] = 3
EDGES_VALUES: Final[np.ndarray] = np.array([0.0, 20.0, 60.0, 100.0, 180.0, 300.0, 500.0], dtype=np.float32)
INSTRUCTION_DATA: Final[Dict[str, Any]] = {"instruction_class": "PulseInstruction", "instruction": {"pitch": 57}}


def _phase_spectra() -> List[Histogram]:
    """Phase spectra spanning the floor, as one candidate's phases would."""
    levels = np.random.default_rng(SEED).exponential(1e-2, (PHASES_PER_SAMPLE, BINS)).astype(np.float32)
    return [Histogram(edges=EDGES_VALUES, values=values) for values in levels]


def _averaged_as_2_0(transformer: FFTTransformer, spectra: List[Histogram]) -> Histogram:
    """The feature a 2.0 build stored: the transformed sum of the spectra over the transformed count."""
    total = Histogram(edges=EDGES_VALUES, values=np.sum([spectrum.values for spectrum in spectra], axis=0))
    divisor = transformer.forward(float(len(spectra)))
    return transformer.forward(total).apply_with(lambda densities: densities / divisor)


def _payload(method: SpectrumMethod, gamma: int, feature: Histogram) -> Dict[str, Any]:
    return {
        CONFIG: {SPECTRUM_METHOD: method.value, TRANSFORMATION_GAMMA: gamma, "sample_rate": SAMPLE_RATE},
        ITEMS: [
            {
                "instruction_data": INSTRUCTION_DATA,
                FRAGMENT: {
                    "generator_class": "PulseGenerator",
                    "sample": {"array": b"\x00\x00\x00\x00"},
                    FEATURE: {
                        EDGES: feature.edges.astype(np.float32).tobytes(),
                        VALUES: feature.values.astype(np.float32).tobytes(),
                    },
                },
            }
        ],
    }


def _stored_values(payload: Dict[str, Any]) -> np.ndarray:
    return np.frombuffer(payload[ITEMS][0][FRAGMENT][FEATURE][VALUES], dtype=np.float32)


class TestAWindowedLibraryRepairsToTheMeanSpectrum(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: None = None
        method: SpectrumMethod
        gamma: int

        @property
        def label(self) -> str:
            return f"{self.method.value}_gamma_{self.gamma}"

    test_cases = (
        TestCase(method=SpectrumMethod.FFT, gamma=50),
        TestCase(method=SpectrumMethod.FFT, gamma=100),
        TestCase(method=SpectrumMethod.LOG_SPACED_FFT, gamma=25),
        TestCase(method=SpectrumMethod.LOG_SPACED_FFT, gamma=100),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_stored_feature_becomes_the_transformed_mean(self, test_case: TestCase) -> None:
        transformer = FFTTransformer.from_gamma(test_case.gamma, SAMPLE_RATE)
        spectra = _phase_spectra()
        payload = _payload(test_case.method, test_case.gamma, _averaged_as_2_0(transformer, spectra))

        mean_values = np.mean([spectrum.values for spectrum in spectra], axis=0, dtype=np.float64)
        expected = transformer.forward(Histogram(edges=EDGES_VALUES, values=mean_values.astype(np.float32)))

        np.testing.assert_allclose(_stored_values(update(payload)), expected.values, rtol=REPAIR_TOLERANCE)


class TestWhatTheRepairLeavesAlone:
    @staticmethod
    def _payload(method: SpectrumMethod, gamma: int) -> Dict[str, Any]:
        transformer = FFTTransformer.from_gamma(gamma, SAMPLE_RATE)
        return _payload(method, gamma, _averaged_as_2_0(transformer, _phase_spectra()))

    def test_a_constant_q_library_averaged_its_spectra_already(self) -> None:
        payload = self._payload(SpectrumMethod.CQT, 50)

        assert update(payload) is payload

    def test_an_identity_transform_averages_the_spectra_already(self) -> None:
        payload = self._payload(SpectrumMethod.FFT, 0)

        assert update(payload) is payload

    def test_every_field_beside_the_feature_values_stays(self) -> None:
        payload = self._payload(SpectrumMethod.FFT, 50)

        repaired = update(payload)
        item, repaired_item = payload[ITEMS][0], repaired[ITEMS][0]

        assert repaired[CONFIG] == payload[CONFIG]
        assert repaired_item["instruction_data"] == item["instruction_data"]
        assert repaired_item[FRAGMENT]["sample"] == item[FRAGMENT]["sample"]
        assert repaired_item[FRAGMENT][FEATURE][EDGES] == item[FRAGMENT][FEATURE][EDGES]

    def test_leaves_the_input_untouched(self) -> None:
        payload = self._payload(SpectrumMethod.FFT, 100)
        snapshot = copy.deepcopy(payload)

        update(payload)

        assert payload == snapshot
