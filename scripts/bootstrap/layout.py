from pathlib import Path
from typing import Final, Tuple

REPOSITORY_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
PROJECT_FILE: Final[str] = "pyproject.toml"
SOURCE_DIRECTORY: Final[str] = "src"
BENCHMARKS_DIRECTORY: Final[str] = "tests/benchmarks"
DISTRIBUTION: Final[str] = "bin"
BUNDLES: Final[str] = "bundles"
BUILD_ENVIRONMENT: Final[str] = ".venv-build"
RELEASE_HOOK: Final[str] = "scripts/runtime_hooks/release_environment.py"
NOTICES: Final[Tuple[str, ...]] = ("LICENSE", "THIRD-PARTY-NOTICES.md", "THIRD-PARTY-LICENSES.txt")
BUILD_TOOLS: Final[Tuple[str, ...]] = ("PIL",)
CLEAN_ARTIFACTS: Final[Tuple[str, ...]] = (DISTRIBUTION, BUNDLES, "build", "dist", "htmlcov", ".coverage")
CLEAN_PATTERNS: Final[Tuple[str, ...]] = ("*.spec",)
CACHE_DIRECTORIES: Final[Tuple[str, ...]] = ("__pycache__",)
CACHE_DIRECTORY_SUFFIXES: Final[Tuple[str, ...]] = (".egg-info",)
CACHE_FILE_SUFFIXES: Final[Tuple[str, ...]] = (".pyc",)
ENVIRONMENTS: Final[Tuple[str, ...]] = (".git", ".venv", BUILD_ENVIRONMENT)


def repository_root() -> Path:
    """The repository the scripts belong to, which every build and clean-up runs against.

    Raises:
        FileNotFoundError: If the scripts lie outside a SampleToNES checkout.
    """
    project = REPOSITORY_ROOT / PROJECT_FILE
    if not project.is_file() or not (REPOSITORY_ROOT / SOURCE_DIRECTORY).is_dir():
        raise FileNotFoundError(f"SampleToNES project root not found (expected {project} beside {SOURCE_DIRECTORY})")

    return REPOSITORY_ROOT
