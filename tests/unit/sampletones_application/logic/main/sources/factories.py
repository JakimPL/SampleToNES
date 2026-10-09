from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from sampletones_application.logic.main.sources.folder import Folder
from sampletones_application.logic.main.sources.recording import Recording
from sampletones_core.constants.algorithm import ALL_STEMS_CHANNEL_CAP
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


def settings(
    channels: Sequence[ChannelName] = (ChannelName.PULSE1,),
    bends: Sequence[ChannelName] = (),
    drives: Optional[Mapping[ChannelName, float]] = None,
    channel_cap: int = ALL_STEMS_CHANNEL_CAP,
) -> StemSettings:
    return StemSettings(
        channels=list(channels),
        bends=list(bends),
        drives=dict(drives or {}),
        channel_cap=channel_cap,
    )


def recording(
    path: str,
    channels: Sequence[ChannelName] = (ChannelName.PULSE1,),
    bends: Sequence[ChannelName] = (),
    drives: Optional[Mapping[ChannelName, float]] = None,
    channel_cap: int = ALL_STEMS_CHANNEL_CAP,
) -> Recording:
    return Recording(path=Path(path), settings=settings(channels, bends, drives, channel_cap))


def folder(root: str, recordings: Iterable[Recording]) -> Folder:
    return Folder(root=Path(root), recordings=tuple(recordings))
