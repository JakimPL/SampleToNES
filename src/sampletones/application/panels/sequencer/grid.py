import dearpygui.dearpygui as dpg

from sampletones.audio import AudioDeviceManager
from sampletones.constants.general import MAX_CHANGE_RATE, MIN_CHANGE_RATE

from ...config.application.manager import ApplicationConfigManager
from ...config.manager import ConfigManager
from ...constants.general import (
    DIM_INPUT_WIDTH,
    MSG_STATUS_INPUT,
    SUF_PANEL_CENTER,
    TAG_TAB_SEQUENCER,
)
from ...constants.sequencer import (
    DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_INSTRUMENT,
    DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_NOTE,
    DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_ROW,
    DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_VOLUME,
    LBL_BUTTON_SEQUENCER_GRID_EXPORT_MODULE,
    LBL_TABLE_SEQUENCER_GRID_COLUMN_INSTRUMENT,
    LBL_TABLE_SEQUENCER_GRID_COLUMN_NOISE,
    LBL_TABLE_SEQUENCER_GRID_COLUMN_NOTE,
    LBL_TABLE_SEQUENCER_GRID_COLUMN_PULSE_1,
    LBL_TABLE_SEQUENCER_GRID_COLUMN_PULSE_2,
    LBL_TABLE_SEQUENCER_GRID_COLUMN_ROW,
    LBL_TABLE_SEQUENCER_GRID_COLUMN_TRIANGLE,
    LBL_TABLE_SEQUENCER_GRID_COLUMN_VOLUME,
    LBL_TEXT_SEQUENCER_GRID_MODULE_OPTIONS,
    LBL_TEXT_SEQUENCER_GRID_NES_FREQUENCY,
    LBL_TEXT_SEQUENCER_GRID_SPEED,
    LBL_TEXT_SEQUENCER_GRID_TEMPO,
    LBL_TEXT_SEQUENCER_GRID_TRACKER,
    TAG_BUTTON_SEQUENCER_GRID_EXPORT_MODULE,
    TAG_GROUP_SEQUENCER_GRID_MODULE_OPTIONS,
    TAG_INPUT_SEQUENCER_GRID_NES_FREQUENCY,
    TAG_INPUT_SEQUENCER_GRID_SPEED,
    TAG_INPUT_SEQUENCER_GRID_TEMPO,
    TAG_PANEL_SEQUENCER_GRID,
    TAG_PANEL_SEQUENCER_GRID_PLAYER,
    TAG_TABLE_SEQUENCER_GRID_TRACKER,
    TAG_WINDOW_SEQUENCER_GRID_TRACKER,
    VAL_SEQUENCER_GRID_SPEED_DEFAULT,
    VAL_SEQUENCER_GRID_SPEED_MAX,
    VAL_SEQUENCER_GRID_SPEED_MIN,
    VAL_SEQUENCER_GRID_TEMPO_DEFAULT,
    VAL_SEQUENCER_GRID_TEMPO_MAX,
    VAL_SEQUENCER_GRID_TEMPO_MIN,
    VAL_SEQUENCER_GRID_TRACKER_ROWS,
)
from ...elements.button import GUIButton
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.panel import GUIPanel
from ...elements.status import GUIStatusBar
from ...panels.player import GUIAudioPlayerPanel


class GUISequencerGridPanel(GUIPanel):
    def __init__(
        self,
        config_manager: ConfigManager,
        application_config_manager: ApplicationConfigManager,
        audio_device_manager: AudioDeviceManager,
    ) -> None:
        self.config_manager = config_manager
        self.application_config_manager = application_config_manager
        self.audio_device_manager = audio_device_manager

        self.player_panel: GUIAudioPlayerPanel

        super().__init__(
            tag=TAG_PANEL_SEQUENCER_GRID,
            parent=f"{TAG_TAB_SEQUENCER}{SUF_PANEL_CENTER}",
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            width=self.width,
            height=self.height,
            parent=self.parent,
            border=False,
        ):
            self._create_audio_panel()
            self._create_module_options()
            self._create_export_button()
            self._create_tracker_view()

    def _create_audio_panel(self) -> None:
        self.player_panel = GUIAudioPlayerPanel(
            tag=TAG_PANEL_SEQUENCER_GRID_PLAYER,
            parent=TAG_PANEL_SEQUENCER_GRID,
            audio_device_manager=self.audio_device_manager,
        )

    def _create_module_options(self) -> None:
        dpg.add_separator()
        section_text = dpg.add_text(LBL_TEXT_SEQUENCER_GRID_MODULE_OPTIONS)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

        with dpg.group(tag=TAG_GROUP_SEQUENCER_GRID_MODULE_OPTIONS):
            dpg.add_input_int(
                label=LBL_TEXT_SEQUENCER_GRID_NES_FREQUENCY,
                default_value=self.config_manager.config.library.change_rate,
                tag=TAG_INPUT_SEQUENCER_GRID_NES_FREQUENCY,
                min_value=MIN_CHANGE_RATE,
                max_value=MAX_CHANGE_RATE,
                width=DIM_INPUT_WIDTH,
            )
            dpg.add_input_int(
                label=LBL_TEXT_SEQUENCER_GRID_TEMPO,
                default_value=VAL_SEQUENCER_GRID_TEMPO_DEFAULT,
                tag=TAG_INPUT_SEQUENCER_GRID_TEMPO,
                min_value=VAL_SEQUENCER_GRID_TEMPO_MIN,
                max_value=VAL_SEQUENCER_GRID_TEMPO_MAX,
                width=DIM_INPUT_WIDTH,
            )
            dpg.add_input_int(
                label=LBL_TEXT_SEQUENCER_GRID_SPEED,
                default_value=VAL_SEQUENCER_GRID_SPEED_DEFAULT,
                tag=TAG_INPUT_SEQUENCER_GRID_SPEED,
                min_value=VAL_SEQUENCER_GRID_SPEED_MIN,
                max_value=VAL_SEQUENCER_GRID_SPEED_MAX,
                width=DIM_INPUT_WIDTH,
            )

        GUIStatusBar.bind_to_item(TAG_INPUT_SEQUENCER_GRID_NES_FREQUENCY, MSG_STATUS_INPUT)
        GUIStatusBar.bind_to_item(TAG_INPUT_SEQUENCER_GRID_TEMPO, MSG_STATUS_INPUT)
        GUIStatusBar.bind_to_item(TAG_INPUT_SEQUENCER_GRID_SPEED, MSG_STATUS_INPUT)

    def _create_export_button(self) -> None:
        dpg.add_separator()
        GUIButton(
            tag=TAG_BUTTON_SEQUENCER_GRID_EXPORT_MODULE,
            label=LBL_BUTTON_SEQUENCER_GRID_EXPORT_MODULE,
            width=-1,
            font=Font.BOLD,
        )

    def _create_tracker_view(self) -> None:
        dpg.add_separator()
        section_text = dpg.add_text(LBL_TEXT_SEQUENCER_GRID_TRACKER)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

        with dpg.child_window(tag=TAG_WINDOW_SEQUENCER_GRID_TRACKER):
            with dpg.table(
                tag=TAG_TABLE_SEQUENCER_GRID_TRACKER,
                header_row=True,
                resizable=False,
                borders_innerH=True,
                borders_innerV=True,
                borders_outerH=True,
                borders_outerV=True,
                scrollY=True,
                policy=dpg.mvTable_SizingFixedFit,
            ):
                dpg.add_table_column(
                    label=LBL_TABLE_SEQUENCER_GRID_COLUMN_ROW,
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_ROW,
                )
                dpg.add_table_column(
                    label=LBL_TABLE_SEQUENCER_GRID_COLUMN_INSTRUMENT,
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_INSTRUMENT,
                )
                dpg.add_table_column(
                    label=f"{LBL_TABLE_SEQUENCER_GRID_COLUMN_PULSE_1} {LBL_TABLE_SEQUENCER_GRID_COLUMN_NOTE}",
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_NOTE,
                )
                dpg.add_table_column(
                    label=f"{LBL_TABLE_SEQUENCER_GRID_COLUMN_PULSE_1} {LBL_TABLE_SEQUENCER_GRID_COLUMN_VOLUME}",
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_VOLUME,
                )
                dpg.add_table_column(
                    label=f"{LBL_TABLE_SEQUENCER_GRID_COLUMN_PULSE_2} {LBL_TABLE_SEQUENCER_GRID_COLUMN_NOTE}",
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_NOTE,
                )
                dpg.add_table_column(
                    label=f"{LBL_TABLE_SEQUENCER_GRID_COLUMN_PULSE_2} {LBL_TABLE_SEQUENCER_GRID_COLUMN_VOLUME}",
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_VOLUME,
                )
                dpg.add_table_column(
                    label=f"{LBL_TABLE_SEQUENCER_GRID_COLUMN_TRIANGLE} {LBL_TABLE_SEQUENCER_GRID_COLUMN_NOTE}",
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_NOTE,
                )
                dpg.add_table_column(
                    label=f"{LBL_TABLE_SEQUENCER_GRID_COLUMN_TRIANGLE} {LBL_TABLE_SEQUENCER_GRID_COLUMN_VOLUME}",
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_VOLUME,
                )
                dpg.add_table_column(
                    label=f"{LBL_TABLE_SEQUENCER_GRID_COLUMN_NOISE} {LBL_TABLE_SEQUENCER_GRID_COLUMN_NOTE}",
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_NOTE,
                )
                dpg.add_table_column(
                    label=f"{LBL_TABLE_SEQUENCER_GRID_COLUMN_NOISE} {LBL_TABLE_SEQUENCER_GRID_COLUMN_VOLUME}",
                    width_fixed=True,
                    init_width_or_weight=DIM_TABLE_CELL_WIDTH_SEQUENCER_GRID_VOLUME,
                )

                for row_index in range(VAL_SEQUENCER_GRID_TRACKER_ROWS):
                    with dpg.table_row():
                        dpg.add_text(f"{row_index:02d}")
                        dpg.add_text("..")
                        dpg.add_text("...")
                        dpg.add_text(".")
                        dpg.add_text("...")
                        dpg.add_text(".")
                        dpg.add_text("...")
                        dpg.add_text(".")
                        dpg.add_text("...")
                        dpg.add_text(".")
