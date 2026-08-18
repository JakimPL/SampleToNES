from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from sampletones_application.logic.sequencer.playback.synthesizer import RowSynthesizer
from sampletones_application.services.render.result import RenderResult
from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceError,
    ServiceSuccess,
)
from sampletones_core.audio.writers import AudioOutputSpec


@dataclass(frozen=True)
class RenderRequest:
    synthesizer: RowSynthesizer
    destination: Path
    spec: AudioOutputSpec
    normalize: bool
    total_samples: int


class FakeRenderService:
    """The render service as the logic drives it, holding what it was asked to render.

    Results are delivered through the handler the logic subscribes, so a test walks a render the
    way the worker reports one.
    """

    def __init__(self, *, accepts: bool = True) -> None:
        self.accepts = accepts
        self.requests: List[RenderRequest] = []
        self.cancels: int = 0
        self.shutdowns: int = 0
        self.running: bool = False
        self._handler: Optional[Callable[[RenderResult], None]] = None

    def subscribe(self, handler: Callable[[RenderResult], None]) -> None:
        self._handler = handler

    def start(
        self,
        *,
        synthesizer: RowSynthesizer,
        destination: Path,
        spec: AudioOutputSpec,
        normalize: bool,
        total_samples: int,
    ) -> bool:
        if not self.accepts:
            return False

        self.requests.append(
            RenderRequest(
                synthesizer=synthesizer,
                destination=destination,
                spec=spec,
                normalize=normalize,
                total_samples=total_samples,
            )
        )
        self.running = True
        return True

    def cancel(self) -> None:
        self.cancels += 1

    def is_running(self) -> bool:
        return self.running

    def shutdown(self) -> None:
        self.shutdowns += 1

    def emit(self, result: RenderResult) -> None:
        assert self._handler is not None, "The logic subscribes to the service it is given"
        self.running = not isinstance(result, (ServiceSuccess, ServiceError, ServiceCancelled))
        self._handler(result)

    @property
    def request(self) -> RenderRequest:
        assert self.requests, "A render was expected to start"
        return self.requests[-1]
