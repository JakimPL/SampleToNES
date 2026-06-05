import zipfile
from pathlib import Path
from typing import Dict

from sampletones_core.paths import EXT_FILE_RECONSTRUCTION
from sampletones_core.project.document import ProjectDocument
from sampletones_core.project.instruments.record import SampleRecord
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.project import Project
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.structures import IdentifiedCollection
from sampletones_shared.constants.project import (
    PROJECT_DOCUMENT_NAME,
    RECONSTRUCTIONS_DIRECTORY,
)
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import JSON_INDENT


class ProjectContainer:
    """Reads and writes a project as a compressed archive.

    The archive (``.stp``) is a zip holding a single ``project.json`` -- the
    validated :class:`ProjectDocument` -- plus one ``reconstructions/<id>.stn`` per
    unique reconstruction in its existing binary format. Samples embed
    reconstructions in memory but reference them by ``reconstruction_id`` on disk,
    so a reconstruction shared by several samples is stored exactly once.

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
                name = f"{RECONSTRUCTIONS_DIRECTORY}/{reconstruction_id}{EXT_FILE_RECONSTRUCTION}"
                archive.writestr(name, reconstruction.serialize())

    @staticmethod
    def load(path: Pathlike) -> Project:
        with zipfile.ZipFile(path, "r") as archive:
            document = ProjectDocument.model_validate_json(archive.read(PROJECT_DOCUMENT_NAME))
            reconstructions = ProjectContainer._read_reconstructions(archive)

        return ProjectContainer._build_project(document, reconstructions)

    @staticmethod
    def _build_document(project: Project) -> ProjectDocument:
        return ProjectDocument(
            metadata=project.metadata,
            info=project.info,
            settings=project.settings,
            samples=[
                SampleRecord(
                    id=sample.id,
                    name=sample.name,
                    reconstruction_id=sample.reconstruction.id,
                )
                for sample in project.samples
            ],
            song=project.song,
        )

    @staticmethod
    def _build_project(
        document: ProjectDocument,
        reconstructions: Dict[str, Reconstruction],
    ) -> Project:
        samples: IdentifiedCollection[Sample] = IdentifiedCollection()
        for record in document.samples:
            reconstruction = reconstructions[record.reconstruction_id]
            samples.append(ProjectContainer._restore_sample(record, reconstruction))

        return Project(
            metadata=document.metadata,
            info=document.info,
            settings=document.settings,
            samples=samples,
            song=document.song,
        )

    @staticmethod
    def _restore_sample(record: SampleRecord, reconstruction: Reconstruction) -> Sample:
        sample = Sample(name=record.name, reconstruction=reconstruction)
        sample.id = record.id
        return sample

    @staticmethod
    def _unique_reconstructions(project: Project) -> Dict[str, Reconstruction]:
        reconstructions: Dict[str, Reconstruction] = {}
        for sample in project.samples:
            reconstructions[sample.reconstruction.id] = sample.reconstruction

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
