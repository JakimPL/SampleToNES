import json
import zipfile
from pathlib import Path
from typing import Dict

from pydantic import ValidationError

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.upgrade import read_version, upgrade_json
from sampletones_core.project.document import PROJECT_DATA_CONTRACT, ProjectDocument
from sampletones_core.project.project import Project
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.record import SampleRecord, VoiceRecord
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.structures import IdentifiedCollection
from sampletones_shared.constants.project import (
    PROJECT_DOCUMENT_NAME,
    RECONSTRUCTIONS_DIRECTORY,
)
from sampletones_shared.exceptions import (
    DeserializationError,
    IncompatibleProjectVersionError,
    IncorrectReconstructionDataError,
    InvalidProjectDataValuesError,
    LoadReconstructionError,
    MissingProjectDataFileError,
    NotAValidArchiveError,
    UnhandledProjectError,
)
from sampletones_shared.paths.extensions import EXT_FILE_RECONSTRUCTION
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import JSON_INDENT
from sampletones_shared.utils.system.paths import get_filename


class ProjectContainer:
    """Reads and writes a project as a compressed archive.

    The archive (``.stp``) is a zip holding a single ``project.json`` -- the
    validated :class:`ProjectDocument` -- plus one ``reconstructions/<id>.stn`` per
    unique reconstruction in its existing binary format. A sample embeds its
    reconstruction in memory but references it by ``reconstruction_id`` on disk,
    so a reconstruction shared by several voices is stored exactly once.

    The entire JSON shape lives in :class:`ProjectDocument`; this class only maps
    the domain to and from it and manages the reconstruction archive. It is a
    stateless namespace.
    """

    @staticmethod
    def save(project: Project, path: Pathlike) -> None:
        document = ProjectContainer._build_document(project)
        payload = document.model_dump_json(indent=JSON_INDENT).encode("utf-8")
        reconstructions = ProjectContainer._unique_reconstructions(project)

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(PROJECT_DOCUMENT_NAME, payload)
            for reconstruction_id, reconstruction in reconstructions.items():
                filename = get_filename(reconstruction_id, EXT_FILE_RECONSTRUCTION)
                name = f"{RECONSTRUCTIONS_DIRECTORY}/{filename}"
                archive.writestr(name, reconstruction.serialize())

    @staticmethod
    def load(path: Pathlike) -> Project:
        try:
            with zipfile.ZipFile(path, "r") as archive:
                document = ProjectContainer._read_document(archive.read(PROJECT_DOCUMENT_NAME))
                reconstructions = ProjectContainer._read_reconstructions(archive)
            return ProjectContainer._build_project(document, reconstructions)
        except zipfile.BadZipFile as exception:
            raise NotAValidArchiveError(f'The project file "{Path(path)}" is not a valid archive.') from exception
        except (LoadReconstructionError, DeserializationError) as exception:
            raise IncorrectReconstructionDataError(
                f'The project file "{Path(path)}" contains invalid reconstruction data: {exception}'
            ) from exception
        except KeyError as exception:
            raise MissingProjectDataFileError(
                f'The project "{Path(path)}" is incomplete: missing {exception}'
            ) from exception
        except (ValidationError, json.JSONDecodeError, UnicodeDecodeError) as exception:
            raise InvalidProjectDataValuesError(
                f'Failed to load project data from "{Path(path)}" due to validation error: {exception}',
                exception,
            ) from exception
        except IncompatibleProjectVersionError:
            raise
        except OSError:
            raise
        except Exception as exception:
            raise UnhandledProjectError(
                f'Unhandled project error while loading "{Path(path)}": {exception}'
            ) from exception

    @staticmethod
    def _read_document(raw: bytes) -> ProjectDocument:
        """The document an archive stores, upgraded, with its version checked before its shape.

        A document no upgrade reaches keeps the shape of the build that wrote it, so the version is
        checked first and the refusal names both versions. A document stating no version is read at
        the version its model gives it.

        Raises:
            IncompatibleProjectVersionError: If the document states a version no upgrade reaches.
            json.JSONDecodeError: If the document is not JSON.
            UnicodeDecodeError: If the document is not text.
            ValidationError: If the document's shape departs from the one this build reads.
        """
        payload = json.loads(upgrade_json(ObjectKind.PROJECT, raw))
        stated_version = read_version(ObjectKind.PROJECT, payload)
        if stated_version is not None:
            PROJECT_DATA_CONTRACT.validate_version(stated_version)

        return ProjectDocument.model_validate(payload)

    @staticmethod
    def _build_document(project: Project) -> ProjectDocument:
        return ProjectDocument(
            metadata=project.metadata,
            info=project.info,
            settings=project.settings,
            voices=[ProjectContainer._voice_record(voice) for voice in project.voices],
            song=project.song,
        )

    @staticmethod
    def _build_project(
        document: ProjectDocument,
        reconstructions: Dict[str, Reconstruction],
    ) -> Project:
        voices: IdentifiedCollection[VoiceUnion] = IdentifiedCollection()
        for record in document.voices:
            voices.append(ProjectContainer._restore_voice(record, reconstructions))

        return Project(
            metadata=document.metadata,
            info=document.info,
            settings=document.settings,
            voices=voices,
            song=document.song,
        )

    @staticmethod
    def _voice_record(voice: VoiceUnion) -> VoiceRecord:
        """The record a voice is written as: a reference for a sample, the whole of it for an instrument."""
        match voice:
            case Sample():
                return SampleRecord(
                    id=voice.id,
                    name=voice.name,
                    reconstruction_id=voice.reconstruction.id,
                )
            case Instrument():
                return voice

    @staticmethod
    def _restore_voice(
        record: VoiceRecord,
        reconstructions: Dict[str, Reconstruction],
    ) -> VoiceUnion:
        """The voice a record describes, resolving a sample's reconstruction from the archive.

        Raises:
            KeyError: If a sample record names a reconstruction the archive holds none of.
        """
        match record:
            case SampleRecord():
                sample = Sample(
                    name=record.name,
                    reconstruction=reconstructions[record.reconstruction_id],
                )
                sample.id = record.id
                return sample
            case Instrument():
                return record

    @staticmethod
    def _unique_reconstructions(project: Project) -> Dict[str, Reconstruction]:
        reconstructions: Dict[str, Reconstruction] = {}
        for voice in project.voices:
            if isinstance(voice, Sample):
                reconstructions[voice.reconstruction.id] = voice.reconstruction

        return reconstructions

    @staticmethod
    def _read_reconstructions(archive: zipfile.ZipFile) -> Dict[str, Reconstruction]:
        reconstructions: Dict[str, Reconstruction] = {}
        prefix = f"{RECONSTRUCTIONS_DIRECTORY}/"
        for name in archive.namelist():
            if name.startswith(prefix) and name.endswith(EXT_FILE_RECONSTRUCTION):
                reconstruction_id = Path(name).stem
                reconstructions[reconstruction_id] = Reconstruction.deserialize_data(
                    archive.read(name),
                    source=name,
                    validation=Reconstruction.validate_metadata,
                )

        return reconstructions
