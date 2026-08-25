from dataclasses import dataclass
from typing import Optional, Tuple

import pytest

from sampletones_shared.meta.import_boundary.imports import imported_module, matches_prefix
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase


class TestImportedModule(BaseTestSuite):
    """The module one line of source imports, whichever spelling the line uses."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Optional[str]
        line: str
        name: str

        @property
        def label(self) -> str:
            return self.name

    test_cases: Tuple[TestCase, ...] = (
        TestCase(name="plain-import", line="import numpy", expected="numpy"),
        TestCase(name="aliased-import", line="import numpy as np", expected="numpy"),
        TestCase(name="dotted-import", line="import dearpygui.dearpygui as dpg", expected="dearpygui.dearpygui"),
        TestCase(name="from-import", line="from package.module import Thing", expected="package.module"),
        TestCase(name="indented-import", line="    import numpy", expected="numpy"),
        TestCase(name="assignment", line="imported = 1", expected=None),
        TestCase(name="comment", line="# import numpy", expected=None),
        TestCase(name="blank", line="", expected=None),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_line_names_the_module_it_imports(self, test_case: TestCase) -> None:
        assert imported_module(test_case.line) == test_case.expected


class TestMatchesPrefix:
    """A prefix names the module itself and everything underneath it, and nothing beside it."""

    def test_the_prefix_itself_matches(self) -> None:
        assert matches_prefix("package.module", "package.module")

    def test_a_module_underneath_matches(self) -> None:
        assert matches_prefix("package.module.inner", "package.module")

    def test_a_module_beside_it_stays_clear(self) -> None:
        assert not matches_prefix("package.modules", "package.module")

    def test_a_module_above_it_stays_clear(self) -> None:
        assert not matches_prefix("package", "package.module")
