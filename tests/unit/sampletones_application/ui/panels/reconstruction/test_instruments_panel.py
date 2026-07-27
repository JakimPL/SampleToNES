from typing import List
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    LANG_EN,
    LAYOUT_DIRECTORY,
    PALETTE_PATH,
    THEME_DIRECTORY,
)
from sampletones_application.tags.general import (
    TAG_GLOBAL_THEME_DEFAULT,
    TAG_GLOBAL_THEME_INPUT_WARNING,
)
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.pitch_stepper import PitchStepperStyle
from sampletones_application.ui.panels.reconstruction.instruments.instruments import (
    GUIReconstructionInstrumentsPanel,
)
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.palette import Palette
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.famitracker.specification.sequences import MAX_SEQUENCE_ITEMS


@pytest.fixture
def layout_config() -> LayoutConfig:
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, Palette.load(PALETTE_PATH))


@pytest.fixture(autouse=True)
def registered_themes(layout_config: LayoutConfig) -> None:
    """Registers the themes the panel resolves on construction, as startup does."""
    setup_themes(THEME_DIRECTORY, Palette.load(PALETTE_PATH))
    GUIPanel.configure_section_header(
        layout_config.glyphs,
        layout_config.general.section_header,
        layout_config.general.collapse,
    )


@pytest.fixture
def bound_themes(monkeypatch: pytest.MonkeyPatch) -> List[str]:
    """Records the theme tags bound to items, standing in for the DPG binding."""
    tags: List[str] = []
    monkeypatch.setattr(Theme, "bind_to_item", lambda self, item: tags.append(self.tag))
    return tags


@pytest.fixture
def panel(layout_config: LayoutConfig) -> GUIReconstructionInstrumentsPanel:
    return GUIReconstructionInstrumentsPanel(
        pitch_stepper_style=PitchStepperStyle.from_general(layout_config.general),
        copy_width=layout_config.general.buttons.copy_width,
        feature_colors=layout_config.general.colors.features,
        layout_graphs=layout_config.graphs,
        language_manager=LanguageManager(LANG_EN),
        status_bar=MagicMock(),
    )


class TestSequenceLengthWarning:
    @pytest.mark.parametrize(
        "item_count",
        [0, 1, MAX_SEQUENCE_ITEMS],
        ids=["empty", "single", "at_the_limit"],
    )
    def test_a_sequence_within_the_limit_keeps_the_default_theme(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        bound_themes: List[str],
        item_count: int,
    ) -> None:
        panel._apply_input_theme(GeneratorName.PULSE1, FeatureKey.VOLUME, item_count)
        assert bound_themes == [TAG_GLOBAL_THEME_DEFAULT]

    def test_a_sequence_beyond_the_limit_takes_the_warning_theme(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        bound_themes: List[str],
    ) -> None:
        panel._apply_input_theme(GeneratorName.PULSE1, FeatureKey.VOLUME, MAX_SEQUENCE_ITEMS + 1)
        assert bound_themes == [TAG_GLOBAL_THEME_INPUT_WARNING]

    def test_a_shortened_sequence_returns_to_the_default_theme(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        bound_themes: List[str],
    ) -> None:
        panel._apply_input_theme(GeneratorName.NOISE, FeatureKey.VOLUME, MAX_SEQUENCE_ITEMS + 40)
        panel._apply_input_theme(GeneratorName.NOISE, FeatureKey.VOLUME, MAX_SEQUENCE_ITEMS)
        assert bound_themes == [TAG_GLOBAL_THEME_INPUT_WARNING, TAG_GLOBAL_THEME_DEFAULT]

    def test_each_dimension_carries_its_own_length(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        bound_themes: List[str],
    ) -> None:
        panel._apply_input_theme(GeneratorName.PULSE1, FeatureKey.VOLUME, MAX_SEQUENCE_ITEMS + 1)
        panel._apply_input_theme(GeneratorName.PULSE1, FeatureKey.ARPEGGIO, 8)
        assert bound_themes == [TAG_GLOBAL_THEME_INPUT_WARNING, TAG_GLOBAL_THEME_DEFAULT]


class TestSequenceStatusMessage:
    def test_a_sequence_within_the_limit_describes_editing(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        bound_themes: List[str],
    ) -> None:
        panel._apply_input_theme(GeneratorName.PULSE1, FeatureKey.VOLUME, 16)
        message = panel._sequence_status_message(GeneratorName.PULSE1, FeatureKey.VOLUME)
        assert message == panel._msg_sequence.format(instrument_feature=FeatureKey.VOLUME.capitalized)

    def test_a_sequence_beyond_the_limit_names_the_limit(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        bound_themes: List[str],
    ) -> None:
        panel._apply_input_theme(GeneratorName.PULSE1, FeatureKey.VOLUME, 300)
        message = panel._sequence_status_message(GeneratorName.PULSE1, FeatureKey.VOLUME)
        assert "300" in message
        assert str(MAX_SEQUENCE_ITEMS) in message
