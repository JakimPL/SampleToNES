import pytest

from sampletones_application.categories.context import (
    CHANNEL_ELEMENTS,
    byte_size_label,
    channel_label,
    channel_letter,
    sample_rate_template,
)
from sampletones_application.categories.elements.global_ import ContextElements
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


class TestTheNameAChannelIsPrintedBy:
    """Every display names a channel by one entry of the language file, so a tracker column, an order
    row, a graph legend and a tree's detail read alike."""

    @pytest.mark.parametrize("channel_name", ChannelName.items(), ids=lambda name: name.value)
    def test_the_name_is_the_language_files_own(
        self, channel_name: ChannelName, language_manager: LanguageManager
    ) -> None:
        key = f"global.context.label.{CHANNEL_ELEMENTS[channel_name].value}"
        assert channel_label(language_manager, channel_name) == language_manager[key]

    def test_the_names_tell_the_channels_apart(self, language_manager: LanguageManager) -> None:
        names = [channel_label(language_manager, channel_name) for channel_name in ChannelName.items()]
        assert len(set(names)) == len(names)

    def test_a_name_reads_as_words_rather_than_the_channels_identifier(self, language_manager: LanguageManager) -> None:
        assert all(
            channel_label(language_manager, channel_name) != channel_name.value.capitalize()
            for channel_name in (ChannelName.PULSE1, ChannelName.PULSE2)
        )


class TestTheFiguresAMeasurementIsPrintedIn:
    """A byte figure and a sample rate are printed through one template each, wherever they appear."""

    @pytest.mark.parametrize("byte_count", [0, 1, 65535])
    def test_a_byte_figure_states_its_count(self, byte_count: int, language_manager: LanguageManager) -> None:
        template = language_manager[f"global.context.template.{ContextElements.SIZE_BYTES.value}"]
        assert byte_size_label(language_manager, byte_count) == template.format(bytes=byte_count)
        assert str(byte_count) in byte_size_label(language_manager, byte_count)

    def test_a_rate_template_names_the_rate(self, language_manager: LanguageManager) -> None:
        assert "44100" in sample_rate_template(language_manager).format(rate=44100)
