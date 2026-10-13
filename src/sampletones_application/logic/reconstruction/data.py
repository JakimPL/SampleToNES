from dataclasses import dataclass, replace
from functools import cached_property
from pathlib import Path
from typing import Dict, Optional, Self, Tuple

import numpy as np

from sampletones_application.logic.shared.renders import RenderCache
from sampletones_application.view_model.shared.waveform_data import WaveformData
from sampletones_core.configs import Config
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.recordings import load_recordings
from sampletones_core.reconstructions.reconstruction.renders import rendered_length
from sampletones_core.reconstructions.reconstruction.stems.hearing import (
    HeardRenders,
    Hearing,
)
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from sampletones_shared.logger import logger


@dataclass(frozen=True)
class ReconstructionData:
    """The open document beside the recordings read for it.

    Attributes:
        name: The name the document is shown under.
        config: The configuration the document was converted at.
        reconstruction: The document itself.
        stem_audios: The loaded recordings, one per entry in entry order, or none at all; each is
            read-only, since a worker mixes them while the render thread holds them.
        filepath: The file the document lives in, ``None`` for one held in memory.
    """

    name: str
    config: Config
    reconstruction: Reconstruction
    stem_audios: Tuple[np.ndarray, ...]
    filepath: Optional[Path]

    @classmethod
    def load(cls, path: Path) -> Self:
        reconstruction = Reconstruction.load(path)
        return cls._assemble(
            reconstruction,
            filepath=path,
            name=cls._derive_name(path),
        )

    @classmethod
    def from_reconstruction(cls, reconstruction: Reconstruction, *, name: str) -> Self:
        """Wraps an in-memory reconstruction for live-linked editing.

        The reconstruction tab edits the very same object the project sample
        holds, so changes propagate live. Such a sample lives only in memory,
        hence ``filepath`` is ``None`` and its display name is supplied by the
        caller (the project sample's name).

        A document whose file was removed in the Browser is wrapped the same way, under the name
        it had. It keeps the locations of its recordings, so they load again from them.
        """
        return cls._assemble(
            reconstruction,
            filepath=None,
            name=name,
        )

    def detached_copy(self, filepath: Path) -> Self:
        """Builds an independent, file-backed copy of this data anchored at ``filepath``.

        Save As writes the reconstruction to its own file and adopts this copy as the open
        document. The copy holds a reconstruction object of its own, which shares every part with
        the one it was copied from, so a document that was a project sample becomes a standalone
        entity: later edits reach only the saved file, leaving the project's sample unchanged. The
        copy shares the loaded recordings, so the mix of them the cache keeps serves it too.
        """
        reconstruction = self.reconstruction.model_copy()
        return replace(
            self,
            reconstruction=reconstruction,
            config=reconstruction.config,
            filepath=filepath,
            name=self._derive_name(filepath),
        )

    def with_reconstruction(self, reconstruction: Reconstruction) -> Self:
        """Rebinds this data to an edited reconstruction, keeping name and origin.

        An edit produces a fresh reconstruction object; the display name and file location
        stand, so the reconstruction and the recordings its entries hold are what the rebind
        refreshes.
        """
        return replace(
            self,
            reconstruction=reconstruction,
            config=reconstruction.config,
            stem_audios=self._recordings_for(reconstruction),
        )

    def _recordings_for(self, reconstruction: Reconstruction) -> Tuple[np.ndarray, ...]:
        """The loaded recordings, each following the entry it was loaded for.

        A recording belongs to the entry standing at its position, so an entry the edit keeps
        carries its audio to the position it now holds and an entry taken out releases it.
        Recordings the load left out stay out. A document naming an entry this one holds no
        recording for, such as one a restore brings back, comes back with no recording at all,
        the way a document whose audio fails to load does.
        """
        if not self.stem_audios:
            return ()

        positions = {entry.id: index for index, entry in enumerate(self.reconstruction.stems_data.config.entries)}
        incoming = reconstruction.stems_data.config.entries
        if any(entry.id not in positions for entry in incoming):
            return ()

        return tuple(self.stem_audios[positions[entry.id]] for entry in incoming)

    @classmethod
    def _assemble(
        cls,
        reconstruction: Reconstruction,
        *,
        filepath: Optional[Path],
        name: str,
    ) -> Self:
        return cls(
            config=reconstruction.config,
            reconstruction=reconstruction,
            stem_audios=cls._load_stem_audios(reconstruction),
            filepath=filepath,
            name=name,
        )

    @staticmethod
    def _derive_name(filepath: Path) -> str:
        """Names a document on disk after its file, for display and export.

        The converter names the file from every recording the conversion read, and a recording
        the document lets go of leaves that name standing, so the file carries the one name a
        document keeps whatever it holds.
        """
        return filepath.stem

    @staticmethod
    def _load_stem_audios(
        reconstruction: Reconstruction,
    ) -> Tuple[np.ndarray, ...]:
        """Loads the recorded source, one recording per path, in path order, each kept read-only.

        Every recording is read at the level its conversion read it at, which the document
        records, so one heard on its own sounds at the level it holds in the mix, and it keeps
        that level once another recording leaves the document. A worker mixes the recordings
        heard while the render thread holds them, so each is kept read-only and what both read
        stands as it was loaded.

        A reconstruction detached from its origin (a project sample) records no source
        path, and a file-backed reconstruction may point at audio absent or unreadable on
        this machine. One unreadable stem costs the whole original, so the recordings
        come back as one empty tuple in either case; the approximation then stands on its
        own in playback and the display.
        """
        try:
            recordings = load_recordings(reconstruction)
        except (FileNotFoundError, IsADirectoryError, PermissionError, OSError) as error:
            logger.warning(f"Could not load the original audio: {error}. The original is unavailable")
            return ()

        for recording in recordings:
            recording.setflags(write=False)

        return recordings

    @cached_property
    def recordings_by_stem(self) -> Dict[int, np.ndarray]:
        """The loaded recordings by the id of the entry each was loaded for, in record order, or none where
        the recordings are absent or unreadable.
        """
        if not self.stem_audios:
            return {}

        entries = self.reconstruction.stems_data.config.entries
        return {entry.id: self.stem_audios[index] for index, entry in enumerate(entries)}

    def recordings_heard(self, selection: StemSelection) -> Tuple[np.ndarray, ...]:
        """The loaded recordings ``selection`` hears anywhere, in record order."""
        heard = selection.any_channel()
        return tuple(recording for stem_id, recording in self.recordings_by_stem.items() if stem_id in heard)

    def waveform_data(
        self,
        renders: RenderCache,
        hearing: Hearing,
    ) -> Optional[WaveformData]:
        """Projects the slice of this data the waveform display renders, the audio read from ``renders``.

        The projection carries what ``hearing`` sounds of the document and the mix of the
        recordings heard anywhere, both read from what the cache keeps, so the reading computes
        no sample. A document whose recordings loaded and none of which is heard draws a silent
        original, answered here, and one with no recording loaded draws none.

        Returns:
            Optional[WaveformData]: The projection, or ``None`` where the cache keeps no audio for
            ``hearing`` yet or no mix of the recordings heard, which is what a worker is then
            asked to render.
        """
        heard = renders.reading(self.reconstruction, hearing)
        if heard is None:
            return None

        if not self.stem_audios:
            return self._waveform_data(None, heard)

        recordings = self.recordings_heard(hearing.selection)
        if not recordings:
            return self._waveform_data(np.zeros(rendered_length(self.reconstruction), dtype=np.float32), heard)

        original = renders.original(recordings, self.config)
        if original is None:
            return None

        return self._waveform_data(original, heard)

    def _waveform_data(
        self,
        original_audio: Optional[np.ndarray],
        heard: HeardRenders,
    ) -> WaveformData:
        return WaveformData(
            original_audio=original_audio,
            approximation=heard.mix,
            playing=heard.playing,
            coefficient=self.reconstruction.coefficient,
            frame_length=self.reconstruction.config.frame_length,
            sample_rate=self.reconstruction.config.sample_rate,
        )
