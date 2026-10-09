import operator
from pathlib import Path

from automation.boundaries.dialogs import DialogKind
from automation.screen import Screen
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.project import ProjectContainer


def save_new_project(screen: Screen, path: Path) -> None:
    """Starts a new project and saves it to ``path`` through File ▸ Save project as."""
    screen.project.create()
    save_project_as(screen, path)


def save_project_as(screen: Screen, path: Path) -> None:
    """Saves the open project to ``path`` through File ▸ Save project as, and dismisses the notice."""
    project = screen.project
    screen.answer_next_dialog(DialogKind.SAVE, path)

    project.save_as()

    screen.expect(
        project.saved_notice.is_shown,
        bool,
        description="the project saved notice",
    )
    project.saved_notice.confirm()
    screen.expect(
        project.saved_notice.is_shown,
        operator.not_,
        description="the notice gone",
    )


def retitle_project(screen: Screen, title: str) -> None:
    """Types ``title`` into Project properties and confirms it, which leaves the project unsaved."""
    properties = screen.project.properties
    properties.open()
    screen.expect(properties.is_shown, bool, description="the Project properties dialog")

    properties.retitle(title)
    properties.confirm()

    screen.expect(properties.is_shown, operator.not_, description="the dialog closed")


def saved_project_title(path: Path) -> str:
    """The title the project file at ``path`` carries."""
    return ProjectContainer.load(path).info.title


def leave_letting_the_project_go(screen: Screen) -> None:
    """Exits, answering Exit to the question about the project, and waits for the application to stop."""
    prompt = screen.project.unsaved_prompt
    screen.press_shortcut(ShortcutId.EXIT)
    screen.expect(prompt.is_shown, bool, description="the question about the project")

    prompt.confirm()

    assert screen.wait_for_exit()
