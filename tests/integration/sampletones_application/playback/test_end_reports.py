from tests.integration.sampletones_application.playback.breaks import (
    FINAL_ZERO,
    NO_CAUSE,
    SILENT_PREVIEW_END,
    SILENT_SONG_STOP,
    broken,
)
from tests.integration.sampletones_application.playback.material import (
    REALTIME,
    SoundCase,
    case,
    each,
    played_through,
    start_sounding,
)
from tests.integration.sampletones_application.playback.rig import EndCause, PlaybackRig, Sound
from tests.suite.base import BaseTestSuite


class TestNaturalEnd(BaseTestSuite):
    """Rule 3: a sound played to its end sends one end report, naming that it finished, once the output is free."""

    TestCase = SoundCase
    once_cases = (
        case(Sound.RECONSTRUCTION, broken(FINAL_ZERO)),
        case(Sound.INSTRUCTION, broken(FINAL_ZERO)),
        case(Sound.SONG),
        case(Sound.AUDITION),
        case(Sound.VOICE, broken(SILENT_PREVIEW_END)),
        case(Sound.FILE, broken(SILENT_PREVIEW_END)),
    )
    cause_cases = (
        case(Sound.RECONSTRUCTION, broken(FINAL_ZERO, NO_CAUSE)),
        case(Sound.INSTRUCTION, broken(FINAL_ZERO, NO_CAUSE)),
        case(Sound.SONG, broken(NO_CAUSE)),
        case(Sound.AUDITION, broken(NO_CAUSE)),
        case(Sound.VOICE, broken(SILENT_PREVIEW_END)),
        case(Sound.FILE, broken(SILENT_PREVIEW_END)),
    )

    @each(once_cases)
    def test_a_sound_played_to_its_end_reports_it_once(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        played_through(rig, test_case.sound)

        assert len(rig.ends(test_case.sound)) == 1

    @each(once_cases)
    def test_the_end_report_lands_with_the_output_free(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        played_through(rig, test_case.sound)

        assert rig.ends(test_case.sound)
        assert all(not end.holding and not end.open_streams for end in rig.ends(test_case.sound))

    @each(cause_cases)
    def test_the_end_report_names_the_sound_finished(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        played_through(rig, test_case.sound)

        assert rig.causes(test_case.sound) == [EndCause.FINISHED]


@REALTIME
class TestStoppedByItsOwner(BaseTestSuite):
    """Rule 3: a source its own tab stops sends one end report, naming the stop, once the output is free."""

    TestCase = SoundCase
    once_cases = (
        case(Sound.RECONSTRUCTION, broken(FINAL_ZERO)),
        case(Sound.INSTRUCTION, broken(FINAL_ZERO)),
        case(Sound.SONG, broken(SILENT_SONG_STOP)),
    )
    cause_cases = (
        case(Sound.RECONSTRUCTION, broken(FINAL_ZERO, NO_CAUSE)),
        case(Sound.INSTRUCTION, broken(FINAL_ZERO, NO_CAUSE)),
        case(Sound.SONG, broken(SILENT_SONG_STOP)),
    )

    @each(once_cases)
    def test_a_stopped_source_reports_its_end_once(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, test_case.sound)

        rig.stop(test_case.sound)
        rig.settle()

        assert len(rig.ends(test_case.sound)) == 1
        assert all(not end.holding for end in rig.ends(test_case.sound))

    @each(cause_cases)
    def test_the_end_report_names_the_stop(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, test_case.sound)

        rig.stop(test_case.sound)
        rig.settle()

        assert rig.causes(test_case.sound) == [EndCause.STOPPED]


@REALTIME
class TestStoppedByTheTransport(BaseTestSuite):
    """Rule 3: whatever sounds when the reader presses Stop sends one end report, naming the stop."""

    TestCase = SoundCase
    once_cases = (
        case(Sound.RECONSTRUCTION, broken(FINAL_ZERO)),
        case(Sound.INSTRUCTION, broken(FINAL_ZERO)),
        case(Sound.SONG, broken(SILENT_SONG_STOP)),
        case(Sound.AUDITION),
        case(Sound.VOICE, broken(SILENT_PREVIEW_END)),
        case(Sound.FILE, broken(SILENT_PREVIEW_END)),
    )
    cause_cases = (
        case(Sound.RECONSTRUCTION, broken(FINAL_ZERO, NO_CAUSE)),
        case(Sound.INSTRUCTION, broken(FINAL_ZERO, NO_CAUSE)),
        case(Sound.SONG, broken(SILENT_SONG_STOP)),
        case(Sound.AUDITION, broken(NO_CAUSE)),
        case(Sound.VOICE, broken(SILENT_PREVIEW_END)),
        case(Sound.FILE, broken(SILENT_PREVIEW_END)),
    )

    @each(once_cases)
    def test_a_sound_the_transport_stops_reports_its_end_once(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, test_case.sound)

        rig.stop_all()
        rig.settle()

        assert len(rig.ends(test_case.sound)) == 1
        assert all(not end.holding for end in rig.ends(test_case.sound))

    @each(cause_cases)
    def test_the_end_report_names_the_stop(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, test_case.sound)

        rig.stop_all()
        rig.settle()

        assert rig.causes(test_case.sound) == [EndCause.STOPPED]
