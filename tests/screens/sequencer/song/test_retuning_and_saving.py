import operator
from typing import Final, List, Tuple

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.sequencer.song.constants import LINE_NUMBER, SETTLING_FRAMES
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import marked, raise_the_first_level, titled, voice_title
from tests.suite.screens.steps.sequencer import leave_letting_the_project_go, on_the_sequencer, open_voice
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT, LINE

LINE_ORDINAL: Final[int] = 0
FIFTY_HERTZ: Final[int] = 50
SIXTY_HERTZ: Final[int] = 60
REFIT_TOLERANCE: Final[float] = 0.02


class TestRetuningWithASampleOpen:
    """A new NES frequency re-fits the sample open on the Reconstructions tab and keeps its edit.

    The edit is made on the noise, whose last frame is silent, so the sample keeps its frames and the
    waveform stretches by the ratio of the two rates. The scenario opens the sample, raises a level,
    retypes the frequency from 60 to 50 Hz, confirms the retune and expects the stretched waveform and
    the same envelope.
    """

    def test_the_waveform_refits_and_the_edit_stays(self, screen: Screen) -> None:
        """The waveform stretches by the ratio of the rates and the edited envelope stays."""
        module = screen.sequencer.module
        reconstructions = screen.reconstructions
        typed: List[str] = []
        limits: List[Tuple[float, float]] = []

        def edit_the_line(screen: Screen) -> None:
            open_voice(screen, LINE)
            screen.expect(
                screen.title,
                voice_title(screen, ARRANGED_PROJECT.stem, LINE_ORDINAL, LINE, unsaved=False).__eq__,
                description="the line open",
            )

            typed.append(
                raise_the_first_level(
                    screen,
                    ChannelName.NOISE,
                    title=voice_title(screen, ARRANGED_PROJECT.stem, LINE_ORDINAL, LINE, unsaved=True),
                )
            )
            limits.append(reconstructions.waveform.limits())

        def retune_to_fifty(screen: Screen) -> None:
            on_the_sequencer(screen)
            assert module.nes_frequency() == SIXTY_HERTZ

            module.retype_nes_frequency(FIFTY_HERTZ)

            screen.expect(module.retune_prompt.is_shown, bool, description="the question about retuning")
            module.retune_prompt.confirm()
            screen.expect(module.retune_prompt.is_shown, operator.not_, description="the question answered")

        def the_waveform_refits_and_the_edit_stays(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)
            low, high = limits[0]

            refitted = screen.expect(
                reconstructions.waveform.limits,
                lambda found: abs(found[1] / high - SIXTY_HERTZ / FIFTY_HERTZ) <= REFIT_TOLERANCE,
                description="the waveform re-fitted to the longer frames",
            )
            assert refitted[0] == low
            assert reconstructions.instruments.envelope(ChannelName.NOISE, FeatureKey.VOLUME) == typed[0]

        screen.scenario(
            edit_the_line, retune_to_fifty, the_waveform_refits_and_the_edit_stays, leave_letting_the_project_go
        ).run()


class TestSavingAProjectOpenedAtStart:
    """Save writes a project opened at start to its own file and goes through at once.

    A cell is edited so the project is marked unsaved, then Save is pressed. The scenario expects the
    saved notice and no file dialog.
    """

    def test_save_writes_its_file(self, screen: Screen) -> None:
        """Save shows the saved notice and opens no dialog."""
        on_the_sequencer(screen)
        screen.sequencer.tracker.click(1, ChannelName.PULSE2, SubColumn.VOICE)
        screen.hand.type_text(LINE_NUMBER)
        screen.expect(
            screen.title, titled(screen, marked(ARRANGED_PROJECT.stem, unsaved=True)).__eq__, description="changed"
        )

        screen.press_shortcut(ShortcutId.SAVE_PROJECT)

        screen.frames(SETTLING_FRAMES)
        assert screen.dialog_requests() == ()
        screen.expect(screen.project.saved_notice.is_shown, bool, description="the project saved notice")
