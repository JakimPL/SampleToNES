from typing import Dict

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from sampletones_tools.corpus.song import ChannelSpec, RowSpec, SongSpec, build_song
from tests.suite.performance import make_noise_reconstruction, make_pulse_reconstruction

ROWS_PER_PATTERN: int = 4


def _catalog() -> Dict[str, Sample]:
    return {
        "lead": Sample(name="lead", reconstruction=make_pulse_reconstruction()),
        "hihat": Sample(name="hihat", reconstruction=make_noise_reconstruction()),
    }


def _spec(channel: ChannelName, rows: Dict[int, RowSpec]) -> SongSpec:
    return SongSpec(
        rows_per_pattern=ROWS_PER_PATTERN,
        order=[{channel: 0}],
        channels={channel: ChannelSpec(patterns={0: list(rows.values())})},
    )


class TestSongSpec:
    def test_the_shipped_arrangement_loads_from_the_package(self) -> None:
        spec = SongSpec.load()

        assert spec.rows_per_pattern > 0
        assert spec.order
        assert set(spec.channels) <= set(ChannelName.items())


class TestBuildSong:
    def test_every_written_row_reaches_its_pattern(self) -> None:
        catalog = _catalog()
        spec = _spec(
            ChannelName.PULSE1,
            {
                0: RowSpec(row=0, sample="lead", transpose=12, volume=10),
                2: RowSpec(row=2, off=True),
                3: RowSpec(row=3, volume=4),
            },
        )

        song = build_song(spec, catalog)

        rows = song.channels[ChannelName.PULSE1].patterns[0].rows
        assert len(rows) == ROWS_PER_PATTERN
        assert rows[0].command == NoteOn(voice_id=catalog["lead"].id)
        assert (rows[0].transpose, rows[0].volume) == (12, 10)
        assert rows[1].command is None
        assert isinstance(rows[2].command, NoteOff)
        assert (rows[3].command, rows[3].volume) == (None, 4)

    def test_the_order_names_every_channel_and_every_channel_is_present(self) -> None:
        song = build_song(_spec(ChannelName.NOISE, {0: RowSpec(row=0, sample="hihat")}), _catalog())

        assert song.order == [{channel: 0 if channel == ChannelName.NOISE else None for channel in ChannelName.items()}]
        assert set(song.channels) == set(ChannelName.items())
        assert song.channels[ChannelName.PULSE1].patterns == {}

    def test_a_sample_the_catalog_lacks_is_refused(self) -> None:
        with pytest.raises(KeyError, match="snare"):
            build_song(_spec(ChannelName.NOISE, {0: RowSpec(row=0, sample="snare")}), _catalog())

    def test_a_sample_on_a_channel_it_has_no_slice_for_is_refused(self) -> None:
        with pytest.raises(ValueError, match="Sample 'lead' has no 'noise' slice"):
            build_song(_spec(ChannelName.NOISE, {0: RowSpec(row=0, sample="lead")}), _catalog())
