from typing import Tuple

import pytest

from sampletones_player.compression.options import EVERY_LAYER, CodecOptions
from sampletones_player.compression.scheme import CompressionScheme, offered_schemes


def layers(options: CodecOptions) -> Tuple[bool, ...]:
    return (options.holds, options.phrases, options.transposition, options.search)


class TestCompressionScheme:
    """Each scheme keeps the layers of the one before it and adds its own."""

    def test_the_lightest_scheme_spells_every_value_out(self) -> None:
        assert not any(layers(CompressionScheme.NONE.options))

    def test_the_hardest_scheme_switches_every_layer_on(self) -> None:
        assert CompressionScheme.SEARCH.options == EVERY_LAYER

    @pytest.mark.parametrize(
        ("lighter", "harder"),
        list(zip(list(CompressionScheme)[:-1], list(CompressionScheme)[1:])),
        ids=str,
    )
    def test_a_harder_scheme_keeps_every_layer_of_the_lighter_one(
        self,
        lighter: CompressionScheme,
        harder: CompressionScheme,
    ) -> None:
        pairs = list(zip(layers(lighter.options), layers(harder.options)))
        assert all(on_harder for on_lighter, on_harder in pairs if on_lighter)
        assert layers(lighter.options) != layers(harder.options)


class TestOfferedSchemes:
    """A song is offered the schemes that write it differently."""

    def test_a_seeded_song_is_offered_every_scheme(self) -> None:
        assert offered_schemes(seeded=True) == tuple(CompressionScheme)

    def test_a_song_seeding_nothing_is_offered_every_scheme_but_the_instruments(self) -> None:
        assert offered_schemes(seeded=False) == tuple(
            scheme for scheme in CompressionScheme if scheme != CompressionScheme.INSTRUMENTS
        )
