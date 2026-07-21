from typing import List

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.data import Metadata
from sampletones_core.project.instruments.record import SampleRecord
from sampletones_shared.application import SAMPLETONES_PROJECT_DATA_VERSION

from .info import ProjectInfo
from .settings import ProjectSettings
from .song import Song


class ProjectDocument(BaseModel):
    """The single, validated schema for a project's ``project.json``.

    It embeds the domain :class:`Song` and represents samples as lightweight records,
    since their reconstructions live as separate ``.stn`` members of the archive.
    ``extra="ignore"`` lets it accept older or unknown fields, and ``format_version``
    carries the schema version that drives upgrades.
    """

    model_config = ConfigDict(extra="ignore")

    format_version: str = Field(
        default=SAMPLETONES_PROJECT_DATA_VERSION,
        description="Project file format version.",
        frozen=True,
    )
    metadata: Metadata
    info: ProjectInfo
    settings: ProjectSettings
    samples: List[SampleRecord]
    song: Song
