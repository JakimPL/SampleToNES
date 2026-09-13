from typing import Dict

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.voices.sample import Sample
from sampletones_tools.corpus.build import build_project
from sampletones_tools.corpus.module import ModuleConfig
from sampletones_tools.corpus.song import ChannelSpec, RowSpec, SongSpec
from tests.suite.performance import make_pulse_reconstruction, make_triangle_reconstruction

MODULE: ModuleConfig = ModuleConfig(title="Demo", author="Someone", tempo=125, speed=3, nes_frequency=50)


def _catalog() -> Dict[str, Sample]:
    return {
        "lead": Sample(name="lead", reconstruction=make_pulse_reconstruction()),
        "bass": Sample(name="bass", reconstruction=make_triangle_reconstruction()),
    }


class TestBuildProject:
    def test_the_project_carries_the_module_the_voices_and_the_song(self) -> None:
        catalog = _catalog()
        spec = SongSpec(
            rows_per_pattern=2,
            order=[{ChannelName.TRIANGLE: 0}],
            channels={ChannelName.TRIANGLE: ChannelSpec(patterns={0: [RowSpec(row=0, sample="bass")]})},
        )

        project = build_project(catalog, MODULE, spec)

        assert (project.info.title, project.info.author) == ("Demo", "Someone")
        assert (project.settings.tempo, project.settings.speed, project.settings.nes_frequency) == (125, 3, 50)
        assert [voice.name for voice in project.voices] == ["lead", "bass"]
        assert project.song.rows_per_pattern == 2
        assert project.song.channels[ChannelName.TRIANGLE].patterns[0].rows[0].volume is None
