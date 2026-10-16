from typing import Final, Sequence, Tuple

from sampletones_core.audio.output.ending import EndCause, Ending
from sampletones_core.audio.output.lifecycle import StreamAction
from tests.unit.sampletones_core.audio.output.session.model import Event, SessionRun, explore
from tests.unit.sampletones_core.audio.output.session.model.events import DEVICE_ERROR

PAIR: Final[int] = 2
TRIO: Final[int] = 3
CONTENTION: Final[Tuple[Event, ...]] = (
    Event.CLAIM_PREVIEW,
    Event.CLAIM_NORMAL,
    Event.STOP,
    Event.STOP_ALL,
    Event.DECIDE,
    Event.SUCCEEDS,
    Event.RUNS_OUT,
    Event.DEVICE_FAILS,
)
OPENING: Final[Tuple[Event, ...]] = (Event.DECIDE, Event.SUCCEEDS)
CUTTING: Final[Tuple[Event, ...]] = (Event.DECIDE, Event.SUCCEEDS)
WRITING: Final[Tuple[Event, ...]] = (Event.DECIDE, Event.SUCCEEDS)
RUNNING_OUT: Final[Tuple[Event, ...]] = (Event.DECIDE, Event.RUNS_OUT)


def _closes_cleanly(run: SessionRun, _word: Sequence[Event]) -> None:
    run.copy().complete()


def _driven(*word: Event) -> SessionRun:
    """A run through ``word`` with two playbacks at most, every answer held to the contract on the way."""
    run = SessionRun(most_claims=PAIR)
    for event in word:
        run.apply(event)

    return run


class TestModel:
    """Every state the core reaches keeps the contract, and from each of them the output closes with every
    playback ended once."""

    def test_every_state_two_playbacks_reach_keeps_the_contract(self) -> None:
        exploration = explore(tuple(Event), most_claims=PAIR, check=_closes_cleanly)

        assert exploration.states > 1

    def test_every_state_three_contending_playbacks_reach_keeps_the_contract(self) -> None:
        exploration = explore(CONTENTION, most_claims=TRIO, check=_closes_cleanly)

        assert exploration.states > 1


class TestClaims:
    """Rule 1: a claim below the holder is declined, and any other takes the output."""

    def test_a_normal_claim_takes_the_output_from_a_preview(self) -> None:
        run = _driven(Event.CLAIM_PREVIEW, Event.CLAIM_NORMAL)

        assert not run.core.is_engaged(0)
        assert run.core.is_engaged(1)

    def test_a_preview_claim_under_a_normal_holder_is_declined(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, Event.CLAIM_PREVIEW)

        assert run.core.is_engaged(0)
        assert run.core.phase_of(1) is None

    def test_a_claim_after_the_close_is_declined(self) -> None:
        run = _driven(Event.CLOSE, Event.CLAIM_NORMAL)

        assert not run.core.is_sounding


class TestStream:
    """Rules 2 and 6: the device holds one stream at most, and a takeover cuts it and opens the next."""

    def test_a_takeover_cuts_the_stream_and_opens_one_of_its_own(self) -> None:
        run = _driven(Event.CLAIM_PREVIEW, *OPENING, *WRITING, Event.CLAIM_NORMAL, *CUTTING, Event.DECIDE)

        assert run.actions == [StreamAction.OPEN, StreamAction.WRITE, StreamAction.ABORT, StreamAction.OPEN]

    def test_a_claim_while_the_stream_opens_plays_on_the_stream_it_opens(self) -> None:
        run = _driven(Event.CLAIM_PREVIEW, Event.DECIDE, Event.CLAIM_NORMAL, Event.SUCCEEDS, Event.DECIDE)

        assert run.actions == [StreamAction.OPEN, StreamAction.WRITE]

    def test_a_stream_a_write_broke_is_let_go_before_another_opens(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, *OPENING, Event.DECIDE, Event.DEVICE_FAILS, Event.CLAIM_NORMAL, Event.DECIDE)

        assert run.actions[-1] is StreamAction.ABORT


class TestEnds:
    """Rules 3 and 6: a finished sound plays its tail out before its report, and a stop cuts it and reports at once."""

    def test_a_finished_sound_reports_once_its_tail_played_out(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, *OPENING, *RUNNING_OUT, Event.DECIDE)
        reports_before_the_drain = list(run.reports)
        run.apply(Event.SUCCEEDS)
        run.apply(Event.DECIDE)

        assert run.actions[-2:] == [StreamAction.DRAIN, StreamAction.EXIT]
        assert reports_before_the_drain == []
        assert [report.ending for report in run.reports] == [Ending.of(EndCause.FINISHED)]

    def test_a_stopped_sound_reports_at_once_and_is_cut(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, *OPENING, *WRITING, Event.STOP, Event.DECIDE)

        assert run.actions[-1] is StreamAction.ABORT
        assert [report.ending for report in run.reports] == [Ending.of(EndCause.STOPPED)]

    def test_a_tail_the_device_fails_to_play_out_reports_the_failure(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, *OPENING, *RUNNING_OUT, Event.DECIDE, Event.DEVICE_FAILS, Event.DECIDE)

        assert [report.ending for report in run.reports] == [Ending.failure(DEVICE_ERROR)]


class TestHold:
    """A paused playback holds the stream open and the device takes nothing, and a writer with nothing left ends."""

    def test_a_paused_playback_writes_nothing(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, *OPENING, *WRITING, Event.PAUSE, Event.DECIDE)

        assert run.actions[-1] is StreamAction.WAIT
        assert run.core.is_engaged(0)

    def test_a_resumed_playback_writes_again(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, *OPENING, Event.PAUSE, Event.DECIDE, Event.RESUME, Event.DECIDE)

        assert run.actions[-2:] == [StreamAction.WAIT, StreamAction.WRITE]

    def test_a_writer_ends_once_nothing_is_left_and_a_claim_starts_the_next(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, *OPENING, *WRITING, Event.STOP, *CUTTING, Event.DECIDE)
        ended = run.writing
        run.apply(Event.CLAIM_NORMAL)
        run.apply(Event.DECIDE)

        assert run.actions[-2:] == [StreamAction.EXIT, StreamAction.OPEN]
        assert not ended


class TestCommands:
    """Rule 4: a command reaches a playback while it plays, and a click as the sound runs out plays on from it."""

    def test_a_command_reaches_a_playing_playback(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, *OPENING)

        assert run.core.command(0)

    def test_a_command_to_an_ended_playback_is_refused(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, *OPENING, Event.STOP)

        assert not run.core.command(0)

    def test_a_command_while_the_last_block_is_written_keeps_the_sound_playing(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, *OPENING, Event.DECIDE, Event.COMMAND, Event.RUNS_OUT, Event.DECIDE)

        assert run.core.is_engaged(0)
        assert run.actions[-1] is StreamAction.WRITE

    def test_a_sound_running_out_with_no_command_waiting_finishes(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, *OPENING, Event.COMMAND, *RUNNING_OUT)

        assert not run.core.is_engaged(0)


class TestPositions:
    """Rule 4: a written block reports the positions of the playbacks it held, and none once they ended."""

    def test_a_written_block_reports_its_playback(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, *OPENING, *WRITING)

        assert run.positions == [0]

    def test_a_block_written_after_a_stop_reports_nothing(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, *OPENING, Event.DECIDE, Event.STOP, Event.SUCCEEDS)

        assert run.positions == []


class TestFailures:
    """Rule 7: a device failure ends every playback holding the output, each told once."""

    def test_a_refused_stream_fails_the_playback_once(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, Event.DECIDE, Event.DEVICE_FAILS, Event.DECIDE, Event.DECIDE)

        assert [report.ending for report in run.reports] == [Ending.failure(DEVICE_ERROR)]


class TestTeardown:
    """Rule 8: a teardown that stops waiting ends every playback at once, and the writer's later turn adds nothing."""

    def test_an_abandoned_output_reports_every_playback_once(self) -> None:
        run = _driven(Event.CLAIM_NORMAL, *OPENING, Event.DECIDE, Event.ABANDON, Event.SUCCEEDS, Event.DECIDE)

        assert [report.ending for report in run.reports] == [Ending.of(EndCause.STOPPED)]
        assert run.positions == []
        assert run.actions[-1] is StreamAction.ABORT
