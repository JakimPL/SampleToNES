import pytest

from sampletones_player.shell.image import ShellImage
from sampletones_tools.player.graphics.deck.deck import Deck


@pytest.fixture(scope="session")
def shell_image() -> ShellImage:
    """The assembled shell every cartridge carries."""
    return ShellImage.load()


@pytest.fixture(scope="session")
def deck() -> Deck:
    """The player screen the shell's tables are built from."""
    return Deck.load()
