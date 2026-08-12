from typing import Dict, Final

from sampletones_application.categories.elements.global_ import ContextElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_core.constants.enums import GeneratorName

CHANNEL_ELEMENTS: Final[Dict[GeneratorName, ContextElements]] = {
    GeneratorName.PULSE1: ContextElements.PULSE_1,
    GeneratorName.PULSE2: ContextElements.PULSE_2,
    GeneratorName.TRIANGLE: ContextElements.TRIANGLE,
    GeneratorName.NOISE: ContextElements.NOISE,
}


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


def channel_label(
    language_manager: LanguageManager,
    generator: GeneratorName,
) -> str:
    """Resolves an NES channel's name, the words every display naming a channel prints.

    The playback menu's mix, the samples menu's byte figures and anything else addressing a
    channel read it from one entry, so a reader meets the same name for the same channel.
    """
    return context_label(language_manager, CHANNEL_ELEMENTS[generator])
