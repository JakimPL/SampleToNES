from dataclasses import replace
from functools import partial
from typing import Dict, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.ui.elements.layout.geometry import RowGeometry
from sampletones_application.ui.elements.layout.region import NO_MARGIN, NO_SCROLL, WindowedRegion
from sampletones_application.ui.elements.stems.columns import StemsColumns
from sampletones_application.ui.elements.stems.expansion import OpenFolders
from sampletones_application.ui.elements.stems.row import StemRowRenderer
from sampletones_application.ui.elements.stems.tags import StemsTags
from sampletones_application.view_model.shared.stems import (
    StemRowViewModel,
    StemsListViewModel,
)


class FolderRenderer:
    """One gathered folder: the row standing for it, and the recordings it opens onto.

    A folder arrives closed, reading as its name and how many recordings it brought in — one row
    among the rows around it, standing in their table and taking the height they take. Opening it
    sinks a region below that row, in which the recordings are drawn the way any other row is, so
    a reader answers for one of them without leaving the list. The region holds a folder's worth
    of rows and scrolls past that, building only the rows it shows — which is what makes opening a
    folder of thousands cost what opening a folder of ten costs.
    """

    def __init__(
        self,
        tags: StemsTags,
        *,
        layout: StemsListLayout,
        geometry: RowGeometry,
        open_folders: OpenFolders,
        rows: StemRowRenderer,
    ) -> None:
        self._tags = tags
        self._layout = layout
        self._geometry = geometry
        self._open_folders = open_folders
        self._rows = rows
        self._regions: Dict[str, WindowedRegion] = {}
        self._resting: Dict[str, float] = {}
        self._columns = StemsColumns(
            layout=layout,
            channels=(),
            master=False,
            removable=False,
            bends=False,
            folders=False,
        )

    def reads(self, columns: StemsColumns) -> None:
        """Takes up the grid the list is drawing, which a folder's own tables stand in too."""
        self._columns = columns

    def forget(self) -> None:
        """Take up where each open folder stood, and let go of the regions a rebuild took down.

        A region goes down with the list around it and comes back a new widget at its top, so the
        position it was scrolled to is held here and handed to the region that replaces it.
        """
        self._resting = {key: region.offset for key, region in self._regions.items()}
        self._regions.clear()

    @property
    def following(self) -> bool:
        """An open folder stands as something other than it will, so the list settles it again."""
        return any(region.settling for region in self._regions.values())

    def settle(self) -> Tuple[str, ...]:
        """Hold every open region to its ceiling and read what a row takes, a frame after a draw.

        Answers the folders whose rows have moved out from under what stands drawn, which is what
        a list redraws to follow a scroll.
        """
        return tuple(key for key, region in self._regions.items() if region.settle())

    def redraw(self, key: str, view_model: StemsListViewModel) -> None:
        """Build the slice one folder's region now reaches, leaving the rest of the list alone."""
        row = view_model.row(key)
        region = self._regions.get(key)
        if row is None or region is None:
            return

        self._fill(region, row, view_model)

    def repaint(
        self,
        row: StemRowViewModel,
        view_model: StemsListViewModel,
        *,
        releasable: bool,
    ) -> None:
        """Draw what the recordings in view currently hold onto the widgets they stand as.

        A recording inside a folder leaves the same way a loose one does, so it answers the same
        rule about whether the list is holding on to what it has.
        """
        region = self._regions.get(row.key)
        if region is None:
            return

        for held in self._reached(region, row):
            self._rows.repaint(held, view_model, releasable=releasable)

    def open(self, row: StemRowViewModel, view_model: StemsListViewModel) -> None:
        """Sink the folder's region below its row and fill it with the rows it reaches.

        The folder's own row stands in the run of rows around it, so what is drawn here is the
        space its recordings scroll in — which is why a folder standing closed draws nothing. The
        region opens no margin of its own: its recordings carry on from the row above them, so
        they start where the region does and the seam stays as narrow as the list's own rules.
        """
        region = WindowedRegion(
            tag=self._tags.region(row.key),
            geometry=self._geometry,
            ceiling=self._layout.folder_ceiling,
            padding=self._layout.well_padding,
            margin=NO_MARGIN,
            gutter=self._layout.scrollbar_width,
            indent=self._layout.well_padding + self._layout.folder_indent,
        )
        region.create(self._tags.body)
        region.opens_at(self._resting.get(row.key, NO_SCROLL))
        self._regions[row.key] = region
        self._fill(region, row, view_model)

    def _fill(
        self,
        region: WindowedRegion,
        row: StemRowViewModel,
        view_model: StemsListViewModel,
    ) -> None:
        region.draw(row.holds, partial(self._create_rows, region, row, view_model), lead=None)

    def _create_rows(
        self,
        region: WindowedRegion,
        row: StemRowViewModel,
        view_model: StemsListViewModel,
        start: int,
        count: int,
    ) -> None:
        """One table of the recordings a region reaches, declaring the columns the list lines up on.

        The room the region spends at its own right is the room the grid outside it holds clear, so
        the recordings inside a folder stand in the columns their neighbors stand in and none of
        them leads with a marker. Rules run between these rows the way they run outside, and the
        grids on either side of the region rule the two seams, so a folder's recordings read as
        the same list as the rows above and below them however far the region is scrolled.
        """
        held_columns = replace(self._columns, folders=False)
        with dpg.table(
            tag=self._tags.held(row.key),
            parent=region.body,
            header_row=False,
            policy=dpg.mvTable_SizingFixedFit,
            resizable=False,
            borders_innerV=True,
            borders_innerH=True,
        ):
            held_columns.declare()
            for held in row.held[start : start + count]:
                self._rows.create(held, view_model, held_columns)

    @staticmethod
    def _reached(region: WindowedRegion, row: StemRowViewModel) -> Tuple[StemRowViewModel, ...]:
        """The recordings the region has widgets for, which are the ones a repaint reaches."""
        start, count = region.window
        return row.held[start : start + count]
