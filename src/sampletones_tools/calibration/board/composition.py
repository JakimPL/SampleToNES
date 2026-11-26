from pathlib import Path
from typing import Dict, Final, List, Optional, Sequence, Set, Tuple

from sampletones_core.constants.enums import ChannelName, ordered_channels
from sampletones_shared.paths.extensions import EXT_FILE_FLAC
from sampletones_shared.utils.system.paths import get_filename
from sampletones_tools.calibration.config.level import VariantLevel
from sampletones_tools.calibration.layout import ORACLE_LABEL, combination_name
from sampletones_tools.calibration.oracle.reading import HIGHEST_READING, LOWEST_READING
from sampletones_tools.calibration.renders import RenderRecord, item_directory, recording_path, variant_directory
from sampletones_tools.calibration.variants import LABEL_SEPARATOR
from sampletones_tools.web.roles.table import channel_role

from .clips import ClipStore
from .headings import heading_column, oracle_column, shared_words
from .model import (
    BoardCell,
    BoardChannel,
    BoardFamily,
    BoardGlyphs,
    BoardGroup,
    BoardPage,
    BoardRecording,
    BoardRow,
)
from .reading import RunReading

NO_CLIP: Final[str] = ""


def compose_page(
    runs: Sequence[RunReading],
    store: ClipStore,
    title: str,
    glyphs: BoardGlyphs,
) -> BoardPage:
    """
    Assemble everything a page draws from the runs it reports.

    One run is read across its variants, which become the columns of a single table, the oracle's
    first where the run read it. Several runs are read against each other, so each variant becomes a
    table of its own and the runs stand as its columns — the comparison a person makes when they run
    the same settings on two versions.

    Args:
        runs: The runs the page reports, in the order the page holds them.
        store: Where the page finds each clip it plays.
        title: The heading the page carries.
        glyphs: The application's glyphs the page draws with.

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
        glyphs=glyphs,
        colors={channel.value: channel_role(channel.value) for channel in ChannelName},
        groups=groups,
    )


def _column_group(run: RunReading, store: ClipStore) -> Tuple[BoardGroup, ...]:
    """One table whose columns are the configurations the run measured, after the oracle where the run read it.

    The oracle reads only the sounds written as NES frames, so a row of another sound leaves its
    oracle cell empty.
    """
    variants = run.variants
    oracle = run if run.holds_oracle else None
    rows = _rows(store, _items(run), [(run, variant) for variant in variants], oracle)
    return (_group(run.label, variants, rows, oracle=oracle is not None),)


def _variant_groups(runs: Sequence[RunReading], store: ClipStore) -> Tuple[BoardGroup, ...]:
    """One table per configuration, whose columns are the runs that measured it."""
    groups: List[BoardGroup] = []
    for variant in _shared_variants(runs):
        holders = [run for run in runs if variant in run.variants]
        rows = _rows(store, _shared_items(holders), [(run, variant) for run in holders], None)
        groups.append(_group(variant, [run.label for run in holders], rows, oracle=False))

    return tuple(groups)


def _group(name: str, columns: Sequence[str], rows: Tuple[BoardRow, ...], *, oracle: bool) -> BoardGroup:
    """A tab of these columns and rows, each heading naming what its column adds to the words they share.

    The oracle's column, where the group holds it, stands first and outside the shared words.
    """
    prefix = shared_words(columns)
    headed = tuple(heading_column(column, prefix) for column in columns)
    return BoardGroup(
        name=name,
        prefix=LABEL_SEPARATOR.join(prefix),
        columns=(oracle_column(), *headed) if oracle else headed,
        families=_families(rows),
        rows=rows,
    )


def _families(rows: Sequence[BoardRow]) -> Tuple[BoardFamily, ...]:
    """A family per name the rows carry, in the order they first name it, with every channel its cells sound."""
    sounding: Dict[str, Set[ChannelName]] = {}
    for row in rows:
        channels = sounding.setdefault(row.family, set())
        channels.update(
            ChannelName(channel.name) for cell in row.cells if cell is not None for channel in cell.channels
        )

    return tuple(
        BoardFamily(name=family, channels=tuple(channel.value for channel in ordered_channels(channels)))
        for family, channels in sounding.items()
    )


def _rows(
    store: ClipStore,
    items: Sequence[str],
    places: Sequence[Tuple[RunReading, str]],
    oracle: Optional[RunReading],
) -> Tuple[BoardRow, ...]:
    """A row per item every column holds a render of, so each row reads across the whole table.

    Where ``oracle`` names a run, each row leads with that run's oracle cell of the item, empty where
    the run read no oracle of it.
    """
    rows = [_row(store, item, places, oracle) for item in items]
    return tuple(row for row in rows if row is not None)


def _row(
    store: ClipStore,
    item: str,
    places: Sequence[Tuple[RunReading, str]],
    oracle: Optional[RunReading],
) -> Optional[BoardRow]:
    records = [(run, _record(run, item, variant)) for run, variant in places]
    held = [(run, record) for run, record in records if record is not None]
    if len(held) != len(records):
        return None

    cells: Tuple[Optional[BoardCell], ...] = tuple(_cell(run, store, record) for run, record in held)
    if oracle is not None:
        read = _record(oracle, item, ORACLE_LABEL)
        cells = (None if read is None else _cell(oracle, store, read), *cells)
        held = [(oracle, read), *held] if read is not None else held

    return BoardRow(
        item=item,
        family=held[0][1].family,
        category=held[0][1].category,
        recordings=_recordings(store, item, held),
        cells=cells,
    )


def _recordings(
    store: ClipStore,
    item: str,
    held: Sequence[Tuple[RunReading, RenderRecord]],
) -> Tuple[BoardRecording, ...]:
    """The recording at each level the cells were matched at, each from the run of the first cell at that level."""
    first: Dict[VariantLevel, RunReading] = {}
    for run, record in held:
        first.setdefault(record.level, run)

    return tuple(
        BoardRecording(level=level.value, clip=store.href(run, recording_path(run.directory, level, item)))
        for level, run in first.items()
    )


def _cell(run: RunReading, store: ClipStore, record: RenderRecord) -> BoardCell:
    channels = _sounding_channels(record)
    return BoardCell(
        render=store.href(run, _render_path(run, record)),
        score=run.score(record),
        silence=run.silence(record),
        channels=tuple(_channel(run, store, record, channel, channels) for channel in channels),
        spread=_spread(run, record),
    )


def _spread(run: RunReading, record: RenderRecord) -> Optional[Tuple[float, float]]:
    """The lowest and highest headline score of the renders a record's score is the mean of, where it keeps them."""
    readings = record.judgments[run.referee]
    if LOWEST_READING not in readings or HIGHEST_READING not in readings:
        return None

    return readings[LOWEST_READING], readings[HIGHEST_READING]


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


def _sounding_channels(record: RenderRecord) -> List[ChannelName]:
    return ordered_channels({ChannelName(name) for name in record.timelines})


def _record(run: RunReading, item: str, variant: str) -> Optional[RenderRecord]:
    for record in run.records:
        if record.item == item and record.variant == variant:
            return record

    return None


def _items(run: RunReading) -> Tuple[str, ...]:
    """The items the run lists, which are the ones it wrote audio for."""
    return tuple(dict.fromkeys(record.item for record in run.records if record.listed))


def _shared_variants(runs: Sequence[RunReading]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(variant for run in runs for variant in run.variants))


def _shared_items(runs: Sequence[RunReading]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(item for run in runs for item in _items(run)))
