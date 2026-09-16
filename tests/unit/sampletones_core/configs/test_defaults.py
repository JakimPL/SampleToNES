from typing import Any, Dict, Mapping, Tuple

import pytest
from pydantic import BaseModel

from sampletones_core.configs.defaults import GENERATION_DEFAULTS_PATH, generation_default
from sampletones_core.configs.generation import GenerationConfig
from sampletones_shared.utils.serialization import load_yaml


def _shipped() -> Mapping[str, Any]:
    values = load_yaml(GENERATION_DEFAULTS_PATH)
    assert isinstance(values, dict)
    return values


def _settings(model: BaseModel, *path: str) -> Dict[Tuple[str, ...], Any]:
    """Every value the model holds, keyed by the path of names reaching it."""
    held: Dict[Tuple[str, ...], Any] = {}
    for name, value in model:
        if isinstance(value, BaseModel):
            held.update(_settings(value, *path, name))
        else:
            held[(*path, name)] = value

    return held


def _stated(values: Mapping[str, Any], *path: str) -> Dict[Tuple[str, ...], Any]:
    """Every value the file states, keyed by the path of names reaching it."""
    stated: Dict[Tuple[str, ...], Any] = {}
    for name, value in values.items():
        if isinstance(value, Mapping):
            stated.update(_stated(value, *path, name))
        else:
            stated[(*path, name)] = value

    return stated


class TestTheFileStatesTheMatchingDefaults:
    """The packaged `generation.yaml` is where a matching default is written, and the only place."""

    def test_every_setting_starts_at_the_value_the_file_states(self) -> None:
        for path, value in _settings(GenerationConfig()).items():
            assert value == generation_default(*path)

    def test_every_value_the_file_states_names_a_setting(self) -> None:
        assert set(_stated(_shipped())) == set(_settings(GenerationConfig()))


class TestReadingOneDefault:
    def test_a_path_the_file_states_nothing_at_is_refused(self) -> None:
        with pytest.raises(KeyError):
            generation_default("metric", "loudness")
