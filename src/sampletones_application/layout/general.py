from typing import Tuple, TypeAlias

from pydantic import BaseModel

from sampletones_application.layout.glyphs import GlyphLayout
from sampletones_application.utils.color import RGBA

Padding: TypeAlias = Tuple[int, int]


class WindowLayout(BaseModel, extra="forbid", frozen=True):
    width: int
    height: int
    position_x: int
    position_y: int
    fullscreen: bool


class ColumnLayout(BaseModel, extra="forbid", frozen=True):
    """Dimensions of one fixed column in a tab layout; a ``height`` of -1 fills the tab vertically."""

    width: int
    height: int


class ColumnsLayout(BaseModel, extra="forbid", frozen=True):
    """The fixed-column geometry the tab coordinators lay their panels out on.

    ``side`` sizes the uniform left column — the browser, library, or explorer —
    that every tab carries, so the side panel stays the same size across tabs. Each
    ``*_right`` column sizes one tab's right column, whose width follows the content
    it holds.
    """

    side: ColumnLayout
    instructions_right: ColumnLayout
    reconstructions_right: ColumnLayout
    sequencer_right: ColumnLayout


class StatusBarLayout(BaseModel, extra="forbid", frozen=True):
    height: int
    reserved_margin: int
    frame_rounding: int
    frame_padding: Padding


class DialogSizeLayout(BaseModel, extra="forbid", frozen=True):
    width: int
    height: int


class DialogSizeNoWidth(BaseModel, extra="forbid", frozen=True):
    height: int


class DialogSizeNoHeight(BaseModel, extra="forbid", frozen=True):
    width: int
    height: int


class DialogsLayout(BaseModel, extra="forbid", frozen=True):
    default: DialogSizeLayout
    error: DialogSizeLayout
    recovery: DialogSizeLayout
    file: DialogSizeLayout
    confirmation: DialogSizeNoWidth
    text_input: DialogSizeNoWidth
    traceback: DialogSizeLayout


class InputsLayout(BaseModel, extra="forbid", frozen=True):
    default_width: int
    search_width: int
    label_width: int


class ButtonsLayout(BaseModel, extra="forbid", frozen=True):
    copy_width: int
    search_width: int
    int_width: int
    frame_rounding: int
    frame_padding: Padding


class TablesLayout(BaseModel, extra="forbid", frozen=True):
    label_width: int
    cell_padding: Padding
    frame_rounding: int


class PitchStepperLayout(BaseModel, extra="forbid", frozen=True):
    label_width: int
    value_width: int
    button_column_width: int
    button_width: int
    hold_delay: float
    commit_delay: int


class MenuLayout(BaseModel, extra="forbid", frozen=True):
    fps_text_offset: int


class CaretLayout(BaseModel, extra="forbid", frozen=True):
    offset: int
    width_padding: int
    fill: RGBA
    border: RGBA


class SectionHeaderLayout(BaseModel, extra="forbid", frozen=True):
    glyph: GlyphLayout


class CollapseLayout(BaseModel, extra="forbid", frozen=True):
    """Geometry a collapsed card shrinks to: the header bar for a vertical card, the rail for a docked column."""

    header_bar_height: int
    rail_width: int


class TextColors(BaseModel, extra="forbid", frozen=True):
    white: RGBA
    default: RGBA
    disabled: RGBA
    error: RGBA
    highlight: RGBA
    traceback: RGBA


class FileColors(BaseModel, extra="forbid", frozen=True):
    wave: RGBA
    library: RGBA
    reconstruction: RGBA
    directory_not_expanded: RGBA


class FavoriteColors(BaseModel, extra="forbid", frozen=True):
    default: RGBA
    child: RGBA


class ButtonColors(BaseModel, extra="forbid", frozen=True):
    default: RGBA
    active: RGBA
    hovered: RGBA
    light: RGBA


class BackgroundColors(BaseModel, extra="forbid", frozen=True):
    default: RGBA
    dark: RGBA
    light: RGBA
    menu: RGBA
    input_invalid: RGBA


class TableColors(BaseModel, extra="forbid", frozen=True):
    header: RGBA
    row: RGBA
    row_alternative: RGBA
    border: RGBA
    label: RGBA
    value: RGBA


class PathColors(BaseModel, extra="forbid", frozen=True):
    default: RGBA
    hover: RGBA


class HeaderColors(BaseModel, extra="forbid", frozen=True):
    library: RGBA
    reconstruction: RGBA


class FeatureColors(BaseModel, extra="forbid", frozen=True):
    """The per-feature palette shared by every view that names a feature.

    The details tab's bar plots and the history panel's detail segments both
    paint from this block, so a feature keeps one colour across the
    application.
    """

    volume: RGBA
    arpeggio: RGBA
    pitch: RGBA
    duty_cycle: RGBA


class GeneralColors(BaseModel, extra="forbid", frozen=True):
    text: TextColors
    files: FileColors
    favorites: FavoriteColors
    buttons: ButtonColors
    backgrounds: BackgroundColors
    tables: TableColors
    paths: PathColors
    headers: HeaderColors
    features: FeatureColors


class GeneralLayout(BaseModel, extra="forbid", frozen=True):
    window: WindowLayout
    panel_gap: int
    columns: ColumnsLayout
    status_bar: StatusBarLayout
    dialogs: DialogsLayout
    inputs: InputsLayout
    buttons: ButtonsLayout
    tables: TablesLayout
    pitch_stepper: PitchStepperLayout
    menu: MenuLayout
    caret: CaretLayout
    section_header: SectionHeaderLayout
    collapse: CollapseLayout
    colors: GeneralColors
