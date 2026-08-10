from typing import Any, Dict, List, Mapping, Optional

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import load_yaml

RowSpec = Dict[str, Any]


def _order(
    order_specs: List[Dict[str, int]],
) -> List[Dict[GeneratorName, Optional[int]]]:
    frames: List[Dict[GeneratorName, Optional[int]]] = []
    for spec in order_specs:
        frames.append({generator: spec.get(generator.value) for generator in GeneratorName.items()})

    return frames


def _row(spec: RowSpec, generator: GeneratorName, samples_by_name: Mapping[str, Sample]) -> Row:
    transpose = spec.get("transpose")
    volume = spec.get("volume")

    if spec.get("off"):
        return Row(command=NoteOff(), volume=volume)

    sample_name = spec.get("sample")
    if sample_name is None:
        return Row(transpose=transpose, volume=volume)

    sample = samples_by_name[sample_name]
    if generator not in sample.reconstruction.instructions:
        raise ValueError(f"Sample '{sample_name}' has no '{generator.value}' slice for the {generator.value} channel")

    command = Instrument(sample_id=sample.id, generator_name=generator)
    return Row(command=command, transpose=transpose, volume=volume)


def _pattern(
    row_specs: List[RowSpec],
    rows_per_pattern: int,
    generator: GeneratorName,
    samples_by_name: Mapping[str, Sample],
) -> Pattern:
    rows = [Row() for _ in range(rows_per_pattern)]
    for spec in row_specs:
        rows[spec["row"]] = _row(spec, generator, samples_by_name)

    return Pattern(rows=rows)


def _channels(
    channels_spec: Dict[str, Dict[str, Any]],
    rows_per_pattern: int,
    samples_by_name: Mapping[str, Sample],
) -> Dict[GeneratorName, Channel]:
    channels: Dict[GeneratorName, Channel] = {}
    for name, spec in channels_spec.items():
        generator = GeneratorName(name)
        patterns = {
            int(index): _pattern(
                row_specs,
                rows_per_pattern,
                generator,
                samples_by_name,
            )
            for index, row_specs in spec["patterns"].items()
        }
        channels[generator] = Channel(
            generator=generator,
            patterns=patterns,
        )

    for generator in GeneratorName.items():
        channels.setdefault(generator, Channel(generator=generator, patterns={}))

    return channels


def load_song(path: Pathlike, samples_by_name: Mapping[str, Sample]) -> Song:
    document = load_yaml(path)
    rows_per_pattern = document["rows_per_pattern"]
    return Song(
        rows_per_pattern=rows_per_pattern,
        order=_order(document["order"]),
        channels=_channels(document["channels"], rows_per_pattern, samples_by_name),
    )
