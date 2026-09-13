from bootstrap.repository import repository_root


class TestRepositoryRoot:
    def test_the_root_holds_the_project_and_the_entry_package(self) -> None:
        root = repository_root()

        assert (root / "pyproject.toml").is_file()
        assert (root / "src" / "sampletones" / "__main__.py").is_file()
