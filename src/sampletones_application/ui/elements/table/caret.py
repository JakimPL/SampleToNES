from typing import Any, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.layout.general import CaretLayout
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_shared.meta import NonInstantiableMeta
from sampletones_shared.types.application import ColorRGBA, Sender

Box = Tuple[float, float, float, float]


_ANCESTOR_WALK_LIMIT = 32


def _as_item_id(item: Sender) -> Sender:
    """Resolves an alias string to its numeric item id, passing ids through unchanged.

    ``get_active_window`` and ``get_item_parent`` report items by alias while stored tags
    are also aliases, so both sides are normalised to ids before comparison.
    """
    if isinstance(item, str):
        return int(dpg.get_alias_id(item))

    return item


class CaretOverlay(metaclass=NonInstantiableMeta):
    """A single-character translucent box marking the tracker edit cursor.

    Tracker cells are atomic ``selectable`` widgets that DearPyGui tints only as a
    whole, so a single rectangle is drawn on a front viewport drawlist at the active
    character's position and redrawn every frame (from the application loop) so it
    follows the table as it scrolls. Because at
    most one cell across both tracker tables holds the cursor at a time, one
    shared rectangle is enough; the ``owner`` token keeps the order and grid
    panels' arm/clear calls from clobbering each other during focus hand-off.
    """

    _fill: ColorRGBA = (0, 0, 0, 0)
    _border: ColorRGBA = (0, 0, 0, 0)
    _offset: float = 0.0
    _width_padding: float = 0.0
    _rectangle: Optional[Sender] = None

    _owner: Optional[Any] = None
    _widget: Optional[Sender] = None
    _caret_index: int = 0
    _font: Optional[Font] = None
    _clip_widget: Optional[Sender] = None
    _root_window: Optional[str] = None

    @classmethod
    def initialize(cls, layout: CaretLayout, *, root_window_tag: str) -> None:
        """Creates the (hidden) overlay rectangle. Call once after the viewport exists.

        ``root_window_tag`` is the primary window that hosts the tracker tables. The caret
        shows only while the active window sits within that window's tree, so a dialog or
        other top-level window that takes focus keeps the front-drawn caret from painting
        over it.
        """
        cls._fill = layout.fill
        cls._border = layout.border
        cls._offset = layout.offset
        cls._width_padding = layout.width_padding
        cls._root_window = root_window_tag
        drawlist = dpg.add_viewport_drawlist(front=True)
        cls._rectangle = dpg.draw_rectangle(
            (0.0, 0.0),
            (0.0, 0.0),
            parent=drawlist,
            fill=cls._fill,
            color=cls._border,
            show=False,
        )

    @classmethod
    def set_target(
        cls,
        *,
        owner: object,
        widget: Optional[Sender],
        caret_index: int,
        font: Font,
        clip_widget: Sender,
    ) -> None:
        """Arms the caret on ``widget`` at character ``caret_index``.

        ``clip_widget`` is the scrolling table the cell lives in; the box is
        clamped to its on-screen rectangle so it stays within the table.
        """
        if widget is None:
            cls.clear(owner)
            return

        cls._owner = owner
        cls._widget = widget
        cls._caret_index = caret_index
        cls._font = font
        cls._clip_widget = clip_widget

    @classmethod
    def clear(cls, owner: object) -> None:
        """Disarms the caret, but only if ``owner`` currently holds it."""
        if cls._owner is not None and cls._owner != owner:
            return

        cls._owner = None
        cls._widget = None
        cls._hide()

    @classmethod
    def redraw(cls) -> None:
        """Repositions the box for the current frame. Cheap no-op when disarmed.

        Hides the box while the active window sits outside the tracker's window tree (a
        dialog or another window holds focus), keeping the armed state so the caret returns
        to the same cell once focus comes back.
        """
        if cls._rectangle is None:
            return

        if not cls._active_within_root():
            cls._hide()
            return

        box = cls._compute_box()
        if box is None:
            cls._hide()
            return

        pmin, pmax = (box[0], box[1]), (box[2], box[3])
        dpg.configure_item(
            cls._rectangle,
            pmin=pmin,
            pmax=pmax,
            fill=cls._fill,
            color=cls._border,
            show=True,
        )

    @classmethod
    def _compute_box(cls) -> Optional[Box]:
        widget = cls._widget
        if widget is None or cls._font is None:
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
        caret_x0 = x0 + cls._offset + cls._caret_index * char_width
        caret_x1 = caret_x0 + char_width + cls._width_padding

        return cls._clip((caret_x0, y0, caret_x1, y1))

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

            parent = dpg.get_item_parent(node)
            if not parent:
                return False

            node = parent

        return False

    @classmethod
    def _hide(cls) -> None:
        if cls._rectangle is not None and dpg.does_item_exist(cls._rectangle):
            dpg.configure_item(cls._rectangle, show=False)
