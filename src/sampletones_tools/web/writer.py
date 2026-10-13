from pathlib import Path
from shutil import copyfile
from typing import Final, Tuple

from sampletones_tools.web.design import ApplicationDesign
from sampletones_tools.web.fonts import fonts_stylesheet
from sampletones_tools.web.paths import FONTS_DIRECTORY, MARK_SOURCE, STATIC_DIRECTORY
from sampletones_tools.web.roles.resolver import resolve_roles
from sampletones_tools.web.stylesheets import roles_stylesheet
from sampletones_tools.web.typography.scale import type_sizes

FONTS_STYLESHEET: Final[str] = "fonts.css"
MARK_FILE: Final[str] = "mark.svg"
ROLES_STYLESHEET: Final[str] = "roles.css"
LAYOUT_STYLESHEETS: Final[Tuple[str, ...]] = (
    "base.css",
    "shell.css",
    "card.css",
    "controls.css",
    "table.css",
    "prose.css",
    "print.css",
)
TEXT_NEWLINE: Final[str] = "\n"


def write_layout(
    directory: Path,
    design: ApplicationDesign,
) -> Tuple[str, ...]:
    """Write the web layout into ``directory``: the faces, the roles of ``design``, the shared
    stylesheets, and the application's mark as :data:`MARK_FILE`.

    Every page the project writes links these files, so a board and the documentation wear one
    layout, drawn from the application's own configuration.

    Returns:
        The stylesheet file names, in the order a page links them.

    Raises:
        FileNotFoundError: If the package lacks a shared stylesheet or a face.
    """
    directory.mkdir(parents=True, exist_ok=True)
    (directory / FONTS_STYLESHEET).write_text(
        fonts_stylesheet(FONTS_DIRECTORY, design.glyph_characters),
        encoding="utf-8",
        newline=TEXT_NEWLINE,
    )
    (directory / ROLES_STYLESHEET).write_text(
        roles_stylesheet(resolve_roles(design), type_sizes(design.fonts, FONTS_DIRECTORY)),
        encoding="utf-8",
        newline=TEXT_NEWLINE,
    )
    for name in LAYOUT_STYLESHEETS:
        source = STATIC_DIRECTORY / name
        if not source.is_file():
            raise FileNotFoundError(f"The package ships no layout stylesheet '{name}' at '{source}'")

        copyfile(source, directory / name)

    copyfile(MARK_SOURCE, directory / MARK_FILE)
    return (FONTS_STYLESHEET, ROLES_STYLESHEET, *LAYOUT_STYLESHEETS)
