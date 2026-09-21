import pytest

from sampletones_application.categories.context import channel_label, channel_letter
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.paths import LANG_EN
from sampletones_core.constants.enums import CHANNEL_ABBREVIATIONS, ChannelName


@pytest.fixture(name="language_manager")
def language_manager_fixture() -> LanguageManager:
    return LanguageManager(LANG_EN)


class TestTheLetterAChannelIsMarkedBy:
    """A lane one bar high names its channel by a letter, which the language file spells."""

    @pytest.mark.parametrize("channel_name", ChannelName.items(), ids=lambda name: name.value)
    def test_every_channel_answers_with_one_character(
        self,
        channel_name: ChannelName,
        language_manager: LanguageManager,
    ) -> None:
        assert len(channel_letter(language_manager, channel_name)) == 1

    def test_the_letters_tell_the_channels_apart(self, language_manager: LanguageManager) -> None:
        letters = [channel_letter(language_manager, channel_name) for channel_name in ChannelName.items()]

        assert len(set(letters)) == len(letters)

    @pytest.mark.parametrize("channel_name", ChannelName.items(), ids=lambda name: name.value)
    def test_a_letter_is_the_one_a_converted_folder_is_named_by(
        self,
        channel_name: ChannelName,
        language_manager: LanguageManager,
    ) -> None:
        """A reader meets the same letter on screen and in the folder a conversion writes."""
        assert channel_letter(language_manager, channel_name) == CHANNEL_ABBREVIATIONS[channel_name]

    @pytest.mark.parametrize("channel_name", ChannelName.items(), ids=lambda name: name.value)
    def test_a_letter_opens_the_name_the_channel_is_read_by(
        self,
        channel_name: ChannelName,
        language_manager: LanguageManager,
    ) -> None:
        letter = channel_letter(language_manager, channel_name)

        assert channel_label(language_manager, channel_name).lower().startswith(letter.lower())
