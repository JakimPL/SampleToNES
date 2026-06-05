from datetime import timezone

import pytest
from pydantic import ValidationError

from sampletones_core.project import ProjectInfo
from sampletones_shared.constants.application import SAMPLETONES_AUTHOR
from sampletones_shared.constants.project import (
    DEFAULT_PROJECT_COMMENT,
    DEFAULT_PROJECT_TITLE,
)


class TestDefaults:
    def test_default_info(self) -> None:
        info = ProjectInfo()
        assert info.title == DEFAULT_PROJECT_TITLE
        assert info.author == SAMPLETONES_AUTHOR
        assert info.comment == DEFAULT_PROJECT_COMMENT

    def test_timestamps_are_utc(self) -> None:
        info = ProjectInfo()
        assert info.created.tzinfo == timezone.utc
        assert info.modified.tzinfo == timezone.utc


class TestMutability:
    def test_touch_updates_modified(self) -> None:
        info = ProjectInfo()
        before = info.modified
        info.touch()
        assert info.modified >= before

    def test_assignment_is_validated(self) -> None:
        info = ProjectInfo()
        info.title = "Song"
        assert info.title == "Song"

        with pytest.raises(ValidationError):
            info.title = 123  # type: ignore[assignment]


class TestSerialization:
    def test_round_trip(self) -> None:
        info = ProjectInfo(title="Song", author="Someone", comment="notes")
        restored = ProjectInfo.model_validate(info.model_dump())
        assert restored == info

    def test_json_round_trip_preserves_timestamps(self) -> None:
        info = ProjectInfo(title="Song")
        restored = ProjectInfo.model_validate_json(info.model_dump_json())
        assert restored.created == info.created
        assert restored.modified == info.modified
