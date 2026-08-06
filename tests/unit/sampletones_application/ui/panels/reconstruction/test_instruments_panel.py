from typing import Final, List
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    LANG_EN,
    LAYOUT_DIRECTORY,
    PALETTES_DIRECTORY,
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
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.formats.famitracker.specification.sequences import MAX_SEQUENCE_ITEMS

SEQUENCE_STATUS_KEY: Final[str] = "reconstructions.instruments.message.status_sequence"


@pytest.fixture
def layout_config() -> LayoutConfig:
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source)


@pytest.fixture(autouse=True)
def registered_themes(layout_config: LayoutConfig) -> None:
    """Registers the themes the panel resolves on construction, as startup does."""
    setup_themes(THEME_DIRECTORY, PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default))
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


class TestInstrumentExport:
    """The export button carries the generator whose slice it writes; the destination the
    dialog answers with names the tracker, so no format travels from here."""

    def test_the_generator_reaches_the_export_callback(
        self,
        panel: GUIReconstructionInstrumentsPanel,
    ) -> None:
        calls: List[GeneratorName] = []
        panel.on_instrument_export = calls.append

        panel._export_callback(GeneratorName.NOISE)()

        assert calls == [GeneratorName.NOISE]

    def test_each_generator_gets_its_own_handler(
        self,
        panel: GUIReconstructionInstrumentsPanel,
    ) -> None:
        calls: List[GeneratorName] = []
        panel.on_instrument_export = calls.append

        for generator_name in GeneratorName.items():
            panel._export_callback(generator_name)()

        assert calls == list(GeneratorName.items())

    def test_the_handler_is_one_the_framework_can_dispatch(
        self,
        panel: GUIReconstructionInstrumentsPanel,
    ) -> None:
        """DearPyGui reads a callback's ``__code__`` to decide how many arguments to pass it,
        so a press handler carries one and takes the arguments the framework offers a button.
        """
        callback = panel._export_callback(GeneratorName.NOISE)

        assert callback.__code__.co_argcount == 0


class TestSequenceStatusMessage:
    def test_a_sequence_within_the_limit_describes_editing(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        bound_themes: List[str],
    ) -> None:
        panel._apply_input_theme(GeneratorName.PULSE1, FeatureKey.VOLUME, 16)
        message = panel._sequence_status_message(GeneratorName.PULSE1, FeatureKey.VOLUME)
        assert message == panel._language_manager[SEQUENCE_STATUS_KEY].format(
            instrument_feature=FeatureKey.VOLUME.capitalized
        )

    def test_a_sequence_beyond_the_limit_names_the_limit(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        bound_themes: List[str],
    ) -> None:
        panel._apply_input_theme(GeneratorName.PULSE1, FeatureKey.VOLUME, 300)
        message = panel._sequence_status_message(GeneratorName.PULSE1, FeatureKey.VOLUME)
        assert "300" in message
        assert str(MAX_SEQUENCE_ITEMS) in message
