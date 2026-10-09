import site
import sys
from typing import Final, Iterable, List, Optional

BUNDLE: Final[str] = sys._MEIPASS  # type: ignore[attr-defined] # pylint: disable=protected-access,no-member


def bundle_site_packages(prefixes: Optional[Iterable[str]] = None) -> List[str]:
    """The directories the CUDA wheels are searched in: the bundle, where PyInstaller placed them."""
    del prefixes
    return [BUNDLE]


site.getsitepackages = bundle_site_packages
site.ENABLE_USER_SITE = False
