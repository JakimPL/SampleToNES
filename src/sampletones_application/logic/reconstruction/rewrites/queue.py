from dataclasses import dataclass, replace
from typing import Callable, List, Optional

from sampletones_application.logic.reconstruction.edit import (
    ChannelEdit,
    ReconstructionEdit,
    Retune,
    StemRemoval,
)
from sampletones_application.logic.reconstruction.envelopes import HeardEnvelopes
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.reconstruction.rewrites.regeneration import (
    RegenerationServiceProtocol,
)
from sampletones_application.logic.reconstruction.rewrites.steps import (
    AfterEdits,
    ChannelChange,
    ListeningChange,
    RateChange,
    Rewrite,
    StemRemovalRequest,
)
from sampletones_application.services.regeneration.result import (
    RegenerationResult,
    RenderedDocument,
)
from sampletones_application.services.result import ServiceError, ServiceSuccess
from sampletones_application.view_model.reconstruction.envelopes import (
    ChannelEnvelopesViewModel,
)
from sampletones_application.view_model.reconstruction.work import Work
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.removal import (
    can_remove_stem,
    without_stem,
)
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin


@dataclass(frozen=True)
class Running:
    """A job the worker runs, beside the document it started from.

    Attributes:
        base: The document the job started from, or ``None`` once an outside replacement put that
            document away.
    """

    base: Optional[Reconstruction]

    def lands_on(self, reconstruction: Optional[Reconstruction]) -> bool:
        """Whether the result belongs to ``reconstruction``, the document it was computed from."""
        return self.base is not None and self.base is reconstruction


@dataclass(frozen=True)
class Rebuild(Running):
    """A channel change the worker is rebuilding.

    Attributes:
        change: What the reader moved.
    """

    change: ChannelChange


@dataclass(frozen=True)
class Reading(Running):
    """A reading of what the reader hears, which the worker is rendering."""


class ReconstructionRewrites(CallbackMixin):
    """The steps that change the open document or what is heard of it, taken one at a time in the order the
    reader asked.

    Every edit of the Reconstructions tab's document passes through here: a channel the reader
    moved, a recording taken out, a new NES frequency, and a gesture that reads or puts away the
    whole document. So does a change to what the reader hears whose sound the screen holds no
    audio for yet, which the worker renders from the document as it then stands. Each step reads
    the document the step before it left, so each edit stands on the one before it, a rebuild
    starts from what stands, and a listening sounds the document the edits before it made.

    Channel changes wait while a job runs, and a change joins the one waiting at the end of the
    line when both move the same channel, so a drag collapses into the place it ended; one
    listening waiting answers every choice made before it is taken. A change reaching its turn
    while the envelopes of what is heard are still on their way, as after a box ticked behind it,
    waits behind a listening of that choice and rebuilds from the envelopes it lands. A result
    lands only on the document it was computed from. A removal or a whole-document gesture
    changes what the panel was drawn on, so a channel change asked for while one waits is
    refused, and the panel is redrawn once the line empties.

    The hooks carry the outcome to whoever shows the document: ``on_edit`` with each edit that
    lands, ``on_heard_rendered`` once a listening's sound is kept for the open document (with
    whether its envelopes changed what the instruments panel draws), ``on_dropped`` when the panel
    draws a change that will never land, ``on_failed`` with a job's failure, ``on_reading_failed``
    when a listening the open document waits for failed, and ``on_work_changed`` as the line
    fills, hands over from one kind of work to the other, and empties.
    """

    def __init__(
        self,
        reconstruction_manager: ReconstructionManager,
        regeneration: RegenerationServiceProtocol,
    ) -> None:
        self._manager = reconstruction_manager
        self._regeneration = regeneration
        self._waiting: List[Rewrite] = []
        self._running: Optional[Running] = None
        self._awaiting_envelopes: Optional[ChannelChange] = None
        self._redraw_owed: bool = False
        self._reported_work: Optional[Work] = None

        self.on_edit: Optional[Callable[[ReconstructionEdit], None]] = None
        self.on_heard_rendered: Optional[Callable[[bool], None]] = None
        self.on_dropped: Optional[VoidCallback] = None
        self.on_failed: Optional[Callable[[Exception], None]] = None
        self.on_reading_failed: Optional[VoidCallback] = None
        self.on_work_changed: Optional[Callable[[Optional[Work]], None]] = None

        regeneration.subscribe(self._on_result)

    @property
    def work(self) -> Optional[Work]:
        """What the running job does, which the waveform's fade names, or ``None`` while none runs."""
        match self._running:
            case Rebuild():
                return Work.REBUILDING
            case Reading():
                return Work.READING

        return None

    @property
    def is_busy(self) -> bool:
        """Whether a job runs or a step waits, which is the span the open document's sound is on its way."""
        return self._running is not None or bool(self._waiting)

    def request(self, rewrite: Rewrite) -> None:
        """Puts a step at the end of the line, and takes it at once where the line stands idle.

        A channel change joins a waiting change of the same channel, a new rate replaces a
        waiting one, and one listening waiting stands for every one asked for after it, so what
        the reader asked for last is what lands.
        """
        match rewrite:
            case ChannelChange() as change:
                self._enqueue_change(change)
            case RateChange() as rate_change:
                self._enqueue_rate(rate_change)
            case ListeningChange() as listening:
                self._enqueue_listening(listening)
            case StemRemovalRequest() | AfterEdits():
                self._waiting.append(rewrite)

        self._advance()
        self._settle()

    def drop(self) -> None:
        """Lets go of the edits meant for a document an outside replacement puts away.

        The channel changes, removals, rates and listenings waiting leave the line, and the running
        job's result is let go. A whole-document gesture the reader asked for keeps its place, so a
        save, a load or an undo still happens, in order, on the document now open. The replacement
        draws the document it puts in place, which answers a redraw still owed.
        """
        self._waiting = [step for step in self._waiting if isinstance(step, AfterEdits)]
        self._redraw_owed = False
        if self._running is not None:
            self._running = replace(self._running, base=None)

        self._settle()

    def drawn(self, envelopes: ChannelEnvelopesViewModel) -> ChannelEnvelopesViewModel:
        """The document's envelopes with every change still on its way written over them, in order.

        The instruments panel draws these, so what the reader sees is what the document will hold
        once the line empties. A rebuild whose document was put away leaves the envelopes as drawn.

        Args:
            envelopes: The envelopes the open document holds.
        """
        changes = self._pending_changes()
        if not changes:
            return envelopes

        channels = dict(envelopes.channels)
        for change in changes:
            channels[change.channel_name] = change.rebased(channels[change.channel_name])

        return ChannelEnvelopesViewModel(channels=channels, ownership=envelopes.ownership)

    def _pending_changes(self) -> List[ChannelChange]:
        """The channel changes on their way to the open document, the running one first."""
        changes: List[ChannelChange] = []
        if isinstance(self._running, Rebuild) and self._running.lands_on(self._manager.reconstruction):
            changes.append(self._running.change)

        changes.extend(step for step in self._waiting if isinstance(step, ChannelChange))
        return changes

    @property
    def _reshaping_waits(self) -> bool:
        """Whether a removal or a whole-document gesture waits, either of which reshapes what the panel drew on."""
        return any(isinstance(step, (StemRemovalRequest, AfterEdits)) for step in self._waiting)

    def _enqueue_change(self, change: ChannelChange) -> None:
        if self._reshaping_waits:
            logger.info(f"A change of {change.channel_name} was drawn before a step that reshapes the document")
            self._redraw_owed = True
            return

        match self._waiting[-1] if self._waiting else None:
            case ChannelChange() as tail if tail.channel_name == change.channel_name:
                self._waiting[-1] = tail.merged(change)
            case _:
                self._waiting.append(change)

    def _enqueue_listening(self, listening: ListeningChange) -> None:
        if not any(isinstance(step, ListeningChange) for step in self._waiting):
            self._waiting.append(listening)

    def _enqueue_rate(self, rate_change: RateChange) -> None:
        match self._waiting[-1] if self._waiting else None:
            case RateChange():
                self._waiting[-1] = rate_change
            case _:
                self._waiting.append(rate_change)

    def _advance(self) -> None:
        """Takes the waiting steps in order until a job runs or the line empties."""
        while self._running is None and self._waiting:
            self._take(self._waiting.pop(0))

    def _take(self, step: Rewrite) -> None:
        match step:
            case ChannelChange() as change:
                self._rebuild(change)
            case StemRemovalRequest() as removal:
                self._remove(removal)
            case RateChange() as rate_change:
                self._retune(rate_change)
            case AfterEdits(gesture=gesture):
                gesture()
            case ListeningChange():
                self._listen()

    def _rebuild(self, change: ChannelChange) -> None:
        """Starts the rebuild of a changed channel from the document and the listening as they stand.

        Everything the job takes is read first, so a reading that raises leaves the line idle;
        the rebuild is then marked running before it starts, since a case's synchronous seam can
        deliver the result inside the start. The renders the cache holds for the document go with
        it, so the worker renders the edited channel alone and the landing finds every channel's
        audio kept. A change finding the envelopes of what is heard on their way waits for them.
        """
        reconstruction = self._manager.reconstruction
        if reconstruction is None:
            logger.info(f"A change of {change.channel_name} found no document open")
            return

        envelopes = self._manager.current_features
        if envelopes is None:
            self._await_envelopes(change)
            return

        self._awaiting_envelopes = None
        rebased = change.rebased(envelopes[change.channel_name])
        hearing = self._manager.listening.hearing
        kept = self._manager.renders.held(reconstruction)
        self._running = Rebuild(change=change, base=reconstruction)
        self._regeneration.start(
            reconstruction,
            change.channel_name,
            rebased,
            hearing=hearing,
            kept=kept,
            recordings=self._manager.recordings,
        )

    def _await_envelopes(self, change: ChannelChange) -> None:
        """Puts ``change`` back at the head of the line behind a listening of the choice its envelopes are owed for.

        The change waits once: where the listening lands no envelopes for it, as a failed one
        does, the change is let go and the line moves on.
        """
        if self._awaiting_envelopes is change:
            logger.info(f"A change of {change.channel_name} found no envelopes to rebuild from and was let go")
            self._awaiting_envelopes = None
            return

        self._awaiting_envelopes = change
        self._waiting[:0] = [ListeningChange(), change]

    def _listen(self) -> None:
        """Starts rendering what the reader hears of the document as it stands.

        Everything the job takes is read first, so a reading that raises leaves the line idle; the
        reading is then marked running before it starts, since a case's synchronous seam can
        deliver the result inside the start. The renders the cache holds go with it, so the worker
        renders what is missing alone.
        """
        reconstruction = self._manager.reconstruction
        if reconstruction is None:
            logger.info("A change to what is heard found no document open")
            return

        hearing = self._manager.listening.hearing
        kept = self._manager.renders.held(reconstruction)
        self._running = Reading(base=reconstruction)
        self._regeneration.start_listening(
            reconstruction,
            hearing=hearing,
            kept=kept,
            recordings=self._manager.recordings,
        )

    def _remove(self, removal: StemRemovalRequest) -> None:
        """Takes a recording out, where a step before it left the recording and another beside it."""
        reconstruction = self._manager.reconstruction
        if reconstruction is None or not can_remove_stem(reconstruction, removal.stem_id):
            logger.info(f"The removal of stem {removal.stem_id} no longer applies to the open document")
            return

        self.call(
            self.on_edit,
            StemRemoval(
                reconstruction=without_stem(reconstruction, removal.stem_id),
                stem_name=removal.stem_name,
            ),
        )

    def _retune(self, rate_change: RateChange) -> None:
        """Re-times the document to the rate asked for, where it runs at another one."""
        reconstruction = self._manager.reconstruction
        if reconstruction is None:
            logger.info(f"A rate of {rate_change.nes_frequency} Hz found no document open")
            return

        retuned = reconstruction.with_nes_frequency(rate_change.nes_frequency)
        if retuned is reconstruction:
            logger.info(f"The open document already runs at {rate_change.nes_frequency} Hz")
            return

        self.call(
            self.on_edit,
            Retune(
                reconstruction=retuned,
                nes_frequency=rate_change.nes_frequency,
            ),
        )

    def _on_result(self, result: RegenerationResult) -> None:
        """Lands a finished job on the document it was computed from, then takes the next step.

        Raises:
            RuntimeError: If a result arrives while no job runs.
        """
        running = self._running
        if running is None:
            raise RuntimeError("A regeneration result arrived while no job was running")

        self._running = None
        match result:
            case ServiceSuccess(value=outcome):
                self._land(running, outcome)
            case ServiceError(exception=exception):
                self.call(self.on_failed, exception)
                self._fail(running)

        self._advance()
        self._settle()

    def _land(
        self,
        running: Running,
        outcome: RenderedDocument,
    ) -> None:
        """Keeps the renders the job made and reports it, where its document is still open."""
        if not running.lands_on(self._manager.reconstruction):
            logger.info("A job finished for a document put away since")
            self._let_go(running)
            return

        self._manager.renders.adopt_rendered(outcome)
        envelopes = HeardEnvelopes(selection=outcome.hearing.selection, channels=outcome.envelopes)
        match running:
            case Rebuild(change=change):
                self.call(
                    self.on_edit,
                    ChannelEdit(
                        reconstruction=outcome.reconstruction,
                        channel_name=change.channel_name,
                        feature_key=change.feature_key,
                        envelopes=envelopes,
                    ),
                )
            case Reading():
                changed = self._manager.adopt_envelopes(outcome.reconstruction, envelopes)
                self.call(self.on_heard_rendered, changed)

    def _let_go(self, running: Running) -> None:
        """Redraws the panel where it still draws a change that will never land.

        A rebuild an outside replacement dropped is answered by the replacement, which drew the
        document it put in place, and a listening draws only once its sound lands.
        """
        if isinstance(running, Rebuild) and running.base is not None:
            self.call(self.on_dropped)

    def _fail(self, running: Running) -> None:
        """Tells the panel what a failed job leaves it with: a change drawn that will never land, or a sound the
        open document waited for that will never land.
        """
        self._let_go(running)
        if isinstance(running, Reading) and running.lands_on(self._manager.reconstruction):
            self.call(self.on_reading_failed)

    def _settle(self) -> None:
        """Pays a redraw owed once the line empties, and reports what the line is busy with as it changes."""
        if not self.is_busy and self._redraw_owed:
            self._redraw_owed = False
            self.call(self.on_dropped)

        work = self.work
        if work != self._reported_work:
            self._reported_work = work
            self.call(self.on_work_changed, work)
