from pathlib import Path

from sampletones_shared.utils.serialization import load_yaml

from .prototype import PrototypeConfig


def load_prototype_config(path: Path) -> PrototypeConfig:
    raw = load_yaml(path)
    if not isinstance(raw, dict):
        raise TypeError(f"Config file must contain a mapping, got {type(raw)}")

    return PrototypeConfig.model_validate(raw)
