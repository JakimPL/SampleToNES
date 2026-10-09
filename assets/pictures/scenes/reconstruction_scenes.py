from typing import Final

from assets.pictures.demo import piece_document
from assets.pictures.paths import guide_picture
from assets.pictures.writer import Pictures
from automation.screen import Screen
from automation.steps.reconstructions import expect_open, load_from_the_browser
from automation.views.instruments import tab
from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.tags.reconstructions import (
    TAG_RECONSTRUCTIONS_BROWSER_PANEL,
    TAG_RECONSTRUCTIONS_INSTRUMENTS_PANEL,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_AUDIO,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_PLOT,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_STEMS,
)
from sampletones_core.constants.enums import ChannelName

PAGE: Final[str] = "reconstruction"
BY_SAMPLE: Final[str] = "global.browser.label.by_sample"


def open_the_piece(screen: Screen) -> None:
    """Opens the piece's reconstruction from the browser and waits for it to stand open."""
    document = piece_document()
    load_from_the_browser(screen, document)
    expect_open(screen, document)


class ReconstructionScenes:
    """The Reconstruction tab with the piece open: the browser, each card, and the menu the piece is exported
    from.
    """

    def picture_browser(self, screen: Screen, pictures: Pictures) -> None:
        open_the_piece(screen)
        browser = screen.reconstructions.browser
        last_heading = screen.expect_item(
            lambda: browser.heading(screen.words(BY_SAMPLE)),
            description="the heading listing reconstructions by sample",
        )
        card = screen.main.card(TAG_RECONSTRUCTIONS_BROWSER_PANEL)
        pictures.rest()

        pictures.around(guide_picture(PAGE, "browser"), card.strip, last_heading)

    def picture_source(self, screen: Screen, pictures: Pictures) -> None:
        open_the_piece(screen)
        pictures.rest()

        pictures.around(
            guide_picture(PAGE, "source"),
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_AUDIO,
        )

    def picture_waveform(self, screen: Screen, pictures: Pictures) -> None:
        open_the_piece(screen)
        pictures.rest()

        pictures.around(
            guide_picture(PAGE, "waveform"),
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_PLOT,
        )

    def picture_stems(self, screen: Screen, pictures: Pictures) -> None:
        open_the_piece(screen)
        screen.hand.scroll_into_view(TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_STEMS)
        pictures.rest()

        pictures.around(
            guide_picture(PAGE, "stems"),
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_STEMS,
        )

    def picture_instruments(self, screen: Screen, pictures: Pictures) -> None:
        open_the_piece(screen)
        instruments = screen.reconstructions.instruments
        instruments.bring_forward(ChannelName.PULSE1)
        screen.expect(
            instruments.front,
            tab(ChannelName.PULSE1).__eq__,
            description="Pulse 1 in front",
        )
        pictures.rest()

        pictures.around(
            guide_picture(PAGE, "instruments"),
            TAG_RECONSTRUCTIONS_INSTRUMENTS_PANEL,
        )

    def picture_export_menu(self, screen: Screen, pictures: Pictures) -> None:
        open_the_piece(screen)
        pictures.rest()

        pictures.popup(
            guide_picture(PAGE, "export-menu"),
            lambda: screen.menu.open_submenu(
                MenuElements.GROUP_RECONSTRUCTION,
                MenuElements.GROUP_RECONSTRUCTION_EXPORT_INSTRUMENTS,
            ),
        )
