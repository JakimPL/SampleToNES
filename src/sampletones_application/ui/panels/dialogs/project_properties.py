from typing import Any, Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    DialogElements,
)
from sampletones_application.categories.elements.settings import (
    ProjectPropertiesElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.project_properties import ProjectPropertiesLayout
from sampletones_application.tags.general import TAG_GLOBAL_THEME_DIALOG
from sampletones_application.tags.settings import (
    TAG_SETTINGS_PROPERTIES_BUTTON_CANCEL,
    TAG_SETTINGS_PROPERTIES_BUTTON_OK,
    TAG_SETTINGS_PROPERTIES_INPUT_AUTHOR,
    TAG_SETTINGS_PROPERTIES_INPUT_COMMENT,
    TAG_SETTINGS_PROPERTIES_INPUT_TITLE,
    TAG_SETTINGS_PROPERTIES_WINDOW,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.field import labeled_field
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.window import GUIWindow
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.dialog_navigation import (
    DialogKeyboardNavigator,
    FocusStop,
)
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.view_model.shared.project_properties import (
    ProjectPropertiesViewModel,
)
from sampletones_shared.constants.project import (
    MAX_PROJECT_AUTHOR_LENGTH,
    MAX_PROJECT_COMMENT_LENGTH,
    MAX_PROJECT_TITLE_LENGTH,
)


class GUIProjectPropertiesWindow(GUIWindow):
    """Modal form to view and edit the project's title, author, and comment.

    Each appearance renders the view model handed to :meth:`open`, and the edited
    values reach the ``on_commit`` hook on confirmation, so the owner applies
    them as one undoable gesture. The title/author/comment feed the exported
    ``.ftm`` INFO block.
    """

    def __init__(
        self,
        *,
        layout: ProjectPropertiesLayout,
        language_manager: LanguageManager,
        shortcut_manager: ShortcutManager,
    ) -> None:
        self._layout = layout
        self._shortcut_manager = shortcut_manager
        self._dialog_theme = ThemeRegistry.get(TAG_GLOBAL_THEME_DIALOG)
        self._navigator: Optional[DialogKeyboardNavigator] = None

        self.on_commit: Optional[Callable[[str, str, str], None]] = None

        self._title_value = ""
        self._author_value = ""
        self._comment_value = ""
        self._created_text = ""
        self._modified_text = ""

        self._ttl_window = language_manager[
            Page.SETTINGS,
            Panel.PROPERTIES,
            TextType.TITLE,
            ProjectPropertiesElements.WINDOW_TITLE,
        ]
        self._lbl_title = self._label(
            language_manager,
            ProjectPropertiesElements.TITLE,
        )
        self._lbl_author = self._label(
            language_manager,
            ProjectPropertiesElements.AUTHOR,
        )
        self._lbl_comment = self._label(
            language_manager,
            ProjectPropertiesElements.COMMENT,
        )
        self._lbl_created = self._label(
            language_manager,
            ProjectPropertiesElements.CREATED,
        )
        self._lbl_modified = self._label(
            language_manager,
            ProjectPropertiesElements.MODIFIED,
        )
        self._lbl_ok = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.LABEL,
            DialogElements.OK,
        ]
        self._lbl_cancel = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.LABEL,
            DialogElements.CANCEL,
        ]

        super().__init__(
            tag=TAG_SETTINGS_PROPERTIES_WINDOW,
            width=layout.window.width,
            height=layout.window.height,
        )

    def open(self, view_model: ProjectPropertiesViewModel) -> None:
        """Shows the dialog seeded with the given project info."""
        self._title_value = view_model.title
        self._author_value = view_model.author
        self._comment_value = view_model.comment
        self._created_text = view_model.created_text
        self._modified_text = view_model.modified_text
        self.show()

    def prepare(self, *_args: Any, **_kwargs: Any) -> None:
        """The rendered values are seeded by :meth:`open` before the tree rebuilds."""

    def create_window(self) -> None:
        with dpg.window(
            tag=self.tag,
            label=self._ttl_window,
            width=self.width,
            height=self.height,
            no_resize=True,
            no_collapse=True,
            on_close=self.hide,
            modal=True,
        ):
            self._create_text_field(
                TAG_SETTINGS_PROPERTIES_INPUT_TITLE,
                self._lbl_title,
                self._title_value,
            )
            self._create_text_field(
                TAG_SETTINGS_PROPERTIES_INPUT_AUTHOR,
                self._lbl_author,
                self._author_value,
            )
            self._create_comment_field()
            dpg.add_separator()
            self._create_metadata()
            dpg.add_separator()
            self._create_action_buttons()

        for input_tag in (
            TAG_SETTINGS_PROPERTIES_INPUT_TITLE,
            TAG_SETTINGS_PROPERTIES_INPUT_AUTHOR,
            TAG_SETTINGS_PROPERTIES_INPUT_COMMENT,
        ):
            self._dialog_theme.bind_to_item(input_tag)

        self._install_navigation()

    def _install_navigation(self) -> None:
        """Wires Tab/Enter/Escape keyboard navigation over the form's fields and buttons."""
        self._navigator = DialogKeyboardNavigator(
            window_tag=self.tag,
            stops=[
                FocusStop.field(TAG_SETTINGS_PROPERTIES_INPUT_TITLE),
                FocusStop.field(TAG_SETTINGS_PROPERTIES_INPUT_AUTHOR),
                FocusStop.field(TAG_SETTINGS_PROPERTIES_INPUT_COMMENT),
                FocusStop.button(TAG_SETTINGS_PROPERTIES_BUTTON_CANCEL, self.hide),
                FocusStop.button(TAG_SETTINGS_PROPERTIES_BUTTON_OK, self._commit),
            ],
            on_escape=self.hide,
            shortcut_manager=self._shortcut_manager,
        )
        self._navigator.install()

    def _teardown(self) -> None:
        if self._navigator is not None:
            self._navigator.dispose()
            self._navigator = None

    def _create_text_field(self, tag: str, label: str, value: str) -> None:
        with labeled_field(label, self._layout.label_width):
            dpg.add_input_text(tag=tag, default_value=value, width=self._layout.input_width)

        self._shortcut_manager.setup_input_focus_handlers(tag)

    def _create_comment_field(self) -> None:
        label_id = dpg.add_text(self._lbl_comment)
        FontRegistry.bind_to_item(label_id, Font.BOLD)
        dpg.add_input_text(
            tag=TAG_SETTINGS_PROPERTIES_INPUT_COMMENT,
            default_value=self._comment_value,
            multiline=True,
            width=self._layout.input_width,
            height=self._layout.comment_height,
        )
        self._shortcut_manager.setup_input_focus_handlers(TAG_SETTINGS_PROPERTIES_INPUT_COMMENT)

    def _create_metadata(self) -> None:
        self._create_metadata_row(self._lbl_created, self._created_text)
        self._create_metadata_row(self._lbl_modified, self._modified_text)

    def _create_metadata_row(self, label: str, value: str) -> None:
        with dpg.group(horizontal=True):
            label_id = dpg.add_text(f"{label}:")
            FontRegistry.bind_to_item(label_id, Font.BOLD)
            dpg.add_text(value)

    @table_wrapper(columns=2)
    def _create_action_buttons(self) -> None:
        GUIButton(
            tag=TAG_SETTINGS_PROPERTIES_BUTTON_CANCEL,
            label=self._lbl_cancel,
            callback=self.hide,
            width=-1,
        )
        GUIButton(
            tag=TAG_SETTINGS_PROPERTIES_BUTTON_OK,
            label=self._lbl_ok,
            callback=self._commit,
            width=-1,
        )

    def _commit(self) -> None:
        self.call(
            self.on_commit,
            dpg.get_value(TAG_SETTINGS_PROPERTIES_INPUT_TITLE)[:MAX_PROJECT_TITLE_LENGTH],
            dpg.get_value(TAG_SETTINGS_PROPERTIES_INPUT_AUTHOR)[:MAX_PROJECT_AUTHOR_LENGTH],
            dpg.get_value(TAG_SETTINGS_PROPERTIES_INPUT_COMMENT)[:MAX_PROJECT_COMMENT_LENGTH],
        )
        self.hide()

    @staticmethod
    def _label(language_manager: LanguageManager, element: ProjectPropertiesElements) -> str:
        return language_manager[Page.SETTINGS, Panel.PROPERTIES, TextType.LABEL, element]
