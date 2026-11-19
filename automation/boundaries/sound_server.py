import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Final, Optional, Tuple

PULSEAUDIO: Final[str] = "pulseaudio"
PULSE_SERVER_VARIABLE: Final[str] = "PULSE_SERVER"
UNIX_ADDRESS_PREFIX: Final[str] = "unix:"
SCRIPT_FILE: Final[str] = "server.pa"
SOCKET_FILE: Final[str] = "native"
LOG_FILE: Final[str] = "server.log"
RUNTIME_FOLDER: Final[str] = "runtime"
STATE_FOLDER: Final[str] = "state"
HOME_FOLDER: Final[str] = "home"
PRIVATE_FOLDER_MODE: Final[int] = 0o700
SILENT_SINK: Final[str] = "silence"
READY_SECONDS: Final[float] = 10.0
POLL_SECONDS: Final[float] = 0.05
STOP_SECONDS: Final[float] = 5.0
KEPT_VARIABLES: Final[Tuple[str, ...]] = ("PATH", "LANG")
SERVER_OPTIONS: Final[Tuple[str, ...]] = (
    "--daemonize=no",
    "--use-pid-file=no",
    "--exit-idle-time=-1",
    "--high-priority=no",
    "--realtime=no",
    "--disable-shm=yes",
    "--log-target=stderr",
    "-n",
)


class SoundServerMissingError(RuntimeError):
    """Raised when the PulseAudio server the scenarios' sound runs through is not installed."""


class SoundServerStartError(RuntimeError):
    """Raised when the scenarios' PulseAudio server exits or stays unreachable as it starts."""


class SoundServer:
    """A PulseAudio server of a worker's own, whose one sink plays into silence.

    A PortAudio built with a PulseAudio host API refuses to start where that host API reaches no
    server, so every scenario's application reaches this one. It reads no configuration of the
    machine's and offers a null sink alone, so the machine's own sound server and sound cards stay
    outside the run on every machine. PortAudio still plays through the scenario's ALSA device,
    the first host API it starts.
    """

    def __init__(self, folder: Path) -> None:
        self._folder = folder
        self._process: Optional[subprocess.Popen[bytes]] = None

    @property
    def address(self) -> str:
        """The address a client reaches the server under, which ``PULSE_SERVER`` carries."""
        return f"{UNIX_ADDRESS_PREFIX}{self._folder / SOCKET_FILE}"

    def start(self) -> str:
        """Starts the server and returns the address a client reaches it under.

        Raises:
            SoundServerMissingError: If PulseAudio is not installed.
            SoundServerStartError: If the server exits, or its socket stays absent, as it starts.
        """
        program = shutil.which(PULSEAUDIO)
        if program is None:
            raise SoundServerMissingError(
                f"{PULSEAUDIO} is not installed. Install it from the system's packages, such as the "
                f"{PULSEAUDIO} package on Debian and Ubuntu, to run the screen scenarios."
            )

        self._lay_out()
        with open(self._folder / LOG_FILE, "wb") as log:
            self._process = subprocess.Popen(
                (program, *SERVER_OPTIONS, "-F", str(self._folder / SCRIPT_FILE)),
                env=self._environment(),
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
            )

        self._wait_until_ready(self._process)
        return self.address

    def stop(self) -> None:
        """Stops the server, waiting a moment for it to end before it is killed."""
        process, self._process = self._process, None
        if process is None:
            return

        process.terminate()
        try:
            process.wait(timeout=STOP_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    def _lay_out(self) -> None:
        for name in (RUNTIME_FOLDER, STATE_FOLDER, HOME_FOLDER):
            (self._folder / name).mkdir(mode=PRIVATE_FOLDER_MODE, parents=True, exist_ok=True)

        (self._folder / SOCKET_FILE).unlink(missing_ok=True)
        script = (
            f"load-module module-null-sink sink_name={SILENT_SINK}\n"
            f"load-module module-native-protocol-unix socket={self._folder / SOCKET_FILE} auth-anonymous=1\n"
            f"set-default-sink {SILENT_SINK}\n"
        )
        (self._folder / SCRIPT_FILE).write_text(script, encoding="utf-8")

    def _environment(self) -> Dict[str, str]:
        """The server's own environment: the machine's programs, and every folder it writes inside its own."""
        environment = {name: os.environ[name] for name in KEPT_VARIABLES if name in os.environ}
        environment.update(
            {
                "HOME": str(self._folder / HOME_FOLDER),
                "XDG_RUNTIME_DIR": str(self._folder / RUNTIME_FOLDER),
                "XDG_CONFIG_HOME": str(self._folder / HOME_FOLDER / ".config"),
                "XDG_STATE_HOME": str(self._folder / STATE_FOLDER),
                "PULSE_RUNTIME_PATH": str(self._folder / RUNTIME_FOLDER / PULSEAUDIO),
                "PULSE_STATE_PATH": str(self._folder / STATE_FOLDER / PULSEAUDIO),
            }
        )
        return environment

    def _wait_until_ready(self, process: subprocess.Popen[bytes]) -> None:
        deadline = time.monotonic() + READY_SECONDS
        socket = self._folder / SOCKET_FILE
        while not socket.exists():
            if process.poll() is not None:
                raise SoundServerStartError(
                    f"{PULSEAUDIO} exited with status {process.returncode} as it started; "
                    f"its log is {self._folder / LOG_FILE}"
                )

            if time.monotonic() > deadline:
                self.stop()
                raise SoundServerStartError(
                    f"{PULSEAUDIO} opened no socket within {READY_SECONDS} seconds; "
                    f"its log is {self._folder / LOG_FILE}"
                )

            time.sleep(POLL_SECONDS)
