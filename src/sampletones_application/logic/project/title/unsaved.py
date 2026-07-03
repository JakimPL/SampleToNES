from sampletones_application.logic.project.title.state import DocumentState


def is_any_unsaved(project: DocumentState, reconstruction: DocumentState) -> bool:
    return project.unsaved_changes or reconstruction.unsaved_changes
