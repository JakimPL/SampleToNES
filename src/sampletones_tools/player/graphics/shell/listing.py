from typing import Final, List

from sampletones_tools.player.graphics.shell.data import ShellData

GENERATED_NOTE: Final[str] = "; Written by `sampletones tiles` from the screen layout and the tile sheet."
BYTES_PER_LINE: Final[int] = 16
DATA_SEGMENT: Final[str] = "PLAYER"
NAME_COLUMN: Final[int] = 24
BYTE_LIMIT: Final[int] = 0x100


def _number(value: int) -> str:
    return f"${value:02X}" if value < BYTE_LIMIT else f"${value:04X}"


def include_text(data: ShellData) -> str:
    """The equates the shell reads the screen by, one per line."""
    lines = [GENERATED_NOTE, ""]
    lines += [f"{name.ljust(NAME_COLUMN)}= {_number(value)}" for name, value in data.equates.items()]
    return "\n".join(lines) + "\n"


def source_text(data: ShellData) -> str:
    """The tables the shell draws the screen from, each exported under its name."""
    lines: List[str] = [
        GENERATED_NOTE,
        "",
        *[f".export {name}" for name in data.tables],
        "",
        f'.segment "{DATA_SEGMENT}"',
    ]
    for name, table in data.tables.items():
        lines += ["", f"{name}:"]
        for start in range(0, len(table), BYTES_PER_LINE):
            chunk = table[start : start + BYTES_PER_LINE]
            lines.append("    .byte " + ", ".join(f"${byte:02X}" for byte in chunk))

    return "\n".join(lines) + "\n"
