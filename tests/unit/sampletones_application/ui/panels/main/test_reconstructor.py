from typing import List, Tuple

import pytest

from sampletones_application.constants.sources import SettingsField
from sampletones_application.tags.main import TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE
from sampletones_application.ui.panels.main import reconstructor as reconstructor_module
from sampletones_application.ui.panels.main.reconstructor import GUIReconstructorPanel
from sampletones_application.view_model.main.updates import GenerationSettingsUpdate
from sampletones_core.constants.enums import ChannelName

DRIVE = 1.5


class Harness:
    """The panel over the gestures it reports, without a window to hold its widgets."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.toggled: List[Tuple[SettingsField, ChannelName]] = []
        self.reported: List[GenerationSettingsUpdate] = []

        monkeypatch.setattr(reconstructor_module, "clamp_widget_value", self._drive)

        self.panel = GUIReconstructorPanel.__new__(GUIReconstructorPanel)
        self.panel.on_slot_toggled = lambda field, channel: self.toggled.append((field, channel))
        self.panel.on_generation_settings_changed = self.reported.append

    @staticmethod
    def _drive(tag: str) -> float:
        assert tag == TAG_MAIN_RECONSTRUCTOR_SLIDER_DRIVE
        return DRIVE


class TestTheChoicesTheCardReports:
    """The card settles nothing itself: it names the choice a reader made and hands it on."""

    @pytest.mark.parametrize("channel", list(ChannelName.items()))
    def test_the_key_a_channel_answers_to_settles_its_own_choice(
        self,
        channel: ChannelName,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        harness = Harness(monkeypatch)

        harness.panel.toggle_channel(channel)

        assert harness.toggled == [(SettingsField.CHANNELS, channel)]

    @pytest.mark.parametrize("field", list(SettingsField))
    def test_a_box_names_the_choice_and_the_channel_it_stands_on(
        self,
        field: SettingsField,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        harness = Harness(monkeypatch)

        harness.panel._on_slot_box(None, True, (field, ChannelName.TRIANGLE))

        assert harness.toggled == [(field, ChannelName.TRIANGLE)]

    def test_drive_reaches_the_configuration_on_its_own(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Drive shapes every run, so it travels apart from the choices a row holds."""
        harness = Harness(monkeypatch)

        harness.panel._report_generation_settings()

        assert harness.reported == [GenerationSettingsUpdate(drive=DRIVE)]


class TestCheckboxTags:
    def test_every_choice_and_channel_carries_a_tag_of_its_own(self) -> None:
        tags = tuple(
            GUIReconstructorPanel._slot_checkbox_tag(field, channel)
            for field in SettingsField
            for channel in ChannelName.items()
        )

        assert len(set(tags)) == len(tags)
