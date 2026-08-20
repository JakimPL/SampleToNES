from dataclasses import dataclass, replace
from functools import cached_property
from pathlib import Path
from typing import AbstractSet, Dict, List, Optional, Self, Tuple

import numpy as np

from sampletones_application.logic.reconstruction.feature import FeatureData
from sampletones_application.view_model.shared.waveform_data import WaveformData
from sampletones_core.audio import load_audio, mix
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.naming.derive import derive_name
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.filter import (
    filter_approximations,
)
from sampletones_shared.logger import logger


@dataclass(frozen=True)
class ReconstructionData:
    name: str
    config: Config
    reconstruction: Reconstruction
    stem_audios: Tuple[np.ndarray, ...]
    feature_data: FeatureData
    filepath: Optional[Path]

    @classmethod
    def load(cls, path: Path) -> Self:
        reconstruction = Reconstruction.load(path)
        return cls._assemble(
            reconstruction,
            filepath=path,
            name=cls._derive_name(reconstruction, path),
        )

    @classmethod
    def from_reconstruction(cls, reconstruction: Reconstruction, *, name: str) -> Self:
        """Wraps an in-memory reconstruction for live-linked editing.

        The reconstruction tab edits the very same object the project sample
        holds, so changes propagate live. Such a sample lives only in memory,
        hence ``filepath`` is ``None`` and its display name is supplied by the
        caller (the project sample's name).
        """
        return cls._assemble(
            reconstruction,
            filepath=None,
            name=name,
        )

    def detached_copy(self, filepath: Path) -> Self:
        """Builds an independent, file-backed copy of this data anchored at ``filepath``.

        Save As writes the reconstruction to its own file and adopts this copy as the open
        document. The copy owns a fresh reconstruction object, so a document that was a project
        sample becomes a standalone entity: later edits reach only the saved file, leaving the
        project's sample unchanged. The copy shares the loaded recordings, so the original
        audio carries over without a reload.
        """
        reconstruction = self.reconstruction.model_copy(deep=True)
        return replace(
            self,
            reconstruction=reconstruction,
            config=reconstruction.config,
            feature_data=FeatureData.load(reconstruction),
            filepath=filepath,
            name=self._derive_name(reconstruction, filepath),
        )

    def with_reconstruction(self, reconstruction: Reconstruction) -> Self:
        """Rebinds this data to an edited reconstruction, keeping name and origin.

        A regeneration produces a fresh reconstruction object; the display name,
        file location and source audio are unchanged, so only the reconstruction
        and its derived features are refreshed.
        """
        return replace(
            self,
            reconstruction=reconstruction,
            config=reconstruction.config,
            feature_data=FeatureData.load(reconstruction),
        )

    @classmethod
    def _assemble(
        cls,
        reconstruction: Reconstruction,
        *,
        filepath: Optional[Path],
        name: str,
    ) -> Self:
        stem_audios = cls._load_stem_audios(reconstruction)
        feature_data = FeatureData.load(reconstruction)

        return cls(
            config=reconstruction.config,
            reconstruction=reconstruction,
            stem_audios=stem_audios,
            feature_data=feature_data,
            filepath=filepath,
            name=name,
        )

    @staticmethod
    def _derive_name(reconstruction: Reconstruction, filepath: Path) -> str:
        """Names the document after its source audio when present, otherwise after the file.

        A file-backed reconstruction keeps the audio's name for display and export; several
        source paths (stems) name the document through the source-naming rules, and a detached
        reconstruction (no source audio) falls back to the ``.stn`` filename.
        """
        source_paths = reconstruction.source_paths
        if source_paths:
            return derive_name(source_paths, fallback_stem=filepath.stem)

        return filepath.stem

    @staticmethod
    def _load_stem_audios(
        reconstruction: Reconstruction,
    ) -> Tuple[np.ndarray, ...]:
        """Loads the recorded source, one recording per path, in path order.

        A reconstruction detached from its origin (a project sample) records no source
        path, and a file-backed reconstruction may point at audio absent or unreadable on
        this machine. One unreadable stem costs the whole original, so the recordings
        come back as one empty tuple in either case; the approximation then stands on its
        own in playback and the display.
        """
        source_paths = reconstruction.source_paths
        if not source_paths:
            return ()

        config = reconstruction.config
        recordings: List[np.ndarray] = []
        for path in source_paths:
            try:
                recordings.append(
                    load_audio(
                        path=path,
                        target_sample_rate=config.library.sample_rate,
                        normalize=config.general.normalize,
                        quantize=config.general.quantize,
                    )
                )
            except (FileNotFoundError, IsADirectoryError, PermissionError, OSError):
                logger.warning(f"Could not load original audio from '{path}'. The original is unavailable")
                return ()

        return tuple(recordings)

    @cached_property
    def original_audio(self) -> Optional[np.ndarray]:
        """The recorded source mixed into one waveform, ``None`` while no source loads."""
        return mix(list(self.stem_audios)) if self.stem_audios else None

    @cached_property
    def _stem_recording_indexes(self) -> Dict[int, int]:
        """Maps each stem id to the index of its recording in ``stem_audios``.

        A stems reconstruction maps the entries' ids to their recordings in entry order, a
        single source presents one implicit stem (id 0) holding its recording, and source
        audio absent or unreadable maps nothing.
        """
        if not self.stem_audios:
            return {}

        stems_data = self.reconstruction.stems_data
        if stems_data is not None:
            return {entry.id: index for index, entry in enumerate(stems_data.config.entries)}

        return {0: 0}

    def original_mix_for(self, selected_stem_ids: AbstractSet[int]) -> np.ndarray:
        """The original audio of the selected stems, silence once none are selected."""
        indexes = self._stem_recording_indexes
        recordings = [self.stem_audios[index] for stem_id, index in indexes.items() if stem_id in selected_stem_ids]
        if not recordings:
            return np.zeros_like(self.reconstruction.approximation)

        return mix(recordings)

    def waveform_data(
        self,
        selected_stem_ids: Optional[AbstractSet[int]] = None,
    ) -> WaveformData:
        """Projects the slice of this data the waveform display renders.

        With a stems selection, the projection carries the selected stems' frames alone
        and their original mix, so the waveform answers exactly what plays.
        """
        if selected_stem_ids is None:
            return self._unfiltered_waveform()

        stems_data = self.reconstruction.stems_data
        if stems_data is None:
            return self._single_source_waveform(selected_stem_ids)

        return self._filtered_waveform(selected_stem_ids, stems_data)

    def _unfiltered_waveform(self) -> WaveformData:
        """The whole document: every channel's stored approximation and the full original."""
        return self._waveform_data(
            self.original_audio,
            dict(self.reconstruction.approximations),
            self.reconstruction.approximation,
        )

    def _single_source_waveform(self, selected_stem_ids: AbstractSet[int]) -> WaveformData:
        """The projection of a reconstruction that records no stems assignment.

        A recorded source with its one implicit stem unselected projects silence; every other
        selection projects the whole document.
        """
        if self.reconstruction.source_paths and not selected_stem_ids:
            return self._silenced_waveform()

        return self._unfiltered_waveform()

    def _filtered_waveform(
        self,
        selected_stem_ids: AbstractSet[int],
        stems_data: StemsData,
    ) -> WaveformData:
        """The selected stems' frames and their original mix, in the unfiltered shape."""
        approximations = filter_approximations(
            stems_data,
            self.reconstruction.approximations,
            selected_stem_ids,
            self.reconstruction.config.frame_length,
        )
        return self._waveform_data(
            self.original_mix_for(selected_stem_ids),
            approximations,
            mix(list(approximations.values())),
        )

    def _waveform_data(
        self,
        original_audio: Optional[np.ndarray],
        approximations: Dict[ChannelName, np.ndarray],
        approximation: np.ndarray,
    ) -> WaveformData:
        return WaveformData(
            original_audio=original_audio,
            approximation=approximation,
            approximations=approximations,
            coefficient=self.reconstruction.coefficient,
            frame_length=self.reconstruction.config.frame_length,
        )

    def _silenced_waveform(self) -> WaveformData:
        """A projection of silence in the shape of the reconstruction."""
        approximation = self.reconstruction.approximation
        return WaveformData(
            original_audio=np.zeros_like(approximation),
            approximation=np.zeros_like(approximation),
            approximations={
                channel: np.zeros_like(audio) for channel, audio in self.reconstruction.approximations.items()
            },
            coefficient=self.reconstruction.coefficient,
            frame_length=self.reconstruction.config.frame_length,
        )

    def get_partials(self, channel_names: List[ChannelName]) -> np.ndarray:
        return self.waveform_data().partials(channel_names)

    def partials_for(
        self,
        channel_names: List[ChannelName],
        selected_stem_ids: AbstractSet[int],
    ) -> np.ndarray:
        """Sums the selected channels with the unselected stems' frames silenced.

        A single source with its one stem unselected is silence, and a reconstruction
        recording no source answers its full approximation.
        """
        return self.waveform_data(selected_stem_ids).partials(channel_names)
