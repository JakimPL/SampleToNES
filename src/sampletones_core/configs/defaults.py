from functools import lru_cache
from pathlib import Path
from typing import Any, Final, Mapping

from sampletones_shared.paths.package import package_directory
from sampletones_shared.utils.serialization import load_yaml

GENERATION_DEFAULTS_PATH: Final[Path] = package_directory("sampletones_core.configs") / "generation.yaml"


@lru_cache(maxsize=1)
def _generation_defaults() -> Mapping[str, Any]:
    values = load_yaml(GENERATION_DEFAULTS_PATH)
    if not isinstance(values, dict):
        raise TypeError(f"{GENERATION_DEFAULTS_PATH} must hold a mapping of settings, got {type(values)}")

    return values


def generation_default(*names: str) -> Any:
    """The shipped value of one matching setting, read from the packaged `generation.yaml`.

    The file states every value a reconstruction starts from, so a tuning is changed there and
    reaches the schema, the interface and the documented defaults together.

    Args:
        names: The setting's path through the section, outermost name first.

    Returns:
        Any: The value the file states for that setting.

    Raises:
        KeyError: If the file states no value at that path.
    """
    value: Any = _generation_defaults()
    for name in names:
        if not isinstance(value, Mapping) or name not in value:
            raise KeyError(f"{GENERATION_DEFAULTS_PATH} states no default for {'.'.join(names)}")

        value = value[name]

    return value
