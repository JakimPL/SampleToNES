from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from sampletones_application.logic.shared.regeneration import ListeningServiceProtocol
from sampletones_application.logic.shared.renders import RenderCache
from sampletones_application.services.regeneration.result import (
    RegenerationResult,
    RenderedDocument,
)
from sampletones_application.services.result import ServiceError, ServiceSuccess
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.hearing import whole_hearing
from sampletones_shared.utils.callbacks import CallbackMixin

Play = Callable[[np.ndarray], None]


@dataclass(frozen=True)
class WantedPreview:
    """A document a reader asked to hear whole, and how it sounds once its audio is in hand.

    Attributes:
        reconstruction: The document to sound.
        play: What sounds the audio, which owns the device, the priority and the refusal a device
            answers with.
    """

    reconstruction: Reconstruction
    play: Play


class DocumentPreviews(CallbackMixin):
    """Sounds whole documents from the render cache, and asks a worker of its own for what the cache lacks.

    A preview of a document is a reading like any other on the Reconstructions tab: sound the
    cache keeps plays at once, and sound it lacks is rendered on a worker and played when it
    lands, so the render thread computes no sample for a voice clicked in the sequencer. The
    cache is the one the tab reads, so a document the tab has landed previews from it and a
    document previewed here opens on the tab rendered.

    The latest preview asked for is the one wanted: a newer request replaces one still on its
    way, whose landing then fills the cache and sounds nothing, and ``cancel`` forgets the wanted
    preview the same way. One job runs at a time and the next wanted document is pursued once it
    lands, reading the cache first, since the tab may have landed it meanwhile. The result a
    landing sounds is the result's own audio, so a landing never asks for the document it just
    delivered. A render that fails reports through ``on_failed`` and forgets the preview that
    asked for it, so the next wanted document is pursued and the failed one is asked for again
    only by a new gesture.

    The service is this reader's own instance: a result reaches every subscriber of the instance
    that made it and names no sender, so a line of previews and the tab's line of rewrites each
    take one. Every result lands on the render thread through the callback queue, which keeps the
    cache's writers there.
    """

    def __init__(
        self,
        renders: RenderCache,
        listening: ListeningServiceProtocol,
    ) -> None:
        self._renders = renders
        self._listening = listening
        self._wanted: Optional[WantedPreview] = None
        self._running: Optional[Reconstruction] = None

        self.on_failed: Optional[Callable[[Exception], None]] = None

        listening.subscribe(self._on_result)

    @property
    def is_busy(self) -> bool:
        """Whether a preview's sound is still on its way, running on the worker or waiting for its turn."""
        return self._running is not None or self._wanted is not None

    def play(
        self,
        reconstruction: Reconstruction,
        play: Play,
    ) -> None:
        """Sounds ``reconstruction`` whole through ``play``, at once or once its render lands.

        Args:
            reconstruction: The document to sound.
            play: What sounds the audio once it is in hand.
        """
        self._wanted = WantedPreview(reconstruction, play)
        self._pursue()

    def cancel(self) -> None:
        """Forgets the preview wanted; a render on its way still lands and fills the cache."""
        self._wanted = None

    def _pursue(self) -> None:
        """Sounds the wanted preview from the cache, or asks the worker for it while no job runs."""
        wanted = self._wanted
        if wanted is None or self._running is not None:
            return

        hearing = whole_hearing(wanted.reconstruction)
        heard = self._renders.reading(wanted.reconstruction, hearing)
        if heard is not None:
            self._wanted = None
            wanted.play(heard.playing)
            return

        self._running = wanted.reconstruction
        self._listening.start_listening(
            wanted.reconstruction,
            hearing=hearing,
            kept=self._renders.held(wanted.reconstruction),
        )

    def _on_result(self, result: RegenerationResult) -> None:
        """Takes a job's result on the render thread: keeps what it rendered, sounds it where still wanted.

        Raises:
            RuntimeError: If a result arrives while no preview is on its way, which is a second
                reader sharing the service instance.
        """
        running = self._running
        if running is None:
            raise RuntimeError("A preview's render arrived while no preview was on its way")

        self._running = None
        match result:
            case ServiceSuccess(value=outcome):
                self._land(outcome)
            case ServiceError(exception=exception):
                if self._wanted is not None and self._wanted.reconstruction is running:
                    self._wanted = None

                self.call(self.on_failed, exception)

        self._pursue()

    def _land(self, outcome: RenderedDocument) -> None:
        self._renders.adopt(outcome.reconstruction, outcome.channels, outcome.mix)
        self._renders.adopt_heard(outcome.reconstruction, outcome.hearing, outcome.heard)
        wanted = self._wanted
        if wanted is not None and wanted.reconstruction is outcome.reconstruction:
            self._wanted = None
            wanted.play(outcome.heard.playing)
