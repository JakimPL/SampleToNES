import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Final, List, Tuple, Type

from sampletones_shared.exceptions import SampleToNESError

if TYPE_CHECKING:
    from sampletones_application.utils.palette.catalog import PaletteCatalog
    from sampletones_application.utils.palette.source import PaletteSource

CHECK_FAILURES: Final[Tuple[Type[Exception], ...]] = (
    ImportError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    RuntimeError,
    SystemError,
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


def _load_palette_catalog() -> "PaletteCatalog":
    from sampletones_application.paths import PALETTES_DIRECTORY
    from sampletones_application.utils.palette.catalog import PaletteCatalog

    return PaletteCatalog.load(PALETTES_DIRECTORY)


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


def _check_palettes() -> str:
    catalog = _load_palette_catalog()
    return f"{', '.join(catalog.names)}, {len(catalog.default.colors)} colors each"


def _palette_sources() -> "List[PaletteSource]":
    from sampletones_application.utils.palette.source import PaletteSource

    return [PaletteSource(palette) for palette in _load_palette_catalog().palettes.values()]


def _check_keybindings() -> str:
    """Loads every shipped scheme, which is where an unanswered action or a clashing key surfaces."""
    from sampletones_application.paths import KEYBINDINGS_DIRECTORY
    from sampletones_application.utils.gui.shortcuts.catalog import ShortcutCatalog

    catalog = ShortcutCatalog.load(KEYBINDINGS_DIRECTORY)
    return f"{', '.join(catalog.names)}, {len(catalog.default.bindings)} actions each"


def _check_layout_config() -> str:
    """Resolves the layout against every shipped palette, since each answers the color tokens itself."""
    from sampletones_application.layout import LayoutConfig, load_layout_config
    from sampletones_application.paths import BEHAVIOR_DIRECTORY, LAYOUT_DIRECTORY

    for source in _palette_sources():
        load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source)

    return f"{len(LayoutConfig.model_fields)} sections"


def _check_themes() -> str:
    """Resolves the theme set against every shipped palette, since each answers the color tokens itself."""
    from sampletones_application.paths import THEME_DIRECTORY
    from sampletones_application.ui.themes.loader import ThemeLoader

    themes = [ThemeLoader(THEME_DIRECTORY, source).load_all() for source in _palette_sources()]
    return f"{len(themes[0])} themes"


def _check_language() -> str:
    from sampletones_application.categories.manager import LanguageManager
    from sampletones_application.paths import LANG_EN

    LanguageManager(LANG_EN)
    return LANG_EN.name


def _check_resources() -> str:
    from sampletones_application.ui.resources.items import FontResource, IconResource
    from sampletones_application.ui.resources.resources import (
        get_font_path,
        get_icon_path,
    )

    for font in FontResource:
        get_font_path(font)

    for icon in IconResource:
        get_icon_path(icon)

    return f"{len(FontResource)} fonts, {len(IconResource)} icons"


def _check_export_backends() -> str:
    """Composes every backend the application exports through.

    A backend reads the resources it writes with as it is built, so this is where a build
    shipping without one — the player's assembled driver among them — names what is missing.
    """
    from sampletones_application.exports import ExportBackends

    return ", ".join(sorted(ExportBackends.build().by_format))


def _check_file_dialog_backend() -> str:
    from sampletones_application.utils.file_dialogs.selection import (
        select_file_dialog_backend,
    )

    return type(select_file_dialog_backend()).__name__


def _check_array_backend() -> str:
    """Names the backend the build computes on, so a GPU build that lost CuPy says so in its inventory."""
    from sampletones_shared.array import describe_array_backend

    return describe_array_backend()


def _check_gpu_backend() -> str:
    """Computes on the graphics card, which is what a GPU build is held to."""
    from sampletones_shared.array import exercise_gpu

    return exercise_gpu()


CHECKS: Final[Tuple[SelfCheck, ...]] = (
    SelfCheck(name="application import", run=_check_application_import),
    SelfCheck(name="deployment config", run=_check_deployment_config),
    SelfCheck(name="palettes", run=_check_palettes),
    SelfCheck(name="keybindings", run=_check_keybindings),
    SelfCheck(name="layout config", run=_check_layout_config),
    SelfCheck(name="themes", run=_check_themes),
    SelfCheck(name="language", run=_check_language),
    SelfCheck(name="resources", run=_check_resources),
    SelfCheck(name="export backends", run=_check_export_backends),
    SelfCheck(name="file dialog backend", run=_check_file_dialog_backend),
    SelfCheck(name="array backend", run=_check_array_backend),
)
GPU_CHECK: Final[SelfCheck] = SelfCheck(name="gpu backend", run=_check_gpu_backend)


def checks_for(*, gpu: bool) -> Tuple[SelfCheck, ...]:
    """The checks a build runs: every startup check, and the GPU check where the build carries GPU support."""
    if gpu:
        return (*CHECKS, GPU_CHECK)

    return CHECKS


def run_self_check(*, gpu: bool) -> int:
    """Runs every startup check in order and returns the process exit status.

    Prints one line per check so a passing run doubles as an inventory of what the build
    carries, and stops at the first failure with the offending check named on the standard
    error stream. A packaged build runs this to prove it starts before it is shipped, and a GPU
    bundle runs it with ``gpu`` set to prove it computes on the graphics card.

    Args:
        gpu: Whether the build is held to the GPU backend.
    """
    checks = checks_for(gpu=gpu)
    for check in checks:
        try:
            detail = check.run()
        except CHECK_FAILURES as exception:
            print(
                f"{FAILURE_PREFIX} {check.name}: {type(exception).__name__}: {exception}",
                file=sys.stderr,
            )
            return FAILURE_STATUS

        print(f"{SUCCESS_PREFIX} {check.name}: {detail}")

    print(f"{SUCCESS_PREFIX} {len(checks)} checks passed")
    return SUCCESS_STATUS
