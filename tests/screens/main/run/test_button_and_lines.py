from typing import Final

from sampletones_application.constants.output import OutputKind
from sampletones_application.tags.main import TAG_MAIN_CONVERTER_GROUP_INPUT, TAG_MAIN_CONVERTER_GROUP_ORDER
from tests.screens.main.run.constants import BASS, LEAD, RUN_TIMEOUT_SECONDS
from tests.screens.main.run.steps import wait_for_the_end
from tests.suite.screens.dearpygui.items.reading import read_item
from tests.suite.screens.holds.conversion import ConversionHold
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.main import gather, home_path
from tests.suite.screens.vocabulary.converter import CONVERT_NOTHING, CONVERT_ONE, CONVERT_SEVERAL

MIX_SEVERAL: Final[str] = "main.converter.template.mix_recordings"


class TestTheButtonNamesTheRun:
    """The button under the list names the run each time the list or the switch changes.

    One recording is gathered, then a second, then the switch turned to a mix, then both removed. The
    button reads, in turn, Convert one, Convert several, the mix, and Convert nothing.
    """

    def test_one_several_a_mix_and_none(self, screen: Screen) -> None:
        main = screen.main
        converter = main.converter

        def one(screen: Screen) -> None:
            gather(screen, home_path(BASS))

            assert converter.action() == screen.words(CONVERT_ONE).format(name=home_path(BASS).stem)

        def several(screen: Screen) -> None:
            gather(screen, home_path(LEAD))

            assert converter.action() == screen.words(CONVERT_SEVERAL).format(count=2)

        def a_mix(screen: Screen) -> None:
            main.choose_output(OutputKind.MIXED)

            screen.expect(converter.action, screen.words(MIX_SEVERAL).format(count=2).__eq__, description="a mix named")

        def none(screen: Screen) -> None:
            converter.list.remove(home_path(BASS))
            converter.list.remove(home_path(LEAD))

            screen.expect(converter.action, screen.words(CONVERT_NOTHING).__eq__, description="nothing to name")

        screen.scenario(one, several, a_mix, none).run()


class TestTheLinesOfTheCard:
    """Order joins from a mix's second recording, Destination always stands, and Input shows only while
    a run reads.
    """

    def test_order_and_destination(self, screen: Screen) -> None:
        """A mix of one shows no Order line, the second recording brings it; Destination always shows."""
        main = screen.main
        converter = main.converter

        def order_waits_for_a_second_recording_in_a_mix(screen: Screen) -> None:
            assert converter.destination()
            gather(screen, home_path(BASS))
            main.choose_output(OutputKind.MIXED)
            screen.expect(main.output, OutputKind.MIXED.__eq__, description="a mix")

            assert not screen.bridge.ask(lambda: read_item(TAG_MAIN_CONVERTER_GROUP_ORDER)).shown

        def the_second_brings_it(screen: Screen) -> None:
            gather(screen, home_path(LEAD))

            screen.expect(
                lambda: screen.bridge.ask(lambda: read_item(TAG_MAIN_CONVERTER_GROUP_ORDER)).shown,
                bool,
                description="Order joining",
            )
            assert converter.destination()

        screen.scenario(order_waits_for_a_second_recording_in_a_mix, the_second_brings_it).run()

    def test_input_stands_while_a_run_reads(self, screen: Screen, conversion_hold: ConversionHold) -> None:
        """The Input line is hidden before a held run, shown while it reads and hidden again after its end."""
        converter = screen.main.converter

        def no_input_before_the_run(screen: Screen) -> None:
            gather(screen, home_path(BASS))

            assert not screen.bridge.ask(lambda: read_item(TAG_MAIN_CONVERTER_GROUP_INPUT)).shown

        def input_while_it_reads(screen: Screen) -> None:
            converter.press_action()

            screen.bridge.expect(
                lambda: screen.bridge.ask(lambda: read_item(TAG_MAIN_CONVERTER_GROUP_INPUT)).shown,
                bool,
                description="the Input line",
                timeout=RUN_TIMEOUT_SECONDS,
            )

        def no_input_after_it(screen: Screen) -> None:
            conversion_hold.release()
            wait_for_the_end(screen)

            assert not screen.bridge.ask(lambda: read_item(TAG_MAIN_CONVERTER_GROUP_INPUT)).shown

        screen.scenario(no_input_before_the_run, input_while_it_reads, no_input_after_it).run()
