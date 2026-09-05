from typing import Callable, Final

import dearpygui.dearpygui as dpg

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_SPACER_ABOVE,
    SUF_SPACER_BELOW,
)
from sampletones_application.ui.elements.layout.geometry import RowGeometry, Window
from sampletones_application.ui.elements.layout.well import well
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_delete_children
from sampletones_shared.types.callback import VoidCallback

SliceBuilder = Callable[[int, int], None]

NO_ROWS: Final[Window] = (0, 0)
AUTO_HEIGHT: Final[int] = 0


class WindowedRegion:
    """A recessed region that builds the rows it shows and reserves the room for the rest.

    A region sizes itself to what it holds up to a ceiling, and scrolls from there on, so the
    card around it keeps its shape however long the list grows. Within it, only the rows the
    reader can reach are built; the ones above and below stand as reserved room, which keeps the
    scrollbar proportional to the whole list and makes drawing a list of thousands cost what
    drawing a list of ten costs.

    The region owns every quantity the window is chosen by: the room it reserved, because it
    placed it, and the height it holds, because it set it. So a caller draws and then settles,
    and there is one order for the two.

    The height a run of rows asks for is worked out from the reading of a row rather than read off
    the widgets, since a region already held to its ceiling clips what it holds and would measure
    its own ceiling back. A region standing at its natural height is what a reading is taken from.
    """

    def __init__(
        self,
        *,
        tag: str,
        geometry: RowGeometry,
        ceiling: int,
        padding: int,
        margin: int,
    ) -> None:
        self._tag = tag
        self._geometry = geometry
        self._ceiling = ceiling
        self._padding = padding
        self._margin = margin
        self._above_tag = compose_tag(tag, SUF_SPACER_ABOVE)
        self._below_tag = compose_tag(tag, SUF_SPACER_BELOW)
        self._body_tag = ""
        self._height = float(ceiling)
        self._total = 0
        self._drawn: Window = NO_ROWS

    @property
    def tag(self) -> str:
        """The region itself, which is what an owner shows, hides and scrolls."""
        return self._tag

    @property
    def body(self) -> str:
        """The group the rows are built into, which a draw empties and fills."""
        return self._body_tag

    @property
    def window(self) -> Window:
        """The slice the region was last drawn from: where it opens, and how many rows it holds."""
        return self._drawn

    @property
    def windowing(self) -> bool:
        """The region holds back rows it has no room for, so a scroll asks it for different ones."""
        return bool(self._total) and self._drawn[1] < self._total

    @property
    def offset(self) -> float:
        """How far the region has been scrolled, read from the region itself."""
        return self._scroll(dpg.get_y_scroll)

    @property
    def extent(self) -> float:
        """How far the region can be scrolled, worked out from the room its rows ask for.

        The travel follows from what the region reserved rather than from what it reports, since a
        region asked to scroll reports its travel a frame late and would send the window to the
        top of the list for that frame.
        """
        return max(0.0, self._content() - self._height)

    def create(self, parent: str, *, show: bool = True) -> None:
        """Sink the region into ``parent``, sized to its rows until they reach its ceiling."""
        self._body_tag = well(
            parent,
            self._tag,
            padding=self._padding,
            margin=self._margin,
            show=show,
        )

    def draw(self, total: int, build: SliceBuilder) -> None:
        """Build the rows the region reaches, reserving the room the ones outside it would take.

        ``build`` is handed where the window opens and how many rows it holds, and adds them to
        :attr:`body` between the two reserves. The scroll position is put back afterwards, so the
        rows a reader was looking at are the rows they keep looking at.

        Before a row has been measured the region builds a first slice at its natural height and
        reserves nothing, which is what gives :meth:`settle` a run of rows to read.
        """
        offset = self.offset
        start, count = self._slice(offset, total)
        dpg_delete_children(self._body_tag)
        measuring = not self._geometry.measured
        self._reserve(self._above_tag, 0 if measuring else start)
        build(start, count)
        self._reserve(self._below_tag, 0 if measuring else total - start - count)
        self._total = total
        self._drawn = (start, count)
        dpg.set_y_scroll(self._tag, offset)

    def draw_whole(self, build: VoidCallback) -> None:
        """Build the region's contents entire, for content that is more than a run of rows.

        A region holding captions, strips or regions of its own has no one row to reserve room by,
        so it stands as tall as what it holds.
        """
        dpg_delete_children(self._body_tag)
        build()
        self._total = 0
        self._drawn = NO_ROWS

    def settle(self) -> bool:
        """Size the region to what it holds and read what a row takes, a frame after a draw.

        Answers whether the rows standing are still the ones the region reaches, which is what
        asks an owner to draw it again.
        """
        if not self._total:
            self._stand_at_natural_height()
            return False

        if not self._geometry.measured:
            self._stand_at_natural_height()
            return self._geometry.take(block=self._body_height(), rows=self._drawn[1])

        self._hold_rows()
        return self._slice(self.offset, self._total) != self._drawn

    def _slice(self, offset: float, total: int) -> Window:
        """The rows the region's scroll position reaches, in the list it is a window onto."""
        return self._geometry.slice_of(
            offset=offset,
            extent=self.extent,
            height=self._height,
            total=total,
        )

    def _reserve(self, tag: str, rows: int) -> None:
        """The room a run of undrawn rows would take, standing in place of them."""
        dpg.add_spacer(tag=tag, parent=self._body_tag, height=self._geometry.reserve(rows))

    def _hold_rows(self) -> None:
        """Size the region to the room its rows ask for, holding it at its ceiling from there on."""
        self._size_to(self._content())

    def _content(self) -> float:
        """The room the region's whole list asks for, the margins above and below it included."""
        return float(self._geometry.reserve(self._total) + 2 * self._margin)

    def _stand_at_natural_height(self) -> None:
        """Let the region take the height of what it holds, which is what a reading is read from."""
        self._height = self._body_height() + 2 * self._margin
        dpg_configure_item(self._tag, height=AUTO_HEIGHT, auto_resize_y=True, no_scrollbar=True)

    def _size_to(self, content: float) -> None:
        within = content <= self._ceiling
        self._height = content if within else float(self._ceiling)
        dpg_configure_item(
            self._tag,
            height=AUTO_HEIGHT if within else self._ceiling,
            auto_resize_y=within,
            no_scrollbar=within,
        )

    def _body_height(self) -> float:
        """How tall the rows drawn into the region stand, as the frame that placed them left them."""
        if not dpg.does_item_exist(self._body_tag):
            return 0.0

        return float(dpg.get_item_rect_size(self._body_tag)[1])

    def _scroll(self, read: Callable[[str], float]) -> float:
        if not dpg.does_item_exist(self._tag):
            return 0.0

        return float(read(self._tag))
