import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Final, Tuple, Type

from sampletones_shared.exceptions import SampleToNESError

if TYPE_CHECKING:
    from sampletones_application.utils.palette import Palette

CHECK_FAILURES: Final[Tuple[Type[Exception], ...]] = (
    ImportError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    SampleToNESError,
)

SUCCESS_STATUS: Final[int] = 0
FAILURE_STATUS: Final[int] = 1

SUCCESS_PREFIX: Final[str] = "[ok]"
FAILURE_PREFIX: Final[str] = "[FAIL]"


@dataclass(frozen=True)
class SelfCheck:
    """A named startup check that reports a short detail line once it succeeds.

    Each check exercises one thing a packaged build has to provide — an importable module,
    a bundled resource, a readable configuration file — through the same code path the
    application uses at startup, so a build lacking any of them is caught before release.
    """

    name: str
    run: Callable[[], str]


def _load_palette() -> "Palette":
    from sampletones_application.paths import PALETTE_PATH
    from sampletones_application.utils.palette import Palette

    return Palette.load(PALETTE_PATH)


def _check_application_import() -> str:
    """Imports the application entry class, pulling in the whole startup import graph.

    Every optional dependency the GUI touches is imported here, which is what a packaged
    build most easily loses; creating a DearPyGui context stays out of the check so it
    runs on a headless machine.
    """
    from sampletones_application.application import Application

    return Application.__module__


def _check_deployment_config() -> str:
    from sampletones_application.config.deployment.deployment import DeploymentConfig
    from sampletones_application.paths import DEPLOYMENT_CONFIG_PATH

    deployment = DeploymentConfig.load(DEPLOYMENT_CONFIG_PATH)
    return f"log_level={deployment.log_level}, strict_history={deployment.strict_history}"


def _check_palette() -> str:
    palette = _load_palette()
    return f"{palette.name}, {len(palette.colors)} colors"


def _check_layout_config() -> str:
    from sampletones_application.layout import LayoutConfig, load_layout_config
    from sampletones_application.paths import BEHAVIOR_DIRECTORY, LAYOUT_DIRECTORY

    load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, _load_palette())
    return f"{len(LayoutConfig.model_fields)} sections"


def _check_themes() -> str:
    from sampletones_application.paths import THEME_DIRECTORY
    from sampletones_application.ui.themes.loader import ThemeLoader

    themes = ThemeLoader(THEME_DIRECTORY, _load_palette()).load_all()
    return f"{len(themes)} themes"


def _check_language() -> str:
    from sampletones_application.categories.manager import LanguageManager
    from sampletones_application.paths import LANG_EN

    LanguageManager(LANG_EN)
    return LANG_EN.name


def _check_resources() -> str:
    from sampletones_application.ui.resources.items import FontResource, IconResource
    from sampletones_application.ui.resources.resources import get_font_path, get_icon_path

    for font in FontResource:
        get_font_path(font)

    for icon in IconResource:
        get_icon_path(icon)

    return f"{len(FontResource)} fonts, {len(IconResource)} icons"


def _check_file_dialog_backend() -> str:
    from sampletones_application.utils.file_dialogs.selection import select_file_dialog_backend

    return type(select_file_dialog_backend()).__name__


CHECKS: Final[Tuple[SelfCheck, ...]] = (
    SelfCheck(name="application import", run=_check_application_import),
    SelfCheck(name="deployment config", run=_check_deployment_config),
    SelfCheck(name="palette", run=_check_palette),
    SelfCheck(name="layout config", run=_check_layout_config),
    SelfCheck(name="themes", run=_check_themes),
    SelfCheck(name="language", run=_check_language),
    SelfCheck(name="resources", run=_check_resources),
    SelfCheck(name="file dialog backend", run=_check_file_dialog_backend),
)


def run_self_check() -> int:
    """Runs every startup check in order and returns the process exit status.

    Prints one line per check so a passing run doubles as an inventory of what the build
    carries, and stops at the first failure with the offending check named on the standard
    error stream. A packaged build runs this to prove it starts before it is shipped.
    """
    for check in CHECKS:
        try:
            detail = check.run()
        except CHECK_FAILURES as exception:
            print(f"{FAILURE_PREFIX} {check.name}: {type(exception).__name__}: {exception}", file=sys.stderr)
            return FAILURE_STATUS

        print(f"{SUCCESS_PREFIX} {check.name}: {detail}")

    print(f"{SUCCESS_PREFIX} {len(CHECKS)} checks passed")
    return SUCCESS_STATUS
