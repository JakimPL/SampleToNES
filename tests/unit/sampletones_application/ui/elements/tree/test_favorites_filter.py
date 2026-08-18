from dataclasses import dataclass
from typing import Any, Final, List, Tuple

import pytest

from sampletones_application.ui.elements.tree import tree as tree_module
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_core.structures.tree import TreeNode
from tests.suite.base import BaseTestSuite
from tests.suite.browser import (
    ARCHIVE,
    BY_CONFIGURATION,
    BY_SAMPLE,
    CLOSED_MARKER,
    OPEN_MARKER,
    PANEL_TAG,
    STARRED_CONFIGURATION,
    TREE_COLORS,
    WHOLE_TREE,
    BrowserCorpus,
    FakeTreeLogic,
    as_view,
    build_browser_panel,
    nodes_at,
    paths_of,
    render_view,
    resolve_pass,
    select_favorites,
    view,
    view_on_selecting_favorites,
    with_branch_open,
    with_rows_open,
)
from tests.suite.case import BaseRegularTestCase

CHECKBOX_TAG: Final[str] = "sequencer.browser.checkbox.favorites"
GLYPH_TAG: Final[str] = "sequencer.browser.text.favorites"

FREQUENCIES: Final[str] = "44.1 kHz·30 Hz"
TRANSFORMATION: Final[str] = "FFT·γ0"
CONFIGURATION_B_ROW: Final[str] = "PTN·#bbbbbbb"


def rows_of(rendered: str) -> List[str]:
    """The rows a view holds, read apart from the state each of them stands in."""
    return [line.replace(OPEN_MARKER, CLOSED_MARKER, 1) for line in rendered.splitlines()]


STARRED_RECONSTRUCTION: Final[str] = as_view("""
    > By configuration
      > 44.1 kHz·30 Hz
        > FFT·γ0
          > PTN·#aaaaaaa
            - beat
    > By sample
      > beat
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
    """)
STARRED_LONE_AUDIO: Final[str] = as_view("""
    > By configuration
      > 44.1 kHz·30 Hz
        > CQT·γ0·PTN
          - solo
    > By sample
      - solo·44.1 kHz·30 Hz·CQT·γ0·PTN
    """)
STARRED_IN_SUBFOLDER: Final[str] = as_view("""
    > By configuration
      > 44.1 kHz·30 Hz
        > FFT·γ0
          > PTN·#aaaaaaa
            > drums
              - kick
    > By sample
      > drums
        > kick
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
    """)
STARRED_PLAIN_FOLDER: Final[str] = as_view("""
    > By configuration
      > archive
        > 48 kHz·50 Hz·LogFFT·γ1·TN
          - song
    """)
STARRED_STRAY: Final[str] = as_view("""
    > By configuration
      - stray
    """)
STARRED_OF_TWO_ALIKE: Final[str] = as_view("""
    > By configuration
      > 44.1 kHz·30 Hz
        > FFT·γ0
          > PTN·#aaaaaaa
            > drums
              - kick
              - snare
            - beat
            - melody
    > By sample
      > beat
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
      > drums
        > kick
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
        - snare·44.1 kHz·30 Hz·FFT·γ0·PTN
      > melody
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#aaaaaaa
    """)
STARRED_FOLDED_CONFIGURATION: Final[str] = as_view("""
    > By configuration
      > 8 kHz·60 Hz·CQT·γ2·P
        - sweep
    > By sample
      - sweep·8 kHz·60 Hz·CQT·γ2·P
    """)
STARRED_CONFIGURATION_B: Final[str] = as_view("""
    > By configuration
      > 44.1 kHz·30 Hz
        > FFT·γ0
          > PTN·#bbbbbbb
            > drums
              - kick
            - beat
            - melody
    > By sample
      > beat
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
      > drums
        > kick
          - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
      > melody
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb
    """)

STARRED_RECONSTRUCTION_OPENED: Final[str] = with_branch_open(STARRED_RECONSTRUCTION, BY_CONFIGURATION, BY_SAMPLE)
STARRED_LONE_AUDIO_OPENED: Final[str] = with_branch_open(STARRED_LONE_AUDIO, BY_CONFIGURATION, BY_SAMPLE)
STARRED_IN_SUBFOLDER_OPENED: Final[str] = with_branch_open(STARRED_IN_SUBFOLDER, BY_CONFIGURATION, BY_SAMPLE)
STARRED_CONFIGURATION_OPENED: Final[str] = with_branch_open(
    with_rows_open(
        STARRED_CONFIGURATION,
        BY_CONFIGURATION,
        FREQUENCIES,
        TRANSFORMATION,
    ),
    BY_SAMPLE,
)
STARRED_PLAIN_FOLDER_OPENED: Final[str] = with_rows_open(STARRED_PLAIN_FOLDER, BY_CONFIGURATION)
STARRED_FOLDER_IN_STARRED_FOLDER_OPENED: Final[str] = with_rows_open(
    STARRED_PLAIN_FOLDER,
    BY_CONFIGURATION,
    ARCHIVE,
)
STARRED_STRAY_OPENED: Final[str] = with_rows_open(STARRED_STRAY, BY_CONFIGURATION)
STARRED_OF_TWO_ALIKE_OPENED: Final[str] = with_branch_open(
    with_rows_open(
        STARRED_OF_TWO_ALIKE,
        BY_CONFIGURATION,
        FREQUENCIES,
        TRANSFORMATION,
    ),
    BY_SAMPLE,
)
STARRED_FOLDED_CONFIGURATION_OPENED: Final[str] = with_rows_open(
    STARRED_FOLDED_CONFIGURATION,
    BY_CONFIGURATION,
    BY_SAMPLE,
)
STARRED_CONFIGURATION_B_OPENED: Final[str] = with_branch_open(
    with_rows_open(
        STARRED_CONFIGURATION_B,
        BY_CONFIGURATION,
        FREQUENCIES,
        TRANSFORMATION,
    ),
    BY_SAMPLE,
)
STARRED_FOLDER_HOLDING_A_STAR_OPENED: Final[str] = with_branch_open(
    with_rows_open(
        STARRED_CONFIGURATION_B,
        BY_CONFIGURATION,
        FREQUENCIES,
        TRANSFORMATION,
        CONFIGURATION_B_ROW,
        BY_SAMPLE,
    ),
    "drums",
)
STARRED_FOLDER_HOLDING_A_STAR_BY_FOLDER: Final[str] = with_rows_open(
    STARRED_CONFIGURATION_B,
    BY_CONFIGURATION,
    FREQUENCIES,
    TRANSFORMATION,
    BY_SAMPLE,
    "beat",
    "melody",
)

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
      > beat  [hidden]
        - 44.1 kHz·30 Hz·FFT·γ0·PTN·#bbbbbbb  [hidden]
      > drums  [hidden]
        > kick  [hidden]
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
      > beat  [hidden]
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


class TestDrawnRows(BaseTestSuite):
    """Which rows the mode draws: what the star reaches, and the rows leading down to it.

    What is drawn is the star's to state and nothing else, so every row stands folded here: the mode
    is stated the way a session restores it, and a mode nobody asked for opens no row. A star belongs
    to a path, so a configuration reading like its sibling stays out while that sibling is drawn, and
    the sample branch reads the top-level configurations, leaving a nested one to stand there alone.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        starred: Tuple[str, ...]
        expected: str

    test_cases = (
        TestCase(
            starred=("A/beat",),
            expected=STARRED_RECONSTRUCTION,
            label="a_starred_reconstruction_is_drawn_in_both_views",
        ),
        TestCase(
            starred=("D/solo",),
            expected=STARRED_LONE_AUDIO,
            label="a_starred_reconstruction_of_an_audio_one_configuration_holds",
        ),
        TestCase(
            starred=("A/drums/kick",),
            expected=STARRED_IN_SUBFOLDER,
            label="a_starred_reconstruction_in_a_mirrored_subfolder",
        ),
        TestCase(
            starred=("C",),
            expected=STARRED_CONFIGURATION,
            label="a_starred_configuration_directory_brings_what_it_holds",
        ),
        TestCase(
            starred=("archive",),
            expected=STARRED_PLAIN_FOLDER,
            label="a_starred_plain_folder_reaches_the_configuration_nested_in_it",
        ),
        TestCase(
            starred=("stray",),
            expected=STARRED_STRAY,
            label="a_starred_reconstruction_outside_every_configuration",
        ),
        TestCase(
            starred=("A",),
            expected=STARRED_OF_TWO_ALIKE,
            label="a_star_on_one_of_two_configurations_reading_alike",
        ),
        TestCase(
            starred=("E",),
            expected=STARRED_FOLDED_CONFIGURATION,
            label="a_starred_configuration_whose_chain_folded_into_one_row",
        ),
        TestCase(
            starred=(),
            expected="",
            label="nothing_starred_draws_no_row",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_rows_a_star_draws(
        self,
        corpus: BrowserCorpus,
        test_case: TestCase,
    ) -> None:
        assert view(corpus, paths_of(corpus, *test_case.starred), favorites_only=True) == test_case.expected

    def test_the_mode_off_draws_every_row(self, corpus: BrowserCorpus) -> None:
        assert view(corpus, paths_of(corpus, "A/beat"), favorites_only=False) == WHOLE_TREE

    def test_the_rows_drawn_are_the_same_whichever_stars_are_followed(self, corpus: BrowserCorpus) -> None:
        """Opening the way down to a star is a separate answer, so it moves no row in or out."""
        favorites = paths_of(corpus, "B", "B/drums/kick")
        assert rows_of(
            view_on_selecting_favorites(
                corpus,
                favorites,
                auto_expand_reconstructions=True,
                auto_expand_directories=True,
            )
        ) == rows_of(view(corpus, favorites, favorites_only=True))


class TestOpenRows(BaseTestSuite):
    """Which rows stand open: the way down to a star the reader asked the browser to follow.

    A star is followed by the kind of thing it marks, so a reconstruction and a folder each answer to
    their own preference: the way down to a starred folder opens while the folder itself stays folded,
    a star inside a starred folder opens that folder once reconstructions are followed, and a folder
    standing on the way to a star below it opens with the rest of that way. In the sample branch no
    row stands for a folder, so a folder's star arrives at the variants it holds.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        starred: Tuple[str, ...]
        expected: str
        auto_expand_reconstructions: bool = False
        auto_expand_directories: bool = False

    test_cases = (
        TestCase(
            starred=("A/beat",),
            expected=STARRED_RECONSTRUCTION,
            label="the_preference_off_opens_nothing",
        ),
        TestCase(
            starred=("A/beat",),
            auto_expand_reconstructions=True,
            expected=STARRED_RECONSTRUCTION_OPENED,
            label="the_rows_above_a_starred_reconstruction_open",
        ),
        TestCase(
            starred=("D/solo",),
            auto_expand_reconstructions=True,
            expected=STARRED_LONE_AUDIO_OPENED,
            label="the_sample_row_above_a_starred_reconstruction_of_a_lone_audio_opens",
        ),
        TestCase(
            starred=("A/drums/kick",),
            auto_expand_reconstructions=True,
            expected=STARRED_IN_SUBFOLDER_OPENED,
            label="the_subfolder_above_a_starred_reconstruction_opens",
        ),
        TestCase(
            starred=("stray",),
            auto_expand_reconstructions=True,
            expected=STARRED_STRAY_OPENED,
            label="the_branch_above_a_starred_reconstruction_outside_every_configuration_opens",
        ),
        TestCase(
            starred=("A",),
            auto_expand_reconstructions=True,
            expected=STARRED_OF_TWO_ALIKE,
            label="a_starred_folder_is_left_folded_while_reconstructions_alone_are_followed",
        ),
        TestCase(
            starred=("A/beat",),
            auto_expand_directories=True,
            expected=STARRED_RECONSTRUCTION,
            label="a_starred_reconstruction_is_left_folded_while_directories_alone_are_followed",
        ),
        TestCase(
            starred=("C",),
            auto_expand_directories=True,
            expected=STARRED_CONFIGURATION_OPENED,
            label="the_rows_above_a_starred_configuration_open_and_it_stays_folded",
        ),
        TestCase(
            starred=("archive",),
            auto_expand_directories=True,
            expected=STARRED_PLAIN_FOLDER_OPENED,
            label="the_rows_above_a_starred_plain_folder_open_and_it_stays_folded",
        ),
        TestCase(
            starred=("archive", "archive/F"),
            auto_expand_directories=True,
            expected=STARRED_FOLDER_IN_STARRED_FOLDER_OPENED,
            label="a_starred_folder_holding_a_starred_folder_opens_the_way_down_to_it",
        ),
        TestCase(
            starred=("E",),
            auto_expand_directories=True,
            expected=STARRED_FOLDED_CONFIGURATION_OPENED,
            label="a_starred_configuration_whose_chain_folded_keeps_the_folded_row_closed",
        ),
        TestCase(
            starred=("B",),
            auto_expand_directories=True,
            expected=STARRED_CONFIGURATION_B_OPENED,
            label="the_sample_branch_opens_the_way_to_the_variants_a_starred_folder_holds",
        ),
        TestCase(
            starred=("B", "B/drums/kick"),
            auto_expand_reconstructions=True,
            expected=STARRED_FOLDER_HOLDING_A_STAR_OPENED,
            label="a_star_inside_a_starred_folder_opens_that_folder",
        ),
        TestCase(
            starred=("B", "B/drums/kick"),
            auto_expand_directories=True,
            expected=STARRED_FOLDER_HOLDING_A_STAR_BY_FOLDER,
            label="a_star_inside_a_starred_folder_takes_its_own_preference",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_rows_the_mode_opens(
        self,
        corpus: BrowserCorpus,
        test_case: TestCase,
    ) -> None:
        assert (
            view_on_selecting_favorites(
                corpus,
                paths_of(corpus, *test_case.starred),
                auto_expand_reconstructions=test_case.auto_expand_reconstructions,
                auto_expand_directories=test_case.auto_expand_directories,
            )
            == test_case.expected
        )

    def test_a_mode_a_session_restored_opens_nothing(self, corpus: BrowserCorpus) -> None:
        """A browser opens with the rows its reader left standing, whichever stars it would follow."""
        assert (
            view(
                corpus,
                paths_of(corpus, "A/beat"),
                favorites_only=True,
                auto_expand_reconstructions=True,
            )
            == STARRED_RECONSTRUCTION
        )

    def test_the_way_down_stands_open_for_as_long_as_the_mode_does(self, corpus: BrowserCorpus) -> None:
        """A refresh while the mode is on leaves the reader looking at the way down to their stars."""
        panel = build_browser_panel(
            corpus,
            paths_of(corpus, "A/beat"),
            favorites_only=False,
            auto_expand_reconstructions=True,
        )
        select_favorites(panel)
        assert render_view(panel) == STARRED_RECONSTRUCTION_OPENED

        resolve_pass(panel)

        assert render_view(panel) == STARRED_RECONSTRUCTION_OPENED

    def test_a_star_gained_while_the_mode_is_on_opens_no_way_of_its_own(self, corpus: BrowserCorpus) -> None:
        """The reader asked to be pointed at the stars they had, so a star gained since points nowhere."""
        panel = build_browser_panel(
            corpus,
            set(),
            favorites_only=False,
            auto_expand_reconstructions=True,
        )
        select_favorites(panel)
        panel._logic = FakeTreeLogic(  # type: ignore[assignment]
            paths_of(corpus, "A/beat"),
            auto_expand_reconstructions=True,
            auto_expand_directories=False,
        )

        resolve_pass(panel)

        assert render_view(panel) == STARRED_RECONSTRUCTION


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
