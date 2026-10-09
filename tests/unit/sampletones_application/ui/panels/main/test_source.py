from typing import Final, FrozenSet, Iterator, List, Optional, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.sources import SettingsField, SourceKind
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    LANG_EN,
    LAYOUT_DIRECTORY,
    PALETTES_DIRECTORY,
    THEME_DIRECTORY,
)
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_HANDLER_REGISTRY,
    TAG_GLOBAL_THEME_CHANNEL_MUTED,
    TAG_GLOBAL_THEME_CHANNEL_PULSE1,
    TAG_GLOBAL_THEME_CHANNEL_PULSE1_PARTIAL,
    TAG_GLOBAL_THEME_STEP_BUTTON,
    TAG_GLOBAL_THEME_STEP_BUTTON_DIM,
    TAG_GLOBAL_THEME_STEP_BUTTON_LIT,
    TAG_GLOBAL_THEME_STEP_BUTTON_PARTIAL,
)
from sampletones_application.tags.main import (
    TAG_MAIN_SOURCE_TABLE_CHANNELS,
    TAG_MAIN_SOURCE_TEXT_SUBJECT,
    TAG_MAIN_SOURCE_TOOLTIP_SUBJECT,
)
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.main.source.panel import GUISourceSettingsPanel
from sampletones_application.ui.panels.main.source.rows import ChannelSettingsRows
from sampletones_application.ui.panels.main.source.steps import ChannelCapSteps
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.main.source import (
    CHANNEL_CAP_STEPS,
    ChannelSettingsViewModel,
    InspectedSourceViewModel,
    SourceSettingsPanelViewModel,
)
from sampletones_application.view_model.shared.agreement import Agreement
from sampletones_core.constants.algorithm import UNIT_DRIVE
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName

ROOT_TAG: Final[str] = "test_root"
LOUD_DRIVE: Final[float] = 1.5
DRAGGED_DRIVE: Final[float] = 2.3456
HELD_RECORDINGS: Final[int] = 1939


@pytest.fixture
def layout_config() -> LayoutConfig:
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source)


@pytest.fixture
def dpg_context(layout_config: LayoutConfig) -> Iterator[None]:
    """Stands up the context, fonts, themes and header geometry the card draws under."""
    dpg.create_context()
    FontRegistry.setup(layout_config.fonts)
    FontRegistry.register_fonts(layout_config.fonts.scale)
    setup_themes(THEME_DIRECTORY, PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default))
    GUIPanel.configure_section_header(
        layout_config.glyphs,
        layout_config.general.section_header,
        layout_config.general.collapse,
    )
    try:
        yield
    finally:
        ThemeRegistry.clear()
        dpg.destroy_context()


class Reports:
    """What the card handed on, in the order a reader's gestures reached it."""

    def __init__(self) -> None:
        self.slots: List[Tuple[SettingsField, ChannelName]] = []
        self.drives: List[Tuple[ChannelName, float]] = []
        self.caps: List[int] = []


def line(
    channel_name: ChannelName,
    *,
    use: Agreement = Agreement.ALL,
    bend: Agreement = Agreement.NONE,
    drive: Optional[float] = UNIT_DRIVE,
) -> ChannelSettingsViewModel:
    return ChannelSettingsViewModel(channel=channel_name, use=use, bend=bend, drive=drive)


def view(
    *changed: ChannelSettingsViewModel,
    subject: Optional[InspectedSourceViewModel] = None,
    caps: FrozenSet[int] = frozenset({len(ChannelName)}),
    channels_used: int = len(ChannelName),
    live: bool = True,
) -> SourceSettingsPanelViewModel:
    """A card reading every channel as used at unit drive, but for the lines ``changed`` names."""
    lines = {channel_name: line(channel_name) for channel_name in ChannelName.items()}
    lines.update({item.channel: item for item in changed})
    return SourceSettingsPanelViewModel(
        subject=subject,
        channels=tuple(lines.values()),
        caps=caps,
        channels_used=channels_used,
        live=live,
    )


def recording(name: str) -> InspectedSourceViewModel:
    return InspectedSourceViewModel(name=name, kind=SourceKind.RECORDING, holds=1)


def folder(name: str, holds: int) -> InspectedSourceViewModel:
    return InspectedSourceViewModel(name=name, kind=SourceKind.FOLDER, holds=holds)


def build(
    layout_config: LayoutConfig,
    initial: SourceSettingsPanelViewModel,
) -> Tuple[GUISourceSettingsPanel, Reports]:
    """The card as the application builds it, over the choices it reports."""
    panel = GUISourceSettingsPanel(
        initial,
        layout=layout_config.tabs.main.source,
        inputs=layout_config.general.inputs,
        language_manager=LanguageManager(LANG_EN),
        status_bar=GUIStatusBar(),
    )
    reports = Reports()
    panel.on_slot_toggled = lambda field, channel: reports.slots.append((field, channel))
    panel.on_drive_changed = lambda channel, drive: reports.drives.append((channel, drive))
    panel.on_channel_cap_changed = reports.caps.append
    with dpg.window(tag=ROOT_TAG):
        panel.create_panel(ROOT_TAG)

    return panel, reports


def theme_of(tag: str) -> str:
    return str(dpg.get_item_alias(dpg.get_item_theme(tag)))


def enabled(tag: str) -> bool:
    return bool(dpg.get_item_configuration(tag)["enabled"])


def release(slider_tag: str) -> None:
    """Let go of a slider the way DearPyGui reports it: through the handler bound to it."""
    registry = compose_tag(TAG_MAIN_SOURCE_TABLE_CHANNELS, SUF_HANDLER_REGISTRY)
    [handler] = dpg.get_item_children(registry, 1)
    dpg.get_item_callback(handler)(handler, slider_tag)


class TestWhatTheCardNames:
    def test_a_recording_reads_its_own_name(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reports = build(layout_config, view())

        panel.update_view(view(subject=recording("bass")))

        assert dpg.get_value(TAG_MAIN_SOURCE_TEXT_SUBJECT) == "bass"

    def test_a_folder_reads_how_many_it_stands_for(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reports = build(layout_config, view())

        panel.update_view(view(subject=folder("VEH2 Loops", HELD_RECORDINGS)))

        named = dpg.get_value(TAG_MAIN_SOURCE_TEXT_SUBJECT)
        assert named.startswith("VEH2 Loops")
        assert str(HELD_RECORDINGS) in named

    def test_with_nothing_picked_it_names_the_recordings_added_next(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        build(layout_config, view())

        assert (
            dpg.get_value(TAG_MAIN_SOURCE_TEXT_SUBJECT) == LanguageManager(LANG_EN)["main.source.label.new_recordings"]
        )

    def test_only_the_recordings_added_next_explain_themselves(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        """A picked row names itself; the settings new recordings start with need the words."""
        panel, _reports = build(layout_config, view())
        explained = dpg.get_item_configuration(TAG_MAIN_SOURCE_TOOLTIP_SUBJECT)["show"]

        panel.update_view(view(subject=recording("bass")))

        assert (explained, dpg.get_item_configuration(TAG_MAIN_SOURCE_TOOLTIP_SUBJECT)["show"]) == (True, False)


class TestTheChannelLines:
    def test_every_channel_holds_a_line(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        build(layout_config, view())

        for channel_name in ChannelName.items():
            assert dpg.does_item_exist(ChannelSettingsRows.name_tag(channel_name))
            assert dpg.does_item_exist(ChannelSettingsRows.box_tag(channel_name, SettingsField.CHANNELS))
            assert dpg.does_item_exist(ChannelSettingsRows.slider_tag(channel_name))

    def test_a_bend_stands_only_where_its_channel_reads_one(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        build(layout_config, view())

        bent = {
            channel_name
            for channel_name in ChannelName.items()
            if dpg.does_item_exist(ChannelSettingsRows.box_tag(channel_name, SettingsField.BENDS))
        }
        assert bent == TONE_CHANNELS

    def test_a_channel_every_recording_uses_reads_ticked(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reports = build(layout_config, view())

        panel.update_view(view(line(ChannelName.PULSE2, use=Agreement.NONE)))

        assert dpg.get_value(ChannelSettingsRows.box_tag(ChannelName.PULSE1, SettingsField.CHANNELS)) is True
        assert dpg.get_value(ChannelSettingsRows.box_tag(ChannelName.PULSE2, SettingsField.CHANNELS)) is False

    def test_a_channel_the_folder_half_uses_reads_clear_and_softened(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        """A tick would state an answer the folder has yet to give, so a divided reading is clear."""
        panel, _reports = build(layout_config, view())

        panel.update_view(view(line(ChannelName.PULSE1, use=Agreement.SOME), subject=folder("takes", 2)))

        box = ChannelSettingsRows.box_tag(ChannelName.PULSE1, SettingsField.CHANNELS)
        assert dpg.get_value(box) is False
        assert theme_of(box) == TAG_GLOBAL_THEME_CHANNEL_PULSE1_PARTIAL

    def test_a_channel_no_recording_uses_reads_muted_and_takes_no_bend_or_drive(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        panel, _reports = build(layout_config, view())

        panel.update_view(view(line(ChannelName.PULSE1, use=Agreement.NONE)))

        assert theme_of(ChannelSettingsRows.name_tag(ChannelName.PULSE1)) == TAG_GLOBAL_THEME_CHANNEL_MUTED
        assert enabled(ChannelSettingsRows.box_tag(ChannelName.PULSE1, SettingsField.CHANNELS)) is True
        assert enabled(ChannelSettingsRows.box_tag(ChannelName.PULSE1, SettingsField.BENDS)) is False
        assert enabled(ChannelSettingsRows.slider_tag(ChannelName.PULSE1)) is False

    def test_a_channel_in_use_wears_its_own_color(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        build(layout_config, view())

        assert theme_of(ChannelSettingsRows.name_tag(ChannelName.PULSE1)) == TAG_GLOBAL_THEME_CHANNEL_PULSE1

    def test_a_running_conversion_holds_every_control(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reports = build(layout_config, view())

        panel.update_view(view(live=False))

        assert not enabled(ChannelSettingsRows.box_tag(ChannelName.PULSE1, SettingsField.CHANNELS))
        assert not enabled(ChannelSettingsRows.slider_tag(ChannelName.PULSE1))
        assert not any(enabled(ChannelCapSteps.step_tag(step)) for step in CHANNEL_CAP_STEPS)


class TestTheDrive:
    def test_the_slider_reads_the_drive(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reports = build(layout_config, view())

        panel.update_view(view(line(ChannelName.TRIANGLE, drive=LOUD_DRIVE)))

        assert dpg.get_value(ChannelSettingsRows.slider_tag(ChannelName.TRIANGLE)) == pytest.approx(LOUD_DRIVE)

    def test_a_drive_the_recordings_differ_on_reads_mixed_at_the_calibrated_level(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        panel, _reports = build(layout_config, view())

        panel.update_view(view(line(ChannelName.TRIANGLE, drive=None), subject=folder("takes", 2)))

        slider = ChannelSettingsRows.slider_tag(ChannelName.TRIANGLE)
        assert dpg.get_item_configuration(slider)["format"] == LanguageManager(LANG_EN)["main.source.label.drive_mixed"]
        assert dpg.get_value(slider) == pytest.approx(UNIT_DRIVE)

    def test_a_settled_drive_reads_its_value_again(self, dpg_context: None, layout_config: LayoutConfig) -> None:
        panel, _reports = build(layout_config, view(line(ChannelName.TRIANGLE, drive=None)))

        panel.update_view(view(line(ChannelName.TRIANGLE, drive=LOUD_DRIVE)))

        slider = ChannelSettingsRows.slider_tag(ChannelName.TRIANGLE)
        assert dpg.get_item_configuration(slider)["format"] == layout_config.tabs.main.source.drive_format


class TestTheSteps:
    @pytest.mark.parametrize(
        ("caps", "channels_used", "expected"),
        [
            (frozenset({2}), 4, (TAG_GLOBAL_THEME_STEP_BUTTON, TAG_GLOBAL_THEME_STEP_BUTTON_LIT)),
            (frozenset({1, 2}), 4, (TAG_GLOBAL_THEME_STEP_BUTTON_PARTIAL, TAG_GLOBAL_THEME_STEP_BUTTON_PARTIAL)),
        ],
        ids=["one_count_lit", "differing_counts_half_lit"],
    )
    def test_the_counts_held_light_their_steps(
        self,
        caps: FrozenSet[int],
        channels_used: int,
        expected: Tuple[str, str],
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        panel, _reports = build(layout_config, view())

        panel.update_view(view(caps=caps, channels_used=channels_used))

        assert (theme_of(ChannelCapSteps.step_tag(1)), theme_of(ChannelCapSteps.step_tag(2))) == expected

    def test_a_step_past_the_channels_used_reads_dim_and_still_answers(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        panel, _reports = build(layout_config, view())

        panel.update_view(view(caps=frozenset({1}), channels_used=2))

        step = ChannelCapSteps.step_tag(3)
        assert (theme_of(step), enabled(step)) == (TAG_GLOBAL_THEME_STEP_BUTTON_DIM, True)


class TestTheChoicesTheCardReports:
    """The card settles nothing itself: it names the choice a reader made and hands it on."""

    @pytest.mark.parametrize("field", list(SettingsField))
    def test_a_box_names_the_choice_and_the_channel_it_stands_on(
        self,
        field: SettingsField,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        _panel, reports = build(layout_config, view())
        box = ChannelSettingsRows.box_tag(ChannelName.TRIANGLE, field)

        dpg.get_item_callback(box)(box, True, dpg.get_item_user_data(box))

        assert reports.slots == [(field, ChannelName.TRIANGLE)]

    def test_a_released_slider_names_its_channel_and_the_drive_it_shows(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        """The widget carries its value in single precision, so the drive reported is the one printed."""
        _panel, reports = build(layout_config, view())
        slider = ChannelSettingsRows.slider_tag(ChannelName.NOISE)
        dpg.set_value(slider, DRAGGED_DRIVE)

        release(slider)

        decimals = layout_config.tabs.main.source.drive_decimals
        assert reports.drives == [(ChannelName.NOISE, round(DRAGGED_DRIVE, decimals))]

    @pytest.mark.parametrize("step", CHANNEL_CAP_STEPS)
    def test_a_step_names_its_count(self, step: int, dpg_context: None, layout_config: LayoutConfig) -> None:
        _panel, reports = build(layout_config, view())
        button = ChannelCapSteps.step_tag(step)

        dpg.get_item_callback(button)(button, None, dpg.get_item_user_data(button))

        assert reports.caps == [step]
