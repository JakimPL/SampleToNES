import struct
from pathlib import Path
from typing import Dict, Final, Tuple

import pytest

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_player.builder import song_from_reconstruction
from sampletones_player.driver.image import DriverImage
from sampletones_player.nsf.file import write_nsf
from sampletones_player.nsf.information import NSFInformation
from sampletones_player.nsf.song import song_to_bytes
from sampletones_player.song import Song
from sampletones_player.specification.binary import WORD_SIZE
from sampletones_player.specification.nsf import (
    HEADER_SIZE,
    NSF_MAGIC,
    PROGRAM_SIZE,
)
from sampletones_player.specification.song import (
    LOOP_TICK_OFFSET,
    NO_LOOP,
    SONG_HEADER_SIZE,
    STEP_FRACTION_OFFSET,
    STEP_WHOLE_OFFSET,
    STREAM_OFFSETS_OFFSET,
    TOTAL_TICKS_OFFSET,
)
from sampletones_shared.paths.extensions import EXT_FILE_RECONSTRUCTION

ARTIST: Final[str] = "Integration"


def exported_information(name: str) -> NSFInformation:
    return NSFInformation(title=name, artist=ARTIST)


def song_block(data: bytes, image: DriverImage) -> bytes:
    return data[HEADER_SIZE + len(image.code) :]


def read_word(data: bytes, offset: int) -> int:
    return int(struct.unpack_from("<H", data, offset)[0])


def stream_offsets(block: bytes) -> Tuple[int, ...]:
    return tuple(read_word(block, STREAM_OFFSETS_OFFSET + WORD_SIZE * channel) for channel in range(len(GeneratorName)))


@pytest.fixture
def exported(song: Song, sample: Sample, nsf_paths: Dict[str, Path]) -> bytes:
    destination = nsf_paths[sample.name]
    write_nsf(destination, song, exported_information(sample.name))
    return destination.read_bytes()


class TestNsfPipeline:
    """End-to-end: synthesized and reconstructed samples -> `Song` -> a playable `.nsf`."""

    def test_every_sample_reaches_a_playable_file(
        self,
        instrument_catalog: Dict[str, Sample],
        nsf_paths: Dict[str, Path],
    ) -> None:
        for name, sample in instrument_catalog.items():
            song = song_from_reconstruction(sample.reconstruction, loop_tick=None)
            write_nsf(nsf_paths[name], song, exported_information(name))
            assert nsf_paths[name].read_bytes()[: len(NSF_MAGIC)] == NSF_MAGIC

    def test_the_file_carries_the_shipped_driver(self, exported: bytes, driver_image: DriverImage) -> None:
        assert exported[HEADER_SIZE : HEADER_SIZE + len(driver_image.code)] == driver_image.code

    def test_the_loaded_image_fits_the_program_area(self, exported: bytes) -> None:
        assert len(exported) - HEADER_SIZE <= PROGRAM_SIZE

    def test_the_song_follows_the_driver_whole(
        self,
        exported: bytes,
        song: Song,
        driver_image: DriverImage,
    ) -> None:
        available = PROGRAM_SIZE - len(driver_image.code)
        assert song_block(exported, driver_image) == song_to_bytes(song, available)


class TestTheSongTheFileCarries:
    """What the driver reads out of the block behind it."""

    def test_the_song_states_the_ticks_the_reconstruction_covers(
        self,
        exported: bytes,
        song: Song,
        driver_image: DriverImage,
    ) -> None:
        assert read_word(song_block(exported, driver_image), TOTAL_TICKS_OFFSET) == song.ticks

    def test_the_song_states_the_rate_it_was_built_at(
        self,
        exported: bytes,
        song: Song,
        driver_image: DriverImage,
    ) -> None:
        block = song_block(exported, driver_image)
        step = song.schedule.fixed_point_step
        assert (block[STEP_WHOLE_OFFSET], read_word(block, STEP_FRACTION_OFFSET)) == (step.whole, step.fraction)

    def test_a_sample_that_ends_stops_there(
        self,
        exported: bytes,
        driver_image: DriverImage,
    ) -> None:
        block = song_block(exported, driver_image)
        assert read_word(block, LOOP_TICK_OFFSET) == NO_LOOP

    def test_every_stream_begins_inside_the_block(
        self,
        exported: bytes,
        driver_image: DriverImage,
    ) -> None:
        block = song_block(exported, driver_image)
        offsets = stream_offsets(block)
        assert offsets[0] == SONG_HEADER_SIZE
        assert all(offset < len(block) for offset in offsets)

    def test_the_streams_stand_in_channel_order(
        self,
        exported: bytes,
        driver_image: DriverImage,
    ) -> None:
        offsets = stream_offsets(song_block(exported, driver_image))
        assert list(offsets) == sorted(offsets)


class TestAStoredReconstructionExportsTheSameFile:
    """A reconstruction saved and read back plays as the very file it played as before."""

    def test_the_round_trip_leaves_the_exported_bytes_alone(
        self,
        sample: Sample,
        song: Song,
        tmp_path: Path,
    ) -> None:
        stored = tmp_path / f"{sample.name}{EXT_FILE_RECONSTRUCTION}"
        sample.reconstruction.save(stored)
        reloaded = song_from_reconstruction(Reconstruction.load(stored), loop_tick=None)

        information = exported_information(sample.name)
        before = tmp_path / "before.nsf"
        after = tmp_path / "after.nsf"
        write_nsf(before, song, information)
        write_nsf(after, reloaded, information)

        assert after.read_bytes() == before.read_bytes()
