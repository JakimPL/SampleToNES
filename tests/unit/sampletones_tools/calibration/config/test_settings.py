import pytest
from pydantic import ValidationError

from sampletones_core.configs import Config
from sampletones_tools.calibration.config.settings import SettingsConfig, overridden


class TestSettingsConfig:
    def test_every_packaged_set_names_settings_the_configuration_holds(self) -> None:
        for overrides in SettingsConfig.load().settings.values():
            assert isinstance(overridden(Config(), overrides), Config)


class TestOverridden:
    def test_a_set_changes_the_values_it_names_and_keeps_the_rest_of_their_section(self) -> None:
        base = Config()
        changed = overridden(base, {"generation": {"decoder": {"top_k": base.generation.decoder.top_k + 1}}})

        assert changed.generation.decoder.top_k == base.generation.decoder.top_k + 1
        assert changed.generation.decoder.selector == base.generation.decoder.selector
        assert changed.generation.metric == base.generation.metric

    def test_a_set_naming_an_unknown_setting_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            overridden(Config(), {"generation": {"decoder": {"selektor": "greedy"}}})
