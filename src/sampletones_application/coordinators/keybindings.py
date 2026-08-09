from typing import Optional, Tuple

from sampletones_application.categories.elements.settings import (
    KeybindingActionElements,
    KeybindingCategoryElements,
    KeybindingsElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.tags.settings import (
    TAG_SETTINGS_KEYBINDINGS_DIALOG_DISCARD,
    TAG_SETTINGS_KEYBINDINGS_DIALOG_REASSIGN,
    TAG_SETTINGS_KEYBINDINGS_DIALOG_RESET,
)
from sampletones_application.ui.panels.dialogs.keybindings import GUIKeybindingsWindow
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.shortcuts.catalog import ShortcutCatalog
from sampletones_application.utils.gui.shortcuts.draft import ShortcutDraft
from sampletones_application.utils.gui.shortcuts.ids import (
    EDITABLE_SHORTCUT_CATEGORIES,
    SHORTCUT_IDS_BY_NAME,
    ShortcutCategory,
    ShortcutId,
)
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.view_model.shared.keybindings import (
    KeybindingGroup,
    KeybindingRow,
    KeybindingsViewModel,
)

NO_COMBINATION: str = ""
NO_MESSAGE: str = ""


class KeybindingsCoordinator:
    """Owns the keys a reader is editing: the draft they stand in, and what confirming them means.

    The dialog edits a draft while the application keeps running on the keys it started with, so
    Escape, Tab and Enter answer the same way throughout a session of rebinding them. Confirming
    hands the draft's scheme to the source every action resolves against and writes the scheme name
    and the rebound actions to the session; cancelling drops the draft and leaves the keys alone.

    An assignment onto keys another action of the same scope holds is offered after a prompt naming
    that action, which is then left unbound — one combination reaches one action within a scope.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        shortcut_source: ShortcutSource,
        shortcut_catalog: ShortcutCatalog,
        *,
        window: GUIKeybindingsWindow,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
    ) -> None:
        self._session_manager = session_manager
        self._shortcut_source = shortcut_source
        self._shortcut_catalog = shortcut_catalog
        self._window = window
        self._dialogs = dialogs
        self._language_manager = language_manager

        self._draft: Optional[ShortcutDraft] = None
        self._scheme_name: str = shortcut_source.scheme.name
        self._selected: Optional[ShortcutId] = None
        self._message: str = NO_MESSAGE

        self._window.on_scheme_selected = self._select_scheme
        self._window.on_action_selected = self._select_action
        self._window.on_combination_typed = self._type_combination
        self._window.on_combination_captured = self._capture_combination
        self._window.on_clear = self._clear
        self._window.on_reset = self._request_reset
        self._window.on_commit = self._commit
        self._window.on_cancel = self._request_close

    def open(self) -> None:
        """Shows the dialog on a draft of the keys the session runs under."""
        self._open_draft(self._session_manager.shortcut_scheme_name)
        self._window.open(self._view_model())

    def _open_draft(self, name: str) -> None:
        """Starts a draft over the named scheme, on the keys a session stores for it."""
        scheme = self._shortcut_catalog.select(name)
        self._scheme_name = scheme.name
        self._draft = ShortcutDraft.open(scheme, self._session_manager.shortcut_overrides)
        self._selected = None
        self._message = NO_MESSAGE

    def _select_scheme(self, name: str) -> None:
        """Opens another scheme as it ships, which is the keyboard the reader asked to work from."""
        if name == self._scheme_name:
            return

        self._open_draft(name)
        self._window.update_view(self._view_model())

    def _select_action(self, name: str) -> None:
        """Puts an action's keys in the entry box, which is where a written combination is given."""
        self._selected = SHORTCUT_IDS_BY_NAME[name]
        self._message = NO_MESSAGE
        self._window.update_view(self._view_model())

    def _type_combination(self, text: str) -> None:
        """Gives the selected action the keys a reader wrote out, reporting what reads as no key."""
        shortcut_id = self._require_selected()
        try:
            combination = KeyCombination.parse(text)
        except KeyError:
            self._message = self._template(KeybindingsElements.UNREADABLE_COMBINATION).format(combination=text)
            self._window.update_view(self._view_model())
            return

        self._assign(shortcut_id, combination)

    def _capture_combination(self, combination: KeyCombination) -> None:
        """Gives the selected action the keys a reader pressed."""
        self._assign(self._require_selected(), combination)

    def _assign(self, shortcut_id: ShortcutId, combination: KeyCombination) -> None:
        """Assigns the combination, asking first where another action of the scope holds it."""
        draft = self._require_draft()
        self._message = NO_MESSAGE
        claimant = draft.claimant(shortcut_id, combination)
        if claimant is None:
            self._apply(draft.assign(shortcut_id, combination))
            return

        self._window.yield_to(lambda: self._ask_to_reassign(shortcut_id, combination, claimant))

    def _ask_to_reassign(
        self,
        shortcut_id: ShortcutId,
        combination: KeyCombination,
        claimant: ShortcutId,
    ) -> None:
        message = self._template(KeybindingsElements.REASSIGN_CONFIRMATION).format(
            combination=combination.display(),
            holder=self._action_label(claimant),
            action=self._action_label(shortcut_id),
        )
        self._dialogs.show_confirmation(
            tag=TAG_SETTINGS_KEYBINDINGS_DIALOG_REASSIGN,
            title=self._title(KeybindingsElements.REASSIGN_CONFIRMATION),
            message=message,
            on_confirm=lambda: self._reassign(shortcut_id, combination),
            on_cancel=self._window.resume,
            ok_label=self._label(KeybindingsElements.REASSIGN_BUTTON),
        )

    def _reassign(self, shortcut_id: ShortcutId, combination: KeyCombination) -> None:
        """Takes the keys for the action the reader named, leaving the action that held them free."""
        self._apply(self._require_draft().assign(shortcut_id, combination))
        self._window.resume()

    def _clear(self) -> None:
        """Leaves the selected action unbound, its keys free for another action to take."""
        self._message = NO_MESSAGE
        self._apply(self._require_draft().clear(self._require_selected()))

    def _request_reset(self) -> None:
        """Answers Reset, asking before the shipped keys replace what the reader has given."""
        self._window.yield_to(self._ask_to_reset)

    def _ask_to_reset(self) -> None:
        self._dialogs.show_confirmation(
            tag=TAG_SETTINGS_KEYBINDINGS_DIALOG_RESET,
            title=self._title(KeybindingsElements.RESET_CONFIRMATION),
            message=self._message_text(KeybindingsElements.RESET_CONFIRMATION),
            on_confirm=self._reset,
            on_cancel=self._window.resume,
            ok_label=self._language_manager["global.dialog.label.ok"],
        )

    def _reset(self) -> None:
        self._message = NO_MESSAGE
        self._apply(self._require_draft().reset())
        self._window.resume()

    def _commit(self) -> None:
        """Puts the draft's keys in force and writes the scheme and the rebound actions down."""
        draft = self._require_draft()
        self._shortcut_source.activate(draft.scheme())
        self._session_manager.set_shortcut_scheme_name(self._scheme_name)
        self._session_manager.set_shortcut_overrides(draft.overrides())
        self._close()

    def _request_close(self) -> None:
        """Answers Cancel, Escape and the title bar's close button, asking before losing an edit."""
        if not self._require_draft().is_dirty:
            self._close()
            return

        self._window.yield_to(self._ask_to_discard)

    def _ask_to_discard(self) -> None:
        self._dialogs.show_confirmation(
            tag=TAG_SETTINGS_KEYBINDINGS_DIALOG_DISCARD,
            title=self._title(KeybindingsElements.DISCARD_CONFIRMATION),
            message=self._message_text(KeybindingsElements.DISCARD_CONFIRMATION),
            on_confirm=self._close,
            on_cancel=self._window.resume,
            ok_label=self._label(KeybindingsElements.DISCARD_BUTTON),
            cancel_label=self._label(KeybindingsElements.KEEP_EDITING_BUTTON),
        )

    def _close(self) -> None:
        self._draft = None
        self._selected = None
        self._window.hide()

    def _apply(self, draft: ShortcutDraft) -> None:
        """Holds the edited draft and shows what it left the actions answering to."""
        self._draft = draft
        self._window.update_view(self._view_model())

    def _view_model(self) -> KeybindingsViewModel:
        draft = self._require_draft()
        return KeybindingsViewModel(
            groups=tuple(self._group(category, draft) for category in EDITABLE_SHORTCUT_CATEGORIES),
            schemes=self._shortcut_catalog.names,
            scheme=self._scheme_name,
            selected=None if self._selected is None else self._selected.value,
            combination=self._selected_combination(draft),
            message=self._message,
        )

    def _group(self, category: ShortcutCategory, draft: ShortcutDraft) -> KeybindingGroup:
        return KeybindingGroup(
            category=category.value,
            label=self._category_label(category),
            rows=self._rows(category, draft),
        )

    def _rows(
        self,
        category: ShortcutCategory,
        draft: ShortcutDraft,
    ) -> Tuple[KeybindingRow, ...]:
        return tuple(
            KeybindingRow(
                action=shortcut_id.value,
                label=self._action_label(shortcut_id),
                combination=self._displayed(draft.combination(shortcut_id)),
            )
            for shortcut_id in ShortcutId
            if shortcut_id.category is category
        )

    def _selected_combination(self, draft: ShortcutDraft) -> str:
        """The keys the entry box shows, empty while no action is selected."""
        if self._selected is None:
            return NO_COMBINATION

        return self._displayed(draft.combination(self._selected))

    @staticmethod
    def _displayed(combination: Optional[KeyCombination]) -> str:
        return NO_COMBINATION if combination is None else combination.display()

    def _action_label(self, shortcut_id: ShortcutId) -> str:
        """The name a reader finds an action under, which its element mirrors member for member."""
        return self._action_text(KeybindingActionElements[shortcut_id.name])

    def _category_label(self, category: ShortcutCategory) -> str:
        """The name a reader finds a scope under, which its element mirrors member for member."""
        return self._category_text(KeybindingCategoryElements[category.name])

    def _action_text(self, element: KeybindingActionElements) -> str:
        return self._language_manager[
            Page.SETTINGS,
            Panel.KEYBINDINGS,
            TextType.LABEL,
            element,
        ]

    def _category_text(self, element: KeybindingCategoryElements) -> str:
        return self._language_manager[
            Page.SETTINGS,
            Panel.KEYBINDINGS,
            TextType.TITLE,
            element,
        ]

    def _label(self, element: KeybindingsElements) -> str:
        return self._language_manager[
            Page.SETTINGS,
            Panel.KEYBINDINGS,
            TextType.LABEL,
            element,
        ]

    def _title(self, element: KeybindingsElements) -> str:
        return self._language_manager[
            Page.SETTINGS,
            Panel.KEYBINDINGS,
            TextType.TITLE,
            element,
        ]

    def _message_text(self, element: KeybindingsElements) -> str:
        return self._language_manager[
            Page.SETTINGS,
            Panel.KEYBINDINGS,
            TextType.MESSAGE,
            element,
        ]

    def _template(self, element: KeybindingsElements) -> str:
        return self._language_manager[
            Page.SETTINGS,
            Panel.KEYBINDINGS,
            TextType.TEMPLATE,
            element,
        ]

    def _require_draft(self) -> ShortcutDraft:
        """The keys the open dialog is editing.

        Raises:
            SystemError: when the dialog is driven while closed.
        """
        if self._draft is None:
            raise SystemError("The keybindings are edited only while the dialog is open")

        return self._draft

    def _require_selected(self) -> ShortcutId:
        """The action the reader is giving keys to.

        Raises:
            SystemError: when a combination arrives with no action selected.
        """
        if self._selected is None:
            raise SystemError("A combination is given to the action the dialog has selected")

        return self._selected
