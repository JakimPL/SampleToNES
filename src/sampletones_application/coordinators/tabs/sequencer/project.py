from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.tags.general import TAG_GLOBAL_DIALOG_NO_PROJECT_OPEN
from sampletones_application.utils.gui.dialogs import DialogsRenderer


class OpenProjectRequirement:
    """What a gesture needing somewhere to put its result asks before it starts.

    A voice, a reconstruction and an import all land in the open project, so each asks here
    first. Answering that nothing is open also tells the reader so, leaving the caller with
    only the decision to stop.
    """

    def __init__(
        self,
        project_controller: ProjectController,
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
    ) -> None:
        self._project_controller = project_controller
        self._dialogs = dialogs
        self._message = language_manager["global.dialog.message.no_project_open"]
        self._title = language_manager["global.dialog.title.no_project_open"]

    def met(self) -> bool:
        """Whether a project stands open, showing the notice when none does."""
        if self._project_controller.is_open:
            return True

        self._dialogs.show_info(
            TAG_GLOBAL_DIALOG_NO_PROJECT_OPEN,
            self._message,
            self._title,
        )
        return False
