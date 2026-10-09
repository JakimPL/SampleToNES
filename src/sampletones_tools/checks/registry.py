from typing import Final, Tuple

from sampletones_shared.command import Command
from sampletones_tools.checks.commands.import_boundary import IMPORT_BOUNDARY
from sampletones_tools.checks.commands.language_keys import LANGUAGE_KEYS
from sampletones_tools.checks.commands.palette_colors import PALETTE_COLORS
from sampletones_tools.checks.commands.rendered_literals import RENDERED_LITERALS
from sampletones_tools.checks.commands.shortcut_actions import SHORTCUT_ACTIONS
from sampletones_tools.checks.commands.tag_names import TAG_NAMES
from sampletones_tools.checks.commands.unused_tags import UNUSED_TAGS

GATES: Final[Tuple[Command, ...]] = (
    IMPORT_BOUNDARY,
    LANGUAGE_KEYS,
    PALETTE_COLORS,
    RENDERED_LITERALS,
    SHORTCUT_ACTIONS,
    TAG_NAMES,
    UNUSED_TAGS,
)
