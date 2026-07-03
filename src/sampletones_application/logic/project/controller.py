from pathlib import Path
from typing import Optional

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MAX_TRANSPOSE, MAX_VOLUME, MIN_TRANSPOSE
from sampletones_core.famitracker.export import write_ftm
from sampletones_core.project import Project
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.patterns.row import NoteCommand, Row
from sampletones_core.project.song import Song
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
      respond precisely to the specific change.
    """

    def __init__(self, project_manager: ProjectManager) -> None:
        self._project_manager = project_manager

        self.on_project_replaced: Optional[VoidCallback] = None
        self.on_info_changed: Optional[VoidCallback] = None
        self.on_settings_changed: Optional[VoidCallback] = None
        self.on_samples_changed: Optional[VoidCallback] = None
        self.on_song_changed: Optional[VoidCallback] = None
        self.on_mutation: Optional[VoidCallback] = None

    @property
    def project(self) -> Project:
        return self._project_manager.current

    @property
    def song(self) -> Song:
        return self.project.song

    @property
    def order_length(self) -> int:
        return self.song.order_length()

    @property
    def is_open(self) -> bool:
        return self._project_manager.is_open

    @property
    def has_samples(self) -> bool:
        return bool(self.project.samples)

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

    def replace_project(self, project: Project) -> None:
        """Installs a project restored from history and rebuilds every dependent view.

        Undo and redo route through here rather than the fine-grained mutators: the
        whole project is swapped at once, so ``on_project_replaced`` fires to rebuild
        the tabs wholesale, mirroring how loading a project refreshes them. The
        fine-grained ``on_mutation`` signal stays silent because a restore is not a
        new user edit to record.
        """
        self._project_manager.install(project)
        self.call(self.on_project_replaced)

    def export_module(self, path: Path) -> None:
        write_ftm(path, self.project)

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

    def set_nes_frequency(self, nes_frequency: int) -> None:
        self.project.settings.nes_frequency = nes_frequency
        self._touch()
        self.call(self.on_settings_changed)

    def set_sample_rate(self, sample_rate: int) -> None:
        self.project.settings.sample_rate = sample_rate
        self._touch()
        self.call(self.on_settings_changed)

    def set_rows_per_pattern(self, rows_per_pattern: int) -> None:
        self.song.resize_patterns(rows_per_pattern)
        self._touch()
        self.call(self.on_song_changed)

    def add_sample(self, reconstruction: Reconstruction, name: str) -> Sample:
        """Embeds a reconstruction as a project sample, detaching its local source-audio origin.

        A project is a self-contained, shareable artifact, so a sample keeps only the reconstruction
        itself and the display name given here — never the author's local audio path.
        """
        reconstruction.detach_source()
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

    def set_sample_loop(self, sample_id: str, loop: bool) -> None:
        self.project.samples[sample_id].loop = loop
        self._touch()
        self.call(self.on_samples_changed)

    def is_sample_used(self, sample_id: str) -> bool:
        return self.song.references_sample(sample_id)

    def remove_sample(self, sample_id: str) -> None:
        self.project.samples.pop(sample_id)
        self.song.clear_sample_references(sample_id)
        self._touch()
        self.call(self.on_samples_changed)
        self.call(self.on_song_changed)

    def duplicate_sample(self, sample_id: str) -> Sample:
        """Appends an independent copy of a sample (same name and loop flag).

        The copy is appended, so existing samples keep their positions; it keeps the
        source name (like duplicated patterns), leaving renaming to the user.
        """
        clone = self.project.samples[sample_id].clone()
        self.project.samples.append(clone)
        self._touch()
        self.call(self.on_samples_changed)
        return clone

    def move_sample(self, sample_id: str, to_index: int) -> None:
        """Reorders the sample pool.

        Pattern rows reference samples by stable id, so reordering keeps every
        reference valid; it only changes the positional index the tracker displays,
        hence ``on_song_changed`` fires so the grid re-renders those indices.
        """
        self.project.samples.move(sample_id, to_index)
        self._touch()
        self.call(self.on_samples_changed)
        self.call(self.on_song_changed)

    def add_pattern(self, generator: GeneratorName) -> int:
        index = self.song.add_pattern(generator)
        self._touch()
        self.call(self.on_song_changed)
        return index

    def duplicate_pattern(self, generator: GeneratorName, pattern_index: int) -> int:
        clone_index = self.song.duplicate_pattern(generator, pattern_index)
        self._touch()
        self.call(self.on_song_changed)
        return clone_index

    def remove_pattern(self, generator: GeneratorName, pattern_index: int) -> None:
        self.song.remove_pattern(generator, pattern_index)
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

    def _existing_row(
        self,
        generator: GeneratorName,
        pattern_index: int,
        row_index: int,
    ) -> Row:
        """Reads a row even before its pattern has been created.

        An order position may reference an empty (uncreated) pattern; partial and
        clear edits treat that as a blank row, and :meth:`set_row` materialises the
        pattern when it writes.
        """
        pattern = self.song.pattern(generator, pattern_index)
        if pattern is None:
            return Row()

        return pattern.rows[row_index]

    def set_row(
        self,
        generator: GeneratorName,
        pattern_index: int,
        row_index: int,
        *,
        command: Optional[NoteCommand] = None,
        transpose: Optional[int] = None,
        volume: Optional[int] = None,
    ) -> None:
        """Replaces the whole row with the given values; omitted fields are cleared.

        This is the full-replace primitive used by :meth:`clear_row`. To change
        only some subcolumns while preserving the rest, use :meth:`update_row`.
        """
        row = Row(
            command=command,
            transpose=self._clamp_transpose(transpose),
            volume=self._clamp_volume(volume),
        )
        channel = self.song[generator]
        channel.ensure_pattern(
            pattern_index,
            self.song.rows_per_pattern,
        )
        channel.set_row(
            pattern_index,
            row_index,
            row,
        )
        self._touch()
        self.call(self.on_song_changed)

    def update_row(
        self,
        generator: GeneratorName,
        pattern_index: int,
        row_index: int,
        *,
        command: Optional[NoteCommand] = None,
        transpose: Optional[int] = None,
        volume: Optional[int] = None,
    ) -> None:
        """Updates only the provided subcolumns, preserving the rest of the row.

        ``None`` means "leave this subcolumn unchanged", so the tracker can edit a
        single subcolumn while the rest of the row carries over. For clearing a
        subcolumn, :meth:`set_row` interprets ``None`` as "clear".
        """
        existing = self._existing_row(generator, pattern_index, row_index)
        self.set_row(
            generator,
            pattern_index,
            row_index,
            command=command if command is not None else existing.command,
            transpose=transpose if transpose is not None else existing.transpose,
            volume=volume if volume is not None else existing.volume,
        )

    def clear_row(
        self,
        generator: GeneratorName,
        pattern_index: int,
        row_index: int,
        *,
        instrument: bool = True,
        transpose: bool = True,
        volume: bool = True,
    ) -> None:
        """Clears the selected subcolumns of a row, preserving the rest.

        Every subcolumn is cleared by default (a blank row); pass ``False`` for a
        subcolumn to keep its current value. With no selectors this is the inverse
        of :meth:`update_row`.
        """
        existing = self._existing_row(generator, pattern_index, row_index)
        self.set_row(
            generator,
            pattern_index,
            row_index,
            command=None if instrument else existing.command,
            transpose=None if transpose else existing.transpose,
            volume=None if volume else existing.volume,
        )

    def append_frame(self) -> None:
        self.song.append_frame()
        self._touch()
        self.call(self.on_song_changed)

    def insert_frame(self, position: int) -> None:
        self.song.insert_frame(position)
        self._touch()
        self.call(self.on_song_changed)

    def set_order_entry(
        self,
        generator: GeneratorName,
        position: int,
        pattern_index: Optional[int],
    ) -> None:
        self.song.set_order_entry(position, generator, pattern_index)
        self._touch()
        self.call(self.on_song_changed)

    def remove_frame(self, position: int) -> None:
        self.song.remove_frame(position)
        self._touch()
        self.call(self.on_song_changed)

    def move_frame(self, from_position: int, to_position: int) -> None:
        self.song.move_frame(from_position, to_position)
        self._touch()
        self.call(self.on_song_changed)

    def duplicate_frame(self, position: int) -> None:
        self.song.duplicate_frame(position)
        self._touch()
        self.call(self.on_song_changed)

    def clear_frame(self, position: int) -> None:
        self.song.clear_frame(position)
        self._touch()
        self.call(self.on_song_changed)

    def _touch(self) -> None:
        self.project.info.touch()
        self._project_manager.mark_updated()
        if self.on_mutation is not None:
            self.on_mutation()
