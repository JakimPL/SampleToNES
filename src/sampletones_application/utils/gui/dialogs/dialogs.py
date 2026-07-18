import re
import uuid
from pathlib import Path
from typing import Dict, Optional, Pattern, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    DialogElements,
    GlobalDialogTitleElements,
    GlobalMessageElements,
    GlobalTemplateElements,
    StatusElements,
    TracebackElements,
)
from sampletones_application.categories.elements.reconstructions import (
    ReconstructionsInstrumentsElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.global_ import TAG_SEPARATOR
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.tags.general import (
    SUF_BUTTON_CANCEL,
    SUF_BUTTON_OK,
    SUF_BUTTON_SAVE,
    SUF_BUTTON_SHOW_TRACEBACK,
    SUF_CHECKBOX,
    SUF_DIALOG_INFO,
    SUF_GROUP,
    SUF_INPUT,
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
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_delete_item,
)
from sampletones_shared.types.callback import Callback, StringCallback

_TEMPLATE_PLACEHOLDER: Pattern[str] = re.compile(r"\{(\w+)\}")


def get_dialog_tag(base_tag: str) -> str:
    dialog_hash = uuid.uuid4().hex
    return f"{base_tag}{TAG_SEPARATOR}{dialog_hash}"


def _bind_dialog_theme(tag: str) -> None:
    ThemeRegistry.get(TAG_GLOBAL_THEME_DIALOG_WINDOW).bind_to_item(tag)


def _show_modal_dialog(
    tag: str,
    title: str,
    content: StringCallback,
    *,
    ok_label: str,
    width: int,
    height: int,
    modal: bool = True,
) -> None:
    with dpg.window(
        label=title,
        tag=tag,
        modal=modal,
        width=width,
        min_size=(width, height),
        no_resize=True,
        autosize=True,
        on_close=lambda: dpg_delete_item(tag),
    ):
        _bind_dialog_theme(tag)
        content(tag)
        dpg.add_separator()
        ok_button_tag = f"{tag}{SUF_BUTTON_OK}"
        GUIButton(
            tag=ok_button_tag,
            label=ok_label,
            callback=lambda: dpg_delete_item(tag),
            width=-1,
        )

        center_when_settled(tag)


class DialogsRenderer:
    def __init__(
        self,
        *,
        layout: GeneralLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self._language_manager = language_manager
        self._status_bar = status_bar
        self._default_width = layout.dialogs.default.width
        self._default_height = layout.dialogs.default.height
        self._error_width = layout.dialogs.error.width
        self._error_height = layout.dialogs.error.height
        self._confirmation_height = layout.dialogs.confirmation.height
        self._text_input_height = layout.dialogs.text_input.height
        self._default_wrap = layout.dialogs.default.width - 10
        self._error_wrap = layout.dialogs.error.width - 10
        self._col_text_error = layout.colors.text.error
        self._col_text_highlight = layout.colors.text.highlight
        self._col_path = layout.colors.paths.default
        self._col_path_hover = layout.colors.paths.hover
        self._recovery_width = layout.dialogs.recovery.width
        self._recovery_height = layout.dialogs.recovery.height
        self._recovery_wrap = layout.dialogs.recovery.width - 10

        self._msg_path = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.PATH,
        ]
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
        self._lbl_save = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.LABEL,
            DialogElements.SAVE,
        ]
        self._lbl_traceback_show = language_manager[
            Page.GLOBAL,
            Panel.TRACEBACK,
            TextType.LABEL,
            TracebackElements.SHOW,
        ]
        self._lbl_traceback_hide = language_manager[
            Page.GLOBAL,
            Panel.TRACEBACK,
            TextType.LABEL,
            TracebackElements.HIDE,
        ]
        self._ttl_error = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TITLE,
            GlobalDialogTitleElements.ERROR,
        ]
        self._ttl_file_not_found = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TITLE,
            GlobalDialogTitleElements.FILE_NOT_FOUND,
        ]
        self._ttl_reconstruction_not_loaded = language_manager[
            Page.RECONSTRUCTIONS,
            Panel.INSTRUMENTS,
            TextType.TITLE,
            ReconstructionsInstrumentsElements.NOT_LOADED_DIALOG,
        ]
        self._msg_reconstruction_no_data = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            GlobalMessageElements.RECONSTRUCTION_NO_DATA,
        ]
        self._ttl_config_recovery = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TITLE,
            GlobalDialogTitleElements.CONFIGURATION_RECOVERY,
        ]
        self._tpl_config_recovery_intro = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TEMPLATE,
            GlobalTemplateElements.CONFIGURATION_RECOVERY_INTRO,
        ]
        self._msg_config_recovery_earlier_version = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            GlobalMessageElements.CONFIGURATION_RECOVERY_EARLIER_VERSION,
        ]
        self._msg_config_recovery_list_header = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            GlobalMessageElements.CONFIGURATION_RECOVERY_LIST_HEADER,
        ]
        self._msg_config_recovery_path_prefix = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            GlobalMessageElements.CONFIGURATION_RECOVERY_PATH_PREFIX,
        ]

    @property
    def default_wrap(self) -> int:
        """Text wrap width matching the default dialog width, for caller-built content."""
        return self._default_wrap

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

        info_tag = f"{tag}{SUF_DIALOG_INFO}"
        dpg_delete_item(info_tag)
        _show_modal_dialog(
            tag=info_tag,
            title=title,
            content=content,
            ok_label=self._lbl_ok,
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
        source = source_version if source_version is not None else self._msg_config_recovery_earlier_version

        def content(parent: str) -> None:
            self._render_template_bold(
                parent,
                self._tpl_config_recovery_intro,
                {"source": source, "target": target_version},
            )

            dpg.add_text(
                self._msg_config_recovery_list_header,
                parent=parent,
                wrap=self._recovery_wrap,
            )
            for property_name in properties:
                dpg.add_text(
                    f"- {property_name}",
                    parent=parent,
                    wrap=self._recovery_wrap,
                    color=self._col_text_highlight,
                )

            dpg.add_text(
                self._msg_config_recovery_path_prefix,
                parent=parent,
                wrap=self._recovery_wrap,
            )
            GUIPathText(
                tag=f"{parent}{SUF_PATH}",
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
            title=self._ttl_config_recovery,
            content=content,
            ok_label=self._lbl_ok,
            width=self._recovery_width,
            height=self._recovery_height,
            modal=False,
        )

    def _render_template_bold(self, parent: str, template: str, substitutions: Dict[str, str]) -> None:
        """
        Renders a placeholder template on one line with the substituted values in bold.

        The literal spans of ``template`` are drawn as regular text and each ``{name}``
        placeholder is replaced by ``substitutions[name]`` in bold, so a sentence keeps its
        natural word order in the language file while its dynamic values stand out. The
        literal spans carry their own spacing, so the row abuts its runs without extra gaps.
        """
        group_tag = f"{parent}{SUF_GROUP}"
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
        tag = get_dialog_tag(TAG_GLOBAL_DIALOG_ERROR)

        with dpg.window(
            label=self._ttl_error,
            tag=tag,
            modal=True,
            min_size=(self._error_width, self._error_height),
            autosize=True,
            no_scrollbar=False,
            on_close=lambda: dpg_delete_item(tag),
        ):
            _bind_dialog_theme(tag)
            if message is not None:
                dpg.add_text(message, parent=tag, wrap=self._error_wrap)

            group_tag = f"{tag}{SUF_GROUP}"
            with dpg.group(tag=group_tag, parent=tag):
                dpg.add_text(
                    f"{str(type(exception).__name__)}: ",
                    parent=group_tag,
                    color=self._col_text_error,
                )
                dpg.add_text(
                    str(exception),
                    parent=group_tag,
                    wrap=self._error_wrap,
                    color=self._col_text_error,
                )

            traceback = GUITraceback(
                parent=tag,
                exception=exception,
                language_manager=self._language_manager,
            )

            dpg.add_separator()

            @table_wrapper(columns=2)
            def content(_: None) -> None:
                show_button_tag = f"{tag}{SUF_BUTTON_SHOW_TRACEBACK}"

                def toggle_traceback() -> None:
                    traceback.toggle_visibility()
                    dpg_configure_item(
                        show_button_tag,
                        label=(self._lbl_traceback_show if not traceback.visible else self._lbl_traceback_hide),
                    )

                GUIButton(
                    tag=show_button_tag,
                    label=self._lbl_traceback_show,
                    width=-1,
                    callback=toggle_traceback,
                )
                GUIButton(
                    tag=f"{tag}{SUF_BUTTON_OK}",
                    label=self._lbl_ok,
                    callback=lambda: dpg_delete_item(tag),
                    width=-1,
                )

            content(None)

        center_when_settled(tag)

    def show_file_not_found(self, filepath: Path, message: str) -> None:
        tag = get_dialog_tag(TAG_GLOBAL_DIALOG_FILE_NOT_FOUND)

        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent, wrap=self._error_wrap)
            dpg.add_text(
                str(filepath),
                parent=parent,
                color=self._col_path,
                wrap=self._error_wrap,
            )

        _show_modal_dialog(
            tag=tag,
            title=self._ttl_file_not_found,
            content=content,
            ok_label=self._lbl_ok,
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

        ``cancel_label`` names the negative button; it falls back to the shared Cancel label.
        When ``opt_out_label`` is given, a checkbox is shown; if it is ticked when the user
        confirms, ``on_opt_out`` runs as well — letting the caller suppress future prompts.
        """
        tag = get_dialog_tag(tag)
        opt_out_tag = f"{tag}{SUF_CHECKBOX}"
        cancel_label = cancel_label if cancel_label is not None else self._lbl_cancel

        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent, wrap=self._default_wrap)

            if path is not None:
                GUIPathText(
                    tag=f"{tag}{SUF_PATH}",
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

            ok_button_tag = f"{tag}{SUF_BUTTON_OK}"
            cancel_button_tag = f"{tag}{SUF_BUTTON_CANCEL}"

            def disable() -> None:
                dpg_configure_item(ok_button_tag, enabled=False)
                dpg_configure_item(cancel_button_tag, enabled=False)

            def close() -> None:
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
            on_close=lambda: dpg_delete_item(tag),
        ):
            _bind_dialog_theme(tag)
            content(tag)

        center_when_settled(tag)

    def show_text_input(
        self,
        tag: str,
        title: str,
        initial_value: str,
        on_submit: StringCallback,
        *,
        ok_label: str,
    ) -> None:
        """Prompt for a single line of text, delivering the entered value to ``on_submit``.

        Submitting via the OK button or Enter reads the field and invokes ``on_submit``;
        cancelling or closing discards it. The caller owns any validation of the value.
        """
        tag = get_dialog_tag(tag)

        def content(parent: str) -> None:
            input_tag = f"{tag}{SUF_INPUT}"
            ok_button_tag = f"{tag}{SUF_BUTTON_OK}"
            cancel_button_tag = f"{tag}{SUF_BUTTON_CANCEL}"

            def disable() -> None:
                dpg_configure_item(ok_button_tag, enabled=False)
                dpg_configure_item(cancel_button_tag, enabled=False)

            def close() -> None:
                dpg_delete_item(tag)

            def _on_submit() -> None:
                value = dpg.get_value(input_tag)
                disable()
                on_submit(value)
                close()

            def _on_cancel() -> None:
                disable()
                close()

            dpg.add_input_text(
                tag=input_tag,
                parent=parent,
                default_value=initial_value,
                width=-1,
                on_enter=True,
                callback=_on_submit,
            )

            @table_wrapper(columns=2)
            def buttons(_: None) -> None:
                GUIButton(
                    tag=ok_button_tag,
                    label=ok_label,
                    callback=_on_submit,
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
            min_size=(self._default_width, self._text_input_height),
            no_resize=True,
            on_close=lambda: dpg_delete_item(tag),
        ):
            _bind_dialog_theme(tag)
            content(tag)

        center_when_settled(tag)

    def show_save_confirmation(
        self,
        tag: str,
        message: str,
        title: str,
        on_save: Callback,
        on_confirm: Callback,
        *,
        ok_label: str,
    ) -> None:
        tag = get_dialog_tag(tag)

        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent, wrap=self._default_wrap)

            save_button_tag = f"{tag}{SUF_BUTTON_SAVE}"
            ok_button_tag = f"{tag}{SUF_BUTTON_OK}"
            cancel_button_tag = f"{tag}{SUF_BUTTON_CANCEL}"

            def disable() -> None:
                dpg_configure_item(save_button_tag, enabled=False)
                dpg_configure_item(ok_button_tag, enabled=False)
                dpg_configure_item(cancel_button_tag, enabled=False)

            def close() -> None:
                dpg_delete_item(tag)

            def _on_save() -> None:
                disable()
                on_save()
                on_confirm()
                close()

            def _on_confirm() -> None:
                disable()
                on_confirm()
                close()

            def _on_cancel() -> None:
                disable()
                close()

            @table_wrapper(columns=3)
            def buttons(_: None) -> None:
                GUIButton(
                    tag=save_button_tag,
                    label=self._lbl_save,
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
            on_close=lambda: dpg_delete_item(tag),
        ):
            _bind_dialog_theme(tag)
            content(tag)

        center_when_settled(tag)

    def show_reconstruction_not_loaded(self) -> None:
        tag = get_dialog_tag(TAG_RECONSTRUCTIONS_RECONSTRUCTION_DIALOG_NOT_LOADED)

        def content(parent: str) -> None:
            dpg.add_text(
                self._msg_reconstruction_no_data,
                parent=parent,
                wrap=self._error_wrap,
            )

        _show_modal_dialog(
            tag=tag,
            title=self._ttl_reconstruction_not_loaded,
            content=content,
            ok_label=self._lbl_ok,
            width=self._error_width,
            height=self._default_height,
            modal=False,
        )

    def show_message_with_path(self, title: str, message: str, path: Path) -> None:
        tag = get_dialog_tag(TAG_GLOBAL_DIALOG_PATH_MESSAGE)

        def content(parent: str) -> None:
            group_tag = f"{parent}{SUF_GROUP}"
            with dpg.group(parent=parent):
                dpg.add_text(message, parent=group_tag, wrap=self._error_wrap)
                GUIPathText(
                    tag=f"{group_tag}{SUF_PATH}",
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
            width=self._error_width,
            height=self._default_height,
            modal=False,
        )
