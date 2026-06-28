from typing import Any, Dict

import pytest

from sampletones_application.constants.instructions import (
    TAG_INSTRUCTIONS_LIBRARY_BUTTON_GENERATE_LIBRARY,
)
from sampletones_application.ui.panels.instruction import library as library_module
from sampletones_application.ui.panels.instruction.library import (
    GUIInstructionsLibraryPanel,
)


class _ConfigureRecorder:
    """Captures the latest ``enabled`` value the panel configured for each widget tag."""

    def __init__(self) -> None:
        self.enabled: Dict[Any, bool] = {}

    def __call__(self, tag: Any, **kwargs: Any) -> None:
        if "enabled" in kwargs:
            self.enabled[tag] = kwargs["enabled"]


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _ConfigureRecorder:
    instance = _ConfigureRecorder()
    monkeypatch.setattr(library_module, "dpg_configure_item", instance)
    return instance


class _FakeTreeLogic:
    """Stands in for the panel's ``TreeLogic`` so ``self.locked`` reflects the tree-rebuild lock."""

    def __init__(self) -> None:
        self.locked = False


def _panel(*, busy: bool = False) -> GUIInstructionsLibraryPanel:
    """A panel with only the state the methods under test touch, bypassing the DearPyGui-dependent
    constructor. ``self.locked`` reads the fake logic; the busy predicate is the injected source of
    truth the panel pulls."""
    panel = GUIInstructionsLibraryPanel.__new__(GUIInstructionsLibraryPanel)
    panel.logic = _FakeTreeLogic()
    panel._is_operation_active = lambda: busy
    return panel


class TestGenerateButtonLock:
    """The generate button stays enabled only while the panel is unlocked and no long operation is
    running. Both inputs are read live, and the tree-rebuild lock composes with the busy state."""

    def test_busy_disables_generate_button(self, recorder: _ConfigureRecorder) -> None:
        panel = _panel(busy=True)
        panel.refresh_action_buttons()
        assert recorder.enabled[TAG_INSTRUCTIONS_LIBRARY_BUTTON_GENERATE_LIBRARY] is False

    def test_idle_enables_generate_button(self, recorder: _ConfigureRecorder) -> None:
        panel = _panel(busy=False)
        panel.refresh_action_buttons()
        assert recorder.enabled[TAG_INSTRUCTIONS_LIBRARY_BUTTON_GENERATE_LIBRARY] is True

    def test_busy_survives_a_tree_rebuild_cycle(self, recorder: _ConfigureRecorder) -> None:
        panel = _panel(busy=True)

        panel.logic.locked = True
        panel._set_tree_enabled(False)
        panel.logic.locked = False
        panel._set_tree_enabled(True)

        assert recorder.enabled[TAG_INSTRUCTIONS_LIBRARY_BUTTON_GENERATE_LIBRARY] is False

    def test_tree_lock_alone_disables_generate_button(self, recorder: _ConfigureRecorder) -> None:
        panel = _panel(busy=False)
        panel.logic.locked = True
        panel.refresh_action_buttons()
        assert recorder.enabled[TAG_INSTRUCTIONS_LIBRARY_BUTTON_GENERATE_LIBRARY] is False
