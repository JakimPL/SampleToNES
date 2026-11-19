import pytest

from sampletones_tools.calibration.referee.auditory import AUDITORY_REFEREE_NAME
from sampletones_tools.calibration.referee.balance import BALANCE_REFEREE
from sampletones_tools.calibration.referee.continuity import CONTINUITY_REFEREE
from sampletones_tools.calibration.referee.contour import CONTOUR_REFEREE
from sampletones_tools.calibration.referee.factory import build_referees, build_truth_referees
from sampletones_tools.calibration.referee.loudness import LOUDNESS_REFEREE_NAME
from sampletones_tools.calibration.referee.pitch import PITCH_REFEREE
from sampletones_tools.calibration.referee.stability import STABILITY_REFEREE
from sampletones_tools.calibration.referee.transcription import TRANSCRIPTION_REFEREE
from sampletones_tools.calibration.referee.zimtohrli import ZIMTOHRLI_REFEREE_NAME, zimtohrli_available

from .conftest import SAMPLE_RATE

AVAILABILITY = "sampletones_tools.calibration.referee.factory.zimtohrli_available"


class TestBuildReferees:
    def test_the_built_in_referees_lead_with_the_headline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(AVAILABILITY, lambda: False)
        assert [referee.name for referee in build_referees(SAMPLE_RATE)] == [
            AUDITORY_REFEREE_NAME,
            LOUDNESS_REFEREE_NAME,
            CONTOUR_REFEREE,
        ]

    @pytest.mark.skipif(not zimtohrli_available(), reason="the calibration dependency group provides the model")
    def test_zimtohrli_joins_where_its_extra_is_installed(self) -> None:
        assert [referee.name for referee in build_referees(SAMPLE_RATE)][-1] == ZIMTOHRLI_REFEREE_NAME


class TestBuildTruthReferees:
    def test_the_transcription_leads_the_rest_of_the_truth_referees(self) -> None:
        assert [referee.name for referee in build_truth_referees()] == [
            TRANSCRIPTION_REFEREE,
            PITCH_REFEREE,
            STABILITY_REFEREE,
            BALANCE_REFEREE,
            CONTINUITY_REFEREE,
        ]
