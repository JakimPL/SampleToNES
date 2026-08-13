import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.categories.pitch import PitchTooltips
from sampletones_application.paths import LANG_EN
from sampletones_core.utils.pitch_kind import PERIOD_VALUE_KIND, PITCH_VALUE_KIND


@pytest.fixture
def language_manager() -> LanguageManager:
    return LanguageManager(LANG_EN)


class TestBuildPitchTooltip:
    def test_fills_every_template_placeholder(self, language_manager: LanguageManager) -> None:
        tooltip = PitchTooltips.build_pitch_tooltip(language_manager, PITCH_VALUE_KIND, "{}/{}/{}")
        assert "{}" not in tooltip
        assert len(tooltip.split("/")) == 3

    def test_example_value_agrees_with_example_name(self, language_manager: LanguageManager) -> None:
        _type_name, example_name, example_value = PitchTooltips.build_pitch_tooltip(
            language_manager, PITCH_VALUE_KIND, "{}|{}|{}"
        ).split("|")
        assert PITCH_VALUE_KIND.to_name(int(example_value)) == example_name

    def test_period_example_value_agrees_with_example_name(self, language_manager: LanguageManager) -> None:
        _type_name, example_name, example_value = PitchTooltips.build_pitch_tooltip(
            language_manager, PERIOD_VALUE_KIND, "{}|{}|{}"
        ).split("|")
        assert PERIOD_VALUE_KIND.to_name(int(example_value)) == example_name

    def test_pitch_and_period_name_the_quantity_differently(self, language_manager: LanguageManager) -> None:
        pitch_type = PitchTooltips.build_pitch_tooltip(language_manager, PITCH_VALUE_KIND, "{}")
        period_type = PitchTooltips.build_pitch_tooltip(language_manager, PERIOD_VALUE_KIND, "{}")
        assert pitch_type != period_type


class TestPitchTooltips:
    """A panel phrases both readings once and picks the one each field takes."""

    def test_a_field_reads_the_help_its_kind_names(self, language_manager: LanguageManager) -> None:
        tooltips = PitchTooltips.build(language_manager, "{}|{}|{}")

        assert tooltips.for_kind(PITCH_VALUE_KIND) == tooltips.pitch
        assert tooltips.for_kind(PERIOD_VALUE_KIND) == tooltips.period

    def test_the_two_readings_phrase_the_same_template_differently(
        self,
        language_manager: LanguageManager,
    ) -> None:
        tooltips = PitchTooltips.build(language_manager, "{}|{}|{}")

        assert tooltips.pitch != tooltips.period
        assert "{}" not in tooltips.pitch
        assert "{}" not in tooltips.period
