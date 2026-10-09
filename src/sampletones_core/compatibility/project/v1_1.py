from typing import Final, List

from sampletones_core.compatibility.fields import (
    CHANNELS,
    COMMAND,
    GENERATOR,
    KIND,
    KIND_SAMPLE,
    KIND_STEP,
    LOOP_POINT,
    NAME,
    PATTERNS,
    PITCH,
    ROWS,
    SAMPLE_ID,
    SAMPLES,
    SONG,
    TRANSPOSE,
    VALUE,
    VOICE_ID,
    VOICES,
)
from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.update import VersionUpdate
from sampletones_shared.deployment.version import Version
from sampletones_shared.types.data import SerializedData


def update(data: SerializedData) -> SerializedData:
    """Gathers a project's samples into its voices, names each channel once, and gives each row a pitch.

    Project format 1.0 held the pool under ``samples``, stored a channel pool's channel under
    ``generator``, wrote a row's note command as a sample id beside the channel slice it named,
    wrote a row's pitch as a bare ``transpose`` integer, and let a sample state a tick its frames
    repeated from. Project format 1.1 holds the pool under ``voices``, each record stating the
    ``kind`` of voice it carries; a channel pool names its channel under ``name``; a note command
    names the voice alone, since the channel a voice sounds on is the one whose pattern holds the
    row; a row's ``pitch`` states its ``kind``, a step from the voice's reference or a note the
    channel sounds, so a stored transpose becomes a step; and a sample plays the frames its
    conversion found, which leaves the repeat to the envelopes an instrument writes.
    """
    updated = dict(data)

    samples = data.get(SAMPLES)
    if isinstance(samples, list):
        updated.pop(SAMPLES, None)
        updated[VOICES] = [_updated_sample(sample) if isinstance(sample, dict) else sample for sample in samples]

    song = data.get(SONG)
    if isinstance(song, dict):
        updated[SONG] = _updated_song(song)

    return updated


def _updated_sample(sample: SerializedData) -> SerializedData:
    """A 1.0 sample as a voice record, leaving behind the tick its frames repeated from."""
    record = {KIND: KIND_SAMPLE, **sample}
    record.pop(LOOP_POINT, None)
    return record


def _updated_song(song: SerializedData) -> SerializedData:
    channels = song.get(CHANNELS)
    if not isinstance(channels, dict):
        return song

    return {
        **song,
        CHANNELS: {
            name: _updated_pool(channel) if isinstance(channel, dict) else channel for name, channel in channels.items()
        },
    }


def _updated_pool(channel: SerializedData) -> SerializedData:
    updated = dict(channel)
    if GENERATOR in updated:
        updated[NAME] = updated.pop(GENERATOR)

    patterns = channel.get(PATTERNS)
    if isinstance(patterns, dict):
        updated[PATTERNS] = {
            index: _updated_pattern(pattern) if isinstance(pattern, dict) else pattern
            for index, pattern in patterns.items()
        }

    return updated


def _updated_pattern(pattern: SerializedData) -> SerializedData:
    rows = pattern.get(ROWS)
    if not isinstance(rows, list):
        return pattern

    updated_rows: List[SerializedData] = [_updated_row(row) if isinstance(row, dict) else row for row in rows]
    return {**pattern, ROWS: updated_rows}


def _updated_row(row: SerializedData) -> SerializedData:
    updated = dict(row)
    command = row.get(COMMAND)
    if isinstance(command, dict) and SAMPLE_ID in command:
        updated[COMMAND] = {VOICE_ID: command[SAMPLE_ID]}

    if TRANSPOSE in updated:
        transpose = updated.pop(TRANSPOSE)
        if isinstance(transpose, int):
            updated[PITCH] = {KIND: KIND_STEP, VALUE: transpose}

    return updated


V1_1: Final[VersionUpdate] = VersionUpdate(
    kind=ObjectKind.PROJECT,
    base=Version.model_validate("1.0"),
    target=Version.model_validate("1.1"),
    apply=update,
)
