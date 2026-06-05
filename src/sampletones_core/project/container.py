from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.data import Metadata
from sampletones_core.paths import EXT_FILE_RECONSTRUCTION
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.sequencer import Instrument
from sampletones_core.structures import IndexedCollection
from sampletones_shared.constants.application import SAMPLETONES_PROJECT_DATA_VERSION
from sampletones_shared.constants.project import (
    PROJECT_DOCUMENT_NAME,
    RECONSTRUCTIONS_DIRECTORY,
)
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import JSON_INDENT

from .info import ProjectInfo
from .patterns.channel import Channel
from .patterns.pattern import Pattern
from .patterns.row import Row
from .project import Project
from .settings import ProjectSettings
from .song import Song


class ProjectContainer:
    """Reads and writes a project as a compressed archive.

    The archive (``.stp``) is a zip holding a single ``project.json`` describing
    the structure -- info, settings, instruments and the song -- plus one
    ``reconstructions/<id>.stn`` per unique reconstruction in its existing binary
    format. Instruments embed reconstructions in memory but reference them by
    ``reconstruction_id`` on disk, so a reconstruction shared by several
    instruments is stored exactly once.

    Every cross-reference inside the JSON (a row's subinstrument, a channel's
    order) is a stable uuid ``id``, never a collection position, so a loaded
    project resolves identically regardless of the order items were stored in.

    The class is a stateless namespace: all serialization logic lives in its
    static methods.
    """

    @staticmethod
    def save(project: Project, path: Pathlike) -> None:
        document = ProjectContainer._serialize_project(project)
        payload = json.dumps(document, indent=JSON_INDENT).encode("utf-8")
        reconstructions = ProjectContainer._unique_reconstructions(project)

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(PROJECT_DOCUMENT_NAME, payload)
            for reconstruction_id, reconstruction in reconstructions.items():
                name = f"{RECONSTRUCTIONS_DIRECTORY}/{reconstruction_id}{EXT_FILE_RECONSTRUCTION}"
                archive.writestr(name, reconstruction.serialize())

    @staticmethod
    def load(path: Pathlike) -> Project:
        with zipfile.ZipFile(path, "r") as archive:
            document = json.loads(archive.read(PROJECT_DOCUMENT_NAME).decode("utf-8"))
            reconstructions = ProjectContainer._read_reconstructions(archive)

        return ProjectContainer._deserialize_project(document, reconstructions)

    @staticmethod
    def _unique_reconstructions(project: Project) -> Dict[str, Reconstruction]:
        reconstructions: Dict[str, Reconstruction] = {}
        for instrument in project.instruments:
            reconstructions[instrument.reconstruction.id] = instrument.reconstruction

        return reconstructions

    @staticmethod
    def _read_reconstructions(archive: zipfile.ZipFile) -> Dict[str, Reconstruction]:
        reconstructions: Dict[str, Reconstruction] = {}
        prefix = f"{RECONSTRUCTIONS_DIRECTORY}/"
        for name in archive.namelist():
            if name.startswith(prefix) and name.endswith(EXT_FILE_RECONSTRUCTION):
                reconstruction_id = Path(name).stem
                reconstructions[reconstruction_id] = Reconstruction.deserialize(archive.read(name))

        return reconstructions

    @staticmethod
    def _serialize_project(project: Project) -> Dict[str, Any]:
        return {
            "format_version": SAMPLETONES_PROJECT_DATA_VERSION,
            "metadata": project.metadata.model_dump(mode="json"),
            "info": project.info.model_dump(mode="json"),
            "settings": project.settings.model_dump(mode="json"),
            "instruments": [
                {
                    "id": instrument.id,
                    "name": instrument.name,
                    "reconstruction_id": instrument.reconstruction.id,
                }
                for instrument in project.instruments
            ],
            "song": ProjectContainer._serialize_song(project.song),
        }

    @staticmethod
    def _serialize_song(song: Song) -> Dict[str, Any]:
        return {
            "channels": {
                generator.value: ProjectContainer._serialize_channel(channel)
                for generator, channel in song.channels.items()
            }
        }

    @staticmethod
    def _serialize_channel(channel: Channel) -> Dict[str, Any]:
        return {
            "generator": channel.generator.value,
            "patterns": [ProjectContainer._serialize_pattern(pattern) for pattern in channel.patterns],
            "order": list(channel.order),
        }

    @staticmethod
    def _serialize_pattern(pattern: Pattern) -> Dict[str, Any]:
        return {
            "id": pattern.id,
            "name": pattern.name,
            "rows": [row.model_dump(mode="json") for row in pattern.rows],
        }

    @staticmethod
    def _deserialize_project(document: Dict[str, Any], reconstructions: Dict[str, Reconstruction]) -> Project:
        instruments: IndexedCollection[Instrument] = IndexedCollection()
        for record in document["instruments"]:
            reconstruction = reconstructions[record["reconstruction_id"]]
            instruments.append(ProjectContainer._restore_instrument(record, reconstruction))

        return Project(
            metadata=Metadata.model_validate(document["metadata"]),
            info=ProjectInfo.model_validate(document["info"]),
            settings=ProjectSettings.model_validate(document["settings"]),
            instruments=instruments,
            song=ProjectContainer._deserialize_song(document["song"]),
        )

    @staticmethod
    def _restore_instrument(record: Dict[str, Any], reconstruction: Reconstruction) -> Instrument:
        instrument = Instrument(name=record["name"], reconstruction=reconstruction)
        instrument.id = record["id"]
        return instrument

    @staticmethod
    def _deserialize_song(document: Dict[str, Any]) -> Song:
        channels: Dict[GeneratorName, Channel] = {}
        for channel_document in document["channels"].values():
            channel = ProjectContainer._deserialize_channel(channel_document)
            channels[channel.generator] = channel

        return Song(channels=channels)

    @staticmethod
    def _deserialize_channel(document: Dict[str, Any]) -> Channel:
        patterns: IndexedCollection[Pattern] = IndexedCollection()
        for pattern_document in document["patterns"]:
            patterns.append(ProjectContainer._restore_pattern(pattern_document))

        return Channel(
            generator=GeneratorName(document["generator"]),
            patterns=patterns,
            order=list(document["order"]),
        )

    @staticmethod
    def _restore_pattern(document: Dict[str, Any]) -> Pattern:
        rows: List[Row] = [Row.model_validate(row) for row in document["rows"]]
        pattern = Pattern(rows=rows, name=document["name"])
        pattern.id = document["id"]
        return pattern
