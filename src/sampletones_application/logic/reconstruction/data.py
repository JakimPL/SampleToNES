from dataclasses import dataclass, replace
from functools import cached_property
from pathlib import Path
from typing import Dict, Optional, Self, Tuple

import numpy as np

from sampletones_application.logic.shared.renders import RenderCache
from sampletones_application.view_model.shared.waveform_data import WaveformData
from sampletones_core.audio import mix
from sampletones_core.configs import Config
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.recordings import load_recordings
from sampletones_core.reconstructions.reconstruction.renders import rendered_length
from sampletones_core.reconstructions.reconstruction.stems.hearing import (
    HeardRenders,
    Hearing,
    heard_renders,
)
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from sampletones_shared.logger import logger


@dataclass(frozen=True)
class ReconstructionData:
    """The open document beside what was read for it: its recordings and their mix.

    Attributes:
        name: The name the document is shown under.
        config: The configuration the document was converted at.
        reconstruction: The document itself.
        stem_audios: The loaded recordings, one per entry in entry order, or none at all.
        filepath: The file the document lives in, ``None`` for one held in memory.
        original_audio: The recorded source mixed into one waveform, ``None`` while no source loads.
    """

    name: str
    config: Config
    reconstruction: Reconstruction
    stem_audios: Tuple[np.ndarray, ...]
    filepath: Optional[Path]
    original_audio: Optional[np.ndarray]

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
        it had. It keeps the locations of its recordings, so its original audio loads again from them.
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
        copy shares the loaded recordings, so the original audio carries over without a reload.
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
        refreshes. The original mix carries over while the recordings stay the same, and is
        mixed again once an entry leaves or returns.
        """
        stem_audios = self._recordings_for(reconstruction)
        original_audio = self.original_audio if self._same_recordings(stem_audios) else self._mixed(stem_audios)
        return replace(
            self,
            reconstruction=reconstruction,
            config=reconstruction.config,
            stem_audios=stem_audios,
            original_audio=original_audio,
        )

    def _same_recordings(self, stem_audios: Tuple[np.ndarray, ...]) -> bool:
        """Whether ``stem_audios`` holds the very recordings this data holds, in the same order."""
        return len(stem_audios) == len(self.stem_audios) and all(
            incoming is held for incoming, held in zip(stem_audios, self.stem_audios)
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
        stem_audios = cls._load_stem_audios(reconstruction)
        return cls(
            config=reconstruction.config,
            reconstruction=reconstruction,
            stem_audios=stem_audios,
            filepath=filepath,
            name=name,
            original_audio=cls._mixed(stem_audios),
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
        """Loads the recorded source, one recording per path, in path order.

        Every recording is read at the level its conversion read it at, which the document
        records, so one heard on its own sounds at the level it holds in the mix, and it keeps
        that level once another recording leaves the document.

        A reconstruction detached from its origin (a project sample) records no source
        path, and a file-backed reconstruction may point at audio absent or unreadable on
        this machine. One unreadable stem costs the whole original, so the recordings
        come back as one empty tuple in either case; the approximation then stands on its
        own in playback and the display.
        """
        try:
            return load_recordings(reconstruction)
        except (FileNotFoundError, IsADirectoryError, PermissionError, OSError) as error:
            logger.warning(f"Could not load the original audio: {error}. The original is unavailable")
            return ()

    @staticmethod
    def _mixed(stem_audios: Tuple[np.ndarray, ...]) -> Optional[np.ndarray]:
        """The recordings mixed into one waveform, ``None`` where none loaded."""
        return mix(list(stem_audios)) if stem_audios else None

    @cached_property
    def _stem_recording_indexes(self) -> Dict[int, int]:
        """Maps each stem id to the index of its recording in ``stem_audios``.

        The entries' ids map to their recordings in entry order, and source audio absent
        or unreadable maps nothing.
        """
        if not self.stem_audios:
            return {}

        stems_data = self.reconstruction.stems_data
        return {entry.id: index for index, entry in enumerate(stems_data.config.entries)}

    def original_mix_for(self, selection: StemSelection) -> Optional[np.ndarray]:
        """The original audio of the stems heard anywhere.

        Returns:
            Optional[np.ndarray]: The mix of the recordings heard, silence where the recordings
            loaded and none of them is heard, and ``None`` where no recording loaded, which leaves
            the approximation on its own in playback and the display.
        """
        if not self.stem_audios:
            return None

        selected_stem_ids = selection.any_channel()
        indexes = self._stem_recording_indexes
        if selected_stem_ids >= indexes.keys():
            return self.original_audio

        recordings = [self.stem_audios[index] for stem_id, index in indexes.items() if stem_id in selected_stem_ids]
        if not recordings:
            return np.zeros(rendered_length(self.reconstruction), dtype=np.float32)

        return mix(recordings)

    def waveform_data(
        self,
        renders: RenderCache,
        hearing: Hearing,
    ) -> Optional[WaveformData]:
        """Projects the slice of this data the waveform display renders, the audio read from ``renders``.

        The projection carries what ``hearing`` sounds of the document and the mix of the
        recordings heard anywhere, so the waveform answers exactly what plays. The audio is read
        from what the cache keeps, so the reading computes no sample.

        Returns:
            Optional[WaveformData]: The projection, or ``None`` where the cache keeps no audio for
            ``hearing`` yet, which is what a worker is then asked to render.
        """
        heard = renders.reading(self.reconstruction, hearing)
        if heard is None:
            return None

        return self._waveform_data(self.original_mix_for(hearing.selection), heard)

    def audio_for(
        self,
        renders: RenderCache,
        hearing: Hearing,
    ) -> np.ndarray:
        """What ``hearing`` plays of the document, rendered here where the cache keeps none of it.

        An export writes what plays and runs where the reader waits for it, so it reads what is
        kept and renders the rest on the spot.
        """
        heard = renders.reading(self.reconstruction, hearing)
        if heard is not None:
            return heard.playing

        channels = renders.channels(self.reconstruction)
        return heard_renders(self.reconstruction, hearing, channels, renders.mix(self.reconstruction)).playing

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
