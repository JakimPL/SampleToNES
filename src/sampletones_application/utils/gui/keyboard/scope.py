from sampletones_application.utils.gui.keyboard.router import ActivePredicate, KeyRouter


def panel_scope_active(
    *,
    tab_active: ActivePredicate,
    router: KeyRouter,
    holds: bool,
    card_open: bool,
) -> bool:
    """Whether a panel scope owns the next key.

    A panel answers while its tab is in front, while its card stands open, while it holds the
    thing the keys act on, and while no field has the keyboard. What a panel holds differs — a
    cursor, a row picked out, an open audition — so each states its own and the rest of the rule
    is answered here.

    The tab and the card are read at the moment of the press, since a cursor, a pick and an
    audition outlive both a move to another tab and a card put away: the reader comes back to
    where they left off, and what rests meanwhile is the panel's claim on the keyboard. A modal
    dialog claims keys above this priority in the router, which is what holds every panel off
    while one stands open.
    """
    return tab_active() and card_open and holds and not router.is_field_focused
