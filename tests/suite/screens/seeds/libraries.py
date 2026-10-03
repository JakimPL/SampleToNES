from dataclasses import dataclass

from sampletones_core.configs import Config
from tests.suite.library import build_served_library


@dataclass(frozen=True)
class MiniLibrary:
    """A small library built for ``config``, saved where the application looks for that configuration's
    library.

    A conversion matches against it in seconds, and the Instructions tab browses it.
    """

    config: Config

    def write(self) -> None:
        """Builds the library and saves it where the application looks for it."""
        library, key = build_served_library(self.config)
        library.save_data(key, library.data[key])
