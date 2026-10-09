from typing import List, Tuple

from sampletones_shared.logger import logger
from sampletones_tools.codec.study.corpus.projects import lengthened_song, project_song
from sampletones_tools.codec.study.corpus.reconstructions import reconstruction_paths, reconstruction_song
from sampletones_tools.codec.study.corpus.song import StudySong
from sampletones_tools.codec.study.manifest import StudyManifest, StudySource


def build_corpus(manifest: StudyManifest) -> Tuple[StudySong, ...]:
    """Reads every song the manifest names.

    Args:
        manifest: What the run reads.

    Returns:
        Tuple[StudySong, ...]: The projects as they stand, then each one lengthened, then every
            stem in manifest order.
    """
    songs: List[StudySong] = []
    for source in manifest.projects:
        logger.info(f"Reading project {source.path}")
        songs.append(project_song(source.path))

    for source in manifest.projects:
        logger.info(f"Lengthening project {source.path} to {manifest.lengthen_seconds} s")
        songs.append(lengthened_song(source.path, manifest.lengthen_seconds))

    for source in manifest.reconstructions:
        songs.extend(_reconstructions(source))

    return tuple(songs)


def _reconstructions(source: StudySource) -> List[StudySong]:
    paths = reconstruction_paths(source.path)
    songs: List[StudySong] = []
    for path in paths:
        logger.info(f"Reading stem {path}")
        name = source.label if len(paths) == 1 else f"{source.label}/{path.stem}"
        songs.append(reconstruction_song(name, path))

    return songs
