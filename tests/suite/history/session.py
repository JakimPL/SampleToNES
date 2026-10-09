from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Final, Iterator, List
from unittest.mock import patch

from sampletones_application.application import Application
from sampletones_application.coordinators.tabs.sequencer.coordinator import SequencerTabCoordinator
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.instruments import ReconstructionInstrumentsLogic
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_core.project import Project
from sampletones_core.project.container import ProjectContainer
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_shared.types.callback import Callback
from tests.suite.application import settled
from tests.suite.clipboard import FakeTextClipboard
from tests.suite.headless import headless_application, headless_context
from tests.suite.history.audit import HistoryAudit, fresh_fingerprint
from tests.suite.history.projects import EVERY_PART_FILENAME, write_every_part_project

TEXT_CLIPBOARD: Final[str] = "sampletones_application.coordinators.tabs.sequencer.coordinator.select_text_clipboard"


@dataclass(frozen=True)
class SequencerDoors:
    """Undo, redo and a jump as the application reaches them, each waiting for the edits before it."""

    coordinator: SequencerTabCoordinator

    def undo(self) -> None:
        self.coordinator.undo()

    def redo(self) -> None:
        self.coordinator.redo()

    def jump_to(self, index: int) -> None:
        self.coordinator.jump_to_history(index)


CONFIRM_POSITION: Final[int] = 3


def _confirmed(
    _renderer: DialogsRenderer,
    *arguments: Any,
    **keywords: Any,
) -> None:
    """A reader answering every confirmation with its confirming choice, however it was asked."""
    on_confirm: Callback = keywords["on_confirm"] if "on_confirm" in keywords else arguments[CONFIRM_POSITION]
    on_confirm()


def open_voice_faults(app: Application) -> List[str]:
    """Where the Reconstructions tab shows a voice the project holds otherwise, or no longer holds."""
    voice_id = app.reconstruction_manager.voice_id
    if voice_id is None:
        return []

    voice = app.project_controller.project.voices.get(voice_id)
    match voice:
        case None:
            return [f"The Reconstructions tab shows voice {voice_id}, which the project no longer holds"]
        case Sample() if app.reconstruction_manager.reconstruction is not voice.reconstruction:
            return [f"The Reconstructions tab shows another document than {voice.name!r} holds"]

    return []


@dataclass(frozen=True)
class HistorySession:
    """The whole application over the every-part project, its history held by an audit.

    A step reaches the application through the hook its panel calls, and the audit checks the
    history after it, the voice the Reconstructions tab shows included.
    """

    app: Application
    audit: HistoryAudit
    project_file: Path
    ids: Dict[str, str]

    @property
    def controller(self) -> ProjectController:
        return self.app.project_controller

    @property
    def history(self) -> HistoryManager:
        return self.app.history

    @property
    def project(self) -> Project:
        return self.app.project_controller.project

    @property
    def sequencer(self) -> SequencerTabCoordinator:
        return self.app._sequencer_tab

    @property
    def instruments(self) -> ReconstructionInstrumentsLogic:
        return self.app._reconstructions_tab._reconstruction_instruments_logic

    def sample(self, name: str) -> Sample:
        return next(voice for voice in self.project.voices if isinstance(voice, Sample) and voice.name == name)

    def instrument(self, name: str) -> Instrument:
        return next(voice for voice in self.project.voices if isinstance(voice, Instrument) and voice.name == name)

    def voice_id(self, name: str) -> str:
        """The id the opened file gave the voice called ``name``, which a rename or a copy leaves standing."""
        return self.ids[name]

    def reopen(self) -> None:
        """Opens the every-part project afresh, the stack starting over from it."""
        self.sequencer._sequencer_voices_panel.deselect()
        self.audit.transition(lambda: self.app._project_coordinator.load_project_safely(self.project_file))

    def open_voice(self, name: str) -> None:
        """Opens a voice on the Reconstructions tab, the way the voices list's Edit does."""
        self.open_voice_id(self.voice_id(name))

    def open_voice_id(self, voice_id: str) -> None:
        """Opens the voice ``voice_id`` names, which tells apart two voices of one name."""
        settled(lambda: self.app._reconstruction_coordinator.open_project_voice(voice_id))

    def mark_voice(self, name: str) -> None:
        """Marks a voice in the voices list, the target a replacement from the browser takes."""
        panel = self.sequencer._sequencer_voices_panel
        panel._selected_voice_id = self.voice_id(name)
        panel._selected_row = self.project.voices.get_index(self.voice_id(name))

    def save(self) -> None:
        """Saves the project to the file it was opened from, as the menu's Save does, after the edits on their way."""
        self.audit.save(self.save_door)

    def save_door(self) -> None:
        """The menu's Save, which waits for the edits of the open document made before it."""
        self.app._reconstruction_coordinator.after_edits(self.app._project_coordinator.save)

    def stored_fingerprint(self) -> str:
        """The state the project file holds, read back by a project manager of its own."""
        return fresh_fingerprint(ProjectContainer.load(self.project_file))


@contextmanager
def history_session(directory: Path) -> Iterator[HistorySession]:
    """Opens the every-part project in a headless application whose history the audit holds.

    The desktop's clipboard stands in memory, and a confirmation a gesture asks for is answered by
    confirming, so every gesture runs down the path a reader who agrees takes.
    """
    project_file = write_every_part_project(directory / EVERY_PART_FILENAME)
    with (
        patch.object(DialogsRenderer, "show_confirmation", _confirmed),
        patch(TEXT_CLIPBOARD, FakeTextClipboard),
        headless_context(),
    ):
        app = headless_application(directory)
        settled(lambda: app._project_coordinator.load_project_safely(project_file))
        audit = HistoryAudit(
            app.project_controller,
            app.history,
            budget=app.session_manager.history_budget,
            doors=SequencerDoors(app._sequencer_tab),
            settle=settled,
            observers=(lambda: _check_open_voice(app),),
        )
        ids = {voice.name: voice.id for voice in app.project_controller.project.voices}
        yield HistorySession(app=app, audit=audit, project_file=project_file, ids=ids)


def _check_open_voice(app: Application) -> None:
    faults = open_voice_faults(app)
    assert not faults, faults
