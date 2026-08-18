from sampletones_shared.paths.resources import CONFIG_DIRECTORY


class TestConfigDirectory:
    def test_the_configuration_directory_holds_the_shipped_files(self) -> None:
        """Read as a package resource, so the bundle finds it beside the executable."""
        assert list(CONFIG_DIRECTORY.rglob("*.yaml"))
