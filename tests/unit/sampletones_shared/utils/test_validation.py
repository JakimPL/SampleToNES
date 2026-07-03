from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.state.state import ApplicationState
from sampletones_core.configs import Config
from sampletones_shared.utils.validation import (
    Location,
    flatten_location,
    validate_with_recovery,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class Leaf(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int = Field(default=5, ge=0, le=10)
    name: str = Field(default="leaf")


class Branch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leaf: Leaf = Field(default_factory=Leaf)
    ratio: float = Field(default=1.0, ge=0.0)
    tags: List[str] = Field(default_factory=list)


class Root(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch: Branch = Field(default_factory=Branch)
    count: int = Field(default=3, ge=1)


class Required(BaseModel):
    needed: int
    optional: int = Field(default=0)


class RootWithRequired(BaseModel):
    required: Required = Field(default_factory=lambda: Required(needed=1))
    count: int = Field(default=3)


class Strict(BaseModel):
    must: int


class TestValidateWithRecovery(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Root
        raw: Dict[str, Any]
        dropped: Tuple[Location, ...]

    test_cases = [
        TestCase(
            label="valid_input_is_preserved",
            raw={
                "branch": {"leaf": {"value": 7, "name": "x"}, "ratio": 2.0, "tags": ["a"]},
                "count": 9,
            },
            expected=Root(branch=Branch(leaf=Leaf(value=7, name="x"), ratio=2.0, tags=["a"]), count=9),
            dropped=(),
        ),
        TestCase(
            label="out_of_range_leaf_falls_back_to_default",
            raw={"branch": {"leaf": {"value": 99, "name": "x"}}},
            expected=Root(branch=Branch(leaf=Leaf(name="x"))),
            dropped=(("branch", "leaf", "value"),),
        ),
        TestCase(
            label="nested_bad_leaf_keeps_its_siblings",
            raw={"branch": {"leaf": {"value": 99, "name": "keep"}, "ratio": 3.0}},
            expected=Root(branch=Branch(leaf=Leaf(name="keep"), ratio=3.0)),
            dropped=(("branch", "leaf", "value"),),
        ),
        TestCase(
            label="extra_forbidden_key_is_dropped",
            raw={"branch": {"unknown": 1, "ratio": 2.0}},
            expected=Root(branch=Branch(ratio=2.0)),
            dropped=(("branch", "unknown"),),
        ),
        TestCase(
            label="renamed_top_level_key_is_dropped",
            raw={"old_count": 5, "count": 4},
            expected=Root(count=4),
            dropped=(("old_count",),),
        ),
        TestCase(
            label="multiple_independent_failures_all_drop",
            raw={"branch": {"leaf": {"value": 99}, "ratio": -1.0}, "count": 0},
            expected=Root(),
            dropped=(("branch", "leaf", "value"), ("branch", "ratio"), ("count",)),
        ),
        TestCase(
            label="bad_list_element_keeps_valid_elements",
            raw={"branch": {"tags": ["ok", 123, "fine"]}},
            expected=Root(branch=Branch(tags=["ok", "fine"])),
            dropped=(("branch", "tags", 1),),
        ),
        TestCase(
            label="wrong_type_leaf_falls_back_to_default",
            raw={"count": "abc"},
            expected=Root(),
            dropped=(("count",),),
        ),
        TestCase(
            label="empty_input_yields_defaults",
            raw={},
            expected=Root(),
            dropped=(),
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_recovery(self, test_case: TestCase) -> None:
        recovered = validate_with_recovery(Root, test_case.raw)
        assert recovered.model == test_case.expected
        assert set(recovered.dropped) == set(test_case.dropped)

    def test_input_mapping_is_not_mutated(self) -> None:
        raw = {"branch": {"leaf": {"value": 99}}, "count": 0}
        snapshot = {"branch": {"leaf": {"value": 99}}, "count": 0}
        validate_with_recovery(Root, raw)
        assert raw == snapshot

    def test_missing_required_field_escalates_to_parent_default(self) -> None:
        raw = {"required": {"needed": "bad", "optional": 9}, "count": 7}
        recovered = validate_with_recovery(RootWithRequired, raw)
        assert recovered.model.required == Required(needed=1)
        assert recovered.model.count == 7
        assert set(recovered.dropped) == {("required", "needed"), ("required",)}

    def test_unrecoverable_required_field_reraises(self) -> None:
        with pytest.raises(ValidationError):
            validate_with_recovery(Strict, {})


class TestFlattenLocation(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: str
        location: Location

    test_cases = [
        TestCase(label="single_key", location=("count",), expected="count"),
        TestCase(label="nested_keys", location=("generation", "drive"), expected="generation.drive"),
        TestCase(label="list_index", location=("generators", 2), expected="generators[2]"),
        TestCase(label="nested_with_index", location=("branch", "tags", 1), expected="branch.tags[1]"),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_flatten(self, test_case: TestCase) -> None:
        assert flatten_location(test_case.location) == test_case.expected


class TestRecoveryOnRealModels:
    def test_config_keeps_valid_settings_and_drops_incompatible(self) -> None:
        raw = {
            "library": {"sample_rate": 22050},
            "generation": {"drive": -5.0, "reset_phase": False},
            "obsolete_field": 123,
        }
        recovered = validate_with_recovery(Config, raw)
        assert recovered.model.library.sample_rate == 22050
        assert recovered.model.generation.reset_phase is False
        assert recovered.model.generation.drive == Config().generation.drive
        assert set(recovered.dropped) == {("generation", "drive"), ("obsolete_field",)}

    def test_application_config_keeps_favorites_when_volume_invalid(self) -> None:
        raw = {"audio": {"volume": 5.0}, "favorites": {"paths": ["/x/y"]}}
        recovered = validate_with_recovery(ApplicationConfig, raw)
        assert recovered.model.audio.volume == ApplicationConfig().audio.volume
        assert Path("/x/y") in recovered.model.favorites.paths
        assert ("audio", "volume") in recovered.dropped

    def test_application_state_keeps_flags_when_window_invalid(self) -> None:
        raw = {"window": {"width": "huge"}, "autoplay": False}
        recovered = validate_with_recovery(ApplicationState, raw)
        assert recovered.model.autoplay is False
        assert recovered.model.window.width == ApplicationState().window.width
        assert ("window", "width") in recovered.dropped
