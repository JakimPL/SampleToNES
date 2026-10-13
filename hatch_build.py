import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Final

from hatchling.builders.config import BuilderConfig
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

EDITABLE: Final[str] = "editable"
FORCE_INCLUDE: Final[str] = "force_include"
SOURCE_DIRECTORY: Final[str] = "src"
SITE_DESTINATION: Final[str] = "sampletones_assets/documentation"
SITE_PREFIX: Final[str] = "sampletones-documentation-"


class DocumentationBuildHook(BuildHookInterface[BuilderConfig]):
    """Writes the user documentation into every wheel, as the pages Help > Documentation opens.

    The maker in ``assets/documentation`` writes the site from the checkout's docs into a
    temporary folder, which the wheel carries at the assets package's documentation path and
    which is removed once the wheel is written. An editable install reads the checkout itself,
    where ``make docs`` writes the same site.
    """

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: Dict[str, Any]) -> None:
        if version == EDITABLE:
            return

        root = Path(self.root)
        for entry in (root / SOURCE_DIRECTORY, root):
            if str(entry) not in sys.path:
                sys.path.insert(0, str(entry))

        from assets.documentation.build import (  # pylint: disable=import-outside-toplevel
            SiteRequest,
            build_site,
        )
        from assets.documentation.paths import (  # pylint: disable=import-outside-toplevel
            DOCS_DIRECTORY,
            PROJECT_FILE,
        )

        site = Path(tempfile.mkdtemp(prefix=SITE_PREFIX))
        build_site(SiteRequest(docs=DOCS_DIRECTORY, project=PROJECT_FILE, output=site))
        build_data[FORCE_INCLUDE][str(site)] = SITE_DESTINATION

    def finalize(
        self,
        version: str,
        build_data: Dict[str, Any],
        artifact_path: str,
    ) -> None:
        for source, destination in build_data[FORCE_INCLUDE].items():
            if destination == SITE_DESTINATION:
                shutil.rmtree(source)
