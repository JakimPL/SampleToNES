from dataclasses import dataclass, field
from typing import Dict, List
from unittest.mock import Mock

import pytest

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project import (
    Channel,
    Pattern,
    Project,
    Row,
    Song,
    SubInstrument,
)
from sampletones_core.sequencer import Instrument
from sampletones_core.structures import IndexedCollection
from tests.suite.scenario import BaseTestScenario, ScenarioStep


def _instrument(name: str) -> Instrument:
    return Instrument(name=name, reconstruction=Mock())


class TestPattern:
    def test_empty_pattern(self) -> None:
        pattern = Pattern.empty(8)
        assert pattern.length == 8
        assert pattern.name is None
        assert all(row == Row() for row in pattern.rows)

    def test_ids_are_unique(self) -> None:
        assert Pattern.empty(1).id != Pattern.empty(1).id

    def test_hash_is_stable_under_mutation(self) -> None:
        pattern = Pattern.empty(4)
        original_hash = hash(pattern)
        pattern.name = "lead"
        pattern.rows = pattern.rows[:2]
        assert hash(pattern) == original_hash
        assert pattern.length == 2

    def test_equality_is_by_id(self) -> None:
        pattern = Pattern.empty(1)
        assert pattern == pattern  # pylint: disable=comparison-with-itself
        assert pattern != Pattern.empty(1)


class TestChannel:
    def test_empty_channel(self) -> None:
        channel = Channel.empty(GeneratorName.PULSE1, rows_per_pattern=16)
        assert channel.generator == GeneratorName.PULSE1
        assert len(channel.patterns) == 1
        assert channel.order == [channel.patterns[0].id]

    def test_pattern_resolution(self) -> None:
        channel = Channel.empty(GeneratorName.NOISE, rows_per_pattern=4)
        pattern_id = channel.patterns[0].id
        assert channel.pattern(pattern_id) is channel.patterns[0]
        assert channel.ordered_patterns() == [channel.patterns[0]]

    def test_unknown_pattern_raises(self) -> None:
        channel = Channel.empty(GeneratorName.NOISE, rows_per_pattern=4)
        with pytest.raises(KeyError):
            channel.pattern("missing")


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
        assert len(project.instruments) == 0
        assert set(project.song.channels) == set(GeneratorName.items())

    def test_instrument_resolution(self) -> None:
        project = Project.create()
        instrument = _instrument("lead")
        project.instruments.append(instrument)
        assert project.instrument(instrument.id) is instrument
        assert project.instrument("missing") is None


@dataclass
class PatternContext:
    channel: Channel
    patterns: List[Pattern]


@dataclass
class InstrumentContext:
    project: Project
    instrument: Instrument
    subinstrument: SubInstrument
    resolved: Dict[str, Instrument] = field(default_factory=dict)


class TestReferenceIntegrity:
    """Reordering a collection or editing an item in place must not break the
    stable-id references that the song relies on."""

    def _build_pattern_context(self) -> PatternContext:
        patterns = [Pattern.empty(4, name=f"p{index}") for index in range(3)]
        collection: IndexedCollection[Pattern] = IndexedCollection(patterns)
        channel = Channel(
            generator=GeneratorName.PULSE1,
            patterns=collection,
            order=[pattern.id for pattern in patterns],
        )
        return PatternContext(channel=channel, patterns=patterns)

    def test_patterns_survive_reorder_and_edit(self) -> None:
        def reorder(context: PatternContext) -> None:
            moved = context.channel.patterns.pop(0)
            context.channel.patterns.append(moved)
            assert context.channel.patterns[-1] is context.patterns[0]
            assert context.channel.ordered_patterns() == context.patterns

        def edit_in_place(context: PatternContext) -> None:
            target = context.patterns[1]
            original_hash = hash(target)
            target.name = "edited"
            target.rows = target.rows[:1]
            assert hash(target) == original_hash
            assert context.channel.pattern(target.id) is target
            assert context.channel.pattern(target.id).name == "edited"

        scenario = BaseTestScenario(
            label="patterns_reorder_and_edit",
            build=self._build_pattern_context,
            steps=[
                ScenarioStep(label="reorder", action=reorder),
                ScenarioStep(label="edit_in_place", action=edit_in_place),
            ],
        )
        scenario.run()

    def _build_instrument_context(self) -> InstrumentContext:
        project = Project.create()
        first = _instrument("first")
        second = _instrument("second")
        project.instruments.extend([first, second])
        subinstrument = SubInstrument(instrument_id=first.id, generator_name=GeneratorName.PULSE1)
        return InstrumentContext(project=project, instrument=first, subinstrument=subinstrument)

    def test_subinstrument_survives_instrument_reorder(self) -> None:
        def check_before(context: InstrumentContext) -> None:
            assert context.project.instruments.index(context.instrument) == 0
            context.resolved["before"] = context.project.instrument(context.subinstrument.instrument_id)

        def reorder(context: InstrumentContext) -> None:
            moved = context.project.instruments.pop(0)
            context.project.instruments.append(moved)
            assert context.project.instruments.index(context.instrument) == 1

        def check_after(context: InstrumentContext) -> None:
            resolved = context.project.instrument(context.subinstrument.instrument_id)
            assert resolved is context.instrument
            assert resolved is context.resolved["before"]

        scenario = BaseTestScenario(
            label="subinstrument_reference_integrity",
            build=self._build_instrument_context,
            steps=[
                ScenarioStep(label="check_before", action=check_before),
                ScenarioStep(label="reorder", action=reorder),
                ScenarioStep(label="check_after", action=check_after),
            ],
        )
        scenario.run()
