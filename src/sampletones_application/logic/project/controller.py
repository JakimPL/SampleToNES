from pathlib import Path
from typing import Optional

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MAX_TRANSPOSE, MAX_VOLUME, MIN_TRANSPOSE
from sampletones_core.project import Project
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.arrays import clamp
from sampletones_shared.utils.callbacks import CallbackMixin

from .manager import ProjectManager


class ProjectController(CallbackMixin):
    """
    The sole write surface for the current project.

    - Every mutation is atomic: the domain change, the dirty-state notification,
      and the observer signal always happen together.
    - Each mutation kind fires a distinct callback so that subscribers can
      respond precisely to what changed rather than polling or handling
      a coarse "something changed" event.
    """

    def __init__(self, project_manager: ProjectManager) -> None:
        self._project_manager = project_manager

        self.on_project_replaced: Optional[VoidCallback] = None
        self.on_info_changed: Optional[VoidCallback] = None
        self.on_settings_changed: Optional[VoidCallback] = None
        self.on_samples_changed: Optional[VoidCallback] = None
        self.on_song_changed: Optional[VoidCallback] = None

    @property
    def project(self) -> Project:
        return self._project_manager.current

    @property
    def is_open(self) -> bool:
        return self._project_manager.is_open

    @property
    def is_dirty(self) -> bool:
        return self._project_manager.is_dirty

    def new(self) -> None:
        self._project_manager.new()
        self.call(self.on_project_replaced)

    def close(self) -> None:
        self._project_manager.close()
        self.call(self.on_project_replaced)

    def load(self, path: Path) -> None:
        self._project_manager.load(path)
        self.call(self.on_project_replaced)

    def save(self, path: Path) -> None:
        self._project_manager.save(path)

    def mark_updated(self) -> None:
        self._touch()
        self.call(self.on_song_changed)

    def set_title(self, title: str) -> None:
        self.project.info.title = title
        self._touch()
        self.call(self.on_info_changed)

    def set_author(self, author: str) -> None:
        self.project.info.author = author
        self._touch()
        self.call(self.on_info_changed)

    def set_comment(self, comment: str) -> None:
        self.project.info.comment = comment
        self._touch()
        self.call(self.on_info_changed)

    def set_tempo(self, tempo: int) -> None:
        self.project.settings.tempo = tempo
        self._touch()
        self.call(self.on_settings_changed)

    def set_speed(self, speed: int) -> None:
        self.project.settings.speed = speed
        self._touch()
        self.call(self.on_settings_changed)

    def set_change_rate(self, change_rate: int) -> None:
        self.project.settings.change_rate = change_rate
        self._touch()
        self.call(self.on_settings_changed)

    def set_sample_rate(self, sample_rate: int) -> None:
        self.project.settings.sample_rate = sample_rate
        self._touch()
        self.call(self.on_settings_changed)

    def set_rows_per_pattern(self, rows_per_pattern: int) -> None:
        self.project.settings.rows_per_pattern = rows_per_pattern
        self._touch()
        self.call(self.on_settings_changed)

    def add_sample(self, reconstruction: Reconstruction, name: str) -> Sample:
        sample = Sample(name=name, reconstruction=reconstruction)
        self.project.samples.append(sample)
        self._touch()
        self.call(self.on_samples_changed)
        return sample

    def replace_sample_reconstruction(self, sample_id: str, reconstruction: Reconstruction) -> None:
        self.project.samples[sample_id].reconstruction = reconstruction
        self._touch()
        self.call(self.on_samples_changed)
        self.call(self.on_song_changed)

    def rename_sample(self, sample_id: str, name: str) -> None:
        self.project.samples[sample_id].name = name
        self._touch()
        self.call(self.on_samples_changed)
        self.call(self.on_song_changed)

    def remove_sample(self, sample_id: str) -> None:
        self.project.samples.pop(sample_id)
        self._purge_sample_references(sample_id)
        self._touch()
        self.call(self.on_samples_changed)
        self.call(self.on_song_changed)

    def add_pattern(self, generator: GeneratorName) -> Pattern:
        pattern = self.project.song[generator].add_pattern(self.project.settings.rows_per_pattern)
        self._touch()
        self.call(self.on_song_changed)
        return pattern

    def duplicate_pattern(self, generator: GeneratorName, pattern_id: str) -> Pattern:
        pattern = self.project.song[generator].duplicate_pattern(pattern_id)
        self._touch()
        self.call(self.on_song_changed)
        return pattern

    def remove_pattern(self, generator: GeneratorName, pattern_id: str) -> None:
        self.project.song[generator].remove_pattern(pattern_id)
        self._touch()
        self.call(self.on_song_changed)

    def _clamp_transpose(self, transpose: Optional[int]) -> Optional[int]:
        if transpose is None:
            return None

        return clamp(transpose, MIN_TRANSPOSE, MAX_TRANSPOSE)

    def _clamp_volume(self, volume: Optional[int]) -> Optional[int]:
        if volume is None:
            return None

        return clamp(volume, 0, MAX_VOLUME)

    def set_row(
        self,
        generator: GeneratorName,
        pattern_id: str,
        row_index: int,
        *,
        instrument: Optional[Instrument] = None,
        transpose: Optional[int] = None,
        volume: Optional[int] = None,
    ) -> None:
        """Replaces the whole row with the given values; omitted fields are cleared.

        This is the full-replace primitive used by :meth:`clear_row`. To change
        only some subcolumns while preserving the rest, use :meth:`update_row`.
        """
        row = Row(
            instrument=instrument,
            transpose=self._clamp_transpose(transpose),
            volume=self._clamp_volume(volume),
        )
        self.project.song[generator].set_row(
            pattern_id,
            row_index,
            row,
        )
        self._touch()
        self.call(self.on_song_changed)

    def update_row(
        self,
        generator: GeneratorName,
        pattern_id: str,
        row_index: int,
        *,
        instrument: Optional[Instrument] = None,
        transpose: Optional[int] = None,
        volume: Optional[int] = None,
    ) -> None:
        """Updates only the provided subcolumns, preserving the rest of the row.

        ``None`` means "leave this subcolumn unchanged", as opposed to
        :meth:`set_row`, which treats ``None`` as "clear". This lets the tracker
        edit a single subcolumn without wiping the others.
        """
        existing = self.project.song[generator].get_row(pattern_id, row_index)
        self.set_row(
            generator,
            pattern_id,
            row_index,
            instrument=instrument if instrument is not None else existing.instrument,
            transpose=transpose if transpose is not None else existing.transpose,
            volume=volume if volume is not None else existing.volume,
        )

    def clear_row(
        self,
        generator: GeneratorName,
        pattern_id: str,
        row_index: int,
    ) -> None:
        self.set_row(generator, pattern_id, row_index)

    def append_to_order(self, generator: GeneratorName, pattern_id: str) -> None:
        self.project.song[generator].append_to_order(pattern_id)
        self._touch()
        self.call(self.on_song_changed)

    def insert_into_order(
        self,
        generator: GeneratorName,
        index: int,
        pattern_id: str,
    ) -> None:
        self.project.song[generator].insert_into_order(index, pattern_id)
        self._touch()
        self.call(self.on_song_changed)

    def remove_from_order(self, generator: GeneratorName, index: int) -> None:
        self.project.song[generator].remove_from_order(index)
        self._touch()
        self.call(self.on_song_changed)

    def move_in_order(self, generator: GeneratorName, from_index: int, to_index: int) -> None:
        self.project.song[generator].move_in_order(from_index, to_index)
        self._touch()
        self.call(self.on_song_changed)

    def _purge_sample_references(self, sample_id: str) -> None:
        """
        Clears the instrument of any row that still points at a removed sample.

        Rows reference samples by id.
        """
        for channel in self.project.song.channels.values():
            for pattern in channel.patterns:
                for row_index, row in enumerate(pattern.rows):
                    if row.instrument is not None and row.instrument.sample_id == sample_id:
                        pattern.rows[row_index] = Row(
                            instrument=None,
                            transpose=row.transpose,
                            volume=row.volume,
                        )

    def _touch(self) -> None:
        self.project.info.touch()
        self._project_manager.mark_updated()
