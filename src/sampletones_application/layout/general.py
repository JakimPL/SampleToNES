from typing import Tuple, TypeAlias

from pydantic import BaseModel

from sampletones_application.layout.glyphs import GlyphLayout
from sampletones_application.utils.palette import PaletteColor

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
    fill: PaletteColor
    border: PaletteColor


class SectionHeaderLayout(BaseModel, extra="forbid", frozen=True):
    glyph: GlyphLayout
    chevron_offset: int


class CollapseLayout(BaseModel, extra="forbid", frozen=True):
    """Geometry a collapsed card shrinks to: the header bar for a vertical card, the rail for a docked column."""

    header_bar_height: int
    rail_width: int
    rail_title_gap: int


class TextColors(BaseModel, extra="forbid", frozen=True):
    white: PaletteColor
    default: PaletteColor
    disabled: PaletteColor
    error: PaletteColor
    highlight: PaletteColor
    traceback: PaletteColor


class FileColors(BaseModel, extra="forbid", frozen=True):
    wave: PaletteColor
    library: PaletteColor
    reconstruction: PaletteColor
    directory_not_expanded: PaletteColor


class FavoriteColors(BaseModel, extra="forbid", frozen=True):
    default: PaletteColor
    child: PaletteColor


class ButtonColors(BaseModel, extra="forbid", frozen=True):
    default: PaletteColor
    active: PaletteColor
    hovered: PaletteColor
    light: PaletteColor


class BackgroundColors(BaseModel, extra="forbid", frozen=True):
    default: PaletteColor
    dark: PaletteColor
    light: PaletteColor
    menu: PaletteColor
    input_invalid: PaletteColor


class TableColors(BaseModel, extra="forbid", frozen=True):
    header: PaletteColor
    row: PaletteColor
    row_alternative: PaletteColor
    border: PaletteColor
    label: PaletteColor
    value: PaletteColor


class PathColors(BaseModel, extra="forbid", frozen=True):
    default: PaletteColor
    hover: PaletteColor


class HeaderColors(BaseModel, extra="forbid", frozen=True):
    library: PaletteColor
    reconstruction: PaletteColor


class FeatureColors(BaseModel, extra="forbid", frozen=True):
    """The per-feature palette shared by every view that names a feature.

    The details tab's bar plots and the history panel's detail segments both
    paint from this block, so a feature keeps one colour across the
    application.
    """

    volume: PaletteColor
    arpeggio: PaletteColor
    pitch: PaletteColor
    duty_cycle: PaletteColor


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
