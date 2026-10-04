from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Mapping, Optional, Tuple

from sampletones_application.utils.gui.keyboard.combination import KeyCombination, display_combinations
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.scheme import ShortcutScheme

Keys = Tuple[KeyCombination, ...]


@dataclass(frozen=True)
class ShortcutDraft:
    """The keys a reader is giving the actions, held apart from the ones the application runs under.

    An editor works on a draft and hands a scheme over once, which leaves the keys in force steady
    while Escape, Tab and Enter are themselves being rebound. A draft is kept as the actions the
    reader moved off the keys the scheme ships and the whole list of keys each answers, main key
    first, since an override replaces a whole binding: every other action answers the scheme the
    build ships, and the moved entries are what a session stores. An empty list leaves an action
    unbound.
    """

    base: ShortcutScheme
    stored: Dict[ShortcutId, Keys]
    edits: Dict[ShortcutId, Keys]

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
            overrides: The keys each rebound action answers to, joined by commas and keyed by the
                action's name.

        Returns:
            ShortcutDraft: The draft holding what the session stores and that alone.
        """
        preferred = base.with_overrides(overrides)
        stored: Dict[ShortcutId, Keys] = {
            shortcut_id: preferred.shortcut(shortcut_id).combinations()
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

    def keys(self, shortcut_id: ShortcutId) -> Keys:
        """Every key an action answers to as the draft stands, main key first, and none while unbound."""
        if shortcut_id in self.edits:
            return self.edits[shortcut_id]

        return self.base.shortcut(shortcut_id).combinations()

    def keys_led_by(
        self,
        shortcut_id: ShortcutId,
        combination: KeyCombination,
    ) -> Keys:
        """The keys an action answers once ``combination`` becomes its main key.

        A pressed key leads the list and the action keeps the keys it had after it, so pressing one
        of its own keys moves that key to the front.
        """
        return (
            combination,
            *(key for key in self.keys(shortcut_id) if key != combination),
        )

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

            if combination in self.keys(other):
                return other

        return None

    def holders(
        self,
        shortcut_id: ShortcutId,
        combinations: Keys,
    ) -> Dict[KeyCombination, ShortcutId]:
        """Each of ``combinations`` another action of the category holds, with the action holding it."""
        holders: Dict[KeyCombination, ShortcutId] = {}
        for combination in combinations:
            claimant = self.claimant(shortcut_id, combination)
            if claimant is not None:
                holders[combination] = claimant

        return holders

    def assign(
        self,
        shortcut_id: ShortcutId,
        combinations: Keys,
    ) -> ShortcutDraft:
        """The draft with an action answering exactly ``combinations``, taken from whichever action
        holds them.

        A holder gives up the keys taken and keeps the rest, its next key becoming its main key,
        which keeps every scheme a draft produces valid, since one combination reaches one action
        within a category. An edit is held to the keys the table names, which is what lets every
        draft be written down and read back. An action left on the keys the scheme ships records no
        edit, so an assignment that changes nothing leaves the draft as it was.

        Args:
            shortcut_id: The action given the keys.
            combinations: Its keys, main key first; a repeated key counts once, and an empty list
                leaves it unbound.

        Raises:
            KeyError: when a combination is built on a key the table names none of.
        """
        given = tuple(dict.fromkeys(combinations))
        for combination in given:
            if not combination.is_writable:
                raise KeyError(f"The key {combination.key} carries no name a binding is written under")

        edits: Dict[ShortcutId, Keys] = dict(self.edits)
        self._record(edits, shortcut_id, given)
        for holder in dict.fromkeys(self.holders(shortcut_id, given).values()):
            self._record(edits, holder, tuple(key for key in self.keys(holder) if key not in given))

        return replace(self, edits=edits)

    def _record(
        self,
        edits: Dict[ShortcutId, Keys],
        shortcut_id: ShortcutId,
        keys: Keys,
    ) -> None:
        """Writes ``keys`` into ``edits`` as the keys an action answers, an action on the keys the
        scheme ships recording no edit."""
        if keys == self.base.shortcut(shortcut_id).combinations():
            edits.pop(shortcut_id, None)
            return

        edits[shortcut_id] = keys

    def clear(self, shortcut_id: ShortcutId) -> ShortcutDraft:
        """The draft with an action left unbound, every key it held free for another action to take."""
        return self.assign(shortcut_id, ())

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
        """The edits as a stored preference writes them: each action's keys joined by commas, keyed by
        the action's name, and ``None`` for an action left unbound.
        """
        return {
            shortcut_id.value: display_combinations(keys) if keys else None for shortcut_id, keys in self.edits.items()
        }
