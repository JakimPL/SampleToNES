import tomllib
from pathlib import Path

from bootstrap.layout import (
    CHECKED_PATHS,
    FORMATTED_PATHS,
    PROJECT_FILE,
    REPOSITORY_ROOT,
    SOURCE_DIRECTORY,
    repository_root,
)


class TestRepositoryRoot:
    def test_the_root_holds_the_project_beside_the_sources(self) -> None:
        root = repository_root()

        assert (root / PROJECT_FILE).is_file()
        assert (root / SOURCE_DIRECTORY / "sampletones" / "__main__.py").is_file()


class TestTheCheckedPaths:
    """``make lint``, ``make format``, mypy and the pre-commit hooks read one set of paths, so a file
    passing one passes them all."""

    def test_mypy_reads_the_source_packages_and_the_checked_paths(self) -> None:
        document = tomllib.loads((REPOSITORY_ROOT / PROJECT_FILE).read_text(encoding="utf-8"))
        files = document["tool"]["mypy"]["files"]
        source = [path for path in files if path.startswith(f"{SOURCE_DIRECTORY}/")]

        assert source and all(Path(path).parent == Path(SOURCE_DIRECTORY) for path in source)
        assert [path for path in files if path not in source] == list(CHECKED_PATHS[1:])

    def test_the_formatted_paths_are_the_checked_ones_and_the_tests(self) -> None:
        assert set(FORMATTED_PATHS) - set(CHECKED_PATHS) == {"tests"}

    def test_every_checked_path_stands_in_the_repository(self) -> None:
        assert all((REPOSITORY_ROOT / path).exists() for path in CHECKED_PATHS)
