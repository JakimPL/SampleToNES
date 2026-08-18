import re
import uuid
from pathlib import Path
from typing import Callable, Dict, List, Optional, Pattern, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON_CANCEL,
    SUF_BUTTON_OK,
    SUF_BUTTON_SAVE,
    SUF_BUTTON_SHOW_TRACEBACK,
    SUF_CHECKBOX,
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
from sampletones_application.ui.elements.trace import GUITraceback
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.align import center_when_settled, table_wrapper
from sampletones_application.utils.gui.dialog_navigation import (
    DialogKeyboardNavigator,
    FocusStop,
)
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_delete_item,
)
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
        self._lbl_traceback_show = language_manager["global.traceback.label.show"]

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

    # TODO: refactor
    def show_error(
        self,
        exception: Exception,
        message: Optional[str] = None,
    ) -> None:
        tag = get_dialog_tag(TAG_GLOBAL_DIALOG_ERROR)
        show_button_tag = compose_tag(tag, SUF_BUTTON_SHOW_TRACEBACK)
        ok_button_tag = compose_tag(tag, SUF_BUTTON_OK)
        navigator: Optional[DialogKeyboardNavigator] = None

        def close() -> None:
            if navigator is not None:
                navigator.dispose()

            dpg_delete_item(tag)

        with dpg.window(
            label=self._language_manager["global.dialog.title.error"],
            tag=tag,
            modal=True,
            min_size=(self._error_width, self._error_height),
            autosize=True,
            no_scrollbar=False,
            on_close=close,
        ):
            _bind_dialog_theme(tag)
            if message is not None:
                dpg.add_text(message, parent=tag, wrap=self._error_wrap)

            group_tag = compose_tag(tag, SUF_GROUP)
            with dpg.group(tag=group_tag, parent=tag):
                name_text = dpg.add_text(
                    f"{type(exception).__name__!s}: ",
                    parent=group_tag,
                )
                dpg_set_palette_color(name_text, self._col_text_error)
                message_text = dpg.add_text(
                    str(exception),
                    parent=group_tag,
                    wrap=self._error_wrap,
                )
                dpg_set_palette_color(message_text, self._col_text_error)

            traceback = GUITraceback(
                parent=tag,
                exception=exception,
                language_manager=self._language_manager,
            )

            dpg.add_separator()

            def toggle_traceback() -> None:
                traceback.toggle_visibility()
                dpg_configure_item(
                    show_button_tag,
                    label=(
                        self._lbl_traceback_show
                        if not traceback.visible
                        else self._language_manager["global.traceback.label.hide"]
                    ),
                )

            @table_wrapper(columns=2)
            def content(_: None) -> None:
                GUIButton(
                    tag=show_button_tag,
                    label=self._lbl_traceback_show,
                    width=-1,
                    callback=toggle_traceback,
                )
                GUIButton(
                    tag=ok_button_tag,
                    label=self._lbl_ok,
                    callback=close,
                    width=-1,
                )

            content(None)

        navigator = _install_navigation(
            window_tag=tag,
            stops=[
                FocusStop.button(show_button_tag, toggle_traceback),
                FocusStop.button(ok_button_tag, close),
            ],
            on_escape=close,
            key_router=self._router,
            shortcut_source=self._shortcuts,
            initial_index=1,
        )
        center_when_settled(tag)

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

    # TODO: refactor
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
        tag = get_dialog_tag(tag)
        opt_out_tag = compose_tag(tag, SUF_CHECKBOX)
        cancel_label = cancel_label if cancel_label is not None else self._lbl_cancel
        ok_button_tag = compose_tag(tag, SUF_BUTTON_OK)
        cancel_button_tag = compose_tag(tag, SUF_BUTTON_CANCEL)
        navigator: Optional[DialogKeyboardNavigator] = None

        def disable() -> None:
            dpg_configure_item(ok_button_tag, enabled=False)
            dpg_configure_item(cancel_button_tag, enabled=False)

        def close() -> None:
            if navigator is not None:
                navigator.dispose()

            dpg_delete_item(tag)

        def _on_confirm() -> None:
            disable()
            if opt_out_label is not None and on_opt_out is not None and dpg.get_value(opt_out_tag):
                on_opt_out()

            on_confirm()
            close()

        def _on_cancel() -> None:
            disable()
            if on_cancel is not None:
                on_cancel()

            close()

        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent, wrap=self._default_wrap)

            if path is not None:
                GUIPathText(
                    tag=compose_tag(tag, SUF_PATH),
                    path=path,
                    parent=parent,
                    color=self._col_path,
                    hover_color=self._col_path_hover,
                    status_message=self._msg_path,
                    use_filename_only=True,
                    status_bar=self._status_bar,
                )

            if opt_out_label is not None:
                dpg.add_checkbox(
                    label=opt_out_label,
                    tag=opt_out_tag,
                    parent=parent,
                )

            @table_wrapper(columns=2)
            def buttons(_: None) -> None:
                GUIButton(
                    tag=ok_button_tag,
                    label=ok_label,
                    callback=_on_confirm,
                    width=-1,
                )
                GUIButton(
                    tag=cancel_button_tag,
                    label=cancel_label,
                    callback=_on_cancel,
                    width=-1,
                )

            buttons(None)

        with dpg.window(
            label=title,
            tag=tag,
            modal=True,
            min_size=(self._default_width, self._confirmation_height),
            no_resize=True,
            on_close=_on_cancel,
        ):
            _bind_dialog_theme(tag)
            content(tag)

        navigator = _install_navigation(
            window_tag=tag,
            stops=[
                FocusStop.button(ok_button_tag, _on_confirm),
                FocusStop.button(cancel_button_tag, _on_cancel),
            ],
            on_escape=_on_cancel,
            key_router=self._router,
            shortcut_source=self._shortcuts,
            initial_index=1,
        )
        center_when_settled(tag)

    # TODO: refactor
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
        tag = get_dialog_tag(tag)
        save_button_tag = compose_tag(tag, SUF_BUTTON_SAVE)
        ok_button_tag = compose_tag(tag, SUF_BUTTON_OK)
        cancel_button_tag = compose_tag(tag, SUF_BUTTON_CANCEL)
        navigator: Optional[DialogKeyboardNavigator] = None

        def disable() -> None:
            dpg_configure_item(save_button_tag, enabled=False)
            dpg_configure_item(ok_button_tag, enabled=False)
            dpg_configure_item(cancel_button_tag, enabled=False)

        def close() -> None:
            if navigator is not None:
                navigator.dispose()

            dpg_delete_item(tag)

        def _on_save() -> None:
            if not on_save():
                return

            disable()
            on_confirm()
            close()

        def _on_confirm() -> None:
            disable()
            on_confirm()
            close()

        def _on_cancel() -> None:
            disable()
            close()

        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent, wrap=self._default_wrap)

            @table_wrapper(columns=3)
            def buttons(_: None) -> None:
                GUIButton(
                    tag=save_button_tag,
                    label=self._language_manager["global.dialog.label.save"],
                    callback=_on_save,
                    width=-1,
                )
                GUIButton(
                    tag=ok_button_tag,
                    label=ok_label,
                    callback=_on_confirm,
                    width=-1,
                )
                GUIButton(
                    tag=cancel_button_tag,
                    label=self._lbl_cancel,
                    callback=_on_cancel,
                    width=-1,
                )

            buttons(None)

        with dpg.window(
            label=title,
            tag=tag,
            modal=True,
            min_size=(self._default_width, self._confirmation_height),
            no_resize=True,
            on_close=close,
        ):
            _bind_dialog_theme(tag)
            content(tag)

        navigator = _install_navigation(
            window_tag=tag,
            stops=[
                FocusStop.button(save_button_tag, _on_save),
                FocusStop.button(ok_button_tag, _on_confirm),
                FocusStop.button(cancel_button_tag, _on_cancel),
            ],
            on_escape=_on_cancel,
            key_router=self._router,
            shortcut_source=self._shortcuts,
            initial_index=2,
        )
        center_when_settled(tag)

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
