from typing import Optional

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.tags.general import TAG_GLOBAL_DIALOG_NO_AUDIO_OUTPUT
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_shared.exceptions import NoOutputDeviceError


class PlaybackFailurePresenter:
    """Tells the reader why a sound they asked for stays silent, whichever gesture asked for it.

    Every recovery boundary around a playback start hands its failure here, so what the reader sees
    is decided in one place. A machine offering no audio output is a fact about the machine, which a
    plain notice states in the reader's words. Any other failure is reported as an error with its
    details.
    """

    def __init__(
        self,
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
    ) -> None:
        self._dialogs = dialogs
        self._language_manager = language_manager

    def present(
        self,
        exception: Exception,
        *,
        message: Optional[str],
    ) -> None:
        """Shows the reader what stopped a playback.

        Args:
            exception: The failure the playback met.
            message: The line an error report opens with, or ``None`` for a report of the error
                alone.
        """
        match exception:
            case NoOutputDeviceError():
                self._dialogs.show_info(
                    TAG_GLOBAL_DIALOG_NO_AUDIO_OUTPUT,
                    self._language_manager["global.dialog.message.no_audio_output"],
                    self._language_manager["global.dialog.title.no_audio_output"],
                    modal=True,
                )
            case _:
                self._dialogs.show_error(exception, message)

    def present_later(self, exception: Exception) -> None:
        """Shows the reader what stopped a playback on the frame after the one that failed.

        A preview or an autoplay fails inside the gesture that asked for it, so the report waits for
        that gesture to finish before a dialog is raised.
        """
        FrameCallbackManager.set_frame_callback(lambda: self.present(exception, message=None))

    def present_playing_failure(self, exception: Exception) -> None:
        """Shows the reader what stopped a playback they asked for, such as a stream the device refused.

        Every source reports such a failure with the same opening line, whether its start failed at
        once or on the thread playing it, so one refusal reads alike on every tab.
        """
        self.present(exception, message=self._language_manager["global.dialog.message.audio_playback_error"])
