from typing import List

import pytest

from sampletones_tools.calibration.config.referee import RefereeConfig
from sampletones_tools.calibration.referee.auditory import MultiResolutionAuditoryReferee
from sampletones_tools.calibration.referee.panel import build_panel

from .conftest import SAMPLE_RATE

AVAILABILITY = "sampletones_tools.calibration.referee.factory.zimtohrli_available"
LOAD = "sampletones_tools.calibration.referee.panel.RefereeConfig.load"


@pytest.fixture(name="loaded")
def loaded_fixture(monkeypatch: pytest.MonkeyPatch) -> List[RefereeConfig]:
    """Every tuning the panel reads, each a copy of its own, so a second read is told from the first."""
    packaged = RefereeConfig.load()
    loaded: List[RefereeConfig] = []

    def load() -> RefereeConfig:
        loaded.append(packaged.model_copy())
        return loaded[-1]

    monkeypatch.setattr(AVAILABILITY, lambda: False)
    monkeypatch.setattr(LOAD, load)
    return loaded


class TestBuildPanel:
    def test_the_panel_reads_its_tuning_once_and_keeps_it(self, loaded: List[RefereeConfig]) -> None:
        panel = build_panel(SAMPLE_RATE)

        assert len(loaded) == 1
        assert panel.config is loaded[0]

    def test_the_referees_are_built_with_the_tuning_the_panel_keeps(self, loaded: List[RefereeConfig]) -> None:
        panel = build_panel(SAMPLE_RATE)

        auditory = panel.audio[0]
        assert isinstance(auditory, MultiResolutionAuditoryReferee)
        assert auditory.config is panel.config

    def test_the_names_follow_the_order_a_conversion_is_judged_in(self, loaded: List[RefereeConfig]) -> None:
        panel = build_panel(SAMPLE_RATE)

        groups = (panel.audio, panel.truth, panel.trace, panel.conversion)
        assert panel.names == tuple(referee.name for group in groups for referee in group)
