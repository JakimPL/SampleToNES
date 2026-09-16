from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, Sequence, Tuple

import numpy as np

from sampletones_core.constants.enums import ChannelName
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
SILENCE_SCORE: Final[float] = 20.0


@dataclass(frozen=True)
class Probe:
    item: str
    category: str
    channels: Tuple[ChannelName, ...]


ITEMS: Final[Tuple[Probe, ...]] = (
    Probe(item="tone-a", category="tone", channels=(ChannelName.TRIANGLE,)),
    Probe(item="mix-a", category="mix", channels=(ChannelName.TRIANGLE, ChannelName.NOISE)),
    Probe(
        item="chord-a",
        category="polyphony",
        channels=(ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE),
    ),
)


def channel_audio(channel: ChannelName) -> np.ndarray:
    """A tone of the channel's own pitch, so a part of a render is told from another by ear."""
    steps = np.arange(CLIP_LENGTH, dtype=np.float32)
    return np.float32(0.1 * (1 + list(ChannelName).index(channel))) * np.sin(steps / SAMPLE_RATE)


def write_run(directory: Path, variants: Sequence[str], offset: float) -> Path:
    """A calibration run of a few items, written exactly as a measured run writes one."""
    for position, probe in enumerate(ITEMS):
        write_recording(directory, probe.item, channel_audio(ChannelName.TRIANGLE), SAMPLE_RATE)
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
                    category=probe.category,
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
