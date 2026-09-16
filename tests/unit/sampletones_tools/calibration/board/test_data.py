import json
from typing import Tuple

from sampletones_tools.calibration.board.data import DATA_GLOBAL, data_script
from sampletones_tools.calibration.board.model import BoardCell, BoardChannel, BoardGroup, BoardPage, BoardRow

PREFIX: Tuple[str, str] = (f"const {DATA_GLOBAL} = ", ";")


def page() -> BoardPage:
    channel = BoardChannel(name="noise", timeline="1100", solo="a.flac", mute="b.flac")
    cell = BoardCell(render="renders/cqt-pe1/tone-a.flac", score=9.5, silence=20.0, channels=(channel,))
    row = BoardRow(item="tone-a", category="tone", recording="recordings/tone-a.flac", cells=(cell,))
    group = BoardGroup(name="run-a", columns=("cqt-pe1",), rows=(row,))
    return BoardPage(title="Calibration", referee="mr-auditory-dB", colors={"noise": "channel_noise"}, groups=(group,))


class TestDataScript:
    def test_the_page_travels_as_the_one_global_the_script_reads(self) -> None:
        script = data_script(page())

        assert script.startswith(PREFIX[0])
        assert script.rstrip().endswith(PREFIX[1])

    def test_everything_the_page_draws_reads_back_unchanged(self) -> None:
        script = data_script(page())

        body = script.strip()[len(PREFIX[0]) : -1]
        assert BoardPage.model_validate(json.loads(body)) == page()
