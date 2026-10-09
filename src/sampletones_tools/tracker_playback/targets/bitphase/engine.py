import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, List, Self, Tuple

from sampletones_shared.utils.system.programs import (
    locate_program,
    missing_program_message,
)
from sampletones_shared.utils.system.system import System
from sampletones_tools.tracker_playback.paths import BITPHASE_TRACE_SCRIPT_PATH
from sampletones_tools.tracker_playback.targets.bitphase.trace import read_engine_trace
from sampletones_tools.tracker_playback.targets.protocol import PlaybackError
from sampletones_tools.tracker_playback.trace.sound import SongTrace

NODE: Final[str] = "node"
NODE_PURPOSE: Final[str] = "the engine of Bitphase's source code plays the exported documents"
TSX_CLI: Final[Path] = Path("node_modules") / "tsx" / "dist" / "cli.mjs"
SOURCE_FILES: Final[Tuple[Path, ...]] = (
    Path("cli") / "btp-loader.ts",
    Path("cli") / "resource-loader-node.ts",
    Path("src") / "lib" / "chips" / "registry-core.ts",
    Path("public") / "nes" / "nes-audio-driver.js",
    Path("public") / "nes" / "nes-apu-engine.js",
    Path("public") / "nes" / "nes_apu.wasm",
    TSX_CLI,
)

INSTALL_HINTS: Final[Dict[System, str]] = {
    System.LINUX: "sudo apt install nodejs",
    System.MACOS: "brew install node",
    System.WINDOWS: "install Node.js from https://nodejs.org",
}


class EngineError(PlaybackError):
    """Bitphase's engine could not play a document: node is absent, the source code lacks a file, or the run failed."""


@dataclass(frozen=True)
class BitphaseSource:
    """A directory holding Bitphase's source code, its packages installed, whose engine plays the documents.

    Attributes:
        root: The source code's top directory.
    """

    root: Path

    @classmethod
    def located(cls, root: Path) -> Self:
        """The source code at ``root``, once every file the trace loads from it is found there.

        Args:
            root: The source code's top directory.

        Returns:
            Self: The source code.

        Raises:
            EngineError: If a file the trace loads is missing, naming each one.
        """
        missing = [str(relative) for relative in SOURCE_FILES if not (root / relative).is_file()]
        if missing:
            raise EngineError(
                f"{root} holds no Bitphase source code with its packages installed; it lacks {', '.join(missing)}. "
                "Clone or download https://github.com/paator/bitphase and run pnpm install there."
            )

        return cls(root=root)


@dataclass(frozen=True)
class BitphaseEngine:
    """Bitphase's own engine, run through node over one copy of its source code.

    Attributes:
        node: The node program.
        source: The source code whose modules play the documents.
    """

    node: Path
    source: BitphaseSource

    @classmethod
    def located(cls, root: Path) -> Self:
        """The engine of the source code at ``root``, played by the node this system has.

        Args:
            root: The source code's top directory.

        Returns:
            Self: The engine.

        Raises:
            EngineError: If node is absent, naming how this system installs it, or the source code lacks
                a file the trace loads.
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
            source=BitphaseSource.located(root),
        )

    def command(
        self,
        document: Path,
        output: Path,
    ) -> List[str]:
        """The command that plays ``document`` and writes its trace to ``output``.

        The source code's own tsx runs the trace script, so the script loads Bitphase's TypeScript
        modules the way its own command-line tools do. The script runs inside the source directory,
        so the document and the trace are named by absolute paths.

        Args:
            document: The `.btp` document to play.
            output: Where the trace is written.

        Returns:
            List[str]: The program and its arguments.
        """
        return [
            str(self.node),
            str(self.source.root / TSX_CLI),
            str(BITPHASE_TRACE_SCRIPT_PATH),
            str(self.source.root),
            str(document.resolve()),
            str(output.resolve()),
        ]

    def trace(
        self,
        document: Path,
        output: Path,
    ) -> SongTrace:
        """Plays a document through the engine and reads what every channel sounds on every tick.

        The trace holds every write the engine made to the chip's registers, and it is written to
        ``output`` and kept there, so a run can be read again by hand.

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
                cwd=self.source.root,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as error:
            raise EngineError(f"Bitphase failed to play {document}:\n{error.stderr}") from error

        return read_engine_trace(output.read_text(encoding="utf-8"))
