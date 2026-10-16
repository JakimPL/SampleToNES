import copy
from collections.abc import Hashable
from typing import Dict, Final, List, Optional, Self, Sequence, Set, Tuple

from sampletones_core.audio.output.ending import EndCause, Ending
from sampletones_core.audio.output.lifecycle import StreamAction, StreamPhase, StreamState
from sampletones_core.audio.output.session import EndReport, SessionCore, SourceRead, Step

from .events import DEVICE_ERROR, FAILURES, NORMAL_RANK, PREVIEW_RANK, SOURCE_ERROR, Event
from .monitor import Demand, Monitor

GONE: Final[int] = -1
COMPLETION_STEPS: Final[int] = 12
STOPPED: Final[Ending] = Ending.of(EndCause.STOPPED)
TAKEN: Final[Ending] = Ending.of(EndCause.TAKEN)
FINISHED: Final[Ending] = Ending.of(EndCause.FINISHED)


class SessionRun:
    """A session core driven by one word of events, with the monitor judging every answer it gives.

    Each event is applied to the core and to the monitor alike, and the core's answer is held to the
    contract at once: who holds the output, what the writer does next, which playbacks a block mixes, whose
    positions go out, and what each end report says. A broken rule raises at the event that broke it.
    At most ``most_claims`` playbacks are claimed, which keeps the states a case explores finite.
    """

    def __init__(self, *, most_claims: int) -> None:
        self.most_claims = most_claims
        self.core: SessionCore[int] = SessionCore()
        self.monitor = Monitor()
        self.pending: Optional[Step[int]] = None
        self.latest: Optional[int] = None
        self.claims: int = 0
        self.writing: bool = False
        self.carried: Set[int] = set()
        self.actions: List[StreamAction] = []
        self.reports: List[EndReport[int]] = []
        self.positions: List[int] = []

    def key(self) -> Hashable:
        """Equal for two runs that answer every later event alike, which lets a case explore each state once.

        A playback whose report went out takes no further part, so the playbacks still present are numbered
        in claim order, and two runs differing only in how many came and went before meet as one.
        """
        live = {key: index for index, key in enumerate(self.monitor.unreported())}
        snapshot = self.core.snapshot()
        playbacks = tuple((live[playback.key], playback.rank, playback.state) for playback in snapshot.playbacks)
        pending = (
            None
            if self.pending is None
            else (self.pending.action, tuple(live.get(key, GONE) for key in self.pending.mixed))
        )
        latest = None if self.latest is None else live.get(self.latest, GONE)
        carried = frozenset(live.get(key, GONE) for key in self.carried)
        return (
            snapshot.stream,
            playbacks,
            self.monitor.key(),
            pending,
            latest,
            self.most_claims - self.claims,
            self.writing,
            carried,
        )

    def moves(self, event: Event) -> bool:
        """Whether ``event`` can change the run, which a writer's turn out of its order and a claim past the
        bound cannot, so a case exploring the states skips the copy it would cost."""
        match event:
            case Event.CLAIM_PREVIEW | Event.CLAIM_NORMAL:
                return self.claims < self.most_claims
            case Event.STOP | Event.PAUSE | Event.RESUME | Event.COMMAND | Event.FAILS_ASIDE:
                return self.latest is not None
            case Event.DECIDE:
                return self.writing and self.pending is None
            case Event.SUCCEEDS | Event.RUNS_OUT | Event.SOURCE_FAILS | Event.DEVICE_FAILS:
                return self.pending is not None
            case Event.STOP_ALL | Event.RECONFIGURE | Event.CLOSE | Event.ABANDON:
                return True

    def apply(self, event: Event) -> None:
        """Applies ``event`` and holds the core's answer to the contract.

        Raises:
            AssertionError: Naming the rule the core's answer broke.
        """
        match event:
            case Event.CLAIM_PREVIEW:
                self._claim(PREVIEW_RANK)
            case Event.CLAIM_NORMAL:
                self._claim(NORMAL_RANK)
            case Event.STOP:
                self._stop()
            case Event.STOP_ALL:
                self.monitor.offer_engaged(STOPPED)
                self.core.stop_all()
            case Event.PAUSE | Event.RESUME:
                self._hold(paused=event is Event.PAUSE)
            case Event.COMMAND:
                self._command()
            case Event.FAILS_ASIDE:
                self._fail_aside()
            case Event.RECONFIGURE:
                self._reconfigure()
            case Event.CLOSE:
                self._close()
            case Event.ABANDON:
                self._abandon()
            case Event.DECIDE:
                self._decide()
            case Event.SUCCEEDS | Event.RUNS_OUT | Event.SOURCE_FAILS | Event.DEVICE_FAILS:
                self._outcome(event)

        self._check_holders()

    def complete(self) -> None:
        """Closes the output and lets the writer run to its exit with every device call succeeding.

        Raises:
            AssertionError: If the writer never exits, or a playback ends other than once.
        """
        if self.pending is not None:
            self.apply(Event.SUCCEEDS)

        self.apply(Event.CLOSE)
        for _ in range(COMPLETION_STEPS):
            if not self.writing:
                break

            self.apply(Event.DECIDE)
            if self.pending is not None:
                self.apply(Event.SUCCEEDS)

        assert not self.writing, "rule 8: the writer never exits once the output closes"
        assert not self.monitor.unreported(), f"rule 3: playbacks {self.monitor.unreported()} never sent an end report"
        assert self.core.stream_phase is StreamPhase.CLOSED, "rule 8: the stream is open after the writer exits"

    def copy(self) -> Self:
        """A run of its own in the same state, sharing the failures, since an ending is known by its error."""
        return copy.deepcopy(self, memo={id(error): error for error in FAILURES})

    def _claim(self, rank: int) -> None:
        if self.claims >= self.most_claims:
            return

        key = self.claims
        self.claims += 1
        expected = not self.monitor.closing and not self.monitor.outranked(rank)
        accepted = self.core.claim(key, rank=rank)
        assert accepted is expected, f"rule 1: a claim at rank {rank} answered {accepted}"
        if accepted:
            self.monitor.offer_engaged(TAKEN)
            self.monitor.claimed(key, rank=rank)
            self.latest = key
            self.writing = True

    def _stop(self) -> None:
        if self.latest is None:
            return

        expected = self.monitor.expectation(self.latest).engaged
        assert self.core.stop(self.latest) is expected, "rule 3: a stop answered other than the playback's state"
        self.monitor.offer(self.latest, STOPPED)

    def _hold(self, *, paused: bool) -> None:
        if self.latest is None:
            return

        expectation = self.monitor.expectation(self.latest)
        answered = self.core.pause(self.latest) if paused else self.core.resume(self.latest)
        assert answered is expectation.engaged, "a pause or a resume answered other than the playback's state"
        if expectation.engaged:
            expectation.paused = paused

    def _command(self) -> None:
        if self.latest is None:
            return

        expectation = self.monitor.expectation(self.latest)
        assert self.core.command(self.latest) is expectation.engaged, "rule 4: a command reached an ended playback"
        if expectation.engaged:
            expectation.commanded = True

    def _fail_aside(self) -> None:
        """The latest playback's source fails on a thread of its own, between the writer's reads."""
        if self.latest is None:
            return

        expectation = self.monitor.expectation(self.latest)
        decides = not expectation.reported and (
            expectation.engaged or (expectation.tail and expectation.upgrade is None)
        )
        assert (
            self.core.fail(self.latest, SOURCE_ERROR) is decides
        ), "rule 7: a failure aside answered other than the playback's state"
        self.monitor.offer(self.latest, Ending.failure(SOURCE_ERROR))

    def _reconfigure(self) -> None:
        expected = not self.monitor.closing
        assert self.core.reconfigure() is expected, "a reconfiguration answered other than the output's state"
        if expected:
            self.monitor.offer_engaged(STOPPED)
            self.writing = True

    def _close(self) -> None:
        self.monitor.closing = True
        self.monitor.offer_engaged(STOPPED)
        self.core.close()

    def _abandon(self) -> None:
        self.monitor.closing = True
        self.monitor.offer_engaged(STOPPED)
        reports = self.core.abandon()
        assert {report.key for report in reports} == set(
            self.monitor.unreported()
        ), "rule 8: a teardown that stops waiting ends every playback present"
        self._receive(reports)

    def _decide(self) -> None:
        if not self.writing or self.pending is not None:
            return

        demand = Demand(
            wanted=bool(self.monitor.engaged()),
            mixing=bool(self._mixing()),
            tail=any(self.monitor.expectation(key).tail for key in self.monitor.unreported()),
        )
        stream = self.core.snapshot().stream
        step = self.core.next_step()
        self._check_action(step.action, stream, demand)
        self._check_settled(step, stream)
        self._receive(step.reports)
        self._check_mixed(step)
        self._check_carried(step)
        for key in step.mixed:
            self.monitor.expectation(key).commanded = False

        self.actions.append(step.action)
        if step.action is StreamAction.EXIT:
            self.writing = False
        elif step.action is not StreamAction.WAIT:
            self.pending = step

    def _outcome(self, event: Event) -> None:
        step = self.pending
        if step is None:
            return

        match step.action:
            case StreamAction.OPEN:
                self._opened(event)
            case StreamAction.WRITE:
                self._wrote(event, step.mixed)
            case StreamAction.DRAIN | StreamAction.ABORT:
                self._closed(event)
            case StreamAction.RECONFIGURE:
                if event is Event.SUCCEEDS:
                    self.core.reconfigured()
                    self.pending = None

    def _opened(self, event: Event) -> None:
        if event is Event.SUCCEEDS:
            self.core.opened()
            self.pending = None
        elif event is Event.DEVICE_FAILS:
            self.monitor.offer_engaged(Ending.failure(DEVICE_ERROR))
            self.core.open_failed(DEVICE_ERROR)
            self.pending = None

    def _wrote(self, event: Event, mixed: Tuple[int, ...]) -> None:
        reads: Dict[int, SourceRead] = {key: SourceRead.filled() for key in mixed}
        if event in (Event.RUNS_OUT, Event.SOURCE_FAILS):
            if not mixed:
                return

            reads[mixed[0]] = SourceRead.last() if event is Event.RUNS_OUT else SourceRead.failed(SOURCE_ERROR)

        self.pending = None
        if event is Event.DEVICE_FAILS:
            for key in self.monitor.unreported():
                own = reads.get(key)
                self.monitor.offer(key, Ending.failure(DEVICE_ERROR if own is None or own.error is None else own.error))

            self.core.write_failed(DEVICE_ERROR, reads)
            return

        self.carried.update(mixed)
        expected = [key for key in mixed if self.monitor.expectation(key).engaged and reads[key].error is None]
        positions = self.core.wrote(reads)
        assert list(positions) == expected, f"rule 4: positions went out for {positions}, not {expected}"
        self.positions.extend(positions)
        for key, read in reads.items():
            if read.error is not None:
                self.monitor.offer(key, Ending.failure(read.error))
            elif read == SourceRead.last() and not self.monitor.expectation(key).commanded:
                self.monitor.offer(key, FINISHED)

    def _closed(self, event: Event) -> None:
        if event is Event.SUCCEEDS:
            self.core.closed(None)
        elif event is Event.DEVICE_FAILS:
            self.monitor.cut_tails(Ending.failure(DEVICE_ERROR))
            self.core.closed(DEVICE_ERROR)
        else:
            return

        self.pending = None
        self.carried.clear()

    def _receive(self, reports: Sequence[EndReport[int]]) -> None:
        for report in reports:
            expectation = self.monitor.expectation(report.key)
            assert not expectation.reported, f"rule 3: playback {report.key} sent a second end report"
            assert not expectation.engaged, f"rule 3: playback {report.key} reported its end while holding the output"
            assert (
                report.ending == expectation.ending
            ), f"rule 3: playback {report.key} reported {report.ending}, not {expectation.ending}"
            self.monitor.reported(report.key)
            self.reports.append(report)

    def _check_settled(self, step: Step[int], stream: StreamState) -> None:
        """Every decided end is reported at the step after it, a finished tail alone waiting for the drain.

        A finished sound reports once its tail played out, unless a close, a reconfiguration or a claim cut it.
        """
        due = [
            key
            for key in self.monitor.unreported()
            if not self.monitor.expectation(key).engaged
            and not (step.action is StreamAction.DRAIN and self.monitor.expectation(key).tail)
        ]
        assert [
            report.key for report in step.reports
        ] == due, f"rule 3: the step reported {[report.key for report in step.reports]}, not {due}"
        finished = [report for report in step.reports if report.ending.cause is EndCause.FINISHED]
        if finished and not self.monitor.engaged() and _settled(stream) and not stream.cutting:
            assert (
                self.core.stream_phase is not StreamPhase.OPEN
            ), "rule 3: a finished sound reported its end before its tail played out"

    def _check_action(self, action: StreamAction, stream: StreamState, demand: Demand) -> None:
        phase = stream.phase
        match action:
            case StreamAction.OPEN:
                assert phase is StreamPhase.CLOSED and demand.wanted, "rule 2: a stream opened over another"
            case StreamAction.WRITE:
                assert demand.mixing, "rule 3: a block was written with no playback sounding"
            case StreamAction.DRAIN:
                assert demand.tail and not demand.wanted, "rule 6: a tail played out with no finished sound behind it"
            case StreamAction.WAIT:
                assert (
                    demand.wanted and not demand.mixing and phase is StreamPhase.OPEN
                ), "the writer waited while a playback could sound, or with no stream to hold"
            case StreamAction.ABORT:
                assert not (
                    _settled(stream) and not stream.cutting and demand.tail and not demand.wanted
                ), "rule 6: a finished sound's tail was cut"
            case StreamAction.EXIT:
                assert (
                    self.monitor.closing or not demand.wanted
                ), "rule 8: the writer ended while a playback held the output"
                assert phase is StreamPhase.CLOSED, "rule 8: the writer ended with the stream open"
            case StreamAction.RECONFIGURE:
                return

    def _check_mixed(self, step: Step[int]) -> None:
        expected = self._mixing() if step.action is StreamAction.WRITE else []
        assert list(step.mixed) == expected, f"rule 3: the block mixes {step.mixed}, not {expected}"

    def _check_carried(self, step: Step[int]) -> None:
        """A block goes to a stream only while every sound the stream played still sounds in it."""
        if step.action is StreamAction.WRITE:
            assert self.carried <= set(
                step.mixed
            ), f"rule 6: playbacks {step.mixed} play on in the stream {sorted(self.carried)} took the output from"

    def _mixing(self) -> List[int]:
        return [key for key in self.monitor.engaged() if not self.monitor.expectation(key).paused]

    def _check_holders(self) -> None:
        present = [playback.key for playback in self.core.snapshot().playbacks]
        unreported = self.monitor.unreported()
        assert all(
            key in unreported for key in present
        ), f"rule 3: playbacks {present} stay present after their end reports"
        engaged = self.monitor.engaged()
        assert len(engaged) <= 1, f"rule 1: playbacks {engaged} hold the output at once"
        assert self.core.is_sounding is bool(engaged), "the output reports sounding other than its playbacks"
        for key in self.monitor.keys():
            holds = self.monitor.expectation(key).engaged
            assert self.core.is_engaged(key) is holds, f"playback {key} reports engaged other than it is"
            assert self.core.accepts_commands(key) is holds, f"rule 4: playback {key} takes commands once it ended"


def _settled(stream: StreamState) -> bool:
    """Whether no close or reconfiguration outranks playing."""
    return not stream.closing and not stream.reconfiguring
