from pathlib import Path

import pytest

from tests.suite.scripts import load_script

hook = load_script("pyinstaller_hooks/hook-cupy.py")


@pytest.fixture(name="site_packages")
def site_packages_fixture(tmp_path: Path) -> Path:
    """A site-packages holding two CUDA components, a cache directory and a component without headers."""
    root = tmp_path / hook.CUDA_PACKAGE
    (root / "cublas" / "lib").mkdir(parents=True)
    (root / "cublas" / "include").mkdir()
    (root / "cuda_runtime" / "lib").mkdir(parents=True)
    (root / "cuda_runtime" / "include").mkdir()
    (root / "nvjitlink" / "bin").mkdir(parents=True)
    (root / "__pycache__").mkdir()
    (root / "__init__.py").write_text("")
    return tmp_path


class TestCudaComponents:
    def test_each_directory_holding_libraries_is_a_component(self, site_packages: Path) -> None:
        components = hook.cuda_components(site_packages)

        assert [component.name for component in components] == ["cublas", "cuda_runtime", "nvjitlink"]

    def test_an_environment_without_the_cuda_wheels_has_none(self, tmp_path: Path) -> None:
        assert hook.cuda_components(tmp_path) == []


class TestHiddenImports:
    def test_the_standard_library_import_leads_and_every_component_follows(self, site_packages: Path) -> None:
        imports = hook.hidden_imports(hook.cuda_components(site_packages))

        assert imports[: len(hook.STANDARD_LIBRARY_IMPORTS)] == list(hook.STANDARD_LIBRARY_IMPORTS)
        assert imports[len(hook.STANDARD_LIBRARY_IMPORTS) :] == [
            f"{hook.CUDA_PACKAGE}.cublas",
            f"{hook.CUDA_PACKAGE}.cuda_runtime",
            f"{hook.CUDA_PACKAGE}.nvjitlink",
        ]


class TestHeaderDirectories:
    def test_each_include_directory_lands_at_its_own_package_path(self, site_packages: Path) -> None:
        components = hook.cuda_components(site_packages)

        assert hook.header_directories(components) == [
            (
                str(site_packages / hook.CUDA_PACKAGE / "cublas" / "include"),
                f"{hook.CUDA_PACKAGE}/cublas/include",
            ),
            (
                str(site_packages / hook.CUDA_PACKAGE / "cuda_runtime" / "include"),
                f"{hook.CUDA_PACKAGE}/cuda_runtime/include",
            ),
        ]


class TestModuleGlobals:
    def test_the_hook_states_what_pyinstaller_reads(self) -> None:
        assert hook.hiddenimports[: len(hook.STANDARD_LIBRARY_IMPORTS)] == list(hook.STANDARD_LIBRARY_IMPORTS)
        assert all(isinstance(source, str) and isinstance(target, str) for source, target in hook.datas)
