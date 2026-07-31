import argparse
import platform
import subprocess
import sys
from pathlib import Path
from typing import Final, List, Sequence

WINDOWS: Final[str] = "Windows"
WINDOWS_LAUNCHER: Final[str] = "sampletones.exe"
POSIX_LAUNCHER: Final[str] = "sampletones"
VERSION_FLAG: Final[str] = "--version"

REQUIRED_NOTICES: Final[Sequence[str]] = (
    "LICENSE",
    "THIRD-PARTY-NOTICES.md",
    "THIRD-PARTY-LICENSES.txt",
)


def launcher_path(bundle: Path, *, system: str) -> Path:
    """The executable a built bundle offers on the platform it was built for."""
    name = WINDOWS_LAUNCHER if system == WINDOWS else POSIX_LAUNCHER
    return bundle / name


def missing_notices(bundle: Path) -> List[str]:
    """The licence and notice files a release bundle must ship that are absent from it."""
    return [name for name in REQUIRED_NOTICES if not (bundle / name).is_file()]


def main(argv: Sequence[str]) -> int:
    """Confirm a built bundle ships its notices and that its launcher starts."""
    parser = argparse.ArgumentParser(description="Verify a built bundle before it is archived.")
    parser.add_argument("bundle", type=Path, help="the built bundle directory, such as bin/sampletones")
    arguments = parser.parse_args(list(argv))

    bundle: Path = arguments.bundle
    absent = missing_notices(bundle)
    if absent:
        print(f"::error::Bundle {bundle} is missing {', '.join(absent)}")
        return 1

    launcher = launcher_path(bundle, system=platform.system())
    if not launcher.is_file():
        print(f"::error::Bundle {bundle} offers no launcher at {launcher}")
        return 1

    completed = subprocess.run([str(launcher), VERSION_FLAG], check=False)
    if completed.returncode != 0:
        print(f"::error::Launcher {launcher} exited with status {completed.returncode}")
        return completed.returncode

    print(f"Bundle {bundle} ships its notices and its launcher starts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
