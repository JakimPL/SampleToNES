from dataclasses import dataclass
from typing import Callable, Dict, Final, FrozenSet, List, Sequence, Tuple

import numpy as np
import pytest
from _pytest.mark import ParameterSet

from sampletones_tools.calibration.config.referee import RefereeConfig
from sampletones_tools.calibration.referee.auditory import AUDITORY_REFEREE_NAME, MultiResolutionAuditoryReferee
from sampletones_tools.calibration.referee.loudness import LOUDNESS_REFEREE_NAME, LoudnessWeightedReferee
from sampletones_tools.calibration.referee.protocol import Referee
from sampletones_tools.calibration.referee.zimtohrli import (
    ZIMTOHRLI_REFEREE_NAME,
    ZimtohrliReferee,
    zimtohrli_available,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from .conftest import SAMPLE_RATE, SEMITONE_RATIO, TONE_FREQUENCY, ProbeSignals

Pair = Tuple[np.ndarray, np.ndarray]
PairBuilder = Callable[[ProbeSignals], Pair]

FAINT_HISS_DECIBELS: Final[float] = -40.0
MEDIUM_HISS_DECIBELS: Final[float] = -30.0
LOUD_HISS_DECIBELS: Final[float] = -20.0
QUIETER_DECIBELS: Final[float] = -3.0
IDENTITY_TOLERANCE: Final[float] = 1e-9
REFEREE_NAMES: Final[Tuple[str, ...]] = (AUDITORY_REFEREE_NAME, LOUDNESS_REFEREE_NAME, ZIMTOHRLI_REFEREE_NAME)

KNOWN_FAILURES: Final[Dict[str, FrozenSet[str]]] = {
    AUDITORY_REFEREE_NAME: frozenset(
        {
            "triangle_beats_silence",
            "pulse_beats_silence",
            "semitone_costs_more_than_faint_hiss",
        }
    ),
    LOUDNESS_REFEREE_NAME: frozenset(),
    ZIMTOHRLI_REFEREE_NAME: frozenset(
        {
            "triangle_beats_silence",
            "pulse_beats_silence",
            "semitone_costs_more_than_faint_hiss",
        }
    ),
}


def _sine_against(estimate: Callable[[ProbeSignals], np.ndarray]) -> PairBuilder:
    return lambda probes: (probes.sine, estimate(probes))


def _availability_marks(name: str) -> List[pytest.MarkDecorator]:
    if name == ZIMTOHRLI_REFEREE_NAME and not zimtohrli_available():
        return [pytest.mark.skip(reason="the calibration dependency group provides the model")]

    return []


def _axiom_parameters(cases: Sequence[BaseRegularTestCase]) -> List[ParameterSet]:
    parameters: List[ParameterSet] = []
    for name in REFEREE_NAMES:
        for case in cases:
            marks = _availability_marks(name)
            if case.label in KNOWN_FAILURES[name]:
                marks.append(pytest.mark.xfail(strict=True, reason=f"{name} is known to break this axiom"))
            parameters.append(pytest.param(name, case, marks=marks, id=f"{name}-{case.label}"))

    return parameters


@pytest.fixture(scope="module", name="referees")
def referees_fixture(referee_config: RefereeConfig) -> Dict[str, Callable[[], Referee]]:
    return {
        AUDITORY_REFEREE_NAME: lambda: MultiResolutionAuditoryReferee(SAMPLE_RATE, config=referee_config),
        LOUDNESS_REFEREE_NAME: lambda: LoudnessWeightedReferee(SAMPLE_RATE, config=referee_config),
        ZIMTOHRLI_REFEREE_NAME: lambda: ZimtohrliReferee(SAMPLE_RATE),
    }


class TestRefereeAxioms(BaseTestSuite):
    """
    What any referee standing in for the ear must hear: silence as far from a tone, noise growing
    with its level, a timing roll and a level offset as nearly free, and a wrong pitch as audible.

    A referee known to break an axiom holds it as a strict expected failure, so a fix shows up
    as an unexpected pass.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        closer: PairBuilder
        farther: PairBuilder

    test_cases = (
        TestCase(
            label="triangle_beats_silence",
            closer=_sine_against(lambda probes: probes.triangle()),
            farther=_sine_against(lambda probes: probes.silence),
        ),
        TestCase(
            label="faint_hiss_beats_silence",
            closer=_sine_against(lambda probes: probes.hissing(probes.sine, FAINT_HISS_DECIBELS)),
            farther=_sine_against(lambda probes: probes.silence),
        ),
        TestCase(
            label="pulse_beats_silence",
            closer=_sine_against(lambda probes: probes.pulse()),
            farther=_sine_against(lambda probes: probes.silence),
        ),
        TestCase(
            label="hiss_grows_from_faint_to_medium",
            closer=_sine_against(lambda probes: probes.hissing(probes.sine, FAINT_HISS_DECIBELS)),
            farther=_sine_against(lambda probes: probes.hissing(probes.sine, MEDIUM_HISS_DECIBELS)),
        ),
        TestCase(
            label="hiss_grows_from_medium_to_loud",
            closer=_sine_against(lambda probes: probes.hissing(probes.sine, MEDIUM_HISS_DECIBELS)),
            farther=_sine_against(lambda probes: probes.hissing(probes.sine, LOUD_HISS_DECIBELS)),
        ),
        TestCase(
            label="rolled_pluck_is_nearly_free",
            closer=lambda probes: (probes.pluck, probes.rolled_pluck()),
            farther=lambda probes: (probes.pluck, probes.hissing(probes.pluck, FAINT_HISS_DECIBELS)),
        ),
        TestCase(
            label="quieter_copy_is_nearly_free",
            closer=_sine_against(lambda probes: probes.sine * 10.0 ** (QUIETER_DECIBELS / 20.0)),
            farther=_sine_against(lambda probes: probes.hissing(probes.sine, FAINT_HISS_DECIBELS)),
        ),
        TestCase(
            label="semitone_costs_more_than_faint_hiss",
            closer=_sine_against(lambda probes: probes.hissing(probes.sine, FAINT_HISS_DECIBELS)),
            farther=_sine_against(lambda probes: probes.tone(TONE_FREQUENCY * SEMITONE_RATIO)),
        ),
    )

    @pytest.mark.parametrize(("referee_name", "test_case"), _axiom_parameters(test_cases))
    def test_the_closer_pair_scores_lower(
        self,
        referees: Dict[str, Callable[[], Referee]],
        probes: ProbeSignals,
        referee_name: str,
        test_case: TestCase,
    ) -> None:
        referee = referees[referee_name]()
        closer = referee.judge(*test_case.closer(probes)).score
        farther = referee.judge(*test_case.farther(probes)).score
        assert closer < farther

    @pytest.mark.parametrize(
        "referee_name", [pytest.param(name, marks=_availability_marks(name)) for name in REFEREE_NAMES]
    )
    def test_identical_signals_score_zero(
        self,
        referees: Dict[str, Callable[[], Referee]],
        probes: ProbeSignals,
        referee_name: str,
    ) -> None:
        referee = referees[referee_name]()
        assert referee.judge(probes.sine, probes.sine).score == pytest.approx(0.0, abs=IDENTITY_TOLERANCE)
