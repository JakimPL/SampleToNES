from typing import Any, Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones.audio import AudioDeviceManager
from sampletones.configs import InstructionsLibraryConfig
from sampletones.exceptions import LibraryDisplayError
from sampletones.instructions import InstructionUnion
from sampletones.library import InstructionLibraryFragment
from sampletones.utils.logger import logger

from ...constants import (
    DIM_WAVEFORM_DEFAULT_HEIGHT,
    LBL_INSTRUCTION_SPECTRUM,
    LBL_INSTRUCTION_WAVEFORM,
    SUF_CENTER_PANEL,
    SUF_INSTRUCTION_SPECTRUM,
    SUF_INSTRUCTION_WAVEFORM,
    TAG_INSTRUCTION_PANEL,
    TAG_INSTRUCTION_PLAYER_PANEL,
    TAG_INSTRUCTION_SPECTRUM_DISPLAY,
    TAG_INSTRUCTION_WAVEFORM_DISPLAY,
    TAG_TAB_INSTRUCTIONS,
    VAL_PLOT_WIDTH_FULL,
)
from ...elements.graphs.spectrum import GUISpectrumDisplay
from ...elements.graphs.waveform import GUIWaveformDisplay
from ...elements.panel import GUIPanel
from ...player.data import AudioData
from ..player import GUIAudioPlayerPanel

OnDisplayInstructionDetailsCallback = Callable[[str, InstructionUnion, Optional[InstructionLibraryFragment[Any]]], None]


class GUIInstructionPanel(GUIPanel):
    def __init__(self, audio_device_manager: AudioDeviceManager) -> None:
        self.audio_device_manager = audio_device_manager
        self.player_panel: GUIAudioPlayerPanel
        self.waveform_display: GUIWaveformDisplay
        self.spectrum_display: GUISpectrumDisplay
        self.library_config: Optional[InstructionsLibraryConfig] = None

        self._on_display_instruction_details: Optional[OnDisplayInstructionDetailsCallback] = None
        self._on_clear_instruction_details: Optional[Callable[[], None]] = None
        self._on_change_audio_state: Optional[Callable[[], None]] = None

        self.waveform_tag = f"{TAG_INSTRUCTION_PANEL}{SUF_INSTRUCTION_WAVEFORM}"
        self.spectrum_tag = f"{TAG_INSTRUCTION_PANEL}{SUF_INSTRUCTION_SPECTRUM}"

        super().__init__(
            tag=TAG_INSTRUCTION_PANEL,
            parent=f"{TAG_TAB_INSTRUCTIONS}{SUF_CENTER_PANEL}",
        )

    def set_callbacks(
        self,
        on_display_instruction_details: Optional[OnDisplayInstructionDetailsCallback] = None,
        on_clear_instruction_details: Optional[Callable[[], None]] = None,
        on_change_audio_state: Optional[Callable[[], None]] = None,
    ) -> None:
        if on_display_instruction_details is not None:
            self._on_display_instruction_details = on_display_instruction_details
        if on_clear_instruction_details is not None:
            self._on_clear_instruction_details = on_clear_instruction_details
        if on_change_audio_state is not None:
            self._on_change_audio_state = on_change_audio_state

    def create_panel(self) -> None:
        self._create_player_panel()
        self._create_waveform_display()
        self._create_spectrum_display()

    def _create_waveform_display(self) -> None:
        with dpg.child_window(
            tag=self.waveform_tag,
            parent=self.parent,
            no_scrollbar=True,
            auto_resize_y=True,
        ):
            self.waveform_display = GUIWaveformDisplay(
                tag=TAG_INSTRUCTION_WAVEFORM_DISPLAY,
                width=VAL_PLOT_WIDTH_FULL,
                height=DIM_WAVEFORM_DEFAULT_HEIGHT,
                parent=self.waveform_tag,
                label=LBL_INSTRUCTION_WAVEFORM,
            )

    def _create_spectrum_display(self) -> None:
        with dpg.child_window(
            tag=self.spectrum_tag,
            parent=self.parent,
            no_scrollbar=True,
            auto_resize_y=True,
        ):
            self.spectrum_display = GUISpectrumDisplay(
                tag=TAG_INSTRUCTION_SPECTRUM_DISPLAY,
                width=VAL_PLOT_WIDTH_FULL,
                height=DIM_WAVEFORM_DEFAULT_HEIGHT,
                parent=self.spectrum_tag,
                label=LBL_INSTRUCTION_SPECTRUM,
            )

    def _create_player_panel(self) -> None:
        self.player_panel = GUIAudioPlayerPanel(
            tag=TAG_INSTRUCTION_PLAYER_PANEL,
            parent=self.parent,
            audio_device_manager=self.audio_device_manager,
            on_position_changed=self._on_player_position_changed,
            on_change_audio_state=self._on_change_audio_state,
        )

    def close_instruction(self) -> None:
        self.library_config = None
        self.player_panel.disable()
        self.waveform_display.clear_layers()
        self.spectrum_display.clear_layers()
        if self._on_clear_instruction_details:
            self._on_clear_instruction_details()

        self.player_panel.enable()

    def is_loaded(self) -> bool:
        return self.library_config is not None

    def display_instruction(
        self,
        generator_class_name: str,
        instruction: InstructionUnion,
        fragment: InstructionLibraryFragment[Any],
        library_config: InstructionsLibraryConfig,
    ) -> None:
        self.library_config = library_config

        self.player_panel.disable()
        if self._on_display_instruction_details:
            self._on_display_instruction_details(generator_class_name, instruction, fragment)

        if fragment:
            sample_rate = library_config.sample_rate
            frame_length = library_config.window_size
            try:
                self.waveform_display.load_library_fragment(fragment)
                self.spectrum_display.load_library_fragment(fragment, sample_rate, frame_length)
            except Exception as exception:
                logger.error_with_traceback(exception, "Error while plotting library data")
                self.player_panel.enable()
                raise LibraryDisplayError("Could not display library data") from exception

            audio_data = AudioData.from_library_fragment(fragment, sample_rate)
            self.player_panel.load_audio_data(audio_data)
        else:
            if self._on_clear_instruction_details:
                self._on_clear_instruction_details()

        self.player_panel.enable()

    def _on_player_position_changed(self, position: int) -> None:
        self.waveform_display.set_position(position)
