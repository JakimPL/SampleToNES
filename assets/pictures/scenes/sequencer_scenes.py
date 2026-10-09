from typing import Final

from assets.pictures.demo import project_document
from assets.pictures.paths import guide_picture
from assets.pictures.writer import Pictures
from automation.boundaries.dialogs import DialogKind
from automation.screen import Screen
from automation.steps.project import leave_letting_the_project_go
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import TAG_GLOBAL_PANEL_PLAYER
from sampletones_application.tags.player import (
    SUF_PLAYER_PAUSE,
    SUF_PLAYER_PLAY,
    SUF_PLAYER_STOP,
)
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_HISTORY_PANEL,
    TAG_SEQUENCER_MODULE_PANEL,
    TAG_SEQUENCER_ORDER_WINDOW_ORDER_CARD,
    TAG_SEQUENCER_TRACKER_PANEL,
    TAG_SEQUENCER_VOICES_PANEL,
)
from sampletones_application.tags.settings import (
    TAG_SETTINGS_NSF_WINDOW,
    TAG_SETTINGS_PROPERTIES_WINDOW,
    TAG_SETTINGS_RENDER_WINDOW,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName

PAGE: Final[str] = "sequencer"
TEMPO: Final[int] = 140
SPEED: Final[int] = 5
CARET_ROW: Final[int] = 7
PLAY_BUTTONS: Final[tuple[str, ...]] = tuple(
    compose_tag(TAG_GLOBAL_PANEL_PLAYER, suffix) for suffix in (SUF_PLAYER_PLAY, SUF_PLAYER_PAUSE, SUF_PLAYER_STOP)
)


def open_the_project(screen: Screen) -> None:
    """Opens the demo project from File ▸ Open project and waits for its voices to be listed."""
    screen.answer_next_dialog(DialogKind.OPEN, project_document())
    screen.project.open()
    screen.expect(screen.sequencer.voices.names, bool, description="the project's voices")
    screen.tabs.bring_to_front(Tab.SEQUENCER)


class SequencerScenes:
    """The Sequencer tab with the demo project open: its cards, the play controls, and the windows the song is
    rendered, exported and described in.

    A window opening with a field in focus shows the caret blinking in it, so the window's title bar is
    clicked first, which takes the focus and keeps the picture the same from one run to the next.
    """

    def picture_voices(self, screen: Screen, pictures: Pictures) -> None:
        open_the_project(screen)
        pictures.rest()

        pictures.around(guide_picture(PAGE, "voices"), TAG_SEQUENCER_VOICES_PANEL)

    def picture_tracker(self, screen: Screen, pictures: Pictures) -> None:
        open_the_project(screen)
        screen.sequencer.tracker.click(CARET_ROW, ChannelName.PULSE1, SubColumn.TRANSPOSE)
        pictures.rest()

        pictures.around(guide_picture(PAGE, "tracker"), TAG_SEQUENCER_TRACKER_PANEL)

    def picture_order(self, screen: Screen, pictures: Pictures) -> None:
        open_the_project(screen)
        pictures.rest()

        pictures.around(guide_picture(PAGE, "order"), TAG_SEQUENCER_ORDER_WINDOW_ORDER_CARD)

    def picture_playback(self, screen: Screen, pictures: Pictures) -> None:
        open_the_project(screen)
        pictures.rest()

        pictures.around(guide_picture(PAGE, "playback"), *PLAY_BUTTONS)

    def picture_module_options(self, screen: Screen, pictures: Pictures) -> None:
        open_the_project(screen)
        pictures.rest()

        pictures.around(guide_picture(PAGE, "module-options"), TAG_SEQUENCER_MODULE_PANEL)

    def picture_history(self, screen: Screen, pictures: Pictures) -> None:
        open_the_project(screen)
        module = screen.sequencer.module
        module.retype_tempo(TEMPO)
        screen.expect(module.tempo, TEMPO.__eq__, description="the tempo retyped")
        module.retype_speed(SPEED)
        screen.expect(module.speed, SPEED.__eq__, description="the speed retyped")
        pictures.rest()

        pictures.around(guide_picture(PAGE, "history"), TAG_SEQUENCER_HISTORY_PANEL)
        leave_letting_the_project_go(screen)

    def picture_nsf_window(self, screen: Screen, pictures: Pictures) -> None:
        open_the_project(screen)
        screen.exports.export_project(MenuElements.ITEM_FILE_EXPORT_NSF)
        screen.expect(screen.exports.nsf.is_shown, bool, description="the NSF window")
        screen.hand.click_title_bar(TAG_SETTINGS_NSF_WINDOW)
        pictures.rest()

        pictures.around(guide_picture(PAGE, "nsf-window"), TAG_SETTINGS_NSF_WINDOW)
        screen.exports.nsf.cancel()

    def picture_render(self, screen: Screen, pictures: Pictures) -> None:
        open_the_project(screen)
        screen.exports.render_song()
        screen.expect(
            screen.exports.render.is_shown,
            bool,
            description="the render window",
        )
        pictures.rest()

        pictures.around(guide_picture(PAGE, "render"), TAG_SETTINGS_RENDER_WINDOW)
        screen.exports.render.cancel()

    def picture_project_properties(self, screen: Screen, pictures: Pictures) -> None:
        open_the_project(screen)
        screen.project.properties.open()
        screen.expect(
            screen.project.properties.is_shown,
            bool,
            description="the properties dialog",
        )
        screen.hand.click_title_bar(TAG_SETTINGS_PROPERTIES_WINDOW)
        pictures.rest()

        pictures.around(
            guide_picture(PAGE, "project-properties"),
            TAG_SETTINGS_PROPERTIES_WINDOW,
        )
        screen.project.properties.cancel()
