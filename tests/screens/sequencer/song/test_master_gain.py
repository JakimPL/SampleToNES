import math
import operator
from typing import Final, List, Tuple

from automation.screen import Screen
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId

UNITY: Final[float] = 1.0
LOUDEST_GAIN: Final[float] = 2.0
BEYOND_THE_LEFT: Final[float] = -0.5
BEYOND_THE_RIGHT: Final[float] = 1.5
NEAR_THE_RIGHT: Final[float] = 0.97
FROM_THE_MIDDLE: Final[float] = 0.5
DECIBELS_PER_DOUBLING: Final[float] = 20.0
SILENT_GAIN: Final[str] = "settings.audio.message.master_gain_silent"
GAIN_TEMPLATE: Final[str] = "settings.audio.template.master_gain_db"


class TestTheMasterGain:
    """The decibel line of Audio settings follows the master gain slider.

    The dialog opens at unity. Dragging the slider past the left end reads silence in the unity color;
    dragging past the right end reads the top level in the warning color; dragging back to the middle
    reads that level in decibels, and Cancel closes the dialog.
    """

    def test_the_line_follows_the_slider(self, screen: Screen) -> None:
        """The decibel line shows silence, the top level and a middle level as the slider moves."""
        settings = screen.audio_settings
        unity_color: List[Tuple[float, ...]] = []

        def open_audio_settings(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.AUDIO_SETTINGS)
            screen.expect(settings.is_shown, bool, description="Audio settings")

            assert settings.gain() == UNITY
            unity_color.append(settings.decibels_color())

        def all_the_way_down_reads_silence(screen: Screen) -> None:
            settings.drag_gain(FROM_THE_MIDDLE, BEYOND_THE_LEFT)

            screen.expect(settings.gain, (0.0).__eq__, description="the gain at zero")
            assert settings.decibels() == screen.words(SILENT_GAIN)
            assert settings.decibels_color() == unity_color[0]

        def all_the_way_up_reads_the_level_in_warning(screen: Screen) -> None:
            settings.drag_gain(FROM_THE_MIDDLE, BEYOND_THE_RIGHT)

            screen.expect(settings.gain, LOUDEST_GAIN.__eq__, description="the gain at its top")
            level = DECIBELS_PER_DOUBLING * math.log10(LOUDEST_GAIN)
            assert settings.decibels() == screen.words(GAIN_TEMPLATE).format(decibels=level)
            assert settings.decibels_color() != unity_color[0]

        def back_to_unity(screen: Screen) -> None:
            settings.drag_gain(NEAR_THE_RIGHT, FROM_THE_MIDDLE)

            gain = screen.expect(settings.gain, lambda found: 0.0 < found < LOUDEST_GAIN, description="a middle gain")
            assert settings.decibels() == screen.words(GAIN_TEMPLATE).format(
                decibels=DECIBELS_PER_DOUBLING * math.log10(gain)
            )
            screen.press_shortcut(ShortcutId.DIALOG_CANCEL)
            screen.expect(settings.is_shown, operator.not_, description="Audio settings closed")

        screen.scenario(
            open_audio_settings,
            all_the_way_down_reads_silence,
            all_the_way_up_reads_the_level_in_warning,
            back_to_unity,
        ).run()
