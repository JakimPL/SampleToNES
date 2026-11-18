from typing import Final

from sampletones_application.categories.dialog import dialog_title, filter_name
from sampletones_application.categories.elements.global_ import (
    FileFilterElements,
    GlobalDialogTitleElements,
)
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.paths import LANG_EN

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)


class TestDialogTexts:
    """A dialog's title and a file type's name are read from the entries the language file keys them by."""

    def test_a_title_is_the_dialogs_own_entry(self) -> None:
        assert (
            dialog_title(LANGUAGE_MANAGER, GlobalDialogTitleElements.EXPORT_NSF_PROJECT)
            == LANGUAGE_MANAGER["global.dialog.title.export_nsf_project"]
        )

    def test_a_filter_is_the_file_types_own_entry(self) -> None:
        assert filter_name(LANGUAGE_MANAGER, FileFilterElements.NSF) == LANGUAGE_MANAGER["global.dialog.filter.nsf"]
