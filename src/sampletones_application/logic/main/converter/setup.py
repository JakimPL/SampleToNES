from pathlib import Path
from typing import Optional, Tuple

from sampletones_application.logic.main.converter.state import ConverterState
from sampletones_application.logic.main.sources.derive import (
    ConversionSetup,
    derive_conversion_setup,
)
from sampletones_core.reconstructions.converter import (
    ConversionPlan,
    DirectoryConversion,
    GroupConversion,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig


def conversion_setup(state: ConverterState) -> ConversionSetup:
    """The recordings and the stems setup a run converts under, carrying the channel cap.

    A mix is what the gathered levels amount to; a single conversion is one stem over every
    enabled channel, which is the classic run's shape.
    """
    settings = state.settings
    if settings.stems_mode:
        return derive_conversion_setup(
            state.gathering.sources,
            state.gathering.levels,
            settings.enabled_channels,
            channel_cap=settings.effective_channel_cap,
            hierarchy_mode=settings.hierarchy_mode,
        )

    joining = settings.joining
    return ConversionSetup(
        sources=(),
        stems=StemsConfig.single_entry(
            joining.channels,
            joining.bends,
            channel_cap=settings.effective_channel_cap,
        ),
    )


def playing_sources(state: ConverterState) -> Tuple[Path, ...]:
    """The recordings that take part, in the order the conversion mixes them."""
    return conversion_setup(state).sources


def conversion_plan(state: ConverterState) -> Optional[ConversionPlan]:
    """What a request amounts to: one reconstruction from the recordings gathered or the file
    picked, or one per audio file the picked directory holds.

    A mix converts the recordings gathered for it, so it names a plan whichever path the reader
    picked. A single conversion needs one, and a converter aimed at nothing has nothing to run.
    """
    setup = conversion_setup(state)
    if state.settings.stems_mode:
        return GroupConversion(sources=setup.sources, stems=setup.stems)

    input_path = state.destination.input_path
    if input_path is None:
        return None

    if state.destination.is_file:
        return GroupConversion(sources=(input_path,), stems=setup.stems)

    return DirectoryConversion(directory=input_path, stems=setup.stems)
