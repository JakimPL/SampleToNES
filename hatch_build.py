import os
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
DEPLOYMENT_DESTINATION: Final[str] = "sampletones_config/application/deployment.yaml"
RELEASE_DEPLOYMENT: Final[str] = "scripts/release/deployment.yaml"
DEPLOYMENT_PREFIX: Final[str] = "sampletones-deployment-"
DEVELOPMENT_WHEEL: Final[str] = "SAMPLETONES_DEVELOPMENT_WHEEL"
DEVELOPMENT_WHEEL_ENABLED: Final[str] = "1"


class DistributionBuildHook(BuildHookInterface[BuilderConfig]):
    """Writes into every wheel what the checkout keeps outside its packages: the user documentation, as
    the pages Help > Documentation opens, and the release deployment settings.

    The maker in ``assets/documentation`` writes the site from the checkout's docs, which the
    wheel carries at the assets package's documentation path. The release settings in
    ``scripts/release/deployment.yaml`` take the place of the development ones the checkout reads,
    so a published wheel, and a release bundle installed from one, is quiet and self-healing. The
    site and the copy of the settings lie in temporary folders, removed once the wheel is written.

    An editable install reads the checkout itself, where ``make docs`` writes the same site. A
    build run with ``SAMPLETONES_DEVELOPMENT_WHEEL=1``, as a development bundle's is, keeps the
    development settings.
    """

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: Dict[str, Any]) -> None:
        if version == EDITABLE:
            return

        root = Path(self.root)
        build_data[FORCE_INCLUDE][str(self._build_site(root))] = SITE_DESTINATION
        if os.environ.get(DEVELOPMENT_WHEEL) != DEVELOPMENT_WHEEL_ENABLED:
            build_data[FORCE_INCLUDE][str(self._release_deployment(root))] = DEPLOYMENT_DESTINATION

    def finalize(
        self,
        version: str,
        build_data: Dict[str, Any],
        artifact_path: str,
    ) -> None:
        for source, destination in build_data[FORCE_INCLUDE].items():
            if destination == SITE_DESTINATION:
                shutil.rmtree(source)
            elif destination == DEPLOYMENT_DESTINATION:
                shutil.rmtree(Path(source).parent)

    @staticmethod
    def _build_site(root: Path) -> Path:
        """The documentation site written from the checkout's docs into a temporary folder."""
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
        return site

    @staticmethod
    def _release_deployment(root: Path) -> Path:
        """A copy of the release deployment settings in a temporary folder.

        Hatchling lets a forced file take the place of a packaged one when the forced file lies
        outside the project, so the copy replaces the checkout's ``deployment.yaml`` in the wheel.
        """
        copy = Path(tempfile.mkdtemp(prefix=DEPLOYMENT_PREFIX)) / Path(DEPLOYMENT_DESTINATION).name
        shutil.copyfile(root / RELEASE_DEPLOYMENT, copy)
        return copy
