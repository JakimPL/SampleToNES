from pathlib import Path
from typing import Callable, Protocol

from sampletones_application.logic.sequencer.playback.synthesizer import RowSynthesizer
from sampletones_application.services.render.result import RenderResult
from sampletones_core.audio.writers import AudioOutputSpec


class SongRenderServiceProtocol(Protocol):
    """The slice of the render service the render logic drives.

    Typing the collaborator structurally keeps the logic layer bound to the service's result
    contract alone; the composition root supplies the real service. The kernel named here is the
    one the logic builds, which the service takes through the wider contract every consumer of a
    song's audio is written against.
    """

    def subscribe(self, handler: Callable[[RenderResult], None]) -> None: ...

    def start(
        self,
        *,
        synthesizer: RowSynthesizer,
        destination: Path,
        spec: AudioOutputSpec,
        normalize: bool,
        total_samples: int,
    ) -> bool: ...

    def cancel(self) -> None: ...

    def is_running(self) -> bool: ...

    def shutdown(self) -> None: ...
