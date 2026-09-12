from sampletones_application.utils.gui.keyboard.router import ActivePredicate, KeyRouter


def panel_scope_active(*, tab_active: ActivePredicate, router: KeyRouter, holds: bool) -> bool:
    """Whether a panel scope owns the next key.

    A panel answers while its tab is in front, while it holds the thing the keys act on, and
    while no field has the keyboard. What a panel holds differs — a cursor, a row picked out, an
    open audition — so each states its own and the rest of the rule is answered here.

    The tab is read at the moment of the press, since a cursor, a pick and an audition all outlive
    a move to another tab. A modal dialog claims keys above this priority in the router, which is
    what holds every panel off while one stands open.
    """
    return tab_active() and holds and not router.is_field_focused
