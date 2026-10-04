from typing import Final, List, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.settings import TAG_SETTINGS_AUDIO_WINDOW
from sampletones_application.ui.panels.dialogs.audio_settings import GUIAudioSettingsWindow
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.view_model.shared.audio_settings import (
    AudioDeviceItem,
    AudioSettingsViewModel,
)
from sampletones_core.constants.audio import DEFAULT_BUFFER_SIZE, DEFAULT_SAMPLE_RATE, BufferSize, SampleRate
from sampletones_shared.constants.audio import UNITY_GAIN
from tests.suite.frames import Frames
from tests.suite.shortcuts import shipped_source

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
DEVICE_INDEX: Final[int] = 3

Committed = Tuple[int, SampleRate, BufferSize]


@pytest.fixture(name="window")
def window_fixture(dpg_context: None, layout_config: LayoutConfig) -> GUIAudioSettingsWindow:
    return GUIAudioSettingsWindow(
        layout=layout_config.settings,
        language_manager=LANGUAGE_MANAGER,
        key_router=KeyRouter(),
        shortcut_source=shipped_source(),
    )


@pytest.fixture(name="committed")
def committed_fixture(window: GUIAudioSettingsWindow) -> List[Committed]:
    """The settings the owner heard, from a window built the way ``open`` builds it."""
    committed: List[Committed] = []
    window.on_commit = lambda device_index, sample_rate, buffer_size: committed.append(
        (device_index, sample_rate, buffer_size)
    )
    window._seed(
        AudioSettingsViewModel(
            devices=(
                AudioDeviceItem(
                    device_index=DEVICE_INDEX,
                    name="Speakers",
                    sample_rates=(DEFAULT_SAMPLE_RATE,),
                    default_sample_rate=DEFAULT_SAMPLE_RATE,
                ),
            ),
            current_device_index=DEVICE_INDEX,
            current_sample_rate=DEFAULT_SAMPLE_RATE,
            buffer_size=DEFAULT_BUFFER_SIZE,
            master_gain=UNITY_GAIN,
        )
    )
    window.create_window()
    return committed


class TestApplying:
    """Applying can raise a playback error, which opens alone once the settings have left."""

    def test_the_window_leaves_before_the_owner_hears_it(
        self,
        window: GUIAudioSettingsWindow,
        committed: List[Committed],
        held_frames: Frames,
    ) -> None:
        window._commit()

        assert not dpg.does_item_exist(TAG_SETTINGS_AUDIO_WINDOW)
        assert committed == []

    def test_the_owner_hears_what_the_window_held(
        self,
        window: GUIAudioSettingsWindow,
        committed: List[Committed],
        held_frames: Frames,
    ) -> None:
        window._commit()
        held_frames.render()

        assert committed == [(DEVICE_INDEX, DEFAULT_SAMPLE_RATE, DEFAULT_BUFFER_SIZE)]


class TestApplyingWithNoDevice:
    """Apply on a machine offering no output device closes the window and leaves the settings as they
    are: the owner hears nothing, even once the frames after it have run."""

    @pytest.fixture(name="nothing_offered")
    def nothing_offered_fixture(self, window: GUIAudioSettingsWindow) -> List[Committed]:
        """The settings the owner heard, from a window built over a machine offering no device."""
        committed: List[Committed] = []
        window.on_commit = lambda device_index, sample_rate, buffer_size: committed.append(
            (device_index, sample_rate, buffer_size)
        )
        window._seed(
            AudioSettingsViewModel(
                devices=(),
                current_device_index=None,
                current_sample_rate=None,
                buffer_size=DEFAULT_BUFFER_SIZE,
                master_gain=UNITY_GAIN,
            )
        )
        window.create_window()
        return committed

    def test_the_window_closes_and_the_owner_hears_nothing(
        self,
        window: GUIAudioSettingsWindow,
        nothing_offered: List[Committed],
        held_frames: Frames,
    ) -> None:
        window._commit()
        held_frames.render()

        assert not dpg.does_item_exist(TAG_SETTINGS_AUDIO_WINDOW)
        assert nothing_offered == []
