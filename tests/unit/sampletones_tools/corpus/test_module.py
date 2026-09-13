from sampletones_tools.corpus.module import ModuleConfig


class TestModuleConfig:
    def test_the_shipped_module_loads_from_the_package(self) -> None:
        module = ModuleConfig.load()

        assert module.title
        assert module.tempo > 0
