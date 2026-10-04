import operator
from functools import partial

from sampletones_application.ui.themes.channels import PARTIAL_CHANNEL_THEME_TAGS
from sampletones_core.constants.enums import ChannelName
from tests.screens.main.row_settings.constants import PAIR, PAIR_TAKES
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.main import gather, home_path
from tests.suite.screens.vocabulary.converter import FOLDER_ROW


class TestAFoldersBoxes:
    """A folder's box reads partial where its recordings disagree; one click on it settles them all and the
    next click lets them go.

    The folder of two takes is gathered and opened. The scenario clicks Pulse 1 on one take, then on the
    folder, then on the folder again, and expects the folder's box to turn partial, then every take to
    hold the box, then every take to let it go.
    """

    def test_a_box_inside_turns_the_folders_partial_and_the_folders_settles_them(self, screen: Screen) -> None:
        main = screen.main
        listing = main.converter.list
        folder = home_path(PAIR)
        first, second = (folder / name for name in PAIR_TAKES)
        channel = ChannelName.PULSE1

        def open_the_folder(screen: Screen) -> None:
            gather(screen, folder)
            listing.toggle_folder(folder)
            screen.expect(partial(listing.is_open, folder), bool, description="the folder open")
            assert listing.channel_ticked(first, channel) and listing.channel_ticked(second, channel)

        def a_box_inside_changes_that_row_alone(screen: Screen) -> None:
            listing.tick(first, channel)

            screen.expect(partial(listing.channel_ticked, first, channel), operator.not_, description="the box let go")
            assert listing.channel_ticked(second, channel)
            screen.expect(
                partial(listing.channel_theme, folder, channel),
                PARTIAL_CHANNEL_THEME_TAGS[channel].__eq__,
                description="the folder's box partial",
            )
            assert not listing.channel_ticked(folder, channel)

        def the_folders_box_settles_them_all(screen: Screen) -> None:
            listing.tick(folder, channel)

            screen.expect(partial(listing.channel_ticked, folder, channel), bool, description="the folder's box held")
            assert listing.channel_ticked(first, channel) and listing.channel_ticked(second, channel)

        def the_next_click_lets_them_go(screen: Screen) -> None:
            listing.tick(folder, channel)

            screen.expect(partial(listing.channel_ticked, folder, channel), operator.not_, description="let go")
            assert not listing.channel_ticked(first, channel) and not listing.channel_ticked(second, channel)

        screen.scenario(
            open_the_folder,
            a_box_inside_changes_that_row_alone,
            the_folders_box_settles_them_all,
            the_next_click_lets_them_go,
        ).run()


class TestTheCardFollowsABoxClicked:
    """Ticking a box inside an open folder brings the card to that row, and the folder's own box brings it
    to the folder.
    """

    def test_the_card_names_the_row_whose_box_was_clicked(self, screen: Screen) -> None:
        """Source settings names the take whose box was clicked, then the folder once its box is clicked."""
        main = screen.main
        listing = main.converter.list
        folder = home_path(PAIR)
        first = folder / PAIR_TAKES[0]
        gather(screen, folder)
        listing.toggle_folder(folder)
        screen.expect(partial(listing.is_open, folder), bool, description="the folder open")

        listing.tick(first, ChannelName.PULSE1)

        screen.expect(main.source.subject, first.stem.__eq__, description="the card on the row clicked")
        listing.tick(folder, ChannelName.PULSE1)
        expected = screen.words(FOLDER_ROW).format(name=PAIR, count=len(PAIR_TAKES))
        screen.expect(main.source.subject, expected.__eq__, description="the card on the folder")
