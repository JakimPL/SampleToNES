import threading
from typing import Final, List, Optional

import numpy as np
import pytest

from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.logic.shared.preview_player import PreviewPlayer
from sampletones_core.audio.output import AudioSource, BufferSource, Ending, Playback, PlaybackListener
from sampletones_core.audio.output.source import ReportT
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE, START_OF_AUDIO
from tests.suite.audio.output import FakeAudioOutput

AUDIO_LENGTH: Final[int] = 100
GATE_SECONDS: Final[float] = 5.0
BLOCKED_SECONDS: Final[float] = 0.1


class Owner:
    """An owner of previews that keeps what it hears."""

    def __init__(self) -> None:
        self.ends: List[Ending] = []

    def positioned(self, _playback: Playback[int], _report: int) -> None:
        return None

    def ended(self, _playback: Playback[int], ending: Ending) -> None:
        self.ends.append(ending)


class GatedOutput(FakeAudioOutput):
    """An output that holds each claim it grants until the case lets it answer, so a stop can arrive meanwhile."""

    def __init__(self) -> None:
        super().__init__()
        self.claimed = threading.Event()
        self.answer = threading.Event()

    def play(
        self,
        source: AudioSource[ReportT],
        *,
        rank: int,
        listener: PlaybackListener[ReportT],
    ) -> Optional[Playback[ReportT]]:
        playback = super().play(source, rank=rank, listener=listener)
        self.claimed.set()
        self.answer.wait(timeout=GATE_SECONDS)
        return playback


def _audio() -> np.ndarray:
    return np.zeros(AUDIO_LENGTH, dtype=np.float32)


def _source() -> BufferSource:
    return BufferSource(_audio(), sample_rate=DEFAULT_SAMPLE_RATE, start=START_OF_AUDIO)


@pytest.fixture
def output() -> FakeAudioOutput:
    return FakeAudioOutput()


@pytest.fixture
def previews(output: FakeAudioOutput) -> PreviewPlayer:
    return PreviewPlayer(output)


class TestStopReachesTheLatestPreview:
    """Stop silences the preview claimed last, whether it plays audio or a source of its own."""

    def test_stop_silences_a_source_played_after_audio(self, previews: PreviewPlayer, output: FakeAudioOutput) -> None:
        owner = Owner()
        audio = previews.play(_audio(), sample_rate=DEFAULT_SAMPLE_RATE, rank=PlaybackPriority.PREVIEW, listener=owner)
        played = previews.play_source(_source(), rank=PlaybackPriority.PREVIEW, listener=owner)
        assert audio is not None and played is not None

        previews.stop()

        assert output.claim(played).stopped
        assert not output.claim(audio).stopped

    def test_a_declined_claim_leaves_stop_on_the_preview_before_it(
        self,
        previews: PreviewPlayer,
        output: FakeAudioOutput,
    ) -> None:
        owner = Owner()
        sounding = previews.play_source(_source(), rank=PlaybackPriority.PREVIEW, listener=owner)
        output.declining = True

        declined = previews.play_source(_source(), rank=PlaybackPriority.PREVIEW, listener=owner)
        previews.stop()

        assert declined is None
        assert sounding is not None and output.claim(sounding).stopped

    def test_a_stop_during_a_claim_reaches_the_preview_claimed(self) -> None:
        output = GatedOutput()
        previews = PreviewPlayer(output)
        claiming = threading.Thread(
            target=previews.play_source,
            args=(_source(),),
            kwargs={"rank": PlaybackPriority.PREVIEW, "listener": Owner()},
        )
        claiming.start()
        assert output.claimed.wait(timeout=GATE_SECONDS)
        stopping = threading.Thread(target=previews.stop)
        stopping.start()
        stopping.join(timeout=BLOCKED_SECONDS)

        output.answer.set()
        claiming.join(timeout=GATE_SECONDS)
        stopping.join(timeout=GATE_SECONDS)

        assert output.claim(output.latest).stopped
