from typing import Dict, Final, Tuple

import pytest
from pydantic import ValidationError

from assets.demo.specification import (
    ConversionSpec,
    DemoSpecification,
    Hit,
    Note,
    Piece,
    PieceConversion,
    RecordingsSpec,
    Stem,
)
from sampletones_core.constants.enums import ChannelName, HierarchyMode

SHIPPED: Final[DemoSpecification] = DemoSpecification.load()
UNKNOWN_VOICE: Final[str] = "theremin"
STEM_CHANNELS: Final[Dict[str, Tuple[ChannelName, ...]]] = {
    "Lead": (ChannelName.PULSE1,),
    "Bass": (ChannelName.TRIANGLE,),
}


def recordings(*, hit_voice: str, note_voice: str) -> RecordingsSpec:
    return RecordingsSpec(
        sample_rate=44100,
        tempo=120.0,
        amplitude=0.8,
        hits=(Hit(name="Kick", voice=hit_voice),),
        piece=Piece(
            name="Piece",
            beats=4.0,
            stems=(Stem(name="Lead", notes=(Note(voice=note_voice, start=0.0, length=1.0, pitch=69),)),),
        ),
    )


class TestTheShippedSpecification:
    """The four shipped files read as one specification whose names all reach what they name."""

    def test_every_stem_is_converted_on_one_level(self) -> None:
        conversion = SHIPPED.conversion.piece
        named = [name for level in conversion.levels for name in level]

        assert sorted(named) == sorted(stem.name for stem in SHIPPED.recordings.piece.stems)
        assert len(named) == len(set(named))

    def test_every_hit_has_channels_to_take(self) -> None:
        assert all(SHIPPED.conversion.hits[hit.name] for hit in SHIPPED.recordings.hits)

    def test_the_song_plays_hits_and_instruments_alone(self) -> None:
        played = {
            row.voice
            for channel in SHIPPED.project.song.channels.values()
            for rows in channel.patterns.values()
            for row in rows
            if row.voice is not None
        }
        offered = {hit.name for hit in SHIPPED.recordings.hits} | set(SHIPPED.project.instruments)

        assert played <= offered


class TestNamesAreHeldToEachOther:
    """A specification naming what no file declares is refused as it is read."""

    def test_a_note_striking_an_undeclared_voice_is_refused(self) -> None:
        with pytest.raises(ValidationError, match=UNKNOWN_VOICE):
            DemoSpecification(
                voices=SHIPPED.voices,
                recordings=recordings(hit_voice="kick", note_voice=UNKNOWN_VOICE),
                conversion=SHIPPED.conversion,
                project=SHIPPED.project,
            )

    def test_a_stem_named_on_two_levels_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="levels"):
            PieceConversion(
                mode=HierarchyMode.ROUND_ROBIN,
                levels=(("Lead",), ("Lead", "Bass")),
                stems=STEM_CHANNELS,
            )

    def test_a_stem_left_off_every_level_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="levels"):
            PieceConversion(mode=HierarchyMode.STRICT, levels=(("Lead",),), stems=STEM_CHANNELS)

    def test_a_note_past_the_end_of_the_piece_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="past"):
            Piece(
                name="Piece",
                beats=2.0,
                stems=(Stem(name="Lead", notes=(Note(voice="lead", start=2.0, length=None, pitch=None),)),),
            )

    def test_a_hit_without_a_conversion_setup_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="hits"):
            DemoSpecification(
                voices=SHIPPED.voices,
                recordings=recordings(hit_voice="kick", note_voice="lead"),
                conversion=ConversionSpec(hits={}, piece=SHIPPED.conversion.piece),
                project=SHIPPED.project,
            )
