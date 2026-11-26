from typing import Any, Dict, Mapping, Tuple

import pytest

from sampletones_core.configs.defaults import GENERATION_DEFAULTS_PATH, generation_default
from sampletones_core.configs.generation import GenerationConfig
from sampletones_shared.utils.serialization import load_yaml


def _shipped() -> Mapping[str, Any]:
    values = load_yaml(GENERATION_DEFAULTS_PATH)
    assert isinstance(values, dict)
    return values


def _settings() -> Dict[Tuple[str, ...], Any]:
    """Every value the default settings hold, written as the file writes it, keyed by the path of names reaching it.

    The file is YAML, which writes a tuple as a list and an enumeration by its value, so the
    settings are read in the form they serialize to.
    """
    return _stated(GenerationConfig().model_dump(mode="json"))


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
        for path, value in _settings().items():
            assert value == generation_default(*path)

    def test_every_value_the_file_states_names_a_setting(self) -> None:
        assert set(_stated(_shipped())) == set(_settings())


class TestReadingOneDefault:
    def test_a_path_the_file_states_nothing_at_is_refused(self) -> None:
        with pytest.raises(KeyError):
            generation_default("metric", "loudness")
