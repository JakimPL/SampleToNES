from typing import Final

from sampletones_player.nsf.information import NSFInformation

ARTIST: Final[str] = "Integration"


def exported_information(name: str) -> NSFInformation:
    """The header text an exported sample carries."""
    return NSFInformation(title=name, artist=ARTIST)
