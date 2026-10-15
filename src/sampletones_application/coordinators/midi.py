import threading
from functools import partial
from typing import Final, Optional, Tuple

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.ui.panels.dialogs.midi_settings import GUIMidiSettingsWindow
from sampletones_application.utils.callbacks.latest import LatestDelivery
from sampletones_application.utils.callbacks.priority import DEFAULT_PRIORITY
from sampletones_application.utils.gui.keyboard.router import PRIORITY_MODAL
from sampletones_application.utils.midi import MidiInputManager, MidiMessage, MidiRouter
from sampletones_application.utils.midi.backends import MidiInputBackend
from sampletones_application.utils.midi.manager import Clock
from sampletones_application.view_model.shared.midi_settings import MidiSettingsViewModel, last_key_label
from sampletones_core.audio.output import Post
from sampletones_shared.exceptions import MidiPortError
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import StringCallback

STARTUP_THREAD_NAME: Final[str] = "MidiStartup"


class _LastKey:
    """The dialog's scope: it names each key played on the dialog's line while the dialog stands."""

    def __init__(self, delivery: LatestDelivery[[str]], *, template: str, number_template: str) -> None:
        self._delivery = delivery
        self._template = template
        self._number_template = number_template

    def press(self, note: int, velocity: int) -> None:
        self._delivery.post(
            last_key_label(note, velocity, template=self._template, number_template=self._number_template)
        )

    def lift(self, note: int) -> None:
        del note


class MidiCoordinator:
    """Owns the MIDI keyboard: the input read, the dialog that picks it, and where its keys go.

    The keys reach the router on the MIDI library's thread, which hands each to the scope it belongs to. The
    dialog is one such scope, ranked as a modal: while it stands it names each key played, and the keys reach
    nothing behind it.

    The library loads on a thread of its own as the application starts, which then reads the keyboard the
    session kept, by its port's name; a keyboard absent this run is quietly left unread. Loading the library is
    the one slow call, so once it has loaded the dialog calls the manager from the render thread. A port picked
    in the dialog is read at once, so the reader tries the keyboard before keeping it; OK keeps it in the
    session with the velocity setting, and Cancel reads again the port the dialog opened with. A keyboard going
    away is told on the status bar.
    """

    def __init__(
        self,
        backend: MidiInputBackend,
        router: MidiRouter,
        session_manager: SessionManager,
        *,
        window: GUIMidiSettingsWindow,
        language_manager: LanguageManager,
        show_status: StringCallback,
        settle_seconds: float,
        clock: Clock,
        post: Post,
    ) -> None:
        self._router = router
        self._session_manager = session_manager
        self._window = window
        self._language_manager = language_manager
        self._show_status = show_status
        self._post = post
        self._manager = MidiInputManager(backend, listener=self, settle_seconds=settle_seconds, clock=clock)
        self._choosing = threading.Lock()
        self._chosen = threading.Event()
        self._available: Optional[bool] = None
        self._ports: Tuple[str, ...] = ()
        self._opening_port: Optional[str] = None
        self._refusal: Optional[str] = None

        router.register(
            _LastKey(
                LatestDelivery(window.show_line, priority=DEFAULT_PRIORITY),
                template=language_manager["settings.midi.template.last_key"],
                number_template=language_manager["settings.midi.template.key_number"],
            ),
            priority=PRIORITY_MODAL,
            active=lambda: window.is_open,
        )
        window.on_port_changed = self._change_port
        window.on_refresh = self._refresh
        window.on_commit = self._commit
        window.on_cancel = self._cancel

    def heard(self, message: MidiMessage) -> None:
        self._router.route(message)

    def lost(self, port_name: str) -> None:
        self._post(partial(self._tell_lost, port_name))

    def start(self) -> None:
        """Loads the library and reads the keyboard the session kept, on a thread of its own."""
        saved = self._session_manager.midi_port
        threading.Thread(target=partial(self._start, saved), name=STARTUP_THREAD_NAME, daemon=True).start()

    def open(self) -> None:
        """Shows the dialog with the inputs as they stand now, remembering the port it opened with."""
        self._opening_port = self._manager.port_name
        self._refusal = None
        if self._is_available():
            self._ports = self._listed()

        self._window.open(self._view_model())

    def close(self) -> None:
        """Lets the keyboard go for the teardown, which lets every key go with it."""
        self._manager.disconnect()

    def _start(self, saved: Optional[str]) -> None:
        """Loads the library, then reads ``saved`` where the reader picked no port meanwhile."""
        try:
            self._manager.describe()
        except MidiPortError as error:
            logger.info(f"MIDI input is unavailable: {error}")
            return

        if saved is None:
            return

        with self._choosing:
            if self._chosen.is_set():
                return

            try:
                self._manager.connect(saved)
            except MidiPortError as error:
                logger.warning(f"The MIDI keyboard {saved!r} could not be opened: {error}")

    def _is_available(self) -> bool:
        """Whether a MIDI library loaded, asking it once, waiting for a startup still loading it."""
        if self._available is None:
            try:
                self._manager.describe()
            except MidiPortError:
                self._available = False
            else:
                self._available = True

        return self._available

    def _listed(self) -> Tuple[str, ...]:
        try:
            return self._manager.ports()
        except MidiPortError as error:
            self._refusal = str(error)
            return ()

    def _change_port(self, port: Optional[str]) -> None:
        """Reads the port picked from now on, or none, telling in the dialog why a port failed to open."""
        self._chosen.set()
        with self._choosing:
            self._refusal = self._read(port)

        self._window.update_view(self._view_model())

    def _read(self, port: Optional[str]) -> Optional[str]:
        """Reads ``port``, answering why it failed to open, or ``None`` where it opened or none was asked for."""
        if port is None:
            self._manager.disconnect()
            return None

        try:
            if self._manager.connect(port):
                return None

            reason = self._language_manager["settings.midi.message.port_gone"]
        except MidiPortError as error:
            reason = str(error)

        return self._language_manager["settings.midi.template.refused"].format(port=port, reason=reason)

    def _refresh(self) -> None:
        self._refusal = None
        try:
            self._ports = self._manager.refresh()
        except MidiPortError as error:
            self._refusal = str(error)

        self._window.update_view(self._view_model())

    def _commit(self, velocity_sets_volume: bool) -> None:
        self._session_manager.set_midi_settings(
            self._manager.port_name,
            velocity_sets_volume=velocity_sets_volume,
        )
        self._window.hide()

    def _cancel(self) -> None:
        """Reads again the port the dialog opened with, where the reader picked another."""
        if self._manager.port_name != self._opening_port:
            with self._choosing:
                self._read(self._opening_port)

        self._window.hide()

    def _tell_lost(self, port_name: str) -> None:
        self._show_status(self._language_manager["settings.midi.template.lost"].format(port=port_name))
        if self._window.is_open:
            self._window.update_view(self._view_model())

    def _view_model(self) -> MidiSettingsViewModel:
        return MidiSettingsViewModel(
            available=bool(self._available),
            ports=self._ports,
            port=self._manager.port_name,
            velocity_sets_volume=self._session_manager.velocity_sets_volume,
            refusal=self._refusal,
        )
