from typing import Dict, Final, Optional, Tuple

from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.grid import SequencerCellViewModel
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.utils.display import display_id, display_transpose, display_volume
from sampletones_shared.constants.symbols import UNDERSCORE

CellValues = Dict[Tuple[int, Optional[GeneratorName], SubColumn], str]

_DEFAULT_LABELS: Final[Dict[SubColumn, str]] = {
    SubColumn.INSTRUMENT: display_id(None),
    SubColumn.TRANSPOSE: display_transpose(None),
    SubColumn.VOLUME: display_volume(None),
}


def default_label(subcolumn: SubColumn) -> str:
    return _DEFAULT_LABELS[subcolumn]


def cell_display(cell_view_model: SequencerCellViewModel, subcolumn: SubColumn) -> str:
    """Extract the pre-formatted display string for one subcolumn from a cell view model."""
    match subcolumn:
        case SubColumn.INSTRUMENT:
            return cell_view_model.instrument
        case SubColumn.TRANSPOSE:
            return cell_view_model.transpose
        case SubColumn.VOLUME:
            return cell_view_model.volume


def format_committed(subcolumn: SubColumn, value: Optional[int]) -> str:
    """Format an integer value as the display string stored in the optimistic cell cache."""
    match subcolumn:
        case SubColumn.INSTRUMENT:
            return display_id(value)
        case SubColumn.TRANSPOSE:
            return display_transpose(value)
        case SubColumn.VOLUME:
            return display_volume(value)


def subcolumn_label(
    row: int,
    generator: Optional[GeneratorName],
    subcolumn: SubColumn,
    *,
    cursor: Optional[TrackerCursor],
    pending: str,
    cell_values: CellValues,
) -> str:
    is_active = (
        cursor is not None and cursor.row == row and cursor.generator == generator and cursor.subcolumn == subcolumn
    )
    stored = cell_values.get((row, generator, subcolumn), _DEFAULT_LABELS[subcolumn])
    if is_active:
        width = len(_DEFAULT_LABELS[subcolumn])
        if pending:
            return pending + UNDERSCORE * (width - len(pending))

        return UNDERSCORE * width

    return stored
