from pathlib import Path
from typing import Final, List

from pydantic import BaseModel, ConfigDict, Field

from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from sampletones_tools.web.design import ApplicationDesign
from sampletones_tools.web.writer import write_layout

from .assets import write_assets
from .clips import clip_store
from .composition import compose_page
from .data import data_script
from .layout import DATA_FILE, PAGE_DIRECTORY
from .reading import read_runs

PAGE_TITLE: Final[str] = "Calibration"


class BoardRequest(BaseModel):
    """What a listening page is asked for: the runs it reports, where it goes, and how it looks.

    Attributes:
        runs: The run directories the page reports, in the order it holds them.
        output: The directory the page is written into.
        palette: The name of the palette the page is drawn in.
        title: The heading the page carries.
    """

    model_config = ConfigDict(frozen=True)

    runs: List[Path] = Field(min_length=1)
    output: Path
    palette: str = DEFAULT_PALETTE_NAME
    title: str = PAGE_TITLE


def build_board(request: BoardRequest) -> Path:
    """
    Build the page a person listens to a run on, from what the runs already wrote.

    Everything the page needs travels with it: the web layout drawn from the application's own
    configuration in the requested palette, the application's faces inside a stylesheet, and the
    run's contents as data. A page written into the run it
    reports plays that run's clips where they lie; anywhere else it carries copies, so either page
    opens straight from the folder it was written into.

    Args:
        request: The runs the page reports, where it goes, and the palette it is drawn in.

    Returns:
        Path: The page, the file a reader opens.

    Raises:
        FileNotFoundError: If a run directory holds no renders, or the package a page file.
        KeyError: If the build ships no palette of the requested name.
    """
    runs = read_runs(request.runs)
    design = ApplicationDesign.load(request.palette)
    request.output.mkdir(parents=True, exist_ok=True)
    page = compose_page(runs, clip_store(runs, request.output), request.title, design.glyphs.headers.reconstruction)
    write_layout(request.output / PAGE_DIRECTORY, design)
    return write_assets(request.output, {DATA_FILE: data_script(page)})
