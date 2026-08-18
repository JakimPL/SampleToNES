from pathlib import Path
from typing import Final, List, Optional

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON
from sampletones_application.tags.settings import (
    TAG_SETTINGS_RENDER_BUTTON_BROWSE,
    TAG_SETTINGS_RENDER_BUTTON_CANCEL,
    TAG_SETTINGS_RENDER_BUTTON_CLOSE,
    TAG_SETTINGS_RENDER_BUTTON_START,
    TAG_SETTINGS_RENDER_CHECKBOX_NORMALIZE,
    TAG_SETTINGS_RENDER_COMBO_BITRATE,
    TAG_SETTINGS_RENDER_COMBO_DEPTH,
    TAG_SETTINGS_RENDER_COMBO_FORMAT,
    TAG_SETTINGS_RENDER_COMBO_SAMPLE_RATE,
    TAG_SETTINGS_RENDER_GROUP_BITRATE,
    TAG_SETTINGS_RENDER_GROUP_DEPTH,
    TAG_SETTINGS_RENDER_GROUP_PROGRESS,
    TAG_SETTINGS_RENDER_GROUP_SETUP,
    TAG_SETTINGS_RENDER_PATH_DESTINATION,
    TAG_SETTINGS_RENDER_PROGRESS,
    TAG_SETTINGS_RENDER_TEXT_DURATION,
    TAG_SETTINGS_RENDER_TEXT_STATUS,
)
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.panels.dialogs.render import GUIRenderWindow
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.view_model.shared.render import (
    RenderPhase,
    SongRenderSettings,
    SongRenderViewModel,
)
from sampletones_core.audio.writers import AudioDepth, AudioFormat
from sampletones_shared.utils.system.paths import shorten_path
from tests.suite.shortcuts import shipped_source

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
DESTINATION: Final[Path] = Path("/home/user/audio/chiptune.wav")
TOTAL_SAMPLES: Final[int] = 44100 * 90
STATUS_TEXT: Final[str] = "Rendering the song..."


def view_model(
    *,
    settings: SongRenderSettings,
    phase: RenderPhase = RenderPhase.CONFIGURING,
    progress: float = 0.0,
) -> SongRenderViewModel:
    return SongRenderViewModel(
        phase=phase,
        formats=(AudioFormat.WAVE, AudioFormat.MP3),
        depths=(AudioDepth.PCM_U8, AudioDepth.PCM_16, AudioDepth.PCM_24),
        settings=settings,
        destination=DESTINATION,
        total_samples=TOTAL_SAMPLES,
        status_text=STATUS_TEXT if phase == RenderPhase.RENDERING else "",
        progress=progress,
    )


def wave_settings() -> SongRenderSettings:
    return SongRenderSettings.initial(AudioFormat.WAVE)


def mp3_settings() -> SongRenderSettings:
    return SongRenderSettings.initial(AudioFormat.MP3)


@pytest.fixture(name="window")
def window_fixture(dpg_context: None, layout_config: LayoutConfig) -> GUIRenderWindow:
    return GUIRenderWindow(
        layout=layout_config.settings,
        path_colors=layout_config.general.colors.paths,
        language_manager=LANGUAGE_MANAGER,
        key_router=KeyRouter(),
        shortcut_source=shipped_source(),
        status_bar=GUIStatusBar(display_time=1.0),
    )


def render(
    window: GUIRenderWindow,
    *,
    settings: Optional[SongRenderSettings] = None,
    phase: RenderPhase = RenderPhase.CONFIGURING,
    progress: float = 0.0,
) -> None:
    """Builds the widget tree for the given state, the way ``open`` does without a live frame."""
    window.update_view(
        view_model(
            settings=settings if settings is not None else wave_settings(),
            phase=phase,
            progress=progress,
        )
    )
    window.create_window()


def press(tag: str) -> None:
    dpg.get_item_callback(compose_tag(tag, SUF_BUTTON))()


class TestTheSetup:
    def test_every_written_container_reaches_the_combo(self, window: GUIRenderWindow) -> None:
        render(window)

        assert dpg.get_item_configuration(TAG_SETTINGS_RENDER_COMBO_FORMAT)["items"] == ["WAV", "MP3"]

    def test_the_rates_offered_are_the_containers_own(self, window: GUIRenderWindow) -> None:
        render(window, settings=mp3_settings())

        assert dpg.get_item_configuration(TAG_SETTINGS_RENDER_COMBO_SAMPLE_RATE)["items"] == [
            "8000 Hz",
            "16000 Hz",
            "22050 Hz",
            "44100 Hz",
            "48000 Hz",
        ]

    def test_a_container_storing_samples_offers_a_depth(self, window: GUIRenderWindow) -> None:
        render(window)

        assert dpg.get_item_configuration(TAG_SETTINGS_RENDER_GROUP_DEPTH)["show"]
        assert not dpg.get_item_configuration(TAG_SETTINGS_RENDER_GROUP_BITRATE)["show"]
        assert dpg.get_value(TAG_SETTINGS_RENDER_COMBO_DEPTH) == "16-bit PCM"

    def test_a_container_encoding_to_a_bitrate_offers_one(self, window: GUIRenderWindow) -> None:
        render(window, settings=mp3_settings())

        assert dpg.get_item_configuration(TAG_SETTINGS_RENDER_GROUP_BITRATE)["show"]
        assert not dpg.get_item_configuration(TAG_SETTINGS_RENDER_GROUP_DEPTH)["show"]
        assert dpg.get_value(TAG_SETTINGS_RENDER_COMBO_BITRATE) == "192 kbps"

    def test_the_song_is_shown_at_the_length_it_renders_to(self, window: GUIRenderWindow) -> None:
        render(window)

        assert dpg.get_value(TAG_SETTINGS_RENDER_TEXT_DURATION) == "1m 30s"

    def test_the_file_and_the_actions_over_it_are_offered(self, window: GUIRenderWindow) -> None:
        render(window)

        assert dpg.get_value(TAG_SETTINGS_RENDER_PATH_DESTINATION) == shorten_path(DESTINATION)
        assert dpg.does_item_exist(TAG_SETTINGS_RENDER_BUTTON_BROWSE)
        assert dpg.does_item_exist(TAG_SETTINGS_RENDER_BUTTON_START)
        assert dpg.does_item_exist(TAG_SETTINGS_RENDER_BUTTON_CLOSE)


class TestTheTwoFaces:
    def test_setting_up_shows_the_setup_alone(self, window: GUIRenderWindow) -> None:
        render(window)

        assert dpg.get_item_configuration(TAG_SETTINGS_RENDER_GROUP_SETUP)["show"]
        assert not dpg.get_item_configuration(TAG_SETTINGS_RENDER_GROUP_PROGRESS)["show"]

    def test_rendering_shows_the_progress_alone(self, window: GUIRenderWindow) -> None:
        render(window, phase=RenderPhase.RENDERING, progress=0.5)

        assert dpg.get_item_configuration(TAG_SETTINGS_RENDER_GROUP_PROGRESS)["show"]
        assert not dpg.get_item_configuration(TAG_SETTINGS_RENDER_GROUP_SETUP)["show"]
        assert dpg.get_value(TAG_SETTINGS_RENDER_PROGRESS) == pytest.approx(0.5)
        assert dpg.get_item_configuration(TAG_SETTINGS_RENDER_PROGRESS)["overlay"] == "50%"
        assert dpg.get_value(TAG_SETTINGS_RENDER_TEXT_STATUS) == STATUS_TEXT

    def test_a_control_off_screen_takes_no_focus(self, window: GUIRenderWindow) -> None:
        """The focus ring skips a disabled stop, which is what keeps Tab on the face being shown."""
        render(window, phase=RenderPhase.RENDERING)

        assert not dpg.get_item_configuration(TAG_SETTINGS_RENDER_COMBO_FORMAT)["enabled"]
        assert not dpg.get_item_configuration(TAG_SETTINGS_RENDER_COMBO_DEPTH)["enabled"]
        assert dpg.get_item_configuration(TAG_SETTINGS_RENDER_BUTTON_CANCEL)["enabled"]

    def test_a_render_already_stopping_takes_no_further_stop(self, window: GUIRenderWindow) -> None:
        render(window, phase=RenderPhase.CANCELLING)

        assert not dpg.get_item_configuration(TAG_SETTINGS_RENDER_BUTTON_CANCEL)["enabled"]

    def test_the_hidden_choice_takes_no_focus(self, window: GUIRenderWindow) -> None:
        render(window, settings=mp3_settings())

        assert not dpg.get_item_configuration(TAG_SETTINGS_RENDER_COMBO_DEPTH)["enabled"]
        assert dpg.get_item_configuration(TAG_SETTINGS_RENDER_COMBO_BITRATE)["enabled"]


class TestReportedEdits:
    """Every control reports the whole edited state, so the owner reconciles one value."""

    @pytest.fixture(name="reported")
    def reported_fixture(self, window: GUIRenderWindow) -> List[SongRenderSettings]:
        reported: List[SongRenderSettings] = []
        window.on_settings_changed = reported.append
        render(window)
        return reported

    def test_picking_a_container_reports_it(
        self,
        window: GUIRenderWindow,
        reported: List[SongRenderSettings],
    ) -> None:
        dpg.get_item_callback(TAG_SETTINGS_RENDER_COMBO_FORMAT)(TAG_SETTINGS_RENDER_COMBO_FORMAT, "MP3")

        assert reported[-1].spec.audio_format == AudioFormat.MP3

    def test_picking_a_rate_reports_it(
        self,
        window: GUIRenderWindow,
        reported: List[SongRenderSettings],
    ) -> None:
        dpg.get_item_callback(TAG_SETTINGS_RENDER_COMBO_SAMPLE_RATE)(
            TAG_SETTINGS_RENDER_COMBO_SAMPLE_RATE,
            "8000 Hz",
        )

        assert reported[-1].spec.sample_rate == 8000

    def test_picking_a_depth_reports_it(
        self,
        window: GUIRenderWindow,
        reported: List[SongRenderSettings],
    ) -> None:
        dpg.get_item_callback(TAG_SETTINGS_RENDER_COMBO_DEPTH)(
            TAG_SETTINGS_RENDER_COMBO_DEPTH,
            "8-bit PCM",
        )

        assert reported[-1].depth == AudioDepth.PCM_U8

    def test_picking_a_bitrate_reports_it(self, window: GUIRenderWindow) -> None:
        reported: List[SongRenderSettings] = []
        window.on_settings_changed = reported.append
        render(window, settings=mp3_settings())

        dpg.get_item_callback(TAG_SETTINGS_RENDER_COMBO_BITRATE)(
            TAG_SETTINGS_RENDER_COMBO_BITRATE,
            "128 kbps",
        )

        assert reported[-1].bitrate == 128

    def test_asking_for_the_peak_to_reach_full_scale_reports_it(
        self,
        window: GUIRenderWindow,
        reported: List[SongRenderSettings],
    ) -> None:
        dpg.get_item_callback(TAG_SETTINGS_RENDER_CHECKBOX_NORMALIZE)(
            TAG_SETTINGS_RENDER_CHECKBOX_NORMALIZE,
            True,
        )

        assert reported[-1].normalize


class TestReportedActions:
    def test_the_browse_button_asks_for_a_file(self, window: GUIRenderWindow) -> None:
        asked: List[None] = []
        window.on_browse = lambda: asked.append(None)
        render(window)

        press(TAG_SETTINGS_RENDER_BUTTON_BROWSE)

        assert asked

    def test_the_render_button_starts_the_render(self, window: GUIRenderWindow) -> None:
        started: List[None] = []
        window.on_render = lambda: started.append(None)
        render(window)

        press(TAG_SETTINGS_RENDER_BUTTON_START)

        assert started

    def test_the_stop_button_stops_a_running_render(self, window: GUIRenderWindow) -> None:
        stopped: List[None] = []
        window.on_cancel = lambda: stopped.append(None)
        render(window, phase=RenderPhase.RENDERING)

        press(TAG_SETTINGS_RENDER_BUTTON_CANCEL)

        assert stopped

    def test_leaving_the_setup_closes_the_dialog(self, window: GUIRenderWindow) -> None:
        closed: List[None] = []
        stopped: List[None] = []
        window.on_close = lambda: closed.append(None)
        window.on_cancel = lambda: stopped.append(None)
        render(window)

        press(TAG_SETTINGS_RENDER_BUTTON_CLOSE)

        assert closed
        assert not stopped

    def test_leaving_a_running_render_stops_it_instead(self, window: GUIRenderWindow) -> None:
        """Escape and the title bar answer through the same handler the Cancel button does."""
        closed: List[None] = []
        stopped: List[None] = []
        window.on_close = lambda: closed.append(None)
        window.on_cancel = lambda: stopped.append(None)
        render(window, phase=RenderPhase.RENDERING)

        press(TAG_SETTINGS_RENDER_BUTTON_CLOSE)

        assert stopped
        assert not closed
