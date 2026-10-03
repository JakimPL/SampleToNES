from tests.screens.application.closing.constants import CONVERSION_RUNNING
from tests.suite.screens.screen import Screen
from tests.suite.screens.views.prompts import Prompt


def conversion_question(screen: Screen) -> Prompt:
    """The prompt Exit shows while a conversion runs, in the window the reconstruction's question uses."""
    return screen.reconstructions.unsaved_prompt


def asks_about_the_conversion(screen: Screen) -> bool:
    """Tells whether the shared prompt is shown with the words about a conversion in progress."""
    prompt = conversion_question(screen)
    return prompt.is_shown() and screen.words(CONVERSION_RUNNING) in prompt.words()
