import pytest

from sampletones_tools.calibration.referee.zimtohrli import OPINION_COMPONENT, ZimtohrliReferee, zimtohrli_available

from .conftest import SAMPLE_RATE, ProbeSignals

zimtohrli_installed = pytest.mark.skipif(
    not zimtohrli_available(),
    reason="the calibration dependency group provides the model",
)


@pytest.fixture(scope="module", name="referee")
def referee_fixture() -> ZimtohrliReferee:
    return ZimtohrliReferee(SAMPLE_RATE)


@zimtohrli_installed
class TestZimtohrliReferee:
    def test_identical_signals_score_zero(self, referee: ZimtohrliReferee, probes: ProbeSignals) -> None:
        assert referee.judge(probes.sine, probes.sine).score == pytest.approx(0.0, abs=1e-9)

    def test_the_opinion_score_is_reported_beside_the_distance(
        self,
        referee: ZimtohrliReferee,
        probes: ProbeSignals,
    ) -> None:
        identical = referee.judge(probes.sine, probes.sine).components[OPINION_COMPONENT]
        noisy = referee.judge(probes.sine, probes.hissing(probes.sine, -20.0)).components[OPINION_COMPONENT]
        assert noisy < identical

    def test_length_mismatch_raises_value_error(self, referee: ZimtohrliReferee, probes: ProbeSignals) -> None:
        with pytest.raises(ValueError):
            referee.judge(probes.sine, probes.sine[:-1])
