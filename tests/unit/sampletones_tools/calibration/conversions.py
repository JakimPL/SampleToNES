from typing import List, Optional, Sequence

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import rendered_mix
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_shared.types.path import Pathlike
from sampletones_tools.calibration.corpus.families import Family
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.referee.panel import RefereePanel
from sampletones_tools.calibration.referee.protocol import Judgment
from sampletones_tools.corpus.written import NO_RECORDINGS, WRITTEN_COEFFICIENT, WRITTEN_SCALE, written_reconstruction


class WrittenReconstructor:
    """A reconstructor answering every path with the same written frames, noting each path it converts."""

    def __init__(self) -> None:
        self.converted: List[Pathlike] = []
        self.reconstruction = written_reconstruction(
            {ChannelName.PULSE1: [PulseInstruction(on=True, pitch=69, volume=12, duty_cycle=2)] * 4},
            coefficient=WRITTEN_COEFFICIENT,
            scale=WRITTEN_SCALE,
            audio_filepath=NO_RECORDINGS,
        )

    def __call__(self, path: Pathlike) -> Optional[Reconstruction]:
        self.converted.append(path)
        return self.reconstruction

    def reconstruct(self, paths: Sequence[Pathlike], stems_config: StemsConfig) -> Optional[Reconstruction]:
        self.converted.extend(paths)
        return self.reconstruction

    def load_audio(self, paths: Sequence[Pathlike]) -> np.ndarray:
        return np.asarray(rendered_mix(self.reconstruction), dtype=np.float64)


class StubReferee:
    """A referee scoring every render alike, so a conversion leaves one row per sound."""

    @property
    def name(self) -> str:
        return "stub"

    def judge(self, reference: np.ndarray, estimate: np.ndarray) -> Judgment:
        return Judgment(score=1.0, components={})


def item_named(name: str, *, listed: bool) -> CorpusItem:
    """A note-family sound of no audio of its own, the written reconstructor answering for it."""
    return CorpusItem(
        name=name,
        family=Family.NOTES,
        category="notes-pulse",
        listed=listed,
        audio=np.zeros(1),
        truth=None,
        channels=None,
        stems=None,
    )


def stub_panel() -> RefereePanel:
    """A panel of the stub referee alone."""
    return RefereePanel(audio=(StubReferee(),), truth=(), conversion=())
