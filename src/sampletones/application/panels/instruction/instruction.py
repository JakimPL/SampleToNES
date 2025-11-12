from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones.audio.manager import AudioDeviceManager
from sampletones.configs import LibraryConfig
from sampletones.instructions import InstructionUnion
from sampletones.library import LibraryFragment

from ...constants import (
    DIM_WAVEFORM_DEFAULT_HEIGHT,
    LBL_INSTRUCTION_SPECTRUM,
    LBL_INSTRUCTION_WAVEFORM,
    SUF_INSTRUCTION_SPECTRUM,
    SUF_INSTRUCTION_WAVEFORM,
    TAG_INSTRUCTION_PANEL,
    TAG_INSTRUCTION_PANEL_GROUP,
    TAG_INSTRUCTION_PLAYER_PANEL,
    TAG_INSTRUCTION_SPECTRUM_DISPLAY,
    TAG_INSTRUCTION_WAVEFORM_DISPLAY,
    VAL_PLOT_WIDTH_FULL,
)
from ...elements.graphs.spectrum import GUISpectrumDisplay
from ...elements.graphs.waveform import GUIWaveformDisplay
from ...elements.panel import GUIPanel
from ...player.data import AudioData
from ..player import GUIAudioPlayerPanel


class GUIInstructionPanel(GUIPanel):
    def __init__(self, audio_device_manager: AudioDeviceManager) -> None:
        self.audio_device_manager = audio_device_manager
        self.waveform_display: GUIWaveformDisplay
        self.spectrum_display: GUISpectrumDisplay
        self.player_panel: GUIAudioPlayerPanel
        self.library_config: Optional[LibraryConfig] = None

        self._on_display_instruction_details: Optional[
            Callable[[str, InstructionUnion, Optional[LibraryFragment]], None]
        ] = None
        self._on_clear_instruction_details: Optional[Callable[[], None]] = None

        self.waveform_tag = f"{TAG_INSTRUCTION_PANEL}{SUF_INSTRUCTION_WAVEFORM}"
        self.spectrum_tag = f"{TAG_INSTRUCTION_PANEL}{SUF_INSTRUCTION_SPECTRUM}"

        super().__init__(
            tag=TAG_INSTRUCTION_PANEL,
            parent=TAG_INSTRUCTION_PANEL_GROUP,
        )

    def set_callbacks(
        self,
        on_display_instruction_details: Optional[
            Callable[[str, InstructionUnion, Optional[LibraryFragment]], None]
        ] = None,
        on_clear_instruction_details: Optional[Callable[[], None]] = None,
    ) -> None:
        if on_display_instruction_details is not None:
            self._on_display_instruction_details = on_display_instruction_details
        if on_clear_instruction_details is not None:
            self._on_clear_instruction_details = on_clear_instruction_details

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
            on_position_changed=self._on_player_position_changed,
            audio_device_manager=self.audio_device_manager,
        )

    def display_instruction(
        self,
        generator_class_name: str,
        instruction: InstructionUnion,
        fragment: LibraryFragment,
        library_config: LibraryConfig,
    ) -> None:
        self.library_config = library_config

        if self._on_display_instruction_details:
            self._on_display_instruction_details(generator_class_name, instruction, fragment)

        if fragment:
            sample_rate = library_config.sample_rate
            frame_length = library_config.window_size
            self.waveform_display.load_library_fragment(fragment)
            self.spectrum_display.load_library_fragment(fragment, sample_rate, frame_length)
            audio_data = AudioData.from_library_fragment(fragment, sample_rate)
            self.player_panel.load_audio_data(audio_data)
        else:
            if self._on_clear_instruction_details:
                self._on_clear_instruction_details()

    def _on_player_position_changed(self, position: int) -> None:
        self.waveform_display.set_position(position)
