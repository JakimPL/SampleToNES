from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Mapping, Optional, Tuple

from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.scheme import ShortcutScheme


@dataclass(frozen=True)
class ShortcutDraft:
    """The keys a reader is giving the actions, held apart from the ones the application runs under.

    An editor works on a draft and hands a scheme over once, which leaves the keys in force steady
    while Escape, Tab and Enter are themselves being rebound. A draft is kept as the actions the
    reader touched and what they gave them, since an override replaces a whole binding: every other
    action answers the scheme the build ships, and the touched entries are what a session stores.
    """

    base: ShortcutScheme
    stored: Dict[ShortcutId, Optional[KeyCombination]]
    edits: Dict[ShortcutId, Optional[KeyCombination]]

    @classmethod
    def open(
        cls,
        base: ShortcutScheme,
        overrides: Mapping[str, Optional[str]],
    ) -> ShortcutDraft:
        """A draft of the scheme a build ships, opened on the keys a session stores.

        The stored preference is read through the scheme, so a draft starts from bindings that
        already resolve and an entry a later build stopped carrying stays behind with the rest of
        the preference in place.

        Args:
            base: The scheme as the build ships it, which the draft states its edits against.
            overrides: The combination each rebound action answers to, keyed by the action's name.

        Returns:
            ShortcutDraft: The draft holding what the session stores and that alone.
        """
        preferred = base.with_overrides(overrides)
        stored: Dict[ShortcutId, Optional[KeyCombination]] = {
            shortcut_id: preferred.shortcut(shortcut_id).combination
            for shortcut_id in ShortcutId
            if preferred.shortcut(shortcut_id) != base.shortcut(shortcut_id)
        }

        return cls(
            base=base,
            stored=stored,
            edits=dict(stored),
        )

    @property
    def is_dirty(self) -> bool:
        """Whether the draft holds keys the session has yet to store."""
        return self.edits != self.stored

    def combination(self, shortcut_id: ShortcutId) -> Optional[KeyCombination]:
        """The keys an action answers to as the draft stands, ``None`` while it is unbound."""
        if shortcut_id in self.edits:
            return self.edits[shortcut_id]

        return self.base.shortcut(shortcut_id).combination

    def claimant(
        self,
        shortcut_id: ShortcutId,
        combination: KeyCombination,
    ) -> Optional[ShortcutId]:
        """The action holding ``combination`` in the category ``shortcut_id`` belongs to.

        An editor asks before it assigns, so a reader is told which action they are taking the keys
        from and the assignment stays theirs to confirm.

        Args:
            shortcut_id: The action the combination is meant for, whose category answers it.
            combination: The keys to look up.

        Returns:
            Optional[ShortcutId]: The action the combination reaches, ``None`` while it is free for
                the asking action to take.
        """
        for other in ShortcutId:
            if other is shortcut_id or other.category is not shortcut_id.category:
                continue

            if combination in self._claimed(other):
                return other

        return None

    def assign(
        self,
        shortcut_id: ShortcutId,
        combination: KeyCombination,
    ) -> ShortcutDraft:
        """The draft with an action answering ``combination``, taken from whichever action holds it.

        Leaving the holder unbound in the same step is what keeps every scheme a draft produces
        valid, since one combination reaches one action within a category. An edit is held to the
        keys the table names, which is what lets every draft be written down and read back.

        Raises:
            KeyError: when the combination is built on a key the table names none of.
        """
        if not combination.is_writable:
            raise KeyError(f"The key {combination.key} carries no name a binding is written under")

        claimant = self.claimant(shortcut_id, combination)
        edits: Dict[ShortcutId, Optional[KeyCombination]] = {
            **self.edits,
            shortcut_id: combination,
        }
        if claimant is not None:
            edits[claimant] = None

        return replace(self, edits=edits)

    def clear(self, shortcut_id: ShortcutId) -> ShortcutDraft:
        """The draft with an action left unbound, its keys free for another action to take."""
        return replace(self, edits={**self.edits, shortcut_id: None})

    def reset(self) -> ShortcutDraft:
        """The draft with every action back on the keys the scheme ships."""
        return replace(self, edits={})

    def scheme(self) -> ShortcutScheme:
        """The scheme the draft describes, ready for the application to resolve its keys against.

        Raises:
            KeyError: when an edit names a key the key table holds none of.
        """
        return self.base.with_bindings(self.edits)

    def overrides(self) -> Dict[str, Optional[str]]:
        """The edits as a stored preference writes them, keyed by each action's name."""
        return {
            shortcut_id.value: None if combination is None else combination.display()
            for shortcut_id, combination in self.edits.items()
        }

    def _claimed(self, shortcut_id: ShortcutId) -> Tuple[KeyCombination, ...]:
        """Every combination an action answers to as the draft stands.

        An action the reader touched answers the one combination they gave it, while the rest answer
        the aliases the scheme ships beside their combination, which an assignment has to take too.
        """
        if shortcut_id not in self.edits:
            return self.base.shortcut(shortcut_id).combinations()

        combination = self.edits[shortcut_id]
        return () if combination is None else (combination,)
