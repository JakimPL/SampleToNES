from pathlib import Path

from tests.suite.scripts import load_script

clean = load_script("clean.py")


def _tree(root: Path) -> None:
    for directory in (
        "bin",
        "build",
        "dist",
        "htmlcov",
        "src/__pycache__",
        "src/sampletones.egg-info",
        ".venv/__pycache__",
    ):
        (root / directory).mkdir(parents=True)

    for file in (".coverage", "sampletones.spec", "src/module.pyc", "src/module.py", ".venv/cached.pyc"):
        (root / file).write_text("")


class TestRemoveArtifacts:
    def test_the_build_outputs_and_reports_go(self, tmp_path: Path) -> None:
        _tree(tmp_path)

        clean.remove_artifacts(tmp_path)

        assert not any((tmp_path / name).exists() for name in ("bin", "build", "dist", "htmlcov", ".coverage"))
        assert not (tmp_path / "sampletones.spec").exists()
        assert (tmp_path / "src" / "module.py").exists()


class TestRemoveCaches:
    def test_the_caches_go_and_the_environments_stay(self, tmp_path: Path) -> None:
        _tree(tmp_path)

        clean.remove_caches(tmp_path)

        assert not (tmp_path / "src" / "__pycache__").exists()
        assert not (tmp_path / "src" / "sampletones.egg-info").exists()
        assert not (tmp_path / "src" / "module.pyc").exists()
        assert (tmp_path / "src" / "module.py").exists()
        assert (tmp_path / ".venv" / "__pycache__").exists()
        assert (tmp_path / ".venv" / "cached.pyc").exists()
