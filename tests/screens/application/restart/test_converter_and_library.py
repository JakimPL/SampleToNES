from pathlib import Path
from typing import Final

import pytest

from automation.boundaries.dialogs import DialogKind
from automation.screen import Screen
from automation.worlds.home import World, screen_filling_state
from automation.written import written_application_config, written_config
from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.application.converter import ConverterConfig
from sampletones_application.constants.output import OutputKind
from sampletones_core.configs import Config
from sampletones_core.constants.enums import DEFAULT_CHANNELS
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.screens.application.restart.constants import RECORDINGS_FOLDER
from tests.screens.application.restart.steps import home_folder, leave, recording_in, state_with_advanced

LIBRARIES_FOLDER: Final[str] = "Libraries"
CHOSEN_CHANNELS_AT_ONCE: Final[int] = 2
SEEDED_CHANNELS_AT_ONCE: Final[int] = 3


def converter_config(output: OutputKind, channels_at_once: int) -> ConverterConfig:
    """A converter setting for ``output`` that allows ``channels_at_once`` channels for each step."""
    settings = StemSettings.covering(list(DEFAULT_CHANNELS)).model_copy(update={"channel_cap": channels_at_once})
    return ConverterConfig(output=output, settings=settings)


class TestTheConverterSettingsAcrossARestart:
    """The converter's output and its channels at once are written as the application leaves, and stand at the
    next start.

    The home seeds the mixed output and three channels at once. The scenario checks both, chooses per-
    recording output and two channels, and expects Exit to write the chosen values.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds a session and settings with the mixed output and three channels at once."""
        return World(
            state=screen_filling_state(),
            application_config=ApplicationConfig(
                converter=converter_config(OutputKind.MIXED, SEEDED_CHANNELS_AT_ONCE),
            ),
            config=None,
            files=(),
        )

    def test_a_home_holding_them_shows_them_and_leaving_writes_the_next(self, screen: Screen) -> None:
        """The seeded values show at start and the chosen values are written at exit."""
        main = screen.main

        def shows_the_seeded_ones(screen: Screen) -> None:
            screen.expect(main.output, OutputKind.MIXED.__eq__, description="the output the settings name")
            assert main.lit_channels_at_once() == SEEDED_CHANNELS_AT_ONCE

        def changes_them(screen: Screen) -> None:
            main.choose_output(OutputKind.PER_RECORDING)
            main.choose_channels_at_once(CHOSEN_CHANNELS_AT_ONCE)

            screen.expect(main.lit_channels_at_once, CHOSEN_CHANNELS_AT_ONCE.__eq__, description="the step lit")
            assert main.output() is OutputKind.PER_RECORDING

        def leaving_writes_them(screen: Screen) -> None:
            leave(screen)

            converter = written_application_config().converter
            assert converter.output is OutputKind.PER_RECORDING
            assert converter.settings.channel_cap == CHOSEN_CHANNELS_AT_ONCE

        screen.scenario(shows_the_seeded_ones, changes_them, leaving_writes_them).run()


class TestTheLibraryFolderAcrossARestart:
    """The library folder Advanced settings points at is written as the application leaves, and named at the
    next start.

    The home seeds one folder as the library folder. The scenario checks it is named, chooses another
    folder through the directory dialog, and expects Exit to write the chosen folder.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds Advanced settings shown, settings naming the Libraries folder, and recordings in two
        folders.
        """
        config = Config()
        general = config.general.model_copy(update={"library_directory": str(home_folder(LIBRARIES_FOLDER))})
        return World(
            state=state_with_advanced(True),
            application_config=None,
            config=config.model_copy(update={"general": general}),
            files=(recording_in(LIBRARIES_FOLDER), recording_in(RECORDINGS_FOLDER)),
        )

    def test_a_home_holding_it_names_it_and_leaving_writes_the_next(self, screen: Screen) -> None:
        """The seeded folder shows at start and the chosen folder is written at exit."""
        main = screen.main
        chosen = home_folder(RECORDINGS_FOLDER)

        def names_the_seeded_one(screen: Screen) -> None:
            screen.expect(
                main.library_directory,
                str(home_folder(LIBRARIES_FOLDER)).__eq__,
                description="the library folder the settings name",
            )

        def points_at_another(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.DIRECTORY, chosen)

            main.choose_library_directory()

            screen.expect(main.library_directory, str(chosen).__eq__, description="the chosen folder named")

        def leaving_writes_it(screen: Screen) -> None:
            leave(screen)

            assert Path(written_config().general.library_directory) == chosen

        screen.scenario(names_the_seeded_one, points_at_another, leaving_writes_it).run()
