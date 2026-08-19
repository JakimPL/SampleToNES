from typing import Final

from sampletones_core.compatibility.fields import CHANNEL_NAME, CHANNELS, CONFIG, GENERATION, GENERATOR_NAME, GENERATORS
from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.update import VersionUpdate
from sampletones_core.compatibility.utils import renamed
from sampletones_shared.deployment.version import Version
from sampletones_shared.types.data import SerializedData


def update(data: SerializedData) -> SerializedData:
    """Names each stored stream and approximation by its channel.

    Data version 2.1 stored a channel's stream and approximation under the key
    ``generator_name`` and the channel selection under
    ``config.generation.generators``. Data version 2.2 names them ``channel_name``
    and ``config.generation.channels``.
    """
    updated = dict(data)
    approximations = data.get("approximations_data")
    if isinstance(approximations, list):
        updated["approximations_data"] = [
            renamed(
                item,
                GENERATOR_NAME,
                CHANNEL_NAME,
            )
            for item in approximations
        ]

    instructions = data.get("instructions_data")
    if isinstance(instructions, list):
        updated["instructions_data"] = [
            renamed(
                item,
                GENERATOR_NAME,
                CHANNEL_NAME,
            )
            for item in instructions
        ]

    config = data.get(CONFIG)
    if isinstance(config, dict):
        generation = config.get(GENERATION)
        if isinstance(generation, dict):
            updated["config"] = {
                **config,
                GENERATION: renamed(generation, GENERATORS, CHANNELS),
            }

    return updated


V2_2: Final[VersionUpdate] = VersionUpdate(
    kind=ObjectKind.RECONSTRUCTION,
    base=Version.model_validate("2.1"),
    target=Version.model_validate("2.2"),
    apply=update,
)
