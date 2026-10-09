import operator
import shutil
from pathlib import Path
from typing import Dict, Final, List

from automation.screen import Screen
from automation.steps.main import explorer_row, gather, home_path
from sampletones_application.constants.output import OutputKind
from sampletones_shared.paths.user import RECONSTRUCTIONS_DIRECTORY
from tests.screens.main.run.constants import ALBUM, BASS, DRUMS, LEAD, RECONSTRUCTION_SUFFIX
from tests.screens.main.run.steps import modified, run_to_its_end, wait_for_the_end, written

OTHER_RECONSTRUCTION: Final[str] = "other.stn"
RECONSTRUCT_FILE: Final[str] = "main.explorer.label.context_reconstruct_file"
RECONSTRUCT_DIRECTORY: Final[str] = "main.explorer.label.context_reconstruct_directory"


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


class TestReconstructingLists:
    """Reconstruct lists what it names to convert one apiece and leaves the run to the reader; over a mix it
    asks first.

    Two recordings are gathered and Reconstruct file chosen on a third: it joins the list and nothing is
    written. The list then turns into a mix, and Reconstruct directory on the Album asks about it: Keep the
    mix leaves it standing, and Replace it lists the Album alone, one reconstruction per recording, with
    nothing written.
    """

    def test_a_list_takes_it_and_a_mix_is_asked_about(self, screen: Screen) -> None:
        main = screen.main
        converter = main.converter
        prompt = converter.replace_prompt
        listed = [home_path(BASS), home_path(LEAD), home_path(DRUMS)]
        standing: List[List[Path]] = []

        def choose_from_the_browser(screen: Screen, path: Path, entry: str) -> None:
            screen.explorer.right_click(explorer_row(screen, path))
            screen.expect(screen.context_menu.is_shown, bool, description="the browser's menu")
            screen.context_menu.choose(screen.words(entry))

        def a_list_takes_the_file(screen: Screen) -> None:
            standing.append(written(RECONSTRUCTIONS_DIRECTORY))
            gather(screen, home_path(BASS), home_path(LEAD))

            choose_from_the_browser(screen, home_path(DRUMS), RECONSTRUCT_FILE)

            screen.expect(
                lambda: converter.list.has_row(home_path(DRUMS)), bool, description="the third recording listed"
            )
            assert converter.list.rows() == [converter.list.row(path) for path in listed]
            assert not prompt.is_shown()
            assert not converter.run_shown()
            assert written(RECONSTRUCTIONS_DIRECTORY) == standing[0]

        def keep_the_mix(screen: Screen) -> None:
            main.choose_output(OutputKind.MIXED)
            screen.expect(main.output, OutputKind.MIXED.__eq__, description="a mix")

            choose_from_the_browser(screen, home_path(ALBUM), RECONSTRUCT_DIRECTORY)
            screen.expect(prompt.is_shown, bool, description="the question about the mix")
            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            assert main.output() is OutputKind.MIXED
            assert all(converter.list.has_row(path) for path in listed)

        def replace_it(screen: Screen) -> None:
            choose_from_the_browser(screen, home_path(ALBUM), RECONSTRUCT_DIRECTORY)
            screen.expect(prompt.is_shown, bool, description="the question again")

            prompt.confirm()

            screen.expect(lambda: converter.list.has_row(home_path(ALBUM)), bool, description="the Album listed")
            assert main.output() is OutputKind.PER_RECORDING
            assert converter.list.rows() == [converter.list.row(home_path(ALBUM))]
            assert not converter.run_shown()
            assert written(RECONSTRUCTIONS_DIRECTORY) == standing[0]

        screen.scenario(a_list_takes_the_file, keep_the_mix, replace_it).run()
