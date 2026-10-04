import errno
import os
from pathlib import Path
from typing import AbstractSet, Dict, FrozenSet, Iterator, List, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.converter.paths.fields import (
    ConfigDirectoryFields,
)
from sampletones_core.reconstructions.naming.derive import derive_name
from sampletones_shared.paths.extensions import (
    EXT_FILE_RECONSTRUCTION,
    EXT_FILES_AUDIO,
    is_audio_file,
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


def reconstructions_directory(config: Config) -> Path:
    """The directory holding the folder of every setting a run writes under."""
    return to_path(config.general.reconstructions_directory)


class ConfigDirectories:
    """The directories one configuration writes its reconstructions into, one per channel set.

    A directory is named after the settings that shaped the library and the channels the
    reconstruction was handed, so reconstructions that differ in either keep apart. The settings'
    part of the name, with its hash, is read once when this is built, and each channel set names
    its directory the first time it is asked for. A plan reads where its recordings are written
    through one of these, so the reading costs one hash, however many recordings it names.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._root = reconstructions_directory(config)
        self._settings_hash = ConfigDirectoryFields.settings_hash(config)
        self._named: Dict[FrozenSet[ChannelName], Path] = {}

    @property
    def root(self) -> Path:
        """The directory holding the directory of every channel set."""
        return self._root

    def directory(self, channels: AbstractSet[ChannelName]) -> Path:
        """The directory of the reconstructions handed ``channels``."""
        channel_set = frozenset(channels)
        directory = self._named.get(channel_set)
        if directory is None:
            fields = ConfigDirectoryFields.from_hashed_config(
                self._config,
                channel_set,
                settings_hash=self._settings_hash,
            )
            directory = self._root / fields.directory_name
            self._named[channel_set] = directory

        return directory


def config_directory_path(
    config: Config,
    channels: AbstractSet[ChannelName],
) -> Path:
    """The directory a reconstruction handed ``channels`` is written into, as :class:`ConfigDirectories` names it."""
    return ConfigDirectories(config).directory(channels)


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
    return named_output_path(config_directory_path(config, channels), sources, suffix)


def named_output_path(
    directory: Path,
    sources: Tuple[Path, ...],
    suffix: str = EXT_FILE_RECONSTRUCTION,
) -> Path:
    """Where the one reconstruction built from ``sources`` is written inside ``directory``.

    The file takes the name the source rules derive: one source names it after itself, and several
    after what they share.

    Raises:
        ValueError: If ``sources`` is empty.
    """
    return Path((directory / f"{derive_name(sources)}{suffix}").absolute())


def walk_entries(input_directory: Path) -> Iterator[Path]:
    """Every path below a directory, reported as the walk meets it.

    A caller that has to answer between entries — one counting what it has found, or one a reader
    may stop partway — reads the tree through this and decides for itself what each entry is. A
    folder below the directory that the reader may not open is passed over with everything it
    holds, so one locked folder leaves the rest of the tree to the walk.

    A POSIX directory opens its entries through its execute permission, so a directory may list its
    names and keep its entries closed. ``os.access`` reads that permission, and it answers True on
    Windows, whose folders carry none.

    Raises:
        OSError: If the directory itself cannot be opened, which leaves the walk nothing to read.
        PermissionError: If the directory lists its names and keeps its entries closed, which leaves
            the walk nothing to read either.
    """
    os.scandir(input_directory).close()
    if not os.access(input_directory, os.X_OK):
        raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(input_directory))

    return input_directory.rglob("*")


def walk_audio_files(
    input_directory: Path,
    extensions: Tuple[str, ...] = EXT_FILES_AUDIO,
) -> Iterator[Path]:
    """The recordings below a directory, reported as the walk meets them.

    A tree is read one entry at a time, so a caller reporting how far it has got hears from the
    walk while it runs rather than once it ends.
    """
    for path in walk_entries(input_directory):
        if is_audio_file(path, extensions):
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
