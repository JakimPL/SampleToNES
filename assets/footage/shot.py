from typing import Dict, Final, Tuple

from pydantic import BaseModel, ConfigDict

from assets.footage.composition import Ground, Layout
from automation.dearpygui.items.types import Item
from automation.screen import Screen
from sampletones_application.config.session.state.window import ViewportState
from sampletones_application.tags.reconstructions import (
    TAG_RECONSTRUCTIONS_INSTRUMENTS_PANEL,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_AUDIO,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_PLOT,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_STEMS,
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_RADIO_AUDIO_SOURCE,
)
from sampletones_application.utils.palette.palette import Palette

SCREEN: Final[str] = "1700x1600"
GROUND_TOKEN: Final[str] = "ground"


class Shot(BaseModel):
    """How the Reconstructions tab is framed: the window it is drawn in, the cards folded in it, the margin cut
    around each pane and the frame the panes are laid on.
    """

    model_config = ConfigDict(frozen=True)

    viewport: ViewportState
    collapsed_cards: Dict[str, bool]
    margin: int
    layout: Layout


RECONSTRUCTIONS_SHOT: Final[Shot] = Shot(
    viewport=ViewportState(width=1340, height=1440, x=0, y=0),
    collapsed_cards={TAG_RECONSTRUCTIONS_INSTRUMENTS_PANEL: True},
    margin=0,
    layout=Layout(width=1080, height=1920, top=250, bottom=1500, gap=24),
)


def panes(screen: Screen) -> Tuple[Tuple[Item, ...], ...]:
    """What the reel shows of the Reconstructions tab, top to bottom: the Source card's bar with the switch
    under it, the Waveform card and the Stems card.
    """
    return (
        (
            screen.main.card(TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_AUDIO).strip,
            TAG_RECONSTRUCTIONS_RECONSTRUCTION_RADIO_AUDIO_SOURCE,
        ),
        (TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_PLOT,),
        (TAG_RECONSTRUCTIONS_RECONSTRUCTION_PANEL_STEMS,),
    )


def ground(palette: Palette) -> Ground:
    """The color the reel shows around its panes: the ground the application's window wears in ``palette``."""
    red, green, blue, _ = palette.colors[GROUND_TOKEN]
    return red, green, blue
