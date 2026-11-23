from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, Iterator, Tuple

import pytest

from sampletones_tools.calibration.source import source_digest
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.unit.sampletones_tools.calibration.source_tree import (
    CONFIGURATION,
    MODULE,
    OTHER_VERSION,
    REFEREE_MODULE,
    VERSION,
    edit_source,
    write_source,
)

Packages = Tuple[Path, ...]

EDITED_CONFIGURATION: Final[str] = "scale: 2\n"
ADDED_MODULE: Final[str] = "judge.py"
RENAMED_MODULE: Final[str] = "converter.py"
CACHED_BYTES: Final[bytes] = b"cached"


def _edit_configuration(packages: Packages) -> None:
    (packages[0] / CONFIGURATION).write_text(EDITED_CONFIGURATION, encoding="utf-8")


def _add_module(packages: Packages) -> None:
    (packages[1] / ADDED_MODULE).write_text("", encoding="utf-8")


def _remove_module(packages: Packages) -> None:
    (packages[1] / REFEREE_MODULE).unlink()


def _rename_module(packages: Packages) -> None:
    (packages[0] / MODULE).rename(packages[0] / RENAMED_MODULE)


def _move_module_to_another_package(packages: Packages) -> None:
    (packages[1] / REFEREE_MODULE).rename(packages[0] / REFEREE_MODULE)


class TestASourceEdit(BaseTestSuite):
    """Any edit to a file the packages ship moves the digest, so a resume across it is told apart."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        edit: Callable[[Packages], None]

    test_cases = (
        TestCase(edit=edit_source, label="module edited"),
        TestCase(edit=_edit_configuration, label="configuration edited"),
        TestCase(edit=_add_module, label="module added"),
        TestCase(edit=_remove_module, label="module removed"),
        TestCase(edit=_rename_module, label="module renamed"),
        TestCase(edit=_move_module_to_another_package, label="module moved to another package"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_an_edit_moves_the_digest(self, test_case: TestCase, packages: Packages) -> None:
        before = source_digest(packages, VERSION)

        test_case.edit(packages)

        assert source_digest(packages, VERSION) != before

    def test_another_version_moves_the_digest(self, packages: Packages) -> None:
        assert source_digest(packages, OTHER_VERSION) != source_digest(packages, VERSION)


class TestAnUnchangedSource:
    """The same source reads the same digest, however and wherever it is found."""

    def test_an_unchanged_tree_reads_the_same_digest(self, packages: Packages) -> None:
        assert source_digest(packages, VERSION) == source_digest(packages, VERSION)

    def test_the_order_the_files_are_listed_in_leaves_the_digest_unmoved(
        self, packages: Packages, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        listed = source_digest(packages, VERSION)
        forward = Path.rglob

        def backward(directory: Path, pattern: str) -> Iterator[Path]:
            return reversed(list(forward(directory, pattern)))

        monkeypatch.setattr(Path, "rglob", backward)

        assert source_digest(packages, VERSION) == listed

    def test_the_order_the_packages_are_named_in_leaves_the_digest_unmoved(self, packages: Packages) -> None:
        assert source_digest(packages[::-1], VERSION) == source_digest(packages, VERSION)

    def test_the_tree_read_from_another_folder_reads_the_same_digest(self, packages: Packages, tmp_path: Path) -> None:
        moved = write_source(tmp_path / "elsewhere")

        assert source_digest(moved, VERSION) == source_digest(packages, VERSION)


class TestCachesBesideTheSource(BaseTestSuite):
    """The caches the interpreter and the developer tools write into a package leave the digest unmoved."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        cache: str

    test_cases = (
        TestCase(cache="__pycache__/conversion.cpython-312.pyc", label="bytecode"),
        TestCase(cache="configs/__pycache__/__init__.cpython-312.pyc", label="nested bytecode"),
        TestCase(cache=".mypy_cache/3.12/conversion.data.json", label="type-check cache"),
        TestCase(cache=".DS_Store", label="hidden file"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_cache_leaves_the_digest_unmoved(self, test_case: TestCase, packages: Packages) -> None:
        before = source_digest(packages, VERSION)
        cache = packages[0] / test_case.cache
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(CACHED_BYTES)

        assert source_digest(packages, VERSION) == before
