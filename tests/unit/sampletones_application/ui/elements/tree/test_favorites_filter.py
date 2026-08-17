from typing import Any, Final, List, Tuple

import pytest

from sampletones_application.ui.elements.tree import tree as tree_module
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_core.structures.tree import TreeNode
from tests.suite.browser import (
    PANEL_TAG,
    TREE_COLORS,
    WHOLE_TREE,
    BrowserCorpus,
    as_view,
    build_browser_panel,
    nodes_at,
    view,
)

CHECKBOX_TAG: Final[str] = "sequencer.browser.checkbox.favorites"
GLYPH_TAG: Final[str] = "sequencer.browser.text.favorites"

STARRED_RECONSTRUCTION: Final[str] = as_view("""
    v By configuration
      v 44.1 kHz·30 Hz
        v FFT·γ0
          v PTN·#aaaaaaa
            - beat
    v By sample
      v beat
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
    """)
STARRED_LONE_AUDIO: Final[str] = as_view("""
    v By configuration
      v 44.1 kHz·30 Hz
        v CQT·γ0·PTN
          - solo
    v By sample
      - solo·44.1 kHz·30 Hz·CQT·γ0·PTN
    """)
STARRED_IN_SUBFOLDER: Final[str] = as_view("""
    v By configuration
      v 44.1 kHz·30 Hz
        v FFT·γ0
          v PTN·#aaaaaaa
            v drums
              - kick
    v By sample
      v drums
        v kick
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
    """)
STARRED_CONFIGURATION: Final[str] = as_view("""
    v By configuration
      v 44.1 kHz·30 Hz
        v FFT·γ0
          v PT
            > takes
              - alt
            - beat
    v By sample
      v beat
        - 44.1 kHz·30 Hz·FFT·γ0·PT
      - takes·alt·44.1 kHz·30 Hz·FFT·γ0·PT
    """)
STARRED_PLAIN_FOLDER: Final[str] = as_view("""
    v By configuration
      v archive
        > 48 kHz·50 Hz·LogFFT·γ1·TN
          - song
    """)
STARRED_FOLDER_AND_WHAT_IT_HOLDS: Final[str] = as_view("""
    v By configuration
      v archive
        v 48 kHz·50 Hz·LogFFT·γ1·TN
          - song
    """)
STARRED_STRAY: Final[str] = as_view("""
    v By configuration
      - stray
    """)
STARRED_OF_TWO_ALIKE: Final[str] = as_view("""
    v By configuration
      v 44.1 kHz·30 Hz
        v FFT·γ0
          v PTN·#aaaaaaa
            > drums
              - kick
              - snare
            - beat
            - melody
    v By sample
      v beat
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
      v drums
        v kick
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
        - snare·44.1 kHz·30 Hz·FFT·γ0·PTN
      v melody
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
    """)
STARRED_FOLDED_CONFIGURATION: Final[str] = as_view("""
    v By configuration
      v 8 kHz·60 Hz·CQT·γ2·P
        - sweep
    v By sample
      - sweep·8 kHz·60 Hz·CQT·γ2·P
    """)
STARRED_CONFIGURATION_B: Final[str] = as_view("""
    v By configuration
      v 44.1 kHz·30 Hz
        v FFT·γ0
          v PTN·#bbbbbbb
            > drums
              - kick
            - beat
            - melody
    v By sample
      v beat
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
      v drums
        v kick
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
      v melody
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
    """)
STARRED_FOLDER_HOLDING_A_STAR: Final[str] = as_view("""
    v By configuration
      v 44.1 kHz·30 Hz
        v FFT·γ0
          v PTN·#bbbbbbb
            v drums
              - kick
            - beat
            - melody
    v By sample
      v beat
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
      v drums
        v kick
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
      v melody
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
    """)
QUERY_INSIDE_THE_MODE: Final[str] = as_view("""
    v By configuration
      v 44.1 kHz·30 Hz
        v FFT·γ0
          v PTN·#bbbbbbb
            > drums  [hidden]
              - kick  [hidden]
            - beat  [hidden]
            - melody
    v By sample
      v beat  [hidden]
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb  [hidden]
      v drums  [hidden]
        v kick  [hidden]
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb  [hidden]
      v melody
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
    """)
QUERY_PAST_THE_MODE: Final[str] = as_view("""
    v By configuration
      v 44.1 kHz·30 Hz
        v FFT·γ0
          v PTN·#aaaaaaa
            - beat  [hidden]
    v By sample
      v beat  [hidden]
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa  [hidden]
    """)
QUERY_ALONE: Final[str] = as_view("""
    v By configuration
      > 8 kHz·60 Hz·CQT·γ2·P  [hidden]
        - sweep  [hidden]
      v 44.1 kHz·30 Hz
        > CQT·γ0·PTN  [hidden]
          - beat  [hidden]
          - solo  [hidden]
        v FFT·γ0
          > PT  [hidden]
            > takes  [hidden]
              - alt  [hidden]
            - beat  [hidden]
          v PTN·#aaaaaaa
            v drums
              - kick
              - snare  [hidden]
            - beat  [hidden]
            - melody  [hidden]
          v PTN·#bbbbbbb
            v drums
              - kick
            - beat  [hidden]
            - melody  [hidden]
      > archive  [hidden]
        > 48 kHz·50 Hz·LogFFT·γ1·TN  [hidden]
          - song  [hidden]
      - stray  [hidden]
    v By sample
      > beat  [hidden]
        - 44.1 kHz·30 Hz·CQT·γ0·PTN  [hidden]
        - 44.1 kHz·30 Hz·FFT·γ0·PT  [hidden]
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa  [hidden]
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb  [hidden]
      v drums
        v kick
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
        - snare·44.1 kHz·30 Hz·FFT·γ0·PTN  [hidden]
      > melody  [hidden]
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa  [hidden]
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb  [hidden]
      - solo·44.1 kHz·30 Hz·CQT·γ0·PTN  [hidden]
      - sweep·8 kHz·60 Hz·CQT·γ2·P  [hidden]
      - takes·alt·44.1 kHz·30 Hz·FFT·γ0·PT  [hidden]
    """)


class TestDrawnRows:
    """Which rows the mode draws: what the star reaches, and the rows leading down to it."""

    def test_a_starred_reconstruction_is_drawn_in_both_views(self, corpus: BrowserCorpus) -> None:
        assert view(corpus, {corpus.paths["A/beat"]}, favorites_only=True) == STARRED_RECONSTRUCTION

    def test_a_starred_reconstruction_of_an_audio_one_configuration_holds(self, corpus: BrowserCorpus) -> None:
        """A sample of a single variant folded into that variant, and the fold carries the star."""
        assert view(corpus, {corpus.paths["D/solo"]}, favorites_only=True) == STARRED_LONE_AUDIO

    def test_a_starred_reconstruction_in_a_mirrored_subfolder(self, corpus: BrowserCorpus) -> None:
        assert view(corpus, {corpus.paths["A/drums/kick"]}, favorites_only=True) == STARRED_IN_SUBFOLDER

    def test_a_starred_configuration_directory_brings_what_it_holds(self, corpus: BrowserCorpus) -> None:
        assert view(corpus, {corpus.paths["C"]}, favorites_only=True) == STARRED_CONFIGURATION

    def test_a_starred_plain_folder_reaches_the_configuration_nested_in_it(self, corpus: BrowserCorpus) -> None:
        """The sample branch reads the top-level configurations, so a nested one stands there alone."""
        assert view(corpus, {corpus.paths["archive"]}, favorites_only=True) == STARRED_PLAIN_FOLDER

    def test_a_starred_reconstruction_outside_every_configuration(self, corpus: BrowserCorpus) -> None:
        assert view(corpus, {corpus.paths["stray"]}, favorites_only=True) == STARRED_STRAY

    def test_a_star_on_one_of_two_configurations_reading_alike(self, corpus: BrowserCorpus) -> None:
        """The star belongs to a path, so the sibling marked with the other hash stays out."""
        assert view(corpus, {corpus.paths["A"]}, favorites_only=True) == STARRED_OF_TWO_ALIKE

    def test_a_starred_configuration_whose_chain_folded_into_one_row(self, corpus: BrowserCorpus) -> None:
        assert view(corpus, {corpus.paths["E"]}, favorites_only=True) == STARRED_FOLDED_CONFIGURATION

    def test_nothing_starred_draws_no_row(self, corpus: BrowserCorpus) -> None:
        assert view(corpus, set(), favorites_only=True) == ""

    def test_the_mode_off_draws_every_row(self, corpus: BrowserCorpus) -> None:
        assert view(corpus, {corpus.paths["A/beat"]}, favorites_only=False) == WHOLE_TREE


class TestOpenRows:
    """Which rows stand open: the way down to a star, and a starred folder showing what it holds."""

    def test_a_starred_folder_opens_and_a_subfolder_holding_no_star_stays_closed(
        self,
        corpus: BrowserCorpus,
    ) -> None:
        assert view(corpus, {corpus.paths["C"]}, favorites_only=True) == STARRED_CONFIGURATION

    def test_a_starred_folder_opens_one_level(self, corpus: BrowserCorpus) -> None:
        assert view(corpus, {corpus.paths["A"]}, favorites_only=True) == STARRED_OF_TWO_ALIKE

    def test_a_star_inside_a_starred_folder_opens_the_way_down_to_itself(self, corpus: BrowserCorpus) -> None:
        favorites = {corpus.paths["B"], corpus.paths["B/drums/kick"]}
        assert view(corpus, favorites, favorites_only=True) == STARRED_FOLDER_HOLDING_A_STAR

    def test_a_starred_folder_inside_a_starred_folder_opens(self, corpus: BrowserCorpus) -> None:
        favorites = {corpus.paths["archive"], corpus.paths["archive/F"]}
        assert view(corpus, favorites, favorites_only=True) == STARRED_FOLDER_AND_WHAT_IT_HOLDS

    def test_the_rows_above_a_starred_reconstruction_open(self, corpus: BrowserCorpus) -> None:
        assert view(corpus, {corpus.paths["A/beat"]}, favorites_only=True) == STARRED_RECONSTRUCTION

    def test_the_sample_branch_opens_the_way_to_the_variants_a_starred_folder_holds(
        self,
        corpus: BrowserCorpus,
    ) -> None:
        """No row stands for the folder there, so the variants are where the star arrives."""
        assert view(corpus, {corpus.paths["B"]}, favorites_only=True) == STARRED_CONFIGURATION_B


class TestSearchInsideTheMode:
    """The mode states which rows are drawn, and the query states which of them are shown."""

    def test_a_query_hides_the_drawn_rows_it_leaves_out(self, corpus: BrowserCorpus) -> None:
        assert (
            view(
                corpus,
                {corpus.paths["B"]},
                favorites_only=True,
                query="melody",
            )
            == QUERY_INSIDE_THE_MODE
        )

    def test_a_query_naming_a_row_the_mode_leaves_out_shows_nothing_of_it(self, corpus: BrowserCorpus) -> None:
        assert (
            view(
                corpus,
                {corpus.paths["A/beat"]},
                favorites_only=True,
                query="melody",
            )
            == QUERY_PAST_THE_MODE
        )

    def test_a_query_cleared_shows_the_rows_the_mode_draws(self, corpus: BrowserCorpus) -> None:
        assert (
            view(
                corpus,
                {corpus.paths["B"]},
                favorites_only=True,
                query="",
            )
            == STARRED_CONFIGURATION_B
        )

    def test_a_query_alone_draws_every_row_and_shows_the_matches(self, corpus: BrowserCorpus) -> None:
        assert view(corpus, set(), favorites_only=False, query="kick") == QUERY_ALONE


class TestEmptyAnswer:
    """A rebuild drawing no row names the filter that answered so, where the rows would be."""

    def test_the_mode_finding_no_favorite_names_the_favorites(self, corpus: BrowserCorpus) -> None:
        panel = build_browser_panel(corpus, set(), favorites_only=True)
        assert panel._empty_filter_message() == "global.dialog.message.tree_no_favorites"

    def test_a_query_finding_nothing_names_the_results(self, corpus: BrowserCorpus) -> None:
        panel = build_browser_panel(corpus, set(), favorites_only=False, query="nothing")
        assert panel._empty_filter_message() == "global.dialog.message.tree_no_results"


class TestControl:
    """What the checkbox beside the search box answers for: the mode, the memory of it, the rows."""

    def test_the_mode_the_control_reads_reaches_the_filter(
        self,
        corpus: BrowserCorpus,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = build_browser_panel(corpus, {corpus.paths["A/beat"]}, favorites_only=False)
        monkeypatch.setattr(panel, "redraw_tree", lambda: None, raising=False)

        panel._on_favorites_only_changed(None, True)

        assert panel._filter.favorites_only

    def test_a_change_is_handed_to_the_hook_remembering_it(
        self,
        corpus: BrowserCorpus,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = build_browser_panel(corpus, {corpus.paths["A/beat"]}, favorites_only=False)
        remembered: List[Tuple[str, bool]] = []
        panel.on_favorites_filter_changed = lambda panel_tag, favorites_only: remembered.append(
            (panel_tag, favorites_only)
        )
        monkeypatch.setattr(panel, "redraw_tree", lambda: None, raising=False)

        panel._on_favorites_only_changed(None, True)

        assert remembered == [(PANEL_TAG, True)]

    def test_a_change_draws_the_rows_the_new_mode_names(
        self,
        corpus: BrowserCorpus,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = build_browser_panel(corpus, {corpus.paths["A/beat"]}, favorites_only=False)
        redraws: List[bool] = []
        monkeypatch.setattr(panel, "redraw_tree", lambda: redraws.append(True), raising=False)

        panel._on_favorites_only_changed(None, True)

        assert redraws == [True]

    def test_the_mode_a_session_left_on_stands_before_the_first_rebuild(self, corpus: BrowserCorpus) -> None:
        panel = build_browser_panel(corpus, {corpus.paths["A/beat"]}, favorites_only=False)

        panel._restore_favorites_only(True)

        assert panel._filter.favorites_only

    def test_a_query_typed_earlier_survives_a_change_of_mode(
        self,
        corpus: BrowserCorpus,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = build_browser_panel(corpus, {corpus.paths["A/beat"]}, favorites_only=False, query="beat")
        monkeypatch.setattr(panel, "redraw_tree", lambda: None, raising=False)

        panel._on_favorites_only_changed(None, True)

        assert panel._filter.query == "beat"


class TestStarColor:
    """The star beside the label reads in the colour of the mode it stands for."""

    def test_the_star_reads_favorite_while_the_mode_is_on(self, corpus: BrowserCorpus) -> None:
        panel = build_browser_panel(corpus, set(), favorites_only=True)
        assert panel._favorites_glyph_color() == TREE_COLORS.favorite

    def test_the_star_reads_muted_while_the_mode_is_off(self, corpus: BrowserCorpus) -> None:
        panel = build_browser_panel(corpus, set(), favorites_only=False)
        assert panel._favorites_glyph_color() == TREE_COLORS.muted

    def test_the_star_is_coloured_with_the_token_the_mode_names(
        self,
        corpus: BrowserCorpus,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The colour reaches the star as a token, so the star follows a palette swapped in place."""
        panel = build_browser_panel(corpus, set(), favorites_only=True)
        panel._favorites_glyph_tag = GLYPH_TAG
        coloured: List[Tuple[str, BaseColor]] = []
        monkeypatch.setattr(
            tree_module,
            "dpg_set_palette_color",
            lambda item, color: coloured.append((item, color)),
        )

        panel._apply_favorites_glyph_color()

        assert coloured == [(GLYPH_TAG, TREE_COLORS.favorite)]


class TestControlLock:
    """A rebuild is what the control asks for, so the tree's lock reaches it."""

    def test_the_lock_reaches_the_control(
        self,
        corpus: BrowserCorpus,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = build_browser_panel(corpus, set(), favorites_only=True)
        panel._favorites_checkbox_tag = CHECKBOX_TAG
        configured: List[Tuple[str, Any]] = []
        monkeypatch.setattr(
            tree_module,
            "dpg_configure_item",
            lambda tag, **kwargs: configured.append((tag, kwargs["enabled"])),
        )

        panel.set_favorites_filter_enabled(False)

        assert configured == [(CHECKBOX_TAG, False)]

    def test_a_browser_offering_no_control_answers_the_lock_as_it_stands(
        self,
        corpus: BrowserCorpus,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = build_browser_panel(corpus, set(), favorites_only=False)
        configured: List[Tuple[str, Any]] = []
        monkeypatch.setattr(
            tree_module,
            "dpg_configure_item",
            lambda tag, **kwargs: configured.append((tag, kwargs["enabled"])),
        )

        panel.set_favorites_filter_enabled(False)

        assert configured == []


class TestFavoriteChange:
    def test_a_change_draws_the_tree_again_while_the_mode_is_on(
        self,
        corpus: BrowserCorpus,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = build_browser_panel(corpus, {corpus.paths["A/beat"]}, favorites_only=True)
        redraws: List[bool] = []
        repaints: List[TreeNode] = []
        monkeypatch.setattr(panel, "redraw_tree", lambda: redraws.append(True), raising=False)
        monkeypatch.setattr(
            panel,
            "_reapply_theme_recursively",
            lambda node, has_favorite_ancestor=False: repaints.append(node),
            raising=False,
        )

        panel.update_favorite_indicators(nodes_at(corpus, "A/beat"))

        assert redraws == [True]
        assert repaints == []

    def test_a_change_repaints_every_row_standing_for_the_path_while_the_mode_is_off(
        self,
        corpus: BrowserCorpus,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """One path reaches the panel as a row in each view, and each takes its own ancestry."""
        panel = build_browser_panel(corpus, {corpus.paths["A/beat"]}, favorites_only=False)
        redraws: List[bool] = []
        repaints: List[TreeNode] = []
        monkeypatch.setattr(panel, "redraw_tree", lambda: redraws.append(True), raising=False)
        monkeypatch.setattr(
            panel,
            "_reapply_theme_recursively",
            lambda node, has_favorite_ancestor=False: repaints.append(node),
            raising=False,
        )
        rows = nodes_at(corpus, "A/beat")

        panel.update_favorite_indicators(rows)

        assert redraws == []
        assert repaints == list(rows)
