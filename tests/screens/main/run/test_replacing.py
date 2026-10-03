import operator
import shutil
from pathlib import Path
from typing import Dict, Final, List

from tests.screens.main.run.constants import BASS, DRUMS, LEAD, RECONSTRUCTION_SUFFIX
from tests.screens.main.run.steps import modified, run_to_its_end, wait_for_the_end, written
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.main import explorer_row, gather, home_path

OTHER_RECONSTRUCTION: Final[str] = "other.stn"
RECONSTRUCT_FILE: Final[str] = "main.explorer.label.context_reconstruct_file"


class TestReplacingWhatARunWrote:
    """Recordings gathered by name and converted before ask first, and Convert anyway replaces exactly
    them.

    Three recordings are converted and a fourth reconstruction is copied beside them. Running again asks
    about replacing; Cancel keeps every file as it was, and Convert anyway rewrites the three while the
    fourth keeps its modification time.
    """

    def test_cancel_writes_nothing_and_convert_anyway_replaces_those_alone(self, screen: Screen) -> None:
        converter = screen.main.converter
        prompt = converter.overwrite_prompt
        paths = [home_path(BASS), home_path(LEAD), home_path(DRUMS)]
        state: Dict[str, Dict[Path, int]] = {}
        destinations: List[Path] = []

        def convert_three_and_set_another_beside_them(screen: Screen) -> None:
            gather(screen, *paths)
            destinations.append(Path(converter.destination()))
            run_to_its_end(screen)
            first = written(destinations[0])[0]
            shutil.copyfile(first, destinations[0] / OTHER_RECONSTRUCTION)
            state["before"] = modified(written(destinations[0]))

        def cancel_writes_nothing(screen: Screen) -> None:
            converter.press_action()
            screen.expect(prompt.is_shown, bool, description="the question about replacing")

            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            assert not converter.run_shown()
            assert modified(written(destinations[0])) == state["before"]

        def convert_anyway_replaces_those_alone(screen: Screen) -> None:
            converter.press_action()
            screen.expect(prompt.is_shown, bool, description="the question again")

            prompt.confirm()

            wait_for_the_end(screen)
            after = modified(written(destinations[0]))
            other = destinations[0] / OTHER_RECONSTRUCTION
            assert after[other] == state["before"][other]
            assert all(
                after[file] != state["before"][file]
                for file in (destinations[0] / f"{path.stem}{RECONSTRUCTION_SUFFIX}" for path in paths)
            )

        screen.scenario(
            convert_three_and_set_another_beside_them,
            cancel_writes_nothing,
            convert_anyway_replaces_those_alone,
        ).run()


class TestReconstructingAFileWhileAListStands:
    """Reconstruct file with a list gathered asks first: Keep the list converts nothing, Replace it
    converts the file.

    Two recordings are gathered and Reconstruct file chosen from the explorer's menu on a third.
    Cancel keeps the list and writes nothing. Choosing it again and confirming runs the third alone.
    """

    def test_keep_the_list_then_replace_it(self, screen: Screen) -> None:
        converter = screen.main.converter
        prompt = converter.replace_prompt
        destinations: List[Path] = []

        def ask_from_the_browser(screen: Screen) -> None:
            gather(screen, home_path(BASS), home_path(LEAD))
            destinations.append(Path(converter.destination()))
            screen.explorer.right_click(explorer_row(screen, home_path(DRUMS)))
            screen.expect(screen.context_menu.is_shown, bool, description="the recording's menu")
            screen.context_menu.choose(screen.words(RECONSTRUCT_FILE))

            screen.expect(prompt.is_shown, bool, description="the question about the list")

        def keep_the_list(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            assert not converter.run_shown()
            assert converter.list.rows() == [converter.list.row(home_path(BASS)), converter.list.row(home_path(LEAD))]
            assert written(destinations[0]) == []

        def replace_it(screen: Screen) -> None:
            screen.explorer.right_click(explorer_row(screen, home_path(DRUMS)))
            screen.expect(screen.context_menu.is_shown, bool, description="the menu again")
            screen.context_menu.choose(screen.words(RECONSTRUCT_FILE))
            screen.expect(prompt.is_shown, bool, description="the question again")

            prompt.confirm()

            wait_for_the_end(screen)
            assert [file.stem for file in written(destinations[0])] == [home_path(DRUMS).stem]

        screen.scenario(ask_from_the_browser, keep_the_list, replace_it).run()
