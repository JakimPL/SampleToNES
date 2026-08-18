from sampletones_shared.paths.source import REPOSITORY_ROOT, SOURCE_ROOT

PROJECT_FILE = "pyproject.toml"
SHARED_PACKAGE = "sampletones_shared"


class TestSourceRoot:
    def test_the_source_root_holds_the_packages(self) -> None:
        assert (SOURCE_ROOT / SHARED_PACKAGE).is_dir()

    def test_the_source_root_is_where_this_package_lives(self) -> None:
        """Reading the root off the package keeps it right wherever the packages are installed."""
        assert (SOURCE_ROOT / SHARED_PACKAGE / "paths" / "source.py").is_file()


class TestRepositoryRoot:
    def test_the_repository_root_holds_the_project_file(self) -> None:
        assert (REPOSITORY_ROOT / PROJECT_FILE).is_file()

    def test_the_repository_root_holds_the_scripts_the_checks_run_from(self) -> None:
        assert (REPOSITORY_ROOT / "scripts" / "checks").is_dir()
