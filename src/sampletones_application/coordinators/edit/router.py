from typing import Optional, Sequence

from sampletones_application.coordinators.edit.protocol import EditSurfaceProtocol


class EditRouter:
    """The single editing surface behind the menu bar's Edit menu.

    A surface is a grid that offers editing gestures on the cell it holds a cursor in. Each one
    states whether it owns those gestures at this moment, and the router asks the one that does to
    build its actions into the menu being built. Surfaces are mutually exclusive, since taking a
    cursor in one drops the cursor of the others, so at most one answers.

    It is stateless: the surface is resolved on each call, so the menu states the actions of
    whoever holds the cursor when it is opened, and needs no notice of cursors moving.

    The router itself draws nothing. It calls the surface, which builds its items into the
    container the menu bar has opened, the way :class:`PlaybackRouter` calls a source to play.
    """

    def __init__(self, *, surfaces: Sequence[EditSurfaceProtocol]) -> None:
        self._surfaces = tuple(surfaces)

    def build_menu_actions(self) -> bool:
        """Builds the focused surface's actions, reporting whether a surface stated any.

        Returns:
            bool: Whether a surface owned the editing gestures and built its actions.
        """
        surface = self._focused_surface()
        if surface is None:
            return False

        surface.build_edit_actions()
        return True

    def _focused_surface(self) -> Optional[EditSurfaceProtocol]:
        """The surface owning the editing gestures, or ``None`` while a reader edits elsewhere."""
        for surface in self._surfaces:
            if surface.owns_edit_actions():
                return surface

        return None
