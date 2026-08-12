from dataclasses import dataclass
from typing import Dict, Final, List, cast
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
    TAG_GLOBAL_THEME_INSTRUMENT_TABS,
    TAG_GLOBAL_THEME_INSTRUMENT_TABS_MUTED,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.pitch_stepper import PitchStepperStyle
from sampletones_application.ui.panels.reconstruction.instruments import instruments as instruments_module
from sampletones_application.ui.panels.reconstruction.instruments.instruments import (
    GUIReconstructionInstrumentsPanel,
)
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.reconstruction.instruments import (
    ReconstructionInstrumentsViewModel,
)
from sampletones_application.view_model.shared.footprint import (
    InstrumentSizeViewModel,
    SampleFootprintViewModel,
)
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.formats.famitracker.specification.sequences import (
    MAX_SEQUENCE_ITEMS,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

SEQUENCE_STATUS_KEY: Final[str] = "reconstructions.instruments.message.status_sequence"

NOT_LOADED: Final[ReconstructionInstrumentsViewModel] = ReconstructionInstrumentsViewModel(
    reconstruction_loaded=False,
    playing_generators=frozenset(),
    footprint=None,
)


def build_view_model(
    channel_bytes: Dict[GeneratorName, int],
) -> ReconstructionInstrumentsViewModel:
    """A loaded reconstruction covering the given channels, each measured at the given size."""
    return ReconstructionInstrumentsViewModel(
        reconstruction_loaded=True,
        playing_generators=frozenset(channel_bytes),
        footprint=SampleFootprintViewModel(
            instruments=tuple(
                InstrumentSizeViewModel(generator=generator_name, total_bytes=byte_count)
                for generator_name, byte_count in channel_bytes.items()
            ),
        ),
    )


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


@pytest.fixture(autouse=True)
def bound_themes(monkeypatch: pytest.MonkeyPatch) -> List[str]:
    """Records the theme tags bound to items, standing in for the DPG binding.

    The panel binds a theme wherever it marks an item, so every test stands in for the
    binding and the ones asserting on it read the record.
    """
    tags: List[str] = []
    monkeypatch.setattr(Theme, "bind_to_item", lambda self, item: tags.append(self.tag))
    return tags


@pytest.fixture
def written(monkeypatch: pytest.MonkeyPatch) -> Dict[str, str]:
    """Records the texts written to items, standing in for the DPG values."""
    values: Dict[str, str] = {}
    monkeypatch.setattr(instruments_module, "dpg_set_value", values.__setitem__)
    return values


@pytest.fixture
def shown(monkeypatch: pytest.MonkeyPatch) -> Dict[str, bool]:
    """Records which items the panel shows, standing in for the DPG configuration."""
    flags: Dict[str, bool] = {}

    def configure(tag: str, *, show: bool) -> None:
        flags[tag] = show

    monkeypatch.setattr(instruments_module, "dpg_configure_item", configure)
    return flags


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
        assert bound_themes == [
            TAG_GLOBAL_THEME_INPUT_WARNING,
            TAG_GLOBAL_THEME_DEFAULT,
        ]

    def test_each_dimension_carries_its_own_length(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        bound_themes: List[str],
    ) -> None:
        panel._apply_input_theme(GeneratorName.PULSE1, FeatureKey.VOLUME, MAX_SEQUENCE_ITEMS + 1)
        panel._apply_input_theme(GeneratorName.PULSE1, FeatureKey.ARPEGGIO, 8)
        assert bound_themes == [
            TAG_GLOBAL_THEME_INPUT_WARNING,
            TAG_GLOBAL_THEME_DEFAULT,
        ]


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


class TestSizeFields(BaseTestSuite):
    """The two read-only byte figures: the sample's above the tabs, each channel's inside its tab."""

    @dataclass(frozen=True, kw_only=True)
    class SizeCase(BaseRegularTestCase):
        channel_bytes: Dict[GeneratorName, int]
        expected: str

    test_cases = (
        SizeCase(
            label="a single channel spends what its instrument does",
            channel_bytes={GeneratorName.PULSE1: 777},
            expected="777 B",
        ),
        SizeCase(
            label="three channels spend their instruments together",
            channel_bytes={
                GeneratorName.PULSE1: 777,
                GeneratorName.TRIANGLE: 519,
                GeneratorName.NOISE: 777,
            },
            expected="2073 B",
        ),
        SizeCase(
            label="a silent channel spends the instrument definition alone",
            channel_bytes={GeneratorName.TRIANGLE: 3},
            expected="3 B",
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_the_sample_size_sums_its_channels(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        written: Dict[str, str],
        shown: Dict[str, bool],
        case: SizeCase,
    ) -> None:
        panel.update_view(build_view_model(case.channel_bytes))
        assert written[panel.sample_size_tag] == case.expected

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_each_channel_states_its_own_size(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        written: Dict[str, str],
        shown: Dict[str, bool],
        case: SizeCase,
    ) -> None:
        panel.update_view(build_view_model(case.channel_bytes))
        assert {
            generator_name: written[panel._get_instrument_size_tag(generator_name)]
            for generator_name in case.channel_bytes
        } == {generator_name: f"{byte_count} B" for generator_name, byte_count in case.channel_bytes.items()}

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_a_channel_standing_by_costs_nothing(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        written: Dict[str, str],
        shown: Dict[str, bool],
        case: SizeCase,
    ) -> None:
        """A channel that describes no frame is written by no export, so its tab states what that costs."""
        panel.update_view(build_view_model(case.channel_bytes))
        assert {
            generator_name: written[panel._get_instrument_size_tag(generator_name)]
            for generator_name in GeneratorName.items()
            if generator_name not in case.channel_bytes
        } == {
            generator_name: "0 B"
            for generator_name in GeneratorName.items()
            if generator_name not in case.channel_bytes
        }


class TestPlayingChannels:
    """Every channel keeps a tab; a muted label and a withheld export mark the ones standing by.

    ``update_view`` marks each channel once in channel order, so the recorded bindings read as
    one theme per channel.
    """

    def test_every_channel_keeps_its_tab(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        written: Dict[str, str],
        shown: Dict[str, bool],
    ) -> None:
        panel.update_view(build_view_model({GeneratorName.PULSE1: 777}))
        assert {
            generator_name: shown[panel._get_generator_tab_tag(generator_name)]
            for generator_name in GeneratorName.items()
        } == {generator_name: True for generator_name in GeneratorName.items()}

    def test_a_channel_standing_by_reads_muted(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        written: Dict[str, str],
        shown: Dict[str, bool],
        bound_themes: List[str],
    ) -> None:
        panel.update_view(build_view_model({GeneratorName.PULSE1: 777}))
        assert dict(zip(GeneratorName.items(), bound_themes)) == {
            GeneratorName.PULSE1: TAG_GLOBAL_THEME_INSTRUMENT_TABS,
            GeneratorName.PULSE2: TAG_GLOBAL_THEME_INSTRUMENT_TABS_MUTED,
            GeneratorName.TRIANGLE: TAG_GLOBAL_THEME_INSTRUMENT_TABS_MUTED,
            GeneratorName.NOISE: TAG_GLOBAL_THEME_INSTRUMENT_TABS_MUTED,
        }

    def test_only_a_playing_channel_offers_its_export(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        written: Dict[str, str],
        shown: Dict[str, bool],
    ) -> None:
        buttons = {generator_name: MagicMock() for generator_name in GeneratorName.items()}
        panel._export_buttons.update(cast(Dict[GeneratorName, GUIButton], buttons))

        panel.update_view(build_view_model({GeneratorName.TRIANGLE: 519}))

        assert {generator_name: button.set_enabled.call_args.args[0] for generator_name, button in buttons.items()} == {
            generator_name: generator_name is GeneratorName.TRIANGLE for generator_name in GeneratorName.items()
        }


class TestSizeVisibility:
    def test_a_loaded_reconstruction_shows_the_sample_size(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        written: Dict[str, str],
        shown: Dict[str, bool],
    ) -> None:
        panel.update_view(build_view_model({GeneratorName.PULSE1: 777}))
        assert shown[panel.sample_size_group_tag] is True

    def test_no_reconstruction_hides_the_sample_size(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        written: Dict[str, str],
        shown: Dict[str, bool],
    ) -> None:
        panel.update_view(NOT_LOADED)
        assert shown[panel.sample_size_group_tag] is False

    def test_no_reconstruction_states_no_figures(
        self,
        panel: GUIReconstructionInstrumentsPanel,
        written: Dict[str, str],
        shown: Dict[str, bool],
    ) -> None:
        panel.update_view(NOT_LOADED)
        assert written == {}
