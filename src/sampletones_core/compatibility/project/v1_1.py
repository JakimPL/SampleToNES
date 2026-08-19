from typing import Final

from sampletones_core.compatibility.fields import (
    CHANNEL_NAME,
    CHANNELS,
    COMMAND,
    GENERATOR,
    GENERATOR_NAME,
    PATTERNS,
    ROWS,
    SONG,
)
from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.update import VersionUpdate
from sampletones_shared.deployment.version import Version
from sampletones_shared.types.data import SerializedData


def update(data: SerializedData) -> SerializedData:
    """Names each channel pool and row command by its channel.

    Project format 1.0 stored a channel pool's channel under ``generator`` and a
    row instrument's channel under ``generator_name``. Project format 1.1 names
    both ``channel_name``.
    """
    updated = dict(data)
    song = data.get(SONG)
    if not isinstance(song, dict):
        return updated

    channels = song.get(CHANNELS)
    if not isinstance(channels, dict):
        return updated

    renamed_channels = {
        name: (
            _renamed_pool(channel)
            if isinstance(
                channel,
                dict,
            )
            else channel
        )
        for name, channel in channels.items()
    }
    updated["song"] = {**song, CHANNELS: renamed_channels}

    return updated


def _renamed_pool(channel: SerializedData) -> SerializedData:
    renamed = dict(channel)
    if GENERATOR in renamed:
        renamed[CHANNEL_NAME] = renamed.pop(GENERATOR)

    patterns = channel.get(PATTERNS)
    if isinstance(patterns, dict):
        renamed[PATTERNS] = {
            index: (
                _renamed_pattern(pattern)
                if isinstance(
                    pattern,
                    dict,
                )
                else pattern
            )
            for index, pattern in patterns.items()
        }

    return renamed


def _renamed_pattern(pattern: SerializedData) -> SerializedData:
    rows = pattern.get(ROWS)
    if not isinstance(rows, dict):
        return pattern

    return {
        **pattern,
        ROWS: {
            index: (
                _renamed_row(row)
                if isinstance(
                    row,
                    dict,
                )
                else row
            )
            for index, row in rows.items()
        },
    }


def _renamed_row(row: SerializedData) -> SerializedData:
    command = row.get(COMMAND)
    if not isinstance(command, dict) or GENERATOR_NAME not in command:
        return row

    renamed_command = dict(command)
    renamed_command[CHANNEL_NAME] = renamed_command.pop(GENERATOR_NAME)

    return {**row, COMMAND: renamed_command}


V1_1: Final[VersionUpdate] = VersionUpdate(
    kind=ObjectKind.PROJECT,
    base=Version.model_validate("1.0"),
    target=Version.model_validate("1.1"),
    apply=update,
)
