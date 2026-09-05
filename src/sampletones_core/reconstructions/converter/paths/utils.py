from pathlib import Path
from typing import AbstractSet, Iterator, List, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.converter.paths.fields import (
    ConfigDirectoryFields,
)
from sampletones_core.reconstructions.naming.derive import derive_name
from sampletones_shared.paths.extensions import (
    EXT_FILE_RECONSTRUCTION,
    EXT_FILES_AUDIO,
)
from sampletones_shared.utils.system.paths import to_path


def get_relative_path(
    base_directory: Path,
    audio_file: Path,
    output_path: Path,
    suffix: str = EXT_FILE_RECONSTRUCTION,
) -> Path:
    relative_path = audio_file.relative_to(base_directory)
    output_path = output_path / relative_path
    output_path = output_path.with_suffix(suffix)
    return Path(output_path.absolute())


def config_directory_path(
    config: Config,
    channels: AbstractSet[ChannelName],
) -> Path:
    """The directory a run writes its reconstructions into.

    The directory is named after the settings that shaped the library and the channels the run
    hands out, so runs that differ in either keep their results apart.
    """
    config_directory = ConfigDirectoryFields.generate_config_directory_name(config, channels)
    return to_path(config.general.reconstructions_directory) / config_directory


def get_output_path(
    config: Config,
    input_path: Path,
    channels: AbstractSet[ChannelName],
    suffix: str = EXT_FILE_RECONSTRUCTION,
) -> Path:
    """Where the reconstruction of one recording, or the folder of them, is written.

    ``channels`` names what the run hands out, which the configuration's own directory is named
    after alongside the settings that shaped the library.
    """
    output_directory = config_directory_path(config, channels)
    if input_path.is_dir():
        return output_directory / input_path.name

    if input_path.is_file():
        return output_directory / input_path.with_suffix(suffix).name

    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    raise OSError(f"Invalid path: {input_path}")


def group_output_path(
    config: Config,
    sources: Tuple[Path, ...],
    channels: AbstractSet[ChannelName],
    suffix: str = EXT_FILE_RECONSTRUCTION,
) -> Path:
    """Where the one reconstruction built from ``sources`` is written.

    The file sits in the configuration's own directory, under the name the source rules derive:
    one source names it after itself, and several after what they share
    (:func:`sampletones_core.reconstructions.naming.derive.derive_name`).

    ``channels`` names what the run hands out, which the configuration's own directory is named
    after.

    Raises:
        ValueError: If ``sources`` is empty.
    """
    output_directory = config_directory_path(config, channels)
    return Path((output_directory / f"{derive_name(sources)}{suffix}").absolute())


def walk_audio_files(
    input_directory: Path,
    extensions: Tuple[str, ...] = EXT_FILES_AUDIO,
) -> Iterator[Path]:
    """The recordings below a directory, reported as the walk meets them.

    A tree is read one entry at a time, so a caller reporting how far it has got hears from the
    walk while it runs rather than once it ends.
    """
    for path in input_directory.rglob("*"):
        if path.is_file() and path.suffix.lower() in extensions:
            yield path


def get_audio_files(
    input_directory: Path,
    extensions: Tuple[str, ...] = EXT_FILES_AUDIO,
    sort: bool = False,
) -> List[Path]:
    audio_files = list(walk_audio_files(input_directory, extensions))
    if sort:
        audio_files.sort()

    return audio_files


def holds_audio_files(
    input_directory: Path,
    extensions: Tuple[str, ...] = EXT_FILES_AUDIO,
) -> bool:
    """Whether a batch of this folder would find anything to convert.

    A batch reaches every recording below the folder, so the walk goes as deep and stops at the
    first one it meets, which is what makes the answer cheap enough for a gesture to ask for it.
    """
    return any(path.is_file() and path.suffix.lower() in extensions for path in input_directory.rglob("*"))


def filter_files(
    audio_files: List[Path],
    base_directory: Path,
    output_directory: Path,
) -> List[Path]:
    filtered_files = []
    for audio_file in audio_files:
        output_path = get_relative_path(
            base_directory,
            audio_file,
            output_directory,
        )
        if not output_path.exists():
            filtered_files.append(audio_file)

    return filtered_files
