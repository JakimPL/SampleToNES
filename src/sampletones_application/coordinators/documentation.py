from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.documentation.shelf import DocumentationShelf
from sampletones_application.tags.general import TAG_GLOBAL_DIALOG_DOCUMENTATION
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_shared.exceptions import DocumentationUnavailableError
from sampletones_shared.utils.system.opening import FileOpener


class DocumentationCoordinator:
    """Opens the documentation the installation carries in the reader's browser.

    The shelf places a copy of the pages in the user's data folder, and the opener shows its index
    in the program the system gives web pages. An installation that came without its pages tells
    the reader where the documentation lives online, and a copy or a browser that fails is
    reported as an error.
    """

    def __init__(
        self,
        *,
        shelf: DocumentationShelf,
        opener: FileOpener,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
        address: str,
    ) -> None:
        self._shelf = shelf
        self._opener = opener
        self._dialogs = dialogs
        self._language_manager = language_manager
        self._address = address

    def open(self) -> None:
        """Shows the documentation's index in the reader's browser."""
        try:
            self._opener.open(self._shelf.place())
        except DocumentationUnavailableError:
            self._dialogs.show_info(
                TAG_GLOBAL_DIALOG_DOCUMENTATION,
                self._language_manager["global.dialog.template.documentation_unavailable"].format(
                    address=self._address,
                ),
                self._language_manager["global.dialog.title.documentation"],
                modal=True,
            )
        except OSError as error:
            self._dialogs.show_error(error, self._language_manager["global.dialog.message.documentation_not_opened"])
