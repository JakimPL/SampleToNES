from typing import Dict, Final

from sampletones_application.categories.elements.global_ import ContextElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_core.constants.enums import ChannelName, GeneratorName

CHANNEL_ELEMENTS: Final[Dict[ChannelName, ContextElements]] = {
    ChannelName.PULSE1: ContextElements.PULSE_1,
    ChannelName.PULSE2: ContextElements.PULSE_2,
    ChannelName.TRIANGLE: ContextElements.TRIANGLE,
    ChannelName.NOISE: ContextElements.NOISE,
}

GENERATOR_ELEMENTS: Final[Dict[GeneratorName, ContextElements]] = {
    GeneratorName.PULSE: ContextElements.PULSE,
    GeneratorName.TRIANGLE: ContextElements.TRIANGLE,
    GeneratorName.NOISE: ContextElements.NOISE,
}


def context_text(
    language_manager: LanguageManager,
    text_type: TextType,
    element: ContextElements,
) -> str:
    """Resolves one reading of a context element: its label, the template it fills or its tooltip.

    A context element is stated once and read in several voices — the byte figures name a size
    with a label, print it through a template and explain it in a tooltip — so every voice of an
    element comes from the same place.

    Args:
        language_manager: The catalog the words are read from.
        text_type: The voice the element is read in.
        element: The context element being read.

    Returns:
        str: The words the catalog holds for that element in that voice.
    """
    return language_manager[
        Page.GLOBAL,
        Panel.CONTEXT,
        text_type,
        element,
    ]


def context_label(
    language_manager: LanguageManager,
    element: ContextElements,
) -> str:
    """Resolves a context-action label, the words every menu offering that action prints.

    Cut, Copy and Play name one gesture wherever they are offered, so the cell menus of the
    sequencer grids, the file trees and the menu bar read them from one entry. A reader then
    meets the same word for the same action, and a translation reaches all of them at once.
    """
    return context_text(language_manager, TextType.LABEL, element)


def channel_label(
    language_manager: LanguageManager,
    channel: ChannelName,
) -> str:
    """Resolves an NES channel's name, the words every display naming a channel prints.

    The playback menu's mix, the samples menu's byte figures and anything else addressing a
    channel read it from one entry, so a reader meets the same name for the same channel.
    """
    return context_label(language_manager, CHANNEL_ELEMENTS[channel])


def generator_label(
    language_manager: LanguageManager,
    generator_name: GeneratorName,
) -> str:
    """Resolves a generator's name, the words every display naming a generator prints.

    A generator names the sound itself rather than one of the channels playing it, so the two
    pulse channels share the one name. Reading it from a single entry keeps a generator called
    the same thing wherever it is offered.
    """
    return context_label(language_manager, GENERATOR_ELEMENTS[generator_name])
