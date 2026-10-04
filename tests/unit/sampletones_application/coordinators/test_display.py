from typing import Any, Dict, List, Tuple

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.coordinators.display import DisplayCoordinator
from sampletones_application.layout.behavior.display import DisplayBehavior
from sampletones_application.layout.general.window import WindowLayout
from sampletones_application.paths import LANG_EN
from sampletones_application.utils.monitors import MonitorArea
from sampletones_application.view_model.shared.display_settings import (
    DisplaySettings,
    DisplaySettingsViewModel,
    WindowMode,
)
from sampletones_application.viewport import WindowPlacement
from sampletones_shared.display import UNLIMITED_FRAME_RATE, Resolution
from sampletones_shared.types.callback import VoidCallback

STUDIO = "studio"
DARK = "dark"

WIDESCREEN = Resolution(width=1600, height=900)
DEFAULT_RESOLUTION = Resolution(width=1280, height=800)
HAND_SIZED = Resolution(width=1300, height=820)

COUNTDOWN_SECONDS = 10.0

OPENING_X = 120
OPENING_Y = 90
FULLSCREEN_PLACEMENT = WindowPlacement(x=0, y=0, resolution=Resolution(width=1920, height=1080))

BEHAVIOR = DisplayBehavior(
    resolutions=(
        Resolution(width=1024, height=768),
        DEFAULT_RESOLUTION,
        WIDESCREEN,
    ),
    frame_rates=(UNLIMITED_FRAME_RATE, 30, 60, 120),
    revert_countdown_seconds=COUNTDOWN_SECONDS,
)

WINDOW_LAYOUT = WindowLayout(
    width=1280,
    height=800,
    min_width=1024,
    min_height=640,
    position_x=200,
    fullscreen=False,
    max_monitor_ratio=0.9,
    fallback_monitor=Resolution(width=1920, height=1080),
)


class _Palette:
    """Stands in for a loaded palette, which the coordinator only ever reads the name of."""

    def __init__(self, name: str) -> None:
        self.name = name


class _PaletteSourceRecorder:
    def __init__(self) -> None:
        self.palette = _Palette(STUDIO)
        self.activated: List[str] = []

    def activate(self, palette: _Palette) -> None:
        self.activated.append(palette.name)
        self.palette = palette


class _PaletteCatalogRecorder:
    names: Tuple[str, ...] = (DARK, "light", STUDIO)

    def select(self, name: str) -> _Palette:
        return _Palette(name)


class _SessionRecorder:
    def __init__(self) -> None:
        self.palette_name = STUDIO
        self.vsync = True
        self.max_fps = 60
        self.borderless = False
        self.fullscreen = False
        self.writes: List[Tuple[str, Any]] = []

    def set_palette_name(self, name: str) -> None:
        self.writes.append(("palette", name))
        self.palette_name = name

    def set_vsync(self, vsync: bool) -> None:
        self.writes.append(("vsync", vsync))
        self.vsync = vsync

    def set_max_fps(self, max_fps: int) -> None:
        self.writes.append(("max_fps", max_fps))
        self.max_fps = max_fps

    def set_borderless(self, borderless: bool) -> None:
        self.writes.append(("borderless", borderless))
        self.borderless = borderless


class _ViewportRecorder:
    def __init__(self) -> None:
        self.resolution: Tuple[int, int] = (
            DEFAULT_RESOLUTION.width,
            DEFAULT_RESOLUTION.height,
        )
        self.position: Tuple[int, int] = (OPENING_X, OPENING_Y)
        self.fullscreen_toggles = 0
        self.calls: List[Tuple[str, Any]] = []

    @property
    def monitor_area(self) -> MonitorArea:
        return MonitorArea(x=0, y=0, width=1920, height=1080, usable_ratio=0.9)

    @property
    def placement(self) -> WindowPlacement:
        width, height = self.resolution
        x, y = self.position
        return WindowPlacement(x=x, y=y, resolution=Resolution(width=width, height=height))

    def place(self, placement: WindowPlacement) -> None:
        self.calls.append(("place", placement))
        self.position = (placement.x, placement.y)
        self.resolution = (placement.resolution.width, placement.resolution.height)

    def set_resolution(self, width: int, height: int) -> None:
        self.calls.append(("resolution", (width, height)))
        self.resolution = (width, height)

    def set_borderless(self, borderless: bool) -> None:
        self.calls.append(("borderless", borderless))

    def set_vsync(self, vsync: bool) -> None:
        self.calls.append(("vsync", vsync))

    def toggle_fullscreen(self) -> None:
        """Answers the reads DearPyGui gives before a frame: the window keeps the fullscreen place.

        Entering fullscreen is read once a frame is drawn, and leaving it is read only on the next
        frame, so a toggle back with no frame between leaves the fullscreen place standing.
        """
        self.fullscreen_toggles += 1
        self.calls.append(("fullscreen", self.fullscreen_toggles))
        self.position = (FULLSCREEN_PLACEMENT.x, FULLSCREEN_PLACEMENT.y)
        self.resolution = (FULLSCREEN_PLACEMENT.resolution.width, FULLSCREEN_PLACEMENT.resolution.height)


class _FrameLimiterRecorder:
    def __init__(self) -> None:
        self.rates: List[int] = []

    def set_max_fps(self, max_fps: int) -> None:
        self.rates.append(max_fps)


class _WindowRecorder:
    """Stands in for the dialog window, with the modal hand-off collapsed to a direct call.

    The real window defers the modal it yields to by a frame, which is what keeps the two from
    competing for the one modal DearPyGui carries; here the frame is taken as having passed.
    """

    def __init__(self) -> None:
        self.view_models: List[DisplaySettingsViewModel] = []
        self.visible = False
        self.on_settings_changed: Any = None
        self.on_commit: Any = None
        self.on_cancel: Any = None

    def open(self, view_model: DisplaySettingsViewModel) -> None:
        self.visible = True
        self.view_models.append(view_model)

    def update_view(self, view_model: DisplaySettingsViewModel) -> None:
        self.view_models.append(view_model)

    def yield_to(self, raise_modal: VoidCallback) -> None:
        self.visible = False
        raise_modal()

    def resume(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    @property
    def settings(self) -> DisplaySettings:
        return self.view_models[-1].settings


class _CountdownRecorder:
    def __init__(self) -> None:
        self.opens = 0
        self.hides = 0
        self.visible = False
        self.remaining: List[int] = []
        self.on_keep: Any = None
        self.on_revert: Any = None

    def open(self, remaining: int) -> None:
        self.opens += 1
        self.visible = True
        self.remaining.append(remaining)

    def set_remaining(self, remaining: int) -> None:
        self.remaining.append(remaining)

    def hide(self) -> None:
        self.hides += 1
        self.visible = False


class _DialogsRecorder:
    def __init__(self) -> None:
        self.confirmations: List[Dict[str, Any]] = []

    def show_confirmation(self, **kwargs: Any) -> None:
        self.confirmations.append(kwargs)

    def confirm(self) -> None:
        self.confirmations[-1]["on_confirm"]()

    def decline(self) -> None:
        self.confirmations[-1]["on_cancel"]()


class Harness:
    """The coordinator wired to recorders, with the gestures a user makes spelled as methods."""

    def __init__(self) -> None:
        self.session = _SessionRecorder()
        self.viewport = _ViewportRecorder()
        self.frame_limiter = _FrameLimiterRecorder()
        self.palette_source = _PaletteSourceRecorder()
        self.window = _WindowRecorder()
        self.countdown = _CountdownRecorder()
        self.dialogs = _DialogsRecorder()
        self.coordinator = DisplayCoordinator(
            self.session,
            self.viewport,
            self.frame_limiter,
            self.palette_source,
            _PaletteCatalogRecorder(),
            window=self.window,
            countdown=self.countdown,
            behavior=BEHAVIOR,
            window_layout=WINDOW_LAYOUT,
            dialogs=self.dialogs,
            language_manager=LanguageManager(LANG_EN),
        )

    def open(self) -> None:
        self.coordinator.open()

    def change(self, settings: DisplaySettings) -> None:
        self.window.on_settings_changed(settings)

    def commit(self) -> None:
        self.window.on_commit()

    def cancel(self) -> None:
        self.window.on_cancel()

    def keep(self) -> None:
        self.countdown.on_keep()

    def revert(self) -> None:
        self.countdown.on_revert()

    def elapse(self, seconds: float) -> None:
        self.coordinator.tick(seconds)

    def end_the_run(self) -> None:
        self.coordinator.cleanup()

    @property
    def settings(self) -> DisplaySettings:
        return self.window.settings


@pytest.fixture(name="harness")
def harness_fixture() -> Harness:
    harness = Harness()
    harness.open()
    return harness


class TestOpening:
    def test_the_dialog_shows_the_settings_in_force(self, harness: Harness) -> None:
        assert harness.settings == DisplaySettings(
            palette=STUDIO,
            window=WindowMode(resolution=DEFAULT_RESOLUTION, borderless=False, fullscreen=False),
            vsync=True,
            frame_rate=60,
        )

    def test_only_the_sizes_the_monitor_leaves_room_for_are_offered(self, harness: Harness) -> None:
        assert harness.window.view_models[-1].resolutions == BEHAVIOR.resolutions

    def test_every_shipped_palette_is_offered(self, harness: Harness) -> None:
        assert harness.window.view_models[-1].palettes == _PaletteCatalogRecorder.names


class TestLiveApplication:
    def test_a_palette_is_swapped_the_moment_it_is_picked(self, harness: Harness) -> None:
        harness.change(harness.settings.with_palette(DARK))

        assert harness.palette_source.activated == [DARK]

    def test_a_frame_rate_repaces_the_loop_the_moment_it_is_picked(self, harness: Harness) -> None:
        harness.change(harness.settings.with_frame_rate(UNLIMITED_FRAME_RATE))

        assert harness.frame_limiter.rates == [UNLIMITED_FRAME_RATE]

    def test_vsync_reaches_the_viewport_the_moment_it_is_switched(self, harness: Harness) -> None:
        harness.change(harness.settings.with_vsync(False))

        assert ("vsync", False) in harness.viewport.calls

    def test_a_size_reaches_the_viewport_the_moment_it_is_picked(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_resolution(WIDESCREEN)))

        assert (
            "resolution",
            (WIDESCREEN.width, WIDESCREEN.height),
        ) in harness.viewport.calls

    def test_nothing_is_written_to_the_session_before_it_is_confirmed(self, harness: Harness) -> None:
        harness.change(harness.settings.with_palette(DARK))
        harness.change(harness.settings.with_vsync(False))

        assert harness.session.writes == []

    def test_fullscreen_goes_through_the_toggle_the_menu_shares(self, harness: Harness) -> None:
        """The View menu's checkmark follows the viewport manager's own toggle."""
        harness.change(harness.settings.with_window(harness.settings.window.with_fullscreen(True)))

        assert harness.viewport.fullscreen_toggles == 1

    def test_a_fullscreen_window_offers_neither_a_size_nor_a_frame(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_fullscreen(True)))

        assert not harness.window.view_models[-1].window_controls_enabled


class TestCommit:
    def test_confirming_writes_every_setting_to_the_session(self, harness: Harness) -> None:
        harness.change(harness.settings.with_palette(DARK))
        harness.change(harness.settings.with_frame_rate(120))
        harness.commit()

        assert dict(harness.session.writes) == {
            "palette": DARK,
            "vsync": True,
            "max_fps": 120,
            "borderless": False,
        }

    def test_confirming_closes_the_dialog(self, harness: Harness) -> None:
        harness.commit()

        assert not harness.window.visible

    def test_confirming_while_the_clock_runs_keeps_the_change_and_stops_the_clock(
        self,
        harness: Harness,
    ) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_borderless(True)))
        harness.commit()
        harness.elapse(COUNTDOWN_SECONDS)

        assert dict(harness.session.writes)["borderless"] is True
        assert not harness.countdown.visible


class TestCancel:
    def test_canceling_an_untouched_dialog_closes_it_without_asking(self, harness: Harness) -> None:
        harness.cancel()

        assert harness.dialogs.confirmations == []
        assert not harness.window.visible

    def test_canceling_a_changed_dialog_asks_first(self, harness: Harness) -> None:
        harness.change(harness.settings.with_palette(DARK))
        harness.cancel()

        assert len(harness.dialogs.confirmations) == 1

    def test_the_dialog_steps_aside_so_the_prompt_can_open(self, harness: Harness) -> None:
        """A prompt raised while the dialog still holds the screen opens where nobody can reach it."""
        harness.change(harness.settings.with_palette(DARK))
        harness.cancel()

        assert not harness.window.visible

    def test_keeping_the_edit_brings_the_dialog_back(self, harness: Harness) -> None:
        harness.change(harness.settings.with_palette(DARK))
        harness.cancel()
        harness.dialogs.decline()

        assert harness.window.visible
        assert harness.settings.palette == DARK

    def test_discarding_puts_back_the_palette_the_dialog_opened_with(self, harness: Harness) -> None:
        harness.change(harness.settings.with_palette(DARK))
        harness.cancel()
        harness.dialogs.confirm()

        assert harness.palette_source.activated == [DARK, STUDIO]
        assert not harness.window.visible

    def test_discarding_puts_back_the_window_mode_the_dialog_opened_with(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_resolution(WIDESCREEN)))
        harness.cancel()
        harness.dialogs.confirm()

        assert harness.viewport.placement == WindowPlacement(
            x=OPENING_X,
            y=OPENING_Y,
            resolution=DEFAULT_RESOLUTION,
        )

    def test_discarding_writes_nothing_to_the_session(self, harness: Harness) -> None:
        harness.change(harness.settings.with_vsync(False))
        harness.cancel()
        harness.dialogs.confirm()

        assert harness.session.writes == []


class TestCancelingAHandSizedWindow:
    """A window sitting at a size of its own goes back to that exact size and place on Cancel.

    The dialog shows the offered size nearest the window's own, and a discard puts back the opening
    place and size the run ending while the dialog stands puts back. A dialog opened in fullscreen goes
    back to fullscreen and is placed nowhere.
    """

    OPENING_PLACEMENT = WindowPlacement(x=OPENING_X, y=OPENING_Y, resolution=HAND_SIZED)

    @pytest.fixture(name="hand_sized")
    def hand_sized_fixture(self) -> Harness:
        """The dialog opened over a window the user sized by hand, between the sizes on offer."""
        harness = Harness()
        harness.viewport.resolution = (HAND_SIZED.width, HAND_SIZED.height)
        harness.open()
        return harness

    def test_the_dialog_shows_the_offered_size_nearest_the_window(self, hand_sized: Harness) -> None:
        assert hand_sized.settings.window.resolution == DEFAULT_RESOLUTION

    def test_discarding_a_new_size_puts_back_the_window_s_own(self, hand_sized: Harness) -> None:
        hand_sized.change(hand_sized.settings.with_window(hand_sized.settings.window.with_resolution(WIDESCREEN)))
        hand_sized.keep()
        hand_sized.cancel()
        hand_sized.dialogs.confirm()

        assert hand_sized.viewport.placement == self.OPENING_PLACEMENT
        assert not hand_sized.window.visible

    def test_canceling_an_untouched_dialog_leaves_the_window_s_own_size(self, hand_sized: Harness) -> None:
        hand_sized.cancel()

        assert hand_sized.viewport.placement == self.OPENING_PLACEMENT

    def test_discarding_fullscreen_puts_back_the_window_s_own_place(self, hand_sized: Harness) -> None:
        hand_sized.change(hand_sized.settings.with_window(hand_sized.settings.window.with_fullscreen(True)))
        hand_sized.keep()
        hand_sized.cancel()
        hand_sized.dialogs.confirm()

        assert hand_sized.viewport.fullscreen_toggles == 2
        assert hand_sized.viewport.placement == self.OPENING_PLACEMENT

    def test_a_dialog_opened_in_fullscreen_goes_back_to_fullscreen(self) -> None:
        harness = Harness()
        harness.session.fullscreen = True
        harness.open()
        harness.change(harness.settings.with_window(harness.settings.window.with_fullscreen(False)))
        harness.keep()
        harness.cancel()
        harness.dialogs.confirm()

        assert harness.viewport.fullscreen_toggles == 2
        assert all(name != "place" for name, _ in harness.viewport.calls)


class TestCountdown:
    def test_a_window_mode_change_starts_the_clock(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_borderless(True)))

        assert harness.countdown.visible
        assert harness.countdown.remaining[0] == int(COUNTDOWN_SECONDS)

    @pytest.mark.parametrize(
        "field",
        ["palette", "vsync", "frame_rate"],
        ids=["palette", "vsync", "frame_rate"],
    )
    def test_a_change_outside_the_window_mode_leaves_the_clock_alone(
        self,
        harness: Harness,
        field: str,
    ) -> None:
        changes: Dict[str, DisplaySettings] = {
            "palette": harness.settings.with_palette(DARK),
            "vsync": harness.settings.with_vsync(False),
            "frame_rate": harness.settings.with_frame_rate(30),
        }
        harness.change(changes[field])

        assert not harness.countdown.visible

    def test_the_clock_counts_down_in_whole_seconds(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_borderless(True)))
        harness.elapse(1.5)

        assert harness.countdown.remaining[-1] == int(COUNTDOWN_SECONDS) - 1

    def test_the_clock_running_out_puts_the_window_mode_back(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_resolution(WIDESCREEN)))
        harness.elapse(COUNTDOWN_SECONDS)

        assert harness.settings.window.resolution == DEFAULT_RESOLUTION
        assert not harness.countdown.visible

    def test_the_clock_running_out_leaves_every_other_edit_standing(self, harness: Harness) -> None:
        harness.change(harness.settings.with_palette(DARK))
        harness.change(harness.settings.with_window(harness.settings.window.with_resolution(WIDESCREEN)))
        harness.elapse(COUNTDOWN_SECONDS)

        assert harness.settings.palette == DARK
        assert harness.settings.window.resolution == DEFAULT_RESOLUTION

    def test_a_second_change_restarts_one_clock_rather_than_starting_another(
        self,
        harness: Harness,
    ) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_resolution(WIDESCREEN)))
        harness.elapse(4.0)
        harness.change(harness.settings.with_window(harness.settings.window.with_borderless(True)))

        assert harness.countdown.opens == 1
        assert harness.countdown.hides == 0
        assert harness.countdown.remaining[-1] == int(COUNTDOWN_SECONDS)

    def test_a_run_of_changes_returns_to_the_mode_last_seen_as_readable(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_resolution(WIDESCREEN)))
        harness.change(harness.settings.with_window(harness.settings.window.with_borderless(True)))
        harness.elapse(COUNTDOWN_SECONDS)

        assert harness.settings.window == WindowMode(
            resolution=DEFAULT_RESOLUTION,
            borderless=False,
            fullscreen=False,
        )

    def test_the_dialog_steps_aside_so_the_prompt_can_open(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_borderless(True)))

        assert not harness.window.visible

    @pytest.mark.parametrize(
        "answer",
        ["keep", "revert"],
        ids=["keep", "revert"],
    )
    def test_answering_the_prompt_brings_the_dialog_back(self, harness: Harness, answer: str) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_borderless(True)))
        {"keep": harness.keep, "revert": harness.revert}[answer]()

        assert harness.window.visible

    def test_the_clock_running_out_brings_the_dialog_back(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_borderless(True)))
        harness.elapse(COUNTDOWN_SECONDS)

        assert harness.window.visible

    def test_keeping_stops_the_clock_and_leaves_the_change_standing(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_borderless(True)))
        harness.keep()
        harness.elapse(COUNTDOWN_SECONDS)

        assert not harness.countdown.visible
        assert harness.settings.window.borderless is True

    def test_a_kept_change_is_still_undone_by_canceling(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_borderless(True)))
        harness.keep()
        made_before_canceling = len(harness.viewport.calls)
        harness.cancel()
        harness.dialogs.confirm()

        assert ("borderless", False) in harness.viewport.calls[made_before_canceling:]

    def test_reverting_by_hand_puts_the_window_mode_back_at_once(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_resolution(WIDESCREEN)))
        harness.revert()

        assert harness.settings.window.resolution == DEFAULT_RESOLUTION
        assert not harness.countdown.visible

    def test_reverting_a_fullscreen_change_toggles_back(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_fullscreen(True)))
        harness.revert()

        assert harness.viewport.fullscreen_toggles == 2
        assert harness.settings.window.fullscreen is False

    def test_a_closed_dialog_leaves_the_clock_idle(self, harness: Harness) -> None:
        harness.commit()
        harness.elapse(COUNTDOWN_SECONDS)

        assert harness.countdown.remaining == []


class TestClosedDialog:
    def test_editing_a_closed_dialog_is_refused(self, harness: Harness) -> None:
        """A gesture arriving after the dialog closed has no state to edit."""
        settings = harness.settings.with_palette(DARK)
        harness.commit()

        with pytest.raises(SystemError):
            harness.change(settings)


class TestARunEndingWhileTheDialogStands:
    """A run that ends while the dialog stands puts back the display it opened with, as Cancel does.

    The session keeps the opening values until OK, and leaving records the window as it stands, so
    the window returns to its opening place and size first. A change kept on the countdown is
    undone the same way, and a dialog already closed leaves the display as it is.
    """

    OPENING_PLACEMENT = WindowPlacement(x=OPENING_X, y=OPENING_Y, resolution=DEFAULT_RESOLUTION)

    def test_a_size_kept_on_the_countdown_goes_back(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_resolution(WIDESCREEN)))
        harness.keep()

        harness.end_the_run()

        assert harness.viewport.placement == self.OPENING_PLACEMENT

    def test_fullscreen_kept_on_the_countdown_goes_back_to_the_opening_place(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_fullscreen(True)))
        harness.keep()

        harness.end_the_run()

        assert harness.viewport.fullscreen_toggles == 2
        assert harness.viewport.placement == self.OPENING_PLACEMENT

    def test_a_dialog_opened_in_fullscreen_goes_back_to_fullscreen(self) -> None:
        harness = Harness()
        harness.session.fullscreen = True
        harness.open()
        harness.change(harness.settings.with_window(harness.settings.window.with_fullscreen(False)))
        harness.keep()

        harness.end_the_run()

        assert harness.viewport.fullscreen_toggles == 2
        assert all(name != "place" for name, _ in harness.viewport.calls)

    def test_the_palette_goes_back_and_nothing_is_written(self, harness: Harness) -> None:
        harness.change(harness.settings.with_palette(DARK))

        harness.end_the_run()

        assert harness.palette_source.activated == [DARK, STUDIO]
        assert harness.session.writes == []
        assert not harness.window.visible

    def test_a_countdown_running_at_the_end_is_stopped(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_borderless(True)))

        harness.end_the_run()

        assert not harness.countdown.visible
        assert harness.viewport.calls[-1] == ("place", self.OPENING_PLACEMENT)

    def test_a_confirmed_change_stays(self, harness: Harness) -> None:
        harness.change(harness.settings.with_window(harness.settings.window.with_resolution(WIDESCREEN)))
        harness.keep()
        harness.commit()
        calls = list(harness.viewport.calls)

        harness.end_the_run()

        assert harness.viewport.calls == calls
        assert harness.viewport.resolution == (WIDESCREEN.width, WIDESCREEN.height)

    def test_a_dialog_never_opened_leaves_the_display_alone(self) -> None:
        harness = Harness()

        harness.end_the_run()

        assert harness.viewport.calls == []
        assert harness.palette_source.activated == []
