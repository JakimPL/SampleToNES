from pathlib import Path

import numpy as np
from PIL import Image

from assets.footage.frames import filmed, frame_path, prepare_frames, write_frame

SHOOT = '{"shoot": 1}'


def kept(folder: Path, count: int) -> None:
    for index in range(count):
        write_frame(np.zeros((2, 2, 3), dtype=np.uint8), frame_path(folder, index))


class TestFrames:
    def test_the_frames_are_counted_up_to_the_first_one_missing(self, tmp_path: Path) -> None:
        kept(tmp_path, 3)
        frame_path(tmp_path, 1).unlink()

        assert filmed(tmp_path) == 1

    def test_a_frame_is_kept_whole_and_readable(self, tmp_path: Path) -> None:
        frame = np.full((2, 3, 3), 7, dtype=np.uint8)

        write_frame(frame, frame_path(tmp_path, 0))

        np.testing.assert_array_equal(np.asarray(Image.open(frame_path(tmp_path, 0))), frame)
        assert [path.name for path in tmp_path.iterdir()] == [frame_path(tmp_path, 0).name]


class TestPreparedFrames:
    def test_the_frames_of_the_same_shoot_are_kept(self, tmp_path: Path) -> None:
        prepare_frames(tmp_path, SHOOT, fresh=False)
        kept(tmp_path, 2)

        prepare_frames(tmp_path, SHOOT, fresh=False)

        assert filmed(tmp_path) == 2

    def test_another_shoot_films_every_frame_again(self, tmp_path: Path) -> None:
        prepare_frames(tmp_path, SHOOT, fresh=False)
        kept(tmp_path, 2)

        prepare_frames(tmp_path, '{"shoot": 2}', fresh=False)

        assert filmed(tmp_path) == 0

    def test_a_fresh_take_films_every_frame_again(self, tmp_path: Path) -> None:
        prepare_frames(tmp_path, SHOOT, fresh=False)
        kept(tmp_path, 2)

        prepare_frames(tmp_path, SHOOT, fresh=True)

        assert filmed(tmp_path) == 0
