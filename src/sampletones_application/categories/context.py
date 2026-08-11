from sampletones_application.categories.elements.global_ import ContextElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager


def context_label(
    language_manager: LanguageManager,
    element: ContextElements,
) -> str:
    """Resolves a context-action label, the words every menu offering that action prints.

    Cut, Copy and Play name one gesture wherever they are offered, so the cell menus of the
    sequencer grids, the file trees and the menu bar read them from one entry. A reader then
    meets the same word for the same action, and a translation reaches all of them at once.
    """
    return language_manager[
        Page.GLOBAL,
        Panel.CONTEXT,
        TextType.LABEL,
        element,
    ]
