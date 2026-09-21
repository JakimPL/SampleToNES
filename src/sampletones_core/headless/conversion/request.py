from functools import cached_property
from pathlib import Path
from typing import List, Optional, Self, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sampletones_core.constants.enums import (
    DEFAULT_CHANNELS,
    ChannelName,
    ordered_channels,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import (
    StemsConfig,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_shared.paths.extensions import EXT_FILES_AUDIO, is_audio_file
from sampletones_shared.utils.serialization import load_json
from sampletones_shared.utils.text import listed_items


def channels_named(stated: Optional[str]) -> List[ChannelName]:
    """The channels a run hands out: the ones named, comma separated, or the usual three.

    Raises:
        ValueError: If a name is none of the channels the hardware has.
    """
    if stated is None:
        return list(DEFAULT_CHANNELS)

    channels: List[ChannelName] = []
    for name in listed_items(stated):
        try:
            channels.append(ChannelName(name))
        except ValueError as error:
            known = ", ".join(channel.value for channel in ChannelName)
            raise ValueError(f"Unknown channel {name!r}; the channels are {known}.") from error

    return channels


def classic_setup(channels: Sequence[ChannelName]) -> StemsConfig:
    """The setup a single-source conversion runs under: one stem over the channels it was given."""
    return StemsConfig.single_entry(StemSettings.covering(ordered_channels(frozenset(channels))))


def load_stems(path: Path) -> StemsConfig:
    """The stems setup a JSON file holds, validated the way the ``.stn`` record is.

    Raises:
        ValueError: If no file stands at the path, the file holds anything other than a JSON
            mapping, or the mapping is no stems setup.
    """
    if not path.is_file():
        raise ValueError(f"No stems file at {path}.")

    loaded = load_json(path)
    if not isinstance(loaded, dict):
        raise ValueError(f"Stems file {path} must hold a mapping, got {type(loaded).__name__}.")  # noqa: TRY004

    return StemsConfig.model_validate(loaded)


class ConversionRequest(BaseModel):
    """What a headless conversion is asked for: the sources, the stems setup and where the result goes.

    The i-th source plays under the i-th entry of the setup. One directory stands for every
    recording under it, each converted alone under the setup's one stem, into the
    configuration's reconstructions directory.

    Attributes:
        sources: The recordings, or one directory of them.
        stems: The setup handing the channels out.
        output_path: The file the reconstruction of the recordings is written to, or ``None``
            for the configuration's own directory.
    """

    model_config = ConfigDict(frozen=True)

    sources: Tuple[Path, ...] = Field(min_length=1)
    stems: StemsConfig
    output_path: Optional[Path]

    @cached_property
    def directory(self) -> Optional[Path]:
        """The one directory the request converts file by file, or ``None`` for recordings.

        The sources are classified once, when the request is validated, and every later reading
        answers from that.
        """
        if len(self.sources) == 1 and self.sources[0].is_dir():
            return self.sources[0]

        return None

    @model_validator(mode="after")
    def _sources_are_recordings_or_one_directory(self) -> Self:
        """Raises:
        ValueError: If a directory stands among several sources, or a source names nothing or
            a file other than a recording.
        """
        if self.directory is not None:
            return self

        for source in self.sources:
            if source.is_dir():
                raise ValueError("Sources are recordings, or one directory alone.")

            if not source.exists():
                raise ValueError(f"No file at {source}.")

            if not is_audio_file(source):
                raise ValueError(f"{source} is no recording; a source is a {', '.join(EXT_FILES_AUDIO)} file.")

        return self

    @model_validator(mode="after")
    def _entries_pair_with_sources(self) -> Self:
        """Raises:
        ValueError: If the setup holds a different number of stems than there are sources.
        """
        entries = len(self.stems.entries)
        if self.directory is not None and entries != 1:
            raise ValueError(f"A directory is converted file by file under one stem; the setup holds {entries}.")

        if self.directory is None and entries != len(self.sources):
            raise ValueError(
                f"{len(self.sources)} sources for {entries} stems; a setup pairs one stem with each source, in order."
            )

        return self

    @model_validator(mode="after")
    def _output_names_the_one_file(self) -> Self:
        """Raises:
        ValueError: If an output path is given for a directory, whose reconstructions land in
            the configuration's directory.
        """
        if self.directory is not None and self.output_path is not None:
            raise ValueError(
                "A directory's reconstructions land in the configuration's reconstructions directory; "
                "an output path names the one file recordings are mixed into."
            )

        return self
