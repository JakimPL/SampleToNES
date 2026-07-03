from datetime import datetime
from typing import Any

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    DialogElements,
    GlobalDialogTitleElements,
)
from sampletones_application.categories.elements.settings import (
    ProjectPropertiesElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.settings import (
    TAG_SETTINGS_PROPERTIES_BUTTON_CANCEL,
    TAG_SETTINGS_PROPERTIES_BUTTON_OK,
    TAG_SETTINGS_PROPERTIES_INPUT_AUTHOR,
    TAG_SETTINGS_PROPERTIES_INPUT_COMMENT,
    TAG_SETTINGS_PROPERTIES_INPUT_TITLE,
    TAG_SETTINGS_PROPERTIES_WINDOW,
)
from sampletones_application.layout.project_properties import ProjectPropertiesLayout
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.window import GUIWindow
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_shared.constants.project import (
    MAX_PROJECT_AUTHOR_LENGTH,
    MAX_PROJECT_COMMENT_LENGTH,
    MAX_PROJECT_TITLE_LENGTH,
)


class GUIProjectPropertiesWindow(GUIWindow):
    """Modal form to view and edit the project's title, author, and comment.

    The fields are captured from the current project on each appearance and written back
    through the controller's setters on commit, which mark the project dirty and refresh
    the window title and menu. The title/author/comment feed the exported ``.ftm`` INFO block.
    """

    def __init__(
        self,
        project_controller: ProjectController,
        *,
        layout: ProjectPropertiesLayout,
        language_manager: LanguageManager,
        shortcut_manager: ShortcutManager,
    ) -> None:
        self._project_controller = project_controller
        self._layout = layout
        self._shortcut_manager = shortcut_manager

        self._title_value = ""
        self._author_value = ""
        self._comment_value = ""
        self._created_text = ""
        self._modified_text = ""

        self._ttl_main_window = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TITLE,
            GlobalDialogTitleElements.MAIN_WINDOW,
        ]
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
            parent=self._ttl_main_window,
            width=layout.window.width,
            height=layout.window.height,
        )

    def show(self, *args: Any, **kwargs: Any) -> None:
        if not self._project_controller.is_open:
            return

        super().show(*args, **kwargs)

    def prepare(self, *args: Any, **kwargs: Any) -> None:
        info = self._project_controller.project.info
        self._title_value = info.title
        self._author_value = info.author
        self._comment_value = info.comment
        self._created_text = self._format_timestamp(info.created)
        self._modified_text = self._format_timestamp(info.modified)

    def create_panel(self) -> None:
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
            self._create_text_field(TAG_SETTINGS_PROPERTIES_INPUT_TITLE, self._lbl_title, self._title_value)
            self._create_text_field(TAG_SETTINGS_PROPERTIES_INPUT_AUTHOR, self._lbl_author, self._author_value)
            self._create_comment_field()
            dpg.add_separator()
            self._create_metadata()
            dpg.add_separator()
            self._create_action_buttons()

    def _create_text_field(self, tag: str, label: str, value: str) -> None:
        with dpg.group(horizontal=True):
            dpg.add_text(label)
            dpg.add_spacer(width=self._layout.label_width - int(dpg.get_text_size(label)[0]))
            dpg.add_input_text(tag=tag, default_value=value, width=self._layout.input_width)

        self._shortcut_manager.setup_input_focus_handlers(tag)

    def _create_comment_field(self) -> None:
        dpg.add_text(self._lbl_comment)
        dpg.add_input_text(
            tag=TAG_SETTINGS_PROPERTIES_INPUT_COMMENT,
            default_value=self._comment_value,
            multiline=True,
            width=self._layout.input_width,
            height=self._layout.comment_height,
        )
        self._shortcut_manager.setup_input_focus_handlers(TAG_SETTINGS_PROPERTIES_INPUT_COMMENT)

    def _create_metadata(self) -> None:
        dpg.add_text(f"{self._lbl_created}: {self._created_text}")
        dpg.add_text(f"{self._lbl_modified}: {self._modified_text}")

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
        self._project_controller.set_title(
            dpg.get_value(TAG_SETTINGS_PROPERTIES_INPUT_TITLE)[:MAX_PROJECT_TITLE_LENGTH]
        )
        self._project_controller.set_author(
            dpg.get_value(TAG_SETTINGS_PROPERTIES_INPUT_AUTHOR)[:MAX_PROJECT_AUTHOR_LENGTH]
        )
        self._project_controller.set_comment(
            dpg.get_value(TAG_SETTINGS_PROPERTIES_INPUT_COMMENT)[:MAX_PROJECT_COMMENT_LENGTH]
        )
        self.hide()

    @staticmethod
    def _label(language_manager: LanguageManager, element: ProjectPropertiesElements) -> str:
        return language_manager[Page.SETTINGS, Panel.PROPERTIES, TextType.LABEL, element]

    @staticmethod
    def _format_timestamp(value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M")
