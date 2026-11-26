from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, Sequence, Tuple

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_tools.calibration.config.level import VariantLevel
from sampletones_tools.calibration.digest import sha256_digest
from sampletones_tools.calibration.fingerprint import RunFingerprint, write_fingerprint
from sampletones_tools.calibration.layout import ORACLE_LABEL
from sampletones_tools.calibration.oracle.reading import HIGHEST_READING, LOWEST_READING
from sampletones_tools.calibration.renders import (
    RenderRecord,
    write_channel_renders,
    write_recording,
    write_render,
)

SAMPLE_RATE: Final[int] = 22050
CLIP_LENGTH: Final[int] = SAMPLE_RATE // 8
REFEREE: Final[str] = "mr-auditory-dB"
SECOND_REFEREE: Final[str] = "mr-loudness-dB"
SOURCE: Final[str] = "probe-source"
SILENCE_SCORE: Final[float] = 20.0
ORACLE_SCORE: Final[float] = 2.0
ORACLE_LOWEST: Final[float] = 1.5
ORACLE_HIGHEST: Final[float] = 2.5


@dataclass(frozen=True)
class Probe:
    item: str
    family: str
    category: str
    channels: Tuple[ChannelName, ...]


ITEMS: Final[Tuple[Probe, ...]] = (
    Probe(item="tone-a", family="sines", category="tone", channels=(ChannelName.TRIANGLE,)),
    Probe(item="mix-a", family="composites", category="mix", channels=(ChannelName.TRIANGLE, ChannelName.NOISE)),
    Probe(
        item="chord-a",
        family="composites",
        category="polyphony",
        channels=(ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE),
    ),
)


def channel_audio(channel: ChannelName) -> np.ndarray:
    """A tone of the channel's own pitch, so a part of a render is told from another by ear."""
    steps = np.arange(CLIP_LENGTH, dtype=np.float32)
    return np.float32(0.1 * (1 + list(ChannelName).index(channel))) * np.sin(steps / SAMPLE_RATE)


def write_run(directory: Path, variants: Sequence[str], offset: float) -> Path:
    """A finished calibration run of a few items: its fingerprint naming ``variants`` in order, then its renders."""
    write_fingerprint(directory, probe_fingerprint(variants))
    return write_renders(directory, variants, offset, level=VariantLevel.DEFAULT)


def probe_fingerprint(variants: Sequence[str]) -> RunFingerprint:
    """A fingerprint of a run measuring the probes under ``variants``, each part held by a digest of its name."""
    return RunFingerprint(
        variants={variant: sha256_digest(variant.encode()) for variant in variants},
        channels=[channel.value for channel in ChannelName.items()],
        items={probe.item: sha256_digest(probe.item.encode()) for probe in ITEMS},
        referees=sha256_digest(REFEREE.encode()),
        source=sha256_digest(SOURCE.encode()),
    )


def write_renders(directory: Path, variants: Sequence[str], offset: float, *, level: VariantLevel) -> Path:
    """The renders, records and recordings a run of a few items converts, written as a conversion writes them."""
    for position, probe in enumerate(ITEMS):
        write_recording(directory, level, probe.item, channel_audio(ChannelName.TRIANGLE), SAMPLE_RATE)
        for variant in variants:
            approximations: Dict[ChannelName, np.ndarray] = {
                channel: channel_audio(channel) for channel in probe.channels
            }
            write_render(
                directory,
                RenderRecord(
                    variant=variant,
                    item=probe.item,
                    position=position,
                    family=probe.family,
                    category=probe.category,
                    level=level,
                    timelines={channel.value: "1010" for channel in probe.channels},
                    judgments={
                        REFEREE: {"score": 10.0 + position + offset},
                        SECOND_REFEREE: {"score": 8.0 + position},
                    },
                    silence={REFEREE: SILENCE_SCORE, SECOND_REFEREE: SILENCE_SCORE},
                ),
                sum(approximations.values()),
                SAMPLE_RATE,
            )
            write_channel_renders(directory, variant, probe.item, approximations, SAMPLE_RATE)

    return directory


def write_oracle(directory: Path, items: Sequence[str]) -> None:
    """The oracle's renders, records and recordings of the probes named ``items``, written as the oracle writes them."""
    for position, probe in enumerate(ITEMS):
        if probe.item not in items:
            continue

        write_recording(directory, VariantLevel.TRUE, probe.item, channel_audio(ChannelName.TRIANGLE), SAMPLE_RATE)
        approximations = {channel: channel_audio(channel) for channel in probe.channels}
        write_render(
            directory,
            RenderRecord(
                variant=ORACLE_LABEL,
                item=probe.item,
                position=position,
                family=probe.family,
                category=probe.category,
                level=VariantLevel.TRUE,
                timelines={channel.value: "1111" for channel in probe.channels},
                judgments={
                    REFEREE: {"score": ORACLE_SCORE, LOWEST_READING: ORACLE_LOWEST, HIGHEST_READING: ORACLE_HIGHEST},
                    SECOND_REFEREE: {
                        "score": ORACLE_SCORE,
                        LOWEST_READING: ORACLE_LOWEST,
                        HIGHEST_READING: ORACLE_HIGHEST,
                    },
                },
                silence={REFEREE: SILENCE_SCORE, SECOND_REFEREE: SILENCE_SCORE},
            ),
            sum(approximations.values()),
            SAMPLE_RATE,
        )
        write_channel_renders(directory, ORACLE_LABEL, probe.item, approximations, SAMPLE_RATE)
