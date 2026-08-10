import importlib.util
from types import ModuleType

from sampletones_shared.paths import REPOSITORY_ROOT


def load_script(relative_path: str) -> ModuleType:
    """Import a repository script from its path, making a standalone entry point testable.

    The scripts under ``scripts/`` are entry points invoked by path from workflows, hooks and the
    Makefile, so importing them the same way keeps a test exercising the module the tooling runs.
    """
    path = REPOSITORY_ROOT / "scripts" / relative_path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
