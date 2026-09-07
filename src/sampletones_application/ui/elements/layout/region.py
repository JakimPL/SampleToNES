from typing import Callable, Final, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_LEAD,
    SUF_SPACER_ABOVE,
    SUF_SPACER_BELOW,
)
from sampletones_application.ui.elements.layout.geometry import RowGeometry, Window
from sampletones_application.ui.elements.layout.well import well
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_delete_children
from sampletones_shared.types.callback import VoidCallback

SliceBuilder = Callable[[int, int], None]
LeadBuilder = Callable[[str], None]

NO_ROWS: Final[Window] = (0, 0)
NO_LEAD: Final[float] = 0.0
AUTO_HEIGHT: Final[int] = 0
NO_SCROLL: Final[float] = 0.0
SCROLL_TOLERANCE: Final[float] = 1.0


class WindowedRegion:
    """A recessed region that builds the rows it shows and reserves the room for the rest.

    A region sizes itself to what it holds up to a ceiling, and scrolls from there on, so the
    card around it keeps its shape however long the list grows. Within it, only the rows the
    reader can reach are built; the ones above and below stand as reserved room, which keeps the
    scrollbar proportional to the whole list and makes drawing a list of thousands cost what
    drawing a list of ten costs.

    A region may carry a **lead** — a heading standing above its rows, built and taken down with
    them and scrolling with them. Its room counts toward the height the content asks for, so the
    travel a window is mapped over covers the whole of what the region holds.

    The region owns every quantity the window is chosen by: the room it reserved, because it
    placed it, and the height it holds, because it set it. So a caller draws and then settles,
    and there is one order for the two.

    The height a run of rows asks for is worked out from the reading of a row rather than read off
    the widgets, since a region already held to its ceiling clips what it holds and would measure
    its own ceiling back. A reading is therefore taken only while the region stands at the height
    of what it holds, which :attr:`natural` reports. A reading arrives after the height it decides
    has been set, so :attr:`settling` asks for the pass that holds the region to it.

    A region redrawn because the reader scrolled leaves the scroll where they put it. The rows it
    holds change while the region itself stands, so a position written back would land against the
    wheel that asked for the new rows and take the reader somewhere they never scrolled. A region
    built in place of one a rebuild took down is a new widget standing at its top, so where the
    reader had scrolled the one before it is named by :meth:`opens_at`, and handed back once the
    frame that placed its rows has been drawn.
    """

    def __init__(
        self,
        *,
        tag: str,
        geometry: RowGeometry,
        ceiling: int,
        padding: int,
        margin: int,
        indent: Optional[int] = None,
    ) -> None:
        self._tag = tag
        self._geometry = geometry
        self._ceiling = ceiling
        self._padding = padding
        self._margin = margin
        self._indent = indent
        self._above_tag = compose_tag(tag, SUF_SPACER_ABOVE)
        self._below_tag = compose_tag(tag, SUF_SPACER_BELOW)
        self._lead_tag = compose_tag(tag, SUF_LEAD)
        self._body_tag = ""
        self._height = float(ceiling)
        self._lead = NO_LEAD
        self._total = 0
        self._windowed = False
        self._natural = True
        self._reading_to_hold = False
        self._drawn: Window = NO_ROWS
        self._resting = NO_SCROLL
        self._restoring = False

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
        return self._windowed and self._drawn[1] < self._total

    @property
    def standing(self) -> bool:
        """The region's body is on screen, which is what a draw fills and a settle reads."""
        return bool(dpg.does_item_exist(self._body_tag))

    @property
    def settling(self) -> bool:
        """The region stands as something other than it will, so whoever drew it settles it again.

        A region holding rows back answers a scroll with a different slice, and one that has
        just read what a row takes holds itself to that reading in the pass that follows. Either
        way what stands now is not what the region comes to rest as. A region whose body has been
        taken down comes to rest where it is, so a window closing ends the pass it was keeping.
        """
        return self.standing and (self.windowing or self._reading_to_hold)

    @property
    def natural(self) -> bool:
        """The region stands at the height of what it holds, so what it holds measures true."""
        return self._natural

    @property
    def offset(self) -> float:
        """How far the region has been scrolled, read from the region itself."""
        return self._scroll(dpg.get_y_scroll)

    def opens_at(self, offset: float) -> None:
        """Open the region where the reader had scrolled the one it stands in place of.

        A region goes down with the list around it and comes back a new widget at its top, so the
        rows the reader was looking at are named by whoever held on to the position.
        """
        self._resting = offset
        self._restoring = True

    def create(self, parent: str, *, show: bool = True) -> None:
        """Sink the region into ``parent``, sized to its rows until they reach its ceiling."""
        self._body_tag = well(
            parent,
            self._tag,
            padding=self._padding,
            margin=self._margin,
            indent=self._indent,
            show=show,
        )

    def draw(self, total: int, build: SliceBuilder, *, lead: Optional[LeadBuilder]) -> None:
        """Build the rows the region reaches, reserving the room the ones outside it would take.

        ``build`` is handed where the window opens and how many rows it holds, and adds them to
        :attr:`body` between the two reserves. ``lead`` builds the heading standing above them,
        into the group it is handed. The rows are chosen for where the reader stands, which is a
        position they scrolled to themselves unless the region is opening in place of another.

        Before a row has been measured the region builds a first slice at its natural height and
        reserves nothing, which is what gives :meth:`settle` a run of rows to read.
        """
        if not self.standing:
            return

        start, count = self._slice(self._reading, total)
        dpg_delete_children(self._body_tag)
        measuring = not self._geometry.measured
        self._build_lead(lead)
        self._reserve(self._above_tag, 0 if measuring else start)
        build(start, count)
        self._reserve(self._below_tag, 0 if measuring else total - start - count)
        self._total = total
        self._windowed = True
        self._drawn = (start, count)

    def draw_whole(self, build: VoidCallback, *, lead: Optional[LeadBuilder], rows: int) -> None:
        """Build the region's contents entire, for content that is more than a run of rows.

        A region holding captions, strips or regions of its own has no one row to reserve room by,
        so it stands as tall as what it holds and scrolls once that reaches its ceiling.

        ``rows`` is how many rows of one height the content is a plain run of, which is what a
        reading of a row is taken from; content standing anything else among its rows is a run of
        none.
        """
        if not self.standing:
            return

        dpg_delete_children(self._body_tag)
        self._build_lead(lead)
        build()
        self._total = rows
        self._windowed = False
        self._drawn = NO_ROWS

    def settle(self) -> bool:
        """Size the region to what it holds and read what a row takes, a frame after a draw.

        Answers whether the rows standing are still the ones the region reaches, which is what
        asks an owner to draw it again. A region whose body has been taken down asks for nothing.
        """
        if not self.standing:
            return False

        self._take_lead()
        if not self._windowed:
            self._take_reading()
            self._hold_content()
            return self._restore()

        if not self._geometry.measured:
            self._stand_at_natural_height()
            self._reading_to_hold = self._take_reading()
            return self._reading_to_hold

        self._hold_rows()
        if self._restore():
            return False

        return self._slice(self.offset, self._total) != self._drawn

    @property
    def _reading(self) -> float:
        """The position the rows are chosen for: where the reader stands, or where they go back to."""
        return self._resting if self._restoring else self.offset

    def _restore(self) -> bool:
        """Put the reader back where they stood, once the frame that placed the rows has drawn.

        Answers whether a scroll was written, since the frame that carries it out is the one whose
        position the window is chosen from.
        """
        if not self._restoring:
            return False

        self._restoring = False
        if abs(self.offset - self._resting) <= SCROLL_TOLERANCE:
            return False

        dpg.set_y_scroll(self._tag, self._resting)
        return True

    def _slice(self, offset: float, total: int) -> Window:
        """The rows the region's scroll position reaches, in the list it is a window onto.

        The position is counted in the rooms the region reserves by, which is what the spacer
        above the rows is built from, so the block stands over what the reader is looking at.
        """
        return self._geometry.slice_of(offset=offset, height=self._height, total=total)

    def _build_lead(self, lead: Optional[LeadBuilder]) -> None:
        """Open the group the heading stands in, and let its owner fill it."""
        if lead is None:
            return

        dpg.add_group(tag=self._lead_tag, parent=self._body_tag)
        lead(self._lead_tag)

    def _reserve(self, tag: str, rows: int) -> None:
        """The room a run of undrawn rows would take, standing in place of them."""
        dpg.add_spacer(tag=tag, parent=self._body_tag, height=self._geometry.reserve(rows))

    def _take_lead(self) -> None:
        """Read the room the heading takes, which the room the whole content asks for counts in."""
        if not self._natural or not dpg.does_item_exist(self._lead_tag):
            return

        self._lead = float(dpg.get_item_rect_size(self._lead_tag)[1])

    def _take_reading(self) -> bool:
        """Read what one row takes from the rows standing, and report a reading worth redrawing.

        The rows are counted off a block measured whole, so the reading holds whatever a table
        lays around them. It is taken while the region stands at its natural height, which is
        where the block measures the room its rows asked for.
        """
        if not self._natural:
            return False

        return self._geometry.take(block=self._body_height() - self._lead, rows=self._standing)

    @property
    def _standing(self) -> int:
        """How many rows of one height stand in the region, which a reading counts by.

        A windowed region reserves nothing while it measures, so the block it stands as is the
        slice it drew; a whole-drawn one stands as every row it was given.
        """
        return self._drawn[1] if self._windowed else self._total

    def _hold_rows(self) -> None:
        """Size the region to the room its rows ask for, holding it at its ceiling from there on."""
        self._size_to(self._room_for(self._total))

    def _hold_content(self) -> None:
        """Size a whole-drawn region to what it holds, holding it at its ceiling from there on.

        What it holds is measured rather than worked out, since content that is more than a run of
        rows has no one row to count by. A region already at its ceiling measures at least its own
        height, which answers the ceiling the way an exact reading would.
        """
        self._size_to(self._body_height() + 2 * self._margin)

    def _room_for(self, total: int) -> float:
        """The room a list of this length asks for: the heading, the rows, and the margins."""
        return float(self._lead + self._geometry.reserve(total) + 2 * self._margin)

    def _stand_at_natural_height(self) -> None:
        """Let the region take the height of what it holds, which is what a reading is read from."""
        self._height = self._body_height() + 2 * self._margin
        self._natural = True
        dpg_configure_item(self._tag, height=AUTO_HEIGHT, auto_resize_y=True, no_scrollbar=True)

    def _size_to(self, content: float) -> None:
        within = content <= self._ceiling
        self._height = content if within else float(self._ceiling)
        self._natural = within
        self._reading_to_hold = False
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
