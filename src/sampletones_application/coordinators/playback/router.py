from typing import Callable, Optional, Sequence

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol
from sampletones_application.logic.shared.preview_player import PreviewPlayer
from sampletones_application.logic.shared.previews import DocumentPreviews
from sampletones_core.audio.output import AudioOutput

ActiveSourceResolver = Callable[[], Optional[AudioPlayerProtocol]]


class PlaybackRouter:
    """The single transport over the shared output device.

    Every command acts on one *target*: the active tab's own source when that tab has something to
    play, and otherwise the intentional source currently engaged (owning the device). Preview
    sounds belong to the preview player and answer only to Stop, which silences one sounding and
    forgets one still on its way. The full contract is documented in
    ``docs/development/application/playback.md``.

    It is stateless: the target is recomputed from the live sources on each call, so the transport
    stays in step with tab changes and playback transitions automatically.
    """

    def __init__(
        self,
        *,
        sources: Sequence[AudioPlayerProtocol],
        active_source_resolver: ActiveSourceResolver,
        output: AudioOutput,
        preview_player: PreviewPlayer,
        language_manager: LanguageManager,
        previews: DocumentPreviews,
    ) -> None:
        self._language_manager = language_manager
        self._sources = tuple(sources)
        self._active_source_resolver = active_source_resolver
        self._output = output
        self._preview_player = preview_player
        self._previews = previews

    def play(self) -> None:
        """Play/Pause: pause or resume the target when engaged, otherwise start it."""
        target = self._target()
        if target is not None:
            target.pause_or_resume()

    def play_from_start(self) -> None:
        """Start the active tab's source from the beginning, preempting whatever is engaged."""
        active_source = self._active_source()
        if active_source is not None:
            active_source.play()

    def stop(self) -> None:
        """Silence everything: the engaged source, any sounding preview, and a preview still on its way.

        Each sound is stopped through its owner, so the owner's transport and mark follow at once.
        """
        self._previews.cancel()
        engaged_source = self._engaged_source()
        if engaged_source is not None:
            engaged_source.stop()

        self._preview_player.stop()

    @property
    def play_label(self) -> str:
        target = self._target()
        if target is not None and target.is_engaged():
            return (
                self._language_manager["global.menu.label.item_playback_resume"]
                if target.is_paused()
                else self._language_manager["global.menu.label.item_playback_pause"]
            )

        return self._language_manager["global.menu.label.item_playback_play"]

    @property
    def is_play_enabled(self) -> bool:
        """Whether the Play/Pause toggle has a target to act on."""
        return self._target() is not None

    @property
    def is_play_from_start_enabled(self) -> bool:
        """Whether the active tab has a source that can start from the beginning."""
        return self._active_source() is not None

    @property
    def is_pause_enabled(self) -> bool:
        """Whether an engaged source is available to pause or resume."""
        target = self._target()
        return target is not None and target.is_engaged()

    @property
    def is_paused(self) -> bool:
        target = self._target()
        return target is not None and target.is_paused()

    @property
    def is_stop_enabled(self) -> bool:
        """Stop is available whenever any sound holds the output, a source or a preview, its stream opening
        included."""
        return self._output.is_sounding

    def _target(self) -> Optional[AudioPlayerProtocol]:
        active_source = self._active_source()
        if active_source is not None:
            return active_source

        return self._engaged_source()

    def _active_source(self) -> Optional[AudioPlayerProtocol]:
        """The active tab's own source when it has audio to play."""
        source = self._active_source_resolver()
        if source is not None and source.is_loaded():
            return source

        return None

    def _engaged_source(self) -> Optional[AudioPlayerProtocol]:
        """The intentional source that currently owns the device output, if any."""
        for source in self._sources:
            if source.is_engaged():
                return source

        return None
