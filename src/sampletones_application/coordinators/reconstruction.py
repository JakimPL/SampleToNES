from pathlib import Path
from typing import Callable, Optional

from sampletones_application.categories.elements.global_ import (
    DialogElements,
    FileFilterElements,
    GlobalDialogTitleElements,
    GlobalMessageElements,
)
from sampletones_application.categories.elements.reconstructions import (
    ReconstructionsBrowserElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, Tab, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.coordinators.tabs.reconstruction import (
    ReconstructionTabCoordinator,
)
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.services import (
    RegeneratedInstrument,
    RegenerationResult,
    RegenerationService,
    ServiceCancelled,
    ServiceError,
    ServiceSuccess,
)
from sampletones_application.tags.general import (
    TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION,
    TAG_GLOBAL_DIALOG_RECONSTRUCTION_SAVED,
)
from sampletones_application.utils.file_dialogs.api import (
    open_file_dialog,
    save_file_dialog,
)
from sampletones_application.utils.file_dialogs.result import ignore_none_path
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import Features
from sampletones_core.paths import EXT_FILE_RECONSTRUCTION
from sampletones_core.types.feature import FeatureValue
from sampletones_shared.exceptions import SampleToNESError
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import Callback, VoidCallback


class ReconstructionCoordinator:
    """
    The application's single authority on reconstruction document lifecycle.

    A reconstruction is a cross-cutting concern:
    - It can be opened from multiple entry points.
    - It must be saved before replacement.
    - Its dirty/saved state drives the window title.
    - Menu bar instrument regeneration flows through it so that all
      reconstruction mutations remain centralised.

    The separate ``set_reconstructions_tab`` call is a consequence of a mutual
    dependency that prevents passing the tab in the constructor; ``_tab`` asserts
    that this second step has been completed before first use.
    """

    def __init__(
        self,
        reconstruction_manager: ReconstructionManager,
        session_manager: SessionManager,
        regeneration_service: RegenerationService,
        audio_device_manager: AudioDeviceManager,
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
        on_tab_switch: Callback,
        on_session_state_changed: VoidCallback,
        on_reconstruction_updated: Callable[[RegeneratedInstrument], None],
        is_reconstruction_embedded: Callable[[], bool],
    ) -> None:
        self._reconstruction_manager = reconstruction_manager
        self._session_manager = session_manager
        self._regeneration_service = regeneration_service
        self._audio_device_manager = audio_device_manager
        self._reconstructions_tab: Optional[ReconstructionTabCoordinator] = None
        self._dialogs = dialogs
        self._language_manager = language_manager
        self._on_tab_switch = on_tab_switch
        self._on_session_state_changed_callback = on_session_state_changed
        self._on_reconstruction_updated_callback = on_reconstruction_updated
        self._is_reconstruction_embedded = is_reconstruction_embedded

        self._reconstruction_manager.session.on_state_changed = self._on_state_changed
        self._regeneration_service.subscribe(self._on_regeneration_result)
        self._reconstruction_manager.set_callbacks(
            on_reconstruction_loaded=self.on_reconstruction_loaded,
            on_reconstruction_closed=self._on_closed,
        )

    def set_reconstructions_tab(self, tab: ReconstructionTabCoordinator) -> None:
        self._reconstructions_tab = tab

    @property
    def _tab(self) -> ReconstructionTabCoordinator:
        if self._reconstructions_tab is None:
            raise RuntimeError("set_reconstructions_tab has not been called")

        return self._reconstructions_tab

    @property
    def reconstruction_name(self) -> Optional[str]:
        return self._reconstruction_manager.session.name

    def is_loaded(self) -> bool:
        return self._reconstruction_manager.session.is_loaded

    def is_unsaved(self) -> bool:
        return self._reconstruction_manager.session.unsaved_changes

    def is_saveable(self) -> bool:
        return self._reconstruction_manager.is_file_backed

    def _requires_save_confirmation(self) -> bool:
        """Reports pending edits that a save prompt can resolve.

        A prompt is warranted only for a standalone reconstruction with unsaved changes. A
        project-embedded reconstruction has no file of its own, and its edits belong to the
        project — closing or replacing it loses nothing, so it needs no prompt.
        """
        return self.is_unsaved() and not self._is_reconstruction_embedded()

    def check_loaded(self) -> bool:
        if not self.is_loaded():
            logger.warning("No reconstruction loaded; cannot proceed")
            self._dialogs.show_reconstruction_not_loaded()
            return False

        return True

    def save_as_dialog(self) -> None:
        reconstruction_data = self._reconstruction_manager.current_reconstruction
        if reconstruction_data is None:
            return

        filepath = reconstruction_data.filepath
        if filepath is not None:
            default_filename = filepath.name
            default_path = str(filepath.parent)
        else:
            default_filename = f"{reconstruction_data.name}{EXT_FILE_RECONSTRUCTION}"
            default_path = str(self._session_manager.get_reconstruction_path())

        filepath = save_file_dialog(
            title=self._language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.SAVE_RECONSTRUCTION,
            ],
            initial_directory=default_path,
            default_filename=default_filename,
            extensions=[EXT_FILE_RECONSTRUCTION],
            filter_name=self._language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.FILTER,
                FileFilterElements.RECONSTRUCTION,
            ],
        )

        self._handle_save_as(filepath)

    @ignore_none_path
    def _handle_save_as(self, filepath: Path) -> None:
        try:
            self._reconstruction_manager.save_reconstruction_as(filepath)
        except (OSError, SampleToNESError) as exception:
            logger.error_with_traceback(exception, f"Failed to save reconstruction to {filepath}")
            self._dialogs.show_error(
                exception,
                self._language_manager[
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.MESSAGE,
                    GlobalMessageElements.RECONSTRUCTION_SAVE_FAILED,
                ],
            )
            return

        self._session_manager.set_reconstruction_path(filepath.parent)
        self._session_manager.set_current_reconstruction(filepath)
        self._tab.display_reconstruction()
        self._dialogs.show_info(
            TAG_GLOBAL_DIALOG_RECONSTRUCTION_SAVED,
            self._language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.MESSAGE,
                GlobalMessageElements.RECONSTRUCTION_SAVED_SUCCESSFULLY,
            ],
            self._language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.RECONSTRUCTION_SAVED,
            ],
        )

    def _load_dialog(self) -> None:
        filepath = open_file_dialog(
            title=self._language_manager[
                Page.RECONSTRUCTIONS,
                Panel.BROWSER,
                TextType.TITLE,
                ReconstructionsBrowserElements.LOAD_RECONSTRUCTION_DIALOG,
            ],
            initial_directory=self._session_manager.get_reconstruction_path(),
            extensions=[EXT_FILE_RECONSTRUCTION],
            filter_name=self._language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.FILTER,
                FileFilterElements.RECONSTRUCTION,
            ],
        )

        self._handle_load(filepath)

    @ignore_none_path
    def load(self, filepath: Path) -> None:
        return self._tab.load_reconstruction(filepath)

    def load_with_confirmation(self, filepath: Optional[Path] = None) -> None:
        def load_reconstruction() -> None:
            if filepath is None:
                self._load_dialog()
            else:
                self.load(filepath)

        if self._requires_save_confirmation():
            self._show_save_confirmation(
                title=self._language_manager[
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.TITLE,
                    GlobalDialogTitleElements.LOAD_UNSAVED_RECONSTRUCTION,
                ],
                message=self._language_manager[
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.MESSAGE,
                    GlobalMessageElements.LOAD_UNSAVED_RECONSTRUCTION,
                ],
                on_save=self.save,
                on_confirm=load_reconstruction,
                ok_label=self._language_manager[
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.LABEL,
                    DialogElements.DISCARD,
                ],
            )
        else:
            load_reconstruction()

    def load_reconstruction_safely(self, path: Path) -> None:
        """Loads the persisted reconstruction when the application starts.

        Startup restore happens automatically, so a failed load is recovered silently:
        the stale session pointer is cleared so a missing, moved, or corrupt file leaves
        the next launch starting from a clean slate. Only known domain and I/O failures
        are absorbed; unexpected errors propagate.
        """
        try:
            self._reconstruction_manager.load_reconstruction(path)
        except (SampleToNESError, OSError) as exception:
            logger.warning(f"Could not restore reconstruction from {logger.format_path(path)}: {exception}")
            self._session_manager.set_current_reconstruction(None)

    def show_exit_save_confirmation(self, on_confirm: Callback) -> None:
        self._show_save_confirmation(
            title=self._language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.EXIT_CONFIRMATION,
            ],
            message=self._language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.MESSAGE,
                GlobalMessageElements.EXIT_UNSAVED_RECONSTRUCTION,
            ],
            on_save=self.save,
            on_confirm=on_confirm,
            ok_label=self._language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.LABEL,
                DialogElements.EXIT,
            ],
        )

    @ignore_none_path
    def _handle_load(self, filepath: Path) -> None:
        self._session_manager.set_reconstruction_path(filepath.parent)
        self._tab.load_reconstruction(filepath)

    def save(self, filepath: Optional[Path] = None) -> bool:
        """Saves the open reconstruction, reporting whether it was written.

        The exit and close prompts wait on this, so they proceed only once it lands on disk and
        hold otherwise.
        """
        return self._reconstruction_manager.save_reconstruction(filepath)

    def close_with_confirmation(self) -> None:
        if self._requires_save_confirmation():
            self._show_save_confirmation(
                title=self._language_manager[
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.TITLE,
                    GlobalDialogTitleElements.CLOSE_UNSAVED_RECONSTRUCTION,
                ],
                message=self._language_manager[
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.MESSAGE,
                    GlobalMessageElements.CLOSE_UNSAVED_RECONSTRUCTION,
                ],
                on_confirm=self._close,
                on_save=self.save,
                ok_label=self._language_manager[
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.LABEL,
                    DialogElements.CLOSE,
                ],
            )
        else:
            self._close()

    def _close(self) -> None:
        self._reconstruction_manager.close_reconstruction()

    def regenerate_instrument(
        self,
        generator_name: GeneratorName,
        features: Features,
        feature_key: FeatureKey,
        data: FeatureValue,
    ) -> None:
        reconstruction_data = self._reconstruction_manager.current_reconstruction
        if reconstruction_data is None:
            return

        accepted = self._regeneration_service.start(
            reconstruction_data.reconstruction,
            generator_name,
            features,
            feature_key,
            data,
        )
        if accepted:
            self._set_reconstruction_dimmed(True)

    def on_reconstruction_loaded(self) -> None:
        reconstruction_data = self._reconstruction_manager.current_reconstruction
        if reconstruction_data is None:
            raise RuntimeError("No reconstruction is loaded after loading process")

        self._audio_device_manager.stop()
        audio_filepath = reconstruction_data.reconstruction.audio_filepath
        if audio_filepath is not None and not audio_filepath.exists():
            self._dialogs.show_file_not_found(
                audio_filepath,
                self._language_manager[
                    Page.RECONSTRUCTIONS,
                    Panel.BROWSER,
                    TextType.MESSAGE,
                    ReconstructionsBrowserElements.AUDIO_FILE_NOT_FOUND,
                ],
            )

        filepath = reconstruction_data.filepath
        self._tab.display_reconstruction()
        self._session_manager.set_current_reconstruction(filepath)
        self._on_tab_switch(Tab.RECONSTRUCTIONS)

    def _on_closed(self) -> None:
        self._tab.close_reconstruction()
        self._session_manager.set_current_reconstruction(None)

    def _on_updated(self, outcome: RegeneratedInstrument) -> None:
        """Applies a regenerated reconstruction across the open document and project.

        The owning-sample hook runs first, while the manager still holds the prior
        reconstruction, so it can locate the owned sample by identity and record the
        edit against the project history, tagged with the channel and feature the
        ``outcome`` names. The open document then rebinds to the new reconstruction,
        keeping the editor and any owned sample sharing one object.
        """
        self._on_reconstruction_updated_callback(outcome)
        self._reconstruction_manager.apply_regenerated(outcome.reconstruction)
        self._tab.update_reconstruction()
        self._reconstruction_manager.mark_updated()

    def _on_regeneration_result(self, result: RegenerationResult) -> None:
        match result:
            case ServiceSuccess(value=outcome):
                self._on_updated(outcome)
            case ServiceError(exception=exception):
                logger.error_with_traceback(exception, "Regeneration failed")
                self._dialogs.show_error(exception)
            case ServiceCancelled():
                logger.info("Regeneration cancelled")

        self._set_reconstruction_dimmed(self._regeneration_service.is_running())

    def _set_reconstruction_dimmed(self, dimmed: bool) -> None:
        """Fades the reconstruction waveform while the regeneration worker is busy.

        The dim is driven off the service's own ``is_running`` span rather than counted per
        request, so a continuous edit stream keeps the waveform faded until the worker settles.
        Each finished result re-reads the live span: while more work is queued it stays faded,
        and it restores once the worker is idle.
        """
        if self._reconstructions_tab is None:
            return

        self._reconstructions_tab.set_reconstruction_dimmed(dimmed)

    def _on_state_changed(self) -> None:
        self._on_session_state_changed_callback()

    def _show_save_confirmation(
        self,
        title: str,
        message: str,
        on_save: Callable[[], bool],
        on_confirm: Callback,
        ok_label: str,
    ) -> None:
        self._dialogs.show_save_confirmation(
            tag=TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION,
            title=title,
            message=message,
            on_save=on_save,
            on_confirm=on_confirm,
            ok_label=ok_label,
        )
