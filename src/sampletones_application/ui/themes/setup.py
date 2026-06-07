from sampletones_application.layout import LayoutConfig
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.themes.converter import ConverterTheme
from sampletones_application.ui.themes.default import DefaultTheme
from sampletones_application.ui.themes.fps import FPSTimerTheme
from sampletones_application.ui.themes.graphs.indicator import IndicatorGraphTheme
from sampletones_application.ui.themes.graphs.overlay import OverlayGraphTheme
from sampletones_application.ui.themes.graphs.zero import ZeroLineGraphTheme
from sampletones_application.ui.themes.input import InvalidInputTheme
from sampletones_application.ui.themes.nodes.favorite import FavoriteChildNodeTheme, FavoriteNodeTheme
from sampletones_application.ui.themes.nodes.file import (
    LibraryFileNodeTheme,
    NoContentFileNodeTheme,
    NotExpandedDirectoryNodeTheme,
    ReconstructionFileNodeTheme,
    WaveFileNodeTheme,
)
from sampletones_application.ui.themes.nodes.library import (
    LibraryGeneratorNodeTheme,
    LibraryGroupNodeTheme,
    LibraryInstructionNodeTheme,
    LibraryLibraryNodeTheme,
)
from sampletones_application.ui.themes.status import StatusBarTheme
from sampletones_application.ui.themes.tables.initial_pitch import InitialPitchTableTheme
from sampletones_application.ui.themes.tables.instruments_row import InstrumentsRowTheme
from sampletones_application.ui.themes.tables.pattern import PatternTableTheme
from sampletones_application.ui.themes.tables.table import TableTheme
from sampletones_application.ui.themes.trace import TracebackTheme


def setup_themes(layout: LayoutConfig) -> None:
    general = layout.general
    graphs = layout.graphs
    instructions = layout.instructions
    reconstructions = layout.reconstructions
    sequencer = layout.sequencer

    FontRegistry.setup(general.fonts)

    DefaultTheme.setup(general)
    StatusBarTheme.setup(general)
    FPSTimerTheme.setup(general)
    ConverterTheme.setup(general)
    InvalidInputTheme.setup(general)
    TracebackTheme.setup(general)
    TableTheme.setup(general)

    FavoriteNodeTheme.setup(general)
    FavoriteChildNodeTheme.setup(general)
    NoContentFileNodeTheme.setup(general)
    ReconstructionFileNodeTheme.setup(general)
    LibraryFileNodeTheme.setup(general)
    WaveFileNodeTheme.setup(general)
    NotExpandedDirectoryNodeTheme.setup(general)

    LibraryLibraryNodeTheme.setup(instructions)
    LibraryGeneratorNodeTheme.setup(instructions)
    LibraryGroupNodeTheme.setup(instructions)
    LibraryInstructionNodeTheme.setup(instructions)

    IndicatorGraphTheme.setup(graphs)
    OverlayGraphTheme.setup(graphs)
    ZeroLineGraphTheme.setup(graphs)

    InitialPitchTableTheme.setup(reconstructions)
    InstrumentsRowTheme.setup(sequencer)
    PatternTableTheme.setup(general, sequencer)
