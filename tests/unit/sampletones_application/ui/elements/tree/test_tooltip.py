from typing import Final, List

from sampletones_application.ui.elements.tree.tooltip import DetailTooltip, NodeDetail
from sampletones_core.structures.tree import NodeType, TreeNode

PANEL_TAG: Final[str] = "browser"
ROW_TAG: Final[str] = "browser.row"
NOTHING: Final[NodeDetail] = NodeDetail(items=[], recordings=())


class _Describer:
    """Answers every row with nothing to list, noting each row it was asked about."""

    def __init__(self) -> None:
        self.asked: List[TreeNode] = []

    def __call__(self, node: TreeNode) -> NodeDetail:
        self.asked.append(node)
        return NOTHING


def _tooltip(describer: _Describer) -> DetailTooltip:
    return DetailTooltip(PANEL_TAG, describer, swatch_label="stems")


class TestWhatAHoverReads:
    """A hover reads a row's details once per visit, and only for the rows a tree draws."""

    def test_a_row_listing_nothing_leaves_the_tooltip_without_an_owner(self) -> None:
        describer = _Describer()
        tooltip = _tooltip(describer)
        row = TreeNode("song", NodeType.FILE)

        tooltip.follow((row, ROW_TAG))

        assert (describer.asked, tooltip.owner_tag) == ([row], None)

    def test_the_row_the_tooltip_already_shows_is_read_once(self) -> None:
        describer = _Describer()
        tooltip = _tooltip(describer)
        tooltip.owner_tag = ROW_TAG

        tooltip.follow((TreeNode("song", NodeType.FILE), ROW_TAG))

        assert describer.asked == []

    def test_a_row_listing_nothing_is_read_on_every_frame_it_is_hovered(self) -> None:
        """A row that lists nothing owns no tooltip, so the next frame's hover asks it again."""
        describer = _Describer()
        tooltip = _tooltip(describer)
        row = TreeNode("song", NodeType.FILE)

        tooltip.follow((row, ROW_TAG))
        tooltip.follow((row, ROW_TAG))

        assert describer.asked == [row, row]

    def test_hover_data_naming_no_row_reads_nothing(self) -> None:
        describer = _Describer()
        tooltip = _tooltip(describer)

        for user_data in (None, ROW_TAG, 7):
            tooltip.follow(user_data)

        assert describer.asked == []

    def test_a_refresh_without_a_shown_row_reads_nothing(self) -> None:
        describer = _Describer()

        _tooltip(describer).refresh()

        assert describer.asked == []

    def test_two_trees_build_tooltips_of_their_own(self) -> None:
        first = DetailTooltip(PANEL_TAG, _Describer(), swatch_label="stems")
        second = DetailTooltip(f"{PANEL_TAG}.other", _Describer(), swatch_label="stems")

        assert first.tag != second.tag
