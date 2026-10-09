# pylint: disable=invalid-name
import sysconfig
from pathlib import Path
from typing import Final, List, Tuple

CUDA_PACKAGE: Final[str] = "nvidia"
LIBRARY_DIRECTORIES: Final[Tuple[str, ...]] = ("lib", "bin")
INCLUDE_DIRECTORY: Final[str] = "include"
STANDARD_LIBRARY_IMPORTS: Final[Tuple[str, ...]] = ("graphlib",)
PURE_LIBRARY: Final[str] = "purelib"


def cuda_components(site_packages: Path) -> List[Path]:
    """The CUDA components the NVIDIA wheels installed, each a directory holding shared libraries.

    Args:
        site_packages: The site-packages directory of the environment the bundle is built in.

    Returns:
        List[Path]: The component directories under the ``nvidia`` package, in name order.
    """
    root = site_packages / CUDA_PACKAGE
    if not root.is_dir():
        return []

    return sorted(
        component
        for component in root.iterdir()
        if any((component / libraries).is_dir() for libraries in LIBRARY_DIRECTORIES)
    )


def hidden_imports(components: List[Path]) -> List[str]:
    """The modules PyInstaller's analysis misses: a standard-library import made inside compiled code, and
    each CUDA component, whose hook collects its shared libraries."""
    return [*STANDARD_LIBRARY_IMPORTS, *(f"{CUDA_PACKAGE}.{component.name}" for component in components)]


def header_directories(components: List[Path]) -> List[Tuple[str, str]]:
    """The CUDA header directories, placed where CuPy's kernel compiler finds them in the bundle."""
    return [
        (str(component / INCLUDE_DIRECTORY), f"{CUDA_PACKAGE}/{component.name}/{INCLUDE_DIRECTORY}")
        for component in components
        if (component / INCLUDE_DIRECTORY).is_dir()
    ]


INSTALLED: Final[List[Path]] = cuda_components(Path(sysconfig.get_paths()[PURE_LIBRARY]))
hiddenimports = hidden_imports(INSTALLED)
datas = header_directories(INSTALLED)
