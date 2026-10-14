from sampletones_core.constants.audio import START_OF_AUDIO
from tests.integration.sampletones_application.playback.breaks import (
    FINAL_ZERO,
    SILENT_PREVIEW_END,
    STOP_ANY_BUFFER,
    broken,
)
from tests.integration.sampletones_application.playback.material import (
    REALTIME,
    SoundCase,
    Span,
    TakeoverCase,
    case,
    each,
    prepare,
    start,
    start_sounding,
    takeover,
)
from tests.integration.sampletones_application.playback.rig import PlaybackRig, Sound
from tests.suite.base import BaseTestSuite


@REALTIME
class TestPlayerOverPlayer(BaseTestSuite):
    """Rules 1 and 3: a source started over another takes the output, and the one it took hears its end once."""

    TestCase = TakeoverCase
    test_cases = (
        takeover(Sound.RECONSTRUCTION, Sound.INSTRUCTION),
        takeover(Sound.INSTRUCTION, Sound.RECONSTRUCTION),
        takeover(Sound.RECONSTRUCTION, Sound.SONG),
        takeover(Sound.SONG, Sound.RECONSTRUCTION),
    )
    told_cases = (
        takeover(Sound.RECONSTRUCTION, Sound.INSTRUCTION, broken(FINAL_ZERO)),
        takeover(Sound.INSTRUCTION, Sound.RECONSTRUCTION, broken(FINAL_ZERO)),
        takeover(Sound.RECONSTRUCTION, Sound.SONG, broken(FINAL_ZERO)),
        takeover(Sound.SONG, Sound.RECONSTRUCTION),
    )

    @each(test_cases)
    def test_the_taker_holds_the_output(self, rig: PlaybackRig, test_case: TakeoverCase) -> None:
        start_sounding(rig, test_case.taken)

        start_sounding(rig, test_case.taker)

        assert rig.engaged(test_case.taker)
        assert not rig.engaged(test_case.taken)

    @each(told_cases)
    def test_the_taken_source_hears_its_end_once(self, rig: PlaybackRig, test_case: TakeoverCase) -> None:
        start_sounding(rig, test_case.taken)

        start_sounding(rig, test_case.taker)

        ends = rig.ends(test_case.taken)
        assert len(ends) == 1
        assert not ends[0].holding

    @broken(FINAL_ZERO)
    def test_the_taken_player_takes_its_mark_off(self, rig: PlaybackRig) -> None:
        start_sounding(rig, Sound.RECONSTRUCTION)

        start_sounding(rig, Sound.INSTRUCTION)

        assert rig.positions(Sound.RECONSTRUCTION)[-1] == START_OF_AUDIO


@REALTIME
class TestAuditionTaken(BaseTestSuite):
    """Rule 3: an audition a player takes the output from hears its end once."""

    @broken(FINAL_ZERO)
    def test_the_audition_hears_its_end_once(self, rig: PlaybackRig) -> None:
        start_sounding(rig, Sound.AUDITION)

        start_sounding(rig, Sound.RECONSTRUCTION)

        assert len(rig.ends(Sound.AUDITION)) == 1


@REALTIME
class TestPreviewAgainstTheSong(BaseTestSuite):
    """Rules 1 and 3: a preview yields to the song, and the song, or a preview the reader asked for, takes the output."""

    TestCase = SoundCase
    test_cases = tuple(case(sound) for sound in (Sound.AUDITION, Sound.VOICE, Sound.FILE))
    told_cases = (
        case(Sound.AUDITION),
        case(Sound.VOICE, broken(SILENT_PREVIEW_END)),
        case(Sound.FILE, broken(SILENT_PREVIEW_END)),
    )
    asked_for = tuple(case(sound) for sound in (Sound.VOICE, Sound.FILE))

    @each(test_cases)
    def test_a_preview_yields_to_the_song(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, Sound.SONG)
        streams = len(rig.timeline.streams())

        prepare(rig, test_case.sound, Span.LONG)
        start(rig, test_case.sound)
        rig.drain()

        assert rig.engaged(Sound.SONG)
        assert len(rig.timeline.streams()) == streams

    @each(test_cases)
    def test_the_song_takes_over_a_preview(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, test_case.sound)

        start_sounding(rig, Sound.SONG)

        assert rig.engaged(Sound.SONG)
        assert rig.timeline.most_streams_open() == 1

    @each(told_cases)
    def test_a_preview_the_song_takes_over_hears_its_end_once(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, test_case.sound)

        start_sounding(rig, Sound.SONG)

        assert len(rig.ends(test_case.sound)) == 1

    @each(asked_for)
    def test_a_preview_asked_for_takes_over_the_song(self, rig: PlaybackRig, test_case: SoundCase) -> None:
        start_sounding(rig, Sound.SONG)
        prepare(rig, test_case.sound, Span.LONG)

        rig.play(test_case.sound)
        rig.wait_for(lambda: bool(rig.ends(Sound.SONG)), what="the song's end")

        assert not rig.engaged(Sound.SONG)
        assert len(rig.ends(Sound.SONG)) == 1


@REALTIME
class TestOwnStop(BaseTestSuite):
    """Rule 3: an owner's stop ends its own playback, and a sound another owner started plays on."""

    @broken(STOP_ANY_BUFFER)
    def test_a_player_stopping_leaves_a_preview_sounding(self, rig: PlaybackRig) -> None:
        start_sounding(rig, Sound.FILE)

        rig.stop(Sound.INSTRUCTION)

        assert rig.timeline.open_streams()
        assert rig.stop_available
