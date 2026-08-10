from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Self

from pydantic import BaseModel, model_validator

from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.utils.gui.shortcuts.ids import (
    SHORTCUT_IDS_BY_NAME,
    ShortcutCategory,
    ShortcutId,
)
from sampletones_application.utils.gui.shortcuts.shortcut import Shortcut
from sampletones_application.utils.gui.shortcuts.written import WrittenShortcut
from sampletones_shared.logger import logger
from sampletones_shared.utils.serialization import load_yaml


class ShortcutScheme(BaseModel, frozen=True):
    """A named set of keybindings, one entry per action the application names.

    The scheme is where a combination is decided: an action declares the id it answers to, and the
    scheme alone says which keys reach it. Every action is answered here, so the combination a menu
    prints, the one a panel acts on and the one a reader edits are the same entry.
    """

    name: str
    bindings: Dict[ShortcutId, WrittenShortcut]

    @cached_property
    def shortcuts(self) -> Dict[ShortcutId, Shortcut]:
        """Every action's binding, read out of its written form once."""
        return {shortcut_id: written.resolve() for shortcut_id, written in self.bindings.items()}

    @cached_property
    def claims(self) -> Dict[ShortcutCategory, Dict[KeyCombination, ShortcutId]]:
        """The action each combination reaches, indexed by the category that answers it.

        A press resolves in one lookup, since a combination names a single action within a
        category while another category is free to give it to an action of its own.
        """
        claims: Dict[ShortcutCategory, Dict[KeyCombination, ShortcutId]] = {
            category: {} for category in ShortcutCategory
        }
        for shortcut_id, shortcut in self.shortcuts.items():
            for combination in shortcut.combinations():
                claims[shortcut_id.category].setdefault(
                    combination,
                    shortcut_id,
                )

        return claims

    @model_validator(mode="after")
    def _read_bindings(self) -> Self:
        """Reads every entry at load, so a scheme in use answers each action with keys that resolve
        and with one action per combination.

        Raises:
            SystemError: when an action goes unanswered, or two actions of one category claim the
                same combination.
            KeyError: when a written combination names a key the key table holds none of.
        """
        self._require_every_action_answered()
        self._require_one_action_per_combination()
        return self

    def shortcut(self, shortcut_id: ShortcutId) -> Shortcut:
        """The binding that answers an action, the combinations it names ready to match a press."""
        return self.shortcuts[shortcut_id]

    def claimant(
        self,
        category: ShortcutCategory,
        combination: KeyCombination,
    ) -> Optional[ShortcutId]:
        """The action of a category a combination reaches.

        An editor asks before it assigns, so a reader is told which action they are taking the keys
        from.

        Args:
            category: The scope asking, which decides what the combination means there.
            combination: The keys to resolve, the modifiers held with them included.

        Returns:
            Optional[ShortcutId]: The action the category binds the combination to, ``None`` while
                the category leaves it unclaimed.
        """
        return self.claims[category].get(combination)

    def action(
        self,
        category: ShortcutCategory,
        event: KeyEvent,
    ) -> Optional[ShortcutId]:
        """The action of a category a press reaches.

        Args:
            category: The scope asking, which decides what the press means there.
            event: The press to resolve, carrying the modifiers held as it fired.

        Returns:
            Optional[ShortcutId]: The action the category binds the press to, ``None`` while the
                category leaves it unnamed.
        """
        return self.claimant(
            category,
            KeyCombination(
                event.key,
                event.modifiers,
            ),
        )

    def with_binding(
        self,
        shortcut_id: ShortcutId,
        combination: Optional[KeyCombination],
    ) -> ShortcutScheme:
        """The scheme with one action answering ``combination``, as it stands for every other entry.

        Args:
            shortcut_id: The action being given keys.
            combination: The keys it answers to, ``None`` leaving it unbound.

        Returns:
            ShortcutScheme: The scheme every action resolves against once the binding is read.

        Raises:
            SystemError: when another action of the same category already answers the combination.
            KeyError: when the combination names a key the key table holds none of.
        """
        return self.with_bindings({shortcut_id: combination})

    def with_bindings(
        self,
        combinations: Mapping[ShortcutId, Optional[KeyCombination]],
    ) -> ShortcutScheme:
        """The scheme as the named actions answer the combinations given, read in one step.

        A named action answers the combination stated and that alone, so the aliases the scheme
        shipped it with go with the keys they extended. Reading the whole set at once is what lets
        two actions trade combinations, each arriving at keys the other is leaving.

        Args:
            combinations: The keys each named action answers to, ``None`` leaving an action unbound.

        Returns:
            ShortcutScheme: The scheme every action resolves against once the bindings are read.

        Raises:
            SystemError: when two actions of one category are left answering one combination.
            KeyError: when a combination names a key the key table holds none of.
        """
        entries: Dict[ShortcutId, WrittenShortcut] = {
            shortcut_id: self.bindings[shortcut_id].rebound(
                None if combination is None else combination.display(),
            )
            for shortcut_id, combination in combinations.items()
        }

        return ShortcutScheme(
            name=self.name,
            bindings={**self.bindings, **entries},
        )

    def with_overrides(
        self,
        overrides: Mapping[str, Optional[str]],
    ) -> ShortcutScheme:
        """The scheme as a reader rebound it, each entry giving one action the keys it names.

        An override names its action the way a keybinding file writes it, which lets a preference
        outlive the build that stored it. The set is read at once, so entries that pass combinations
        between them arrive together; where the whole leaves the scheme unresolvable, the entries are
        read one at a time and each that stands aside costs only itself.

        Args:
            overrides: The combination each rebound action answers to, keyed by the action's name.

        Returns:
            ShortcutScheme: The scheme every action resolves against once the overrides are read.
        """
        if not overrides:
            return self

        try:
            return self.with_bindings(self._read_overrides(overrides))
        except (KeyError, SystemError) as exception:
            logger.warning(f"Keybindings overrides read one entry at a time: {exception}")
            return self._rebound_each(overrides)

    def rebound(self, name: str, combination: Optional[str]) -> ShortcutScheme:
        """The scheme as one stored preference rebinds it, read the way a preference is read.

        An entry takes effect while it names an action this build carries, a key the table holds and
        a combination its category has room for; anything else is reported and the scheme is
        returned as it stands, so one unreadable preference costs only itself.

        Args:
            name: The action the entry rebinds, named the way a keybinding file writes it.
            combination: The keys it answers to, ``None`` leaving the action unbound.

        Returns:
            ShortcutScheme: The scheme the entry leaves in place.
        """
        shortcut_id = SHORTCUT_IDS_BY_NAME.get(name)
        if shortcut_id is None:
            logger.warning(f"Keybinding override names unknown action {name!r}, keeping the scheme's own keys")
            return self

        try:
            return self.with_binding(
                shortcut_id,
                None if combination is None else KeyCombination.parse(combination),
            )
        except (KeyError, SystemError) as exception:
            logger.warning(f"Keybinding override giving {name!r} the combination {combination!r} left out: {exception}")
            return self

    @classmethod
    def load(cls, path: Path) -> ShortcutScheme:
        """Load the scheme a keybinding file holds.

        Raises:
            TypeError: when the file holds a value other than a mapping.
            SystemError: when the file is not available.
        """
        try:
            raw = load_yaml(path)
        except OSError as exception:
            raise SystemError(f"Keybinding file '{path}' not found") from exception

        if not isinstance(raw, dict):
            raise TypeError(f"Keybinding file '{path}' must contain a mapping, got {type(raw)}")

        return cls.model_validate(raw)

    def _read_overrides(
        self,
        overrides: Mapping[str, Optional[str]],
    ) -> Dict[ShortcutId, Optional[KeyCombination]]:
        """Every override as the action and the combination it names.

        Raises:
            KeyError: when an entry names an action this build carries none of, or a key the table
                holds none of.
        """
        return {
            SHORTCUT_IDS_BY_NAME[name]: None if combination is None else KeyCombination.parse(combination)
            for name, combination in overrides.items()
        }

    def _rebound_each(self, overrides: Mapping[str, Optional[str]]) -> ShortcutScheme:
        """The scheme as every override that stands rebinds it, read one entry at a time."""
        scheme = self
        for name, combination in overrides.items():
            scheme = scheme.rebound(name, combination)

        return scheme

    def _require_every_action_answered(self) -> None:
        unanswered: List[str] = [shortcut_id.value for shortcut_id in ShortcutId if shortcut_id not in self.bindings]
        if unanswered:
            raise SystemError(f"Keybinding scheme {self.name!r} leaves actions unanswered: {unanswered}")

    def _require_one_action_per_combination(self) -> None:
        """Checks each action against the index, which holds the first claimant of a combination.

        An action the index answers with someone else is the second to claim that combination
        within its category, which leaves the press ambiguous.
        """
        for shortcut_id, shortcut in self.shortcuts.items():
            for combination in shortcut.combinations():
                claimant = self.claims[shortcut_id.category][combination]
                if claimant is not shortcut_id:
                    raise SystemError(
                        f"Keybinding scheme {self.name!r} gives {combination.display()} to both "
                        f"{claimant.value!r} and {shortcut_id.value!r}, "
                        f"which share the {shortcut_id.category} category"
                    )
