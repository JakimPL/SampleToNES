from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Tuple

import numpy as np

from assets.demo.paths import (
    CONFIG_FILE,
    LIBRARY_FOLDER,
    PROJECTS_FOLDER,
    RECONSTRUCTIONS_FOLDER,
    RECORDINGS_FOLDER,
)
from assets.demo.render import leveled, render_stem
from assets.demo.specification import (
    DemoSpecification,
    InstrumentSpec,
    RecordingsSpec,
)
from sampletones_core.audio.io import write_wave
from sampletones_core.configs import Config
from sampletones_core.features.envelope import Envelope
from sampletones_core.headless.conversion.request import classic_setup
from sampletones_core.headless.conversion.runners import reconstruct_sources
from sampletones_core.headless.library import ensure_library
from sampletones_core.project import ProjectContainer
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.converter.paths.utils import (
    group_output_path,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import (
    StemsConfig,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import (
    StemEntry,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import (
    StemsHierarchy,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import (
    StemSettings,
)
from sampletones_shared.paths.extensions import EXT_FILE_PROJECT, EXT_FILE_WAVE
from sampletones_tools.corpus.build import build_project


def build_demo(destination: Path) -> Tuple[Path, ...]:
    """Writes the demo tree under ``destination`` and returns every file written, in writing order.

    The tree is a documents folder with the recordings beside it: the hits and the stems rendered
    from the voices, a configuration whose library and reconstructions folders lie in the tree, the
    library that configuration asks for, one reconstruction per hit and one of the whole piece, and
    the project arranging the hits and the instruments into a song. Each reconstruction names its
    recordings relative to the tree, so the tree reads the same wherever it is put, with the
    application run from inside it.

    Raises:
        FileExistsError: If the destination already holds files, which a fresh tree would mix with.
    """
    specification = DemoSpecification.load()
    root = destination.resolve()
    _require_empty(root)
    written: List[Path] = []
    recordings = _write_recordings(root, specification, written)
    config = _write_config(root, written)
    ensure_library(config)
    written.extend(sorted(config.library_directory.iterdir()))
    documents = _convert(root, specification, config, recordings)
    _relocate(root, documents.values())
    written.extend(documents.values())
    written.append(_write_project(root, specification, documents))
    return tuple(written)


def _require_empty(root: Path) -> None:
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"{root} already holds files; the demo tree is written into an empty folder")


def _write_recordings(
    root: Path,
    specification: DemoSpecification,
    written: List[Path],
) -> Dict[str, Path]:
    """Renders every hit and every stem to a WAV file, and returns each recording's path by its name."""
    recordings = specification.recordings
    voices = specification.voices.voices
    generator = np.random.default_rng(specification.voices.seed)
    folder = root / RECORDINGS_FOLDER
    paths: Dict[str, Path] = {}
    for hit in recordings.hits:
        audio = voices[hit.voice].render(sample_rate=recordings.sample_rate, generator=generator)
        paths[hit.name] = _write_recording(folder / f"{hit.name}{EXT_FILE_WAVE}", audio, recordings)

    piece = recordings.piece
    for stem in piece.stems:
        audio = render_stem(
            stem,
            voices,
            tempo=recordings.tempo,
            beats=piece.beats,
            sample_rate=recordings.sample_rate,
            generator=generator,
        )
        paths[stem.name] = _write_recording(
            folder / piece.name / f"{stem.name}{EXT_FILE_WAVE}",
            audio,
            recordings,
        )

    written.extend(paths.values())
    return paths


def _write_recording(path: Path, audio: np.ndarray, recordings: RecordingsSpec) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_wave(path, recordings.sample_rate, leveled(audio, recordings.amplitude))
    return path


def _write_config(root: Path, written: List[Path]) -> Config:
    """Writes the default configuration pointed at the tree's own library and reconstructions folders."""
    config = Config()
    general = config.general.model_copy(
        update={
            "library_directory": str(root / LIBRARY_FOLDER),
            "reconstructions_directory": str(root / RECONSTRUCTIONS_FOLDER),
        }
    )
    config = config.model_copy(update={"general": general})
    path = root / CONFIG_FILE
    config.save(path)
    written.append(path)
    return config


def _convert(
    root: Path,
    specification: DemoSpecification,
    config: Config,
    recordings: Mapping[str, Path],
) -> Dict[str, Path]:
    """Converts each hit alone and the stems together, and returns each document's path by its name."""
    del root
    conversion = specification.conversion
    documents: Dict[str, Path] = {}
    for hit in specification.recordings.hits:
        sources: Tuple[Path, ...] = (recordings[hit.name],)
        stems = classic_setup(list(conversion.hits[hit.name]))
        reconstruct_sources(sources, config, stems, None)
        documents[hit.name] = group_output_path(config, sources, stems.covered_channels)

    piece = specification.recordings.piece
    sources = tuple(recordings[stem.name] for stem in piece.stems)
    stems = _piece_setup(specification)
    reconstruct_sources(sources, config, stems, None)
    documents[piece.name] = group_output_path(config, sources, stems.covered_channels)
    return documents


def _piece_setup(specification: DemoSpecification) -> StemsConfig:
    """The setup converting the stems together: one entry per stem in piece order, on the declared levels."""
    conversion = specification.conversion.piece
    names = [stem.name for stem in specification.recordings.piece.stems]
    entries = tuple(
        StemEntry(
            id=index,
            settings=StemSettings.covering(list(conversion.stems[name])),
        )
        for index, name in enumerate(names)
    )
    levels = tuple(tuple(names.index(name) for name in level) for level in conversion.levels)
    return StemsConfig(
        entries=entries,
        hierarchy=StemsHierarchy(levels=levels, mode=conversion.mode),
    )


def _relocate(root: Path, documents: Iterable[Path]) -> None:
    """Rewrites each document to name its recordings relative to the tree, so the tree can be moved whole."""
    for path in documents:
        reconstruction = Reconstruction.load(path)
        relative = tuple(recording.relative_to(root) for recording in reconstruction.audio_filepath)
        relocated = reconstruction.model_copy(update={"stems_data": reconstruction.stems_data.with_sources(relative)})
        relocated.save(path)


def _write_project(
    root: Path,
    specification: DemoSpecification,
    documents: Mapping[str, Path],
) -> Path:
    """Arranges the hits and the instruments into the song and saves the project, returning its path."""
    catalog: Dict[str, VoiceUnion] = {
        hit.name: Sample(
            name=hit.name,
            reconstruction=Reconstruction.load(documents[hit.name]),
        )
        for hit in specification.recordings.hits
    }
    for name, instrument in specification.project.instruments.items():
        catalog[name] = _instrument(name, instrument)

    module = specification.project.module
    project = build_project(catalog, module, specification.project.song)
    project.info.created = specification.project.created
    project.info.modified = specification.project.created
    path = root / PROJECTS_FOLDER / f"{module.title}{EXT_FILE_PROJECT}"
    path.parent.mkdir(parents=True, exist_ok=True)
    ProjectContainer.save(project, path)
    return path


def _instrument(name: str, specification: InstrumentSpec) -> Instrument:
    return Instrument(
        name=name,
        envelopes=InstrumentEnvelopes(
            volume=Envelope[int](items=specification.volume),
            arpeggio=Envelope[int](items=specification.arpeggio),
            duty_cycle=Envelope[int](items=specification.duty_cycle),
        ),
        initial_pitch=specification.initial_pitch,
    )
