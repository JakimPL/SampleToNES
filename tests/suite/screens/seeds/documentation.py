from dataclasses import dataclass
from pathlib import Path
from typing import Final

from automation.paths import SHIPPED_DOCUMENTATION_FOLDER
from sampletones_shared.documentation.site import DocumentationSite

SHIPPED_INDEX: Final[str] = "<!doctype html><title>SampleToNES documentation</title><h1>Shipped pages</h1>\n"


def shipped_site() -> DocumentationSite:
    """The site a scenario's application ships, in the home of the scenario's process."""
    return DocumentationSite(Path.home() / SHIPPED_DOCUMENTATION_FOLDER)


@dataclass(frozen=True)
class ShippedDocumentation:
    """The documentation an installation ships: an index sealed by its stamp, where the scenario's
    application reads its pages from."""

    def write(self) -> None:
        """Writes the index and seals the site."""
        site = shipped_site()
        site.directory.mkdir(parents=True, exist_ok=True)
        site.index.write_text(SHIPPED_INDEX, encoding="utf-8")
        site.write_stamp()
