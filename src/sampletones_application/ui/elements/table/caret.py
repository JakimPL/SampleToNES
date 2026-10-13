from dataclasses import dataclass
from typing import Any, Final, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.layout.general.caret import CaretLayout
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.utils.gui.dpg import dpg_get_item_parent
from sampletones_shared.meta import NonInstantiableMeta
from sampletones_shared.types.application import ColorRGBA, Sender

Box = Tuple[float, float, float, float]

STILL: Final[float] = 0.0
UNFILLED: Final[ColorRGBA] = (0, 0, 0, 0)
FRAME_THICKNESS: Final[float] = 1.0
MARK_CLEARANCE: Final[float] = 1.0
_ANCESTOR_WALK_LIMIT = 32


def _as_item_id(item: Sender) -> Sender:
    """Resolves an alias string to its numeric item id, passing ids through unchanged.

    ``get_active_window`` and ``get_item_parent`` report items by alias while stored tags
    are also aliases, so both sides are normalized to ids before comparison.
    """
    if isinstance(item, str):
        return int(dpg.get_alias_id(item))

    return item


@dataclass(frozen=True)
class CaretBoxes:
    """Where the caret draws this frame: the mark under the active character and the frame around its cell."""

    mark: Box
    frame: Box


class CaretOverlay(metaclass=NonInstantiableMeta):
    """A mark under the character the tracker edits and a frame around the cell it stands in.

    Tracker cells are atomic ``selectable`` widgets that DearPyGui tints only as a whole, so the
    mark is drawn on a front viewport drawlist at the active character's position and redrawn
    every frame (from the application loop) so it follows the table as it scrolls. The mark is an
    underline, so the glyph it stands under stays whole; the frame is an outline, so the cell's own
    wash can stay faint without the cursor getting lost in a full grid. Because at most one cell
    across both tracker tables holds the cursor at a time, one shared pair of rectangles is
    enough; the ``owner`` token keeps the order and tracker panels' arm/clear calls from clobbering
    each other during focus hand-off.

    A grid that re-centers the row it moved to asks for a scroll the table answers a frame later
    than the rectangles it reports, so the panel hands the overlay the distance that scroll will
    carry the row (``scroll_shift``), which the next redraw takes off the boxes and then forgets.
    """

    _layout: Optional[CaretLayout] = None
    _mark: Optional[Sender] = None
    _frame: Optional[Sender] = None

    _owner: Optional[Any] = None
    _widget: Optional[Sender] = None
    _caret_index: int = 0
    _font: Optional[Font] = None
    _clip_widget: Optional[Sender] = None
    _scroll_shift: float = STILL
    _root_window: Optional[str] = None

    @classmethod
    def initialize(cls, layout: CaretLayout, *, root_window_tag: str) -> None:
        """Creates the (hidden) overlay rectangles. Call once after the viewport exists.

        ``root_window_tag`` is the primary window that hosts the tracker tables. The caret
        shows only while the active window sits within that window's tree, so a dialog or
        other top-level window that takes focus keeps the front-drawn caret from painting
        over it.
        """
        cls._layout = layout
        cls._root_window = root_window_tag
        drawlist = dpg.add_viewport_drawlist(front=True)
        cls._frame = dpg.draw_rectangle(
            (0.0, 0.0),
            (0.0, 0.0),
            parent=drawlist,
            fill=UNFILLED,
            color=layout.frame.rgba,
            thickness=FRAME_THICKNESS,
            show=False,
        )
        cls._mark = dpg.draw_rectangle(
            (0.0, 0.0),
            (0.0, 0.0),
            parent=drawlist,
            fill=layout.color.rgba,
            color=UNFILLED,
            show=False,
        )

    @classmethod
    def set_target(
        cls,
        *,
        owner: Any,
        widget: Optional[Sender],
        caret_index: int,
        font: Font,
        clip_widget: Sender,
        scroll_shift: float,
    ) -> None:
        """Arms the caret on ``widget`` at character ``caret_index``.

        ``clip_widget`` is the scrolling table the cell lives in; the boxes are clamped to its
        on-screen rectangle so they stay within the table. ``scroll_shift`` is how far a scroll
        already asked for will carry the cell before the next frame is drawn, ``STILL`` where
        none is pending.
        """
        if widget is None:
            cls.clear(owner)
            return

        cls._owner = owner
        cls._widget = widget
        cls._caret_index = caret_index
        cls._font = font
        cls._clip_widget = clip_widget
        cls._scroll_shift = scroll_shift

    @classmethod
    def clear(cls, owner: Any) -> None:
        """Disarms the caret, but only if ``owner`` currently holds it."""
        if cls._owner is not None and cls._owner != owner:
            return

        cls._owner = None
        cls._widget = None
        cls._hide()

    @classmethod
    def redraw(cls) -> None:
        """Repositions the boxes for the current frame. Cheap no-op when disarmed.

        Hides the boxes while the active window sits outside the tracker's window tree (a
        dialog or another window holds focus), keeping the armed state so the caret returns
        to the same cell once focus comes back.
        """
        if cls._mark is None or cls._frame is None or cls._layout is None:
            return

        if not cls._active_within_root():
            cls._hide()
            return

        boxes = cls._compute_boxes()
        cls._scroll_shift = STILL
        if boxes is None:
            cls._hide()
            return

        dpg.configure_item(
            cls._frame,
            pmin=(boxes.frame[0], boxes.frame[1]),
            pmax=(boxes.frame[2], boxes.frame[3]),
            color=cls._layout.frame.rgba,
            show=True,
        )
        dpg.configure_item(
            cls._mark,
            pmin=(boxes.mark[0], boxes.mark[1]),
            pmax=(boxes.mark[2], boxes.mark[3]),
            fill=cls._layout.color.rgba,
            show=True,
        )

    @classmethod
    def _compute_boxes(cls) -> Optional[CaretBoxes]:
        """The mark and the frame for this frame, or None while the cell is off screen or empty.

        The mark spans one character of the cell's label, measured from the label's own width
        in the cell's font, and stands under the text band, which the cell centers vertically.
        The frame takes the cell the widget belongs to, the group that holds its slots, and the
        widget's own rectangle where the widget stands alone in its cell.
        """
        widget = cls._widget
        if widget is None or cls._font is None or cls._layout is None:
            return None

        if not dpg.does_item_exist(widget):
            return None

        if not dpg.is_item_visible(widget):
            return None

        cell = cls._rect(widget)
        if cell is None:
            return None

        text = dpg.get_item_configuration(widget).get("label") or ""
        if not text:
            return None

        size = dpg.get_text_size(text, font=FontRegistry.get_tag(cls._font))
        if not size or size[0] <= 0:
            return None

        x0, y0, _, y1 = cell
        char_width = size[0] / len(text)
        mark_x0 = x0 + cls._caret_index * char_width
        mark_x1 = mark_x0 + char_width
        text_bottom = (y0 + y1 + size[1]) / 2
        mark_y1 = text_bottom + MARK_CLEARANCE
        mark_y0 = mark_y1 - cls._layout.height

        mark = cls._clip(cls._shifted((mark_x0, mark_y0, mark_x1, mark_y1)))
        frame = cls._clip(cls._shifted(cls._cell_box(widget, cell)))
        if mark is None or frame is None:
            return None

        return CaretBoxes(mark=mark, frame=frame)

    @classmethod
    def _cell_box(cls, widget: Sender, own: Box) -> Box:
        """The cell the frame outlines: the parent group's rectangle, or the widget's own where the parent reports
        none.
        """
        parent = dpg_get_item_parent(widget)
        if parent is None:
            return own

        group = cls._rect(parent)
        return group if group is not None else own

    @classmethod
    def _shifted(cls, box: Box) -> Box:
        """``box`` carried by the scroll the table is about to answer."""
        shift = cls._scroll_shift
        return (box[0], box[1] - shift, box[2], box[3] - shift)

    @classmethod
    def _clip(cls, box: Box) -> Optional[Box]:
        if cls._clip_widget is None:
            return box

        bounds = cls._rect(cls._clip_widget)
        if bounds is None:
            return box

        cx0, cy0, cx1, cy1 = bounds
        x0, y0 = max(box[0], cx0), max(box[1], cy0)
        x1, y1 = min(box[2], cx1), min(box[3], cy1)
        if x0 >= x1 or y0 >= y1:
            return None

        return (x0, y0, x1, y1)

    @staticmethod
    def _rect(widget: Sender) -> Optional[Box]:
        """On-screen rectangle of ``widget`` as ``(x0, y0, x1, y1)``.

        Returns None for a missing widget or one that exposes no rect (a ``table``
        reports no ``rect_min``), so callers can skip it.
        """
        if not dpg.does_item_exist(widget):
            return None

        state = dpg.get_item_state(widget)
        rect_min = state.get("rect_min")
        rect_max = state.get("rect_max")
        if rect_min is None or rect_max is None:
            return None

        return (rect_min[0], rect_min[1], rect_max[0], rect_max[1])

    @classmethod
    def _active_within_root(cls) -> bool:
        """Whether the active window sits within the tracker's root window tree.

        ``get_active_window`` reports the top child window under the primary that owns the
        focused widget, so the tracker's active window carries the primary among its
        ancestors. A dialog or other top-level window opens outside that tree, so its
        ancestor chain excludes the primary and the caret is suppressed. An absent active
        window counts as outside; the caret is armed only after a tracker cell is clicked,
        which puts focus back inside the tree.

        The frame after a dialog closes, ``get_active_window`` can still name the destroyed
        window, so each node is confirmed to exist before it is walked.
        """
        if cls._root_window is None:
            return True

        active_window = dpg.get_active_window()
        if not active_window:
            return False

        root_id = _as_item_id(cls._root_window)
        node: Sender = active_window
        for _ in range(_ANCESTOR_WALK_LIMIT):
            if not dpg.does_item_exist(node):
                return False

            if _as_item_id(node) == root_id:
                return True

            parent = dpg_get_item_parent(node)
            if not parent:
                return False

            node = parent

        return False

    @classmethod
    def _hide(cls) -> None:
        for rectangle in (cls._mark, cls._frame):
            if rectangle is not None and dpg.does_item_exist(rectangle):
                dpg.configure_item(rectangle, show=False)
