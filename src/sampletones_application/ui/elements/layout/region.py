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

SliceBuilder = Callable[[int, int], None]

NO_ROWS: Final[Window] = (0, 0)
AUTO_HEIGHT: Final[int] = 0


class WindowedRegion:
    """A recessed region that builds the rows it shows and reserves the room for the rest.

    A region sizes itself to what it holds up to a ceiling, and scrolls from there on, so the
    card around it keeps its shape however long the list grows. Within it, only the rows the
    reader can reach are built; the ones above and below stand as reserved room, which keeps the
    scrollbar proportional to the whole list and makes opening a folder of thousands cost what
    opening a folder of ten costs.

    The region owns every quantity the window is chosen by: the room it reserved, because it
    placed it, and the height it holds, because it set it. So a caller draws and then settles,
    and there is one order for the two.
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
        """
        offset = self.offset
        start, count = self._geometry.slice_of(offset=offset, height=self._height, total=total)
        dpg_delete_children(self._body_tag)
        self._reserve(self._above_tag, start)
        build(start, count)
        self._reserve(self._below_tag, total - start - count)
        self._total = total
        self._drawn = (start, count)
        dpg.set_y_scroll(self._tag, offset)

    def settle(self) -> bool:
        """Hold the region to its ceiling and read what a row takes, a frame after a draw.

        Answers whether the rows standing are still the ones the region reaches, which is what
        asks an owner to draw it again.
        """
        self._hold()
        moved = self._measure()
        reached = self._geometry.slice_of(offset=self.offset, height=self._height, total=self._total)
        return moved or reached != self._drawn

    @property
    def offset(self) -> float:
        """How far the region has been scrolled, read from the region itself."""
        if not dpg.does_item_exist(self._tag):
            return 0.0

        return float(dpg.get_y_scroll(self._tag))

    def _reserve(self, tag: str, rows: int) -> None:
        """The room a run of undrawn rows would take, standing in place of them."""
        dpg.add_spacer(tag=tag, parent=self._body_tag, height=self._geometry.reserve(rows))

    def _hold(self) -> None:
        """Size the region to its rows up to its ceiling, and scroll them from there on."""
        content = self._content_height()
        within = content <= self._ceiling
        self._height = content if within else float(self._ceiling)
        dpg_configure_item(
            self._tag,
            height=AUTO_HEIGHT if within else self._ceiling,
            auto_resize_y=within,
            no_scrollbar=within,
        )

    def _measure(self) -> bool:
        """Read what one row takes from the block of rows the region last drew."""
        start, count = self._drawn
        reserved = self._geometry.reserve(start) + self._geometry.reserve(self._total - start - count)
        return self._geometry.take(block=self._body_height() - reserved, rows=count)

    def _content_height(self) -> float:
        """The room the region's rows ask for, the margins it opens above and below included."""
        return self._body_height() + 2 * self._margin

    def _body_height(self) -> float:
        """How tall the rows drawn into the region stand, as the frame that placed them left them."""
        if not dpg.does_item_exist(self._body_tag):
            return 0.0

        return float(dpg.get_item_rect_size(self._body_tag)[1])
