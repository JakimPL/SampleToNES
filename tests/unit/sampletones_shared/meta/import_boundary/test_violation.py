from pathlib import Path

from sampletones_shared.meta.import_boundary.violation import Violation


class TestViolationLocation:
    """Where a report sends a reader to see what a rule caught."""

    def test_the_location_reads_as_path_and_line(self) -> None:
        violation = Violation.at("other_package", Path("package/logic/direct.py"), 2, "import other_package")

        assert violation.location == "package/logic/direct.py:2: import other_package"

    def test_the_quoted_line_stands_clear_of_its_indentation(self) -> None:
        violation = Violation.at("other_package", Path("direct.py"), 1, "    import other_package")

        assert violation.location.endswith(": import other_package")

    def test_the_kind_names_what_the_rule_forbids(self) -> None:
        assert Violation.at("other_package", Path("direct.py"), 1, "import other_package").kind == "other_package"
