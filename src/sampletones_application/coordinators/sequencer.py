import dearpygui.dearpygui as dpg

from sampletones_application.config.application.manager import ApplicationConfigManager
from sampletones_application.config.manager import ConfigManager
from sampletones_application.constants.general import (
    DIM_PANEL_HEIGHT_LEFT,
    DIM_PANEL_HEIGHT_RIGHT,
    DIM_PANEL_WIDTH_LEFT,
    LBL_TAB_SEQUENCER,
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    SUF_PANEL_RIGHT,
    TAG_TAB_SEQUENCER,
    TAG_TABS,
)
from sampletones_application.constants.sequencer import DIM_PANEL_WIDTH_SEQUENCER_INSTRUMENTS
from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_application.logic.sequencer.browser import SequencerBrowserLogic
from sampletones_application.logic.sequencer.grid import SequencerGridLogic
from sampletones_application.ui.panels.sequencer.browser.panel import GUISequencerBrowserPanel
from sampletones_application.ui.panels.sequencer.grid.panel import GUISequencerGridPanel
from sampletones_application.ui.panels.sequencer.samples import GUISequencerSamplesPanel
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
    ) -> None:
        self._sequencer_browser_logic: SequencerBrowserLogic = SequencerBrowserLogic(config_manager, browser_manager)
        self._sequencer_browser_panel: GUISequencerBrowserPanel = GUISequencerBrowserPanel(
            self._sequencer_browser_logic,
            application_config_manager,
            audio_device_manager,
            shortcut_manager,
        )
        self._sequencer_grid_logic: SequencerGridLogic = SequencerGridLogic(config_manager)
        self._sequencer_grid_panel: GUISequencerGridPanel = GUISequencerGridPanel(
            self._sequencer_grid_logic,
            audio_device_manager,
        )
        self._sequencer_samples_panel: GUISequencerSamplesPanel = GUISequencerSamplesPanel()

    def create_tab(self) -> None:
        with dpg.tab(
            tag=TAG_TAB_SEQUENCER,
            parent=TAG_TABS,
            label=LBL_TAB_SEQUENCER,
        ):
            with dpg.table(
                parent=TAG_TAB_SEQUENCER,
                header_row=False,
                resizable=False,
                policy=dpg.mvTable_SizingStretchProp,
            ):
                dpg.add_table_column(width_fixed=True)
                dpg.add_table_column()
                dpg.add_table_column(width_fixed=True)

                with dpg.table_row():
                    with dpg.child_window(
                        tag=f"{TAG_TAB_SEQUENCER}{SUF_PANEL_LEFT}",
                        width=DIM_PANEL_WIDTH_LEFT,
                        height=DIM_PANEL_HEIGHT_LEFT,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._sequencer_browser_panel.create_panel()

                    with dpg.child_window(
                        tag=f"{TAG_TAB_SEQUENCER}{SUF_PANEL_CENTER}",
                        no_scroll_with_mouse=True,
                    ):
                        self._sequencer_grid_panel.create_panel()

                    with dpg.child_window(
                        tag=f"{TAG_TAB_SEQUENCER}{SUF_PANEL_RIGHT}",
                        width=DIM_PANEL_WIDTH_SEQUENCER_INSTRUMENTS,
                        height=DIM_PANEL_HEIGHT_RIGHT,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._sequencer_samples_panel.create_panel()
