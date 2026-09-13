from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict

from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.voices.sample import Sample
from sampletones_tools.corpus.catalog import CatalogSpec, build_catalog
from sampletones_tools.corpus.module import ModuleConfig
from sampletones_tools.corpus.song import SongSpec, build_song
from sampletones_tools.corpus.synth import SynthConfig


@dataclass(frozen=True)
class Corpus:
    """The synthetic corpus: the reconstructed samples and the arrangement that plays them.

    Attributes:
        catalog: The samples, by name.
        project: The arrangement, carrying the samples as its voices.
    """

    catalog: Dict[str, Sample]
    project: Project


def build_project(
    catalog: Dict[str, Sample],
    module_config: ModuleConfig,
    song_spec: SongSpec,
) -> Project:
    """The arrangement playing the catalog under the module's identity and playback settings."""
    settings = ProjectSettings(
        tempo=module_config.tempo,
        speed=module_config.speed,
        nes_frequency=module_config.nes_frequency,
    )
    project = Project.create(
        title=module_config.title,
        author=module_config.author,
        settings=settings,
    )
    for sample in catalog.values():
        project.voices.append(sample)

    project.song = build_song(song_spec, catalog)
    return project


def build_synthetic_corpus() -> Corpus:
    """Renders, reconstructs and arranges the corpus the package describes.

    The recordings are rendered into a temporary directory of the build's own, which is gone once
    their reconstructions are made.

    Returns:
        Corpus: The samples and the arrangement.
    """
    with TemporaryDirectory() as recordings:
        catalog = build_catalog(CatalogSpec.load(), SynthConfig.load(), tmp_dir=Path(recordings))

    return Corpus(
        catalog=catalog,
        project=build_project(catalog, ModuleConfig.load(), SongSpec.load()),
    )
