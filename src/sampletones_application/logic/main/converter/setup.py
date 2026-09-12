from pathlib import Path
from typing import Optional, Tuple

from sampletones_application.logic.main.converter.state import ConverterState
from sampletones_application.logic.main.sources.derive import (
    ConversionSetup,
    derive_conversion_setup,
)
from sampletones_core.reconstructions.converter import (
    BatchConversion,
    BatchEntry,
    ConversionPlan,
    GroupConversion,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig


def conversion_setup(state: ConverterState) -> ConversionSetup:
    """The recordings and the stems setup a mix converts under, carrying the channel cap."""
    settings = state.settings
    return derive_conversion_setup(
        state.gathering.sources,
        state.gathering.levels,
        channel_cap=settings.effective_channel_cap,
        hierarchy_mode=settings.hierarchy_mode,
    )


def playing_sources(state: ConverterState) -> Tuple[Path, ...]:
    """The recordings that take part, in the order the run reaches them."""
    if state.settings.mixes:
        return conversion_setup(state).sources

    return tuple(entry.source for entry in batch_entries(state))


def batch_entries(state: ConverterState) -> Tuple[BatchEntry, ...]:
    """One entry per gathered recording still holding a channel.

    Each carries a setup of its own, so what a reader settled on a row is what that recording's
    reconstruction records. The folder a recording was gathered from decides where it is written,
    which is what makes a run over a folder mirror that folder's tree.
    """
    settings = state.settings
    gathering = state.gathering
    entries = []
    for recording in gathering.sources.recordings:
        if not recording.settings.channels:
            continue

        entries.append(
            BatchEntry(
                source=recording.path,
                stems=StemsConfig.single_entry(
                    recording.settings.channels,
                    recording.settings.bends,
                    channel_cap=settings.effective_channel_cap,
                ),
                base_directory=gathering.folder_root_of(recording.path),
            )
        )

    return tuple(entries)


def conversion_plan(state: ConverterState) -> Optional[ConversionPlan]:
    """What a request amounts to: one reconstruction from the recordings gathered, or one apiece.

    A run with nobody taking part names no plan, which is what a converter aimed at nothing is.
    """
    if state.settings.mixes:
        setup = conversion_setup(state)
        return GroupConversion(sources=setup.sources, stems=setup.stems) if setup.sources else None

    entries = batch_entries(state)
    return BatchConversion(entries=entries) if entries else None
