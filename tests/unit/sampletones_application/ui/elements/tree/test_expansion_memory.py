from pathlib import Path
from typing import Any, Dict, Final, List, Tuple

import pytest

from sampletones_application.ui.elements.tree import tree as tree_module
from tests.suite.browser import (
    WHOLE_TREE,
    BrowserCorpus,
    as_view,
    build_browser_panel,
    build_corpus,
    nodes_at,
    render_view,
    row_named,
    select_favorites,
    set_filter,
    set_row_expanded,
)

STARRED_CONFIGURATION: Final[str] = as_view("""
    > By configuration
      > 44.1 kHz·30 Hz
        > FFT·γ0
          > PT
            > takes
              - alt
            - beat
    > By sample
      > beat
        - 44.1 kHz·30 Hz·FFT·γ0·PT
      - takes·alt·44.1 kHz·30 Hz·FFT·γ0·PT
    """)
SUBFOLDER_THE_READER_OPENED: Final[str] = as_view("""
    > By configuration
      > 44.1 kHz·30 Hz
        > FFT·γ0
          > PT
            v takes
              - alt
            - beat
    > By sample
      > beat
        - 44.1 kHz·30 Hz·FFT·γ0·PT
      - takes·alt·44.1 kHz·30 Hz·FFT·γ0·PT
    """)
WHOLE_TREE_WITHOUT_THE_ARCHIVE: Final[str] = as_view("""
    > By configuration
      > 8 kHz·60 Hz·CQT·γ2·P
        - sweep
      > 44.1 kHz·30 Hz
        > CQT·γ0·PTN
          - beat
          - solo
        > FFT·γ0
          > PT
            > takes
              - alt
            - beat
          > PTN·#aaaaaaa
            > drums
              - kick
              - snare
            - beat
            - melody
          > PTN·#bbbbbbb
            > drums
              - kick
            - beat
            - melody
      - stray
    > By sample
      > beat
        - 44.1 kHz·30 Hz·CQT·γ0·PTN
        - 44.1 kHz·30 Hz·FFT·γ0·PT
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
      > drums
        > kick
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
        - snare·44.1 kHz·30 Hz·FFT·γ0·PTN
      > melody
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
      - solo·44.1 kHz·30 Hz·CQT·γ0·PTN
      - sweep·8 kHz·60 Hz·CQT·γ2·P
      - takes·alt·44.1 kHz·30 Hz·FFT·γ0·PT
    """)


class TestTheReadersShape:
    """A row stands where the reader left it, and a later pass brings it back that way."""

    def test_a_row_the_reader_opened_is_drawn_open(self, corpus: BrowserCorpus) -> None:
        panel = build_browser_panel(corpus, {corpus.paths["C"]}, favorites_only=True)
        assert render_view(panel) == STARRED_CONFIGURATION

        set_row_expanded(panel, row_named(corpus, "takes"), expanded=True)

        assert render_view(panel) == SUBFOLDER_THE_READER_OPENED

    def test_a_row_the_reader_closed_is_drawn_closed(self, corpus: BrowserCorpus) -> None:
        panel = build_browser_panel(corpus, {corpus.paths["C"]}, favorites_only=True)
        set_row_expanded(panel, row_named(corpus, "takes"), expanded=True)
        render_view(panel)

        set_row_expanded(panel, row_named(corpus, "takes"), expanded=False)

        assert render_view(panel) == STARRED_CONFIGURATION

    def test_the_rows_the_mode_opened_fold_back_once_it_goes_off(self, corpus: BrowserCorpus) -> None:
        """What the browser unfolded to show a favorite is the mode's, so the shape is left untouched."""
        panel = build_browser_panel(
            corpus,
            {corpus.paths["A/beat"]},
            favorites_only=False,
            auto_expand_reconstructions=True,
        )
        select_favorites(panel)
        render_view(panel)

        set_filter(panel, favorites_only=False)

        assert render_view(panel) == WHOLE_TREE

    def test_the_rows_the_mode_opened_are_no_part_of_what_a_save_writes(self, corpus: BrowserCorpus) -> None:
        panel = build_browser_panel(
            corpus,
            {corpus.paths["A/beat"]},
            favorites_only=False,
            auto_expand_reconstructions=True,
        )
        select_favorites(panel)
        render_view(panel)

        assert panel.expanded_rows == set()

    def test_a_row_the_mode_never_drew_keeps_the_state_it_had(self, corpus: BrowserCorpus) -> None:
        panel = build_browser_panel(corpus, {corpus.paths["A/beat"]}, favorites_only=False)
        set_row_expanded(panel, row_named(corpus, "archive"), expanded=True)
        render_view(panel)

        set_filter(panel, favorites_only=True)
        render_view(panel)
        set_filter(panel, favorites_only=False)

        assert "v archive" in render_view(panel)

    def test_a_refresh_brings_the_rows_back_standing_as_they_were(
        self,
        corpus: BrowserCorpus,
        tmp_path: Path,
    ) -> None:
        """A rebuilt model states the same rows, and a row is remembered by the ancestry it reads."""
        panel = build_browser_panel(corpus, set(), favorites_only=False)
        set_row_expanded(panel, row_named(corpus, "archive"), expanded=True)
        render_view(panel)

        panel.tree = build_corpus(tmp_path).tree

        assert "v archive" in render_view(panel)

    def test_a_pass_over_the_whole_tree_forgets_the_rows_the_model_dropped(
        self,
        corpus: BrowserCorpus,
    ) -> None:
        panel = build_browser_panel(corpus, set(), favorites_only=False)
        archive = row_named(corpus, "archive")
        set_row_expanded(panel, archive, expanded=True)
        render_view(panel)

        archive.parent = None

        assert render_view(panel) == WHOLE_TREE_WITHOUT_THE_ARCHIVE
        assert panel._expanded_rows == set()

    def test_a_browser_opens_with_the_rows_a_session_left_it(self, corpus: BrowserCorpus) -> None:
        """The shape outlives the run it was made in, so a browser is handed it as it is built."""
        panel = build_browser_panel(corpus, set(), favorites_only=False)
        archive_tag = panel._generate_node_tag(row_named(corpus, "archive"))

        opened = build_browser_panel(
            corpus,
            set(),
            favorites_only=False,
            expanded_rows={archive_tag},
        )

        assert "v archive" in render_view(opened)

    def test_a_pass_in_the_favorites_mode_forgets_the_rows_the_model_dropped(
        self,
        corpus: BrowserCorpus,
    ) -> None:
        """The model states which rows exist whatever the mode narrows to, so a lost row is dropped."""
        panel = build_browser_panel(corpus, {corpus.paths["A/beat"]}, favorites_only=False)
        archive = row_named(corpus, "archive")
        set_row_expanded(panel, archive, expanded=True)
        render_view(panel)

        archive.parent = None
        set_filter(panel, favorites_only=True)
        render_view(panel)

        assert panel._expanded_rows == set()

    def test_the_shape_a_save_writes_is_the_rows_standing_open(self, corpus: BrowserCorpus) -> None:
        panel = build_browser_panel(corpus, set(), favorites_only=False)
        archive_tag = panel._generate_node_tag(row_named(corpus, "archive"))
        set_row_expanded(panel, row_named(corpus, "archive"), expanded=True)

        assert panel.expanded_rows == {archive_tag}

    def test_the_shape_a_save_reads_is_taken_apart_from_the_browser(self, corpus: BrowserCorpus) -> None:
        """The browser keeps writing its own memory, so what a save carries is a reading of it."""
        panel = build_browser_panel(corpus, set(), favorites_only=False)
        set_row_expanded(panel, row_named(corpus, "archive"), expanded=True)
        written = panel.expanded_rows

        set_row_expanded(panel, row_named(corpus, "archive"), expanded=False)

        assert written != panel.expanded_rows

    def test_two_browsers_over_one_tree_remember_their_own_shape(self, corpus: BrowserCorpus) -> None:
        """A row is remembered under the tag of the browser showing it, so neither reaches the other."""
        sequencer = build_browser_panel(corpus, set(), favorites_only=False, panel_tag="sequencer.browser")
        reconstruction = build_browser_panel(corpus, set(), favorites_only=False, panel_tag="reconstruction.browser")

        set_row_expanded(sequencer, row_named(corpus, "archive"), expanded=True)

        assert "v archive" in render_view(sequencer)
        assert render_view(reconstruction) == WHOLE_TREE


class TestFollowingTheReader:
    """A click on a row is how it folds, and the browser reads what it stands as afterwards."""

    def test_a_click_reads_the_row_the_frame_after_it_landed(
        self,
        corpus: BrowserCorpus,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = build_browser_panel(corpus, set(), favorites_only=False)
        scheduled: List[Tuple[Any, Tuple[Any, ...], Dict[str, Any]]] = []
        monkeypatch.setattr(
            tree_module.CallbackQueue,
            "add",
            lambda callback, *args, **kwargs: scheduled.append((callback, args, kwargs)),
        )

        panel._remember_clicked_row((row_named(corpus, "archive"), "row.tag"))

        assert scheduled == [(panel._read_row_expansion, ("row.tag",), {"delay": 1})]

    def test_a_row_holding_nothing_has_nothing_to_remember(
        self,
        corpus: BrowserCorpus,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = build_browser_panel(corpus, set(), favorites_only=False)
        scheduled: List[Tuple[Any, Tuple[Any, ...], Dict[str, Any]]] = []
        monkeypatch.setattr(
            tree_module.CallbackQueue,
            "add",
            lambda callback, *args, **kwargs: scheduled.append((callback, args, kwargs)),
        )

        panel._remember_clicked_row((nodes_at(corpus, "stray")[0], "row.tag"))

        assert scheduled == []

    def test_the_reading_takes_the_state_the_row_stands_in(
        self,
        corpus: BrowserCorpus,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = build_browser_panel(corpus, set(), favorites_only=False)
        monkeypatch.setattr(tree_module.dpg, "does_item_exist", lambda tag: True)
        monkeypatch.setattr(tree_module, "dpg_get_value", lambda tag: True)

        panel._read_row_expansion("row.tag")

        assert panel._expanded_rows == {"row.tag"}

    def test_a_row_that_left_the_tree_is_read_no_further(
        self,
        corpus: BrowserCorpus,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = build_browser_panel(corpus, set(), favorites_only=False)
        monkeypatch.setattr(tree_module.dpg, "does_item_exist", lambda tag: False)

        panel._read_row_expansion("row.tag")

        assert panel._expanded_rows == set()
