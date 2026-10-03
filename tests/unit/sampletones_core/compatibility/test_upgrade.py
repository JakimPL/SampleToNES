from dataclasses import dataclass
from typing import Any, Final, Optional

import pytest

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.update import VersionUpdate
from sampletones_core.compatibility.upgrade import read_version, upgrade
from sampletones_shared.deployment.version import Version
from sampletones_shared.types.data import SerializedData
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

FIRST_MARKER: Final[str] = "first"
SECOND_MARKER: Final[str] = "second"


def _marking_update(base: str, target: str, marker: str) -> VersionUpdate:
    def apply(data: SerializedData) -> SerializedData:
        markers = list(data["markers"])
        markers.append(marker)
        return {**data, "markers": markers}

    return VersionUpdate(ObjectKind.RECONSTRUCTION, Version.model_validate(base), Version.model_validate(target), apply)


def _reconstruction_data(version: str) -> SerializedData:
    return {"metadata": {"reconstruction_data_version": version}, "markers": []}


class TestUpgradeChain:
    def test_chain_applies_each_update_in_order(self) -> None:
        updates = (
            _marking_update("1.0", "1.1", FIRST_MARKER),
            _marking_update("1.1", "1.2", SECOND_MARKER),
        )

        upgraded = upgrade(ObjectKind.RECONSTRUCTION, "1.0", _reconstruction_data("1.0"), updates, "1.2")

        assert upgraded["markers"] == [FIRST_MARKER, SECOND_MARKER]
        assert upgraded["metadata"]["reconstruction_data_version"] == "1.2"

    def test_current_version_returns_the_input_unchanged(self) -> None:
        updates = (_marking_update("1.0", "1.1", FIRST_MARKER),)
        data = _reconstruction_data("1.1")

        assert upgrade(ObjectKind.RECONSTRUCTION, "1.1", data, updates, "1.1") is data

    def test_partial_chain_returns_the_input_unchanged(self) -> None:
        updates = (_marking_update("1.0", "1.1", FIRST_MARKER),)
        data = _reconstruction_data("1.0")

        assert upgrade(ObjectKind.RECONSTRUCTION, "1.0", data, updates, "1.2") is data

    def test_future_version_returns_the_input_unchanged(self) -> None:
        updates = (_marking_update("1.0", "1.1", FIRST_MARKER),)
        data = _reconstruction_data("1.2")

        assert upgrade(ObjectKind.RECONSTRUCTION, "1.2", data, updates, "1.1") is data

    def test_unknown_starting_version_returns_the_input_unchanged(self) -> None:
        updates = (_marking_update("1.0", "1.1", FIRST_MARKER),)
        data = _reconstruction_data("0.9")

        assert upgrade(ObjectKind.RECONSTRUCTION, "0.9", data, updates, "1.1") is data

    def test_two_component_version_matches_three_component_base(self) -> None:
        updates = (_marking_update("1.1.0", "1.2", FIRST_MARKER),)

        upgraded = upgrade(ObjectKind.RECONSTRUCTION, "1.1", _reconstruction_data("1.1"), updates, "1.2")

        assert upgraded["markers"] == [FIRST_MARKER]

    def test_project_update_stamps_format_version(self) -> None:
        updates = (
            VersionUpdate(
                ObjectKind.PROJECT,
                Version.model_validate("1.0"),
                Version.model_validate("1.1"),
                lambda data: {**data, "upgraded": True},
            ),
        )

        upgraded = upgrade(ObjectKind.PROJECT, "1.0", {"format_version": "1.0"}, updates, "1.1")

        assert upgraded["format_version"] == "1.1"
        assert upgraded["upgraded"] is True

    def test_duplicate_base_raises(self) -> None:
        updates = (
            _marking_update("1.0", "1.1", FIRST_MARKER),
            _marking_update("1.0", "1.2", SECOND_MARKER),
        )

        with pytest.raises(ValueError):
            upgrade(ObjectKind.RECONSTRUCTION, "1.0", _reconstruction_data("1.0"), updates, "1.2")


class TestReadVersion(BaseTestSuite):
    """A format's version is read where the format keeps it, and anything else there states none."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        kind: ObjectKind
        payload: Any
        expected: Optional[str]

    test_cases = (
        TestCase(
            label="a project states it at the root",
            kind=ObjectKind.PROJECT,
            payload={"format_version": "1.0"},
            expected="1.0",
        ),
        TestCase(
            label="a reconstruction states it in its metadata",
            kind=ObjectKind.RECONSTRUCTION,
            payload={"metadata": {"reconstruction_data_version": "2.1"}},
            expected="2.1",
        ),
        TestCase(
            label="a library states it in its metadata",
            kind=ObjectKind.LIBRARY,
            payload={"metadata": {"library_data_version": "2.0"}},
            expected="2.0",
        ),
        TestCase(
            label="a project version in metadata is another format's place",
            kind=ObjectKind.PROJECT,
            payload={"metadata": {"format_version": "1.0"}},
            expected=None,
        ),
        TestCase(
            label="a reconstruction version at the root is another format's place",
            kind=ObjectKind.RECONSTRUCTION,
            payload={"reconstruction_data_version": "2.1"},
            expected=None,
        ),
        TestCase(
            label="a version written as a number",
            kind=ObjectKind.PROJECT,
            payload={"format_version": 1.0},
            expected=None,
        ),
        TestCase(
            label="metadata that is not a mapping",
            kind=ObjectKind.RECONSTRUCTION,
            payload={"metadata": ["reconstruction_data_version", "2.1"]},
            expected=None,
        ),
        TestCase(
            label="a payload that is not a mapping",
            kind=ObjectKind.PROJECT,
            payload=["format_version", "1.0"],
            expected=None,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_stated_version_is_read_from_its_place(self, test_case: TestCase) -> None:
        assert read_version(test_case.kind, test_case.payload) == test_case.expected
