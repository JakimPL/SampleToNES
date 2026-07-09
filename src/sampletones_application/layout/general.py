from pydantic import BaseModel

from sampletones_application.layout.glyphs import GlyphLayout
from sampletones_application.utils.color import RGBA

Padding = tuple[int, int]


class WindowLayout(BaseModel, frozen=True):
    width: int
    height: int
    position_x: int
    position_y: int
    fullscreen: bool


class ColumnLayout(BaseModel, frozen=True):
    """Dimensions of one fixed column in a tab layout; a ``height`` of -1 fills the tab vertically."""

    width: int
    height: int


class ColumnsLayout(BaseModel, frozen=True):
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


class StatusBarLayout(BaseModel, frozen=True):
    height: int
    reserved_margin: int
    frame_rounding: int
    frame_padding: Padding


class FontsLayout(BaseModel, frozen=True):
    size: int
    size_small: int
    size_large: int
    scale: int


class DialogSizeLayout(BaseModel, frozen=True):
    width: int
    height: int


class DialogSizeNoWidth(BaseModel, frozen=True):
    height: int


class DialogSizeNoHeight(BaseModel, frozen=True):
    width: int
    height: int


class DialogsLayout(BaseModel, frozen=True):
    default: DialogSizeLayout
    error: DialogSizeLayout
    recovery: DialogSizeLayout
    file: DialogSizeLayout
    confirmation: DialogSizeNoWidth
    text_input: DialogSizeNoWidth
    traceback: DialogSizeLayout


class InputsLayout(BaseModel, frozen=True):
    default_width: int
    search_width: int


class ButtonsLayout(BaseModel, frozen=True):
    copy_width: int
    search_width: int
    int_width: int
    frame_rounding: int
    frame_padding: Padding


class TablesLayout(BaseModel, frozen=True):
    label_width: int
    cell_padding: Padding
    frame_rounding: int


class PitchStepperLayout(BaseModel, frozen=True):
    label_width: int
    value_width: int
    button_column_width: int
    button_width: int
    hold_delay: float
    commit_delay: int


class MenuLayout(BaseModel, frozen=True):
    fps_text_offset: int


class CaretLayout(BaseModel, frozen=True):
    offset: int
    width_padding: int
    fill: RGBA
    border: RGBA


class SectionHeaderLayout(BaseModel, frozen=True):
    glyph: GlyphLayout


class TextColors(BaseModel, frozen=True):
    white: RGBA
    default: RGBA
    disabled: RGBA
    error: RGBA
    highlight: RGBA
    traceback: RGBA


class FileColors(BaseModel, frozen=True):
    wave: RGBA
    library: RGBA
    reconstruction: RGBA
    directory_not_expanded: RGBA


class FavoriteColors(BaseModel, frozen=True):
    default: RGBA
    child: RGBA


class ButtonColors(BaseModel, frozen=True):
    default: RGBA
    active: RGBA
    hovered: RGBA
    light: RGBA


class BackgroundColors(BaseModel, frozen=True):
    default: RGBA
    dark: RGBA
    light: RGBA
    menu: RGBA
    input_invalid: RGBA


class TableColors(BaseModel, frozen=True):
    header: RGBA
    row: RGBA
    row_alternative: RGBA
    border: RGBA
    label: RGBA
    value: RGBA


class PathColors(BaseModel, frozen=True):
    default: RGBA
    hover: RGBA


class HeaderColors(BaseModel, frozen=True):
    library: RGBA
    reconstruction: RGBA


class FeatureColors(BaseModel, frozen=True):
    """The per-feature palette shared by every view that names a feature.

    The details tab's bar plots and the history panel's detail segments both
    paint from this block, so a feature keeps one colour across the
    application.
    """

    volume: RGBA
    arpeggio: RGBA
    pitch: RGBA
    duty_cycle: RGBA


class GeneralColors(BaseModel, frozen=True):
    text: TextColors
    files: FileColors
    favorites: FavoriteColors
    buttons: ButtonColors
    backgrounds: BackgroundColors
    tables: TableColors
    paths: PathColors
    headers: HeaderColors
    features: FeatureColors


class GeneralLayout(BaseModel, frozen=True):
    window: WindowLayout
    panel_gap: int
    columns: ColumnsLayout
    status_bar: StatusBarLayout
    fonts: FontsLayout
    dialogs: DialogsLayout
    inputs: InputsLayout
    buttons: ButtonsLayout
    tables: TablesLayout
    pitch_stepper: PitchStepperLayout
    menu: MenuLayout
    caret: CaretLayout
    section_header: SectionHeaderLayout
    colors: GeneralColors
