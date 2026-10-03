import operator
from functools import partial
from typing import Final, List

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectrumMethod
from tests.screens.main.library.steps import library_world
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.instructions import library_path, library_row
from tests.suite.screens.vocabulary.libraries import LIBRARY_LOADED
from tests.suite.screens.worlds.home import World, one_worker_config

QUICK_SAMPLE_RATE: Final[int] = 11025
GENERATION_TIMEOUT_SECONDS: Final[float] = 300.0
LIBRARY_MISSING: Final[str] = "instructions.library.template.library_not_exists_template"
GENERATE: Final[str] = "instructions.library.label.generate_library_button"
REGENERATE: Final[str] = "instructions.library.label.regenerate_library_button"
GENERATION_CANCELED: Final[str] = "instructions.library.message.status_generation_canceled"


def quick_config() -> Config:
    """Settings whose library generates in seconds: a low sample rate, measured by the plain spectrum."""
    config = one_worker_config()
    library = config.library.model_copy(
        update={"sample_rate": QUICK_SAMPLE_RATE, "spectrum_method": SpectrumMethod.FFT}
    )
    return config.model_copy(update={"library": library})


class TestGeneratingALibrary:
    """A configuration with no library generates one, which the tree lists and the status reads as loaded."""

    @pytest.fixture
    def world(self) -> World:
        """A home holding no library for the quick settings."""
        return library_world(quick_config(), built=False)

    def test_generate_lists_it_loaded_and_offers_regenerate(self, screen: Screen) -> None:
        """Generate lists the library, the status reads it loaded, and the button then offers Regenerate."""
        library = screen.instructions.library
        path = library_path(quick_config())

        def nothing_to_list(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.INSTRUCTIONS)

            screen.expect(library.generate_label, screen.words(GENERATE).__eq__, description="Generate offered")
            assert library.row(path.name) is None

        def generate(screen: Screen) -> None:
            library.generate()

            row = screen.bridge.expect(
                partial(library.row, path.name),
                lambda found: found is not None,
                description="the library listed",
                timeout=GENERATION_TIMEOUT_SECONDS,
            )
            assert row is not None
            name = library.tree.label(row)
            screen.bridge.expect(
                library.status,
                screen.words(LIBRARY_LOADED).format(name).__eq__,
                description="the library loaded",
                timeout=GENERATION_TIMEOUT_SECONDS,
            )
            assert library.generate_label() == screen.words(REGENERATE)
            assert path.exists()

        screen.scenario(nothing_to_list, generate).run()

    def test_cancelling_a_generation_leaves_no_library(self, screen: Screen) -> None:
        """Canceling a generation reports it; Generate is offered again and the library has no file or row."""
        library = screen.instructions.library
        path = library_path(quick_config())

        def start_and_cancel(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.INSTRUCTIONS)
            library.generate()

            library.cancel_generation()

            screen.bridge.expect(
                library.notice.is_shown, bool, description="the cancel reported", timeout=GENERATION_TIMEOUT_SECONDS
            )
            assert library.notice.words() == screen.words(GENERATION_CANCELED)
            library.notice.dismiss()
            screen.expect(library.notice.is_shown, operator.not_, description="the report dismissed")

        def nothing_was_written(screen: Screen) -> None:
            screen.expect(library.generate_label, screen.words(GENERATE).__eq__, description="Generate offered again")

            assert not path.exists()
            assert library.row(path.name) is None
            assert library.status().endswith(screen.words(LIBRARY_MISSING).format(""))

        screen.scenario(start_and_cancel, nothing_was_written).run()


class TestRegeneratingALibrary:
    """Regenerate asks first, and Cancel keeps the library as it stands.

    The built library is listed and Regenerate pressed. Cancel on the question keeps the file's bytes,
    and the next press asks again.
    """

    @pytest.fixture
    def world(self) -> World:
        """A home holding a built library."""
        return library_world(one_worker_config(), built=True)

    def test_cancel_keeps_it_and_the_next_press_asks_again(self, screen: Screen) -> None:
        library = screen.instructions.library
        prompt = library.regenerate_prompt
        path = library_path(one_worker_config())
        kept: List[bytes] = []

        def regenerate_asks(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.INSTRUCTIONS)
            library_row(screen, path)
            kept.append(path.read_bytes())

            library.generate()

            screen.expect(prompt.is_shown, bool, description="the question")

        def cancel_keeps_it(screen: Screen) -> None:
            prompt.cancel()
            screen.expect(prompt.is_shown, operator.not_, description="the question gone")

            library.generate()

            screen.expect(prompt.is_shown, bool, description="the question asked again")
            prompt.cancel()
            screen.expect(prompt.is_shown, operator.not_, description="the question gone again")
            assert path.read_bytes() == kept[0]

        screen.scenario(regenerate_asks, cancel_keeps_it).run()
