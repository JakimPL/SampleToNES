from dataclasses import dataclass, field
from typing import Dict
from unittest.mock import Mock

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.song import Song
from tests.suite.scenario import BaseTestScenario, ScenarioStep


def _sample(name: str) -> Sample:
    return Sample(name=name, reconstruction=Mock())


class TestPattern:
    def test_empty_pattern(self) -> None:
        pattern = Pattern.empty(8)
        assert pattern.length == 8
        assert pattern.name is None
        assert all(row == Row() for row in pattern.rows)


class TestChannel:
    def test_empty_channel(self) -> None:
        channel = Channel.empty(GeneratorName.PULSE1, rows_per_pattern=16)
        assert channel.generator == GeneratorName.PULSE1
        assert len(channel.patterns) == 1
        assert channel.order == [0]

    def test_pattern_resolution(self) -> None:
        channel = Channel.empty(GeneratorName.NOISE, rows_per_pattern=4)
        assert channel.pattern(0) is channel.patterns[0]
        assert channel.ordered_patterns() == [channel.patterns[0]]

    def test_unknown_pattern_returns_none(self) -> None:
        channel = Channel.empty(GeneratorName.NOISE, rows_per_pattern=4)
        assert channel.pattern(99) is None


class TestSong:
    def test_empty_song_has_all_channels(self) -> None:
        song = Song.empty(rows_per_pattern=8)
        assert set(song.channels) == set(GeneratorName.items())
        for generator in GeneratorName.items():
            assert song[generator].generator == generator


class TestProject:
    def test_create(self) -> None:
        project = Project.create(title="Demo")
        assert project.info.title == "Demo"
        assert len(project.samples) == 0
        assert set(project.song.channels) == set(GeneratorName.items())

    def test_instrument_resolution(self) -> None:
        project = Project.create()
        sample = _sample("lead")
        project.samples.append(sample)
        assert project.sample(sample.id) is sample
        assert project.sample("missing") is None


@dataclass
class SampleContext:
    project: Project
    sample: Sample
    instrument: Instrument
    resolved: Dict[str, Sample] = field(default_factory=dict)


class TestReferenceIntegrity:
    """Reordering a collection or editing an item in place must not break the
    stable-id references that the song relies on."""

    def _build_instrument_context(self) -> SampleContext:
        project = Project.create()
        first = _sample("first")
        second = _sample("second")
        project.samples.extend([first, second])
        instrument = Instrument(sample_id=first.id, generator_name=GeneratorName.PULSE1)
        return SampleContext(project=project, sample=first, instrument=instrument)

    def test_instrument_survives_instrument_reorder(self) -> None:
        def check_before(context: SampleContext) -> None:
            assert context.project.samples.index(context.sample) == 0
            context.resolved["before"] = context.project.sample(context.instrument.sample_id)

        def reorder(context: SampleContext) -> None:
            moved = context.project.samples.pop(0)
            context.project.samples.append(moved)
            assert context.project.samples.index(context.sample) == 1

        def check_after(context: SampleContext) -> None:
            resolved = context.project.sample(context.instrument.sample_id)
            assert resolved is context.sample
            assert resolved is context.resolved["before"]

        scenario = BaseTestScenario(
            label="instrument_reference_integrity",
            build=self._build_instrument_context,
            steps=[
                ScenarioStep(label="check_before", action=check_before),
                ScenarioStep(label="reorder", action=reorder),
                ScenarioStep(label="check_after", action=check_after),
            ],
        )
        scenario.run()
