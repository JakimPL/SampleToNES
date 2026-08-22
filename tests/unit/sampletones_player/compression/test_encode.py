from typing import Final, FrozenSet, Tuple

import pytest

from sampletones_player.compression.decode import decode_planes
from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.encode import emit, encode_planes
from sampletones_player.compression.options import CodecOptions
from sampletones_player.compression.planes.channel import ChannelPlanes
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.compression.progress.report import CodecProgress
from sampletones_player.compression.tokens.hold import HoldToken
from sampletones_player.compression.tokens.literal import LiteralToken
from sampletones_player.compression.tokens.phrase import PhraseToken
from sampletones_player.specification.compression import (
    MAX_PHRASE_TICKS,
    PHRASE_ID_ESCAPE,
    TokenTag,
)
from sampletones_shared.exceptions import OperationCancelled
from tests.suite.progress import FIRST_REPORT, RecordingReporter

EVERY_LAYER: Final[CodecOptions] = CodecOptions(
    holds=True,
    phrases=True,
    transposition=True,
    search=True,
)
SEEDED: Final[CodecOptions] = CodecOptions(
    holds=True,
    phrases=True,
    transposition=True,
    search=False,
)
NO_BOUNDARIES: Final[FrozenSet[int]] = frozenset()
MOTIF: Final[bytes] = bytes((40, 44, 47, 44))
TIMBRE: Final[bytes] = bytes((0x3F, 0x3A, 0x35, 0x30))
REPEATS: Final[int] = 12


def song_planes(control: bytes, value: bytes) -> SongPlanes:
    channel = ChannelPlanes(control=control, value=value)
    resting = ChannelPlanes(control=bytes(len(control)), value=bytes(len(value)))
    return SongPlanes(pulse1=channel, pulse2=resting, triangle=resting, noise=resting)


class TestWhatATokenLooksLikeOnTheBus:
    """The opcode layout is what the driver reads, so the bytes themselves are the contract."""

    def test_a_hold_carries_its_count_inside_its_opcode(self) -> None:
        assert emit((HoldToken(ticks=3),)) == bytes((TokenTag.HOLD | 2,))

    def test_a_literal_carries_its_length_inside_its_opcode(self) -> None:
        assert emit((LiteralToken(values=bytes((0x10, 0x20))),)) == bytes((TokenTag.LITERAL | 1, 0x10, 0x20))

    def test_a_phrase_carries_a_cheap_id_inside_its_opcode(self) -> None:
        token = PhraseToken(phrase_id=2, ticks=5, transpose=0)
        assert emit((token,)) == bytes((TokenTag.PHRASE | 2, 4))

    def test_a_shifted_phrase_states_the_shift_after_the_count(self) -> None:
        token = PhraseToken(phrase_id=2, ticks=5, transpose=0xFD)
        assert emit((token,)) == bytes((TokenTag.TRANSPOSED_PHRASE | 2, 4, 0xFD))

    def test_a_phrase_beyond_the_cheap_ids_names_itself_in_the_byte_that_follows(self) -> None:
        token = PhraseToken(phrase_id=200, ticks=MAX_PHRASE_TICKS, transpose=0)
        assert emit((token,)) == bytes((TokenTag.PHRASE | PHRASE_ID_ESCAPE, 200, MAX_PHRASE_TICKS - 1))

    def test_a_stream_takes_the_bytes_the_parse_counted(self) -> None:
        tokens = (LiteralToken(values=MOTIF), HoldToken(ticks=4), PhraseToken(phrase_id=1, ticks=2, transpose=3))
        assert len(emit(tokens)) == sum(token.size for token in tokens)


class TestEncodingASong:
    """The instruments seed the dictionary, the search fills the rest, and the table settles."""

    def test_a_song_plays_back_as_the_planes_it_was_written_from(self) -> None:
        planes = song_planes(TIMBRE * REPEATS, MOTIF * REPEATS)
        compressed = encode_planes(
            planes,
            (),
            options=EVERY_LAYER,
            boundaries=NO_BOUNDARIES,
        )
        assert decode_planes(compressed) == planes

    def test_the_figure_the_song_repeats_reaches_the_dictionary(self) -> None:
        """The search states the figure at whatever length pays best, the motif being its unit."""
        planes = song_planes(bytes((0x30,)) * (len(MOTIF) * REPEATS), MOTIF * REPEATS)
        compressed = encode_planes(
            planes,
            (),
            options=EVERY_LAYER,
            boundaries=NO_BOUNDARIES,
        )
        assert compressed.phrases.phrases
        for phrase in compressed.phrases.phrases:
            assert phrase.body == MOTIF * (len(phrase.body) // len(MOTIF))

    def test_a_seed_the_song_never_leans_on_leaves_the_dictionary(self) -> None:
        """A phrase earns its entry by sparing more than the entry costs."""
        planes = song_planes(bytes((0x30,)) * len(MOTIF), MOTIF)
        compressed = encode_planes(
            planes,
            (Phrase(body=MOTIF),),
            options=SEEDED,
            boundaries=NO_BOUNDARIES,
        )
        assert compressed.phrases.phrases == ()

    def test_the_figure_played_most_takes_the_cheapest_id(self) -> None:
        planes = song_planes(bytes((0x30,)) * (len(MOTIF) * REPEATS), MOTIF * REPEATS)
        seeds: Tuple[Phrase, ...] = (Phrase(body=bytes((0x30,)) * 8), Phrase(body=MOTIF))
        compressed = encode_planes(
            planes,
            seeds,
            options=SEEDED,
            boundaries=NO_BOUNDARIES,
        )
        assert compressed.phrases[0] == Phrase(body=MOTIF)

    def test_a_song_re_entered_at_a_boundary_still_plays_back_whole(self) -> None:
        planes = song_planes(TIMBRE * REPEATS, MOTIF * REPEATS)
        compressed = encode_planes(
            planes,
            (),
            options=EVERY_LAYER,
            boundaries=frozenset({len(MOTIF) * 3}),
        )
        assert decode_planes(compressed) == planes

    def test_every_plane_of_the_song_carries_a_stream(self) -> None:
        planes = song_planes(bytes((0x30,)) * 4, MOTIF)
        compressed = encode_planes(
            planes,
            (),
            options=EVERY_LAYER,
            boundaries=NO_BOUNDARIES,
        )
        assert len(compressed.streams) == len(planes.planes)
        assert compressed.ticks == planes.ticks


class TestWhatAnEncodingSaysAboutItself:
    """Compressing a song takes as long as the song decides, so it reports as it runs."""

    def test_the_last_word_is_what_the_run_answered_with(self) -> None:
        reporter: RecordingReporter[CodecProgress] = RecordingReporter()
        planes = song_planes(TIMBRE * REPEATS, MOTIF * REPEATS)
        compressed = encode_planes(
            planes,
            (),
            options=EVERY_LAYER,
            boundaries=NO_BOUNDARIES,
            report=reporter,
        )
        assert reporter.last == CodecProgress(phrases=len(compressed.phrases), size=compressed.size)

    def test_a_run_looks_up_often_enough_to_be_stopped(self) -> None:
        """The stretch between two reports is one plane, so a withdrawal lands within one."""
        reporter: RecordingReporter[CodecProgress] = RecordingReporter()
        planes = song_planes(TIMBRE * REPEATS, MOTIF * REPEATS)
        encode_planes(
            planes,
            (),
            options=EVERY_LAYER,
            boundaries=NO_BOUNDARIES,
            report=reporter,
        )
        assert len(reporter.reports) > len(planes.planes)


class TestWithdrawingAnEncoding:
    """A caller that stops wanting the song stops the work producing it."""

    def test_a_withdrawn_run_unwinds(self) -> None:
        reporter: RecordingReporter[CodecProgress] = RecordingReporter(withdraw_at=FIRST_REPORT)
        planes = song_planes(TIMBRE * REPEATS, MOTIF * REPEATS)
        with pytest.raises(OperationCancelled):
            encode_planes(
                planes,
                (),
                options=EVERY_LAYER,
                boundaries=NO_BOUNDARIES,
                report=reporter,
            )

    def test_a_withdrawn_run_stops_where_it_was_told(self) -> None:
        reporter: RecordingReporter[CodecProgress] = RecordingReporter(withdraw_at=FIRST_REPORT)
        planes = song_planes(TIMBRE * REPEATS, MOTIF * REPEATS)
        with pytest.raises(OperationCancelled):
            encode_planes(
                planes,
                (),
                options=EVERY_LAYER,
                boundaries=NO_BOUNDARIES,
                report=reporter,
            )

        assert len(reporter.reports) == FIRST_REPORT
