from functools import partial
from pathlib import Path
from typing import Dict, Optional, Tuple

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.render.logic import SongRenderLogic
from sampletones_application.ui.panels.dialogs.render import GUIRenderWindow
from sampletones_application.utils.file_dialogs.api import save_file_dialog
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.utils.file_dialogs.result import ignore_none_path
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.view_model.shared.render import SongRenderViewModel
from sampletones_core.audio.writers import AudioFormat, capability_of
from sampletones_shared.types.callback import VoidCallback


class SongRenderCoordinator:
    """Owns writing the song to an audio file from the reader's side: the dialog, the destination
    it is asked for, and the report a finished render makes.

    The logic holds the render itself, so what is orchestrated here is the screen: the window
    opens over the settings the logic offers and follows every view it emits, the destination is
    asked for through the OS dialog, and each outcome leaves the window and raises the dialog that
    reports it.

    A render claims the application for as long as its dialog stands, so every way out passes
    through one close, which releases the claim and tells the application to read it again.
    """

    def __init__(
        self,
        render_logic: SongRenderLogic,
        *,
        window: GUIRenderWindow,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
        on_activity_changed: VoidCallback,
    ) -> None:
        self._logic = render_logic
        self._window = window
        self._dialogs = dialogs
        self._on_activity_changed = on_activity_changed
        self._view_model: Optional[SongRenderViewModel] = None
        self._window_open = False

        self._title_destination = language_manager["settings.render.title.destination_dialog"]
        self._title_rendered = language_manager["settings.render.title.rendered"]
        self._msg_rendered = language_manager["settings.render.message.rendered"]
        self._msg_failed = language_manager["settings.render.message.render_failed"]
        self._filter_names: Dict[AudioFormat, str] = {
            AudioFormat.WAVE: language_manager["global.dialog.filter.wave"],
            AudioFormat.MP3: language_manager["global.dialog.filter.mp3"],
        }

        self._logic.on_view_changed = self._on_view_changed
        self._logic.on_choose_destination = self._choose_destination
        self._logic.on_success = self._on_success
        self._logic.on_error = self._on_error
        self._logic.on_cancelled = self._on_cancelled

        self._window.on_settings_changed = self._logic.apply
        self._window.on_browse = self._logic.request_destination
        self._window.on_render = self._logic.start
        self._window.on_cancel = self._logic.cancel
        self._window.on_close = self._close

    @property
    def is_active(self) -> bool:
        """A render occupies the application from the dialog opening until it closes."""
        return self._logic.is_active

    def open(self) -> None:
        """Offers the render settings for the open song, over the document as it stands now."""
        if not self._logic.open():
            return

        self._window_open = True
        self._window.open(self._require_view_model())
        self._on_activity_changed()

    def cleanup(self) -> None:
        """Winds a running render down for application exit."""
        self._logic.cleanup()

    def _on_view_changed(self, view_model: SongRenderViewModel) -> None:
        """Keeps the open window standing at where the render has got to."""
        self._view_model = view_model
        if self._window_open:
            self._window.update_view(view_model)

    def _choose_destination(
        self,
        destination: Path,
        audio_format: AudioFormat,
    ) -> None:
        """Asks for the file the render writes, starting from the one the dialog stands at."""
        filepath = save_file_dialog(
            title=self._title_destination,
            initial_directory=destination.parent,
            default_filename=destination.name,
            filters=self._destination_filters(audio_format),
        )

        self._set_destination(filepath)

    @ignore_none_path
    def _set_destination(self, filepath: Path) -> None:
        self._logic.set_destination(filepath)

    def _destination_filters(self, audio_format: AudioFormat) -> Tuple[FileFilter, ...]:
        """The type a destination is offered under: the container the dialog stands at.

        The format is chosen in the dialog itself, so the file type follows it and a name typed
        without an extension takes the one that container is written under.
        """
        return (
            FileFilter.for_extensions(
                self._filter_names[audio_format],
                [capability_of(audio_format).extension],
            ),
        )

    def _on_success(self, destination: Path) -> None:
        """Reports the file a finished render wrote, as a path that opens in the file manager."""
        self._close()
        self._present(
            partial(
                self._dialogs.show_message_with_path,
                self._title_rendered,
                self._msg_rendered,
                destination,
            )
        )

    def _on_error(self, exception: Exception) -> None:
        """Reports what a render failed on, leaving the destination as it was."""
        self._close()
        self._present(partial(self._dialogs.show_error, exception, self._msg_failed))

    def _on_cancelled(self) -> None:
        """Closes the dialog of a render that was stopped, which leaves no file to report."""
        self._close()

    def _close(self) -> None:
        """Takes the dialog off screen and hands the application back."""
        self._window_open = False
        self._view_model = None
        self._window.hide()
        self._logic.close()
        self._on_activity_changed()

    def _present(self, raise_dialog: VoidCallback) -> None:
        """Raises ``raise_dialog`` once the frame the window left the screen in has finished.

        The render window is modal and DearPyGui carries one modal at a time, so a report waits
        for the frame that draws the screen without it and opens onto a clear screen.
        """
        FrameCallbackManager.set_frame_callback(raise_dialog)

    def _require_view_model(self) -> SongRenderViewModel:
        """The render the dialog opens on.

        Raises:
            SystemError: when the window is raised before the logic offers a view.
        """
        if self._view_model is None:
            raise SystemError("The render window is opened over the view the logic emits")

        return self._view_model
