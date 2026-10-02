import multiprocessing
import operator
import shutil
from pathlib import Path
from typing import Dict, Final, FrozenSet, List, Tuple

import pytest

from sampletones_application.constants.output import OutputKind
from sampletones_application.tags.main import TAG_MAIN_CONVERTER_GROUP_INPUT, TAG_MAIN_CONVERTER_GROUP_ORDER
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction
from sampletones_shared.paths.user import RECONSTRUCTIONS_DIRECTORY
from tests.suite.screens.dearpygui.items import read_item
from tests.suite.screens.holds import ConversionHold
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds import Recording
from tests.suite.screens.steps.main import explorer_row, gather, give_each_its_own_channel, home_path
from tests.suite.screens.world import HomeFile, World, converting_world

SECONDS: Final[float] = 0.3
FREQUENCY: Final[float] = 220.0
RUN_TIMEOUT_SECONDS: Final[float] = 120.0
BASS: Final[str] = "bass.wav"
LEAD: Final[str] = "lead.wav"
DRUMS: Final[str] = "drums.wav"
ALBUM: Final[str] = "Album"
DISC: Final[str] = "Disc2"
ALBUM_TAKES: Final[Tuple[str, ...]] = ("one.wav", "two.wav")
DISC_TAKES: Final[Tuple[str, ...]] = ("three.wav",)
RECONSTRUCTION_SUFFIX: Final[str] = ".stn"
OTHER_RECONSTRUCTION: Final[str] = "other.stn"

CONVERT_NOTHING: Final[str] = "main.converter.label.convert_button"
CONVERT_ONE: Final[str] = "main.converter.template.convert_recording"
CONVERT_SEVERAL: Final[str] = "main.converter.template.convert_recordings"
MIX_SEVERAL: Final[str] = "main.converter.template.mix_recordings"
CANCEL_RUN: Final[str] = "main.converter.label.cancel_button"
RECONSTRUCT_FILE: Final[str] = "main.explorer.label.context_reconstruct_file"
RUN_FAILED: Final[str] = "main.converter.message.status_error"


def recording(path: Path) -> HomeFile:
    return Recording(destination=path, seconds=SECONDS, frequency=FREQUENCY)


def run_world() -> World:
    paths = [
        home_path(BASS),
        home_path(LEAD),
        home_path(DRUMS),
        *(home_path(ALBUM) / name for name in ALBUM_TAKES),
        *(home_path(ALBUM) / DISC / name for name in DISC_TAKES),
    ]
    return converting_world(tuple(recording(path) for path in paths))


@pytest.fixture
def world() -> World:
    return run_world()


def run_to_its_end(screen: Screen) -> None:
    """Presses the button naming the run and waits for the question its end asks, which it closes."""
    converter = screen.main.converter
    converter.press_action()
    wait_for_the_end(screen)


def wait_for_the_end(screen: Screen) -> None:
    converter = screen.main.converter
    screen.bridge.expect(converter.end_prompt.is_shown, bool, description="the run's end", timeout=RUN_TIMEOUT_SECONDS)
    converter.end_prompt.cancel()
    screen.expect(converter.end_prompt.is_shown, operator.not_, description="the end closed")


def written(destination: Path) -> List[Path]:
    return sorted(destination.rglob(f"*{RECONSTRUCTION_SUFFIX}"))


def converted_channels(path: Path) -> FrozenSet[ChannelName]:
    """The channels a written reconstruction approximates, read off the file."""
    return frozenset(Reconstruction.load(path).approximations)


def modified(paths: List[Path]) -> Dict[Path, int]:
    return {path: path.stat().st_mtime_ns for path in paths}


class TestTheButtonNamesTheRun:
    """The button under the list names the run each time it changes."""

    def test_one_several_a_mix_and_none(self, screen: Screen) -> None:
        main = screen.main
        converter = main.converter

        def one(screen: Screen) -> None:
            gather(screen, home_path(BASS))

            assert converter.action() == screen.words(CONVERT_ONE).format(name=home_path(BASS).stem)

        def several(screen: Screen) -> None:
            gather(screen, home_path(LEAD))

            assert converter.action() == screen.words(CONVERT_SEVERAL).format(count=2)

        def a_mix(screen: Screen) -> None:
            main.choose_output(OutputKind.MIXED)

            screen.expect(converter.action, screen.words(MIX_SEVERAL).format(count=2).__eq__, description="a mix named")

        def none(screen: Screen) -> None:
            converter.list.remove(home_path(BASS))
            converter.list.remove(home_path(LEAD))

            screen.expect(converter.action, screen.words(CONVERT_NOTHING).__eq__, description="nothing to name")

        screen.scenario(one, several, a_mix, none).run()


class TestTheLinesOfTheCard:
    """Order joins only from a mix's second recording, Destination always stands, and Input only while a run reads."""

    def test_order_and_destination(self, screen: Screen) -> None:
        main = screen.main
        converter = main.converter

        def order_waits_for_a_second_recording_in_a_mix(screen: Screen) -> None:
            assert converter.destination()
            gather(screen, home_path(BASS))
            main.choose_output(OutputKind.MIXED)
            screen.expect(main.output, OutputKind.MIXED.__eq__, description="a mix")

            assert not screen.bridge.ask(lambda: read_item(TAG_MAIN_CONVERTER_GROUP_ORDER)).shown

        def the_second_brings_it(screen: Screen) -> None:
            gather(screen, home_path(LEAD))

            screen.expect(
                lambda: screen.bridge.ask(lambda: read_item(TAG_MAIN_CONVERTER_GROUP_ORDER)).shown,
                bool,
                description="Order joining",
            )
            assert converter.destination()

        screen.scenario(order_waits_for_a_second_recording_in_a_mix, the_second_brings_it).run()

    def test_input_stands_while_a_run_reads(self, screen: Screen, conversion_hold: ConversionHold) -> None:
        converter = screen.main.converter

        def no_input_before_the_run(screen: Screen) -> None:
            gather(screen, home_path(BASS))

            assert not screen.bridge.ask(lambda: read_item(TAG_MAIN_CONVERTER_GROUP_INPUT)).shown

        def input_while_it_reads(screen: Screen) -> None:
            converter.press_action()

            screen.bridge.expect(
                lambda: screen.bridge.ask(lambda: read_item(TAG_MAIN_CONVERTER_GROUP_INPUT)).shown,
                bool,
                description="the Input line",
                timeout=RUN_TIMEOUT_SECONDS,
            )

        def no_input_after_it(screen: Screen) -> None:
            conversion_hold.release()
            wait_for_the_end(screen)

            assert not screen.bridge.ask(lambda: read_item(TAG_MAIN_CONVERTER_GROUP_INPUT)).shown

        screen.scenario(no_input_before_the_run, input_while_it_reads, no_input_after_it).run()


def written_as(path: Path) -> Path:
    """The one reconstruction a run wrote for the recording at ``path``, wherever below the folder it went."""
    found = [file for file in written(RECONSTRUCTIONS_DIRECTORY) if file.stem == path.stem]
    assert len(found) == 1, found
    return found[0]


class TestWhereARunWrites:
    """A run writes each recording with the channels its row gave, where the Destination line says."""

    def channels(self) -> Dict[Path, ChannelName]:
        return {home_path(BASS): ChannelName.TRIANGLE, home_path(LEAD): ChannelName.PULSE1}

    def test_each_recording_carries_the_channels_its_row_gave(self, screen: Screen) -> None:
        gather(screen, home_path(BASS), home_path(LEAD))
        give_each_its_own_channel(screen, self.channels())

        run_to_its_end(screen)

        for path, channel in self.channels().items():
            assert converted_channels(written_as(path)) == {channel}

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: Destination names no folder a run of differing channels writes into",
    )
    def test_the_destination_line_names_the_folder_the_run_writes_into(self, screen: Screen) -> None:
        converter = screen.main.converter
        gather(screen, home_path(BASS), home_path(LEAD))
        give_each_its_own_channel(screen, self.channels())
        destination = Path(converter.destination())

        run_to_its_end(screen)

        assert all(written_as(path).parent == destination for path in self.channels())


class TestAFolderConverts:
    """A listed folder converts into a tree mirroring it; a rerun leaves what was written and makes the rest."""

    def test_a_mirrored_tree_then_only_what_is_missing(self, screen: Screen) -> None:
        converter = screen.main.converter
        folder = home_path(ALBUM)
        expected = [Path(name).with_suffix(RECONSTRUCTION_SUFFIX) for name in ALBUM_TAKES] + [
            (Path(DISC) / name).with_suffix(RECONSTRUCTION_SUFFIX) for name in DISC_TAKES
        ]
        kept: List[Dict[Path, int]] = []
        destinations: List[Path] = []

        def convert_the_folder(screen: Screen) -> None:
            gather(screen, folder)
            destinations.append(Path(converter.destination()))

            run_to_its_end(screen)

            files = written(destinations[0])
            assert len(files) == len(expected)
            assert all(any(file.as_posix().endswith(part.as_posix()) for file in files) for part in expected)

        def rerun_makes_only_what_is_missing(screen: Screen) -> None:
            files = written(destinations[0])
            missing, *standing = files
            missing.unlink()
            kept.append(modified(standing))

            run_to_its_end(screen)

            assert written(destinations[0]) == files
            assert modified(standing) == kept[0]

        screen.scenario(convert_the_folder, rerun_makes_only_what_is_missing).run()


class TestReplacingWhatARunWrote:
    """Recordings gathered by name and converted before ask first, and Convert anyway replaces exactly them."""

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
    """Reconstruct file with a list gathered asks first: Keep the list converts none, Replace it converts the file."""

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


class TestAHeldRun:
    """A run shows its progress, Continue lets it run on, and Stop ends it with nothing written and no worker left."""

    @pytest.mark.usefixtures("conversion_hold")
    def test_progress_continue_and_stop(self, screen: Screen) -> None:
        converter = screen.main.converter
        prompt = converter.cancel_prompt
        destinations: List[Path] = []

        def start_it(screen: Screen) -> None:
            gather(screen, home_path(BASS))
            destinations.append(Path(converter.destination()))

            converter.press_action()

            screen.bridge.expect(
                converter.progress, lambda progress: progress > 0, description="progress", timeout=RUN_TIMEOUT_SECONDS
            )
            assert converter.action() == screen.words(CANCEL_RUN)

        def continue_lets_it_run(screen: Screen) -> None:
            converter.press_action()
            screen.expect(prompt.is_shown, bool, description="the question about stopping")

            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            assert converter.action() == screen.words(CANCEL_RUN)

        def stop_ends_it(screen: Screen) -> None:
            converter.press_action()
            screen.expect(prompt.is_shown, bool, description="the question again")

            prompt.confirm()

            screen.bridge.expect(
                converter.action,
                screen.words(CONVERT_ONE).format(name=home_path(BASS).stem).__eq__,
                description="the run over",
                timeout=RUN_TIMEOUT_SECONDS,
            )
            screen.bridge.expect(
                lambda: len(multiprocessing.active_children()),
                operator.not_,
                description="no worker left",
                timeout=RUN_TIMEOUT_SECONDS,
            )
            assert written(destinations[0]) == []

        screen.scenario(start_it, continue_lets_it_run, stop_ends_it).run()


class TestARecordingGoneBeforeTheRun:
    """A recording deleted after it was gathered is reported in words naming it when the run reaches it."""

    def test_the_run_says_what_went_wrong(self, screen: Screen) -> None:
        converter = screen.main.converter
        notice = screen.error_notice
        gather(screen, home_path(BASS))
        home_path(BASS).unlink()

        converter.press_action()

        screen.bridge.expect(notice.is_shown, bool, description="the failure reported", timeout=RUN_TIMEOUT_SECONDS)
        words = notice.words()
        screen.claim_error(home_path(BASS).name)
        notice.dismiss()
        screen.expect(notice.is_shown, operator.not_, description="the report dismissed")
        assert words.startswith(screen.words(RUN_FAILED))
        assert home_path(BASS).name in words
        assert converter.status() == screen.words(RUN_FAILED)
