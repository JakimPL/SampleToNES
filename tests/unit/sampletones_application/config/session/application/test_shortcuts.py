from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.application.shortcuts import ShortcutsConfig
from sampletones_application.constants.keybindings import DEFAULT_SCHEME_NAME

REBOUND_UNDO = {"Undo": "Ctrl+Alt+U"}


class TestDefaults:
    def test_a_fresh_configuration_runs_the_default_scheme(self) -> None:
        assert ShortcutsConfig().scheme == DEFAULT_SCHEME_NAME

    def test_a_fresh_configuration_rebinds_nothing(self) -> None:
        assert ShortcutsConfig().overrides == {}

    def test_each_configuration_carries_its_own_overrides(self) -> None:
        """One reader's rebind stays with the configuration it was made in."""
        first = ShortcutsConfig()
        first.overrides.update(REBOUND_UNDO)

        assert first.overrides == REBOUND_UNDO
        assert ShortcutsConfig().overrides == {}

    def test_the_application_configuration_carries_a_shortcuts_section(self) -> None:
        assert ApplicationConfig().shortcuts == ShortcutsConfig()


class TestRoundTrip:
    def test_the_preferences_survive_a_dump_and_a_reload(self) -> None:
        shortcuts = ShortcutsConfig(scheme="compact", overrides=REBOUND_UNDO)

        assert ShortcutsConfig.model_validate(shortcuts.model_dump()) == shortcuts

    def test_the_preferences_survive_the_whole_application_configuration(self) -> None:
        config = ApplicationConfig()
        config.shortcuts.scheme = "compact"
        config.shortcuts.overrides = dict(REBOUND_UNDO)

        reloaded = ApplicationConfig.model_validate(config.model_dump())

        assert (reloaded.shortcuts.scheme, reloaded.shortcuts.overrides) == ("compact", REBOUND_UNDO)

    def test_a_configuration_written_before_the_shortcuts_section_reads_the_defaults(self) -> None:
        """A stored file outlives the build that wrote it, so an absent section takes defaults."""
        assert ApplicationConfig.model_validate({}).shortcuts == ShortcutsConfig()
