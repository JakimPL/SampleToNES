import operator
from functools import partial
from pathlib import Path
from typing import Callable, Dict, Final, List, Optional, Tuple

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.tags.general import TAG_GLOBAL_THEME_INPUT_INVALID, TAG_GLOBAL_THEME_INPUT_WARNING
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey, GeneratorName
from sampletones_core.formats.famitracker.specification.sequences import MAX_SEQUENCE_ITEMS
from sampletones_core.project import ProjectContainer
from sampletones_core.project.voices.instrument import Instrument
from sampletones_shared.paths.user import PROJECTS_DIRECTORY
from tests.suite.screens.application import Startup
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.dearpygui.keys import IMGUI_DIGIT_ZERO, IMGUI_LETTER_A
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.project import save_project_as
from tests.suite.screens.steps.reconstructions import edit_envelope, expect_open, marked, titled
from tests.suite.screens.steps.sequencer import open_voice
from tests.suite.screens.views.waveform import read_cursor
from tests.suite.screens.world import OPEN_RECONSTRUCTION, PLAYABLE_RECONSTRUCTION, SONG, SONG_INSTRUMENT

SAVED_SONG: Final[Path] = PROJECTS_DIRECTORY / "Saved.stp"
ASIDE: Final[Point] = Point(x=0, y=0)
STILL_FRAMES: Final[int] = 20
NOTE_FRAMES: Final[int] = 30
FADING: Final[str] = "12 8 4"
LOOPING_VOLUME: Final[str] = "15 14 | 12 10"
LOOPING_DUTY: Final[str] = "0 1 | 2"
LOOP_FROM_THE_START: Final[str] = "| 15"
TWO_LOOPS: Final[str] = "15 | | 14"
NOT_A_NUMBER: Final[str] = "x"
TOO_LOUD: Final[str] = "99"
LOUDEST: Final[str] = "15"
NOTHING: Final[str] = ""
BENT_ITEM: Final[int] = 2
FLAT_PITCH: Final[str] = "0 0 0 0 0"
BEND: Final[float] = 40.0
PITCH_FLOOR: Final[int] = -128
PITCH_CEILING: Final[int] = 127
PIANO_C: Final[int] = IMGUI_LETTER_A + ord("z") - ord("a")
PIANO_C_SHARP_UP: Final[int] = IMGUI_DIGIT_ZERO + 2
PULSE_ROWS: Final[Tuple[FeatureKey, ...]] = (
    FeatureKey.VOLUME,
    FeatureKey.ARPEGGIO,
    FeatureKey.PITCH,
    FeatureKey.HI_PITCH,
    FeatureKey.DUTY_CYCLE,
)
TRIANGLE_ROWS: Final[Tuple[FeatureKey, ...]] = (
    FeatureKey.VOLUME,
    FeatureKey.ARPEGGIO,
    FeatureKey.PITCH,
    FeatureKey.HI_PITCH,
)
NOISE_ROWS: Final[Tuple[FeatureKey, ...]] = (FeatureKey.VOLUME, FeatureKey.ARPEGGIO, FeatureKey.DUTY_CYCLE)
PITCH_BEND: Final[str] = "reconstructions.instruments.tooltip.pitch_bend"
HI_PITCH_BEND: Final[str] = "reconstructions.instruments.tooltip.hi_pitch_bend"
TYPING_HINT: Final[str] = "reconstructions.instruments.message.status_sequence"
TOO_LONG: Final[str] = "reconstructions.instruments.message.status_sequence_too_long"
KEPT_FAMITRACKER: Final[str] = "reconstructions.instruments.template.kept_famitracker"
INVALID_INPUT: Final[str] = "Invalid PULSE1 data input for VOLUME"
PLAY: Final[str] = "global.menu.label.item_playback_play"


def status_over(screen: Screen, item: str) -> str:
    """Brings the pointer onto ``item`` from the window's corner, which is what sets the status line, and reads it."""
    screen.hand.move_to(ASIDE)
    screen.hand.scroll_into_view(item)
    screen.hand.hover(item)
    return screen.status()


def saved_instrument(path: Path, name: str) -> Instrument:
    """The instrument named ``name`` in the project stored at ``path``."""
    return next(
        voice for voice in ProjectContainer.load(path).voices if isinstance(voice, Instrument) and voice.name == name
    )


def open_the_instrument(screen: Screen) -> None:
    instruments = screen.reconstructions.instruments
    open_voice(screen, SONG_INSTRUMENT)

    screen.expect(instruments.offers_audition, bool, description="the instrument open")


def song_title(screen: Screen, *, unsaved: bool) -> str:
    return titled(screen, marked(SONG.stem, unsaved=unsaved))


def leave_letting_the_project_go(screen: Screen) -> None:
    """Exits, answering Exit to the question about the project."""
    prompt = screen.project.unsaved_prompt
    screen.press_shortcut(ShortcutId.EXIT)
    screen.expect(prompt.is_shown, bool, description="the question about the project")

    prompt.confirm()

    assert screen.wait_for_exit()


def give_it_a_volume(screen: Screen) -> None:
    open_the_instrument(screen)
    edit_envelope(
        screen,
        channel=ChannelName.PULSE1,
        feature=FeatureKey.VOLUME,
        sequence=FADING,
        title=song_title(screen, unsaved=True),
    )


class TestTheRowsEachChannelDraws:
    """Pulse and triangle tabs draw Pitch and Hi-pitch rows, the noise tab neither; a bend field explains a step."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_rows_per_channel_and_the_bend_explanation(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments
        expected = {
            ChannelName.PULSE1: PULSE_ROWS,
            ChannelName.PULSE2: PULSE_ROWS,
            ChannelName.TRIANGLE: TRIANGLE_ROWS,
            ChannelName.NOISE: NOISE_ROWS,
        }

        def each_tab_draws_its_rows(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)

            for channel, rows in expected.items():
                instruments.bring_forward(channel)
                screen.expect(partial(instruments.rows, channel), rows.__eq__, description=f"the rows of {channel}")
                assert instruments.offers_pitch_stepper(channel)

            assert not instruments.offers_audition()

        def a_bend_field_explains_a_step(screen: Screen) -> None:
            instruments.bring_forward(ChannelName.PULSE1)
            for feature, key in ((FeatureKey.PITCH, PITCH_BEND), (FeatureKey.HI_PITCH, HI_PITCH_BEND)):
                field = instruments.field(ChannelName.PULSE1, feature)
                screen.hand.scroll_into_view(field)
                screen.hand.hover(field)

                screen.expect(partial(screen.shows_text, screen.words(key)), bool, description=f"{key} shown")

        def the_volume_field_explains_no_bend(screen: Screen) -> None:
            field = instruments.field(ChannelName.PULSE1, FeatureKey.VOLUME)
            screen.hand.scroll_into_view(field)
            screen.hand.hover(field)
            screen.frames(STILL_FRAMES)

            assert not screen.shows_text(screen.words(PITCH_BEND))
            assert not screen.shows_text(screen.words(HI_PITCH_BEND))

        screen.scenario(each_tab_draws_its_rows, a_bend_field_explains_a_step, the_volume_field_explains_no_bend).run()


class TestAHandWrittenVoice:
    """A hand-written voice offers the Audition switch and no pitch stepper, and Export follows its envelopes."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=SONG)

    def test_no_stepper_and_export_answers_while_it_sounds(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments

        def its_tab_alone(screen: Screen) -> None:
            open_the_instrument(screen)

            assert not instruments.offers_pitch_stepper(ChannelName.PULSE1)
            assert [channel for channel in ChannelName if instruments.tab_shown(channel)] == [ChannelName.PULSE1]
            assert not instruments.can_export(ChannelName.PULSE1)

        def a_volume_brings_export(screen: Screen) -> None:
            edit_envelope(
                screen,
                channel=ChannelName.PULSE1,
                feature=FeatureKey.VOLUME,
                sequence=FADING,
                title=song_title(screen, unsaved=True),
            )

            screen.expect(lambda: instruments.can_export(ChannelName.PULSE1), bool, description="Export answering")

        def clearing_it_greys_export_out(screen: Screen) -> None:
            instruments.type_envelope(ChannelName.PULSE1, FeatureKey.VOLUME, NOTHING)

            screen.expect(
                lambda: instruments.can_export(ChannelName.PULSE1), operator.not_, description="Export greyed out"
            )
            assert instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == NOTHING

        screen.scenario(
            its_tab_alone,
            a_volume_brings_export,
            clearing_it_greys_export_out,
            leave_letting_the_project_go,
        ).run()


class TestALoopTyped:
    """A sequence typed with "|" repeats from the item after it, and a sibling of another length from its own point.

    The status line explains the "|" before anything is typed.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=SONG)

    def test_each_envelope_keeps_its_own_loop(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments

        def the_status_line_explains_the_bar(screen: Screen) -> None:
            open_the_instrument(screen)
            field = instruments.field(ChannelName.PULSE1, FeatureKey.VOLUME)

            hint = screen.words(TYPING_HINT).format(instrument_feature=FeatureKey.VOLUME.capitalized)
            screen.expect(partial(status_over, screen, field), hint.__eq__, description="the hint about the bar")

        def type_two_loops(screen: Screen) -> None:
            edit_envelope(
                screen,
                channel=ChannelName.PULSE1,
                feature=FeatureKey.VOLUME,
                sequence=LOOPING_VOLUME,
                title=song_title(screen, unsaved=True),
            )
            instruments.type_envelope(ChannelName.PULSE1, FeatureKey.DUTY_CYCLE, LOOPING_DUTY)

            screen.expect(
                lambda: instruments.envelope(ChannelName.PULSE1, FeatureKey.DUTY_CYCLE),
                LOOPING_DUTY.__eq__,
                description="the duty cycle typed",
            )
            assert instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == LOOPING_VOLUME

        def the_project_keeps_each_loop(screen: Screen) -> None:
            save_project_as(screen, SAVED_SONG)

            envelopes = saved_instrument(SAVED_SONG, SONG_INSTRUMENT).envelopes
            assert (envelopes.volume.items, envelopes.volume.loop_point) == ((15, 14, 12, 10), 2)
            assert (envelopes.duty_cycle.items, envelopes.duty_cycle.loop_point) == ((0, 1, 2), 2)

        screen.scenario(the_status_line_explains_the_bar, type_two_loops, the_project_keeps_each_loop).run()


class TestSequencesTheFieldAnswers:
    """A sequence the field cannot read is refused and leaves the envelope; one it can read is applied as written.

    A value past the range is brought into it, an empty field clears the dimension, and one longer than
    an export keeps is applied with a warning naming what the export keeps.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=SONG)

    def test_refused_clamped_cleared_and_warned(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments
        long_sequence = " ".join(["8"] * (MAX_SEQUENCE_ITEMS + 1))
        plain: List[Optional[str]] = []

        def typed(sequence: str) -> None:
            instruments.type_envelope(ChannelName.PULSE1, FeatureKey.VOLUME, sequence)
            screen.frames(STILL_FRAMES)

        def theme() -> Optional[str]:
            return instruments.field_theme(ChannelName.PULSE1, FeatureKey.VOLUME)

        def unreadable_sequences_are_refused(screen: Screen) -> None:
            open_the_instrument(screen)
            plain.append(theme())

            for sequence in (TWO_LOOPS, NOT_A_NUMBER):
                typed(sequence)

                screen.claim_error(INVALID_INPUT)
                assert theme() == TAG_GLOBAL_THEME_INPUT_INVALID
                assert instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == sequence
                assert screen.title() == song_title(screen, unsaved=False)

        def a_loop_from_the_start_is_applied(screen: Screen) -> None:
            typed(LOOP_FROM_THE_START)

            screen.expect(screen.title, song_title(screen, unsaved=True).__eq__, description="the edit applied")
            assert theme() != TAG_GLOBAL_THEME_INPUT_INVALID
            assert instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == LOOP_FROM_THE_START

        def a_value_past_the_range_is_brought_into_it(screen: Screen) -> None:
            typed(TOO_LOUD)

            screen.expect(
                lambda: instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
                LOUDEST.__eq__,
                description="the loudest level written",
            )

        def a_sequence_past_every_export_is_applied_with_a_warning(screen: Screen) -> None:
            typed(long_sequence)

            screen.expect(theme, TAG_GLOBAL_THEME_INPUT_WARNING.__eq__, description="the warning")
            instruments.bring_forward(ChannelName.PULSE1)
            field = instruments.field(ChannelName.PULSE1, FeatureKey.VOLUME)
            warning = screen.words(TOO_LONG).format(
                instrument_feature=FeatureKey.VOLUME.capitalized,
                items=MAX_SEQUENCE_ITEMS + 1,
                kept=screen.words(KEPT_FAMITRACKER).format(limit=MAX_SEQUENCE_ITEMS),
            )
            screen.expect(
                partial(status_over, screen, field), warning.__eq__, description="the status naming what each keeps"
            )

        def an_empty_field_clears_it(screen: Screen) -> None:
            typed(NOTHING)

            screen.expect(theme, plain[0].__eq__, description="the warning gone")
            assert instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == NOTHING

        def the_project_keeps_what_was_applied_last(screen: Screen) -> None:
            typed(FADING)
            screen.expect(
                lambda: instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
                FADING.__eq__,
                description="the last sequence applied",
            )

            save_project_as(screen, SAVED_SONG)

            assert saved_instrument(SAVED_SONG, SONG_INSTRUMENT).envelopes.volume.items == (12, 8, 4)

        screen.scenario(
            unreadable_sequences_are_refused,
            a_loop_from_the_start_is_applied,
            a_value_past_the_range_is_brought_into_it,
            a_sequence_past_every_export_is_applied_with_a_warning,
            an_empty_field_clears_it,
            the_project_keeps_what_was_applied_last,
        ).run()


class TestDraggingAPitchBar:
    """Dragging a bar of the Pitch row sets that item to the value the drag lets go at, and only that item."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=SONG)

    def test_the_item_takes_the_value_under_the_release(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments
        graph = instruments.graph(ChannelName.PULSE1, FeatureKey.PITCH)
        standing: List[int] = []

        def give_it_a_flat_pitch(screen: Screen) -> None:
            give_it_a_volume(screen)
            instruments.type_envelope(ChannelName.PULSE1, FeatureKey.PITCH, FLAT_PITCH)
            screen.expect(
                lambda: instruments.envelope(ChannelName.PULSE1, FeatureKey.PITCH),
                FLAT_PITCH.__eq__,
                description="the flat pitch typed",
            )

            screen.hand.scroll_into_view(graph.plot)

            standing.extend(int(item) for item in FLAT_PITCH.split())

        def drag_one_bar(screen: Screen) -> None:
            release = graph.drag_item(BENT_ITEM, start=standing[BENT_ITEM], end=BEND)

            _, under = graph.value_under(release)
            expected = [*standing]
            expected[BENT_ITEM] = min(max(round(under), PITCH_FLOOR), PITCH_CEILING)
            screen.expect(
                lambda: [int(item) for item in instruments.envelope(ChannelName.PULSE1, FeatureKey.PITCH).split()],
                expected.__eq__,
                description="one item bent",
            )
            assert expected[BENT_ITEM] != standing[BENT_ITEM]

        screen.scenario(give_it_a_flat_pitch, drag_one_bar, leave_letting_the_project_go).run()


class TestTheNoteKeys:
    """With an instrument open the note keys sound it, a field being typed in takes them as characters,
    and the keys a reconstruction gives a meaning keep it."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=SONG)

    def test_keys_sound_the_instrument_and_a_field_keeps_them(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments

        def sounded(key: int) -> bool:
            with screen.record(partial(read_cursor, screen.reconstructions.waveform.cursor_line)) as recording:
                screen.hand.press_key(key, modifiers=[])
                screen.frames(NOTE_FRAMES)

            return any(reading is not None and reading > 0 for reading in recording.values())

        def the_keys_sound_it(screen: Screen) -> None:
            give_it_a_volume(screen)

            assert sounded(PIANO_C)
            assert sounded(PIANO_C_SHARP_UP)

        def a_field_takes_them_as_characters(screen: Screen) -> None:
            field = instruments.field(ChannelName.PULSE1, FeatureKey.ARPEGGIO)
            screen.hand.scroll_into_view(field)
            screen.hand.click(field)

            assert not sounded(PIANO_C)
            assert "z" in instruments.envelope(ChannelName.PULSE1, FeatureKey.ARPEGGIO)

        screen.scenario(the_keys_sound_it, a_field_takes_them_as_characters, leave_letting_the_project_go).run()

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: an instrument's note keys take Ctrl+Z on the Reconstructions tab",
    )
    def test_undo_undoes_with_an_instrument_open(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments
        give_it_a_volume(screen)
        screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)

        screen.press_shortcut(ShortcutId.UNDO)

        screen.expect(
            lambda: instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
            NOTHING.__eq__,
            description="the volume undone",
        )


class TestAChannelKeyOnAReconstruction:
    """With a reconstruction open, a channel's number key ticks its box above the waveform."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_two_lets_pulse_two_go_and_brings_it_back(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        expect_open(screen, OPEN_RECONSTRUCTION)
        assert reconstructions.channel_ticked(ChannelName.PULSE2)

        screen.press_shortcut(ShortcutId.TOGGLE_CHANNEL_PULSE_2)

        screen.expect(
            lambda: reconstructions.channel_ticked(ChannelName.PULSE2), operator.not_, description="Pulse 2 let go"
        )
        screen.press_shortcut(ShortcutId.TOGGLE_CHANNEL_PULSE_2)
        screen.expect(lambda: reconstructions.channel_ticked(ChannelName.PULSE2), bool, description="Pulse 2 back")


class TestTheAuditionSwitch:
    """The Audition switch draws the instrument on the generator it names, and back."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=None, project=SONG)

    def test_each_generator_redraws_the_waveform(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments
        waveform = screen.reconstructions.waveform
        drawn: Dict[GeneratorName, List[float]] = {}

        def drawn_now() -> List[float]:
            return waveform.drawn(SONG_INSTRUMENT)

        def on_the_pulse(screen: Screen) -> None:
            give_it_a_volume(screen)

            assert instruments.audition() == screen.generator_words(GeneratorName.PULSE)
            drawn[GeneratorName.PULSE] = drawn_now()

        def on_the_triangle(screen: Screen) -> None:
            instruments.choose_audition(screen.generator_words(GeneratorName.TRIANGLE))

            drawn[GeneratorName.TRIANGLE] = screen.expect(
                drawn_now, drawn[GeneratorName.PULSE].__ne__, description="the waveform redrawn"
            )

        def back_on_the_pulse(screen: Screen) -> None:
            instruments.choose_audition(screen.generator_words(GeneratorName.PULSE))

            screen.expect(drawn_now, drawn[GeneratorName.PULSE].__eq__, description="the pulse drawn again")

        screen.scenario(on_the_pulse, on_the_triangle, back_on_the_pulse, leave_letting_the_project_go).run()


class TestAnInstrumentsWaveform:
    """A click on an open instrument's waveform plays nothing, while a note key sounds it.

    A reconstruction that plays stands open before the instrument, so a click that sounds anything
    at all is heard.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=SONG)

    def test_a_click_plays_nothing_and_a_key_does(self, screen: Screen) -> None:
        waveform = screen.reconstructions.waveform

        def cursors_over(gesture: Callable[[], None]) -> List[Optional[float]]:
            with screen.record(partial(read_cursor, waveform.cursor_line)) as recording:
                gesture()
                screen.frames(NOTE_FRAMES)

            return recording.values()

        def a_click_plays_nothing(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            give_it_a_volume(screen)
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)

            cursors = cursors_over(partial(waveform.click, 0.5))

            assert not any(cursors)
            assert screen.sequencer.playback.play_entry() == screen.words(PLAY)

        def a_note_key_sounds_it(screen: Screen) -> None:
            cursors = cursors_over(partial(screen.hand.press_key, PIANO_C, modifiers=[]))

            assert any(cursors)

        screen.scenario(a_click_plays_nothing, a_note_key_sounds_it, leave_letting_the_project_go).run()
