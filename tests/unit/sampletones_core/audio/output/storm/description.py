from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

from tests.suite.audio.timeline import TimelineEvent, Written

from .record import StormRecord
from .source import identity_of


@dataclass
class _Run:
    """Blocks one stream wrote in a row, for the same sounds."""

    stream: int
    sounds: Tuple[int, ...]
    blocks: int
    frames: int

    def line(self) -> str:
        sounds = ", ".join(str(sound) for sound in self.sounds) or "silence"
        return f"stream {self.stream} wrote {self.blocks} blocks ({self.frames} frames) of sound {sounds}"


def describe(record: StormRecord, events: Sequence[TimelineEvent], broken: Sequence[str]) -> str:
    """The seed, every rule the storm broke, what each owner did and what the device was asked, in order."""
    return "\n".join(
        [
            f"The storm seeded {record.seed} broke the output contract:",
            *(f"  {rule}" for rule in broken),
            "",
            "What the owners did, in order:",
            *(f"  {entry.owner}: {entry.operation}: {entry.outcome}" for entry in record.entries),
            "",
            "What the device was asked, in order:",
            *(f"  {line}" for line in timeline_lines(events)),
        ]
    )


def timeline_lines(events: Sequence[TimelineEvent]) -> List[str]:
    """One line for each event the device met, with the writes one stream made in a row for one sound joined."""
    lines: List[str] = []
    run: Optional[_Run] = None
    for event in events:
        if not isinstance(event, Written):
            if run is not None:
                lines.append(run.line())
                run = None

            lines.append(repr(event))
            continue

        sounds = _sounds(event.samples)
        if run is not None and (run.stream, run.sounds) == (event.stream, sounds):
            run.blocks += 1
            run.frames += len(event.samples)
            continue

        if run is not None:
            lines.append(run.line())

        run = _Run(stream=event.stream, sounds=sounds, blocks=1, frames=len(event.samples))

    if run is not None:
        lines.append(run.line())

    return lines


def _sounds(samples: np.ndarray) -> Tuple[int, ...]:
    return tuple(sorted({identity_of(float(level)) for level in np.unique(samples[samples != 0])}))
