from pathlib import Path
from typing import Dict, Final, List, Optional, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName, ordered_channels
from sampletones_shared.paths.extensions import EXT_FILE_FLAC
from sampletones_shared.utils.system.paths import get_filename
from sampletones_tools.calibration.layout import RECORDINGS_DIRECTORY, combination_name
from sampletones_tools.calibration.renders import RenderRecord, item_directory, variant_directory

from .clips import ClipStore
from .model import BoardCell, BoardChannel, BoardGroup, BoardPage, BoardRow
from .palette import channel_token
from .reading import RunReading

NO_CLIP: Final[str] = ""


def compose_page(
    runs: Sequence[RunReading],
    store: ClipStore,
    title: str,
) -> BoardPage:
    """
    Assemble everything a page draws from the runs it reports.

    One run is read across its variants, which become the columns of a single table. Several runs
    are read against each other, so each variant becomes a table of its own and the runs stand as
    its columns — the comparison a person makes when they run the same settings on two versions.

    Args:
        runs: The runs the page reports, in the order the page holds them.
        store: Where the page finds each clip it plays.
        title: The heading the page carries.

    Returns:
        The page, ready to be written.

    Raises:
        ValueError: If no run is given.
    """
    if not runs:
        raise ValueError("A page reports at least one run")

    groups = _variant_groups(runs, store) if len(runs) > 1 else _column_group(runs[0], store)
    return BoardPage(
        title=title,
        referee=runs[0].referee,
        colors={channel.value: channel_token(channel.value) for channel in ChannelName},
        groups=groups,
    )


def _column_group(run: RunReading, store: ClipStore) -> Tuple[BoardGroup, ...]:
    """One table whose columns are the configurations the run measured."""
    variants = run.variants
    items = [(item, run) for item in _items(run)]
    rows = _rows(store, items, [(run, variant) for variant in variants])
    return (BoardGroup(name=run.label, columns=variants, rows=rows),)


def _variant_groups(runs: Sequence[RunReading], store: ClipStore) -> Tuple[BoardGroup, ...]:
    """One table per configuration, whose columns are the runs that measured it."""
    groups: List[BoardGroup] = []
    for variant in _shared_variants(runs):
        holders = [run for run in runs if variant in run.variants]
        rows = _rows(store, _shared_items(holders), [(run, variant) for run in holders])
        groups.append(BoardGroup(name=variant, columns=tuple(run.label for run in holders), rows=rows))

    return tuple(groups)


def _rows(
    store: ClipStore,
    items: Sequence[Tuple[str, RunReading]],
    places: Sequence[Tuple[RunReading, str]],
) -> Tuple[BoardRow, ...]:
    """A row per item every column holds a render of, so each row reads across the whole table."""
    rows = [_row(store, item, recording_run, places) for item, recording_run in items]
    return tuple(row for row in rows if row is not None)


def _row(
    store: ClipStore,
    item: str,
    recording_run: RunReading,
    places: Sequence[Tuple[RunReading, str]],
) -> Optional[BoardRow]:
    records = [(run, _record(run, item, variant)) for run, variant in places]
    held = [(run, record) for run, record in records if record is not None]
    if len(held) != len(records):
        return None

    return BoardRow(
        item=item,
        category=held[0][1].category,
        recording=store.href(recording_run, _recording_path(recording_run, item)),
        cells=tuple(_cell(run, store, record) for run, record in held),
    )


def _cell(run: RunReading, store: ClipStore, record: RenderRecord) -> BoardCell:
    channels = _sounding_channels(record)
    return BoardCell(
        render=store.href(run, _render_path(run, record)),
        score=run.score(record),
        silence=run.silence(record),
        channels=tuple(_channel(run, store, record, channel, channels) for channel in channels),
    )


def _channel(
    run: RunReading,
    store: ClipStore,
    record: RenderRecord,
    channel: ChannelName,
    channels: Sequence[ChannelName],
) -> BoardChannel:
    others = [other for other in channels if other != channel]
    return BoardChannel(
        name=channel.value,
        timeline=record.timelines[channel.value],
        solo=_part(run, store, record, [channel]) if others else NO_CLIP,
        mute=_part(run, store, record, others),
    )


def _part(
    run: RunReading,
    store: ClipStore,
    record: RenderRecord,
    channels: Sequence[ChannelName],
) -> str:
    if not channels:
        return NO_CLIP

    directory = item_directory(run.directory, record.variant, record.item)
    return store.href(run, directory / get_filename(combination_name(channels), EXT_FILE_FLAC))


def _render_path(run: RunReading, record: RenderRecord) -> Path:
    return variant_directory(run.directory, record.variant) / get_filename(record.item, EXT_FILE_FLAC)


def _recording_path(run: RunReading, item: str) -> Path:
    return run.directory / RECORDINGS_DIRECTORY / get_filename(item, EXT_FILE_FLAC)


def _sounding_channels(record: RenderRecord) -> List[ChannelName]:
    return ordered_channels({ChannelName(name) for name in record.timelines})


def _record(run: RunReading, item: str, variant: str) -> Optional[RenderRecord]:
    for record in run.records:
        if record.item == item and record.variant == variant:
            return record

    return None


def _items(run: RunReading) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(record.item for record in run.records))


def _shared_variants(runs: Sequence[RunReading]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(variant for run in runs for variant in run.variants))


def _shared_items(runs: Sequence[RunReading]) -> List[Tuple[str, RunReading]]:
    seen: Dict[str, RunReading] = {}
    for run in runs:
        for item in _items(run):
            seen.setdefault(item, run)

    return list(seen.items())
