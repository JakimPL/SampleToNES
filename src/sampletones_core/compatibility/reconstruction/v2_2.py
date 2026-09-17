from pathlib import Path
from typing import Any, Final, List

from sampletones_core.compatibility.fields import (
    APPROXIMATION,
    APPROXIMATIONS_DATA,
    ASSIGNMENTS,
    AUDIO_FILEPATH,
    BENDS,
    CHANNEL_CAP,
    CHANNEL_NAME,
    CHANNELS,
    CONFIG,
    DRIVE,
    DRIVES,
    ENTRIES,
    GENERATION,
    GENERATOR_NAME,
    GENERATORS,
    HIERARCHY,
    ID,
    INSTRUCTION,
    INSTRUCTIONS,
    INSTRUCTIONS_DATA,
    LEVELS,
    METADATA,
    MIXER,
    MODE,
    NAME,
    ON,
    PATH,
    RECONSTRUCTION_DATA_VERSION,
    SETTINGS,
    SOURCES,
    STEM_ID,
    STEM_IDS,
    STEMS_DATA,
    UNION_DATA,
)
from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.update import VersionUpdate
from sampletones_core.compatibility.utils import renamed
from sampletones_core.constants.algorithm import (
    ALL_STEMS_CHANNEL_CAP,
    DEFAULT_STEMS_HIERARCHY_MODE,
    MAX_DRIVE,
    MIN_DRIVE,
    RESTING_STEM_ID,
    UNIT_DRIVE,
)
from sampletones_shared.deployment.version import Version
from sampletones_shared.types.data import SerializedData

SOURCE_DATA_VERSION: Final[str] = "2.1"
TARGET_DATA_VERSION: Final[str] = "2.2"
SINGLE_STEM_ID: Final[int] = 0
STORED_AUDIO: Final[tuple[str, str]] = (APPROXIMATION, APPROXIMATIONS_DATA)


def _without_the_stored_audio(data: SerializedData) -> SerializedData:
    """The payload with the rendered audio let go of.

    A reconstruction renders its channels from the instructions it stores, so the waveform a 2.1
    file carried beside them describes nothing the document does not already say. Letting it go
    first is also what keeps the rest of the step cheap: the audio is nearly the whole of such a
    file, and every later transform would otherwise carry it along.
    """
    return {key: value for key, value in data.items() if key not in STORED_AUDIO}


def _streams_named_by_channel(data: SerializedData) -> SerializedData:
    """The payload with each stored stream named by the channel it plays.

    Data version 2.1 keyed a stream by ``generator_name``; a channel is what the reconstruction
    calls it now.
    """
    streams = data.get(INSTRUCTIONS_DATA)
    if not isinstance(streams, list):
        return data

    updated = dict(data)
    updated[INSTRUCTIONS_DATA] = [
        renamed(stream, GENERATOR_NAME, CHANNEL_NAME) if isinstance(stream, dict) else stream for stream in streams
    ]
    return updated


def _stamped_embedded_config(data: SerializedData) -> SerializedData:
    """The payload whose embedded configuration states the version its shape now matches.

    A reconstruction carries the configuration it was built under, and that configuration carries
    metadata of its own. The load contract reads every metadata it meets, so the embedded one is
    stamped alongside the outer.
    """
    config = data.get(CONFIG)
    if not isinstance(config, dict):
        return data

    metadata = config.get(METADATA)
    if not isinstance(metadata, dict) or not isinstance(metadata.get(RECONSTRUCTION_DATA_VERSION), str):
        return data

    updated = dict(data)
    updated[CONFIG] = {
        **config,
        METADATA: {**metadata, RECONSTRUCTION_DATA_VERSION: TARGET_DATA_VERSION},
    }
    return updated


def _with_the_stems_record(data: SerializedData) -> SerializedData:
    """The payload carrying the record of the one recording a 2.1 conversion answered to.

    A file written before the record states its channels and its drive in the configuration, and
    names the recording it was built from beside them, so the record is read from those: one entry
    covering every channel the run handed out, driven as it stored, holding every frame that
    sounds, and naming the file it read.
    """
    updated = dict(data)
    channels = _stored_channels(data)
    drive = _stored_drive(data)
    updated[STEMS_DATA] = {
        CONFIG: {
            ENTRIES: [
                {
                    ID: SINGLE_STEM_ID,
                    SETTINGS: {
                        CHANNELS: channels,
                        BENDS: [],
                        DRIVES: {channel: drive for channel in channels},
                        CHANNEL_CAP: ALL_STEMS_CHANNEL_CAP,
                    },
                }
            ],
            HIERARCHY: {LEVELS: [[SINGLE_STEM_ID]], MODE: str(DEFAULT_STEMS_HIERARCHY_MODE)},
        },
        SOURCES: _recorded_sources(data),
        ASSIGNMENTS: _frame_owners(data),
    }
    return updated


def _stored_channels(data: SerializedData) -> List[Any]:
    """The channels the run handed out, which a 2.1 file states in its configuration."""
    config = data.get(CONFIG)
    generation = config.get(GENERATION, {}) if isinstance(config, dict) else {}
    channels = generation.get(GENERATORS) if isinstance(generation, dict) else None
    return list(channels) if isinstance(channels, list) else []


def _stored_drive(data: SerializedData) -> float:
    """The level the run played its channels at, held within the bounds a recording allows.

    A build before the setting was renamed stored it as ``mixer``, and one that stated it nowhere
    played at unit drive.
    """
    config = data.get(CONFIG)
    generation = config.get(GENERATION, {}) if isinstance(config, dict) else {}
    stored = generation.get(DRIVE, generation.get(MIXER)) if isinstance(generation, dict) else None
    if not isinstance(stored, (int, float)):
        return UNIT_DRIVE

    return min(max(float(stored), MIN_DRIVE), MAX_DRIVE)


def _recorded_sources(data: SerializedData) -> List[SerializedData]:
    """Where the one recording came from, named after the file the conversion read.

    A document detached from its origin names no file, which a project carrying a reconstruction
    stores, so such a payload records no source at all.
    """
    stored = data.get(AUDIO_FILEPATH)
    if not isinstance(stored, str) or not stored:
        return []

    return [{STEM_ID: SINGLE_STEM_ID, NAME: Path(stored).stem, PATH: stored}]


def _frame_owners(data: SerializedData) -> List[SerializedData]:
    """Per channel, the recording holding each frame: the one entry where it sounds, rest where not.

    Rest and silence name the same frames, so the owners are read from the stream itself rather
    than assumed, which is what makes the record answer for the document it describes.
    """
    streams = data.get(INSTRUCTIONS_DATA)
    if not isinstance(streams, list):
        return []

    return [
        {
            CHANNEL_NAME: stream.get(CHANNEL_NAME, stream.get(GENERATOR_NAME)),
            STEM_IDS: [SINGLE_STEM_ID if _sounds(frame) else RESTING_STEM_ID for frame in stream[INSTRUCTIONS]],
        }
        for stream in streams
        if isinstance(stream, dict) and isinstance(stream.get(INSTRUCTIONS), list) and stream[INSTRUCTIONS]
    ]


def _sounds(frame: Any) -> bool:
    """Whether one stored frame sounds, read from the instruction the stream holds for it.

    A stream stores each frame as its instruction class beside the instruction itself, which the
    payload tags and nests, so the flag every instruction carries is read from that nesting.
    """
    if not isinstance(frame, dict):
        return False

    instruction = frame.get(INSTRUCTION)
    if not isinstance(instruction, dict):
        return False

    stored = instruction.get(UNION_DATA)
    return bool(stored.get(ON)) if isinstance(stored, dict) else False


def update(data: SerializedData) -> SerializedData:
    """Reads a reconstruction the last release wrote as the document this build describes.

    Data version 2.1 stored the rendered audio beside the instructions, keyed each stream by
    ``generator_name``, and stated in its configuration which channels a run handed out, how hard
    it drove them, and the recording it was built from. Data version 2.2 renders its audio from the
    instructions it keeps, names each stream by its channel, and carries the record of the
    recordings behind its frames: the recording's own settings, where it was read from, and the
    frame-by-frame account of what it holds, where a silent frame answers to rest.
    """
    updated = _without_the_stored_audio(data)
    updated = _streams_named_by_channel(updated)
    updated = _stamped_embedded_config(updated)
    return _with_the_stems_record(updated)


V2_2: Final[VersionUpdate] = VersionUpdate(
    kind=ObjectKind.RECONSTRUCTION,
    base=Version.model_validate(SOURCE_DATA_VERSION),
    target=Version.model_validate(TARGET_DATA_VERSION),
    apply=update,
)
