from pathlib import Path
from typing import Optional, Tuple

from sampletones_application.logic.reconstruction.data import ReconstructionData
from sampletones_application.view_model.reconstruction.paths.path import ReconstructionPathViewModel
from sampletones_application.view_model.reconstruction.paths.state import ReconstructionPathState


def location_view_models(
    reconstruction_data: ReconstructionData,
) -> Tuple[ReconstructionPathViewModel, ReconstructionPathViewModel]:
    """The reconstruction's own file and its original audio, as the Source card names them.

    Each location is reported independently. A file-backed reconstruction knows its own file;
    one with no file, such as a project sample or a document whose file was removed, reports
    not-applicable. Its source audio is available when the recorded file loaded, not-found when
    a path is recorded yet its content is unavailable, and not-applicable when the
    reconstruction has been detached from its origin.
    """
    reconstruction_file = file_location(reconstruction_data.filepath)
    original_audio = audio_location(
        reconstruction_data.reconstruction.audio_filepath,
        loaded=bool(reconstruction_data.stem_audios),
    )
    return reconstruction_file, original_audio


def file_location(filepath: Optional[Path]) -> ReconstructionPathViewModel:
    if filepath is None:
        return ReconstructionPathViewModel(state=ReconstructionPathState.NOT_APPLICABLE, paths=())

    return ReconstructionPathViewModel(state=ReconstructionPathState.AVAILABLE, paths=(str(filepath),))


def audio_location(source_paths: Tuple[Path, ...], *, loaded: bool) -> ReconstructionPathViewModel:
    """Reports the original-audio location, treating a recorded path with unusable content
    the same as a missing one, so the source toggle and waveform agree with what actually loaded."""
    if source_paths and not loaded:
        return ReconstructionPathViewModel(state=ReconstructionPathState.NOT_FOUND, paths=())

    return ReconstructionPathViewModel(
        state=ReconstructionPathState.from_source_paths(source_paths),
        paths=tuple(str(path) for path in source_paths),
    )
