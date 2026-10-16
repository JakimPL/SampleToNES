import queue
import threading
from concurrent.futures import Future
from dataclasses import dataclass
from functools import partial
from importlib.metadata import version
from typing import Callable, Final, Optional, Tuple, TypeVar

from sampletones_application.utils.midi.backends.protocol import MidiPort, MidiSink
from sampletones_shared.exceptions import MidiPortError

from .library import DISTRIBUTION_NAME, LIBRARY_NAME, PortMidiInput, PortMidiLibrary
from .packing import wire_message

THREAD_NAME: Final[str] = "MidiPortMidi"
POLL_SECONDS: Final[float] = 0.001
BUFFER_SIZE: Final[int] = 4096
READ_BATCH: Final[int] = 64

ResultT = TypeVar("ResultT")
LibraryLoader = Callable[[], PortMidiLibrary]
Request = Callable[[], None]


@dataclass(frozen=True)
class _Reading:
    """The input being read, the name it was opened by, and what hears it."""

    name: str
    stream: PortMidiInput
    sink: MidiSink


class PortMidiBackend:
    """MIDI input through PortMidi, as pygame-ce carries it, which reaches Windows' and macOS's own MIDI services.

    PortMidi is called from one thread alone, which the backend owns. It loads the library at its first call, so
    pygame's import, which initializes the whole of pygame, stays off the caller's thread. It answers each call
    in order and reads the open input between them, polling, since PortMidi offers no wait.

    PortMidi's quirks shape the rest:

    - Its device list stays as it was at its initialization, so a listing initializes it again, and a port left
      open is opened again by its name, or told lost where the name is gone.
    - Inputs and outputs share one list, addressed by their place in it, and an input is opened only at a place
      the latest listing gave it, under the same name, since opening a place past the list ends the process.
    - Names arrive as bytes.
    - It raises a bare ``Exception`` on every failure, which a call hands its caller as ``MidiPortError``.
    """

    def __init__(self, load_library: LibraryLoader) -> None:
        """Holds what loads PortMidi on the backend's thread.

        Args:
            load_library: Imports the library, raising ``ImportError`` or ``OSError`` where it fails to load.
        """
        self._load_library = load_library
        self._requests: "queue.Queue[Request]" = queue.Queue()
        self._start_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._library: Optional[PortMidiLibrary] = None
        self._initialized: bool = False
        self._reading: Optional[_Reading] = None

    def describe(self) -> str:
        self._call(lambda library: None)
        return f"{LIBRARY_NAME} ({DISTRIBUTION_NAME} {version(DISTRIBUTION_NAME)})"

    def ports(self) -> Tuple[MidiPort, ...]:
        return self._call(self._relist)

    def open(self, port: MidiPort, sink: MidiSink) -> None:
        self._call(partial(self._open, port, sink))

    def close(self) -> None:
        if self._thread is not None:
            self._call(lambda library: self._stop_reading())

    def _call(self, request: Callable[[PortMidiLibrary], ResultT]) -> ResultT:
        """Runs ``request`` on the backend's thread and answers its result, raising what it raised.

        A call from the thread itself, as a sink's own call makes, runs at once.

        Raises:
            MidiPortError: If the library fails to load, or fails the request.
        """
        future: "Future[ResultT]" = Future()
        task = partial(self._run_request, request, future)
        if threading.current_thread() is self._thread:
            task()
        else:
            self._requests.put(task)
            self._ensure_thread()

        return future.result()

    def _run_request(self, request: Callable[[PortMidiLibrary], ResultT], future: "Future[ResultT]") -> None:
        """Answers ``request`` through ``future``: its result, or its failure as ``MidiPortError``.

        The caller waits on the future, so every failure is handed to it and raised there; PortMidi's own come as
        a bare ``Exception``.
        """
        try:
            future.set_result(request(self._loaded()))
        except MidiPortError as error:
            future.set_exception(error)
        except Exception as error:  # pylint: disable=broad-exception-caught
            future.set_exception(MidiPortError(f"PortMidi failed: {error}"))

    def _ensure_thread(self) -> None:
        with self._start_lock:
            if self._thread is None:
                self._thread = threading.Thread(target=self._serve, name=THREAD_NAME, daemon=True)
                self._thread.start()

    def _serve(self) -> None:
        """Answers each call in order, and reads the open input between calls while one is open."""
        while True:
            try:
                task = self._requests.get(timeout=POLL_SECONDS if self._reading is not None else None)
            except queue.Empty:
                self._read_waiting()
                continue

            task()
            self._read_waiting()

    def _loaded(self) -> PortMidiLibrary:
        if self._library is None:
            try:
                self._library = self._load_library()
            except (ImportError, OSError) as error:
                raise MidiPortError(f"PortMidi failed to load: {error}") from error

        return self._library

    def _relist(self, library: PortMidiLibrary) -> Tuple[MidiPort, ...]:
        """Lists the inputs as they stand now, opening a port left open again by its name."""
        reading = self._reading
        self._stop_reading()
        if self._initialized:
            library.Terminate()

        library.Initialize()
        self._initialized = True
        ports = self._inputs(library)
        if reading is not None:
            self._reopen(library, ports, reading)

        return ports

    def _reopen(self, library: PortMidiLibrary, ports: Tuple[MidiPort, ...], reading: _Reading) -> None:
        port = next((listed for listed in ports if listed.name == reading.name), None)
        if port is None:
            reading.sink.lost()
            return

        self._open(port, reading.sink, library)

    def _open(self, port: MidiPort, sink: MidiSink, library: PortMidiLibrary) -> None:
        """Opens ``port`` where the latest listing placed it under its name, closing the input open before."""
        self._stop_reading()
        if not self._initialized:
            raise MidiPortError(f"The port {port.name!r} comes from no listing of this PortMidi")

        device_id = port.address[0] if len(port.address) == 1 else -1
        if self._listed_name(library, device_id) != port.name:
            raise MidiPortError(f"The port {port.name!r} is no longer at its place in PortMidi's list")

        self._reading = _Reading(name=port.name, stream=library.Input(device_id, BUFFER_SIZE), sink=sink)

    def _stop_reading(self) -> None:
        reading, self._reading = self._reading, None
        if reading is not None:
            reading.stream.Close()

    def _read_waiting(self) -> None:
        """Hands the open input's waiting messages to its sink; a failing input is told lost and let go."""
        reading = self._reading
        if reading is None:
            return

        try:
            events = reading.stream.Read(READ_BATCH) if reading.stream.Poll() else ()
        except Exception:  # pylint: disable=broad-exception-caught
            self._reading = None
            reading.sink.lost()
            return

        for packed, _ in events:
            message = wire_message(packed)
            if message is not None:
                reading.sink.received(message)

    @staticmethod
    def _inputs(library: PortMidiLibrary) -> Tuple[MidiPort, ...]:
        ports = []
        for device_id in range(library.CountDevices()):
            info = library.GetDeviceInfo(device_id)
            if info is not None and info[2]:
                ports.append(MidiPort(name=info[1].decode(errors="replace"), address=(device_id,)))

        return tuple(ports)

    @staticmethod
    def _listed_name(library: PortMidiLibrary, device_id: int) -> Optional[str]:
        """The name of the input at ``device_id`` in the current list, or ``None`` where no input stands there."""
        if not 0 <= device_id < library.CountDevices():
            return None

        info = library.GetDeviceInfo(device_id)
        if info is None or not info[2]:
            return None

        return info[1].decode(errors="replace")
