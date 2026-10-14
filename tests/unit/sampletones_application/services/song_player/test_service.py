from typing import Final, List

import pytest

from sampletones_application.services.song_player.result import (
    SongPlaybackEnded,
    SongPlayerResult,
    SongPositionUpdate,
)
from sampletones_application.services.song_player.service import SongPlayerService
from sampletones_application.services.song_player.source import SongSource
from sampletones_core.audio.output import EndCause, Ending
from sampletones_core.project.song_position import SongPosition
from sampletones_shared.exceptions import NoOutputDeviceError
from tests.suite.audio.output import FakeAudioOutput
from tests.unit.sampletones_application.services.song_player.ramp_song import RampSong

OUTPUT_PRIORITY: Final[int] = 1
MASTER_GAIN: Final[float] = 0.5
ROW: Final[SongPosition] = SongPosition(order_position=1, row_index=3)
DEVICE_FAILURE: Final[str] = "The device failed"


@pytest.fixture
def output() -> FakeAudioOutput:
    return FakeAudioOutput()


@pytest.fixture
def service(output: FakeAudioOutput) -> SongPlayerService:
    return SongPlayerService(
        output,
        RampSong([0, 1], rows=4).factory,
        should_loop=lambda: False,
        master_gain=lambda: MASTER_GAIN,
        output_priority=OUTPUT_PRIORITY,
    )


@pytest.fixture
def results(service: SongPlayerService) -> List[SongPlayerResult]:
    heard: List[SongPlayerResult] = []
    service.subscribe(heard.append)
    return heard


def _start(service: SongPlayerService) -> None:
    service.start(order_position=0, row_index=0)


class TestStart:
    """A start claims the output at the song's rank with its master gain, and a declined claim starts nothing."""

    def test_a_start_holds_the_output_at_the_songs_rank(
        self, service: SongPlayerService, output: FakeAudioOutput
    ) -> None:
        _start(service)

        assert service.alive
        assert service.is_playing
        assert output.claim(output.latest).rank == OUTPUT_PRIORITY
        assert output.latest.gain() == MASTER_GAIN
        assert isinstance(output.claim(output.latest).source, SongSource)

    def test_a_declined_start_leaves_the_song_idle(self, service: SongPlayerService, output: FakeAudioOutput) -> None:
        output.declining = True

        _start(service)

        assert not service.alive

    def test_a_start_with_no_device_raises_the_refusal(
        self, service: SongPlayerService, output: FakeAudioOutput
    ) -> None:
        output.refusal = NoOutputDeviceError("no device")

        with pytest.raises(NoOutputDeviceError):
            _start(service)

        assert not service.alive

    def test_a_start_over_the_song_stops_the_one_playing(
        self,
        service: SongPlayerService,
        output: FakeAudioOutput,
    ) -> None:
        _start(service)
        first = output.latest

        _start(service)

        assert output.claim(first).stopped
        assert output.latest is not first
        assert service.alive


class TestTransport:
    """Pause and resume hold the song where it stands, and a stop lets it go."""

    def test_a_paused_song_stays_engaged(self, service: SongPlayerService) -> None:
        _start(service)

        service.pause()

        assert service.is_paused
        assert not service.is_playing
        assert service.alive

    def test_a_resumed_song_plays(self, service: SongPlayerService) -> None:
        _start(service)
        service.pause()

        service.resume()

        assert service.is_playing

    def test_a_stopped_song_is_idle_and_its_end_report_reaches_nobody(
        self,
        service: SongPlayerService,
        output: FakeAudioOutput,
        results: List[SongPlayerResult],
    ) -> None:
        _start(service)
        playback = output.latest

        service.stop()
        output.end(playback, Ending.of(EndCause.STOPPED))

        assert not service.alive
        assert output.claim(playback).stopped
        assert results == []

    def test_a_seek_of_an_idle_song_moves_nothing(self, service: SongPlayerService, output: FakeAudioOutput) -> None:
        service.seek(1)
        service.relocate(1)

        assert output.playbacks == []


class TestReports:
    """The subscribers hear every row of the song held, and its one end report."""

    def test_a_row_of_the_held_song_reaches_the_subscribers(
        self,
        service: SongPlayerService,
        output: FakeAudioOutput,
        results: List[SongPlayerResult],
    ) -> None:
        _start(service)

        output.report(output.latest, ROW)

        assert results == [SongPositionUpdate(position=ROW)]

    def test_a_row_of_a_song_let_go_reaches_nobody(
        self,
        service: SongPlayerService,
        output: FakeAudioOutput,
        results: List[SongPlayerResult],
    ) -> None:
        _start(service)
        older = output.latest
        _start(service)

        output.report(older, ROW)

        assert results == []

    def test_the_end_of_the_held_song_reaches_the_subscribers_once_the_song_is_idle(
        self,
        service: SongPlayerService,
        output: FakeAudioOutput,
    ) -> None:
        heard: List[bool] = []
        service.subscribe(lambda _result: heard.append(service.alive))
        _start(service)

        output.end(output.latest, Ending.of(EndCause.TAKEN))

        assert heard == [False]

    def test_a_failure_reaches_the_subscribers_with_its_error(
        self,
        service: SongPlayerService,
        output: FakeAudioOutput,
        results: List[SongPlayerResult],
    ) -> None:
        _start(service)
        failure = OSError(DEVICE_FAILURE)

        output.end(output.latest, Ending.failure(failure))

        assert results == [SongPlaybackEnded(ending=Ending.failure(failure))]
