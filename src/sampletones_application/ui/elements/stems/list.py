from typing import Optional

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.ui.elements.layout.well import well
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.stems.bands import LevelBands
from sampletones_application.ui.elements.stems.gestures import (
    ChannelCallback,
    ChannelsCallback,
    KeyOffsetCallback,
    KeyPairCallback,
    StemsGestures,
)
from sampletones_application.ui.elements.stems.messages import StemsMessages
from sampletones_application.ui.elements.stems.offer import StemsListOffer
from sampletones_application.ui.elements.stems.row import StemRowRenderer
from sampletones_application.ui.elements.stems.tags import StemsTags
from sampletones_application.view_model.shared.stems import (
    StemRowViewModel,
    StemsListViewModel,
)
from sampletones_shared.types.callback import StringCallback
from sampletones_shared.utils.callbacks import CallbackMixin


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
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        offer: StemsListOffer,
    ) -> None:
        self._tags = StemsTags(prefix=prefix)
        self._layout = layout
        self._offer = offer
        self._view = StemsListViewModel.empty()

        self._messages = StemsMessages(
            language_manager,
            offer=offer,
            activatable=lambda: self.activatable,
        )
        self._gestures = StemsGestures(self._tags, messages=self._messages, status_bar=status_bar)
        self._rows = StemRowRenderer(
            self._tags,
            layout=layout,
            offer=offer,
            language_manager=language_manager,
            messages=self._messages,
            gestures=self._gestures,
        )
        self._bands = LevelBands(
            self._tags,
            layout=layout,
            offer=offer,
            language_manager=language_manager,
            rows=self._rows,
            gestures=self._gestures,
        )

        self.on_channels_changed: Optional[ChannelsCallback] = None
        self.on_channel_toggled: Optional[ChannelCallback] = None
        self.on_remove_requested: Optional[StringCallback] = None
        self.on_menu_requested: Optional[StringCallback] = None
        self.on_row_activated: Optional[StringCallback] = None
        self.on_dropped_on_row: Optional[KeyPairCallback] = None
        self.on_dropped_on_level: Optional[KeyOffsetCallback] = None

        self._gestures.on_channels_settled = lambda key, channels: self.call(self.on_channels_changed, key, channels)
        self._gestures.on_channel_toggled = lambda key, channel: self.call(self.on_channel_toggled, key, channel)
        self._gestures.on_removal_asked = lambda key: self.call(self.on_remove_requested, key)
        self._gestures.on_menu_asked = lambda key: self.call(self.on_menu_requested, key)
        self._gestures.on_row_activated = lambda key: self.call(self.on_row_activated, key)
        self._gestures.on_dropped_on_row = lambda key, target: self.call(self.on_dropped_on_row, key, target)
        self._gestures.on_dropped_on_level = lambda key, position: self.call(self.on_dropped_on_level, key, position)

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
        well(
            parent,
            self._tags.well,
            padding=self._layout.well_padding,
            margin=self._layout.well_margin,
            show=show,
        )

    def update_view(self, view_model: StemsListViewModel) -> None:
        """Take up a new reading of the setup: rebuild the bands where it reshapes them, repaint
        the rows either way."""
        self._view = view_model
        self._messages.reads(view_model)
        self._gestures.reads(view_model)
        self._bands.rebuild_if_reshaped(view_model)
        for row in view_model.rows:
            self._rows.repaint(row, view_model, releasable=self._releasable)

    def row(self, key: str) -> Optional[StemRowViewModel]:
        """The row a gesture named, as the list last rendered it."""
        return self._view.row(key)

    @property
    def _releasable(self) -> bool:
        """Whether a row may leave, which a list holding on to its last one answers by its count."""
        return self._view.row_count > 1 or not self._offer.keeps_last_row
