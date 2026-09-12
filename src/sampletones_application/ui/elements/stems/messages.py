from typing import Any, Optional, Tuple

from sampletones_application.categories.context import channel_label
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.ui.elements.stems.expansion import OpenFolders
from sampletones_application.ui.elements.stems.host import StemsListHost
from sampletones_application.ui.elements.stems.offer import StemsListOffer
from sampletones_application.view_model.shared.stems import (
    StemRowViewModel,
    StemsListViewModel,
)
from sampletones_core.constants.enums import ChannelName


class StemsMessages:
    """What a stems list puts to a reader: the hover explanation and the status-bar line.

    The status bar asks the widget under the pointer to explain itself, so there is one answer per
    widget kind and each reads the row the widget carries. What a list offers decides which answer
    a row gives, which is why the offer is stated once and read here.
    """

    def __init__(
        self,
        language_manager: LanguageManager,
        *,
        offer: StemsListOffer,
        open_folders: OpenFolders,
        host: StemsListHost,
    ) -> None:
        self._language_manager = language_manager
        self._offer = offer
        self._open_folders = open_folders
        self._host = host
        self._view = StemsListViewModel.empty()
        self._msg_drag = language_manager["global.stems.message.drag_tooltip"]
        self._msg_inert = language_manager["global.stems.message.inert_tooltip"]
        self._msg_missing = language_manager["global.stems.message.missing_tooltip"]
        self._msg_unoffered = language_manager["global.stems.message.unoffered_tooltip"]
        self._msg_folder = language_manager["global.stems.message.folder_tooltip"]

    def reads(self, view_model: StemsListViewModel) -> None:
        """Takes up the view the list is drawing, which is what every answer is read from."""
        self._view = view_model

    def row_explanation(self, row: StemRowViewModel) -> str:
        """What the row's hover states: where the source is, why it is grayed out where it
        contributes nothing, and how it moves where the list lets it."""
        lines = [str(row.path)]
        if row.stands_for_a_folder:
            lines.append(self._msg_folder)
        elif not row.available:
            lines.append(self._msg_missing)
        elif not row.offers_channels:
            lines.append(self._msg_unoffered)
        elif not row.takes_part:
            lines.append(self._msg_inert)

        if self._offer.drags(self._view):
            lines.append(self._msg_drag)

        return "\n".join(lines)

    def name(self, *_args: Any, user_data: str, **_kwargs: Any) -> str:
        """The status line a row's name puts up: what the gestures it takes would do to it."""
        row = self._row(user_data)
        if row is None:
            return ""

        if row.stands_for_a_folder:
            return self._language_manager["global.stems.message.status_folder_row"].format(
                name=row.name,
                count=row.holds,
            )

        return " ".join(self._row_gestures(row))

    def _row_gestures(self, row: StemRowViewModel) -> Tuple[str, ...]:
        """What a reader can do to a recording, in the order the list offers it.

        A list that sounds a row says so, since a double-click is the one gesture nothing on the
        row draws; a list that neither drags nor reveals reads as the name alone.
        """
        lines: Tuple[str, ...] = ()
        if self._offer.drags(self._view):
            lines += (self._language_manager["global.stems.message.status_row_drag"].format(name=row.name),)
        if self._host.activatable:
            lines += (self._language_manager["global.stems.message.status_row_reveal"].format(name=row.name),)

        if self._host.playable:
            lines += (self._language_manager["global.stems.message.status_row_play"].format(name=row.name),)

        return lines or (row.name,)

    def channel(
        self,
        *_args: Any,
        user_data: Tuple[str, ChannelName],
        **_kwargs: Any,
    ) -> str:
        key, channel_name = user_data
        row = self._row(key)
        if row is None:
            return ""

        channel = channel_label(self._language_manager, channel_name)
        if row.stands_for_a_folder:
            return self._language_manager["global.stems.message.status_folder_channel"].format(
                channel=channel,
                name=row.name,
            )

        if channel_name in self._view.muted_channels:
            return self._language_manager["global.stems.message.status_channel_muted"].format(
                channel=channel,
                name=row.name,
            )

        return self._language_manager["global.stems.message.status_channel"].format(
            channel=channel,
            name=row.name,
        )

    def master(self, *_args: Any, user_data: str, **_kwargs: Any) -> str:
        row = self._row(user_data)
        if row is None:
            return ""

        return self._language_manager["global.stems.message.status_master"].format(name=row.name)

    def remove(self, *_args: Any, user_data: str, **_kwargs: Any) -> str:
        row = self._row(user_data)
        if row is None:
            return ""

        if row.stands_for_a_folder:
            return self._language_manager["global.stems.message.status_folder_remove"].format(name=row.name)

        return self._language_manager["global.stems.message.status_remove"].format(name=row.name)

    def twisty(self, *_args: Any, user_data: str, **_kwargs: Any) -> str:
        """What the marker beside a folder's name does from where it now stands."""
        row = self._row(user_data)
        if row is None:
            return ""

        return self._language_manager[
            (
                "global.stems.message.status_folder_close"
                if self._open_folders.stands_open(user_data)
                else "global.stems.message.status_folder_open"
            )
        ].format(name=row.name)

    def _row(self, key: str) -> Optional[StemRowViewModel]:
        return self._view.row(key)
