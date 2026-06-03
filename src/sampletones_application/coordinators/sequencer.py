import dearpygui.dearpygui as dpg

from sampletones_application.config.application.manager import ApplicationConfigManager
from sampletones_application.config.manager import ConfigManager
from sampletones_application.constants.general import (
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    SUF_PANEL_RIGHT,
    TAG_TAB_GLOBAL_SEQUENCER,
    TAG_TABS_GLOBAL,
)
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_application.logic.sequencer.browser import SequencerBrowserLogic
from sampletones_application.logic.sequencer.grid import SequencerGridLogic
from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.text.elements.global_ import MenuElements
from sampletones_application.text.hierarchy import Page, Panel, TextType
from sampletones_application.text.key import TextKey
from sampletones_application.text.manager import LanguageManager
from sampletones_application.ui.panels.sequencer.browser import GUISequencerBrowserPanel
from sampletones_application.ui.panels.sequencer.grid import GUISequencerGridPanel
from sampletones_application.ui.panels.sequencer.samples import GUISequencerSamplesPanel
from sampletones_application.utils.dialogs import DialogsRenderer
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_core.audio import AudioDeviceManager


class SequencerTabCoordinator:
    def __init__(
        self,
        config_manager: ConfigManager,
        application_config_manager: ApplicationConfigManager,
        audio_device_manager: AudioDeviceManager,
        shortcut_manager: ShortcutManager,
        browser_manager: BrowserManager,
        *,
        layout: LayoutConfig,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
    ) -> None:
        self._tab_label = language_manager[TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.TAB_SEQUENCER)]
        self._left_width = layout.general.panels.left.width
        self._left_height = layout.general.panels.left.height
        self._instruments_width = layout.sequencer.instruments_panel_width
        self._right_height = layout.general.panels.right.height

        self._sequencer_browser_logic: SequencerBrowserLogic = SequencerBrowserLogic(config_manager, browser_manager)
        self._sequencer_browser_panel: GUISequencerBrowserPanel = GUISequencerBrowserPanel(
            self._sequencer_browser_logic,
            application_config_manager,
            audio_device_manager,
            shortcut_manager,
            scheduling=layout.behavior.scheduling,
            tree_behavior=layout.behavior.sequencer,
            language_manager=language_manager,
        )
        self._sequencer_grid_logic: SequencerGridLogic = SequencerGridLogic(config_manager)
        self._sequencer_player_logic = PlayerLogic(audio_device_manager)
        self._sequencer_grid_panel: GUISequencerGridPanel = GUISequencerGridPanel(
            self._sequencer_grid_logic,
            self._sequencer_player_logic,
            layout=layout.sequencer,
            layout_player=layout.player,
            input_width=layout.general.inputs.default_width,
            language_manager=language_manager,
            dialogs=dialogs,
        )
        self._sequencer_samples_panel: GUISequencerSamplesPanel = GUISequencerSamplesPanel(
            layout=layout.sequencer,
            language_manager=language_manager,
        )

    def create_tab(self) -> None:
        with dpg.tab(
            tag=TAG_TAB_GLOBAL_SEQUENCER,
            parent=TAG_TABS_GLOBAL,
            label=self._tab_label,
        ):
            with dpg.table(
                parent=TAG_TAB_GLOBAL_SEQUENCER,
                header_row=False,
                resizable=False,
                policy=dpg.mvTable_SizingStretchProp,
            ):
                dpg.add_table_column(width_fixed=True)
                dpg.add_table_column()
                dpg.add_table_column(width_fixed=True)

                with dpg.table_row():
                    with dpg.child_window(
                        tag=f"{TAG_TAB_GLOBAL_SEQUENCER}{SUF_PANEL_LEFT}",
                        width=self._left_width,
                        height=self._left_height,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._sequencer_browser_panel.create_panel()

                    with dpg.child_window(
                        tag=f"{TAG_TAB_GLOBAL_SEQUENCER}{SUF_PANEL_CENTER}",
                        no_scroll_with_mouse=True,
                    ):
                        self._sequencer_grid_panel.create_panel()

                    with dpg.child_window(
                        tag=f"{TAG_TAB_GLOBAL_SEQUENCER}{SUF_PANEL_RIGHT}",
                        width=self._instruments_width,
                        height=self._right_height,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._sequencer_samples_panel.create_panel()
