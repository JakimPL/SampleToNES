from dataclasses import dataclass

from sampletones_core.project.song_position import SongPosition


@dataclass(frozen=True)
class SongPositionUpdate:
    position: SongPosition


@dataclass(frozen=True)
class SongPlaybackStopped:
    pass


@dataclass(frozen=True)
class SongPlaybackError:
    error: Exception


SongPlayerResult = SongPositionUpdate | SongPlaybackStopped | SongPlaybackError
