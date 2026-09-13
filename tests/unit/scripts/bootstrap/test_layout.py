from bootstrap.layout import PROJECT_FILE, SOURCE_DIRECTORY, repository_root


class TestRepositoryRoot:
    def test_the_root_holds_the_project_beside_the_sources(self) -> None:
        root = repository_root()

        assert (root / PROJECT_FILE).is_file()
        assert (root / SOURCE_DIRECTORY / "sampletones" / "__main__.py").is_file()
