from dataclasses import dataclass
from enum import Enum
from typing import Dict, Final, List, Optional, Sequence, Tuple, Union

from sampletones_core.audio.output.ending import EndCause, Ending
from sampletones_core.audio.output.lifecycle import PlaybackLifecycle, PlaybackPhase
from tests.suite.words import words

LONGEST: Final[int] = 5


class Event(Enum):
    """Everything a playback's lifecycle can be told, by its owner or by the thread writing to the device."""

    PAUSE = "pause"
    RESUME = "resume"
    COMMAND = "command"
    STOP = "stop"
    DISPLACE = "displace"
    FINISH = "finish"
    FAIL = "fail"
    WRITTEN = "written"
    SETTLE = "settle"


Output = Union[bool, Optional[Ending]]
FAILURES: Final[Tuple[Exception, ...]] = tuple(RuntimeError(f"failure at event {index}") for index in range(LONGEST))
DECIDING: Final[Dict[Event, EndCause]] = {
    Event.STOP: EndCause.STOPPED,
    Event.DISPLACE: EndCause.TAKEN,
    Event.FINISH: EndCause.FINISHED,
    Event.FAIL: EndCause.FAILED,
}


@dataclass(frozen=True)
class Expected:
    """What a playback told a word of events answers, and where it stands after it."""

    outputs: Tuple[Output, ...]
    phase: PlaybackPhase
    paused: bool
    ending: Optional[Ending]


def _apply(lifecycle: PlaybackLifecycle, event: Event, index: int) -> Output:
    match event:
        case Event.PAUSE:
            return lifecycle.pause()
        case Event.RESUME:
            return lifecycle.resume()
        case Event.COMMAND:
            return lifecycle.accepts_commands()
        case Event.STOP:
            return lifecycle.stop()
        case Event.DISPLACE:
            return lifecycle.displace()
        case Event.FINISH:
            return lifecycle.finish()
        case Event.FAIL:
            return lifecycle.fail(FAILURES[index])
        case Event.WRITTEN:
            return lifecycle.written()
        case Event.SETTLE:
            return lifecycle.settle()


def _run(word: Sequence[Event]) -> Tuple[PlaybackLifecycle, Tuple[Output, ...]]:
    lifecycle = PlaybackLifecycle()
    return lifecycle, tuple(_apply(lifecycle, event, index) for index, event in enumerate(word))


def _ending(word: Sequence[Event], decided: int, settled: Optional[int]) -> Ending:
    """The ending the first deciding event names, or the failure that cuts a finished sound's tail short."""
    cause = DECIDING[word[decided]]
    if cause is EndCause.FAILED:
        return Ending.failure(FAILURES[decided])

    if cause is EndCause.FINISHED:
        upgrade = _first(word, Event.FAIL, start=decided + 1, end=settled)
        if upgrade is not None:
            return Ending.failure(FAILURES[upgrade])

    return Ending.of(cause)


def _first(word: Sequence[Event], event: Event, *, start: int, end: Optional[int]) -> Optional[int]:
    stop = len(word) if end is None else end
    return next((index for index in range(start, stop) if word[index] is event), None)


def _held(word: Sequence[Event], end: int) -> bool:
    """Whether the last pause or resume before ``end`` held the playback."""
    holds = [event for event in word[:end] if event in (Event.PAUSE, Event.RESUME)]
    return bool(holds) and holds[-1] is Event.PAUSE


def _reference(word: Sequence[Event]) -> Expected:
    """What the contract says a playback answers to ``word``, read off the word as a whole.

    The first deciding event ends the playback, and until it every request is taken. After it every request
    is refused, the first settle sends the ending, and a failure before that settle replaces a finish.
    """
    decided = next((index for index, event in enumerate(word) if event in DECIDING), None)
    if decided is None:
        outputs = tuple(None if event is Event.SETTLE else True for event in word)
        return Expected(outputs=outputs, phase=PlaybackPhase.PLAYING, paused=_held(word, len(word)), ending=None)

    settled = _first(word, Event.SETTLE, start=decided + 1, end=None)
    ending = _ending(word, decided, settled)
    upgrade = _first(word, Event.FAIL, start=decided + 1, end=settled) if word[decided] is Event.FINISH else None
    outputs: List[Output] = []
    for index, event in enumerate(word):
        if index < decided:
            outputs.append(None if event is Event.SETTLE else True)
        elif index == decided:
            outputs.append(True)
        elif event is Event.SETTLE:
            outputs.append(ending if index == settled else None)
        else:
            outputs.append(event is Event.FAIL and index == upgrade)

    phase = PlaybackPhase.ENDING if settled is None else PlaybackPhase.ENDED
    return Expected(outputs=tuple(outputs), phase=phase, paused=False, ending=ending)


class TestModel:
    """The lifecycle answers every word of events up to ``LONGEST`` as the contract read off the whole word does."""

    def test_every_word_matches_the_reference(self) -> None:
        for word in words(tuple(Event), longest=LONGEST):
            lifecycle, outputs = _run(word)
            expected = _reference(word)

            assert outputs == expected.outputs, word
            assert lifecycle.phase is expected.phase, word
            assert lifecycle.paused is expected.paused, word
            assert lifecycle.ending == expected.ending, word
            assert lifecycle.engaged is (expected.phase is PlaybackPhase.PLAYING), word
            assert lifecycle.mixed is (lifecycle.engaged and not expected.paused), word

    def test_every_word_sends_one_end_report_at_most(self) -> None:
        for word in words(tuple(Event), longest=LONGEST):
            _, outputs = _run((*word, Event.SETTLE))

            reports = [output for output in outputs if isinstance(output, Ending)]
            decided = any(event in DECIDING for event in word)
            assert len(reports) == (1 if decided else 0), word

    def test_nothing_reaches_a_playback_once_its_end_is_decided(self) -> None:
        for word in words(tuple(Event), longest=LONGEST):
            lifecycle, _ = _run(word)
            if lifecycle.engaged:
                continue

            assert not lifecycle.written(), word
            assert not lifecycle.accepts_commands(), word
            assert not lifecycle.pause(), word
            assert not lifecycle.stop(), word


class TestEnding:
    """Rule 3: the first cause ends a playback, and its one report names it."""

    def test_a_stop_ends_the_playback_once(self) -> None:
        lifecycle, outputs = _run((Event.STOP, Event.SETTLE, Event.SETTLE))

        assert outputs == (True, Ending.of(EndCause.STOPPED), None)
        assert lifecycle.phase is PlaybackPhase.ENDED

    def test_a_takeover_after_a_stop_keeps_the_stop(self) -> None:
        _, outputs = _run((Event.STOP, Event.DISPLACE, Event.SETTLE))

        assert outputs == (True, False, Ending.of(EndCause.STOPPED))

    def test_a_failure_cutting_a_finished_tail_names_the_failure(self) -> None:
        _, outputs = _run((Event.FINISH, Event.FAIL, Event.SETTLE))

        assert outputs[2] == Ending.failure(FAILURES[1])

    def test_a_failure_after_a_stop_keeps_the_stop(self) -> None:
        _, outputs = _run((Event.STOP, Event.FAIL, Event.SETTLE))

        assert outputs == (True, False, Ending.of(EndCause.STOPPED))

    def test_a_failure_after_the_report_changes_nothing(self) -> None:
        lifecycle, outputs = _run((Event.FINISH, Event.SETTLE, Event.FAIL))

        assert outputs == (True, Ending.of(EndCause.FINISHED), False)
        assert lifecycle.ending == Ending.of(EndCause.FINISHED)


class TestRequests:
    """Rules 4 and 6: a playing playback takes positions, commands and pauses, and an ending one takes none."""

    def test_a_playing_playback_reports_positions_and_takes_commands(self) -> None:
        _, outputs = _run((Event.WRITTEN, Event.COMMAND))

        assert outputs == (True, True)

    def test_a_stopped_playback_reports_no_position_and_refuses_commands(self) -> None:
        _, outputs = _run((Event.STOP, Event.WRITTEN, Event.COMMAND))

        assert outputs == (True, False, False)

    def test_a_paused_playback_is_left_out_of_the_mix(self) -> None:
        lifecycle, _ = _run((Event.PAUSE,))

        assert lifecycle.engaged
        assert not lifecycle.mixed

    def test_a_pause_after_the_end_holds_nothing(self) -> None:
        lifecycle, outputs = _run((Event.STOP, Event.PAUSE))

        assert outputs == (True, False)
        assert not lifecycle.paused
