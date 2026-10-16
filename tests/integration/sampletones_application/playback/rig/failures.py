from typing import Callable, Optional
from unittest.mock import MagicMock

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.coordinators.playback.failures import PlaybackFailurePresenter
from sampletones_application.utils.gui.dialogs import DialogsRenderer

from .sound import Sound

Tell = Callable[[Optional[Sound], Exception], None]


class RecordedFailures(PlaybackFailurePresenter):
    """The failure presenter one owner's guard reports through, telling the rig what a dialog would show."""

    def __init__(
        self,
        tell: Tell,
        *,
        listener: Sound,
        language_manager: LanguageManager,
    ) -> None:
        super().__init__(dialogs=MagicMock(spec=DialogsRenderer), language_manager=language_manager)
        self._tell = tell
        self._listener = listener

    def present(
        self,
        exception: Exception,
        *,
        message: Optional[str],
    ) -> None:
        self._tell(self._listener, exception)
