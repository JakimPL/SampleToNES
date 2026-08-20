from typing import Final

import pytest

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.update import VersionUpdate
from sampletones_core.compatibility.upgrade import upgrade
from sampletones_shared.deployment.version import Version
from sampletones_shared.types.data import SerializedData

FIRST_MARKER: Final[str] = "first"
SECOND_MARKER: Final[str] = "second"


def _marking_update(base: str, target: str, marker: str) -> VersionUpdate:
    def apply(data: SerializedData) -> SerializedData:
        markers = list(data["markers"])
        markers.append(marker)
        return {**data, "markers": markers}

    return VersionUpdate(ObjectKind.LIBRARY, Version.model_validate(base), Version.model_validate(target), apply)


def _library_data(version: str) -> SerializedData:
    return {"metadata": {"library_data_version": version}, "markers": []}


class TestUpgradeChain:
    def test_chain_applies_each_update_in_order(self) -> None:
        updates = (
            _marking_update("1.0", "1.1", FIRST_MARKER),
            _marking_update("1.1", "1.2", SECOND_MARKER),
        )

        upgraded = upgrade(ObjectKind.LIBRARY, "1.0", _library_data("1.0"), updates, "1.2")

        assert upgraded["markers"] == [FIRST_MARKER, SECOND_MARKER]
        assert upgraded["metadata"]["library_data_version"] == "1.2"

    def test_current_version_returns_the_input_unchanged(self) -> None:
        updates = (_marking_update("1.0", "1.1", FIRST_MARKER),)
        data = _library_data("1.1")

        assert upgrade(ObjectKind.LIBRARY, "1.1", data, updates, "1.1") is data

    def test_partial_chain_returns_the_input_unchanged(self) -> None:
        updates = (_marking_update("1.0", "1.1", FIRST_MARKER),)
        data = _library_data("1.0")

        assert upgrade(ObjectKind.LIBRARY, "1.0", data, updates, "1.2") is data

    def test_future_version_returns_the_input_unchanged(self) -> None:
        updates = (_marking_update("1.0", "1.1", FIRST_MARKER),)
        data = _library_data("1.2")

        assert upgrade(ObjectKind.LIBRARY, "1.2", data, updates, "1.1") is data

    def test_unknown_starting_version_returns_the_input_unchanged(self) -> None:
        updates = (_marking_update("1.0", "1.1", FIRST_MARKER),)
        data = _library_data("0.9")

        assert upgrade(ObjectKind.LIBRARY, "0.9", data, updates, "1.1") is data

    def test_two_component_version_matches_three_component_base(self) -> None:
        updates = (_marking_update("1.1.0", "1.2", FIRST_MARKER),)

        upgraded = upgrade(ObjectKind.LIBRARY, "1.1", _library_data("1.1"), updates, "1.2")

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
            upgrade(ObjectKind.LIBRARY, "1.0", _library_data("1.0"), updates, "1.2")
