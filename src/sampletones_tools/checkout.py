from pathlib import Path
from typing import Final

from sampletones_shared.paths.source import REPOSITORY_ROOT

PROJECT_FILE: Final[str] = "pyproject.toml"
SOURCE_DIRECTORY: Final[str] = "src"
CHECKOUT_ADVICE: Final[str] = (
    "This command reads the repository, so it runs from a checkout: clone SampleToNES, run "
    "'make setup', then 'uv run sampletones {command}'."
)


def is_checkout(root: Path) -> bool:
    """Whether ``root`` is a SampleToNES checkout: the project file beside the source tree."""
    return (root / PROJECT_FILE).is_file() and (root / SOURCE_DIRECTORY).is_dir()


def require_checkout(command: str) -> None:
    """Holds a developer command to a checkout, where the repository it reads or writes is.

    An installed copy, from the wheel or the bundle, carries the package without the repository
    around it, so the refusal names the way to run the command there.

    Args:
        command: The command line the advice names, such as ``check import-boundary --all``.

    Raises:
        SystemExit: If the package runs outside a checkout.
    """
    if not is_checkout(REPOSITORY_ROOT):
        raise SystemExit(CHECKOUT_ADVICE.format(command=command))
