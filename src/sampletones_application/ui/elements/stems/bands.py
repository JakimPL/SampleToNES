from typing import List, Sequence

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.tags.general import (
    SUF_STRIP,
    SUF_TABLE,
    SUF_TEXT,
    TAG_GLOBAL_THEME_SECTION_HEADER,
    TAG_GLOBAL_THEME_STEMS_DROP_STRIP,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.stems.columns import StemsColumns
from sampletones_application.ui.elements.stems.expansion import OpenFolders
from sampletones_application.ui.elements.stems.folder import FolderRenderer
from sampletones_application.ui.elements.stems.gestures import StemsGestures
from sampletones_application.ui.elements.stems.heading import StemsHeading
from sampletones_application.ui.elements.stems.offer import StemsListOffer
from sampletones_application.ui.elements.stems.row import StemRowRenderer
from sampletones_application.ui.elements.stems.shape import ListShape, Reshape
from sampletones_application.ui.elements.stems.tags import StemsTags
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.view_model.shared.stems import (
    StemRowViewModel,
    StemsListViewModel,
)


class LevelBands:
    """The rows of a stems list, grouped into the levels they pick on.

    A band is a caption, a table of the rows standing on that level, and — where the list takes
    drops — the strip above it a recording lands in to take a level of its own. Collapsing the
    levels draws every row in one table, which is the shape a list takes where the bands record a
    setup rather than offer somewhere to drop onto.

    A folder breaks the run of rows it stands in, so the recordings it opens onto stand between
    the rows above it and the rows below. Every table declares the same columns, so the rows line
    up down the list however many folders break it.
    """

    def __init__(
        self,
        tags: StemsTags,
        *,
        layout: StemsListLayout,
        offer: StemsListOffer,
        language_manager: LanguageManager,
        rows: StemRowRenderer,
        folders: FolderRenderer,
        heading: StemsHeading,
        open_folders: OpenFolders,
        gestures: StemsGestures,
    ) -> None:
        self._tags = tags
        self._layout = layout
        self._offer = offer
        self._rows = rows
        self._folders = folders
        self._heading = heading
        self._open_folders = open_folders
        self._gestures = gestures
        self._level_template = language_manager["global.stems.template.level_caption"]
        self._shape = ListShape.nothing()

    def reshape(self, view_model: StemsListViewModel) -> Reshape:
        """What the view asks of the widgets standing: the whole list, some folders, or nothing.

        The shape is taken up either way, so a list that has answered a reshape once answers the
        same view with a repaint from then on.
        """
        shape = ListShape.of(view_model, self._open_folders)
        if shape == self._shape:
            return Reshape.nothing()

        asked = shape.against(self._shape)
        self._shape = shape
        return asked

    def forget(self) -> None:
        """Let go of the shape standing, so the next reading is drawn rather than repainted."""
        self._shape = ListShape.nothing()

    def build_heading(self, view_model: StemsListViewModel, parent: str) -> None:
        """Name the channels once above the rows, so a cell below them holds the box alone.

        The heading stands above whatever the list draws, banded or plain, and every table below
        it is declared from the same grid. A list drawing no channel columns has nothing to name,
        so the rows stand on their own.
        """
        columns = self.columns(view_model)
        self._folders.reads(columns)
        if not columns.channels:
            return

        self._heading.create(parent, columns)
        self._heading.render(view_model.muted_channels)

    def build_rows(self, view_model: StemsListViewModel, start: int, count: int) -> None:
        """One table of the rows a window reaches, in the grid the whole list stands in."""
        self._create_table(self._tags.segment(0), view_model, view_model.rows[start : start + count])

    def build(self, view_model: StemsListViewModel) -> None:
        """Build the bands the view names, into whatever the list has cleared for them."""
        if view_model.collapse_levels:
            self._create_listing(view_model)
            return

        for level_index in range(view_model.level_count):
            self._create_strip(level_index)
            self._create_caption(level_index)
            self._create_table(
                self._tags.level(level_index, SUF_TABLE),
                view_model,
                view_model.rows_on(level_index),
            )

        if view_model.level_count:
            self._create_strip(view_model.level_count)

    def _create_listing(self, view_model: StemsListViewModel) -> None:
        """Every row in one run, a folder breaking it so its own recordings stand below it."""
        loose: List[StemRowViewModel] = []
        segment = 0
        for row in view_model.rows:
            if not row.stands_for_a_folder:
                loose.append(row)
                continue

            segment = self._flush(loose, view_model, segment)
            self._folders.create(row, view_model)

        self._flush(loose, view_model, segment)

    def _flush(self, loose: List[StemRowViewModel], view_model: StemsListViewModel, segment: int) -> int:
        """Draw the run of rows gathered since the last folder, and open the next run empty."""
        if not loose:
            return segment

        self._create_table(self._tags.segment(segment), view_model, tuple(loose))
        loose.clear()
        return segment + 1

    def _create_strip(self, position: int) -> None:
        """The gap a level is broken at: a recording dropped here takes a level of its own.

        The strip reads as the gap it is and lights up only while a payload hovers it, so a
        band separator stays a separator to everything but a drag.
        """
        if not self._offer.dragging:
            return

        strip = dpg.add_button(
            label="",
            tag=self._tags.level(position, SUF_STRIP),
            parent=self._tags.body,
            height=self._layout.level_strip_height,
            user_data=position,
            payload_type=self._tags.payload,
            drop_callback=self._gestures.on_level_drop,
        )
        ThemeRegistry.get(TAG_GLOBAL_THEME_STEMS_DROP_STRIP).bind_to_item(strip)

    def _create_caption(self, level_index: int) -> None:
        """The band's own name, in the accent a section header takes, so a level reads as one."""
        caption = dpg.add_text(
            self._level_template.format(level_index + 1).upper(),
            tag=self._tags.level(level_index, SUF_TEXT),
            parent=self._tags.body,
        )
        FontRegistry.bind_to_item(caption, Font.BOLD)
        ThemeRegistry.get(TAG_GLOBAL_THEME_SECTION_HEADER).bind_to_item(caption)

    def _create_table(
        self,
        tag: str,
        view_model: StemsListViewModel,
        rows: Sequence[StemRowViewModel],
    ) -> None:
        """One grid of rows, every band declaring the same columns so they line up across bands."""
        columns = self.columns(view_model)
        with dpg.table(
            tag=tag,
            parent=self._tags.body,
            header_row=False,
            policy=dpg.mvTable_SizingFixedFit,
            resizable=False,
            borders_innerV=True,
        ):
            columns.declare()
            for row in rows:
                self._rows.create(row, view_model, columns)

    def columns(self, view_model: StemsListViewModel) -> StemsColumns:
        """The grid every table of this list stands in, the heading above them included.

        A list holding a folder says so to the grid, which is what stands the columns around a
        folder where the columns inside its own region stand and opens a loose row's name where a
        folder's marker opens.
        """
        return StemsColumns(
            layout=self._layout,
            channels=view_model.channels_in_play,
            master=self._offer.master_box,
            removable=self._offer.removal,
            bends=self._offer.bends,
            folders=view_model.holds_folders,
        )
