import pytest

from sampletones_shared.paths.source import SOURCE_ROOT
from sampletones_tools.checks.source.packages import source_package_directory

SHARED_PACKAGE = "sampletones_shared"
APPLICATION_PACKAGE = "sampletones_application"


class TestSourcePackageDirectory:
    def test_a_top_level_package_sits_under_the_source_root(self) -> None:
        assert source_package_directory(SHARED_PACKAGE) == SOURCE_ROOT / SHARED_PACKAGE

    def test_a_subpackage_is_named_part_by_part(self) -> None:
        assert (
            source_package_directory(SHARED_PACKAGE, "utils", "system")
            == SOURCE_ROOT / SHARED_PACKAGE / "utils" / "system"
        )

    def test_the_answer_is_a_directory_a_sweep_reads_under(self) -> None:
        """A package resource resolves to `__init__.py`, which a sweep reads nothing under."""
        assert source_package_directory(APPLICATION_PACKAGE, "tags").is_dir()

    def test_a_package_the_source_root_holds_no_directory_for_raises(self) -> None:
        with pytest.raises(NotADirectoryError):
            source_package_directory("sampletones_absent")

    def test_a_module_named_as_a_package_raises(self) -> None:
        with pytest.raises(NotADirectoryError):
            source_package_directory(SHARED_PACKAGE, "paths.py")

    def test_the_report_names_the_path_it_looked_at(self) -> None:
        with pytest.raises(NotADirectoryError, match="sampletones_absent"):
            source_package_directory("sampletones_absent")
