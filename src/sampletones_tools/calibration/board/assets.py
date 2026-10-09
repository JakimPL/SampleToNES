from pathlib import Path
from shutil import copyfile
from typing import Dict

from .layout import PAGE_DIRECTORY, PAGE_FILE, SHIPPED_FILES
from .paths import STATIC_DIRECTORY


def write_assets(output: Path, generated: Dict[str, str]) -> Path:
    """
    Put the page's files in place: the shipped ones copied, the generated ones written.

    The page itself lands in the output directory, where a person opens it, and everything it reads
    sits one directory down, so a run directory gains one file a reader can name.

    Args:
        output: The directory the page is written into.
        generated: The generated files, keyed by the name the page reads them under.

    Returns:
        Path: The page, the file a reader opens.

    Raises:
        FileNotFoundError: If the package is missing a shipped file.
    """
    directory = output / PAGE_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    for name in SHIPPED_FILES:
        source = STATIC_DIRECTORY / name
        if not source.is_file():
            raise FileNotFoundError(f"The package ships no page file '{name}' at '{source}'")

        copyfile(source, output / name if name == PAGE_FILE else directory / name)

    for name, content in generated.items():
        (directory / name).write_text(content, encoding="utf-8")

    return output / PAGE_FILE
