from typing import List, Tuple

from tests.screens.interface.display.steps import another_size, kept, open_display_settings, size_named, window_size
from tests.suite.screens.screen import Screen
from tests.suite.screens.written import written_state


class TestClosingWithASizeKeptButNotConfirmed:
    """Closing the window while Display settings holds a size kept on the countdown but left unconfirmed
    writes the size the dialog opened with.

    The session keeps that size, as it does for every setting the dialog has yet to commit. The
    scenario keeps another size, closes the window, and expects the opening size in the written
    session.
    """

    def test_leaving_writes_the_confirmed_size(self, screen: Screen) -> None:
        settings = screen.display_settings
        opened: List[Tuple[int, int]] = []

        def keep_a_size_without_confirming_it(screen: Screen) -> None:
            opened.append(window_size(screen))
            open_display_settings(screen)
            label = another_size(screen)

            settings.choose_resolution(label)
            kept(screen)

            screen.expect(
                lambda: window_size(screen),
                (size_named(label).width, size_named(label).height).__eq__,
                description="the window at the size picked",
            )

        def close_the_window(screen: Screen) -> None:
            screen.close_window()

            assert screen.wait_for_exit()
            viewport = written_state().viewport
            assert (viewport.width, viewport.height) == opened[0]

        screen.scenario(keep_a_size_without_confirming_it, close_the_window).run()
