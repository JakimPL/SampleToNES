from pathlib import Path
from typing import List, Tuple

import pytest

from sampletones_application.logic.main.sources import scan as scan_module
from sampletones_application.logic.main.sources.scan import REPORT_EVERY, FolderScan
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from tests.suite.base import BaseTestSuite


@pytest.fixture(name="scan")
def scan_fixture() -> FolderScan:
    return FolderScan()


def tree(root: Path, count: int, *, deep: int = 0) -> Path:
    """A folder holding ``count`` recordings, and ``deep`` more in a folder below it."""
    root.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        (root / f"take_{index:04d}.wav").touch()

    if deep:
        tree(root / "below", deep)

    return root


def read(scan: FolderScan, root: Path) -> List[Tuple[Path, Tuple[Path, ...]]]:
    """Reads the folder and waits for the walk, reporting what the answer was handed."""
    answered: List[Tuple[Path, Tuple[Path, ...]]] = []
    scan.start(root, lambda found_root, found: answered.append((found_root, found)))
    SingleThreadExecutor.join_all()
    return answered


class TestWhatAWalkFinds(BaseTestSuite):
    """The walk goes as deep as the folder does and hands what it found to whoever asked."""

    def test_every_recording_below_the_folder(self, scan: FolderScan, tmp_path: Path) -> None:
        root = tree(tmp_path / "takes", 3, deep=2)

        answered = read(scan, root)

        assert len(answered[0][1]) == 5

    def test_the_folder_it_was_asked_about(self, scan: FolderScan, tmp_path: Path) -> None:
        root = tree(tmp_path / "takes", 1)

        answered = read(scan, root)

        assert answered[0][0] == root

    def test_they_arrive_in_name_order(self, scan: FolderScan, tmp_path: Path) -> None:
        root = tree(tmp_path / "takes", 4)

        found = read(scan, root)[0][1]

        assert list(found) == sorted(found)

    def test_a_folder_holding_none_answers_with_none(self, scan: FolderScan, tmp_path: Path) -> None:
        root = tree(tmp_path / "takes", 0)

        assert read(scan, root)[0][1] == ()


class TestWhatTheReaderIsTold(BaseTestSuite):
    """The reader hears which folder is being read and how far the walk has got."""

    def test_the_folder_is_named_before_the_walk(self, scan: FolderScan, tmp_path: Path) -> None:
        named: List[Path] = []
        scan.on_started = named.append
        root = tree(tmp_path / "takes", 1)

        read(scan, root)

        assert named == [root]

    def test_the_count_rises_while_it_walks(self, scan: FolderScan, tmp_path: Path) -> None:
        counted: List[int] = []
        scan.on_progress = counted.append
        root = tree(tmp_path / "takes", REPORT_EVERY * 2)

        read(scan, root)

        assert counted == [REPORT_EVERY, REPORT_EVERY * 2]


class TestGivingUp(BaseTestSuite):
    """A reader who asked for the wrong folder stops the walk rather than waiting it out."""

    def test_a_stopped_walk_answers_nobody(self, scan: FolderScan, tmp_path: Path) -> None:
        root = tree(tmp_path / "takes", REPORT_EVERY * 4)
        answered: List[Tuple[Path, Tuple[Path, ...]]] = []
        scan.on_progress = lambda _count: scan.stop()

        scan.start(root, lambda found_root, found: answered.append((found_root, found)))
        SingleThreadExecutor.join_all()

        assert answered == []

    def test_it_says_that_it_stopped(self, scan: FolderScan, tmp_path: Path) -> None:
        root = tree(tmp_path / "takes", REPORT_EVERY * 4)
        stopped: List[bool] = []
        scan.on_stopped = lambda: stopped.append(True)
        scan.on_progress = lambda _count: scan.stop()

        scan.start(root, lambda _root, _found: None)
        SingleThreadExecutor.join_all()

        assert stopped == [True]

    def test_a_walk_that_ended_leaves_the_next_free_to_start(
        self,
        scan: FolderScan,
        tmp_path: Path,
    ) -> None:
        root = tree(tmp_path / "takes", 1)
        read(scan, root)

        assert scan.running is False
        assert len(read(scan, root)) == 1


class TestOneWalkAtATime(BaseTestSuite):
    """The answer travels with the walk that earns it, and a walk is let go however it ends."""

    def test_each_walk_answers_the_caller_that_asked_for_it(
        self,
        scan: FolderScan,
        tmp_path: Path,
    ) -> None:
        """Two callers ask this one scan — a gathering and a conversion — so a walk that reported
        to the other one would convert a folder nobody asked about."""
        first = tree(tmp_path / "first", 2)
        second = tree(tmp_path / "second", 3)
        gathered: List[Tuple[Path, Tuple[Path, ...]]] = []
        converted: List[Tuple[Path, Tuple[Path, ...]]] = []

        scan.start(first, lambda root, found: gathered.append((root, found)))
        SingleThreadExecutor.join_all()
        scan.start(second, lambda root, found: converted.append((root, found)))
        SingleThreadExecutor.join_all()

        assert [root for root, _ in gathered] == [first]
        assert [root for root, _ in converted] == [second]

    def test_a_walk_that_fails_leaves_the_next_free_to_start(
        self,
        scan: FolderScan,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A reading that dies partway holds nothing back, so the reader may ask again."""
        root = tree(tmp_path / "takes", 2)

        def raising(_root: Path) -> List[Path]:
            raise OSError("the tree went away")

        monkeypatch.setattr(scan_module, "walk_entries", raising)
        scan.start(root, lambda _root, _found: None)
        SingleThreadExecutor.join_all()

        assert scan.running is False

        monkeypatch.undo()
        assert len(read(scan, root)) == 1

    def test_a_folder_asked_for_while_one_is_read_is_turned_away(
        self,
        scan: FolderScan,
        tmp_path: Path,
    ) -> None:
        """One walk runs at a time, so the second answer hears nothing until it is asked again."""
        root = tree(tmp_path / "takes", 2)
        answered: List[Path] = []
        scan._running.set()

        scan.start(root, lambda found_root, _found: answered.append(found_root))
        SingleThreadExecutor.join_all()

        assert answered == []
