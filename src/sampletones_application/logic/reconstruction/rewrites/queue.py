from dataclasses import dataclass, replace
from typing import Callable, List, Optional

from sampletones_application.logic.reconstruction.edit import (
    ChannelEdit,
    ReconstructionEdit,
    Retune,
    StemRemoval,
)
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.reconstruction.rewrites.regeneration import (
    RegenerationServiceProtocol,
)
from sampletones_application.logic.reconstruction.rewrites.steps import (
    AfterEdits,
    ChannelChange,
    RateChange,
    Rewrite,
    StemRemovalRequest,
)
from sampletones_application.services.regeneration.result import (
    RegeneratedInstrument,
    RegenerationResult,
)
from sampletones_application.services.result import ServiceError, ServiceSuccess
from sampletones_application.view_model.reconstruction.envelopes import (
    ChannelEnvelopesViewModel,
)
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.removal import (
    can_remove_stem,
    without_stem,
)
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin


@dataclass(frozen=True)
class Rebuild:
    """A channel change the regeneration is rebuilding, beside the document it started from.

    Attributes:
        change: What the reader moved.
        base: The document the rebuild started from, or ``None`` once an outside replacement put
            that document away.
    """

    change: ChannelChange
    base: Optional[Reconstruction]

    def lands_on(self, reconstruction: Optional[Reconstruction]) -> bool:
        """Whether the result belongs to ``reconstruction``, the document it was computed from."""
        return self.base is not None and self.base is reconstruction


class ReconstructionRewrites(CallbackMixin):
    """The steps that change the open document, taken one at a time in the order the reader asked.

    Every edit of the Reconstructions tab's document passes through here: a channel the reader
    moved, a recording taken out, a new NES frequency, and a gesture that reads or puts away the
    whole document. Each step reads the document the step before it left, so one edit never
    overwrites another and a rebuild always starts from what stands.

    Channel changes wait while a rebuild runs, and a change joins the one waiting at the end of the
    line when both move the same channel, so a drag collapses into the place it ended. A rebuild's
    result lands only on the document it was computed from. A removal or a whole-document gesture
    changes what the panel was drawn on, so a channel change asked for while one waits is refused,
    and the panel is redrawn once the line empties.

    The hooks carry the outcome to whoever shows the document: ``on_edit`` with each edit that
    lands, ``on_dropped`` when the panel draws a change that will never land, ``on_failed`` with a
    rebuild's failure, and ``on_busy_changed`` as the line fills and empties.
    """

    def __init__(
        self,
        reconstruction_manager: ReconstructionManager,
        regeneration: RegenerationServiceProtocol,
    ) -> None:
        self._manager = reconstruction_manager
        self._regeneration = regeneration
        self._waiting: List[Rewrite] = []
        self._running: Optional[Rebuild] = None
        self._redraw_owed: bool = False
        self._reported_busy: bool = False

        self.on_edit: Optional[Callable[[ReconstructionEdit], None]] = None
        self.on_dropped: Optional[VoidCallback] = None
        self.on_failed: Optional[Callable[[Exception], None]] = None
        self.on_busy_changed: Optional[Callable[[bool], None]] = None

        regeneration.subscribe(self._on_result)

    @property
    def is_busy(self) -> bool:
        """Whether a rebuild runs or a step waits, which is the span the open document is being rewritten."""
        return self._running is not None or bool(self._waiting)

    def request(self, rewrite: Rewrite) -> None:
        """Puts a step at the end of the line, and takes it at once where nothing runs before it.

        A channel change joins a waiting change of the same channel, and a new rate replaces a
        waiting one, so what the reader asked for last is what lands.
        """
        match rewrite:
            case ChannelChange() as change:
                self._enqueue_change(change)
            case RateChange() as rate_change:
                self._enqueue_rate(rate_change)
            case StemRemovalRequest() | AfterEdits():
                self._waiting.append(rewrite)

        self._advance()
        self._settle()

    def drop(self) -> None:
        """Lets go of the edits meant for a document an outside replacement puts away.

        The channel changes, removals and rates waiting leave the line, and the running rebuild's
        result no longer lands. A whole-document gesture the reader asked for keeps its place, so a
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
        once the line empties. A rebuild whose document was put away writes nothing.

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
        if self._running is not None and self._running.lands_on(self._manager.reconstruction):
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

    def _enqueue_rate(self, rate_change: RateChange) -> None:
        match self._waiting[-1] if self._waiting else None:
            case RateChange():
                self._waiting[-1] = rate_change
            case _:
                self._waiting.append(rate_change)

    def _advance(self) -> None:
        """Takes the waiting steps in order until a rebuild runs or the line empties."""
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

    def _rebuild(self, change: ChannelChange) -> None:
        """Starts the rebuild of a changed channel from the document and the listening as they stand.

        The rebuild is marked running before it starts, since a result can arrive before the start
        returns.
        """
        reconstruction = self._manager.reconstruction
        envelopes = self._manager.current_features
        if reconstruction is None or envelopes is None:
            logger.info(f"A change of {change.channel_name} found no document open")
            return

        self._running = Rebuild(change=change, base=reconstruction)
        self._regeneration.start(
            reconstruction,
            change.channel_name,
            change.rebased(envelopes[change.channel_name]),
            self._manager.listening.heard_on(change.channel_name),
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
        """Lands a finished rebuild on the document it was computed from, then takes the next step.

        Raises:
            RuntimeError: If a result arrives while no rebuild runs.
        """
        rebuild = self._running
        if rebuild is None:
            raise RuntimeError("A regeneration result arrived while no rebuild was running")

        self._running = None
        match result:
            case ServiceSuccess(value=outcome):
                self._land(rebuild, outcome)
            case ServiceError(exception=exception):
                self.call(self.on_failed, exception)
                self._let_go(rebuild)

        self._advance()
        self._settle()

    def _land(self, rebuild: Rebuild, outcome: RegeneratedInstrument) -> None:
        if not rebuild.lands_on(self._manager.reconstruction):
            logger.info(f"A rebuild of {rebuild.change.channel_name} finished for a document put away since")
            self._let_go(rebuild)
            return

        self.call(
            self.on_edit,
            ChannelEdit(
                reconstruction=outcome.reconstruction,
                channel_name=rebuild.change.channel_name,
                feature_key=rebuild.change.feature_key,
            ),
        )

    def _let_go(self, rebuild: Rebuild) -> None:
        """Redraws the panel where it still draws a change that will never land.

        A rebuild an outside replacement dropped needs nothing, since the replacement drew the
        document it put in place.
        """
        if rebuild.base is not None:
            self.call(self.on_dropped)

    def _settle(self) -> None:
        """Pays a redraw owed once the line empties, and reports the line filling or emptying."""
        if not self.is_busy and self._redraw_owed:
            self._redraw_owed = False
            self.call(self.on_dropped)

        busy = self.is_busy
        if busy != self._reported_busy:
            self._reported_busy = busy
            self.call(self.on_busy_changed, busy)
