from dataclasses import dataclass
from enum import Enum
from typing import Dict, Final, Sequence, Set, Tuple

from sampletones_core.audio.output.lifecycle import StreamAction, StreamLifecycle, StreamPhase
from tests.suite.words import words

LONGEST: Final[int] = 6
STEADY_STEPS: Final[int] = 4


class Event(Enum):
    """Everything the stream's lifecycle can be told: the writer's outcomes and the render thread's requests."""

    OPENED = "opened"
    WRITE_FAILED = "write_failed"
    CLOSED = "closed"
    CLAIMED = "claimed"
    RECONFIGURE = "reconfigure"
    RECONFIGURED = "reconfigured"
    CLOSE = "close"


@dataclass(frozen=True)
class Demand:
    """What the playbacks present ask of the stream: to hold the output, to sound, and to play a tail out."""

    wanted: bool
    mixing: bool
    tail: bool


PHASE_AFTER: Final[Dict[Tuple[StreamPhase, Event], StreamPhase]] = {
    (StreamPhase.CLOSED, Event.OPENED): StreamPhase.OPEN,
    (StreamPhase.OPEN, Event.WRITE_FAILED): StreamPhase.BROKEN,
    (StreamPhase.OPEN, Event.CLOSED): StreamPhase.CLOSED,
    (StreamPhase.BROKEN, Event.CLOSED): StreamPhase.CLOSED,
}
DEMANDS: Final[Tuple[Demand, ...]] = tuple(
    Demand(wanted=wanted, mixing=mixing, tail=tail)
    for wanted in (False, True)
    for mixing in ((False, True) if wanted else (False,))
    for tail in (False, True)
)
STEADY: Final[Set[StreamAction]] = {StreamAction.WRITE, StreamAction.WAIT, StreamAction.EXIT}
SOUNDING: Final[Demand] = Demand(wanted=True, mixing=True, tail=False)
HELD: Final[Demand] = Demand(wanted=True, mixing=False, tail=False)
FINISHED: Final[Demand] = Demand(wanted=False, mixing=False, tail=True)
SILENT: Final[Demand] = Demand(wanted=False, mixing=False, tail=False)


@dataclass(frozen=True)
class State:
    phase: StreamPhase
    closing: bool
    reconfiguring: bool
    cutting: bool


def _apply(lifecycle: StreamLifecycle, event: Event) -> None:
    match event:
        case Event.OPENED:
            lifecycle.opened()
        case Event.WRITE_FAILED:
            lifecycle.write_failed()
        case Event.CLOSED:
            lifecycle.closed()
        case Event.CLAIMED:
            lifecycle.claimed()
        case Event.RECONFIGURE:
            lifecycle.request_reconfigure()
        case Event.RECONFIGURED:
            lifecycle.reconfigured()
        case Event.CLOSE:
            lifecycle.request_close()


def _run(word: Sequence[Event]) -> StreamLifecycle:
    lifecycle = StreamLifecycle()
    for event in word:
        _apply(lifecycle, event)

    return lifecycle


def _next(lifecycle: StreamLifecycle, demand: Demand) -> StreamAction:
    return lifecycle.next_action(wanted=demand.wanted, mixing=demand.mixing, tail=demand.tail)


def _reference(word: Sequence[Event]) -> State:
    """Where the stream stands after ``word``: the phase by the transition table, the requests by the last word on them.

    A close is final and outranks a reconfiguration, which the next settings taken end. A claim cuts the stream
    open at that moment, until it closes.
    """
    phase = StreamPhase.CLOSED
    cutting = False
    for event in word:
        if event is Event.CLAIMED and phase is StreamPhase.OPEN:
            cutting = True
        elif event is Event.CLOSED:
            cutting = False

        phase = PHASE_AFTER.get((phase, event), phase)

    closing = Event.CLOSE in word
    requests = [event for event in word if event in (Event.RECONFIGURE, Event.RECONFIGURED)]
    reconfiguring = not closing and bool(requests) and requests[-1] is Event.RECONFIGURE
    return State(phase=phase, closing=closing, reconfiguring=reconfiguring, cutting=cutting)


def _permitted(action: StreamAction, state: State, demand: Demand) -> bool:
    """Whether the contract lets the writer take ``action`` in ``state``.

    A stream opens only from closed and only to sound, and a claim plays on a stream of its own. A close and a
    reconfiguration outrank playing. A finished sound alone drains its tail, a broken stream is let go before
    anything else, and the writer ends once nothing is left to play.
    """
    settled = not state.closing and not state.reconfiguring
    playing = settled and not state.cutting
    phase = state.phase
    match action:
        case StreamAction.OPEN:
            return phase is StreamPhase.CLOSED and demand.wanted and settled
        case StreamAction.WRITE:
            return phase is StreamPhase.OPEN and demand.mixing and playing
        case StreamAction.WAIT:
            return phase is StreamPhase.OPEN and demand.wanted and not demand.mixing and playing
        case StreamAction.DRAIN:
            return phase is StreamPhase.OPEN and not demand.wanted and demand.tail and playing
        case StreamAction.ABORT:
            return phase is StreamPhase.BROKEN or (
                phase is StreamPhase.OPEN and (not playing or (not demand.wanted and not demand.tail))
            )
        case StreamAction.RECONFIGURE:
            return phase is StreamPhase.CLOSED and state.reconfiguring and not state.closing
        case StreamAction.EXIT:
            return phase is StreamPhase.CLOSED and (state.closing or (settled and not demand.wanted))


def _follow(lifecycle: StreamLifecycle, action: StreamAction) -> None:
    """Runs ``action`` the way a writer whose every device call succeeds does."""
    match action:
        case StreamAction.OPEN:
            lifecycle.opened()
        case StreamAction.DRAIN | StreamAction.ABORT:
            lifecycle.closed()
        case StreamAction.RECONFIGURE:
            lifecycle.reconfigured()
        case StreamAction.WRITE | StreamAction.WAIT | StreamAction.EXIT:
            return


def _steps(lifecycle: StreamLifecycle, demand: Demand) -> Tuple[StreamAction, ...]:
    actions = []
    for _ in range(STEADY_STEPS):
        actions.append(_next(lifecycle, demand))
        _follow(lifecycle, actions[-1])

    return tuple(actions)


class TestModel:
    """The stream answers every word of events up to ``LONGEST`` as the transition table and the rules say."""

    def test_every_word_matches_the_reference(self) -> None:
        for word in words(tuple(Event), longest=LONGEST):
            lifecycle = _run(word)

            assert State(lifecycle.phase, lifecycle.closing, lifecycle.reconfiguring, lifecycle.cutting) == (
                _reference(word)
            ), word

    def test_every_state_permits_exactly_the_action_decided(self) -> None:
        for word in words(tuple(Event), longest=LONGEST):
            lifecycle = _run(word)
            state = _reference(word)
            for demand in DEMANDS:
                action = _next(lifecycle, demand)
                permitted = {candidate for candidate in StreamAction if _permitted(candidate, state, demand)}

                assert permitted == {action}, (word, demand)

    def test_every_state_settles_within_a_few_steps(self) -> None:
        for word in words(tuple(Event), longest=LONGEST):
            for demand in DEMANDS:
                actions = _steps(_run(word), demand)

                assert actions[-1] in STEADY, (word, demand, actions)


class TestOneStream:
    """Rule 2: the device holds one stream at most, opened only from closed."""

    def test_a_wanted_closed_stream_opens(self) -> None:
        assert _next(StreamLifecycle(), SOUNDING) is StreamAction.OPEN

    def test_an_open_stream_writes_and_opens_no_second(self) -> None:
        lifecycle = _run((Event.OPENED, Event.OPENED))

        assert lifecycle.phase is StreamPhase.OPEN
        assert _next(lifecycle, SOUNDING) is StreamAction.WRITE

    def test_a_broken_stream_is_let_go_before_it_opens_again(self) -> None:
        lifecycle = _run((Event.OPENED, Event.WRITE_FAILED))

        assert _next(lifecycle, SOUNDING) is StreamAction.ABORT


class TestClaims:
    """Rule 6: a claim made while a stream plays cuts it, and the new sound opens a stream of its own."""

    def test_a_claim_over_an_open_stream_cuts_it_and_opens_the_next(self) -> None:
        assert _steps(_run((Event.OPENED, Event.CLAIMED)), SOUNDING) == (
            StreamAction.ABORT,
            StreamAction.OPEN,
            StreamAction.WRITE,
            StreamAction.WRITE,
        )

    def test_a_claim_while_the_stream_is_closed_opens_one_stream(self) -> None:
        assert _steps(_run((Event.CLAIMED,)), SOUNDING) == (StreamAction.OPEN,) + (StreamAction.WRITE,) * 3

    def test_a_claim_cuts_a_finished_tail(self) -> None:
        assert _next(_run((Event.OPENED, Event.CLAIMED)), FINISHED) is StreamAction.ABORT


class TestHold:
    """A stream whose every playback is paused stays open and takes nothing, and the writer ends once idle."""

    def test_a_paused_playback_holds_the_stream_open_and_writes_nothing(self) -> None:
        assert _steps(_run((Event.OPENED,)), HELD) == (StreamAction.WAIT,) * STEADY_STEPS

    def test_a_writer_with_nothing_to_play_ends(self) -> None:
        assert _next(StreamLifecycle(), SILENT) is StreamAction.EXIT

    def test_a_writer_ends_once_a_stopped_sound_is_cut(self) -> None:
        assert _steps(_run((Event.OPENED,)), SILENT)[:2] == (StreamAction.ABORT, StreamAction.EXIT)


class TestEnds:
    """Rule 6: a sound that finished alone plays its tail out, and any other end cuts it."""

    def test_a_finished_sound_drains(self) -> None:
        assert _next(_run((Event.OPENED,)), FINISHED) is StreamAction.DRAIN

    def test_a_stopped_sound_is_cut(self) -> None:
        assert _next(_run((Event.OPENED,)), SILENT) is StreamAction.ABORT

    def test_a_close_cuts_a_finished_tail(self) -> None:
        assert _next(_run((Event.OPENED, Event.CLOSE)), FINISHED) is StreamAction.ABORT


class TestRequests:
    """A reconfiguration lets the stream go and takes settings before the next opens, and a close is final."""

    def test_a_reconfiguration_takes_settings_before_the_next_stream_opens(self) -> None:
        assert _steps(_run((Event.OPENED, Event.RECONFIGURE)), SOUNDING) == (
            StreamAction.ABORT,
            StreamAction.RECONFIGURE,
            StreamAction.OPEN,
            StreamAction.WRITE,
        )

    def test_a_reconfiguration_with_nothing_playing_takes_settings_and_ends(self) -> None:
        assert _steps(_run((Event.RECONFIGURE,)), SILENT)[:2] == (StreamAction.RECONFIGURE, StreamAction.EXIT)

    def test_a_reconfiguration_after_a_close_is_refused(self) -> None:
        lifecycle = _run((Event.CLOSE,))

        assert not lifecycle.request_reconfigure()
        assert _next(lifecycle, SOUNDING) is StreamAction.EXIT
