from typing import Dict, Mapping, Self

from pydantic import BaseModel, JsonValue

from sampletones_core.configs import Config
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.calibration.paths import SETTINGS_CONFIG_PATH

Overrides = Dict[str, JsonValue]


class SettingsConfig(BaseModel, frozen=True):
    """
    Named sets of settings a run measures beside its base configuration, one variant each.

    Each set is a nested mapping in the shape of the configuration file, holding only the values it
    changes, so an opt-in setting is measured by name against the configuration it departs from.
    Values are loaded from the packaged `settings.yaml`.
    """

    settings: Dict[str, Overrides]

    @classmethod
    def load(cls) -> Self:
        """
        Load the packaged settings.

        Returns:
            The settings validated from `sampletones_tools/calibration/config/settings.yaml`.

        Raises:
            TypeError: If the configuration file holds anything other than a mapping.
        """
        return load_yaml_model(SETTINGS_CONFIG_PATH, cls)


def overridden(base: Config, overrides: Mapping[str, JsonValue]) -> Config:
    """The configuration ``base`` becomes with ``overrides`` written over it, section by section.

    Raises:
        ValidationError: If an override names a setting the configuration lacks or holds a value it refuses.
    """
    return Config.model_validate(_merged(base.model_dump(mode="json"), overrides))


def _merged(base: Mapping[str, JsonValue], overrides: Mapping[str, JsonValue]) -> Dict[str, JsonValue]:
    merged: Dict[str, JsonValue] = dict(base)
    for key, value in overrides.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _merged(current, value)
        else:
            merged[key] = value

    return merged
