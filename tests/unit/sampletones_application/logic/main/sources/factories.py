from pathlib import Path
from typing import Iterable, Sequence

from sampletones_application.logic.main.sources.folder import Folder
from sampletones_application.logic.main.sources.recording import Recording
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


def settings(
    channels: Sequence[ChannelName] = (ChannelName.PULSE1,),
    bends: Sequence[ChannelName] = (),
) -> StemSettings:
    return StemSettings(channels=list(channels), bends=list(bends))


def recording(
    path: str,
    channels: Sequence[ChannelName] = (ChannelName.PULSE1,),
    bends: Sequence[ChannelName] = (),
) -> Recording:
    return Recording(path=Path(path), settings=settings(channels, bends))


def folder(root: str, recordings: Iterable[Recording]) -> Folder:
    return Folder(root=Path(root), recordings=tuple(recordings))
