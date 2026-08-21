import re
import uuid
from pathlib import Path
from typing import Callable, Dict, List, Optional, Pattern, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON_OK,
    SUF_DIALOG_INFO,
    SUF_GROUP,
    SUF_PATH,
    TAG_GLOBAL_DIALOG_ERROR,
    TAG_GLOBAL_DIALOG_FILE_NOT_FOUND,
    TAG_GLOBAL_DIALOG_PATH_MESSAGE,
    TAG_GLOBAL_THEME_DIALOG_WINDOW,
)
from sampletones_application.tags.reconstructions import (
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_DIALOG_NOT_LOADED,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.path import GUIPathText
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.align import center_when_settled
from sampletones_application.utils.gui.dialog_navigation import (
    DialogKeyboardNavigator,
    FocusStop,
)
from sampletones_application.utils.gui.dialogs.windows.confirmation import (
    GUIConfirmationWindow,
)
from sampletones_application.utils.gui.dialogs.windows.error import (
    GUIErrorDialogWindow,
)
from sampletones_application.utils.gui.dialogs.windows.save_confirmation import (
    GUISaveConfirmationWindow,
)
from sampletones_application.utils.gui.dpg import dpg_delete_item
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.palette.dpg import dpg_set_palette_color
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_shared.types.callback import Callback, StringCallback, VoidCallback

_TEMPLATE_PLACEHOLDER: Pattern[str] = re.compile(r"\{(\w+)\}")


def get_dialog_tag(base_tag: str) -> str:
    dialog_hash = uuid.uuid4().hex
    return compose_tag(base_tag, dialog_hash)


def _bind_dialog_theme(tag: str) -> None:
    ThemeRegistry.get(TAG_GLOBAL_THEME_DIALOG_WINDOW).bind_to_item(tag)


def _install_navigation(
    *,
    window_tag: str,
    stops: List[FocusStop],
    on_escape: VoidCallback,
    key_router: KeyRouter,
    shortcut_source: ShortcutSource,
    initial_index: int = 0,
) -> DialogKeyboardNavigator:
    """Builds and installs the keyboard navigator that claims the keyboard for ``window_tag``."""
    navigator = DialogKeyboardNavigator(
        window_tag=window_tag,
        stops=stops,
        on_escape=on_escape,
        key_router=key_router,
        shortcut_source=shortcut_source,
        initial_index=initial_index,
    )
    navigator.install()
    return navigator


def _show_modal_dialog(
    tag: str,
    title: str,
    content: StringCallback,
    *,
    ok_label: str,
    width: int,
    height: int,
    key_router: KeyRouter,
    shortcut_source: ShortcutSource,
    modal: bool = True,
) -> None:
    ok_button_tag = compose_tag(tag, SUF_BUTTON_OK)
    navigator: Optional[DialogKeyboardNavigator] = None

    def close() -> None:
        if navigator is not None:
            navigator.dispose()

        dpg_delete_item(tag)

    with dpg.window(
        label=title,
        tag=tag,
        modal=modal,
        width=width,
        min_size=(width, height),
        no_resize=True,
        autosize=True,
        on_close=close,
    ):
        _bind_dialog_theme(tag)
        content(tag)
        dpg.add_separator()
        GUIButton(
            tag=ok_button_tag,
            label=ok_label,
            callback=close,
            width=-1,
        )

        center_when_settled(tag)

    if modal:
        navigator = _install_navigation(
            window_tag=tag,
            stops=[FocusStop.button(ok_button_tag, close)],
            on_escape=close,
            key_router=key_router,
            shortcut_source=shortcut_source,
        )


class DialogsRenderer:
    def __init__(
        self,
        *,
        layout: GeneralLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
    ) -> None:
        self._language_manager = language_manager
        self._status_bar = status_bar
        self._router = key_router
        self._shortcuts = shortcut_source
        self._default_width = layout.dialogs.default.width
        self._default_height = layout.dialogs.default.height
        self._error_width = layout.dialogs.error.width
        self._error_height = layout.dialogs.error.height
        self._confirmation_height = layout.dialogs.confirmation.height
        self._default_wrap = layout.dialogs.default.width - 10
        self._error_wrap = layout.dialogs.error.width - 10
        self._col_text_error = layout.colors.text.error
        self._col_text_highlight = layout.colors.text.highlight
        self._col_path = layout.colors.paths.default
        self._col_path_hover = layout.colors.paths.hover
        self._recovery_width = layout.dialogs.recovery.width
        self._recovery_height = layout.dialogs.recovery.height
        self._recovery_wrap = layout.dialogs.recovery.width - 10

        self._msg_path = language_manager["global.status.message.path"]
        self._lbl_ok = language_manager["global.dialog.label.ok"]
        self._lbl_cancel = language_manager["global.dialog.label.cancel"]
        self._lbl_save = language_manager["global.dialog.label.save"]

    def show_modal(
        self,
        tag: str,
        title: str,
        content: StringCallback,
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
        modal: bool = True,
    ) -> None:
        _show_modal_dialog(
            tag,
            title,
            content,
            ok_label=self._lbl_ok,
            key_router=self._router,
            shortcut_source=self._shortcuts,
            width=width if width is not None else self._default_width,
            height=height if height is not None else self._default_height,
            modal=modal,
        )

    def show_info(
        self,
        tag: str,
        message: str,
        title: str,
        *,
        modal: bool = False,
    ) -> None:
        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent, wrap=self._error_wrap)

        info_tag = compose_tag(tag, SUF_DIALOG_INFO)
        dpg_delete_item(info_tag)
        _show_modal_dialog(
            tag=info_tag,
            title=title,
            content=content,
            ok_label=self._lbl_ok,
            key_router=self._router,
            shortcut_source=self._shortcuts,
            width=self._default_width,
            height=self._default_height,
            modal=modal,
        )

    def show_config_recovery(
        self,
        *,
        tag: str,
        source_version: Optional[str],
        target_version: str,
        properties: Tuple[str, ...],
        config_path: Path,
    ) -> None:
        """
        Reports that a stored configuration was migrated, listing the discarded settings.

        The version numbers are emphasised in bold, each discarded setting is drawn in the
        highlight colour to stand apart from the surrounding prose, and the trailing path
        opens the configuration file's directory so the user can edit it directly.
        """
        source = (
            source_version
            if source_version is not None
            else self._language_manager["global.dialog.message.configuration_recovery_earlier_version"]
        )

        def content(parent: str) -> None:
            self._render_template_bold(
                parent,
                self._language_manager["global.dialog.template.configuration_recovery_intro"],
                {"source": source, "target": target_version},
            )

            dpg.add_text(
                self._language_manager["global.dialog.message.configuration_recovery_list_header"],
                parent=parent,
                wrap=self._recovery_wrap,
            )
            for property_name in properties:
                property_text = dpg.add_text(
                    f"- {property_name}",
                    parent=parent,
                    wrap=self._recovery_wrap,
                )
                dpg_set_palette_color(property_text, self._col_text_highlight)

            dpg.add_text(
                self._language_manager["global.dialog.message.configuration_recovery_path_prefix"],
                parent=parent,
                wrap=self._recovery_wrap,
            )
            GUIPathText(
                tag=compose_tag(parent, SUF_PATH),
                path=config_path,
                parent=parent,
                color=self._col_path,
                hover_color=self._col_path_hover,
                status_message=self._msg_path,
                status_bar=self._status_bar,
            )

        dpg_delete_item(tag)
        _show_modal_dialog(
            tag=tag,
            title=self._language_manager["global.dialog.title.configuration_recovery"],
            content=content,
            ok_label=self._lbl_ok,
            key_router=self._router,
            shortcut_source=self._shortcuts,
            width=self._recovery_width,
            height=self._recovery_height,
            modal=False,
        )

    def _render_template_bold(
        self,
        parent: str,
        template: str,
        substitutions: Dict[str, str],
    ) -> None:
        """
        Renders a placeholder template on one line with the substituted values in bold.

        The literal spans of ``template`` are drawn as regular text and each ``{name}``
        placeholder is replaced by ``substitutions[name]`` in bold, so a sentence keeps its
        natural word order in the language file while its dynamic values stand out. The
        literal spans carry their own spacing, so the runs sit flush at exactly that spacing.
        """
        group_tag = compose_tag(parent, SUF_GROUP)
        with dpg.group(
            horizontal=True,
            horizontal_spacing=0,
            tag=group_tag,
            parent=parent,
        ):
            position = 0
            for match in _TEMPLATE_PLACEHOLDER.finditer(template):
                literal = template[position : match.start()]
                if literal:
                    dpg.add_text(literal, parent=group_tag)

                value_item = dpg.add_text(
                    substitutions[match.group(1)],
                    parent=group_tag,
                )
                FontRegistry.bind_to_item(value_item, Font.BOLD)
                position = match.end()

            trailing = template[position:]
            if trailing:
                dpg.add_text(trailing, parent=group_tag)

    def show_error(
        self,
        exception: Exception,
        message: Optional[str] = None,
    ) -> None:
        GUIErrorDialogWindow(
            tag=get_dialog_tag(TAG_GLOBAL_DIALOG_ERROR),
            width=self._error_width,
            height=self._error_height,
            wrap=self._error_wrap,
            language_manager=self._language_manager,
            error_color=self._col_text_error,
            key_router=self._router,
            shortcut_source=self._shortcuts,
        ).show(exception, message)

    def show_file_not_found(self, filepath: Path, message: str) -> None:
        tag = get_dialog_tag(TAG_GLOBAL_DIALOG_FILE_NOT_FOUND)

        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent, wrap=self._error_wrap)
            path_text = dpg.add_text(
                str(filepath),
                parent=parent,
                wrap=self._error_wrap,
            )
            dpg_set_palette_color(path_text, self._col_path)

        _show_modal_dialog(
            tag=tag,
            title=self._language_manager["global.dialog.title.file_not_found"],
            content=content,
            ok_label=self._lbl_ok,
            key_router=self._router,
            shortcut_source=self._shortcuts,
            width=self._error_width,
            height=self._default_height,
        )

    def show_confirmation(
        self,
        tag: str,
        message: str,
        title: str,
        on_confirm: Callback,
        *,
        ok_label: str,
        cancel_label: Optional[str] = None,
        path: Optional[Path] = None,
        opt_out_label: Optional[str] = None,
        on_opt_out: Optional[Callback] = None,
        on_cancel: Optional[Callback] = None,
    ) -> None:
        """Modal confirmation. ``on_confirm``/``on_cancel`` run on the respective choice.

        The title bar's close button reads as the negative choice, so every way out of the
        prompt reaches the caller and a dialog waiting behind it hears the answer.

        ``cancel_label`` names the negative button; it falls back to the shared Cancel label.
        When ``opt_out_label`` is given, a checkbox is shown; if it is ticked when the user
        confirms, ``on_opt_out`` runs as well — letting the caller suppress future prompts.
        """
        GUIConfirmationWindow(
            tag=get_dialog_tag(tag),
            width=self._default_width,
            height=self._confirmation_height,
            wrap=self._default_wrap,
            path_color=self._col_path,
            path_hover_color=self._col_path_hover,
            path_message=self._msg_path,
            status_bar=self._status_bar,
            key_router=self._router,
            shortcut_source=self._shortcuts,
        ).show(
            message,
            title,
            on_confirm,
            ok_label=ok_label,
            cancel_label=cancel_label if cancel_label is not None else self._lbl_cancel,
            path=path,
            opt_out_label=opt_out_label,
            on_opt_out=on_opt_out,
            on_cancel=on_cancel,
        )

    def show_save_confirmation(
        self,
        tag: str,
        message: str,
        title: str,
        on_save: Callable[[], bool],
        on_confirm: Callback,
        *,
        ok_label: str,
    ) -> None:
        """Modal save-or-proceed prompt for an unsaved document.

        ``on_save`` writes the document and reports whether it completed; the prompt runs
        ``on_confirm`` and closes once the save reports success, so a cancelled save keeps the
        prompt open for another attempt. The middle button discards the pending changes and runs
        ``on_confirm`` to proceed, and Cancel — the initially focused button — dismisses the prompt.
        """
        GUISaveConfirmationWindow(
            tag=get_dialog_tag(tag),
            width=self._default_width,
            height=self._confirmation_height,
            wrap=self._default_wrap,
            save_label=self._lbl_save,
            cancel_label=self._lbl_cancel,
            key_router=self._router,
            shortcut_source=self._shortcuts,
        ).show(
            message,
            title,
            on_save,
            on_confirm,
            ok_label=ok_label,
        )

    def show_reconstruction_not_loaded(self) -> None:
        tag = get_dialog_tag(TAG_RECONSTRUCTIONS_RECONSTRUCTION_DIALOG_NOT_LOADED)

        def content(parent: str) -> None:
            dpg.add_text(
                self._language_manager["global.dialog.message.reconstruction_no_data"],
                parent=parent,
                wrap=self._error_wrap,
            )

        _show_modal_dialog(
            tag=tag,
            title=self._language_manager["reconstructions.instruments.title.not_loaded_dialog"],
            content=content,
            ok_label=self._lbl_ok,
            key_router=self._router,
            shortcut_source=self._shortcuts,
            width=self._error_width,
            height=self._default_height,
            modal=False,
        )

    def show_message_with_path(
        self,
        title: str,
        message: str,
        path: Path,
    ) -> None:
        tag = get_dialog_tag(TAG_GLOBAL_DIALOG_PATH_MESSAGE)

        def content(parent: str) -> None:
            group_tag = compose_tag(parent, SUF_GROUP)
            with dpg.group(parent=parent):
                dpg.add_text(message, parent=group_tag, wrap=self._error_wrap)
                GUIPathText(
                    tag=compose_tag(group_tag, SUF_PATH),
                    path=path,
                    parent=group_tag,
                    color=self._col_path,
                    hover_color=self._col_path_hover,
                    status_message=self._msg_path,
                    status_bar=self._status_bar,
                )

        _show_modal_dialog(
            tag=tag,
            title=title,
            content=content,
            ok_label=self._lbl_ok,
            key_router=self._router,
            shortcut_source=self._shortcuts,
            width=self._error_width,
            height=self._default_height,
            modal=False,
        )
