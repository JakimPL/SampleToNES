from sampletones_tools.checks.paths import SCRIPTS_ROOT


class TestScriptsRoot:
    def test_the_scripts_root_holds_the_bootstrap_tree(self) -> None:
        assert (SCRIPTS_ROOT / "bootstrap" / "__init__.py").is_file()
