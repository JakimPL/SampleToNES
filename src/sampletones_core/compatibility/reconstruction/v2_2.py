from typing import Any, Final

from sampletones_core.compatibility.fields import (
    APPROXIMATIONS_DATA,
    ASSIGNMENTS,
    AUDIO_FILEPATH,
    BENDS,
    CHANNEL_CAP,
    CHANNEL_NAME,
    CHANNELS,
    CONFIG,
    ENTRIES,
    GENERATION,
    GENERATOR_NAME,
    GENERATORS,
    HIERARCHY,
    ID,
    INSTRUCTIONS,
    INSTRUCTIONS_DATA,
    LEVELS,
    METADATA,
    MODE,
    RECONSTRUCTION_DATA_VERSION,
    SETTINGS,
    STEM_IDS,
    STEMS_DATA,
)
from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.update import VersionUpdate
from sampletones_core.compatibility.utils import renamed
from sampletones_core.constants.algorithm import (
    DEFAULT_STEMS_CHANNEL_CAP,
    DEFAULT_STEMS_HIERARCHY_MODE,
)
from sampletones_shared.deployment.version import Version
from sampletones_shared.types.data import SerializedData

SOURCE_DATA_VERSION: Final[str] = "2.1"
TARGET_DATA_VERSION: Final[str] = "2.2"


def _normalized_audio_filepath(data: SerializedData) -> Any:
    raw = data.get(AUDIO_FILEPATH)
    if raw is None:
        return []

    if isinstance(raw, list):
        return raw

    return [raw]


def _default_stems_data(data: SerializedData) -> SerializedData:
    """The single-entry stems record a conversion predating stems carries.

    One stem covers every enabled channel and owns every frame of each channel that plays,
    which is the classic run's shape, so the synthesized record states what the
    reconstruction is. It bends nothing, which is what a build writing this shape did.
    """
    config = data.get(CONFIG)
    channels = config.get(GENERATION, {}).get(CHANNELS, []) if isinstance(config, dict) else []
    instructions_data = data.get(INSTRUCTIONS_DATA)
    stream_items = instructions_data if isinstance(instructions_data, list) else []
    assignments = [
        {
            CHANNEL_NAME: item.get(CHANNEL_NAME),
            STEM_IDS: [0] * len(item.get(INSTRUCTIONS, [])),
        }
        for item in stream_items
        if isinstance(item, dict) and item.get(INSTRUCTIONS)
    ]
    return {
        CONFIG: {
            ENTRIES: [{ID: 0, SETTINGS: {CHANNELS: channels, BENDS: []}}],
            HIERARCHY: {LEVELS: [[0]], MODE: str(DEFAULT_STEMS_HIERARCHY_MODE)},
            CHANNEL_CAP: DEFAULT_STEMS_CHANNEL_CAP,
        },
        ASSIGNMENTS: assignments,
    }


def _renamed_stream_keys(data: SerializedData) -> SerializedData:
    """The stream and approximation sections keyed by channel name."""
    updated = dict(data)
    for section in (APPROXIMATIONS_DATA, INSTRUCTIONS_DATA):
        entries = data.get(section)
        if isinstance(entries, list):
            updated[section] = [renamed(item, GENERATOR_NAME, CHANNEL_NAME) for item in entries]

    return updated


def _stamped_embedded_config(data: SerializedData) -> SerializedData:
    """The embedded config named by channel and stamped with the target version."""
    updated = dict(data)
    config = data.get(CONFIG)
    if not isinstance(config, dict):
        return updated

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
        updated_config[GENERATION] = renamed(generation, GENERATORS, CHANNELS)

    updated[CONFIG] = updated_config
    return updated


def _normalized_source_paths(data: SerializedData) -> SerializedData:
    """The recorded source audio as one path per stem."""
    updated = dict(data)
    updated[AUDIO_FILEPATH] = _normalized_audio_filepath(data)
    return updated


def _with_default_stems_record(data: SerializedData) -> SerializedData:
    """The single-entry stems record, present on every reconstruction."""
    updated = dict(data)
    if STEMS_DATA not in updated:
        updated[STEMS_DATA] = _default_stems_data(updated)

    return updated


def _without_configured_channels(data: SerializedData) -> SerializedData:
    """The embedded config with its channel list dropped, now the stems record carries it.

    Which channels a run hands out is the setup's to state, so the configuration holds the
    settings that shaped the library and nothing about the channels themselves.
    """
    config = data.get(CONFIG)
    if not isinstance(config, dict):
        return data

    generation = config.get(GENERATION)
    if not isinstance(generation, dict):
        return data

    updated = dict(data)
    updated[CONFIG] = {
        **config,
        GENERATION: {key: value for key, value in generation.items() if key != CHANNELS},
    }
    return updated


def update(data: SerializedData) -> SerializedData:
    """Names each stored stream and approximation by its channel.

    Data version 2.1 stored a channel's stream and approximation under the key
    ``generator_name`` and the channel selection under
    ``config.generation.generators``. Data version 2.2 names the streams
    ``channel_name``, stamps the embedded config's metadata with the new data version,
    records the source audio as one path per stem, and carries the single-entry stems
    record every reconstruction states, down to the settings each stem is converted
    with: the channels it takes, and the ones it carries towards its own recording. The
    channel selection moves onto that record, so the embedded configuration lets it go.
    """
    updated = dict(data)
    updated = _renamed_stream_keys(updated)
    updated = _stamped_embedded_config(updated)
    updated = _normalized_source_paths(updated)
    updated = _with_default_stems_record(updated)
    return _without_configured_channels(updated)


V2_2: Final[VersionUpdate] = VersionUpdate(
    kind=ObjectKind.RECONSTRUCTION,
    base=Version.model_validate(SOURCE_DATA_VERSION),
    target=Version.model_validate(TARGET_DATA_VERSION),
    apply=update,
)
