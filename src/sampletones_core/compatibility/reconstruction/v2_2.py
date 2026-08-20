from typing import Final

from sampletones_core.compatibility.fields import (
    APPROXIMATIONS_DATA,
    CHANNEL_NAME,
    CHANNELS,
    CONFIG,
    GENERATION,
    GENERATOR_NAME,
    GENERATORS,
    INSTRUCTIONS_DATA,
    METADATA,
    RECONSTRUCTION_DATA_VERSION,
)
from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.update import VersionUpdate
from sampletones_core.compatibility.utils import renamed
from sampletones_shared.deployment.version import Version
from sampletones_shared.types.data import SerializedData

SOURCE_DATA_VERSION: Final[str] = "2.1"
TARGET_DATA_VERSION: Final[str] = "2.2"


def update(data: SerializedData) -> SerializedData:
    """Names each stored stream and approximation by its channel.

    Data version 2.1 stored a channel's stream and approximation under the key
    ``generator_name`` and the channel selection under
    ``config.generation.generators``. Data version 2.2 names them ``channel_name``
    and ``config.generation.channels``, and stamps the embedded config's metadata
    with the new data version, since the load contract holds every metadata block
    to it.
    """
    updated = dict(data)
    approximations = data.get(APPROXIMATIONS_DATA)
    if isinstance(approximations, list):
        updated[APPROXIMATIONS_DATA] = [
            renamed(
                item,
                GENERATOR_NAME,
                CHANNEL_NAME,
            )
            for item in approximations
        ]

    instructions = data.get(INSTRUCTIONS_DATA)
    if isinstance(instructions, list):
        updated[INSTRUCTIONS_DATA] = [
            renamed(
                item,
                GENERATOR_NAME,
                CHANNEL_NAME,
            )
            for item in instructions
        ]

    config = data.get(CONFIG)
    if isinstance(config, dict):
        updated_config = dict(config)
        metadata = config.get(METADATA)
        if isinstance(metadata, dict) and isinstance(
            metadata.get(RECONSTRUCTION_DATA_VERSION),
            str,
        ):
            updated_config[METADATA] = {
                **metadata,
                RECONSTRUCTION_DATA_VERSION: TARGET_DATA_VERSION,
            }

        generation = config.get(GENERATION)
        if isinstance(generation, dict):
            updated_config[GENERATION] = renamed(
                generation,
                GENERATORS,
                CHANNELS,
            )

        updated[CONFIG] = updated_config

    return updated


V2_2: Final[VersionUpdate] = VersionUpdate(
    kind=ObjectKind.RECONSTRUCTION,
    base=Version.model_validate(SOURCE_DATA_VERSION),
    target=Version.model_validate(TARGET_DATA_VERSION),
    apply=update,
)
