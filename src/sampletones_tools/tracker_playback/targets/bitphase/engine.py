import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, List, Self, Tuple

from pydantic import BaseModel, ConfigDict

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PERIOD
from sampletones_shared.utils.system.programs import (
    locate_program,
    missing_program_message,
)
from sampletones_shared.utils.system.system import System
from sampletones_tools.tracker_playback.paths import BITPHASE_TRACE_SCRIPT_PATH
from sampletones_tools.tracker_playback.targets.protocol import PlaybackError
from sampletones_tools.tracker_playback.trace.sound import (
    ABSENT_REGISTER,
    ChannelSound,
    SongTrace,
    TickPosition,
)

NODE: Final[str] = "node"
NODE_PURPOSE: Final[str] = "a Bitphase checkout's own engine plays the exported documents"
TSX_CLI: Final[Path] = Path("node_modules") / "tsx" / "dist" / "cli.mjs"
CHECKOUT_FILES: Final[Tuple[Path, ...]] = (
    Path("cli") / "btp-loader.ts",
    Path("cli") / "resource-loader-node.ts",
    Path("src") / "lib" / "chips" / "registry-core.ts",
    Path("public") / "nes" / "nes-audio-driver.js",
    Path("public") / "nes" / "nes_apu.wasm",
    TSX_CLI,
)
SQUARE_TIMER_OFFSET: Final[int] = 1

INSTALL_HINTS: Final[Dict[System, str]] = {
    System.LINUX: "sudo apt install nodejs",
    System.MACOS: "brew install node",
    System.WINDOWS: "install Node.js from https://nodejs.org",
}


class EngineError(PlaybackError):
    """Bitphase's engine could not play a document: node is absent, the checkout lacks a file, or the run failed."""


class DriverChannel(BaseModel):
    """One channel as Bitphase's NES driver leaves it for the APU on a tick.

    Attributes:
        enabled: Whether the driver lets the channel sound.
        period: The tuning period the note resolves to, on the pulse and triangle channels.
        volume: The level the instrument and the volume column combine to.
        duty: The duty cycle, on the pulse channels.
        noise_period: The period index, on the noise channel.
        noise_mode: Whether the noise channel runs its short mode.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool
    period: int
    volume: int
    duty: int
    noise_period: int
    noise_mode: bool


class DriverTick(BaseModel):
    """What Bitphase's driver leaves every channel on one tick, and where in the song the tick falls.

    Attributes:
        frame: The order position being played.
        row: The row of that position's pattern.
        channels: The pulse, pulse, triangle and noise channels, in that order.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    frame: int
    row: int
    channels: Tuple[DriverChannel, DriverChannel, DriverChannel, DriverChannel]


class DriverTrace(BaseModel):
    """Every tick of one pass through a document, as the trace script writes it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticks: Tuple[DriverTick, ...]


@dataclass(frozen=True)
class BitphaseCheckout:
    """A Bitphase source checkout whose engine plays the documents, its packages installed.

    Attributes:
        root: The checkout's top directory.
    """

    root: Path

    @classmethod
    def located(cls, root: Path) -> Self:
        """The checkout at ``root``, once every file the trace loads from it is found there.

        Args:
            root: The checkout's top directory.

        Returns:
            Self: The checkout.

        Raises:
            EngineError: If a file the trace loads is missing, naming each one.
        """
        missing = [str(relative) for relative in CHECKOUT_FILES if not (root / relative).is_file()]
        if missing:
            raise EngineError(
                f"{root} is no Bitphase checkout with its packages installed; it lacks {', '.join(missing)}. "
                "Clone https://github.com/paator/bitphase and run pnpm install there."
            )

        return cls(root=root)


@dataclass(frozen=True)
class BitphaseEngine:
    """Bitphase's own engine, run through node over one checkout.

    Attributes:
        node: The node program.
        checkout: The checkout whose modules play the documents.
    """

    node: Path
    checkout: BitphaseCheckout

    @classmethod
    def located(cls, root: Path) -> Self:
        """The engine of the checkout at ``root``, played by the node this system has.

        Args:
            root: The checkout's top directory.

        Returns:
            Self: The engine.

        Raises:
            EngineError: If node is absent, naming how this system installs it, or the checkout lacks a
                file the trace loads.
        """
        node = locate_program(NODE)
        if node is None:
            raise EngineError(
                missing_program_message(
                    NODE,
                    NODE_PURPOSE,
                    INSTALL_HINTS,
                )
            )

        return cls(
            node=node,
            checkout=BitphaseCheckout.located(root),
        )

    def command(
        self,
        document: Path,
        output: Path,
    ) -> List[str]:
        """The command that plays ``document`` and writes its trace to ``output``.

        The checkout's own tsx runs the trace script, so the script loads the checkout's TypeScript
        modules the way its own command-line tools do. The script runs inside the checkout, so the
        document and the trace are named by absolute paths.

        Args:
            document: The `.btp` document to play.
            output: Where the trace is written.

        Returns:
            List[str]: The program and its arguments.
        """
        return [
            str(self.node),
            str(self.checkout.root / TSX_CLI),
            str(BITPHASE_TRACE_SCRIPT_PATH),
            str(self.checkout.root),
            str(document.resolve()),
            str(output.resolve()),
        ]

    def trace(
        self,
        document: Path,
        output: Path,
    ) -> SongTrace:
        """Plays a document through the engine and reads what every channel sounds on every tick.

        The trace is written to ``output`` and kept there, so a run can be read again by hand.

        Args:
            document: The `.btp` document to play.
            output: Where the trace is written.

        Returns:
            SongTrace: One pass through the document's song.

        Raises:
            EngineError: If the engine fails to play the document.
        """
        try:
            subprocess.run(
                self.command(document, output),
                cwd=self.checkout.root,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as error:
            raise EngineError(f"Bitphase failed to play {document}:\n{error.stderr}") from error

        return read_driver_trace(output.read_text(encoding="utf-8"))


def read_driver_trace(text: str) -> SongTrace:
    """What a trace script's output says every channel sounds, in the terms the application is read in.

    Args:
        text: The JSON the trace script wrote.

    Returns:
        SongTrace: One pass through the song.

    Raises:
        ValidationError: If the text is no trace the script writes.
    """
    trace = DriverTrace.model_validate_json(text)
    return SongTrace(
        positions=tuple(TickPosition(frame=tick.frame, row=tick.row) for tick in trace.ticks),
        channels={
            channel_name: tuple(driver_sound(channel_name, tick.channels[index]) for tick in trace.ticks)
            for index, channel_name in enumerate(ChannelName.items())
        },
    )


def driver_sound(
    channel_name: ChannelName,
    channel: DriverChannel,
) -> ChannelSound:
    """What the APU sounds of one channel the driver leaves, by the rules Bitphase's engine writes it by.

    Bitphase's `nes-apu-engine.js` silences a pulse or triangle channel whose period is zero, writes a
    pulse channel's timer as its period less one, and writes the triangle's timer as its period
    whole. The noise channel sounds whenever the driver enables it.

    Args:
        channel_name: The channel the driver's values belong to.
        channel: The values the driver left.

    Returns:
        ChannelSound: The channel's sound, in the registers the APU takes.
    """
    match channel_name:
        case ChannelName.PULSE1 | ChannelName.PULSE2:
            return ChannelSound(
                audible=channel.enabled and channel.period > 0,
                period=max(channel.period - SQUARE_TIMER_OFFSET, 0),
                volume=channel.volume,
                timbre=channel.duty,
            )
        case ChannelName.TRIANGLE:
            return ChannelSound(
                audible=channel.enabled and channel.period > 0,
                period=channel.period,
                volume=ABSENT_REGISTER,
                timbre=ABSENT_REGISTER,
            )
        case ChannelName.NOISE:
            return ChannelSound(
                audible=channel.enabled,
                period=channel.noise_period & MAX_PERIOD,
                volume=channel.volume,
                timbre=int(channel.noise_mode),
            )
