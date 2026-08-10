from typing import Final

from sampletones_application.application import Application
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager

HISTORY_BUDGET: Final[int] = 10
FIRST_HIGHLIGHT: Final[int] = 3
SECOND_HIGHLIGHT: Final[int] = 12


def _application() -> Application:
    """An application with only the attributes the properties commit touches, bypassing the full
    composition root constructor. History runs strict so an untracked mutation fails the test.
    """
    application = Application.__new__(Application)
    controller = ProjectController(ProjectManager())
    history = HistoryManager(controller, budget=HISTORY_BUDGET, strict=True)
    controller.on_mutation = history.handle_mutation
    controller.new()
    history.reset()
    application.project_controller = controller
    application.history = history
    return application


class TestPropertiesCommitHistory:
    """The properties dialog's commit lands as one undoable gesture: every changed field joins a
    single ``EDIT_PROJECT_PROPERTIES`` entry, and an unchanged confirmation records nothing.
    """

    def test_changed_fields_group_into_one_entry(self) -> None:
        application = _application()

        application._commit_project_properties(
            "Title",
            "Author",
            "Comment",
            FIRST_HIGHLIGHT,
            SECOND_HIGHLIGHT,
        )

        assert len(application.history.entries) == 2
        assert application.history.entries[-1].action is HistoryAction.EDIT_PROJECT_PROPERTIES
        info = application.project_controller.project.info
        assert (info.title, info.author, info.comment) == ("Title", "Author", "Comment")

    def test_the_metre_joins_the_same_entry_as_the_info(self) -> None:
        """The highlights are project settings, and the dialog commits them beside the info."""
        application = _application()

        application._commit_project_properties(
            "Title",
            "Author",
            "Comment",
            FIRST_HIGHLIGHT,
            SECOND_HIGHLIGHT,
        )

        settings = application.project_controller.project.settings
        assert (settings.first_highlight, settings.second_highlight) == (FIRST_HIGHLIGHT, SECOND_HIGHLIGHT)
        assert len(application.history.entries) == 2

    def test_unchanged_confirmation_records_nothing(self) -> None:
        application = _application()
        info = application.project_controller.project.info
        settings = application.project_controller.project.settings

        application._commit_project_properties(
            info.title,
            info.author,
            info.comment,
            settings.first_highlight,
            settings.second_highlight,
        )

        assert len(application.history.entries) == 1

    def test_undo_restores_the_previous_properties(self) -> None:
        application = _application()
        info = application.project_controller.project.info
        settings = application.project_controller.project.settings
        previous = (
            info.title,
            info.author,
            info.comment,
            settings.first_highlight,
            settings.second_highlight,
        )

        application._commit_project_properties(
            "Title",
            "Author",
            "Comment",
            FIRST_HIGHLIGHT,
            SECOND_HIGHLIGHT,
        )
        application.history.undo()

        info = application.project_controller.project.info
        settings = application.project_controller.project.settings
        assert (
            info.title,
            info.author,
            info.comment,
            settings.first_highlight,
            settings.second_highlight,
        ) == previous
