from sampletones_application.categories.elements.global_ import (
    FileFilterElements,
    GlobalDialogTitleElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager


def dialog_title(language_manager: LanguageManager, element: GlobalDialogTitleElements) -> str:
    """Resolves the title a dialog shows, the words every surface opening that dialog prints.

    An export's save dialog and its setup window are titled by the same entry, so a format reads
    the same way wherever it is offered.
    """
    return language_manager[
        Page.GLOBAL,
        Panel.DIALOG,
        TextType.TITLE,
        element,
    ]


def filter_name(language_manager: LanguageManager, element: FileFilterElements) -> str:
    """Resolves the name a file dialog shows a file type under."""
    return language_manager[
        Page.GLOBAL,
        Panel.DIALOG,
        TextType.FILTER,
        element,
    ]
