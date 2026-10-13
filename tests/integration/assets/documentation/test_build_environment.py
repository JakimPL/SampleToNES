import json
import re
import subprocess
import sys
import tomllib
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, Final, List, Set

import pytest

from hatch_build import SOURCE_DIRECTORY
from sampletones_shared.application import SAMPLETONES_PACKAGE_NAME
from sampletones_shared.paths.source import REPOSITORY_ROOT

PROJECT_FILE: Final[Path] = REPOSITORY_ROOT / "pyproject.toml"
REQUIREMENT_NAME: Final[re.Pattern[str]] = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
EXTRA_MARKER: Final[str] = "extra =="
PASSING_PREFIXES: Final[List[str]] = ["sampletones_", "assets", "_sysconfigdata"]
FORBIDDEN_MODULES: Final[List[str]] = ["sampletones_shared.paths.user", "dearpygui", "platformdirs"]

PROBE: Final[str] = """
import importlib.abc
import importlib.metadata
import json
import sys
from pathlib import Path

root, source, output, allowed, passing, package = sys.argv[1:7]
allowed = set(json.loads(allowed))
passing = tuple(json.loads(passing))


class Fence(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        top = name.partition(".")[0]
        if top in allowed or top in sys.stdlib_module_names or top.startswith(passing):
            return None
        raise ModuleNotFoundError(f"the build environment holds no {name}")


real_version = importlib.metadata.version


def version(name):
    if name == package:
        raise importlib.metadata.PackageNotFoundError(name)
    return real_version(name)


importlib.metadata.version = version
sys.meta_path.insert(0, Fence())
sys.path[:0] = [source, root]

from assets.documentation.build import SiteRequest, build_site
from assets.documentation.paths import DOCS_DIRECTORY, PROJECT_FILE

site = build_site(SiteRequest(docs=DOCS_DIRECTORY, project=PROJECT_FILE, output=Path(output)))
print(json.dumps({"stamp": site.read_stamp(), "modules": sorted(sys.modules)}))
"""


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str:
    match = REQUIREMENT_NAME.match(requirement)
    assert match is not None, requirement
    return normalized(match.group(1))


def project_tables() -> Dict[str, Any]:
    with PROJECT_FILE.open("rb") as stream:
        return tomllib.load(stream)


def hook_dependencies() -> List[str]:
    dependencies: List[str] = project_tables()["tool"]["hatch"]["build"]["targets"]["wheel"]["hooks"]["custom"][
        "dependencies"
    ]
    return dependencies


def distribution_closure(names: List[str]) -> Set[str]:
    """Every distribution the named ones install, theirs included, as their normalized names."""
    pending = [requirement_name(name) for name in names]
    closure: Set[str] = set()
    while pending:
        name = pending.pop()
        if name in closure:
            continue

        closure.add(name)
        for requirement in metadata.requires(name) or []:
            if EXTRA_MARKER not in requirement:
                pending.append(requirement_name(requirement))

    return closure


def importable_modules(distributions: Set[str]) -> List[str]:
    return sorted(
        module
        for module, owners in metadata.packages_distributions().items()
        if any(normalized(owner) in distributions for owner in owners)
    )


@pytest.fixture(scope="module")
def probe(tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Any]:
    output = tmp_path_factory.mktemp("build-environment") / "site"
    allowed = importable_modules(distribution_closure(hook_dependencies()))
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            PROBE,
            str(REPOSITORY_ROOT),
            str(REPOSITORY_ROOT / SOURCE_DIRECTORY),
            str(output),
            json.dumps(allowed),
            json.dumps(PASSING_PREFIXES),
            SAMPLETONES_PACKAGE_NAME,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert completed.returncode == 0, completed.stderr
    result: Dict[str, Any] = json.loads(completed.stdout)
    return result


class TestTheBuildEnvironment:
    def test_the_maker_runs_on_the_hook_dependencies_alone(self, probe: Dict[str, Any]) -> None:
        assert probe["stamp"]

    @pytest.mark.parametrize("module", FORBIDDEN_MODULES)
    def test_the_maker_leaves_the_user_folders_and_the_interface_alone(
        self,
        probe: Dict[str, Any],
        module: str,
    ) -> None:
        assert module not in probe["modules"]

    def test_each_hook_dependency_carries_the_project_range(self) -> None:
        tables = project_tables()
        declared = [*tables["project"]["dependencies"], *tables["dependency-groups"]["assets"]]
        ranges = {requirement_name(requirement): requirement for requirement in declared}

        assert [ranges.get(requirement_name(requirement)) for requirement in hook_dependencies()] == hook_dependencies()
