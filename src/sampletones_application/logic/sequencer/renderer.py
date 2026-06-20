from typing import Protocol

import numpy as np

from sampletones_core.project import Project


class SongRenderer(Protocol):
    """Renders a project's song into a single playable mono waveform.

    This is the seam between the sequencer and audio output. An implementation
    walks each channel's ``order`` → ``patterns`` → ``rows``, feeds every active
    row's referenced sample reconstruction instructions (shifted by the row
    ``transpose`` and scaled by ``volume``) through the matching
    :class:`~sampletones_core.generators.generator.Generator`, advancing one
    tracker row every ``speed`` engine ticks at the project ``tempo`` /
    ``nes_frequency``, then mixes the four channels into one buffer.
    """

    def render(self, project: Project) -> np.ndarray: ...


class UnimplementedSongRenderer:
    """Placeholder renderer until the synthesis engine lands.

    Kept as a concrete type so the sequencer can hold a renderer reference and
    fail loudly (rather than silently producing no audio) if play is wired
    before the engine exists.
    """

    def render(self, project: Project) -> np.ndarray:
        raise NotImplementedError("Song rendering is not implemented yet; see SongRenderer.")
