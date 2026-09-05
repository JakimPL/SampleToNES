from functools import partial
from typing import Final, Optional, Tuple

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.layout.glyphs.common import CommonGlyphs
from sampletones_application.ui.elements.layout.geometry import RowGeometry
from sampletones_application.ui.elements.layout.region import WindowedRegion
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.stems.bands import LevelBands
from sampletones_application.ui.elements.stems.expansion import OpenFolders
from sampletones_application.ui.elements.stems.folder import FolderRenderer
from sampletones_application.ui.elements.stems.gestures import (
    ChannelCallback,
    ChannelsCallback,
    KeyOffsetCallback,
    KeyPairCallback,
    StemsGestures,
)
from sampletones_application.ui.elements.stems.heading import StemsHeading
from sampletones_application.ui.elements.stems.messages import StemsMessages
from sampletones_application.ui.elements.stems.offer import StemsListOffer
from sampletones_application.ui.elements.stems.row import StemRowRenderer
from sampletones_application.ui.elements.stems.tags import StemsTags
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.view_model.shared.stems import (
    StemRowViewModel,
    StemsListViewModel,
)
from sampletones_shared.types.callback import StringCallback
from sampletones_shared.utils.callbacks import CallbackMixin

NO_ROWS: Final[int] = 0


class GUIStemsList(CallbackMixin):
    """The stems of one setup, as a table of rows banded by the levels they pick on.

    Both the converter's gathered recordings and a reconstruction's recorded assignment are the
    same list, so one composition draws them and each owner states what it offers a reader
    (:class:`StemsListOffer`). Rows are keyed by the identity their owner reports gestures under,
    and every column lines up across the bands because each table declares the same columns.

    The list holds the view it was last given and nothing beside it: the rows, the columns and
    what a gesture may reach are all read from that one value.
    """

    def __init__(
        self,
        *,
        prefix: str,
        layout: StemsListLayout,
        glyphs: CommonGlyphs,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        offer: StemsListOffer,
    ) -> None:
        self._tags = StemsTags(prefix=prefix)
        self._layout = layout
        self._offer = offer
        self._view = StemsListViewModel.empty()
        self._open_folders = OpenFolders()
        self._geometry = RowGeometry.unmeasured(overscan=layout.window_overscan)
        self._settling = False
        self._region = WindowedRegion(
            tag=self._tags.well,
            geometry=self._geometry,
            ceiling=layout.well_ceiling,
            padding=layout.well_padding,
            margin=layout.well_margin,
        )

        self._messages = StemsMessages(
            language_manager,
            offer=offer,
            open_folders=self._open_folders,
            activatable=lambda: self.activatable,
        )
        self._gestures = StemsGestures(self._tags, messages=self._messages, status_bar=status_bar)
        self._rows = StemRowRenderer(
            self._tags,
            layout=layout,
            offer=offer,
            glyphs=glyphs,
            open_folders=self._open_folders,
            language_manager=language_manager,
            messages=self._messages,
            gestures=self._gestures,
        )
        self._folders = FolderRenderer(
            self._tags,
            layout=layout,
            geometry=self._geometry,
            open_folders=self._open_folders,
            rows=self._rows,
        )
        self._heading = StemsHeading(
            prefix=prefix,
            layout=layout,
            language_manager=language_manager,
            bends=offer.bends,
        )
        self._bands = LevelBands(
            self._tags,
            layout=layout,
            offer=offer,
            language_manager=language_manager,
            rows=self._rows,
            folders=self._folders,
            heading=self._heading,
            open_folders=self._open_folders,
            gestures=self._gestures,
        )

        self.on_channels_changed: Optional[ChannelsCallback] = None
        self.on_channel_toggled: Optional[ChannelCallback] = None
        self.on_remove_requested: Optional[StringCallback] = None
        self.on_menu_requested: Optional[StringCallback] = None
        self.on_row_activated: Optional[StringCallback] = None
        self.on_dropped_on_row: Optional[KeyPairCallback] = None
        self.on_dropped_on_level: Optional[KeyOffsetCallback] = None
        self.on_row_opened: Optional[StringCallback] = None

        self._gestures.on_channels_settled = lambda key, channels: self.call(self.on_channels_changed, key, channels)
        self._gestures.on_channel_toggled = lambda key, channel: self.call(self.on_channel_toggled, key, channel)
        self._gestures.on_removal_asked = lambda key: self.call(self.on_remove_requested, key)
        self._gestures.on_menu_asked = lambda key: self.call(self.on_menu_requested, key)
        self._gestures.on_row_activated = lambda key: self.call(self.on_row_activated, key)
        self._gestures.on_dropped_on_row = lambda key, target: self.call(self.on_dropped_on_row, key, target)
        self._gestures.on_dropped_on_level = lambda key, position: self.call(self.on_dropped_on_level, key, position)
        self._gestures.on_row_opened = lambda key: self.call(self.on_row_opened, key)
        self._gestures.on_folder_toggled = self.toggle_folder

    @property
    def tags(self) -> StemsTags:
        """The grammar the list's widgets are named under."""
        return self._tags

    @property
    def tag(self) -> str:
        """The recessed region the list is drawn in, which is what an owner shows and hides."""
        return self._tags.well

    @property
    def activatable(self) -> bool:
        """The owner answers a click on a row, so the list hands one on rather than absorbing it."""
        return self.on_row_activated is not None

    def create(self, parent: str, *, show: bool = True) -> None:
        """Build the list's recessed region and the handlers its rows share."""
        self._gestures.create_handlers()
        self._region.create(parent, show=show)

    def update_view(self, view_model: StemsListViewModel) -> None:
        """Take up a new reading of the setup: rebuild the bands where it reshapes them, repaint
        the rows either way."""
        self._view = view_model
        self._open_folders.hold_to({row.key for row in view_model.rows})
        self._messages.reads(view_model)
        self._gestures.reads(view_model)
        if self._bands.reshaped(view_model):
            self._rebuild(view_model)
            self._settle_soon()

        self._repaint(view_model)

    def _rebuild(self, view_model: StemsListViewModel) -> None:
        """Draw the list afresh: the bands the view names, and a region under each open folder."""
        self._folders.forget()
        if self._windows(view_model):
            self._draw_window(view_model)
            return

        self._region.draw_whole(
            partial(self._bands.build, view_model),
            lead=partial(self._bands.build_heading, view_model),
            rows=self._plain_rows(view_model),
        )

    def _draw_window(self, view_model: StemsListViewModel) -> None:
        """Draw the rows the well reaches, reserving the room the rest of them would take."""
        self._region.draw(
            view_model.row_count,
            partial(self._bands.build_rows, view_model),
            lead=partial(self._bands.build_heading, view_model),
        )

    @staticmethod
    def _windows(view_model: StemsListViewModel) -> bool:
        """Whether the well draws a window over its rows rather than the whole run of them.

        A window slides over rows of one height, which is what a list of recordings alone is: a
        list banded by levels stands captions and strips among its rows, and a folder stands a
        region of its own under one. A folder answers for its own length inside that region, so
        the well holds the rows around it entire.
        """
        return view_model.collapse_levels and not view_model.holds_folders

    def _plain_rows(self, view_model: StemsListViewModel) -> int:
        """How many rows a whole-drawn well stands as a plain run of, which a reading counts by.

        A run broken by a caption, a strip or an open folder's region carries more than rows, so
        it counts none and the reading in force stands.
        """
        if not view_model.collapse_levels or self._open_folders:
            return NO_ROWS

        return view_model.row_count

    def _repaint(self, view_model: StemsListViewModel) -> None:
        """Draw what the rows in view currently hold onto the widgets they stand as."""
        for row in self._reached(view_model):
            self._rows.repaint(row, view_model, releasable=self._releasable)
            self._folders.repaint(row, view_model)

    def _reached(self, view_model: StemsListViewModel) -> Tuple[StemRowViewModel, ...]:
        """The rows the well has widgets for, which are the ones a repaint reaches."""
        if not self._region.windowing:
            return view_model.rows

        start, count = self._region.window
        return view_model.rows[start : start + count]

    def row(self, key: str) -> Optional[StemRowViewModel]:
        """The row a gesture named, as the list last rendered it."""
        return self._view.row(key)

    def stands_open(self, key: str) -> bool:
        """Whether the folder's recordings are in view, which is what a menu names its move by."""
        return self._open_folders.stands_open(key)

    def toggle_folder(self, key: str) -> None:
        """Put a folder's recordings in view or away again, and draw the list as it now stands."""
        self._open_folders.toggle(key)
        self.update_view(self._view)

    @property
    def _following(self) -> bool:
        """A region is holding rows back, so the list watches for the scroll that asks for them."""
        return self._region.windowing or self._folders.following

    def _settle_soon(self) -> None:
        """Ask to read the drawn rows back once the frame that placed them has been rendered.

        The list keeps this going for as long as a region it drew is holding rows back, so a
        region refills itself rather than waiting on a frame hook an owner remembered to wire. A
        list short enough to be drawn whole asks for nothing after the frame that placed it.
        """
        if self._settling:
            return

        self._settling = True
        FrameCallbackManager.set_frame_callback(self._settle)

    def _settle(self) -> None:
        """Read back what the regions drew, refill the ones a scroll has moved on from, and keep
        watching for as long as one of them holds rows it has yet to build."""
        self._settling = False
        if self._region.settle():
            self._draw_window(self._view)
            self._repaint(self._view)

        for key in self._folders.settle():
            self._folders.redraw(key, self._view)
            row = self._view.row(key)
            if row is not None:
                self._folders.repaint(row, self._view)

        if self._following:
            self._settle_soon()

    @property
    def _releasable(self) -> bool:
        """Whether a row may leave, which a list holding on to its last one answers by its count."""
        return self._view.row_count > 1 or not self._offer.keeps_last_row
