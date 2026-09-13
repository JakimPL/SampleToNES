from typing import Final, Tuple

from sampletones.commands.convert import CONVERT
from sampletones.commands.library import LIBRARY
from sampletones.commands.open import OPEN
from sampletones.commands.run import RUN
from sampletones.commands.self_check import SELF_CHECK
from sampletones_shared.command import Command

USER_COMMANDS: Final[Tuple[Command, ...]] = (RUN, OPEN, CONVERT, LIBRARY, SELF_CHECK)
COMMANDS: Final[Tuple[Command, ...]] = USER_COMMANDS
