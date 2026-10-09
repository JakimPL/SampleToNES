from sampletones_application.categories.manager import LanguageManager
from sampletones_application.utils.gui.dialogs import DialogsRenderer


class UnhandledFailurePresenter:
    """Tells the reader that an action stopped on a failure nothing recovered from.

    ``UnhandledFailures`` hands every such failure here on the render thread. Nothing more precise
    can be said about a failure no coordinator named, so the report opens with one plain line and
    carries the error and its traceback.
    """

    def __init__(
        self,
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
    ) -> None:
        self._dialogs = dialogs
        self._language_manager = language_manager

    def present(self, exception: Exception) -> None:
        """Shows the reader ``exception`` under the line saying the last action did not finish."""
        self._dialogs.show_failure_report(
            exception,
            self._language_manager["global.dialog.message.unexpected_failure"],
        )
