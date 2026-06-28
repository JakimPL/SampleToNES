from typing import Any, Dict

import pytest

from sampletones_application.constants.reconstructions import (
    TAG_RECONSTRUCTIONS_BROWSER_BUTTON_RECONSTRUCT_DIRECTORY,
    TAG_RECONSTRUCTIONS_BROWSER_BUTTON_RECONSTRUCT_FILE,
)
from sampletones_application.ui.panels.reconstruction import browser as browser_module
from sampletones_application.ui.panels.reconstruction.browser import GUIBrowserPanel

RECONSTRUCT_BUTTONS = (
    TAG_RECONSTRUCTIONS_BROWSER_BUTTON_RECONSTRUCT_FILE,
    TAG_RECONSTRUCTIONS_BROWSER_BUTTON_RECONSTRUCT_DIRECTORY,
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
    monkeypatch.setattr(browser_module, "dpg_configure_item", instance)
    return instance


class _FakeTreeLogic:
    """Stands in for the panel's ``TreeLogic`` so ``self.locked`` reflects the tree-rebuild lock."""

    def __init__(self) -> None:
        self.locked = False


def _panel(*, busy: bool = False) -> GUIBrowserPanel:
    """A panel with only the state the methods under test touch, bypassing the DearPyGui-dependent
    constructor. ``self.locked`` reads the fake logic; the busy predicate is the injected source of
    truth the panel pulls."""
    panel = GUIBrowserPanel.__new__(GUIBrowserPanel)
    panel.logic = _FakeTreeLogic()
    panel._is_operation_in_progress = lambda: busy
    return panel


class TestReconstructButtonLock:
    """The reconstruct buttons stay enabled only while the panel is unlocked and no long operation is
    running. Both inputs are read live, and the tree-rebuild lock composes with the busy state."""

    def test_busy_disables_reconstruct_buttons(self, recorder: _ConfigureRecorder) -> None:
        panel = _panel(busy=True)
        panel.refresh_action_buttons()
        assert all(recorder.enabled[tag] is False for tag in RECONSTRUCT_BUTTONS)

    def test_idle_enables_reconstruct_buttons(self, recorder: _ConfigureRecorder) -> None:
        panel = _panel(busy=False)
        panel.refresh_action_buttons()
        assert all(recorder.enabled[tag] is True for tag in RECONSTRUCT_BUTTONS)

    def test_busy_survives_a_tree_rebuild_cycle(self, recorder: _ConfigureRecorder) -> None:
        panel = _panel(busy=True)

        panel.logic.locked = True
        panel._set_tree_enabled(False)
        panel.logic.locked = False
        panel._set_tree_enabled(True)

        assert all(recorder.enabled[tag] is False for tag in RECONSTRUCT_BUTTONS)

    def test_tree_lock_alone_disables_reconstruct_buttons(self, recorder: _ConfigureRecorder) -> None:
        panel = _panel(busy=False)
        panel.logic.locked = True
        panel.refresh_action_buttons()
        assert all(recorder.enabled[tag] is False for tag in RECONSTRUCT_BUTTONS)
